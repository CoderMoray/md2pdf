#!/usr/bin/env bash
# release.sh — md2pdf 一键发布脚本
# 用法: bash scripts/release.sh 1.1.0 [--skip-github] [--skip-clawhub] [--skip-skillhub] [--dry-run]
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "用法: $0 <X.Y.Z> [--skip-github] [--skip-clawhub] [--skip-skillhub] [--dry-run]"
  exit 1
fi

SKIP_GITHUB=false
SKIP_CLAWHUB=false
SKIP_SKILLHUB=false
DRY_RUN=false

for arg in "${@:2}"; do
  case "$arg" in
    --skip-github)   SKIP_GITHUB=true ;;
    --skip-clawhub)  SKIP_CLAWHUB=true ;;
    --skip-skillhub) SKIP_SKILLHUB=true ;;
    --dry-run)       DRY_RUN=true ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$ROOT/scripts"

echo "🚀 md2pdf 发布 v$VERSION"
[[ "$DRY_RUN" == "true" ]] && echo "⚠️  DRY-RUN 模式（不实际发布）"
echo ""

# ── 前置检查: 发布平台登录状态 ──────────────────────────────
echo "🔍 检查发布平台登录状态..."

SKILLHUB_OK=false
if command -v skillhub &>/dev/null; then
  if skillhub auth whoami &>/dev/null; then
    SKILLHUB_OK=true
    echo "  ✅ SkillHub: 已登录 ($(skillhub auth whoami 2>&1 | grep handle | awk '{print $2}'))"
  else
    echo "  ⚠️  SkillHub: 未登录，跳过（使用 --skip-skillhub 或先 skillhub auth login）"
    SKIP_SKILLHUB=true
  fi
else
  echo "  ⚠️  skillhub CLI 未安装，跳过"
  SKIP_SKILLHUB=true
fi

CLAWHUB_OK=false
if command -v clawhub &>/dev/null; then
  if clawhub whoami &>/dev/null; then
    CLAWHUB_OK=true
    echo "  ✅ ClawHub: 已登录 ($(clawhub whoami 2>&1 | tail -1))"
  else
    echo "  ⚠️  ClawHub: 未登录，跳过（使用 --skip-clawhub 或先 clawhub login）"
    SKIP_CLAWHUB=true
  fi
else
  echo "  ⚠️  clawhub CLI 未安装，跳过"
  SKIP_CLAWHUB=true
fi

echo ""

# ── Step 1: Bump Version ────────────────────────────────────────────
echo "[1/7] 升级版本号..."
bash "$SCRIPTS/bump-version.sh" "$VERSION"

# ── Step 2: Lint ────────────────────────────────────────────────────
echo "[2/7] 发布前自检..."
bash "$SCRIPTS/lint-paths.sh"

# ── Step 3: Build SkillHub Package ──────────────────────────────────
SKILLHUB_SLUG="md2pdf-chrome"  # SkillHub 上 md2pdf 被占用，使用 md2pdf-chrome
echo "[3/7] 构建 SkillHub 包 (slug: $SKILLHUB_SLUG)..."
bash "$SCRIPTS/build-skillhub.sh" --slug "$SKILLHUB_SLUG"

# ── Step 4: Check File Size ─────────────────────────────────────────
echo "[4/7] 文件尺寸检查..."
bash "$SCRIPTS/check-file-size.sh"

# ── Step 5: Publish to ClawHub ─────────────────────────────────────
SKILLHUB_SLUG="${SKILLHUB_SLUG:-md2pdf-chrome}"  # SkillHub 上 md2pdf 被占用
ZIP_PATH="$ROOT/releases/${SKILLHUB_SLUG}-${VERSION}-skillhub.zip"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[5/7] DRY-RUN: 跳过 ClawHub 发布"
  echo "  命令: clawhub publish . --version $VERSION"
else
  echo "[5/7] 发布到 ClawHub..."
  if [[ "$SKIP_CLAWHUB" == "false" ]]; then
    (cd "$ROOT" && clawhub publish . --version "$VERSION" \
      --changelog "详见 docs/CHANGELOG.md") || echo "  ⚠️  ClawHub 发布失败（可手动重试）"
  else
    echo "  ⏭️  跳过 ClawHub"
  fi
fi

# ── Step 6: Publish to SkillHub ────────────────────────────────────
if [[ "$DRY_RUN" == "true" ]]; then
  echo "[6/7] DRY-RUN: 跳过 SkillHub 发布"
  echo "  命令: skillhub publish $ZIP_PATH"
else
  echo "[6/7] 发布到 SkillHub..."
  if [[ "$SKIP_SKILLHUB" == "false" ]]; then
    skillhub publish "$ZIP_PATH" \
      --changelog "详见 docs/CHANGELOG.md" \
      || echo "  ⚠️  SkillHub 发布失败（slug 可能冲突，可手动处理）"
  else
    echo "  ⏭️  跳过 SkillHub"
  fi
fi

# ── Step 7: Git Commit + Tag + Push ────────────────────────────────
echo "[7/7] Git 提交 + Tag + Push..."
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  DRY-RUN: 跳过 git 操作"
  echo "  要执行的命令:"
  echo "    git add -A && git commit -m \"release: v$VERSION\""
  echo "    git tag v$VERSION && git push origin v$VERSION && git push origin main"
elif [[ "$SKIP_GITHUB" == "false" ]]; then
  git add -A
  git commit -m "release: v$VERSION"
  git tag "v$VERSION"
  git push origin "v$VERSION"
  git push origin main
  echo "  ✅ 已推送, GitHub Actions 将自动创建 Release"
else
  git add -A
  git commit -m "release: v$VERSION"
  git tag "v$VERSION"
  echo "  ⚠️  跳过 git push（需手动: git push origin v$VERSION && git push origin main）"
fi

echo ""
echo "✅ md2pdf v$VERSION 发布完成"

# ── 清理：删除本地构建产物（已发布到平台和 GitHub，不再需要） ──
if [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo "🧹 清理本地构建产物..."
  rm -f "$ROOT/releases/${SKILLHUB_SLUG}-${VERSION}-skillhub.zip"
  echo "  ✅ 已删除: releases/${SKILLHUB_SLUG}-${VERSION}-skillhub.zip"
fi
