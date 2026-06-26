<p align="center">
  <h1 align="center">md2pdf</h1>
  <p align="center">说句话，Markdown 变精美 PDF</p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/CodeBuddy-Skill-7B68EE.svg" alt="CodeBuddy Skill">
    <a href="https://github.com/CoderMoray/md2pdf/releases"><img src="https://img.shields.io/github/v/release/CoderMoray/md2pdf" alt="GitHub Release"></a>
  </p>
</p>

**md2pdf 是一个 CodeBuddy Skill**。安装后，你只需对 AI 说一句话，它就会把你的 Markdown 文件转成排版精美的 PDF——自动加上封面、目录、书签、页码。

管线：**pandoc**（MD→HTML）→ **Playwright**（HTML→PDF），输出与浏览器预览一致。

---

## 效果预览

[📄 默认主题示例 PDF](output/README-default.pdf) | [📄 学术主题示例 PDF](output/README-academic.pdf)

---

## 快速开始

### 1. 安装 Skill

```bash
# 方式一：一键安装
npx skills add CoderMoray/md2pdf

# 方式二：GitHub 仓库直接引用
cd .codebuddy/skills
git clone https://github.com/CoderMoray/md2pdf.git
```

### 2. 对 AI 说一句话

安装后，在 CodeBuddy 里直接对 AI 说：

> "把这份 report.md 转成 PDF，用学术主题"

AI 会自动执行完整的转换流程。你不需要知道参数、脚本在哪里、Python 怎么跑。

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 📄 **封面页** | 从 YAML front-matter 自动生成（标题/作者/日期/版本） |
| 📑 **交互式目录** | 可点击目录页 + PDF 侧边栏书签 |
| 🔢 **页码** | 每页底部居中 |
| 🎨 **多主题** | `default`（苹果风格） / `academic`（学术衬线） |
| 🌏 **中英文混排** | 原生支持 CJK，无乱码 |
| 📊 **表格/代码块** | 完整保留格式，代码高亮 |
| 🔧 **环境自检** | 自动检测依赖完整性 |
| 🧠 **AI 驱动** | 安装后一句话完成转换 |

### 即将支持

| 特性 | 状态 |
|------|------|
| KaTeX 数学公式 | 🚧 规划中 |
| Mermaid 图表 | 🚧 规划中 |
| 更多主题 | 📋 待定 |

---

## 封面配置

在 Markdown 文件头部添加 YAML front-matter，AI 会自动读取并生成封面：

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

## AI Agent 工作流

当 AI 加载 md2pdf Skill 后，会自动执行：

1. **环境检测** → 运行 `--validate`，确保 pandoc + Playwright 就绪
2. **询问偏好** → 主题、字号、纸张、是否需要封面/目录
3. **执行转换** → 调用脚本生成 PDF
4. **验证输出** → 运行页面诊断，确认无空白页异常
5. **交付结果** → 告知用户 PDF 位置

用户只需提供 MD 文件路径，其余全部自动完成。

---

## 安装与环境

### 依赖

| 组件 | 说明 |
|------|------|
| pandoc | Markdown → HTML 转换器（约 30MB） |
| Playwright + Chromium | HTML → PDF 渲染引擎（约 180MB） |

安装命令：

```bash
brew install pandoc
pip install playwright && playwright install chromium
```

### 项目结构

```
md2pdf/
├── SKILL.md              # 核心：CodeBuddy 读取的 Skill 描述
├── scripts/md2pdf.py     # 转换引擎
├── themes/
│   ├── default.css       # 默认主题
│   └── academic.css      # 学术主题
├── output/               # 生成的 PDF
├── docs/CHANGELOG.md
└── README.md
```

---

## CLI 参考（底层）

如果不使用 AI Agent，也可以直接命令行调用：

```bash
python3 scripts/md2pdf.py --input doc.md --theme academic
```

完整参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | — | Markdown 文件路径（必填） |
| `--output` | 自动推断 | 输出 PDF 路径 |
| `--theme` | `default` | `default` / `academic` |
| `--cover` / `--no-cover` | 开启 | 是否生成封面 |
| `--toc` / `--no-toc` | 开启 | 是否生成目录 |
| `--toc-depth` | `4` | 目录深度（1-6） |
| `--font-size` | `14` | 字号（px） |
| `--page-size` | `A4` | A4 / A3 / letter / legal |
| `--validate` | — | 环境检测模式 |

---

## 技术架构

```
Markdown → 解析 front-matter → pandoc (--toc) → HTML
                                                    ↓
                                         注入封面 + CSS 主题
                                                    ↓
                                              Playwright (Chromium)
                                                    ↓
                                              PDF (封面/目录/书签/页码)
```

- **pandoc** 解析 Markdown，不依赖 AI 理解
- **Playwright** 用真实 Chromium 渲染，输出与预览一致
- 全部逻辑内嵌脚本，结果可复现

### PDF 交互特性

| 特性 | 实现 |
|------|------|
| 📌 侧边栏书签 | Playwright `outline: true`，阅读器书签树 |
| 📑 页内跳转 | pandoc `--toc` 超链接 |
| 🔢 页码 | Playwright 页脚模板 |

---

## 同类 Skill 对比

| 特性 | md2pdf | any2pdf (reportlab) |
|------|:---:|:---:|
| 安装体积 | ~210MB | ~10MB |
| 中文支持 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 代码高亮 | ⭐⭐⭐（真实浏览器） | ⭐⭐ |
| 封面/目录/书签 | ✅ | ✅ |
| 多主题 | ✅ (2) | ✅ (12) |
| 环境自检 | ✅ | ❌ |
| AI Agent 集成 | ✅ CodeBuddy | ✅ npx & MCP |
| 页面诊断 | ✅ | ❌ |

---

## 许可

[MIT](LICENSE) &copy; 2026 CoderMoray
