#!/usr/bin/env python3
"""md2pdf — Markdown → PDF 转换引擎 (CLI 入口)"""

import argparse
import os
import sys

from md2pdf.pipeline import md_to_pdf
from md2pdf.diagnose import diagnose_pdf
from md2pdf.themes import list_themes
from md2pdf.config import (
    PROJECT_DIR, MERMAID_JS_PATH,
    HIGHLIGHT_JS_PATH, HIGHLIGHT_CSS_PATH,
)
from validate import run_validate


def main():
    themes_list = [t for t in (list_themes() or ["default"]) if t != "chinese"]

    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown 转 PDF（pandoc + Playwright 引擎）",
    )
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 文件路径")
    parser.add_argument("--validate", action="store_true", help="仅检测环境，不执行转换")
    parser.add_argument("--font-size", type=int, default=None, help="正文字号（px），默认 14")
    parser.add_argument("--page-size", default="A4", choices=["A4", "A3", "letter", "legal"], help="纸张大小")
    parser.add_argument("--theme", default="default", choices=themes_list, help=f"主题。可用: {', '.join(themes_list)}")
    parser.add_argument("--cover", action="store_true", default=True, help="生成封面页（默认开启）")
    parser.add_argument("--no-cover", action="store_false", dest="cover", help="不生成封面")
    parser.add_argument("--toc", action="store_true", default=True, help="生成目录（默认开启）")
    parser.add_argument("--no-toc", action="store_false", dest="toc", help="不生成目录")
    parser.add_argument("--toc-depth", type=int, default=4, choices=range(1, 7), help="目录深度 1-6")
    parser.add_argument("--font-family", default=None, help="正文字体")
    parser.add_argument("--katex", action="store_true", default=False, help="启用 KaTeX 数学公式")
    parser.add_argument("--mermaid", action="store_true", default=False, help="启用 Mermaid 图表")
    parser.add_argument("--chinese-layout", action="store_true", default=False, help="中文排版增强")
    parser.add_argument("--highlight", action="store_true", default=True, help="代码语法高亮（默认开启）")
    parser.add_argument("--no-highlight", action="store_false", dest="highlight", help="关闭代码高亮")
    parser.add_argument("--list-themes", action="store_true", default=False, help="列出所有可用主题")

    args = parser.parse_args()

    if args.list_themes:
        for t in themes_list:
            print(t)
        sys.exit(0)

    if args.validate:
        ok = run_validate(themes_list, MERMAID_JS_PATH, HIGHLIGHT_JS_PATH, HIGHLIGHT_CSS_PATH)
        sys.exit(0 if ok else 1)

    if not args.input:
        parser.error("请指定 --input")

    if not args.output:
        input_abs = os.path.abspath(args.input)
        if input_abs.startswith(PROJECT_DIR):
            os.makedirs(os.path.join(PROJECT_DIR, "output"), exist_ok=True)
            base = os.path.splitext(os.path.basename(args.input))[0]
            args.output = os.path.join(PROJECT_DIR, "output", base + ".pdf")
        else:
            args.output = os.path.splitext(args.input)[0] + ".pdf"

    result = md_to_pdf(
        md_path=args.input, pdf_path=args.output,
        font_size=args.font_size, page_size=args.page_size,
        theme=args.theme, with_cover=args.cover, with_toc=args.toc,
        toc_depth=args.toc_depth, font_family=args.font_family,
        katex=args.katex, mermaid=args.mermaid,
        chinese_layout=args.chinese_layout, highlight=args.highlight,
    )

    if result["ok"]:
        print(f"✅ 转换完成: {result['output']} ({result['size'] / 1024:.0f} KB)")
        diagnose_pdf(result["output"], with_cover=args.cover, with_toc=args.toc)
        sys.exit(0)
    else:
        print(f"❌ 转换失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
