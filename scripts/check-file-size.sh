#!/usr/bin/env bash
# check-file-size.sh — md2pdf 文件尺寸检查
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
warnings=0

echo "📏 md2pdf 文件尺寸检查..."

check_file() {
  local path="$1"
  local name="$2"
  local warn_lines="${3:-500}"

  if [[ ! -f "$path" ]]; then
    echo "  ⚠️  $name 不存在"
    return
  fi

  local lines=$(wc -l < "$path" | tr -d ' ')
  local size=$(wc -c < "$path" | tr -d ' ')

  echo "  📄 $name: $lines 行, $((size / 1024)) KB"

  if [[ $lines -gt $warn_lines ]]; then
    echo "    ⚠️  超过 $warn_lines 行，建议精简"
    warnings=$((warnings + 1))
  fi
}

check_file "$ROOT/SKILL.md" "SKILL.md" 400
check_file "$ROOT/scripts/md2pdf.py" "md2pdf.py" 600

echo ""
if [[ $warnings -eq 0 ]]; then
  echo "✅ 尺寸检查通过"
else
  echo "⚠️  有 $warnings 项超过建议尺寸"
fi
