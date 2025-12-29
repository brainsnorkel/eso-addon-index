# ESO Addon Index

## Project Status: **IN DEVELOPMENT**

A curated, peer-reviewed registry of ESO (Elder Scrolls Online) addon metadata published as static JSON via GitHub Pages. The index stores only metadata—addon source code remains in author-owned repositories.

### Quick Reference

- **Published Index**: `https://xop.co/eso-addon-index/index.json`
- **Metadata Format**: TOML files in `addons/[slug]/addon.toml`
- **Output Format**: Static JSON files in `public/`
- **Automation**: GitHub Actions for validation, building, and release polling

---

## Repository Structure

```
eso-addon-index/
├── .github/
│   ├── workflows/
│   │   ├── validate-pr.yml          # PR validation pipeline
│   │   ├── build-index.yml          # Build and publish JSON
│   │   └── check-releases.yml       # Scheduled release polling
│   ├── ISSUE_TEMPLATE/
│   │   ├── addon-submission.yml     # Submission form
│   │   └── bug-report.yml
│   └── CODEOWNERS                   # Reviewer assignments
├── addons/
│   ├── _schema.toml                 # TOML schema reference
│   └── [addon-slug]/
│       └── addon.toml               # Individual addon metadata
├── scripts/
│   ├── validate.py                  # Schema + manifest validator
│   ├── build-index.py               # Compiles JSON from TOML
│   ├── poll-releases.py             # GitHub release checker
│   └── luacheck-remote.py           # Remote Luacheck runner
├── public/                          # GitHub Pages output (generated)
│   ├── index.json                   # Full addon index
│   ├── index.min.json               # Minified version
│   └── feed.json                    # JSON Feed for updates
├── docs/
│   ├── addon-manager-client-context.md  # Client integration guide
│   ├── CONTRIBUTING.md              # Submission guidelines
│   ├── REVIEW_PROCESS.md            # Reviewer checklist
│   └── SCHEMA.md                    # Metadata documentation
├── .luacheckrc                      # Luacheck ESO config
└── README.md
```

---

## Development Commands

### Setup

```bash
# Using uv (recommended)
uv sync

# Or traditional venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: Install Luacheck (requires Lua)
brew install lua luarocks
luarocks install luacheck
```

### Validation & Building

```bash
# Validate a single addon TOML
python scripts/validate.py addons/warmask/addon.toml

# Validate all addons
python scripts/validate.py addons/*/addon.toml

# Build the JSON index
python scripts/build-index.py

# Check for new releases
python scripts/poll-releases.py
```

### Testing

```bash
# Validate TOML schema locally
python -c "import toml; print(toml.load('addons/warmask/addon.toml'))"

# Test GitHub API access
curl -s https://api.github.com/repos/brainsnorkel/WarMask | jq '.name, .default_branch'
```

---

## Addon Metadata Schema

### addon.toml Format

```toml
[addon]
slug = "warmask"                       # Unique ID (lowercase, hyphens only)
name = "WarMask"                       # Display name
description = "Brief addon description"
authors = ["brainsnorkel"]
license = "MIT"
category = "combat"                    # See categories below
tags = ["pvp", "combat"]

[source]
type = "github"                        # github | gitlab | custom
repo = "brainsnorkel/WarMask"
branch = "main"                        # Optional
path = "LibAddonMenu-2.0"              # Optional: subdirectory if not at repo root
release_type = "tag"                   # tag | release | branch

[compatibility]
api_version = "101044"                 # Current ESO API version
game_versions = ["U44"]
required_dependencies = []
optional_dependencies = []

[meta]
submitted_by = "brainsnorkel"
submitted_date = 2024-12-27
last_reviewed = 2024-12-27
status = "approved"                    # pending | approved | deprecated | removed
reviewers = ["reviewer1"]
```

### Categories

```
combat, crafting, dungeons, guilds, housing, inventory, library,
maps, miscellaneous, pvp, quests, roleplay, social, trading, ui
```

### Validation Rules

1. `slug` must be unique, lowercase, alphanumeric + hyphens
2. `slug` must match parent directory name
3. Repository must exist and be accessible
4. Repository must contain valid ESO manifest (`.txt` or `.addon` with `## Title:`)
5. If `path` specified, manifest must be in that subdirectory
6. At least one release/tag must exist

