"""
md2pdf — Markdown → PDF 转换引擎

依赖关系：
  main.py → pipeline.py → themes.py, cover.py, assets.py, utils.py
  改 themes.py  → 影响 pipeline 输出的视觉样式
  改 assets.py  → 影响 mermaid/highlight 缓存逻辑
  改 utils.py   → 影响所有模块（被 pipeline, cover, diagnose 引用）
  改 diagnose.py → 仅影响 PDF 页面诊断输出

入口：上层的 scripts/md2pdf.py
"""
