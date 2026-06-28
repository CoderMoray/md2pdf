"""运行时资产缓存：Mermaid.js、highlight.js 自动下载"""

import os

from .config import (
    MERMAID_JS_PATH, MERMAID_CDN_URL,
    HIGHLIGHT_JS_PATH, HIGHLIGHT_CSS_PATH,
    HIGHLIGHT_JS_URL, HIGHLIGHT_CSS_URL,
)


def _ensure_mermaid():
    """确保本地有 mermaid.min.js，没有则自动下载"""
    if os.path.isfile(MERMAID_JS_PATH):
        return True
    try:
        import urllib.request
        urllib.request.urlretrieve(MERMAID_CDN_URL, MERMAID_JS_PATH)
        return True
    except Exception:
        return False


def _ensure_highlight():
    """确保本地有 highlight.js，没有则自动下载"""
    ok = True
    for path, url in [(HIGHLIGHT_JS_PATH, HIGHLIGHT_JS_URL), (HIGHLIGHT_CSS_PATH, HIGHLIGHT_CSS_URL)]:
        if os.path.isfile(path):
            continue
        try:
            import urllib.request
            urllib.request.urlretrieve(url, path)
        except Exception:
            ok = False
    return ok
