#!/usr/bin/env bash
# build-skillhub.sh — md2pdf SkillHub 发布包构建
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 读取版本号
VERSION=$(python3 -c "import json; print(json.load(open('$ROOT/_meta.json'))['version'])" 2>/dev/null || echo "")
if [[ -z "$VERSION" ]]; then
  echo "❌ 无法从 _meta.json 读取版本号"
  exit 1
fi

echo "📦 构建 SkillHub 发布包 (v$VERSION)..."

TMPDIR=$(mktemp -d)
ZIP_NAME="md2pdf-${VERSION}-skillhub.zip"
ZIP_PATH="$ROOT/releases/$ZIP_NAME"

# 确保 releases/ 目录存在
mkdir -p "$ROOT/releases"

# 复制 SkillHub 清单文件
echo "  复制文件..."
cp "$ROOT/SKILL.md" "$TMPDIR/"
cp "$ROOT/scripts/md2pdf.py" "$TMPDIR/"
cp "$ROOT/README.md" "$TMPDIR/"
[[ -f "$ROOT/docs/CHANGELOG.md" ]] && cp "$ROOT/docs/CHANGELOG.md" "$TMPDIR/CHANGELOG.md"

# 打包
cd "$TMPDIR"
zip -qr "$ZIP_PATH" ./*

# 验证 zip 不包含开发者文件
echo "  验证 zip 内容..."
zipinfo -1 "$ZIP_PATH" | grep -qE '^tests/|^docs/|^reports/|^scripts/' && {
  echo "  ❌ zip 包含开发者文件!"
  exit 1
} || true

rm -rf "$TMPDIR"

echo "✅ 生成: releases/$ZIP_NAME ($(du -h "$ZIP_PATH" | cut -f1))"
