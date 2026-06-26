---
title: "md2pdf — Markdown 转 PDF"
subtitle: "Pandoc + Playwright 渲染引擎"
author: "CoderMoray"
date: "2026-06-26"
version: "1.1.0"
---

# md2pdf — Markdown 转 PDF

> 将 Markdown 文档渲染为排版精美的 PDF 文件。  
> 管线：pandoc（MD→HTML）+ Playwright（HTML→PDF），输出效果与浏览器预览一致。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 快速开始

```bash
# 环境检测
python3 scripts/md2pdf.py --validate

# 基本转换（自动生成封面 + 目录 + 页码）
python3 scripts/md2pdf.py --input doc.md

# 切换主题
python3 scripts/md2pdf.py --input doc.md --theme academic

# 自定义字号和纸张
python3 scripts/md2pdf.py --input doc.md --font-size 16 --page-size A3

# 简洁模式（无封面、无目录）
python3 scripts/md2pdf.py --input doc.md --no-cover --no-toc
```

## 功能

| 功能 | 支持 |
|------|------|
| 中文/英文/emoji/表格/代码块 | ✅ |
| 封面页（front-matter 自动生成） | ✅ |
| 交互式目录 + PDF 侧边栏书签 | ✅ |
| 居中页码 | ✅ |
| 多主题切换 | ✅ (default / academic) |
| 自定义字号 | ✅ (`--font-size`) |
| 纸张大小 | ✅ (`--page-size`: A4/A3/letter/legal) |
| 环境自检 | ✅ (`--validate`) |
| 离线运行 | ✅ |

## 封面配置

在 Markdown 文件头部添加 YAML 元数据即可自动生成封面：

```yaml
---
title: "文档标题"
subtitle: "副标题"
author: "作者"
date: "2026-06-26"
version: "1.0"
---
```

## 环境要求

- **pandoc** — `brew install pandoc`
- **Playwright** — `pip install playwright && playwright install chromium`

## 项目结构

```
md2pdf/
├── SKILL.md                # CodeBuddy Skill 描述
├── _meta.json              # 元数据
├── scripts/
│   └── md2pdf.py           # 核心转换引擎
├── themes/
│   ├── default.css         # 默认主题（苹果风格）
│   └── academic.css        # 学术主题（衬线字体）
├── docs/
│   └── CHANGELOG.md
├── README.md
└── LICENSE
```

## 许可

[MIT](LICENSE)
