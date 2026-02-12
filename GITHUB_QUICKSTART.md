# GitHub Setup - Quick Start

## 3 Simple Steps

### Step 1: Get Your GitHub Token

1. Go to: https://github.com/settings/tokens/new
2. Token name: `nav-scoring`
3. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
4. Click "Generate token"
5. **Copy the token** (starts with `ghp_...`)

### Step 2: Create Credentials File

```bash
cd /home/michael/clawd/work/nav_scoring
cp .github-credentials.template .github-credentials
```

Then edit `.github-credentials` and fill in:

```bash
GITHUB_USERNAME="YourGitHubUsername"
GITHUB_TOKEN="ghp_YourActualTokenHere"
GITHUB_ORG=""  # Leave empty for personal account
REPO_NAME="nav-scoring"
```

**Save the file.**

### Step 3: Run Setup Script

```bash
./scripts/setup-github.sh
```

That's it! The script will:
- Create the GitHub repository (if needed)
- Connect your local repo to GitHub
- Push all your code
- Push version tags

## Done!

Your repository will be live at:
`https://github.com/YourUsername/nav-scoring`

## Making Releases

After setup, create new releases with:

```bash
# Make your changes, commit normally
git commit -m "feat: add new feature"

# Create a release (patch version bump)
./scripts/release.sh patch

# Or for bigger changes:
./scripts/release.sh minor   # 0.1.0 → 0.2.0
./scripts/release.sh major   # 0.1.0 → 1.0.0
```

## Troubleshooting

**"Repository already exists"**
- That's fine! The script will connect to it and push your code.

**"Authentication failed"**
- Check your token is correct in `.github-credentials`
- Make sure token has `repo` scope

**"Permission denied"**
- Make sure script is executable: `chmod +x scripts/setup-github.sh`

Need help? Check `docs/GITHUB_SETUP.md` for detailed guide.
