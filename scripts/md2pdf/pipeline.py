"""核心转换管线：Markdown → HTML → PDF"""

import os
import re
import subprocess
import sys
import tempfile

from .config import (
    MERMAID_JS_PATH, MERMAID_CDN_URL,
    HIGHLIGHT_JS_PATH, HIGHLIGHT_CSS_PATH,
)
from .utils import parse_front_matter, find_python_executable, build_footer_html
from .themes import load_theme_css
from .cover import build_cover_html
from .assets import _ensure_mermaid, _ensure_highlight


def md_to_pdf(md_path, pdf_path, font_size=None, page_size=None,
              theme="default", with_cover=True, with_toc=True, toc_depth=4,
              font_family=None, katex=False, mermaid=False, chinese_layout=False,
              highlight=True):
    """Markdown → PDF 转换管线"""

    if not os.path.isfile(md_path):
        return {"ok": False, "error": f"输入文件不存在: {md_path}"}

    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    meta, body = parse_front_matter(raw_text)

    if with_cover and not meta.get("title"):
        basename = os.path.splitext(os.path.basename(md_path))[0]
        meta["title"] = basename.replace("-", " ").replace("_", " ").strip()

    # --- Step 1: pandoc MD → HTML ---
    pandoc_args = ["pandoc", "-f", "commonmark_x", "-t", "html5", "--self-contained"]
    if with_toc:
        pandoc_args.extend(["--toc", f"--toc-depth={toc_depth}"])
    if katex:
        pandoc_args.append("--katex")

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        html_path = f.name

    pandoc_proc = subprocess.run(
        pandoc_args + ["-o", html_path],
        input=body, capture_output=True, text=True, timeout=180,
    )

    if pandoc_proc.returncode != 0:
        os.unlink(html_path)
        stderr_text = pandoc_proc.stderr.strip() or "(无错误输出，可能文件为空或编码异常)"
        return {"ok": False, "error": f"pandoc 转换失败 → 常见原因: MD 语法错误、非 UTF-8 编码、文件不是 Markdown。\n详情: {stderr_text}"}

    # --- Step 2: 注入封面 ---
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(r'<style>.*?</style>', '', html, flags=re.DOTALL)

    if with_cover:
        cover = build_cover_html(meta)
        if cover.strip():
            html = html.replace("<body>", f"<body>\n{cover}")

    # --- Step 3: CSS ---
    css = load_theme_css(theme, font_size, font_family, chinese_layout)
    if css:
        html = html.replace("</head>", f"<style>{css}</style></head>")

    # --- Step 3.5: Mermaid ---
    has_mermaid = False
    if mermaid:
        if re.search(r'```\s*mermaid', raw_text, re.IGNORECASE):
            if not _ensure_mermaid():
                print("  ⚠️  无法下载 mermaid.js，跳过 Mermaid 渲染", file=sys.stderr)
            else:
                has_mermaid = True
                html = html.replace("</head>", f"""<script src="file://{MERMAID_JS_PATH}"></script>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
<style>pre.mermaid, div.mermaid, svg[id^="mermaid-"] {{ max-width:100%; page-break-inside:avoid; }}</style>
</head>""")
                mermaid_transform_js = """<script>
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('pre code').forEach(function(block) {
        var parent = block.parentElement;
        if ((parent.className + ' ' + block.className).toLowerCase().indexOf('mermaid') === -1) return;
        parent.style.display = 'none';
        var div = document.createElement('div'); div.className = 'mermaid';
        div.textContent = block.textContent.trim();
        parent.parentNode.insertBefore(div, parent);
    });
    mermaid.init(undefined, document.querySelectorAll('.mermaid'));
});
</script>"""
                html = html.replace("</body>", f"{mermaid_transform_js}</body>")

    # --- Step 3.6: Highlight.js ---
    has_highlight = False
    if highlight:
        if re.search(r'<pre[^>]*><code', html):
            if not _ensure_highlight():
                print("  ⚠️  无法下载 highlight.js，跳过代码高亮", file=sys.stderr)
            else:
                has_highlight = True
                hl_injection = f"""<link rel="stylesheet" href="file://{HIGHLIGHT_CSS_PATH}">
<script src="file://{HIGHLIGHT_JS_PATH}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('pre code').forEach(function(el) {{
        el.className = el.className.replace(/sourceCode\\s*/g, '').trim();
        el.parentElement.className = el.parentElement.className.replace(/sourceCode\\s*/g, '').trim();
    }});
    hljs.highlightAll();
}});
</script>
"""
                html = html.replace("</head>", f"{hl_injection}</head>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # --- Step 4: Playwright HTML → PDF ---
    python_exec = find_python_executable()
    if not python_exec:
        os.unlink(html_path)
        return {"ok": False, "error": "未找到安装了 Playwright 的 Python 环境"}

    page_size_map = {"A4": "format='A4'", "A3": "format='A3'",
                     "letter": "format='Letter'", "legal": "format='Legal'"}
    pdf_options = page_size_map.get(page_size or "A4", "format='A4'")

    footer_html = build_footer_html()

    page_size_mm = {"A4": (210, 297), "A3": (297, 420),
                    "Letter": (215.9, 279.4), "Legal": (215.9, 355.6)}
    pw_mm = page_size_mm.get(page_size or "A4", (210, 297))
    content_width_px = int((pw_mm[0] - 40) * 96 / 25.4)

    mermaid_wait = ""
    if has_mermaid:
        mermaid_wait = """
    page.evaluate('''() => {
        return new Promise(resolve => {
            if (typeof mermaid === 'undefined') { resolve(); return; }
            mermaid.init(undefined, document.querySelectorAll('.mermaid'));
            var check = setInterval(function() {
                var pending = document.querySelectorAll('.mermaid[data-processed="false"], .mermaid:not([data-processed])');
                if (pending.length === 0) { clearInterval(check); resolve(); }
            }, 200);
            setTimeout(function() { clearInterval(check); resolve(); }, 10000);
        });
    }''')
    page.wait_for_timeout(500)
"""

    table_scale_js = f"""
    page.evaluate('''() => {{
        document.querySelectorAll('table').forEach(function(table) {{
            if (table.closest('.md2pdf-cover')) return;
            var cols = table.rows[0] ? table.rows[0].cells.length : 0;
            if (cols >= 5) {{
                var scale = Math.max(0.50, 1.35 - cols * 0.10).toFixed(2);
                table.style.zoom = scale;
                table.style.width = 'auto';
                table.style.margin = '0 auto';
            }}
        }});
    }}''')
    page.wait_for_timeout(100)
"""

    code = f"""
import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('file://{html_path}')
    page.wait_for_load_state('networkidle')
    page.evaluate('''() => {{
        var cover = document.querySelector('.md2pdf-cover');
        if (cover) {{
            cover.style.minHeight = cover.style.height = window.innerHeight + 'px';
            cover.style.boxSizing = 'border-box';
        }}
    }}''')
    page.wait_for_timeout(200)
    page.evaluate('''() => {{
        var ph = window.innerHeight;
        document.querySelectorAll('h1').forEach(function(h) {{
            if (h.closest('.md2pdf-cover')) return;
            var pos = h.getBoundingClientRect().top % ph;
            if (pos < 0) pos += ph;
            if (pos > ph * 0.3) h.style.pageBreakBefore = 'always';
        }});
    }}''')
    page.wait_for_timeout(100){table_scale_js}{mermaid_wait}
    {'page.wait_for_timeout(300)' if has_highlight else ''}
    page.pdf(
        path={repr(pdf_path)},
        {pdf_options},
        outline=True,
        display_header_footer=True,
        header_template='<span></span>',
        footer_template={repr(footer_html)},
        margin={{"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}},
    )
    browser.close()
print('OK')
"""

    pw_result = subprocess.run(
        [python_exec, "-c", code],
        capture_output=True, text=True, timeout=120,
    )

    os.unlink(html_path)

    if pw_result.returncode != 0:
        return {"ok": False, "error": f"HTML→PDF 渲染失败 → 常见原因: Chromium 未安装、系统资源不足。运行 --validate 检查。\n详情: {pw_result.stderr}"}

    if not os.path.isfile(pdf_path):
        return {"ok": False, "error": "PDF 文件未生成 → 可能原因: 输出路径无写入权限、磁盘空间不足。请检查: {pdf_path}"}

    return {"ok": True, "output": pdf_path, "size": os.path.getsize(pdf_path)}
