#!/bin/bash

# Complete release workflow
# Usage: ./scripts/release.sh [major|minor|patch]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

BUMP_TYPE="${1:-patch}"

echo "=========================================="
echo "NAV Scoring Release Workflow"
echo "=========================================="
echo ""

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 [major|minor|patch]"
    exit 1
fi

# Check working directory is clean
if [[ -n $(cd "$PROJECT_ROOT" && git status --porcelain) ]]; then
    echo "Error: Working directory is not clean"
    echo "Please commit or stash your changes first:"
    echo "  git status"
    exit 1
fi

# Check we're on main/master
CURRENT_BRANCH=$(cd "$PROJECT_ROOT" && git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]] && [[ "$CURRENT_BRANCH" != "master" ]]; then
    echo "Warning: You are on branch '$CURRENT_BRANCH'"
    echo "Releases should typically be on 'main' or 'master'"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Step 1: Bumping version..."
$SCRIPTS_DIR/bump-version.sh "$BUMP_TYPE"
echo ""

echo "Step 2: Generating changelog..."
$SCRIPTS_DIR/generate-changelog.sh
echo ""

# Get the new version
NEW_VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d ' \n')

echo "Step 3: Reviewing changes..."
echo "Latest commit:"
cd "$PROJECT_ROOT" && git log -1 --oneline
echo ""
echo "Latest tag:"
cd "$PROJECT_ROOT" && git describe --tags --abbrev=0
echo ""

read -p "Ready to push release v$NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled"
    exit 1
fi

echo ""
echo "Step 4: Pushing to GitHub..."
cd "$PROJECT_ROOT"

if git remote | grep -q "^origin$"; then
    echo "Pushing branch and tags..."
    git push origin "$CURRENT_BRANCH" --tags
    echo "✓ Pushed to origin"
else
    echo "No 'origin' remote configured yet"
    echo "Configure it with: git remote add origin <url>"
    echo ""
    echo "Manual push commands:"
    echo "  git push origin $CURRENT_BRANCH --tags"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Release v$NEW_VERSION Complete!"
echo "=========================================="
echo ""
echo "Release summary:"
echo "  Version: $NEW_VERSION"
echo "  Branch: $CURRENT_BRANCH"
echo "  Tag: v$NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. Create release on GitHub: https://github.com/YOUR_ORG/nav-scoring/releases"
echo "  2. Or wait for GitHub Actions to create it automatically (if configured)"
echo ""
