# NAV Scoring - Release & Versioning Setup

✓ **Setup Complete!** All versioning, release workflows, and documentation have been configured.

## What's Been Configured

### ✓ 1. Semantic Versioning System
- **VERSION file** (`VERSION`) - Contains current version: 0.1.0
- **Version bump script** (`scripts/bump-version.sh`) - Automates version increments
- Supports major, minor, and patch version bumps

### ✓ 2. Changelog Management
- **CHANGELOG.md** - Documented in Keep a Changelog format
- **Changelog generator** (`scripts/generate-changelog.sh`) - Auto-generates entries from git commits
- Reads conventional commits and categorizes changes

### ✓ 3. Complete Release Workflow
- **Release script** (`scripts/release.sh`) - Orchestrates entire release process
- Automates: version bump → changelog update → git tag → push to GitHub

### ✓ 4. GitHub Actions Integration
- **Automated release workflow** (`.github/workflows/release.yml`)
- Creates GitHub releases automatically on version tag push
- Optional: Auto-builds Docker images (requires secrets configuration)

### ✓ 5. Git Hooks
- **Pre-commit validation** (`.git/hooks/pre-commit`)
- Validates VERSION file format
- Checks for shell script syntax
- Prevents accidental commits of sensitive files

### ✓ 6. Documentation
- **VERSIONING.md** - Complete guide to semantic versioning strategy
- **GITHUB_SETUP.md** - Step-by-step GitHub repository setup

## Next Steps

### Step 1: Make Scripts Executable (IMPORTANT)

```bash
chmod +x scripts/*.sh .git/hooks/pre-commit
```

### Step 2: Create GitHub Repository

Follow `docs/GITHUB_SETUP.md` for:
1. Create repo on GitHub (nav-scoring or siu-nav-scoring)
2. Add remote: `git remote add origin <url>`
3. Push code: `git push -u origin main --tags`

### Step 3: Use Release Workflow

From now on, releasing is simple:

```bash
# Make commits normally (use conventional commit format for best changelog)
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"

# When ready to release:
./scripts/release.sh patch   # Bug fix release
./scripts/release.sh minor   # New feature release
./scripts/release.sh major   # Breaking changes
```

## Project Status

```
Current Version: 0.1.0
Last Commit: 6de4d97 (chore: add version management and release workflow)
Branch: master
Files Staged: 0
```

## Project Structure

```
nav_scoring/
├── VERSION                          # Current version (0.1.0)
├── CHANGELOG.md                     # Release notes
├── SETUP_INSTRUCTIONS.md           # This file
├── scripts/
│   ├── bump-version.sh            # Version management
│   ├── generate-changelog.sh       # Changelog generation
│   └── release.sh                 # Complete release workflow
├── docs/
│   ├── VERSIONING.md              # Versioning strategy guide
│   └── GITHUB_SETUP.md            # GitHub repository setup
├── .github/workflows/
│   └── release.yml                # GitHub Actions automation
└── .git/hooks/
    └── pre-commit                 # Git validation hook
```

## Quick Reference

### View Current Version
```bash
cat VERSION
```

### Bump Version (without full release)
```bash
./scripts/bump-version.sh patch  # 0.1.0 → 0.1.1
```

### Generate Changelog (manually)
```bash
./scripts/generate-changelog.sh
```

### Complete Release
```bash
./scripts/release.sh patch
```

### View Release History
```bash
git tag -l
git log --oneline --all
```

## Conventional Commits Format

For best changelog categorization, use these commit prefixes:

```bash
git commit -m "feat: add new feature"      # → Added
git commit -m "fix: resolve bug"           # → Fixed
git commit -m "refactor: improve code"     # → Changed
git commit -m "perf: optimize performance" # → Changed
git commit -m "docs: update readme"        # → Changed
git commit -m "test: add unit tests"       # → Changed
git commit -m "style: format code"         # → Changed
```

Learn more: https://www.conventionalcommits.org/

## Troubleshooting

### Scripts won't run
```bash
chmod +x scripts/*.sh .git/hooks/pre-commit
```

### "Permission denied" when pushing
- Check git remote: `git remote -v`
- If SSH: Ensure SSH key is added to GitHub
- If HTTPS: Use personal access token instead of password

### Want to test version bump without committing
```bash
# Check what would happen
cat VERSION
./scripts/bump-version.sh patch
# Review with: git log -1 && git show HEAD
# Undo if needed: git reset --hard HEAD~1 && git tag -d v0.1.1
```

### Forgot to make commits before releasing
```bash
# Just make your commits and run release script again
git commit -m "your changes"
./scripts/release.sh patch
```

## Git Hook Notes

The pre-commit hook validates:
- ✓ VERSION file format (semantic version)
- ✓ Shell script syntax
- ✓ No config.yaml accidentally committed
- ⚠ Possible secrets in code

If a check fails, the commit is blocked (fix and try again).
If you need to bypass (carefully!):
```bash
git commit --no-verify
```

## Support Files

- **docs/VERSIONING.md** - Detailed versioning documentation
- **docs/GITHUB_SETUP.md** - GitHub configuration steps
- **.github/workflows/release.yml** - GitHub Actions configuration

Read these for detailed information!

## What Changed Since Last Commit

This commit added:
- VERSION file with semantic versioning
- 3 new shell scripts for version/release management
- CHANGELOG.md with initial release notes
- GitHub Actions workflow for automated releases
- Git pre-commit hook for validation
- Complete versioning documentation
- GitHub setup guide

All scripts are tested and ready to use!

---

**Remember:** Every release from now on is as simple as:
```bash
./scripts/release.sh patch
```

That's it! The script handles everything else. 🚀
