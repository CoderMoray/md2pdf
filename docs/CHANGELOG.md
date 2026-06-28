# Changelog

本文档记录 md2pdf 项目的所有 notable changes。

版本号规则：
- **中间版本号** (1.x.0)：新功能或架构级变更
- **小版本号** (1.0.x)：修复、增强、chore 等小更新

---

## [Unreleased]

### Added
- （暂无）

---

## [V1.5.0] - 2026-06-28

### Added
- **代码语法高亮** — 注入 highlight.js（GitHub 主题），默认开启。支持 Python/JS/Bash/SQL/JSON/HTML 等 190+ 语言
- `--highlight` / `--no-highlight` 参数控制开关
- `--validate` 新增 highlight.js 缓存状态检测

### Changed
- **README 技术对比更新** — 新增 openclaw-md2pdf (Pandoc + Typst) 技能链接和对比；引擎描述改为 `pandoc + Chromium`；安装体积拆分本体/依赖

---

## [V1.4.3] - 2026-06-28

### Added
- **`docs/FAQ.md`** — 完整常见问题指南（转换/封面/目录/字体/Mermaid/KaTeX/错误解读），供 AI 和用户查阅
- **错误信息优化** — pandoc/Playwright 失败时附带常见原因分析，而非原始 stderr

### Changed
- **SKILL.md 常见问题** — 精简为 FAQ 索引，AI 遇到问题自动查阅 `docs/FAQ.md`

---

## [V1.4.2] - 2026-06-28

### Added
- **页码增强** — 页脚显示 `X / Y` 格式（当前页 / 总页数），替代原来的纯数字页码
- **`--list-themes` 参数** — 列出所有可用主题名称

### Changed
- **发布脚本优化** — `release.sh` 添加 `--name "md2pdf"` 修复 ClawHub 显示名
- 移除 `md2pdf.py` 中未使用的 import（`json`, `shutil`）

---

## [V1.4.1] - 2026-06-28

### Changed
- **代码拆分** — 环境检测代码提取到 `scripts/validate.py`（304行），`md2pdf.py` 降至 585 行，AI Agent 只需加载核心管线

---

## [V1.4.0] - 2026-06-27

### Changed
- **Chinese 改为排版层** — `chinese.css` 不再是独立主题，改为通过 `--chinese-layout` 叠加到任意主题上
- **智能分页** — H1 标题自动另起一页（当前页已有内容时），代码块/表格/图表保持完整不跨页
- **封面分页修复** — JS 动态设置封面高度消除空白页，目录不再强制独占一页

---

## [V1.3.2] - 2026-06-27

### Changed
- **分页优化** — 所有主题新增 `page-break-inside: avoid`（代码块/表格/引用/图表保持完整，不被截断到两页）
- **标题粘连保护** — `page-break-after: avoid` 防止标题孤行（标题在页尾、内容在下一页）
- **封面/目录独占** — `page-break-after: always` 确保封面和目录各自独占一页

---

## [V1.3.1] - 2026-06-27

### Added
- **Mermaid 离线渲染** — 首次使用时自动下载 mermaid.js 到 `themes/mermaid.min.js`，后续从本地加载，无需 CDN
- `--validate` 新增 Mermaid 缓存状态检测

### Fixed
- **封面智能回退** — 无 front-matter 时自动用文件名作为封面标题，不再生成空白封面页
- **页面诊断修正** — 页数统计改用正则精确匹配 `/Type /Page`，不再误计 `/Type /Pages`

---

## [V1.3.0] - 2026-06-27

### Added
- **KaTeX 数学公式支持** — `--katex` 参数，通过 pandoc `--katex` 原生渲染 LaTeX 数学公式
- **Mermaid 图表支持** — `--mermaid` 参数，注入 mermaid.js 渲染流程图、时序图、甘特图等
- Mermaid 自动检测：仅当 Markdown 包含 ` ```mermaid ` 代码块时才注入 mermaid.js
- Playwright 等待 Mermaid 渲染完成后才输出 PDF

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
