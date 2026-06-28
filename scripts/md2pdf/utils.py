"""工具函数：front-matter 解析、Python 环境查找、页脚 HTML"""

import subprocess
import re
import sys

from .config import PROJECT_DIR


def parse_front_matter(text):
    """从 Markdown 文本中解析 YAML front-matter，返回 (meta, body)。"""
    meta = {}
    body = text

    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if m:
        raw = m.group(1)
        body = text[m.end():]
        for line in raw.splitlines():
            line = line.strip()
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.+)$', line)
            if kv:
                key = kv.group(1)
                val = kv.group(2).strip().strip('"').strip("'")
                meta[key] = val

    return meta, body


def find_python_executable():
    """返回已安装 Playwright 的 Python 解释器路径"""
    for python_path in ["/usr/bin/python3", "/usr/local/bin/python3",
                        "/opt/homebrew/bin/python3",
                        "/opt/homebrew/Caskroom/miniconda/base/bin/python3"]:
        try:
            result = subprocess.run(
                [python_path, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return python_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def build_footer_html():
    """Playwright footerTemplate — 居中页码 Page X / Y"""
    return """
    <div style="
        width: 100%;
        text-align: center;
        font-size: 9px;
        color: #8e8e93;
        font-family: -apple-system, 'PingFang SC', sans-serif;
        padding: 0 20mm;
    ">
        <span class="pageNumber"></span> / <span class="totalPages"></span>
    </div>
    """


def _escape_html(text):
    """简单的 HTML 转义"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
