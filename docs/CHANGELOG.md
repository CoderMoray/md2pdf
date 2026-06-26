# Changelog

本文档记录 md2pdf 项目的所有 notable changes。

版本号规则：
- **中间版本号** (1.x.0)：新功能或架构级变更
- **小版本号** (1.0.x)：修复、增强、chore 等小更新

---

## [Unreleased]

### Added
- 项目初始化：Markdown → PDF 转换管线（pandoc + Playwright 引擎）
- 环境自检机制（`--validate`）
- 自定义字号（`--font-size`）和纸张大小（`--page-size`）
- 内置 CSS 样式排版

---

## [V1.2.0] - 2026-06-27

### Added
- **`--font-family` 参数** — 可自定义正文字体，覆盖主题默认字体
- **`chinese.css` 主题** — 专为中文排版优化（禁则处理、行间距、标点调整、首行缩进）
- **CJK 字体检测** — `--validate` 自动检测并列出系统中文字体，推荐最佳选择
- **Linux 字体安装指引** — CJK 字体缺失时自动提示安装命令

---

## [V1.1.0] - 2026-06-26

### Added
- **封面页** — 从 YAML front-matter（title/author/date/subtitle/version）自动生成封面
- **交互式目录** — pandoc `--toc` 生成可点击目录页 + Playwright `outline: true` 生成 PDF 侧边栏书签
- **页码** — Playwright `displayHeaderFooter` 居中页码
- **主题框架** — 支持多主题切换，内置 `default`、`academic` 两套主题
- **`themes/` 目录** — 主题 CSS 独立文件，方便扩展
- **CLI 参数扩展** — `--theme`、`--cover/--no-cover`、`--toc/--no-toc`、`--toc-depth`
- **PDF 互动性** — 阅读器侧边栏可点击书签树 + 页内超链接跳转
