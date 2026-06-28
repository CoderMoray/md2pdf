#!/usr/bin/env python3
"""
md2pdf — Markdown → PDF 转换引擎

将 Markdown 文件渲染为排版精美的 PDF。
使用 pandoc（Markdown → HTML）+ Playwright（HTML → PDF）管线。

支持：
  - 封面页（从 YAML front-matter 自动生成）
  - 可交互目录（pandoc --toc + PDF 侧边栏书签）
  - 页码
  - 多主题
  - KaTeX 数学公式（pandoc --katex 原生支持）
  - Mermaid 图表（注入 mermaid.js 渲染）

Usage:
  md2pdf.py --input doc.md                           # 基本转换
  md2pdf.py --input doc.md --output doc.pdf           # 指定输出
  md2pdf.py --input doc.md --font-size 16             # 自定义字号
  md2pdf.py --input doc.md --page-size A3             # 自定义纸张
  md2pdf.py --input doc.md --theme academic           # 切换主题
  md2pdf.py --input doc.md --no-cover --no-toc        # 无封面/目录
  md2pdf.py --input doc.md --toc-depth 2              # 目录深度
  md2pdf.py --input doc.md --katex                    # 启用 KaTeX 数学公式
  md2pdf.py --input doc.md --mermaid                  # 启用 Mermaid 图表
  md2pdf.py --validate                                 # 环境检测
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

from validate import run_validate, _find_python_with_playwright


# ============================================================
# 路径
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
THEMES_DIR = os.path.join(PROJECT_DIR, "themes")


# ============================================================
# Front-matter 解析（纯正则，无外部依赖）
# ============================================================

def parse_front_matter(text):
    """从 Markdown 文本中解析 YAML front-matter，返回 (meta, body)。"""
    meta = {}
    body = text

    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if m:
        raw = m.group(1)
        body = text[m.end():]
        for line in raw.splitlines():
            line = line.strip()
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.+)$', line)
            if kv:
                key = kv.group(1)
                val = kv.group(2).strip().strip('"').strip("'")
                meta[key] = val

    return meta, body


# ============================================================
# 主题管理
# ============================================================

AVAILABLE_THEMES = {}

def _scan_themes():
    """扫描 themes/ 目录获取可用主题列表"""
    global AVAILABLE_THEMES
    if not os.path.isdir(THEMES_DIR):
        AVAILABLE_THEMES = {}
        return
    for f in os.listdir(THEMES_DIR):
        if f.endswith(".css"):
            name = f[:-4]
            AVAILABLE_THEMES[name] = os.path.join(THEMES_DIR, f)

_scan_themes()


def load_theme_css(theme_name, font_size=None, font_family=None, chinese_layout=False):
    """加载主题 CSS，可选覆盖字号、字体、中文排版层"""
    if theme_name not in AVAILABLE_THEMES:
        print(f"⚠️  主题 '{theme_name}' 不存在，使用 default")
        theme_name = "default"

    path = AVAILABLE_THEMES.get(theme_name)
    if not path:
        return ""

    with open(path, "r", encoding="utf-8") as f:
        css = f.read()

    if font_size:
        css = re.sub(r'font-size:\s*14px;', f'font-size: {font_size}px;', css)
        css = re.sub(r'font-size:\s*14pt;', f'font-size: {font_size}pt;', css)
        css = re.sub(r'font-size:\s*12pt;', f'font-size: {font_size}pt;', css)

    if font_family:
        # 替换 body 的 font-family 声明
        css = re.sub(
            r'(body\s*\{[^}]*font-family:\s*)[^;"]*("?[^;"]*"?);',
            rf'\1{font_family};',
            css,
        )

    # 叠加中文排版层（chinese.css 中仅保留排版规则，不含主题色/字体等）
    if chinese_layout:
        chinese_css_path = os.path.join(THEMES_DIR, "chinese.css")
        if os.path.isfile(chinese_css_path):
            with open(chinese_css_path, "r", encoding="utf-8") as f:
                css += "\n/* === 中文排版层 === */\n" + f.read()

    return css


def list_themes():
    """返回可用主题列表"""
    return sorted(AVAILABLE_THEMES.keys())


# ============================================================
# 封面页生成
# ============================================================

def build_cover_html(meta):
    """根据 front-matter 元数据生成封面页 HTML"""
    parts = ['<section data-page="cover" class="md2pdf-cover">']

    title = meta.get("title", "")
    if title:
        parts.append(f'<h1>{_escape_html(title)}</h1>')

    subtitle = meta.get("subtitle", "")
    if subtitle:
        parts.append(f'<p class="subtitle">{_escape_html(subtitle)}</p>')

    parts.append('<hr>')

    author = meta.get("author", "")
    if author:
        parts.append(f'<p class="meta">{_escape_html(author)}</p>')

    date = meta.get("date", "")
    if date:
        parts.append(f'<p class="meta">{_escape_html(date)}</p>')

    version = meta.get("version", "")
    if version:
        parts.append(f'<p class="version">v{_escape_html(version)}</p>')

    parts.append('</section>')
    return "\n".join(parts)


def _escape_html(text):
    """简单的 HTML 转义"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ============================================================
