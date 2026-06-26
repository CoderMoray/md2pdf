<p align="center">
  <h1 align="center">md2pdf</h1>
  <p align="center">Markdown → 精美 PDF &middot; 一键生成封面/目录/书签/页码</p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/CodeBuddy-Skill-7B68EE.svg" alt="CodeBuddy Skill">
    <a href="https://github.com/CoderMoray/md2pdf/releases"><img src="https://img.shields.io/github/v/release/CoderMoray/md2pdf" alt="GitHub Release"></a>
  </p>
</p>

**md2pdf** 是一个 [CodeBuddy Skill](https://www.codebuddy.ai)，将 Markdown 文档渲染为排版精美的 PDF，支持中文、代码块、表格、emoji。

管线：**pandoc**（MD→HTML）→ **Playwright**（HTML→PDF），输出与浏览器预览完全一致。

---

## 效果预览

| Default 主题（苹果风格） | Academic 主题（学术风格） |
|:---:|:---:|
| [![default](output/README-default.pdf)](output/README-default.pdf) | [![academic](output/README-academic.pdf)](output/README-academic.pdf) |

> 点击链接下载示例 PDF，含封面、交互式目录、PDF 侧边栏书签、页码。

---

## 快速开始

```bash
# 1. 安装依赖
brew install pandoc
pip install playwright && playwright install chromium

# 2. 环境检测
python3 scripts/md2pdf.py --validate

# 3. 转换文档
python3 scripts/md2pdf.py --input README.md
```

> 转换后的 PDF 自动保存在 `output/` 目录，内容不受 git 跟踪。

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 📄 **封面页** | 从 YAML front-matter 自动生成（标题/作者/日期/版本） |
| 📑 **交互式目录** | 可点击目录页 + PDF 侧边栏书签（Outline） |
| 🔢 **页码** | 每页底部居中 |
| 🎨 **多主题** | `default`（苹果风格） / `academic`（学术衬线） |
| 🌏 **中英文混排** | 原生支持 CJK 字符，无乱码 |
| 📊 **表格/代码块** | 完整保留格式，代码高亮 |
| 🔧 **环境自检** | `--validate` 一键检测依赖完整性 |

### 正在规划

| 特性 | 状态 |
|------|------|
| KaTeX 数学公式 | 🚧 规划中 |
| Mermaid 图表 | 🚧 规划中 |
| 更多主题 | 📋 待定 |
| 一键安装脚本 | 📋 待定 |

---

## 使用方式

### 封面配置

在 Markdown 文件头部添加 YAML front-matter：

```yaml
---
title: "文档标题"
subtitle: "副标题"
author: "作者"
date: "2026-06-26"
version: "1.0"
---
```

所有字段均为可选，有 `title` 字段就自动生成封面页。

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input <path>` | — | 输入 Markdown 文件路径（必填） |
| `--output <path>` | 自动推断 | 输出 PDF 路径 |
| `--theme <name>` | `default` | 主题：`default` / `academic` |
| `--cover` / `--no-cover` | `--cover` | 是否生成封面页 |
| `--toc` / `--no-toc` | `--toc` | 是否生成目录 |
| `--toc-depth <n>` | `4` | 目录标题层级深度（1-6） |
| `--font-size <px>` | `14` | 正文字号 |
| `--page-size <format>` | `A4` | 纸张：`A4` / `A3` / `letter` / `legal` |
| `--validate` | — | 仅检测环境，不执行转换 |

### 示例

```bash
# 基础转换
python3 scripts/md2pdf.py --input doc.md

# 学术主题
python3 scripts/md2pdf.py --input doc.md --theme academic

# 无封面、无目录的简洁模式
python3 scripts/md2pdf.py --input doc.md --no-cover --no-toc

# 控制目录深度和字号
python3 scripts/md2pdf.py --input doc.md --toc-depth 2 --font-size 16

# 切换纸张
python3 scripts/md2pdf.py --input doc.md --page-size A3
```

---

## 安装

### 作为 CodeBuddy Skill 使用

```bash
# 从 GitHub 安装
codebuddy skills install CoderMoray/md2pdf
```

### 手动使用

```bash
git clone https://github.com/CoderMoray/md2pdf.git
cd md2pdf

# 依赖
brew install pandoc                      # macOS
pip install playwright
playwright install chromium

# 运行
python3 scripts/md2pdf.py --validate
```

---

## 项目结构

```
md2pdf/
├── SKILL.md              # CodeBuddy Skill 描述（AI Agent 读取）
├── _meta.json            # 元数据（版本/分类/标签）
├── scripts/
│   └── md2pdf.py         # 核心转换引擎（pandoc + Playwright）
├── themes/
│   ├── default.css       # 默认主题（苹果风格）
│   └── academic.css      # 学术主题（衬线字体）
├── output/               # 生成的 PDF（git ignored）
├── docs/
│   └── CHANGELOG.md
├── README.md
└── LICENSE
```

---

## 技术架构

```
Markdown ──→ 解析 front-matter ──→ pandoc (--toc) ──→ HTML
                                                        │
                                             注入封面 + CSS 主题
                                                        │
                                              Playwright (Chromium)
                                                        │
                                                   ┌────┴────┐
                                                   │   PDF   │
                                                   │ 封面/目录│
                                                   │ 书签/页码│
                                                   └─────────┘
```

- **pandoc** 负责 Markdown 解析，不依赖 AI 理解
- **Playwright** 使用真实 Chromium 渲染，输出与预览一致
- 全部逻辑内嵌在脚本中，结果可复现：同一份 MD 每次输出完全相同的 PDF

### PDF 交互特性

| 特性 | 实现方式 |
|------|---------|
| 📌 侧边栏书签 | Playwright `outline: true`，阅读器左侧可点击书签树 |
| 📑 页内目录跳转 | pandoc `--toc` 生成 `<a href="#id">` 超链接 |
| 🔢 页码 | Playwright `displayHeaderFooter` 页脚模板 |

---

## 同类项目对比

| 特性 | md2pdf | Pandoc+LaTeX | any2pdf (reportlab) | VS Code 插件 |
|------|:---:|:---:|:---:|:---:|
| 安装体积 | ~300MB | 1-5GB | ~10MB | ~150MB |
| 中文支持 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 代码高亮 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 封面/目录/书签 | ✅ | ✅ | ✅ | ❌ |
| 多主题 | ✅ (2) | ❌ | ✅ (12) | ❌ |
| 环境自检 | ✅ | ❌ | ❌ | ❌ |
| AI Agent 集成 | ✅ (CodeBuddy) | ❌ | ✅ (npx) | ❌ |

---

## 许可

[MIT](LICENSE) &copy; 2026 CoderMoray
