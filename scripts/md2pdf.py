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

Usage:
  md2pdf.py --input doc.md                           # 基本转换
  md2pdf.py --input doc.md --output doc.pdf           # 指定输出
  md2pdf.py --input doc.md --font-size 16             # 自定义字号
  md2pdf.py --input doc.md --page-size A3             # 自定义纸张
  md2pdf.py --input doc.md --theme academic           # 切换主题
  md2pdf.py --input doc.md --no-cover --no-toc        # 无封面/目录
  md2pdf.py --input doc.md --toc-depth 2              # 目录深度
  md2pdf.py --validate                                 # 环境检测
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


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


def load_theme_css(theme_name, font_size=None):
    """加载主题 CSS，可选覆盖字号"""
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

    return css


def list_themes():
    """返回可用主题列表"""
    return sorted(AVAILABLE_THEMES.keys())


# ============================================================
# 封面页生成
# ============================================================

def build_cover_html(meta):
    """根据 front-matter 元数据生成封面页 HTML"""
    parts = ['<div class="md2pdf-cover" style="page-break-after:always;">']

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

    parts.append('</div>')
    return "\n".join(parts)


def _escape_html(text):
    """简单的 HTML 转义"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ============================================================
# 页码页脚 HTML
# ============================================================

def build_footer_html():
    """Playwright footerTemplate — 居中页码"""
    return """
    <div style="
        width: 100%;
        text-align: center;
        font-size: 9px;
        color: #8e8e93;
        font-family: -apple-system, 'PingFang SC', sans-serif;
        padding: 0 20mm;
    ">
        <span class="pageNumber"></span>
    </div>
    """


# ============================================================
# 环境检测
# ============================================================

def check_pandoc():
    path = shutil.which("pandoc")
    if path:
        result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.splitlines()[0] if result.stdout else "unknown"
        return {"available": True, "path": path, "version": version}
    return {"available": False, "path": None, "version": None}


def check_playwright():
    playwright_cmd = shutil.which("playwright")
    if playwright_cmd:
        result = subprocess.run([playwright_cmd, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() if result.stdout else "unknown"
        return {"available": True, "path": playwright_cmd, "version": version}

    for python_candidate in [
        "/opt/homebrew/Caskroom/miniconda/base/bin/python3",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
    ]:
        if os.path.isfile(python_candidate):
            result = subprocess.run(
                [python_candidate, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return {"available": True, "path": python_candidate, "version": "via " + python_candidate}

    return {"available": False, "path": None, "version": None}


def check_chromium():
    probe_code = """
import sys
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        b.close()
    print('ok')
except Exception as e:
    print(f'FAIL: {e}', file=sys.stderr)
    sys.exit(1)
