"""主题管理：扫描、加载、列表"""

import os
import re

from .config import THEMES_DIR

AVAILABLE_THEMES = {}


def _scan_themes():
    """扫描 themes/ 目录获取可用主题列表"""
    global AVAILABLE_THEMES
    if not os.path.isdir(THEMES_DIR):
        AVAILABLE_THEMES = {}
        return
    for f in os.listdir(THEMES_DIR):
        if f.endswith(".css"):
            name = f[:-4]
            AVAILABLE_THEMES[name] = os.path.join(THEMES_DIR, f)


_scan_themes()


def load_theme_css(theme_name, font_size=None, font_family=None, chinese_layout=False):
    """加载主题 CSS，可选覆盖字号、字体、中文排版层"""
    if theme_name not in AVAILABLE_THEMES:
        theme_name = "default"

    path = AVAILABLE_THEMES.get(theme_name)
    if not path:
        return ""

    with open(path, "r", encoding="utf-8") as f:
        css = f.read()

    if font_size:
        css = re.sub(r'font-size:\s*14px;', f'font-size: {font_size}px;', css)
        css = re.sub(r'font-size:\s*14pt;', f'font-size: {font_size}pt;', css)
        css = re.sub(r'font-size:\s*12pt;', f'font-size: {font_size}pt;', css)

    if font_family:
        css = re.sub(
            r'(body\s*\{[^}]*font-family:\s*)[^;"]*("?[^;"]*"?);',
            rf'\1{font_family};',
            css,
        )

    if chinese_layout:
        chinese_css_path = os.path.join(THEMES_DIR, "chinese.css")
        if os.path.isfile(chinese_css_path):
            with open(chinese_css_path, "r", encoding="utf-8") as f:
                css += "\n/* === 中文排版层 === */\n" + f.read()

    return css


def list_themes():
    """返回可用主题列表"""
    return sorted(AVAILABLE_THEMES.keys())
