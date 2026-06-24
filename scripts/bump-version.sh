#!/usr/bin/env bash
# bump-version.sh — md2pdf 版本号升级
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "用法: $0 X.Y.Z"
  echo "  批量更新 SKILL.md、_meta.json 的版本号"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1) SKILL.md frontmatter version
if grep -q '^version:' "$ROOT/SKILL.md"; then
  sed -i '' "s/^version: \".*\"/version: \"$VERSION\"/" "$ROOT/SKILL.md"
  echo "✅ SKILL.md → $VERSION"
else
  echo "⚠️  SKILL.md 中未找到 version: 字段"
fi

# 2) _meta.json version
if [[ -f "$ROOT/_meta.json" ]]; then
  python3 -c "
import json
with open('$ROOT/_meta.json') as f:
    meta = json.load(f)
meta['version'] = '$VERSION'
with open('$ROOT/_meta.json', 'w') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)
" && echo "✅ _meta.json → $VERSION"
fi

# 3) 提醒手动更新
echo ""
echo "⚠️  请手动更新以下文件的版本号:"
echo "   - docs/CHANGELOG.md (建议追加 V$VERSION 条目)"
echo "   - README.md (如有版本引用)"
