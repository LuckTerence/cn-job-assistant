#!/usr/bin/env bash
# Create GitHub Release for current skill.json version (needs: gh auth login)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: install GitHub CLI: https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: not logged in. Run: gh auth login" >&2
  echo "Then re-run: bash scripts/publish_github_release.sh" >&2
  exit 1
fi

VER="$(python3 -c "import json; print(json.load(open('skill.json'))['version'])")"
TAG="v${VER}"
REPO="${GITHUB_REPOSITORY:-LuckTerence/cn-job-assistant}"
NOTES="docs/github-release-v1.0.0.md"
if [[ ! -f "$NOTES" ]]; then
  NOTES="CHANGELOG.md"
fi

# Ensure tag exists remotely or create from HEAD
if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag -a "$TAG" -m "$TAG"
  echo "created local tag $TAG"
fi

if ! git ls-remote --tags cn "refs/tags/$TAG" | grep -q "$TAG"; then
  git push cn "$TAG" || git push origin "$TAG" || true
fi

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "release $TAG already exists on $REPO"
  gh release view "$TAG" --repo "$REPO" --web 2>/dev/null || true
  exit 0
fi

gh release create "$TAG" \
  --repo "$REPO" \
  --title "CN Job Assistant ${TAG}" \
  --notes-file "$NOTES" \
  --latest

echo "OK: https://github.com/${REPO}/releases/tag/${TAG}"
