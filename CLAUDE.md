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
│   ├── version-history.json         # Historical versions for all addons
│   ├── releases.atom                # Atom feed for version updates
│   ├── releases-history.json        # Internal: persists Atom feed entries
│   ├── feed.json                    # JSON Feed for updates
│   └── missing-dependencies.json    # Dependencies not in index
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
  "tags": ["pvp", "combat"],
  "url": "https://github.com/brainsnorkel/WarMask",
  "last_updated": "2024-12-01T12:00:00Z",
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
    "version": "v1.3.0",
    "download_url": "https://github.com/.../v1.3.0.zip",
    "published_at": "2024-12-01T12:00:00Z",
    "commit_sha": "abc123def456789..."
  },
  "download_sources": [
    {"type": "jsdelivr", "url": "https://cdn.jsdelivr.net/gh/owner/repo@v1.3.0/"},
    {"type": "github_archive", "url": "https://github.com/.../v1.3.0.zip"}
  ],
  "version_info": {
    "version_normalized": {"major": 1, "minor": 3, "patch": 0, "prerelease": null},
    "version_sort_key": 1003000000,
    "is_prerelease": false,
    "release_channel": "stable"
  }
}
```

**Auto-generated fields:**
- `url`: From `source.type` and `source.repo` (GitHub/GitLab/custom)
- `last_updated`: ISO 8601 timestamp of when the addon was last changed
  - New addon: current build timestamp
  - Version/commit changed: `published_at` from the new release
  - Metadata changed: current build timestamp
  - No changes: preserved from previous index
- `install`: Pipeline instructions for addon managers
  - `method`: `github_archive` | `github_release` | `branch`
  - `extract_path`: Subdirectory to extract (null = root)
  - `target_folder`: Folder name in AddOns/ (from `install_folder` > `path` > `name`)
  - `excludes`: Patterns for files to skip
- `latest_release.commit_sha`: Full commit SHA for precise version tracking
- `download_sources`: Array of download URLs in priority order
  - Primary: jsDelivr CDN (no rate limits, CORS-friendly, works if GitHub blocked)
  - Fallback: Direct GitHub archive ZIP
- `version_info`: Pre-computed version metadata for client convenience
  - `version_normalized`: Parsed semver components (null if unparseable or branch-based)
  - `version_sort_key`: Integer for simple version comparison
  - `is_prerelease`: True if alpha/beta/rc/dev version
  - `release_channel`: `stable` | `prerelease` | `branch`
  - `commit_message`: First line of commit (branch-based addons only)

---

## Version History Tracking

The index maintains historical version data for each addon, enabling:
- **Version history popup**: Users can click on version badges to see all recorded versions
- **Atom feed**: RSS/Atom feed of version changes for notifications and tracking
- **Change detection**: Track when addons are updated and what changed

### version-history.json Format

```json
{
  "version": "1.0",
  "generated_at": "2025-12-30T12:00:00Z",
  "description": "Version history for all addons in the index",
  "addons": {
    "warmask": [
      {
        "version": "v1.3.0",
        "published_at": "2025-12-15T10:00:00Z",
        "detected_at": "2025-12-15T12:00:00Z",
        "commit_sha": "abc123..."
      },
      {
        "version": "v1.2.0",
        "published_at": "2025-11-01T10:00:00Z",
        "detected_at": "2025-11-01T12:00:00Z",
        "commit_sha": "def456..."
      }
    ]
  }
}
```

### releases.atom (Atom Feed)

XML Atom feed for version update notifications:
- **URL**: `https://xop.co/eso-addon-index/releases.atom`
- **Entries**: Version change events (addon X updated from v1.0 to v1.1)
- **Limit**: 100 most recent entries
- **Use case**: RSS readers, notification systems, CI/CD triggers

### UI Features

- **Version badge**: Clickable badge on addon cards showing current version
- **Version history modal**: Shows all recorded versions with dates
- **Date format**: Release date and detection date for each version

---

## GitHub Actions Workflows

### validate-pr.yml
- **Trigger**: PRs modifying `addons/**/*.toml`
- **Steps**: Schema validation, repo check, Luacheck, security scan
- **Required**: Must pass for PR merge

### build-index.yml
- **Trigger**: Push to `main` branch
- **Steps**: Compile TOML to JSON, deploy to GitHub Pages
- **Output**: `public/index.json`, `public/version-history.json`, `public/releases.atom`, `public/feed.json`, `public/missing-dependencies.json`

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

### Backward Compatibility (Critical)

**Avoid breaking changes to the JSON schema.** Addon manager clients depend on the index structure, and breaking changes force all clients to update simultaneously.

**Safe changes (additive, non-breaking):**
- Adding new optional fields (clients ignore unknown fields)
- Adding new endpoints (existing endpoints unchanged)
- Adding new values to existing arrays
- Adding new properties to nested objects

**Breaking changes (avoid unless absolutely necessary):**
- Removing fields clients depend on
- Renaming existing fields
- Changing field types (string → array, object → string)
- Changing the structure of nested objects
- Removing endpoints

**If a breaking change is unavoidable:**
1. Deprecate the old field/structure first (add warning to docs)
2. Support both old and new formats during transition period
3. Announce the change with a clear migration timeline
4. Increment the major version number

### Checklist for API Changes

- [ ] Verify change is backward-compatible (additive only)
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