# 页码页脚 HTML
# ============================================================

def build_footer_html():
    """Playwright footerTemplate — 居中页码 Page X / Y"""
    return """
    <div style="
        width: 100%;
        text-align: center;
        font-size: 9px;
        color: #8e8e93;
        font-family: -apple-system, 'PingFang SC', sans-serif;
        padding: 0 20mm;
    ">
        <span class="pageNumber"></span> / <span class="totalPages"></span>
    </div>
    """


# ============================================================
# Mermaid 离线缓存
# ============================================================

MERMAID_JS_PATH = os.path.join(PROJECT_DIR, "themes", "mermaid.min.js")
MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"


def _ensure_mermaid():
    """确保本地有 mermaid.min.js，没有则自动下载"""
    if os.path.isfile(MERMAID_JS_PATH):
        return True
    try:
        import urllib.request
        urllib.request.urlretrieve(MERMAID_CDN_URL, MERMAID_JS_PATH)
        return True
    except Exception:
        return False


HIGHLIGHT_JS_PATH = os.path.join(PROJECT_DIR, "themes", "highlight.min.js")
HIGHLIGHT_CSS_PATH = os.path.join(PROJECT_DIR, "themes", "highlight.css")
HIGHLIGHT_JS_URL = "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/highlight.min.js"
HIGHLIGHT_CSS_URL = "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/styles/github.min.css"


def _ensure_highlight():
    """确保本地有 highlight.js，没有则自动下载"""
    ok = True
    for path, url in [(HIGHLIGHT_JS_PATH, HIGHLIGHT_JS_URL), (HIGHLIGHT_CSS_PATH, HIGHLIGHT_CSS_URL)]:
        if os.path.isfile(path):
            continue
        try:
            import urllib.request
            urllib.request.urlretrieve(url, path)
        except Exception:
            ok = False
    return ok


# ============================================================
# 核心转换
# ============================================================

