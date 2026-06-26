#!/usr/bin/env python3
"""
md2pdf — Markdown → PDF 转换引擎

将 Markdown 文件渲染为排版精美的 PDF。
使用 pandoc（Markdown → HTML）+ Playwright（HTML → PDF）管线。

支持：
  - 封面页（从 YAML front-matter 自动生成）
  - 可交互目录（pandoc --toc + PDF 侧边栏书签）
  - 页码
  - 多主题
  - KaTeX 数学公式（pandoc --katex 原生支持）
  - Mermaid 图表（注入 mermaid.js 渲染）

Usage:
  md2pdf.py --input doc.md                           # 基本转换
  md2pdf.py --input doc.md --output doc.pdf           # 指定输出
  md2pdf.py --input doc.md --font-size 16             # 自定义字号
  md2pdf.py --input doc.md --page-size A3             # 自定义纸张
  md2pdf.py --input doc.md --theme academic           # 切换主题
  md2pdf.py --input doc.md --no-cover --no-toc        # 无封面/目录
  md2pdf.py --input doc.md --toc-depth 2              # 目录深度
  md2pdf.py --input doc.md --katex                    # 启用 KaTeX 数学公式
  md2pdf.py --input doc.md --mermaid                  # 启用 Mermaid 图表
  md2pdf.py --validate                                 # 环境检测
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


# ============================================================
# 路径
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
THEMES_DIR = os.path.join(PROJECT_DIR, "themes")


# ============================================================
# Front-matter 解析（纯正则，无外部依赖）
# ============================================================

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


# ============================================================
# 主题管理
# ============================================================

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


def load_theme_css(theme_name, font_size=None, font_family=None):
    """加载主题 CSS，可选覆盖字号和字体"""
    if theme_name not in AVAILABLE_THEMES:
        print(f"⚠️  主题 '{theme_name}' 不存在，使用 default")
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
        # 替换 body 的 font-family 声明
        css = re.sub(
            r'(body\s*\{[^}]*font-family:\s*)[^;"]*("?[^;"]*"?);',
            rf'\1{font_family};',
            css,
        )

    return css


def list_themes():
    """返回可用主题列表"""
    return sorted(AVAILABLE_THEMES.keys())


# ============================================================
# 封面页生成
# ============================================================

def build_cover_html(meta):
    """根据 front-matter 元数据生成封面页 HTML"""
    parts = ['<section data-page="cover" class="md2pdf-cover">']

    title = meta.get("title", "")
    if title:
        parts.append(f'<h1>{_escape_html(title)}</h1>')

    subtitle = meta.get("subtitle", "")
    if subtitle:
        parts.append(f'<p class="subtitle">{_escape_html(subtitle)}</p>')

    parts.append('<hr>')

    author = meta.get("author", "")
    if author:
        parts.append(f'<p class="meta">{_escape_html(author)}</p>')

    date = meta.get("date", "")
    if date:
        parts.append(f'<p class="meta">{_escape_html(date)}</p>')

    version = meta.get("version", "")
    if version:
        parts.append(f'<p class="version">v{_escape_html(version)}</p>')

    parts.append('</section>')
    return "\n".join(parts)


def _escape_html(text):
    """简单的 HTML 转义"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ============================================================
# 页码页脚 HTML
# ============================================================

def build_footer_html():
    """Playwright footerTemplate — 居中页码"""
    return """
    <div style="
        width: 100%;
        text-align: center;
        font-size: 9px;
        color: #8e8e93;
        font-family: -apple-system, 'PingFang SC', sans-serif;
        padding: 0 20mm;
    ">
        <span class="pageNumber"></span>
    </div>
    """


# ============================================================
# 环境检测
# ============================================================

def check_pandoc():
    path = shutil.which("pandoc")
    if path:
        result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.splitlines()[0] if result.stdout else "unknown"
        return {"available": True, "path": path, "version": version}
    return {"available": False, "path": None, "version": None}


