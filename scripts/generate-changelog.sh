#!/bin/bash

# Changelog generator
# Reads git commits since last tag and categorizes them
# Usage: ./scripts/generate-changelog.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGELOG_FILE="$PROJECT_ROOT/CHANGELOG.md"
VERSION_FILE="$PROJECT_ROOT/VERSION"

# Get current version
CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d ' \n')
CURRENT_DATE=$(date +%Y-%m-%d)

# Get last tag if it exists
LAST_TAG=$(git -C "$PROJECT_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")

if [[ -z "$LAST_TAG" ]]; then
    echo "No previous tags found. Getting all commits since initial commit..."
    COMMIT_RANGE="HEAD"
else
    echo "Last tag: $LAST_TAG"
    COMMIT_RANGE="${LAST_TAG}..HEAD"
fi

# Get commits and categorize
declare -A categories
categories["Added"]=""
categories["Changed"]=""
categories["Fixed"]=""
categories["Removed"]=""

while IFS= read -r commit; do
    [[ -z "$commit" ]] && continue
    # Parse commit message
    message=$(git -C "$PROJECT_ROOT" log -1 --format=%B "$commit" 2>/dev/null | head -1)
    
    # Categorize based on conventional commits
    if [[ $message =~ ^feat ]]; then
        category="Added"
    elif [[ $message =~ ^fix ]]; then
        category="Fixed"
    elif [[ $message =~ ^refactor ]]; then
        category="Changed"
    elif [[ $message =~ ^perf ]]; then
        category="Changed"
    elif [[ $message =~ ^docs ]]; then
        category="Changed"
    elif [[ $message =~ ^chore ]]; then
        # Skip version bump commits
        if [[ $message == *"bump version"* ]]; then
            continue
        else
            category="Changed"
        fi
    elif [[ $message =~ ^style ]]; then
        category="Changed"
    elif [[ $message =~ ^test ]]; then
        category="Changed"
    else
        category="Added"
    fi
    
    # Clean up message
    clean_message=$(echo "$message" | sed 's/^[a-z]*(\([^)]*\)): //' | sed 's/^[a-z]*: //')
    clean_message=$(echo "$clean_message" | head -c 70)
    
    # Add to category (avoid duplicates and empty lines)
    if [[ -n "$clean_message" ]]; then
        categories["$category"]+="- $clean_message
"
    fi
done < <(git -C "$PROJECT_ROOT" rev-list $COMMIT_RANGE 2>/dev/null || true)

# Build changelog entry
CHANGELOG_ENTRY="## [$CURRENT_VERSION] - $CURRENT_DATE

"

for category in "Added" "Changed" "Fixed" "Removed"; do
    if [[ -n "${categories[$category]}" ]]; then
        CHANGELOG_ENTRY+="### $category
${categories[$category]}
"
    fi
done

# Handle existing CHANGELOG.md
if [[ -f "$CHANGELOG_FILE" ]]; then
    # Check if this version is already in the changelog
    if grep -q "\[$CURRENT_VERSION\]" "$CHANGELOG_FILE"; then
        echo "Version [$CURRENT_VERSION] already in CHANGELOG.md"
        echo "To update, manually edit the changelog or remove the version entry first"
        exit 0
    fi
    
    # Insert after the "# Changelog" header (first 2 lines)
    head -n 2 "$CHANGELOG_FILE" > "$CHANGELOG_FILE.tmp"
    echo "" >> "$CHANGELOG_FILE.tmp"
    echo "$CHANGELOG_ENTRY" >> "$CHANGELOG_FILE.tmp"
    tail -n +3 "$CHANGELOG_FILE" >> "$CHANGELOG_FILE.tmp"
    mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
else
    # Create new CHANGELOG.md
    cat > "$CHANGELOG_FILE" << 'EOF'
# Changelog

All notable changes to the NAV Scoring application.

EOF
    echo "$CHANGELOG_ENTRY" >> "$CHANGELOG_FILE"
fi

echo "✓ CHANGELOG.md updated with version $CURRENT_VERSION"
echo ""
echo "Review the changes:"
echo "  git diff CHANGELOG.md"
echo ""
echo "If you want to edit the changelog, do so now and then:"
echo "  git add CHANGELOG.md"
echo "  git commit --amend --no-edit"
