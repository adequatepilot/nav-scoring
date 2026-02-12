# Versioning Strategy

This document explains the versioning system and release workflow for the NAV Scoring project.

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/) (SemVer) with the format `MAJOR.MINOR.PATCH`:

- **MAJOR** (X.0.0) - Breaking changes or major feature releases
- **MINOR** (0.X.0) - New features that are backwards-compatible
- **PATCH** (0.0.X) - Bug fixes and small improvements

Examples:
- `0.1.0` → `0.2.0` (new feature) = MINOR bump
- `0.1.0` → `1.0.0` (breaking change) = MAJOR bump
- `0.1.0` → `0.1.1` (bug fix) = PATCH bump

## Version Management

The current version is stored in the `VERSION` file at the project root.

### Viewing the Current Version

```bash
cat VERSION
```

### Bumping the Version

Use the `bump-version.sh` script to increment the version automatically:

```bash
# Bump patch version (0.1.0 → 0.1.1)
./scripts/bump-version.sh patch

# Bump minor version (0.1.0 → 0.2.0)
./scripts/bump-version.sh minor

# Bump major version (0.1.0 → 1.0.0)
./scripts/bump-version.sh major
```

This script:
- Updates the VERSION file
- Creates a git commit with the version change
- Creates a git tag (e.g., `v0.1.1`)

## Changelog Management

The `CHANGELOG.md` file documents all notable changes to the project.

### Changelog Format

We use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [0.2.0] - 2026-02-15

### Added
- New feature description

### Changed
- Existing functionality change

### Fixed
- Bug fix description

### Removed
- Deprecated feature removal
```

### Generating Changelog Entries

Use the `generate-changelog.sh` script to automatically extract changes from git commits:

```bash
./scripts/generate-changelog.sh
```

This script:
- Reads git commits since the last tag
- Categorizes them using [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat:` → Added
  - `fix:` → Fixed
  - `refactor:`, `perf:`, `docs:`, `style:`, `test:` → Changed
  - `chore:` → Skipped (unless relevant)
- Prepends the new section to CHANGELOG.md
- Prevents duplicate entries

### Manual Changelog Editing

The changelog can be edited manually. Just ensure you maintain the format above.

## Complete Release Workflow

The `release.sh` script automates the complete release process:

```bash
./scripts/release.sh [major|minor|patch]
```

This script:
1. Checks the working directory is clean
2. Bumps the version using `bump-version.sh`
3. Generates changelog entries using `generate-changelog.sh`
4. Shows you the changes for review
5. Asks for confirmation
6. Pushes everything to GitHub (branch + tags)

### Step-by-Step Release Process

#### 1. Make Your Changes

```bash
# Make code changes, fixes, new features, etc.
git commit -m "feat: add awesome new feature"
git commit -m "fix: resolve navigation bug"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format for clear categorization:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `perf:` - Performance improvement
- `docs:` - Documentation
- `style:` - Formatting/style changes
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

#### 2. Prepare Release

```bash
# Run the release script with appropriate bump type
./scripts/release.sh patch
```

The script will:
- Bump the version
- Update CHANGELOG.md
- Show you the changes
- Ask for confirmation

#### 3. Verify Push

Check GitHub to confirm:
- The commit was pushed to your branch
- The tag appears in the releases page
- Changelog is in the repository

#### 4. Create GitHub Release (Optional)

If not using GitHub Actions, manually create a release:

1. Go to: `https://github.com/YOUR_ORG/nav-scoring/releases`
2. Click "Draft a new release"
3. Select tag: `v0.1.1` (whatever version you released)
4. Add release notes from CHANGELOG.md
5. Publish

## Conventional Commits

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for consistent changelog generation.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Examples

```bash
git commit -m "feat: add coach authentication system"
git commit -m "fix(ui): correct navigation button styling"
git commit -m "refactor(routes): simplify route calculation logic"
git commit -m "docs: add API documentation"
git commit -m "test: add unit tests for scoring engine"
```

## Git Tags

Version tags follow the pattern `v<MAJOR>.<MINOR>.<PATCH>`:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`
- `v1.0.0`

View all tags:

```bash
git tag -l
```

View a specific tag:

```bash
git show v0.1.0
```

## GitHub Integration

### Setting Up Remote

First time only:

```bash
git remote add origin https://github.com/YOUR_ORG/nav-scoring.git
git push -u origin main --tags
```

### Pushing Releases

```bash
# Automated via release.sh
./scripts/release.sh patch

# Or manually:
git push origin main --tags
```

### GitHub Actions (Optional)

The `.github/workflows/release.yml` workflow can automatically:
- Create releases on GitHub
- Build Docker images
- Run tests on release branches

See `.github/workflows/release.yml` for configuration.

## Quick Reference

### Common Workflows

**Release a bug fix:**
```bash
git commit -m "fix: resolve issue with flight submission"
./scripts/release.sh patch
```

**Release new features:**
```bash
git commit -m "feat: add route analytics dashboard"
git commit -m "feat: add export to PDF functionality"
./scripts/release.sh minor
```

**Release breaking changes:**
```bash
git commit -m "refactor: reorganize API endpoints

BREAKING CHANGE: /api/v1 endpoints have moved to /api/v2"
./scripts/release.sh major
```

### Troubleshooting

**Forgot to commit before running release.sh:**
```bash
git commit -m "your changes"
./scripts/release.sh patch
```

**Need to fix a commit in the last release:**
```bash
git commit --amend
git push origin main --force-with-lease
# Re-run release script if needed
```

**Remove a tag:**
```bash
git tag -d v0.1.1          # Local
git push origin :v0.1.1    # Remote
```

**Want to bump without releasing:**
```bash
./scripts/bump-version.sh patch
# Review, edit VERSION if needed, then:
git commit --amend
```

## More Information

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