def check_playwright():
    playwright_cmd = shutil.which("playwright")
    if playwright_cmd:
        result = subprocess.run([playwright_cmd, "--version"], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() if result.stdout else "unknown"
        return {"available": True, "path": playwright_cmd, "version": version}

    for python_candidate in [
        "/opt/homebrew/Caskroom/miniconda/base/bin/python3",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
    ]:
        if os.path.isfile(python_candidate):
            result = subprocess.run(
                [python_candidate, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return {"available": True, "path": python_candidate, "version": "via " + python_candidate}

    return {"available": False, "path": None, "version": None}


def check_system_chrome():
    """检查系统是否已安装 Chrome/Chromium/Edge"""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "google-chrome-stable", "google-chrome", "chromium", "chromium-browser",
        "microsoft-edge", "edge",
    ]
    for cmd in candidates:
        path = shutil.which(cmd) if "/" not in cmd else (cmd if os.path.isfile(cmd) else None)
        if path:
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                version = result.stdout.strip()[:60] if result.stdout else "unknown"
            except Exception:
                version = "unknown"
            return {"available": True, "path": path, "version": version}
    return {"available": False, "path": None, "version": None}


def check_chromium():
    probe_code = """
import sys
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        b.close()
    print('ok')
except Exception as e:
    print(f'FAIL: {e}', file=sys.stderr)
    sys.exit(1)
"""
    for python_candidate in _find_python_with_playwright():
        result = subprocess.run(
            [python_candidate, "-c", probe_code.strip()],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"available": True, "detail": "Playwright 内置 Chromium 就绪"}
        elif "executable doesn't exist" in result.stderr:
            return {"available": False, "detail": "未安装 Playwright Chromium",
                     "hint": "playwright install chromium"}
        else:
            return {"available": False, "detail": (result.stderr.strip() or result.stdout.strip())[:200]}
    return {"available": False, "detail": "无法找到安装了 Playwright 的 Python 环境"}


def _find_python_with_playwright():
    candidates = []
    for p in [
        "/opt/homebrew/Caskroom/miniconda/base/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    ]:
        if os.path.isfile(p):
            candidates.append(p)
    return candidates


def _is_chinese_env():
    """检测当前是否为中文语言环境"""
    lang = os.environ.get("LANG", "")
    return lang.startswith("zh") or "chinese" in lang.lower()


def _install_hint(component):
    """根据语言环境返回安装提示（含镜像建议）"""
    cn = _is_chinese_env()
    hints = {
        "pandoc": {
            "en": "  brew install pandoc",
            "zh": "  brew install pandoc",
        },
        "playwright": {
            "en": "  pip install playwright && playwright install chromium",
            "zh": "  pip install playwright && playwright install chromium\n"
                  "  国内用户建议使用镜像:\n"
                  "  PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/playwright \\\n"
                  "  pip install playwright && playwright install chromium",
        },
        "chromium": {
            "en": "  playwright install chromium",
            "zh": "  playwright install chromium\n"
                  "  国内用户建议使用镜像:\n"
                  "  PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/playwright \\\n"
                  "  playwright install chromium",
        },
    }
    hint = hints.get(component, {}).get("zh" if cn else "en", "")
    if cn and component == "playwright":
        return hint
    return hint


def _detect_cjk_fonts():
    """检测系统可用的 CJK 字体"""
    cjk_keywords = [
        "PingFang", "Heiti", "Songti", "Kaiti", "STSong", "STHeiti",
        "Noto.*CJK", "Noto.*Sans.*CJK", "Noto.*Serif.*CJK",
        "Source Han", "思源", "WenQuanYi", "文泉驿",
        "Hiragino.*Sans", "Hiragino.*Mincho",
        "Microsoft YaHei", "SimHei", "SimSun", "FangSong", "KaiTi",
    ]
    found = set()
    try:
        result = subprocess.run(
            ["fc-list", ":lang=zh", "-f", "%{family}\n"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                for kw in cjk_keywords:
                    if re.search(kw, line, re.IGNORECASE):
                        found.add(line.split(",")[0].strip())
                        break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: 检查 macOS 字体目录
    mac_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    for p in mac_paths:
        if os.path.isfile(p):
            name = os.path.splitext(os.path.basename(p))[0].replace(" Light", "").replace(" Medium", "")
            found.add(name)

    return sorted(found)


# ============================================================
# Mermaid 离线缓存
# ============================================================

MERMAID_JS_PATH = os.path.join(PROJECT_DIR, "themes", "mermaid.min.js")
MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"


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


# ============================================================
# 环境检测
# ============================================================

def run_validate():
    is_cn = _is_chinese_env()
    lang_tag = "🇨🇳 中文" if is_cn else "🇬🇧 English"
    print("=" * 55)
    print("  md2pdf — 环境检测")
    print(f"  语言环境: {lang_tag}")
    print("=" * 55)

    # pandoc
    pc = check_pandoc()
    if pc["available"]:
        print(f"  ✅ pandoc: {pc['version']}")
        print(f"    路径: {pc['path']}")
    else:
        print("  ❌ pandoc: 未找到")
        print(f"    {_install_hint('pandoc')}")

    # 系统 Chrome（浏览器本体，非 Playwright）
    sc = check_system_chrome()
    if sc["available"]:
        print(f"  ✅ 系统浏览器: {sc['version']}")
        print(f"    路径: {sc['path']}")
    else:
        print("  ℹ️  系统浏览器: 未检测到 Chrome/Edge")
        print("     非必需，Playwright 内置 Chromium 也可工作")

    # Playwright
    pw = check_playwright()
    if pw["available"]:
        print(f"  ✅ Playwright: {pw['version']}")
        print(f"    路径: {pw['path']}")
    else:
        print("  ❌ Playwright: 未找到")
        print(f"    {_install_hint('playwright')}")

    # Chromium（Playwright 内置）
    cr = {"available": False}
    if pw["available"]:
        cr = check_chromium()
        if cr["available"]:
            print(f"  ✅ Chromium: {cr['detail']}")
        else:
            print(f"  ❌ Chromium: {cr['detail']}")
            hint = cr.get("hint")
            if hint:
                print(f"    {_install_hint('chromium')}")
    else:
        print("  ⚠️  Chromium: 跳过（Playwright 不可用）")

    # 主题
    themes = list_themes()
    if themes:
        print(f"\n  🎨 可用主题: {', '.join(themes)}")
    else:
        print("\n  ⚠️ 未找到主题文件")

    # Mermaid 缓存
    if os.path.isfile(MERMAID_JS_PATH):
        size_kb = os.path.getsize(MERMAID_JS_PATH) / 1024
        print(f"\n  📈 Mermaid: 已缓存 ({size_kb:.0f} KB)")
    else:
        print("\n  📈 Mermaid: 未缓存，首次使用 --mermaid 时自动下载")

    # CJK 字体检测
    cjk_fonts = _detect_cjk_fonts()
    if cjk_fonts:
        print(f"\n  🈶 检测到 {len(cjk_fonts)} 款 CJK 字体:")
        for name in cjk_fonts[:8]:
            print(f"     - {name}")
        print(f"     建议: --font-family \"{cjk_fonts[0]}\"")
    else:
        print("\n  ⚠️ 未检测到 CJK 中文字体")
        print("     建议: 安装中文字体包")
        if sys.platform == "darwin":
            print("     macOS 自带 PingFang SC，检查是否正常")
        else:
            print("     Ubuntu/Debian: sudo apt install fonts-noto-cjk")
            print("     CentOS/Fedora:  sudo dnf install google-noto-cjk-fonts")

    # 结论
    has_pw_chrome = pw["available"] and cr["available"]
    has_system_browser = sc["available"]
    all_ok = pc["available"] and (has_pw_chrome or has_system_browser)
    if all_ok:
        print("\n  🟢 环境就绪，可以转换。")
        if has_system_browser and not has_pw_chrome:
            print("  ⚡ 使用系统浏览器渲染（无需额外下载）")
    else:
        print("\n  🔴 环境不完整，请安装缺失组件。")
    return all_ok


# ============================================================
# 核心转换
# ============================================================

def find_python_executable():
    for python_path in _find_python_with_playwright():
        result = subprocess.run(
            [python_path, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return python_path
    return None


def md_to_pdf(md_path, pdf_path, font_size=None, page_size=None,
              theme="default", with_cover=True, with_toc=True, toc_depth=4,
              font_family=None, katex=False, mermaid=False):
    """
    Markdown → PDF 转换管线。

    管线: Markdown → 解析 front-matter → pandoc (--toc, --katex) →
          注入封面 HTML → 注入 CSS 主题 → 注入 Mermaid/KaTeX → Playwright PDF
    """

    # --- 输入验证 ---
    if not os.path.isfile(md_path):
        return {"ok": False, "error": f"输入文件不存在: {md_path}"}

    # --- 读取并解析 Markdown ---
    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    meta, body = parse_front_matter(raw_text)

    # --- 封面智能处理 ---
    # 如果用户要封面但没有 title，自动用文件名作为标题
    if with_cover and not meta.get("title"):
        basename = os.path.splitext(os.path.basename(md_path))[0]
        # 去掉常见的连字符美化文件名
        display_name = basename.replace("-", " ").replace("_", " ").strip()
        meta["title"] = display_name

    # --- Step 1: pandoc MD → HTML ---
    # 注意：front-matter 已剥离，pandoc 不会自动生成标题块
    pandoc_args = [
        "pandoc",
        "-f", "commonmark_x",
        "-t", "html5",
        "--self-contained",
    ]

    if with_toc:
        pandoc_args.extend(["--toc", f"--toc-depth={toc_depth}"])

    if katex:
        pandoc_args.append("--katex")

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        html_path = f.name

    pandoc_proc = subprocess.run(
        pandoc_args + ["-o", html_path],
        input=body,
        capture_output=True, text=True, timeout=180,
    )

    if pandoc_proc.returncode != 0:
        os.unlink(html_path)
        return {"ok": False, "error": f"pandoc 转换失败:\n{pandoc_proc.stderr}"}

    # --- Step 2: 注入封面 + Mermaid + KaTeX CSS ---
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    if with_cover:
        cover_html = build_cover_html(meta)
        if cover_html.strip():
            html = html.replace("<body>", f"<body>\n{cover_html}")

    # --- Step 3: 注入 CSS 主题 ---
    css = load_theme_css(theme, font_size, font_family)
    if css:
        html = html.replace("</head>", f"<style>{css}</style></head>")

    # --- Step 3.5: 注入 Mermaid.js（离线缓存，需在 CSS 之后） ---
    has_mermaid = False
    if mermaid:
        if re.search(r'```\s*mermaid', raw_text, re.IGNORECASE):
            if not _ensure_mermaid():
                print("  ⚠️  无法下载 mermaid.js，跳过 Mermaid 渲染", file=sys.stderr)
            else:
                has_mermaid = True
                mermaid_injection = f"""
<script src="file://{MERMAID_JS_PATH}"></script>
<script>
  mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
</script>
<style>
  pre.mermaid, div.mermaid, svg[id^="mermaid-"] {{
    max-width: 100%;
    page-break-inside: avoid;
  }}
</style>
"""
                html = html.replace("</head>", f"{mermaid_injection}</head>")
                mermaid_transform_js = """
<script>
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('pre code').forEach(function(block) {
      var parent = block.parentElement;
      var classes = (parent.className + ' ' + block.className).toLowerCase();
      if (classes.indexOf('mermaid') === -1) return;
      parent.style.display = 'none';
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = block.textContent.trim();
      parent.parentNode.insertBefore(div, parent);
    });
    mermaid.init(undefined, document.querySelectorAll('.mermaid'));
  });
</script>
"""
                html = html.replace("</body>", f"{mermaid_transform_js}</body>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # --- Step 4: Playwright HTML → PDF ---
    python_exec = find_python_executable()
    if not python_exec:
        os.unlink(html_path)
        return {"ok": False, "error": "未找到安装了 Playwright 的 Python 环境"}

    # 纸张大小映射
    page_size_map = {
        "A4": "format='A4'",
        "A3": "format='A3'",
        "letter": "format='Letter'",
        "legal": "format='Legal'",
    }
    pdf_options = page_size_map.get(page_size or "A4", "format='A4'")

    footer_html = build_footer_html()

    # Mermaid 等待逻辑
    mermaid_wait = ""
    if has_mermaid:
        mermaid_wait = """
    page.evaluate('''() => {
        return new Promise(resolve => {
            if (typeof mermaid === 'undefined') { resolve(); return; }
            mermaid.init(undefined, document.querySelectorAll('.mermaid'));
            var check = setInterval(function() {
                var pending = document.querySelectorAll('.mermaid[data-processed="false"], .mermaid:not([data-processed])');
                if (pending.length === 0) { clearInterval(check); resolve(); }
            }, 200);
            setTimeout(function() { clearInterval(check); resolve(); }, 10000);
        });
    }''')
    page.wait_for_timeout(500)
"""

    code = f"""
import sys
from playwright.sync_api import sync_playwright
html_path = {repr(html_path)}
pdf_path = {repr(pdf_path)}
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('file://' + html_path)
    page.wait_for_load_state('networkidle'){mermaid_wait}
    page.pdf(
        path=pdf_path,
        {pdf_options},
        outline=True,
        display_header_footer=True,
        header_template='<span></span>',
        footer_template={repr(footer_html)},
        margin={{"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}},
    )
    browser.close()
print('OK')
"""

    pw_result = subprocess.run(
        [python_exec, "-c", code],
        capture_output=True, text=True, timeout=120,
    )

    os.unlink(html_path)

    if pw_result.returncode != 0:
        return {"ok": False, "error": f"Playwright PDF 生成失败:\n{pw_result.stderr}"}

    if not os.path.isfile(pdf_path):
        return {"ok": False, "error": "PDF 文件未生成（未知错误）"}

    pdf_size = os.path.getsize(pdf_path)
    return {"ok": True, "output": pdf_path, "size": pdf_size}


# ============================================================
# PDF 页面诊断
# ============================================================

def diagnose_pdf(pdf_path, with_cover=True, with_toc=True):
    """分析 PDF 页数，检测异常空白页"""
    if not os.path.isfile(pdf_path):
        print(f"  ❌ PDF 文件不存在: {pdf_path}", file=sys.stderr)
        return

    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ 无法读取 PDF: {e}", file=sys.stderr)
        return

    # 精确统计页数：正则 /\bType\s*/\s*Page\b 匹配页面对象，
    # 不会误匹配 /Type /Pages（页面树节点）
    page_count = len(re.findall(rb'/Type\s*/\s*Page\b', content))

    print("=" * 55)
    print("  📄 PDF 页面诊断")
    print("=" * 55)
    print(f"  文件: {pdf_path}")
    print(f"  大小: {os.path.getsize(pdf_path) / 1024:.0f} KB")
    print(f"  总页数: {page_count}")

    # 根据实际参数生成预期结构
    expected_notes = []
    page_idx = 0
    if with_cover:
        page_idx += 1
        expected_notes.append(f"P{page_idx} 封面")
    if with_toc:
        page_idx += 1
        expected_notes.append(f"P{page_idx} 目录")
    if page_count > page_idx:
        expected_notes.append(f"P{page_idx + 1}~P{page_count} 正文")

    if expected_notes:
        print(f"  预期: {' → '.join(expected_notes)}")

    # 检查页数合理性
    min_pages = (1 if with_cover else 0) + (1 if with_toc else 0)
    has_content = page_count > min_pages
    if page_count <= 1 and with_cover:
        print(f"\n  ⚠️  警告: 只有 {page_count} 页，请检查内容是否为空")
    elif page_count <= min_pages and min_pages > 0 and not has_content:
        print(f"\n  ℹ️  仅封面/目录页，正文内容较短")
    else:
        print(f"\n  ✅ 页面结构合理")


# ============================================================
# CLI 入口
# ============================================================

def main():
    themes_list = list_themes() or ["default"]

    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown 转 PDF（pandoc + Playwright 引擎）",
    )
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 文件路径")
    parser.add_argument("--validate", action="store_true", help="仅检测环境，不执行转换")
    parser.add_argument("--font-size", type=int, default=None, help="正文字号（px），默认 14")
    parser.add_argument("--page-size", default="A4", choices=["A4", "A3", "letter", "legal"],
                        help="纸张大小，默认 A4")
    parser.add_argument("--theme", default="default", choices=themes_list,
                        help=f"主题，默认 default。可用: {', '.join(themes_list)}")
    parser.add_argument("--cover", action="store_true", default=True,
                        help="生成封面页（从 front-matter 自动生成，默认开启）")
    parser.add_argument("--no-cover", action="store_false", dest="cover",
                        help="不生成封面页")
    parser.add_argument("--toc", action="store_true", default=True,
                        help="生成目录（默认开启）")
    parser.add_argument("--no-toc", action="store_false", dest="toc",
                        help="不生成目录")
    parser.add_argument("--toc-depth", type=int, default=4, choices=range(1, 7),
                        help="目录深度（标题层级 1-6），默认 4")
    parser.add_argument("--font-family", default=None,
                        help="正文字体，覆盖主题默认字体。如 PingFang SC, Noto Serif CJK SC")
    parser.add_argument("--katex", action="store_true", default=False,
                        help="启用 KaTeX 数学公式渲染（pandoc --katex）")
    parser.add_argument("--mermaid", action="store_true", default=False,
                        help="启用 Mermaid 图表渲染（注入 mermaid.js）")

    args = parser.parse_args()

    # --validate 模式
    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    # 参数校验
    if not args.input:
        parser.error("请指定 --input")
    if not args.output:
        input_abs = os.path.abspath(args.input)
        # 如果输入文件在本技能目录内，输出到 output/ 目录
        if input_abs.startswith(PROJECT_DIR):
            os.makedirs(os.path.join(PROJECT_DIR, "output"), exist_ok=True)
            base = os.path.splitext(os.path.basename(args.input))[0]
            args.output = os.path.join(PROJECT_DIR, "output", base + ".pdf")
        else:
            base = os.path.splitext(args.input)[0]
            args.output = base + ".pdf"

    # 执行转换
    result = md_to_pdf(
        md_path=args.input,
        pdf_path=args.output,
        font_size=args.font_size,
        page_size=args.page_size,
        theme=args.theme,
        with_cover=args.cover,
        with_toc=args.toc,
        toc_depth=args.toc_depth,
        font_family=args.font_family,
        katex=args.katex,
        mermaid=args.mermaid,
    )

    if result["ok"]:
        size_kb = result["size"] / 1024
        print(f"✅ 转换完成: {result['output']} ({size_kb:.0f} KB)")
        # 自动做页面诊断，检测空页等异常
        diagnose_pdf(result["output"], with_cover=args.cover, with_toc=args.toc)
        sys.exit(0)
    else:
        print(f"❌ 转换失败: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
