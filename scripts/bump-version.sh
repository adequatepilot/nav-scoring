#!/bin/bash

# Semantic versioning bump script
# Usage: ./scripts/bump-version.sh [major|minor|patch]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/VERSION"

# Validate VERSION file exists
if [[ ! -f "$VERSION_FILE" ]]; then
    echo "Error: VERSION file not found at $VERSION_FILE"
    exit 1
fi

# Parse current version
CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d ' \n')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Validate bump type
BUMP_TYPE="${1:-patch}"
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 [major|minor|patch]"
    echo "  major - bump to next major version (1.0.0 → 2.0.0)"
    echo "  minor - bump to next minor version (1.0.0 → 1.1.0)"
    echo "  patch - bump to next patch version (1.0.0 → 1.0.1)"
    exit 1
fi

# Calculate new version
case "$BUMP_TYPE" in
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="${NEW_MAJOR}.0.0"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"
        ;;
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
        ;;
esac

echo "Bumping version from $CURRENT_VERSION to $NEW_VERSION ($BUMP_TYPE)"

# Update VERSION file
echo "$NEW_VERSION" > "$VERSION_FILE"

# Create git commit with version
cd "$PROJECT_ROOT"
git add VERSION
git commit -m "chore: bump version to $NEW_VERSION" || true

# Create git tag
git tag -a "v$NEW_VERSION" -m "Release $NEW_VERSION" || {
    echo "Warning: Tag v$NEW_VERSION already exists"
}

echo "✓ Version bumped to $NEW_VERSION"
echo "✓ Git commit created"
echo "✓ Git tag created (v$NEW_VERSION)"
echo ""
echo "Next steps:"
echo "  1. Run ./scripts/generate-changelog.sh to update CHANGELOG.md"
echo "  2. Review the changes: git show HEAD"
echo "  3. Push to GitHub: git push origin master --tags"
echo "  4. Or use ./scripts/release.sh to automate the full process"
