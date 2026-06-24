#!/usr/bin/env bash
# lint-paths.sh — md2pdf 发布前自检
set -euo pipefail

STRICT=false
[[ "${1:-}" == "--strict" ]] && STRICT=true

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
errors=0

echo "🔍 md2pdf 发布前自检..."

# 1) 必需文件存在性
required_files=("SKILL.md" "_meta.json" "scripts/md2pdf.py")
for f in "${required_files[@]}"; do
  if [[ -f "$ROOT/$f" ]]; then
    echo "  ✅ $f 存在"
  else
    echo "  ❌ $f 缺失"
    errors=$((errors + 1))
  fi
done

# 2) 版本号一致性
meta_ver=$(python3 -c "import json; print(json.load(open('$ROOT/_meta.json'))['version'])" 2>/dev/null || echo "?")
skill_ver=$(python3 -c "
import re
with open('$ROOT/SKILL.md') as f:
    m = re.search(r'^version:\s*\"(.+)\"', f.read(), re.MULTILINE)
    print(m.group(1) if m else '?')
" 2>/dev/null || echo "?")

echo "  📦 _meta.json:     $meta_ver"
echo "  📄 SKILL.md:       $skill_ver"

if [[ "$meta_ver" == "$skill_ver" ]] && [[ "$meta_ver" != "?" ]]; then
  echo "  ✅ 版本号一致"
else
  echo "  ❌ 版本号不一致!"
  errors=$((errors + 1))
fi

# 3) CHANGELOG 最新版本匹配
if [[ -f "$ROOT/docs/CHANGELOG.md" ]]; then
  changelog_ver=$(grep -oE 'V[0-9]+\.[0-9]+\.[0-9]+' "$ROOT/docs/CHANGELOG.md" | head -1 | sed 's/^V//')
  echo "  📋 CHANGELOG 最新: $changelog_ver"
  if [[ "$meta_ver" != "$changelog_ver" ]]; then
    echo "  ⚠️  CHANGELOG 版本 ($changelog_ver) 与 _meta.json ($meta_ver) 不一致"
  fi
else
  echo "  ⚠️  CHANGELOG.md 不存在"
fi

echo ""
if [[ $errors -eq 0 ]]; then
  echo "✅ 自检通过"
  exit 0
else
  echo "❌ 自检失败 ($errors 项)"
  [[ "$STRICT" == "true" ]] && exit 1
  exit 0
fi
