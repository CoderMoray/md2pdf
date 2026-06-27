#!/usr/bin/env python3
"""
md2pdf — 环境检测模块

检测 pandoc、Playwright、Chromium、CJK 字体等依赖是否就绪。
md2pdf.py 通过 import 使用本模块，AI Agent 不需要直接读取此文件。
"""

import os
import re
import shutil
import subprocess
import sys


# ============================================================
# Python 路径发现
# ============================================================

def _find_python_with_playwright():
    """查找安装了 Playwright 的 Python 解释器"""
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


# ============================================================
# 语言环境
# ============================================================

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


# ============================================================
# 组件检测
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


# ============================================================
# CJK 字体检测
# ============================================================

def detect_cjk_fonts():
    """检测系统可用的 CJK 字体（公开接口）"""
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
# 入口：环境检测
# ============================================================

def run_validate(themes_list, mermaid_js_path):
    """
    执行完整环境检测并打印结果。
    
    参数:
        themes_list: 可用主题名列表（如 ['default', 'academic']）
        mermaid_js_path: Mermaid.js 本地缓存路径
    返回:
        bool: 环境是否就绪
    """
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

    # 系统 Chrome
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

    # Chromium
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
    if themes_list:
        print(f"\n  🎨 可用主题: {', '.join(themes_list)}")
        print(f"  📐 中文排版: --chinese-layout 叠加到任意主题")
    else:
        print("\n  ⚠️ 未找到主题文件")

    # Mermaid 缓存
    if os.path.isfile(mermaid_js_path):
        size_kb = os.path.getsize(mermaid_js_path) / 1024
        print(f"\n  📈 Mermaid: 已缓存 ({size_kb:.0f} KB)")
    else:
        print("\n  📈 Mermaid: 未缓存，首次使用 --mermaid 时自动下载")

    # CJK 字体
    cjk_fonts = detect_cjk_fonts()
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
