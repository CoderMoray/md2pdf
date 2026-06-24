# md2pdf — Markdown 转 PDF

> 将 Markdown 文档渲染为排版精美的 PDF 文件。  
> 管线：pandoc（MD→HTML）+ Playwright（HTML→PDF），输出效果与浏览器预览一致。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 快速开始

```bash
# 环境检测
python3 scripts/md2pdf.py --validate

# 基本转换
python3 scripts/md2pdf.py --input doc.md --output doc.pdf

# 自定义字号和纸张
python3 scripts/md2pdf.py --input doc.md --output doc.pdf --font-size 16 --page-size A3
```

## 环境要求

- **pandoc** — `brew install pandoc`
- **Playwright** — `pip install playwright && playwright install chromium`

## 功能

| 功能 | 支持 |
|------|------|
| 中文/英文/emoji | ✅ |
| 表格/代码块 | ✅ |
| 自定义字号 | ✅ (`--font-size`) |
| 纸张大小 | ✅ (`--page-size`: A4/A3/letter/legal) |
| 环境自检 | ✅ (`--validate`) |
| 离线运行 | ✅ |

## 许可

[MIT](LICENSE)
