#!/usr/bin/env python3
"""md2pdf — Markdown → PDF 转换引擎 (CLI 入口)"""

import argparse
import json
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


def _load_config():
    """加载 config.json 获取默认页眉/水印/加密配置"""
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _resolve(value_cli, enabled_cli, cfg, key):
    """解析一个配置项：CLI值 > CLI开关 > config默认 > 关闭"""
    # 显式传了值 → 启用
    if value_cli is not None:
        return True, value_cli
    # CLI 显式禁用
    if enabled_cli is False:
        return False, ""
    # 用 config 默认
    cfg_sec = cfg.get(key, {}) if cfg else {}
    return cfg_sec.get("enabled", False), cfg_sec.get("text", "")


def main():
    themes_list = [t for t in (list_themes() or ["default"]) if t != "chinese"]
    cfg = _load_config()

    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown 转 PDF（pandoc + Playwright 引擎）",
    )
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 文件路径")
    parser.add_argument("--validate", action="store_true", help="仅检测环境")
    parser.add_argument("--font-size", type=int, default=None, help="正文字号（px）")
    parser.add_argument("--page-size", default="A4", choices=["A4", "A3", "letter", "legal"])
    parser.add_argument("--theme", default="default", choices=themes_list, help=f"可用: {', '.join(themes_list)}")
    parser.add_argument("--cover", action="store_true", default=True)
    parser.add_argument("--no-cover", action="store_false", dest="cover")
    parser.add_argument("--toc", action="store_true", default=True)
    parser.add_argument("--no-toc", action="store_false", dest="toc")
    parser.add_argument("--toc-depth", type=int, default=4, choices=range(1, 7))
    parser.add_argument("--font-family", default=None)
    parser.add_argument("--katex", action="store_true", default=False)
    parser.add_argument("--mermaid", action="store_true", default=False)
    parser.add_argument("--chinese-layout", action="store_true", default=False)
    parser.add_argument("--highlight", action="store_true", default=True)
    parser.add_argument("--no-highlight", action="store_false", dest="highlight")
    parser.add_argument("--list-themes", action="store_true", default=False)

    # 页眉
    parser.add_argument("--header", type=str, default=None, metavar="TEXT",
                        help="自定义页眉文字（同时启用页眉）")
    parser.add_argument("--no-header", action="store_false", dest="header_enabled",
                        help="禁用页眉")
    parser.set_defaults(header_enabled=None)
    # 水印
    parser.add_argument("--watermark", type=str, default=None, metavar="TEXT",
                        help="水印文字（同时启用水印）")
    parser.add_argument("--no-watermark", action="store_false", dest="watermark_enabled",
                        help="禁用水印")
    parser.set_defaults(watermark_enabled=None)
    # 加密
    parser.add_argument("--password", type=str, default=None, metavar="PWD",
                        help="设置 PDF 打开密码")

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

    # 解析页眉/水印/加密
    header_on, header_text = _resolve(args.header, args.header_enabled, cfg, "header")
    watermark_on, watermark_text = _resolve(args.watermark, args.watermark_enabled, cfg, "watermark")

    result = md_to_pdf(
        md_path=args.input, pdf_path=args.output,
        font_size=args.font_size, page_size=args.page_size,
        theme=args.theme, with_cover=args.cover, with_toc=args.toc,
        toc_depth=args.toc_depth, font_family=args.font_family,
        katex=args.katex, mermaid=args.mermaid,
        chinese_layout=args.chinese_layout, highlight=args.highlight,
        header_text=header_text if header_on else "",
        watermark_text=watermark_text if watermark_on else "",
        password=args.password or "",
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
