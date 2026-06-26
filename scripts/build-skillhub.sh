#!/usr/bin/env bash
# build-skillhub.sh — md2pdf SkillHub 发布包构建
# 用法: bash scripts/build-skillhub.sh [--slug <slug>]
#   --slug: 覆盖 zip 内 SKILL.md 的 slug（用于 SkillHub slug 冲突时）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 解析参数
SKILLHUB_SLUG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SKILLHUB_SLUG="$2"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# 读取版本号
VERSION=$(python3 -c "import json; print(json.load(open('$ROOT/_meta.json'))['version'])" 2>/dev/null || echo "")
if [[ -z "$VERSION" ]]; then
  echo "❌ 无法从 _meta.json 读取版本号"
  exit 1
fi

echo "📦 构建 SkillHub 发布包 (v$VERSION)..."

TMPDIR=$(mktemp -d)
SLUG_NAME="${SKILLHUB_SLUG:-md2pdf}"
ZIP_NAME="${SLUG_NAME}-${VERSION}-skillhub.zip"
ZIP_PATH="$ROOT/releases/$ZIP_NAME"

# 确保 releases/ 目录存在
mkdir -p "$ROOT/releases"

# 复制文件到临时目录
echo "  复制文件..."
cp "$ROOT/SKILL.md" "$TMPDIR/"
cp "$ROOT/scripts/md2pdf.py" "$TMPDIR/"
cp -r "$ROOT/themes" "$TMPDIR/themes"
cp "$ROOT/README.md" "$TMPDIR/"
[[ -f "$ROOT/docs/CHANGELOG.md" ]] && cp "$ROOT/docs/CHANGELOG.md" "$TMPDIR/CHANGELOG.md"

# 如需覆盖 slug，修改临时 SKILL.md 中的 slug 字段
if [[ -n "$SKILLHUB_SLUG" ]]; then
  echo "  覆盖 slug: md2pdf → $SKILLHUB_SLUG"
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s/^slug:.*/slug: $SKILLHUB_SLUG/" "$TMPDIR/SKILL.md"
  else
    sed -i "s/^slug:.*/slug: $SKILLHUB_SLUG/" "$TMPDIR/SKILL.md"
  fi
fi

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