"""
    for python_candidate in _find_python_with_playwright():
        result = subprocess.run(
            [python_candidate, "-c", probe_code.strip()],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"available": True, "detail": "Chromium 可用"}
        elif "executable doesn't exist" in result.stderr:
            return {"available": False, "detail": "Chromium 未安装，运行 playwright install chromium"}
        else:
            return {"available": False, "detail": (result.stderr.strip() or result.stdout.strip())[:200]}
    return {"available": False, "detail": "无法找到可用的 Python 环境"}


def _find_python_with_playwright():
    candidates = []
    for p in [
        "/opt/homebrew/Caskroom/miniconda/base/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    ]:
        if os.path.isfile(p):
            candidates.append(p)
    return candidates


def run_validate():
    print("=" * 55)
    print("  md2pdf — 环境检测")
    print("=" * 55)

    pc = check_pandoc()
    if pc["available"]:
        print(f"  ✅ pandoc: {pc['version']}")
        print(f"    路径: {pc['path']}")
    else:
        print("  ❌ pandoc: 未找到")
        print("    安装: brew install pandoc")

    pw = check_playwright()
    if pw["available"]:
        print(f"  ✅ Playwright: {pw['version']}")
        print(f"    路径: {pw['path']}")
    else:
        print("  ❌ Playwright: 未找到")
        print("    安装: pip install playwright && playwright install chromium")

    if pw["available"]:
        cr = check_chromium()
        if cr["available"]:
            print("  ✅ Chromium: 就绪")
        else:
            print(f"  ❌ Chromium: {cr['detail']}")
    else:
        print("  ⚠️ Chromium: 跳过（Playwright 不可用）")

    themes = list_themes()
    if themes:
        print(f"\n  🎨 可用主题: {', '.join(themes)}")
    else:
        print("\n  ⚠️ 未找到主题文件")

    all_ok = pc["available"] and pw["available"] and cr["available"] if pw["available"] else False
    if all_ok:
        print("\n  🟢 环境就绪，可以转换。")
    else:
        print("\n  🔴 环境不完整，请安装缺失组件。")
    return all_ok


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
              theme="default", with_cover=True, with_toc=True, toc_depth=4):
    """
    Markdown → PDF 转换管线。

    管线: Markdown → 解析 front-matter → pandoc (--toc) →
          注入封面 HTML → 注入 CSS 主题 → Playwright PDF (outline + 页码)
    """

    # --- 输入验证 ---
    if not os.path.isfile(md_path):
        return {"ok": False, "error": f"输入文件不存在: {md_path}"}

    # --- 读取并解析 Markdown ---
    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    meta, body = parse_front_matter(raw_text)

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

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        html_path = f.name

    pandoc_proc = subprocess.run(
        pandoc_args + ["-o", html_path],
        input=body,
        capture_output=True, text=True, timeout=60,
    )

    if pandoc_proc.returncode != 0:
        os.unlink(html_path)
        return {"ok": False, "error": f"pandoc 转换失败:\n{pandoc_proc.stderr}"}

    # --- Step 2: 注入封面 + 分页控制 ---
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 封面：在 <body> 开头注入（封面自带 page-break-after:always 行内样式）
    if with_cover:
        cover_html = build_cover_html(meta)
        if cover_html.strip():
            html = html.replace("<body>", f"<body>\n{cover_html}")

    # 目录 nav：添加 page-break-after:always（封面已 break → TOC 自然从第 2 页开始）
    if with_toc:
        html = html.replace(
            '<nav id="TOC"',
            '<nav id="TOC" style="page-break-after:always;"',
        )

    # --- Step 3: 注入 CSS 主题 ---
    css = load_theme_css(theme, font_size)
    if css:
        html = html.replace("</head>", f"<style>{css}</style></head>")

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
    page.pdf(
        path=pdf_path,
        {pdf_options},
        outline=True,
        display_header_footer=True,
        header_template='',
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
        return {"ok": False, "error": f"Playwright PDF 生成失败:\n{pw_result.stderr}"}

    if not os.path.isfile(pdf_path):
        return {"ok": False, "error": "PDF 文件未生成（未知错误）"}

    pdf_size = os.path.getsize(pdf_path)
    return {"ok": True, "output": pdf_path, "size": pdf_size}


# ============================================================
# PDF 页面诊断
# ============================================================

def diagnose_pdf(pdf_path):
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

    # 统计 /Type /Page 出现次数 = 总页数
    page_count = content.count(b'/Type /Page')

    print("=" * 55)
    print("  📄 PDF 页面诊断")
    print("=" * 55)
    print(f"  文件: {pdf_path}")
    print(f"  大小: {os.path.getsize(pdf_path) / 1024:.0f} KB")
    print(f"  总页数: {page_count}")

    # 预期的页面结构提示
    expected_notes = []
    if page_count >= 1:
        expected_notes.append("P1 封面")
    if page_count >= 2:
        expected_notes.append("P2 目录")
    if page_count >= 3:
        expected_notes.append(f"P3~P{page_count} 正文")

    print(f"  预期: {' → '.join(expected_notes)}")

    # 检查页数合理性
    # 封面 + 目录 + 至少 1 页内容 = 最少 3 页
    # 如果只有 1-2 页但开启了封面+目录，说明很可能有空页合并或分页失败
    if page_count <= 2 and expected_notes:
        print(f"\n  ⚠️  警告: 开启了封面+目录但只有 {page_count} 页")
        print(f"  可能原因: page-break 未生效，内容挤在同一页")
    elif page_count <= 1:
        print(f"\n  ⚠️  警告: 只有 {page_count} 页，请检查内容是否为空")
    else:
        print(f"\n  ✅ 页面结构合理")


# ============================================================
# CLI 入口
# ============================================================

def main():
    themes_list = list_themes() or ["default"]

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

    args = parser.parse_args()

    # --validate 模式
    if args.validate:
        ok = run_validate()
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
    )

    if result["ok"]:
        size_kb = result["size"] / 1024
        print(f"✅ 转换完成: {result['output']} ({size_kb:.0f} KB)")
        # 自动做页面诊断，检测空页等异常
        diagnose_pdf(result["output"])
        sys.exit(0)
    else:
        print(f"❌ 转换失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
