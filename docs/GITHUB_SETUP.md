# GitHub Repository Setup Guide

This guide walks through setting up the nav-scoring repository on GitHub and configuring it for automated releases.

## Prerequisites

- GitHub account with organization access (if applicable)
- Git installed locally
- Personal Access Token (PAT) or credentials ready

## Step 1: Create GitHub Repository

### Option A: Using GitHub Web UI (Recommended)

1. Go to https://github.com/new
2. **Repository name:** `nav-scoring` (or `siu-nav-scoring` if preferred)
3. **Description:** "NAV Scoring application for SIU Aviation"
4. **Visibility:** Choose Public or Private
5. **Initialize repository:** Leave unchecked (we already have commits)
6. Click "Create repository"

### Option B: Using GitHub CLI

```bash
gh repo create nav-scoring \
  --description "NAV Scoring application for SIU Aviation" \
  --private \
  --source=. \
  --remote=origin \
  --push
```

## Step 2: Connect Local Repository to GitHub

The local repository is initialized but not connected to GitHub yet.

### Get Repository URL

From your newly created GitHub repository, copy the HTTPS or SSH URL:
- HTTPS: `https://github.com/YOUR_ORG/nav-scoring.git`
- SSH: `git@github.com:YOUR_ORG/nav-scoring.git`

### Add Remote and Push

```bash
cd /home/michael/clawd/work/nav_scoring

# Add the remote
git remote add origin https://github.com/YOUR_ORG/nav-scoring.git

# Rename 'master' branch to 'main' (recommended)
git branch -M main

# Push initial commit and all tags
git push -u origin main --tags
```

### Verify

Check that the code appears on GitHub:
- Navigate to your repository
- You should see your code files and the initial commit
- Check "v0.1.0" tag appears in the Releases section

## Step 3: Configure Default Branch

On GitHub:

1. Go to Repository Settings → Branches
2. Set default branch to `main`
3. Verify "master" branch is no longer default

## Step 4: Enable GitHub Actions (Optional but Recommended)

GitHub Actions are already configured in `.github/workflows/release.yml`.

### To Enable Automatic Docker Builds

If you want automatic Docker image builds on release:

1. Go to Repository Secrets (Settings → Secrets and variables → Actions)
2. Add these secrets:
   - `DOCKER_USERNAME` - Your Docker Hub username
   - `DOCKER_PASSWORD` - Your Docker Hub access token

The GitHub Actions workflow will then automatically:
- Create GitHub Release when you push a version tag
- Build Docker image and push to Docker Hub
- Include changelog in release notes

## Step 5: Make Scripts Executable

The release scripts need execute permissions:

```bash
cd /home/michael/clawd/work/nav_scoring
chmod +x scripts/*.sh
chmod +x .git/hooks/pre-commit

# Verify
ls -la scripts/*.sh
```

## Step 6: First Release

Everything is set up! Here's how to make your first release:

### Make Changes (if needed)

```bash
# Edit files, make commits
git commit -m "feat: add awesome feature"
```

### Run Release Workflow

```bash
# Make sure working directory is clean
git status

# Run the complete release workflow
./scripts/release.sh patch
```

The script will:
1. Bump version (0.1.0 → 0.1.1)
2. Update CHANGELOG.md
3. Create git commit and tag
4. Push to GitHub
5. Trigger GitHub Actions (if enabled)

### Verify Release

1. Check GitHub Releases: `https://github.com/YOUR_ORG/nav-scoring/releases`
2. New release should appear with changelog
3. If Docker secrets configured, image will build automatically

## Troubleshooting

### "fatal: remote origin already exists"

The remote might already be configured. Check:

```bash
git remote -v
```

Either:
- Update existing remote: `git remote set-url origin <new-url>`
- Or remove and re-add: `git remote remove origin && git remote add origin <url>`

### "Permission denied" when running scripts

The scripts need execute permission:

```bash
chmod +x scripts/*.sh .git/hooks/pre-commit
```

### "! [rejected] main -> main (non-fast-forward)"

The remote has divergent history. Options:
- Pull and merge: `git pull origin main --rebase`
- Force push (careful!): `git push -f origin main --tags`

### SSH vs HTTPS

If using SSH and getting permission errors:

```bash
# Check SSH key is added to GitHub
ssh -T git@github.com

# If not working, generate new key
ssh-keygen -t ed25519 -C "your-email@example.com"
# Add public key to GitHub settings
```

## Next Steps

Now you're ready to use the release workflow:

```bash
# Normal development
git commit -m "feat: new feature"
git commit -m "fix: bug fix"

# When ready to release
./scripts/release.sh patch     # for bug fixes
./scripts/release.sh minor     # for new features
./scripts/release.sh major     # for breaking changes
```

See `docs/VERSIONING.md` for detailed information about semantic versioning and the release process.

## Quick Reference

```bash
# View current setup
git remote -v
git branch -a
cat VERSION

# Test without pushing
./scripts/bump-version.sh patch --dry-run  # (not implemented, use with caution)

# Undo a release
git tag -d v0.1.0
git push origin :v0.1.0

# Change remote URL
git remote set-url origin https://github.com/NEW_ORG/nav-scoring.git
```

## Support

If you encounter issues:

1. Check git status: `git status`
2. View remote config: `git remote -v`
3. Check logs: `git log --oneline --all`
4. Review script output carefully for error messages
5. Consult `docs/VERSIONING.md` for detailed documentation
