---
slug: md2pdf
displayName: "md2pdf / Markdown 转 PDF"
name: md2pdf
description: |
  将 Markdown 文档渲染为排版精美的 PDF 文件。
  管线：pandoc（MD→HTML）+ Playwright（HTML→PDF），
  输出效果与浏览器预览一致，支持 emoji/中文/表格/代码块。
author: HaluCatch Team
version: "1.0.0"
tags:
  - "文档处理"
  - "PDF生成"
  - "document-conversion"
  - "markdown"
  - "pdf"
category: "utility"
---

# md2pdf — Markdown 转 PDF

将 Markdown 文件转换为排版精美的 PDF，不依赖 AI 语义理解。

## 能力边界

| 擅长 | 不擅长 |
|------|--------|
| Markdown → PDF 转换 | 合并多个 MD 为单个 PDF |
| 中文/英文/emoji/表格/代码块 | 从零创建 PDF（请先写 MD） |
| 自定义字号和纸张大小 | 深度排版控制（如分栏、页眉页脚自定义） |
| 环境自检（--validate） | 加密/水印/签名 PDF |

---

## 输入

| 参数 | 是否必需 | 说明 |
|------|---------|------|
| `--input <path>` | ✅ | 输入 Markdown 文件路径 |
| `--output <path>` | ❌ | 输出 PDF 路径，不指定则自动生成（同目录同名.pdf） |
| `--font-size <px>` | ❌ | 正文字号，默认 14px |
| `--page-size <format>` | ❌ | 纸张大小，可选 A4/A3/letter/legal，默认 A4 |
| `--validate` | ❌ | 环境检测模式，不执行转换 |

---

## 工作流

### 第 1 步：确认需求

确认用户提供的 Markdown 文件路径，确认输出需求。

### 第 2 步：环境检测

首次使用或环境变更后，先运行环境检测：

```bash
python3 scripts/md2pdf.py --validate
```

输出示例：
```
=======================================================
  md2pdf — 环境检测
=======================================================
  ✅ pandoc: pandoc 2.12
    路径: /opt/homebrew/Caskroom/miniconda/base/bin/pandoc
  ✅ Playwright: Version 1.56.0
    路径: /opt/homebrew/Caskroom/miniconda/base/bin/playwright
  ✅ Chromium: 就绪

  🟢 环境就绪，可以转换。
```

**环境不完整时：**
- pandoc 缺失 → `brew install pandoc`
- Playwright 缺失 → `pip install playwright && playwright install chromium`

### 第 3 步：执行转换

```bash
# 基本用法（AI 拼装命令后执行）
python3 scripts/md2pdf.py --input /path/to/doc.md --output /path/to/doc.pdf

# 自定义字号
python3 scripts/md2pdf.py --input doc.md --output doc.pdf --font-size 16

# 自定义纸张
python3 scripts/md2pdf.py --input doc.md --output doc.pdf --page-size A3
```

### 第 4 步：验证输出

转换完成后确认：
- PDF 文件已生成
- 文件大小不为 0（一般 300KB+）
- 打开确认排版无误

---

## 架构

```
管线: Markdown → (pandoc) → HTML → (Playwright/Chromium) → PDF
         ↑                       ↑
    commonmark_x 解析      CSS 样式注入（内置）
```

**为什么这样设计：**
- pandoc 处理 Markdown 解析，不依赖 AI 理解
- Playwright 使用真实 Chromium 浏览器渲染，输出与预览一致
- 所有样式和逻辑内嵌在脚本中，无需 AI 判断
- 结果可复现：同一份 MD 每次输出完全相同的 PDF

---

## 输出

转换成功后输出：`✅ 转换完成: /path/to/output.pdf (629 KB)`

失败时输出错误信息到 stderr，退出码为 1。

---

## 常见问题

| 问题 | 解决 |
|------|------|
| pandoc 未安装 | `brew install pandoc` |
| playwright 未安装 | `pip install playwright && playwright install chromium` |
| 中文显示为方块 | 确认系统有中文字体（macOS 自带 PingFang） |
| emoji 不显示 | 确认使用 `--validate` 检测到的环境正常 |
| 输出文件未生成 | 检查输出路径是否有写入权限 |
