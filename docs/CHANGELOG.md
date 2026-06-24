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