def find_python_executable():
    for python_path in _find_python_with_playwright():
        result = subprocess.run(
            [python_path, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return python_path
    return None


def md_to_pdf(md_path, pdf_path, font_size=None, page_size=None,
              theme="default", with_cover=True, with_toc=True, toc_depth=4,
              font_family=None, katex=False, mermaid=False, chinese_layout=False,
              highlight=True):
    """
    Markdown → PDF 转换管线。

    管线: Markdown → 解析 front-matter → pandoc (--toc, --katex) →
          注入封面 HTML → 注入 CSS 主题 + 中文排版层 →
          注入 Mermaid/highlight.js → Playwright PDF
    """

    # --- 输入验证 ---
    if not os.path.isfile(md_path):
        return {"ok": False, "error": f"输入文件不存在: {md_path}"}

    # --- 读取并解析 Markdown ---
    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    meta, body = parse_front_matter(raw_text)

    # --- 封面智能处理 ---
    # 如果用户要封面但没有 title，自动用文件名作为标题
    if with_cover and not meta.get("title"):
        basename = os.path.splitext(os.path.basename(md_path))[0]
        # 去掉常见的连字符美化文件名
        display_name = basename.replace("-", " ").replace("_", " ").strip()
        meta["title"] = display_name

    # --- Step 1: pandoc MD → HTML ---
    # 注意：front-matter 已剥离，pandoc 不会自动生成标题块
    pandoc_args = [
        "pandoc",
        "-f", "commonmark_x",
        "-t", "html5",
        "--self-contained",
    ]

    if with_toc:
        pandoc_args.extend(["--toc", f"--toc-depth={toc_depth}"])

    if katex:
        pandoc_args.append("--katex")

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        html_path = f.name

    pandoc_proc = subprocess.run(
        pandoc_args + ["-o", html_path],
        input=body,
        capture_output=True, text=True, timeout=180,
    )

    if pandoc_proc.returncode != 0:
        os.unlink(html_path)
        stderr_text = pandoc_proc.stderr.strip()
        if not stderr_text:
            stderr_text = "(无错误输出，可能文件为空或编码异常)"
        return {"ok": False, "error": f"pandoc 转换失败 → 常见原因: MD 语法错误、非 UTF-8 编码、文件不是 Markdown。\n详情: {stderr_text}"}

    # --- Step 2: 注入封面 + Mermaid + KaTeX CSS ---
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 移除 pandoc --self-contained 自动注入的默认样式（会覆盖主题 CSS）
    html = re.sub(r'<style>.*?</style>', '', html, flags=re.DOTALL)

    if with_cover:
        cover_html = build_cover_html(meta)
        if cover_html.strip():
            html = html.replace("<body>", f"<body>\n{cover_html}")

    # --- Step 3: 注入 CSS 主题 + 中文排版层 ---
    css = load_theme_css(theme, font_size, font_family, chinese_layout)
    if css:
        html = html.replace("</head>", f"<style>{css}</style></head>")

    # --- Step 3.5: 注入 Mermaid.js（离线缓存，需在 CSS 之后） ---
    has_mermaid = False
    if mermaid:
        if re.search(r'```\s*mermaid', raw_text, re.IGNORECASE):
            if not _ensure_mermaid():
                print("  ⚠️  无法下载 mermaid.js，跳过 Mermaid 渲染", file=sys.stderr)
            else:
                has_mermaid = True
                mermaid_injection = f"""
<script src="file://{MERMAID_JS_PATH}"></script>
<script>
  mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
</script>
<style>
  pre.mermaid, div.mermaid, svg[id^="mermaid-"] {{
    max-width: 100%;
    page-break-inside: avoid;
  }}
</style>
"""
                html = html.replace("</head>", f"{mermaid_injection}</head>")
                mermaid_transform_js = """
<script>
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('pre code').forEach(function(block) {
      var parent = block.parentElement;
      var classes = (parent.className + ' ' + block.className).toLowerCase();
      if (classes.indexOf('mermaid') === -1) return;
      parent.style.display = 'none';
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = block.textContent.trim();
      parent.parentNode.insertBefore(div, parent);
    });
    mermaid.init(undefined, document.querySelectorAll('.mermaid'));
  });
</script>
"""
                html = html.replace("</body>", f"{mermaid_transform_js}</body>")

    # --- Step 3.6: 注入 highlight.js（代码语法高亮，离线缓存） ---
    has_highlight = False
    if highlight:
        if re.search(r'<pre[^>]*><code', html):
            if not _ensure_highlight():
                print("  ⚠️  无法下载 highlight.js，跳过代码高亮", file=sys.stderr)
            else:
                has_highlight = True
                hl_injection = f"""
<link rel="stylesheet" href="file://{HIGHLIGHT_CSS_PATH}">
<script src="file://{HIGHLIGHT_JS_PATH}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    // pandoc 输出 class="sourceCode python"，去掉 sourceCode 让 highlight.js 识别语言
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

    # 纸张大小映射
    page_size_map = {
        "A4": "format='A4'",
        "A3": "format='A3'",
        "letter": "format='Letter'",
        "legal": "format='Legal'",
    }
    pdf_options = page_size_map.get(page_size or "A4", "format='A4'")

    footer_html = build_footer_html()

    # 计算页面内容区宽度（mm → CSS px，96 DPI: 1mm = 96/25.4 px）
    page_size_mm = {"A4": (210, 297), "A3": (297, 420),
                    "Letter": (215.9, 279.4), "Legal": (215.9, 355.6)}
    pw = page_size_mm.get(page_size or "A4", (210, 297))
    margin_mm = 20
    content_width_mm = pw[0] - 2 * margin_mm
    content_width_px = int(content_width_mm * 96 / 25.4)

    # Mermaid 等待逻辑
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

    # 宽表缩放 JS
    table_scale_js = f"""
    # 宽表自动缩放：按列数自适应，避免 A4 页面截断
    page.evaluate('''() => {{
        document.querySelectorAll('table').forEach(function(table) {{
            if (table.closest('.md2pdf-cover')) return;
            var cols = table.rows[0] ? table.rows[0].cells.length : 0;
            // 5列=0.85, 6列=0.75, 7列=0.65, 8+列=0.55
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
html_path = {repr(html_path)}
pdf_path = {repr(pdf_path)}
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('file://' + html_path)
    page.wait_for_load_state('networkidle')
    # 动态设置封面高度为页面可用高度，消除空白页
    page.evaluate('''() => {{
        var cover = document.querySelector('.md2pdf-cover');
        if (!cover) return;
        var vh = window.innerHeight;
        cover.style.minHeight = vh + 'px';
        cover.style.height = vh + 'px';
        cover.style.boxSizing = 'border-box';
    }}''')
    page.wait_for_timeout(200)
    # H1 智能分页：如果 H1 不在页面顶部区域（前 30%），另起一页
    page.evaluate('''() => {{
        var pageHeight = window.innerHeight;
        var h1s = document.querySelectorAll('h1');
        h1s.forEach(function(h1) {{
            if (h1.closest('.md2pdf-cover')) return;
            var rect = h1.getBoundingClientRect();
            var posInPage = rect.top % pageHeight;
            if (posInPage < 0) posInPage += pageHeight;
            if (posInPage > pageHeight * 0.3) {{
                h1.style.pageBreakBefore = 'always';
            }}
        }});
    }}''')
    page.wait_for_timeout(100){table_scale_js}{mermaid_wait}
    {'page.wait_for_timeout(300)  # 等待 highlight.js 完成' if has_highlight else ''}
    page.pdf(
        path=pdf_path,
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

    pdf_size = os.path.getsize(pdf_path)
    return {"ok": True, "output": pdf_path, "size": pdf_size}


# ============================================================
# PDF 页面诊断
# ============================================================

def diagnose_pdf(pdf_path, with_cover=True, with_toc=True):
    """分析 PDF 页数，检测异常空白页"""
    if not os.path.isfile(pdf_path):
        print(f"  ❌ PDF 文件不存在: {pdf_path}", file=sys.stderr)
        return

    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ 无法读取 PDF: {e}", file=sys.stderr)
        return

    # 精确统计页数：正则 /\bType\s*/\s*Page\b 匹配页面对象，
    # 不会误匹配 /Type /Pages（页面树节点）
    page_count = len(re.findall(rb'/Type\s*/\s*Page\b', content))

    print("=" * 55)
    print("  📄 PDF 页面诊断")
    print("=" * 55)
    print(f"  文件: {pdf_path}")
    print(f"  大小: {os.path.getsize(pdf_path) / 1024:.0f} KB")
    print(f"  总页数: {page_count}")

    # 根据实际参数生成预期结构
    expected_notes = []
    page_idx = 0
    if with_cover:
        page_idx += 1
        expected_notes.append(f"P{page_idx} 封面")
    if with_toc:
        page_idx += 1
        expected_notes.append(f"P{page_idx} 目录")
    if page_count > page_idx:
        expected_notes.append(f"P{page_idx + 1}~P{page_count} 正文")

    if expected_notes:
        print(f"  预期: {' → '.join(expected_notes)}")

    # 检查页数合理性
    min_pages = (1 if with_cover else 0) + (1 if with_toc else 0)
    has_content = page_count > min_pages
    if page_count <= 1 and with_cover:
        print(f"\n  ⚠️  警告: 只有 {page_count} 页，请检查内容是否为空")
    elif page_count <= min_pages and min_pages > 0 and not has_content:
        print(f"\n  ℹ️  仅封面/目录页，正文内容较短")
    else:
        print(f"\n  ✅ 页面结构合理")


# ============================================================
# CLI 入口
# ============================================================

def main():
    themes_list = [t for t in (list_themes() or ["default"]) if t != "chinese"]

    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown 转 PDF（pandoc + Playwright 引擎）",
    )
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 文件路径")
    parser.add_argument("--validate", action="store_true", help="仅检测环境，不执行转换")
    parser.add_argument("--font-size", type=int, default=None, help="正文字号（px），默认 14")
    parser.add_argument("--page-size", default="A4", choices=["A4", "A3", "letter", "legal"],
                        help="纸张大小，默认 A4")
    parser.add_argument("--theme", default="default", choices=themes_list,
                        help=f"主题，默认 default。可用: {', '.join(themes_list)}")
    parser.add_argument("--cover", action="store_true", default=True,
                        help="生成封面页（从 front-matter 自动生成，默认开启）")
    parser.add_argument("--no-cover", action="store_false", dest="cover",
                        help="不生成封面页")
    parser.add_argument("--toc", action="store_true", default=True,
                        help="生成目录（默认开启）")
    parser.add_argument("--no-toc", action="store_false", dest="toc",
                        help="不生成目录")
    parser.add_argument("--toc-depth", type=int, default=4, choices=range(1, 7),
                        help="目录深度（标题层级 1-6），默认 4")
    parser.add_argument("--font-family", default=None,
                        help="正文字体，覆盖主题默认字体。如 PingFang SC, Noto Serif CJK SC")
    parser.add_argument("--katex", action="store_true", default=False,
                        help="启用 KaTeX 数学公式渲染（pandoc --katex）")
    parser.add_argument("--mermaid", action="store_true", default=False,
                        help="启用 Mermaid 图表渲染（注入 mermaid.js）")
    parser.add_argument("--chinese-layout", action="store_true", default=False,
                        help="叠加中文排版增强（行距、首行缩进、禁则处理），可配合任意主题使用")
    parser.add_argument("--highlight", action="store_true", default=True,
                        help="启用代码语法高亮（highlight.js，默认开启）")
    parser.add_argument("--no-highlight", action="store_false", dest="highlight",
                        help="关闭代码语法高亮")
    parser.add_argument("--list-themes", action="store_true", default=False,
                        help="列出所有可用主题")

    args = parser.parse_args()

    # --list-themes 模式
    if args.list_themes:
        for t in themes_list:
            print(t)
        sys.exit(0)

    # --validate 模式
    if args.validate:
        ok = run_validate(themes_list, MERMAID_JS_PATH,
                         HIGHLIGHT_JS_PATH, HIGHLIGHT_CSS_PATH)
        sys.exit(0 if ok else 1)

    # 参数校验
    if not args.input:
        parser.error("请指定 --input")
    if not args.output:
        input_abs = os.path.abspath(args.input)
        # 如果输入文件在本技能目录内，输出到 output/ 目录
        if input_abs.startswith(PROJECT_DIR):
            os.makedirs(os.path.join(PROJECT_DIR, "output"), exist_ok=True)
            base = os.path.splitext(os.path.basename(args.input))[0]
            args.output = os.path.join(PROJECT_DIR, "output", base + ".pdf")
        else:
            base = os.path.splitext(args.input)[0]
            args.output = base + ".pdf"

    # 执行转换
    result = md_to_pdf(
        md_path=args.input,
        pdf_path=args.output,
        font_size=args.font_size,
        page_size=args.page_size,
        theme=args.theme,
        with_cover=args.cover,
        with_toc=args.toc,
        toc_depth=args.toc_depth,
        font_family=args.font_family,
        katex=args.katex,
        mermaid=args.mermaid,
        chinese_layout=args.chinese_layout,
        highlight=args.highlight,
    )

    if result["ok"]:
        size_kb = result["size"] / 1024
        print(f"✅ 转换完成: {result['output']} ({size_kb:.0f} KB)")
        # 自动做页面诊断，检测空页等异常
        diagnose_pdf(result["output"], with_cover=args.cover, with_toc=args.toc)
        sys.exit(0)
    else:
        print(f"❌ 转换失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