### JSON Output Format

The build script generates JSON with these fields:

```json
{
  "slug": "warmask",
  "name": "WarMask",
  "description": "Tracks Mark of Hircine...",
  "authors": ["brainsnorkel"],
  "license": "MIT",
  "category": "combat",
  "tags": ["pvp", "combat"],
  "url": "https://github.com/brainsnorkel/WarMask",
  "source": {
    "type": "github",
    "repo": "brainsnorkel/WarMask",
    "branch": "master",
    "path": "SubDir"
  },
  "compatibility": {...},
  "install": {
    "method": "github_archive",
    "extract_path": null,
    "target_folder": "WarMask",
    "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"]
  },
  "latest_release": {
    "version": "1.0.0",
    "download_url": "https://github.com/.../1.0.0.zip",
    "published_at": "2024-12-01T12:00:00Z"
  }
}
```

**Auto-generated fields:**
- `url`: From `source.type` and `source.repo` (GitHub/GitLab/custom)
- `install`: Pipeline instructions for addon managers
  - `method`: `github_archive` | `github_release` | `branch`
  - `extract_path`: Subdirectory to extract (null = root)
  - `target_folder`: Folder name in AddOns/ (from `install_folder` > `path` > `name`)
  - `excludes`: Patterns for files to skip

---

## GitHub Actions Workflows

### validate-pr.yml
- **Trigger**: PRs modifying `addons/**/*.toml`
- **Steps**: Schema validation, repo check, Luacheck, security scan
- **Required**: Must pass for PR merge

### build-index.yml
- **Trigger**: Push to `main` branch
- **Steps**: Compile TOML to JSON, deploy to GitHub Pages
- **Output**: `public/index.json`, `public/feed.json`

### check-releases.yml
- **Trigger**: Daily at 06:00 UTC
- **Steps**: Poll GitHub for new addon releases, update version info
- **Output**: Auto-commit version updates

---

## Review Process

### For Reviewers

Checklist:
- [ ] TOML schema valid
- [ ] Repository accessible
- [ ] Contains valid ESO addon manifest
- [ ] Luacheck passes (no errors)
- [ ] No malicious code patterns
- [ ] Description accurate
- [ ] Category appropriate
- [ ] Not a duplicate

### Security Patterns to Flag

- `os.execute`, `io.popen` (shell commands)
- `loadstring`, `load` with external input
- Network calls to non-ESO domains
- File operations outside addon directory

---

## Test Addons

The repository includes test addons for development:

### WarMask (standard addon)
- **Source**: https://github.com/brainsnorkel/WarMask
- **Path**: `addons/warmask/addon.toml`

### LibAddonMenu (subdirectory addon)
- **Source**: https://github.com/sirinsidiator/ESO-LibAddonMenu
- **Subdirectory**: `LibAddonMenu-2.0` (addon lives in a subdirectory)
- **Path**: `addons/libaddonmenu/addon.toml`

---

## Dependencies

### Python (3.11+)
- `toml` - TOML parsing
- `requests` - HTTP client for GitHub API
- `jsonschema` - Schema validation

### Optional
- `luacheck` - Lua static analysis
- `gh` - GitHub CLI for workflow testing

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.luacheckrc` | Luacheck config with ESO globals |
| `.github/CODEOWNERS` | Reviewer assignments |
| `addons/_schema.toml` | Reference schema |

---

## API Documentation Maintenance

**IMPORTANT**: When making changes to the index API (JSON structure, fields, endpoints), you MUST update the client documentation:

- **`docs/addon-manager-client-context.md`** - Client integration guide
  - Update field references when schema changes
  - Update endpoints if new JSON files are added
  - Update version history table with changes
  - Update example JSON snippets to reflect current structure

### Checklist for API Changes

- [ ] Update `addon-manager-client-context.md` with new/changed fields
- [ ] Update `docs/SCHEMA.md` if TOML schema changes
- [ ] Update `addons/_schema.toml` reference file
- [ ] Increment version in client docs version history
- [ ] Test that example code snippets still work

---

## Notes

- **No addon source code** - Only metadata stored here
- **Peer review required** - Team of reviewers for submissions
- **Daily polling** - Versions auto-updated via GitHub Actions
- **GitHub Pages** - Static JSON published automatically
