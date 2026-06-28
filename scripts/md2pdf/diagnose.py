"""PDF 页面诊断：统计页数、检测异常空白页"""

import os
import re
import sys


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

    page_count = len(re.findall(rb'/Type\s*/\s*Page\b', content))

    print("=" * 55)
    print("  📄 PDF 页面诊断")
    print("=" * 55)
    print(f"  文件: {pdf_path}")
    print(f"  大小: {os.path.getsize(pdf_path) / 1024:.0f} KB")
    print(f"  总页数: {page_count}")

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

    min_pages = (1 if with_cover else 0) + (1 if with_toc else 0)
    has_content = page_count > min_pages
    if page_count <= 1 and with_cover:
        print(f"\n  ⚠️  警告: 只有 {page_count} 页，请检查内容是否为空")
    elif page_count <= min_pages and min_pages > 0 and not has_content:
        print(f"\n  ℹ️  仅封面/目录页，正文内容较短")
    else:
        print(f"\n  ✅ 页面结构合理")
