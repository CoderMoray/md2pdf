"""路径常量和资产缓存 URL"""

import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
THEMES_DIR = os.path.join(PROJECT_DIR, "themes")

# Mermaid 离线缓存
MERMAID_JS_PATH = os.path.join(PROJECT_DIR, "themes", "mermaid.min.js")
MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"

# Highlight.js 离线缓存
HIGHLIGHT_JS_PATH = os.path.join(PROJECT_DIR, "themes", "highlight.min.js")
HIGHLIGHT_CSS_PATH = os.path.join(PROJECT_DIR, "themes", "highlight.css")
HIGHLIGHT_JS_URL = "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/highlight.min.js"
HIGHLIGHT_CSS_URL = "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/styles/github.min.css"
