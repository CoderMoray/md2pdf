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

## [V1.1.0] - 2026-06-26

### Added
- **封面页** — 从 YAML front-matter（title/author/date/subtitle/version）自动生成封面
- **交互式目录** — pandoc `--toc` 生成可点击目录页 + Playwright `outline: true` 生成 PDF 侧边栏书签
- **页码** — Playwright `displayHeaderFooter` 居中页码
- **主题框架** — 支持多主题切换，内置 `default`、`academic` 两套主题
- **`themes/` 目录** — 主题 CSS 独立文件，方便扩展
- **CLI 参数扩展** — `--theme`、`--cover/--no-cover`、`--toc/--no-toc`、`--toc-depth`
- **PDF 互动性** — 阅读器侧边栏可点击书签树 + 页内超链接跳转
