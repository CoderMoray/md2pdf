# md2pdf

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
[![GitHub Release](https://img.shields.io/github/v/release/CoderMoray/md2pdf)](https://github.com/CoderMoray/md2pdf/releases)

一个 CodeBuddy Skill — 把 Markdown 转成排版精美的 PDF，自动生成封面、目录、书签、页码。你只需说一句话，剩下交给 AI。

## 目录

- [效果预览](#效果预览)
- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [封面配置](#封面配置)
- [AI 工作流](#ai-工作流)
- [安装与环境](#安装与环境)
- [CLI 参考](#cli-参考)
- [项目结构](#项目结构)
- [技术架构](#技术架构)
- [同类对比](#同类对比)
- [许可](#许可)

---

## 效果预览

- [📄 默认主题示例 PDF](output/README-default.pdf)
- [📄 学术主题示例 PDF](output/README-academic.pdf)

---

## 快速开始

### 安装

```bash
# 方式一：一键安装
npx skills add CoderMoray/md2pdf

# 方式二：手动 clone 到 skills 目录
cd .codebuddy/skills
git clone https://github.com/CoderMoray/md2pdf.git
```

### 使用

安装后在 CodeBuddy 中对 AI 说：

> "把这份 report.md 转成 PDF，用学术主题"

AI 会自动完成环境检测、转换、验证，你只需提供 Markdown 文件路径。

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 📄 封面页 | 从 YAML front-matter 自动生成标题、作者、日期、版本 |
| 📑 交互式目录 | 可点击目录页 + PDF 侧边栏书签（Outline） |
| 🔢 页码 | 每页底部居中 |
| 🎨 多主题 | `default` 苹果风格、`academic` 学术衬线 |
| 🌏 中英文混排 | 原生支持 CJK，无乱码 |
| 📊 表格/代码块 | 完整保留格式，语法高亮 |
| 🔧 环境自检 | 自动检测 pandoc + Playwright 是否就绪 |

---

## 封面配置

在 Markdown 文件头部添加 YAML 元数据，AI 自动读取并生成封面：

```yaml
---
title: "文档标题"
subtitle: "副标题"
author: "作者"
date: "2026-06-26"
version: "1.0"
---
```

所有字段可选。有 `title` 就有封面。

---

## AI 工作流

加载 md2pdf Skill 后，AI 自动执行：

1. **环境检测** → 确保 pandoc + Playwright 就绪
2. **询问偏好** → 主题、字号、纸张、是否要封面/目录
3. **执行转换** → 调用底层脚本
4. **验证输出** → 页面诊断，检查空白页等异常
5. **交付结果** → 告知 PDF 位置

---

## 安装与环境

### 依赖

| 组件 | 用途 | 大小 |
|------|------|------|
| pandoc | Markdown → HTML | ~30 MB |
| Playwright + Chromium | HTML → PDF | ~180 MB |

```bash
brew install pandoc
pip install playwright && playwright install chromium
```

---

## CLI 参考

如果不使用 AI Agent，也可以直接命令行调用：

```bash
python3 scripts/md2pdf.py --input doc.md --theme academic
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | — | Markdown 文件路径（必填） |
| `--output` | 自动推断 | 输出 PDF 路径 |
| `--theme` | `default` | 主题：default / academic |
| `--cover` / `--no-cover` | 开启 | 是否生成封面 |
| `--toc` / `--no-toc` | 开启 | 是否生成目录 |
| `--toc-depth` | `4` | 目录深度（1-6） |
| `--font-size` | `14` | 字号（px） |
| `--page-size` | `A4` | A4 / A3 / letter / legal |
| `--validate` | — | 仅检测环境 |

---

## 项目结构

```
md2pdf/
├── SKILL.md              # CodeBuddy Skill 描述
├── scripts/md2pdf.py     # 转换引擎
├── themes/
│   ├── default.css       # 默认主题
│   └── academic.css      # 学术主题
├── output/               # 生成的 PDF
├── docs/CHANGELOG.md
└── README.md
```

---

## 技术架构

```
Markdown → pandoc (--toc) → HTML → Playwright/Chromium → PDF
                                   ↑
                            封面 + CSS 主题
```

- **pandoc** 解析 Markdown，不依赖 AI
- **Playwright** 用真实浏览器渲染，输出与预览一致
- 全部逻辑内嵌脚本，结果可复现

### PDF 交互

| 特性 | 实现 |
|------|------|
| 侧边栏书签 | Playwright `outline: true` |
| 页内跳转 | pandoc `--toc` 超链接 |
| 页码 | Playwright 页脚模板 |

---

## 同类对比

| 特性 | md2pdf | any2pdf |
|------|:---:|:---:|
| 安装体积 | ~210 MB | ~10 MB |
| 中文支持 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 代码高亮 | ⭐⭐⭐ | ⭐⭐ |
| 封面/目录/书签 | ✅ | ✅ |
| 多主题 | 2 | 12 |
| 环境自检 | ✅ | ❌ |
| 页面诊断 | ✅ | ❌ |

---

## 许可

[MIT](LICENSE) © 2026 CoderMoray
