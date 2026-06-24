#!/usr/bin/env python3
"""
md2pdf — Markdown → PDF 转换引擎

将 Markdown 文件渲染为排版精美的 PDF。
使用 pandoc（Markdown → HTML）+ Playwright（HTML → PDF）管线。

Usage:
  md2pdf.py --input doc.md --output doc.pdf            # 基本转换
  md2pdf.py --input doc.md --output doc.pdf --font-size 16   # 自定义字号
  md2pdf.py --validate                                   # 环境检测
  md2pdf.py --input doc.md --output doc.pdf --page-size A3   # 自定义纸张
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


# ============================================================
# CSS 样式（内置，不依赖外部文件）
# ============================================================

STYLE_CSS = """
body {
    font-family: -apple-system, "PingFang SC", "Heiti SC", sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #1d1d1f;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
}
h1 { font-size: 24px; font-weight: 700; margin-top: 32px; margin-bottom: 16px; }
h2 { font-size: 19px; font-weight: 600; margin-top: 28px; margin-bottom: 12px;
     padding-bottom: 6px; border-bottom: 1px solid #e5e5ea; }
h3 { font-size: 16px; font-weight: 600; margin-top: 24px; margin-bottom: 8px; }
h4 { font-size: 15px; font-weight: 600; margin-top: 20px; margin-bottom: 6px; }
p { margin: 8px 0; }
ul, ol { margin: 8px 0; padding-left: 24px; }
li { margin: 6px 0; line-height: 1.7; }
li p { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
th, td { border: 1px solid #d1d1d6; padding: 8px 12px; text-align: left; }
th { background: #f5f5f7; font-weight: 600; }
code { background: #f5f5f7; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
pre { background: #f5f5f7; padding: 16px; border-radius: 8px; overflow-x: auto;
      font-size: 12px; line-height: 1.5; margin: 12px 0; }
blockquote { border-left: 3px solid #007aff; margin: 12px 0; padding: 8px 16px;
             background: #f5f5f7; border-radius: 0 8px 8px 0; }
blockquote p { margin: 4px 0; }
hr { border: none; border-top: 1px solid #e5e5ea; margin: 24px 0; }
strong { font-weight: 700; }
img { max-width: 100%; height: auto; }
code { font-family: "SF Mono", "Menlo", "Consolas", monospace; }
"""


# ============================================================
# 环境检测
# ============================================================

def check_pandoc():
    """检查 pandoc 是否可用"""
    path = shutil.which("pandoc")
    if path:
        result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.splitlines()[0] if result.stdout else "unknown"
        return {"available": True, "path": path, "version": version}
    return {"available": False, "path": None, "version": None}


def check_playwright():
    """检查 playwright 是否可用（通过 miniconda 或系统 Python）"""
    # 先找系统 playwright 命令
    playwright_cmd = shutil.which("playwright")
    if playwright_cmd:
        result = subprocess.run([playwright_cmd, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() if result.stdout else "unknown"
        return {"available": True, "path": playwright_cmd, "version": version}

    # 尝试通过 Python 检测
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
    """检查 Chromium 浏览器是否已安装"""
    import tempfile
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
    try:
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
    except Exception as e:
        return {"available": False, "detail": str(e)}
    return {"available": False, "detail": "无法找到可用的 Python 环境"}


def _find_python_with_playwright():
    """查找安装了 playwright 的 Python"""
    candidates = []
    # 已知的候选路径
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
    """执行环境检测"""
    print("=" * 55)
    print("  md2pdf — 环境检测")
    print("=" * 55)

    # pandoc
    pc = check_pandoc()
    if pc["available"]:
        print(f"  ✅ pandoc: {pc['version']}")
        print(f"    路径: {pc['path']}")
    else:
        print("  ❌ pandoc: 未找到")
        print("    安装: brew install pandoc")

    # playwright
    pw = check_playwright()
    if pw["available"]:
        print(f"  ✅ Playwright: {pw['version']}")
        print(f"    路径: {pw['path']}")
    else:
        print("  ❌ Playwright: 未找到")
        print("    安装: pip install playwright && playwright install chromium")

    # chromium
    if pw["available"]:
        cr = check_chromium()
        if cr["available"]:
            print("  ✅ Chromium: 就绪")
        else:
            print(f"  ❌ Chromium: {cr['detail']}")
    else:
        print("  ⚠️ Chromium: 跳过（Playwright 不可用）")

    # 结论
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
    """找一个可用的、安装了 playwright 的 Python"""
    for python_path in _find_python_with_playwright():
        result = subprocess.run(
            [python_path, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return python_path
    return None


def md_to_pdf(md_path, pdf_path, font_size=None, page_size=None):
    """
    Markdown → PDF 转换管线。

    管线: Markdown → (pandoc) → HTML → (Playwright) → PDF
    """

    # --- 输入验证 ---
    if not os.path.isfile(md_path):
        return {"ok": False, "error": f"输入文件不存在: {md_path}"}

    md_dir = os.path.dirname(os.path.abspath(md_path))
    md_name = os.path.basename(md_path)

    # --- Step 1: pandoc MD → HTML ---
    css = STYLE_CSS
    if font_size:
        css = css.replace("font-size: 14px;", f"font-size: {font_size}px;")

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        html_path = f.name

    pandoc_result = subprocess.run(
        ["pandoc", md_path,
         "-f", "commonmark_x",
         "-t", "html5",
         "--self-contained",
         "-o", html_path],
        capture_output=True, text=True, timeout=60,
    )

    if pandoc_result.returncode != 0:
        os.unlink(html_path)
        return {"ok": False, "error": f"pandoc 转换失败:\n{pandoc_result.stderr}"}

    # --- Step 2: 注入 CSS ---
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("</head>", f"<style>{css}</style></head>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # --- Step 3: Playwright HTML → PDF ---
    python_exec = find_python_executable()
    if not python_exec:
        os.unlink(html_path)
        return {"ok": False, "error": "未找到安装了 Playwright 的 Python 环境"}

    page_size_map = {
        "A4": "format='A4'",
        "A3": "format='A3'",
        "letter": "format='Letter'",
        "legal": "format='Legal'",
    }
    pdf_kwargs_str = page_size_map.get(page_size or "A4", "format='A4'")

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
    page.pdf(path=pdf_path, {pdf_kwargs_str}, margin={{"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}})
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
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown 转 PDF（pandoc + Playwright 引擎）",
    )
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 文件路径")
    parser.add_argument("--validate", action="store_true", help="仅检测环境，不执行转换")
    parser.add_argument("--font-size", type=int, default=None, help="正文字号（px），默认 14")
    parser.add_argument("--page-size", default="A4", choices=["A4", "A3", "letter", "legal"],
                        help="纸张大小，默认 A4")

    args = parser.parse_args()

    # --validate 模式
    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    # 参数校验
    if not args.input:
        parser.error("请指定 --input")
    if not args.output:
        # 自动推断输出路径：同目录下同名 .pdf
        base = os.path.splitext(args.input)[0]
        args.output = base + ".pdf"

    # 执行转换
    result = md_to_pdf(
        md_path=args.input,
        pdf_path=args.output,
        font_size=args.font_size,
        page_size=args.page_size,
    )

    if result["ok"]:
        size_kb = result["size"] / 1024
        print(f"✅ 转换完成: {result['output']} ({size_kb:.0f} KB)")
        sys.exit(0)
    else:
        print(f"❌ 转换失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
