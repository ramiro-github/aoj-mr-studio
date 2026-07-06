#!/usr/bin/env bash
# deploy.sh — commit, push, and publish a GitHub release (tag triggers Actions).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "pyproject.toml" ]] || [[ ! -f "aoj-mr-studio.spec" ]]; then
  echo "Error: run from the AOJ MR Studio repository root (scripts/deploy.sh)."
  exit 1
fi

read_pyproject_version() {
  grep -E '^version = "' pyproject.toml | head -n1 | sed -E 's/^version = "([^"]+)".*/\1/'
}

bump_patch_version() {
  local ver="$1"
  if [[ ! "$ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: cannot bump invalid version: $ver" >&2
    return 1
  fi
  local major minor patch
  IFS=. read -r major minor patch <<< "$ver"
  patch=$((patch + 1))
  echo "${major}.${minor}.${patch}"
}

latest_release_version() {
  git fetch "$REMOTE" --tags --quiet 2>/dev/null || true
  local from_tag
  from_tag="$(git tag -l "v*" --sort=-v:refname | head -n1 | sed 's/^v//')"
  if [[ -n "$from_tag" ]]; then
    echo "$from_tag"
    return
  fi
  read_pyproject_version
}

set_pyproject_version() {
  local ver="$1"
  if [[ "$OSTYPE" == darwin* ]]; then
    sed -i '' -E "s/^version = \".*\"/version = \"${ver}\"/" pyproject.toml
  else
    sed -i -E "s/^version = \".*\"/version = \"${ver}\"/" pyproject.toml
  fi
}

REMOTE="${REMOTE:-origin}"
BRANCH="$(git branch --show-current)"
REMOTE_URL="$(git remote get-url "$REMOTE" 2>/dev/null || true)"

# github.com/owner/repo(.git) -> owner/repo
GITHUB_SLUG=""
if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+/[^/.]+) ]]; then
  GITHUB_SLUG="${BASH_REMATCH[1]}"
fi

LAST_VERSION="$(latest_release_version)"
NEXT_VERSION="$(bump_patch_version "$LAST_VERSION")"

echo "=== AOJ MR Studio — deploy ==="
echo ""
echo "Last version: $LAST_VERSION"
echo "Next version: $NEXT_VERSION  (patch + 1)"
echo ""

read -r -p "Commit message: " COMMIT_MSG
if [[ -z "${COMMIT_MSG// }" ]]; then
  echo "Error: empty commit message."
  exit 1
fi

read -r -p "Release version [${NEXT_VERSION}]: " VERSION_INPUT
VERSION="${VERSION_INPUT:-$NEXT_VERSION}"
VERSION="${VERSION#v}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: invalid version. Use X.Y.Z"
  exit 1
fi
TAG="v${VERSION}"

echo ""
echo "Branch:  $BRANCH"
echo "Remote:  $REMOTE"
echo "Tag:     $TAG"
echo "Commit:  $COMMIT_MSG"
echo ""
read -r -p "Continue? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[yYsS]$ ]]; then
  echo "Cancelled."
  exit 0
fi

echo ""
echo "=== Tests ==="
if [[ -x ".venv/Scripts/python.exe" ]]; then
  .venv/Scripts/python.exe -m pytest
elif [[ -x ".venv/bin/python" ]]; then
  .venv/bin/python -m pytest
elif command -v pytest >/dev/null 2>&1; then
  pytest
else
  python -m pytest
fi

echo ""
echo "=== Version bump (pyproject.toml) ==="
set_pyproject_version "$VERSION"
echo "pyproject.toml -> $VERSION"

echo ""
echo "=== Git commit + push ==="
git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit (working tree clean)."
else
  git commit -m "$COMMIT_MSG"
fi

git push "$REMOTE" "$BRANCH"

echo ""
echo "=== Tag + release ==="
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: tag $TAG already exists locally."
  exit 1
fi

git tag "$TAG"
git push "$REMOTE" "$TAG"

echo ""
echo "=== Deploy started ==="
echo "GitHub Actions will build: AOJ-MR-Studio-${TAG}-win64.zip"
if [[ -n "$GITHUB_SLUG" ]]; then
  echo "Actions:  https://github.com/${GITHUB_SLUG}/actions"
  echo "Releases: https://github.com/${GITHUB_SLUG}/releases"
else
  echo "Check your GitHub repository Actions and Releases pages."
fi
