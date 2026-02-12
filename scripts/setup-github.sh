#!/bin/bash
# GitHub Setup Script - Automates repository creation and initial push
# Usage: ./scripts/setup-github.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 GitHub Repository Setup"
echo "=========================="
echo ""

# Check for credentials file
if [ ! -f ".github-credentials" ]; then
    echo "❌ ERROR: .github-credentials file not found!"
    echo ""
    echo "Please create .github-credentials from the template:"
    echo "  1. cp .github-credentials.template .github-credentials"
    echo "  2. Edit .github-credentials with your GitHub username and token"
    echo "  3. Run this script again"
    echo ""
    exit 1
fi

# Source credentials
source .github-credentials

# Validate credentials
if [ -z "$GITHUB_USERNAME" ] || [ "$GITHUB_USERNAME" = "your-github-username" ]; then
    echo "❌ ERROR: GITHUB_USERNAME not set in .github-credentials"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_YourPersonalAccessTokenHere" ]; then
    echo "❌ ERROR: GITHUB_TOKEN not set in .github-credentials"
    exit 1
fi

if [ -z "$REPO_NAME" ]; then
    REPO_NAME="nav-scoring"
fi

echo "✅ Credentials loaded"
echo "   Username: $GITHUB_USERNAME"
echo "   Token: ${GITHUB_TOKEN:0:10}..."
echo "   Repo: $REPO_NAME"
echo ""

# Determine repository URL
if [ -z "$GITHUB_ORG" ]; then
    REPO_OWNER="$GITHUB_USERNAME"
else
    REPO_OWNER="$GITHUB_ORG"
fi

REPO_URL="https://github.com/$REPO_OWNER/$REPO_NAME.git"
API_URL="https://api.github.com"

echo "📦 Creating GitHub repository: $REPO_OWNER/$REPO_NAME"

# Create repository via GitHub API
CREATE_RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"NAV Scoring application for SIU Aviation\",\"private\":false}" \
    "$API_URL/user/repos" 2>&1)

if echo "$CREATE_RESPONSE" | grep -q '"id"'; then
    echo "✅ Repository created successfully"
elif echo "$CREATE_RESPONSE" | grep -q "name already exists"; then
    echo "ℹ️  Repository already exists (continuing)"
else
    echo "⚠️  Could not create repository via API (may need manual creation)"
    echo "   Response: $CREATE_RESPONSE"
    echo ""
    echo "📝 Manual steps:"
    echo "   1. Go to https://github.com/new"
    echo "   2. Create repository named: $REPO_NAME"
    echo "   3. Run this script again"
    echo ""
    read -p "Press Enter if you've manually created the repo, or Ctrl+C to exit..."
fi

echo ""
echo "🔗 Connecting local repository to GitHub"

# Check if remote already exists
if git remote get-url origin >/dev/null 2>&1; then
    CURRENT_URL=$(git remote get-url origin)
    echo "ℹ️  Remote 'origin' already exists: $CURRENT_URL"
    read -p "Replace with $REPO_URL? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        git remote add origin "$REPO_URL"
        echo "✅ Remote updated"
    fi
else
    git remote add origin "$REPO_URL"
    echo "✅ Remote 'origin' added"
fi

echo ""
echo "🏷️  Renaming branch to 'main'"
git branch -M main

echo ""
echo "📤 Pushing to GitHub"

# Configure git credential helper for this push
git config credential.helper store
echo "https://$GITHUB_USERNAME:$GITHUB_TOKEN@github.com" > ~/.git-credentials

# Push with credentials
if git push -u origin main; then
    echo "✅ Code pushed successfully!"
else
    echo "⚠️  Push failed. Trying with force..."
    git push -u origin main --force
fi

# Push tags
echo ""
echo "🏷️  Pushing tags"
git push origin --tags

# Clean up credentials
rm -f ~/.git-credentials
git config --unset credential.helper

echo ""
echo "=============================="
echo "✅ GitHub Setup Complete!"
echo "=============================="
echo ""
echo "🔗 Repository URL: https://github.com/$REPO_OWNER/$REPO_NAME"
echo ""
echo "📋 Next steps:"
echo "   • View your repo: https://github.com/$REPO_OWNER/$REPO_NAME"
echo "   • Set up GitHub Actions secrets (if using Docker registry)"
echo "   • Make changes and use: ./scripts/release.sh patch"
echo ""
