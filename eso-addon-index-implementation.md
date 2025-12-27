# eso-addon-index Implementation Guide

Version: 1.0  
Date: 27 December 2024

## Overview

A curated, peer-reviewed registry of ESO addon metadata published as static JSON via GitHub Pages. The index stores only metadata—addon source code remains in author-owned repositories.

---

## Repository Structure

```
eso-addon-index/
├── .github/
│   ├── workflows/
│   │   ├── validate-pr.yml          # Runs on PR submissions
│   │   ├── build-index.yml          # Builds and publishes JSON
│   │   └── check-releases.yml       # Scheduled release polling
│   ├── ISSUE_TEMPLATE/
│   │   ├── addon-submission.yml     # Structured submission form
│   │   └── bug-report.yml
│   └── CODEOWNERS                   # Reviewer assignments
├── addons/
│   ├── _schema.toml                 # TOML schema reference
│   └── [addon-slug]/
│       └── addon.toml               # Individual addon metadata
├── scripts/
│   ├── validate.py                  # Schema + manifest validator
│   ├── build-index.py               # Compiles JSON from TOML files
│   ├── poll-releases.py             # Checks GitHub for new versions
│   └── luacheck-remote.py           # Runs Luacheck on source repos
├── public/                          # GitHub Pages output (generated)
│   ├── index.json                   # Full addon index
│   ├── index.min.json               # Minified version
│   └── feed.json                    # JSON Feed for updates
├── docs/
│   ├── CONTRIBUTING.md              # Submission guidelines
│   ├── REVIEW_PROCESS.md            # Reviewer checklist
│   └── SCHEMA.md                    # Metadata field documentation
├── .luacheckrc                      # Luacheck config for ESO addons
├── LICENSE                          # MIT or Apache 2.0
└── README.md
```

---

## Addon Metadata Schema

### addon.toml Format

```toml
[addon]
slug = "libaddonmenu"                      # Unique identifier (lowercase, hyphens)
name = "LibAddonMenu-2.0"                  # Display name
description = "A library for creating addon settings menus"
authors = ["sirinsidiator", "votan"]
license = "Artistic-2.0"
category = "library"                       # See category list below
tags = ["settings", "ui", "library"]

[source]
type = "github"                            # github | gitlab | custom
repo = "sirinsidiator/ESO-LibAddonMenu"
branch = "master"                          # Optional, defaults to default branch
release_type = "tag"                       # tag | release | branch

[compatibility]
api_version = "101044"                     # Current ESO API version
game_versions = ["U44", "U43"]             # Supported game updates
optional_dependencies = []
required_dependencies = []

[meta]
submitted_by = "github-username"
submitted_date = 2024-12-27
last_reviewed = 2024-12-27
status = "approved"                        # pending | approved | deprecated | removed
reviewers = ["reviewer1", "reviewer2"]
```

### Categories

```
combat, crafting, dungeons, guilds, housing, inventory, library,
maps, miscellaneous, pvp, quests, roleplay, social, trading, ui
```

### Validation Rules

1. `slug` must be unique, lowercase, alphanumeric + hyphens
2. `repo` must be a valid, accessible GitHub/GitLab repository
3. Repository must contain a valid ESO addon manifest (`.txt` file with `## Title:`)
4. At least one release/tag must exist
5. `api_version` must be a valid ESO API version string

---

## GitHub Actions Workflows

### 1. PR Validation (`validate-pr.yml`)

Triggered on pull requests to `addons/**/*.toml`.

```yaml
name: Validate Addon Submission

on:
  pull_request:
    paths:
      - 'addons/**/*.toml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install toml requests luacheck-wrapper jsonschema
      
      - name: Get changed files
        id: changed
        uses: tj-actions/changed-files@v44
        with:
          files: 'addons/**/*.toml'
      
      - name: Validate TOML schema
        run: python scripts/validate.py ${{ steps.changed.outputs.all_changed_files }}
      
      - name: Check source repository
        run: python scripts/check-repo.py ${{ steps.changed.outputs.all_changed_files }}
      
      - name: Run Luacheck on source
        run: python scripts/luacheck-remote.py ${{ steps.changed.outputs.all_changed_files }}
        continue-on-error: true  # Warnings don't block, only errors
      
      - name: Security scan
        run: python scripts/security-scan.py ${{ steps.changed.outputs.all_changed_files }}
      
      - name: Post results to PR
        uses: actions/github-script@v7
        with:
          script: |
            // Post validation summary as PR comment
```

### 2. Build Index (`build-index.yml`)

Triggered on push to `main` branch.

```yaml
name: Build and Publish Index

on:
  push:
    branches: [main]
    paths:
      - 'addons/**/*.toml'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install toml requests
      
      - name: Build index JSON
        run: python scripts/build-index.py
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
          cname: addons.example.com  # Optional custom domain
```

### 3. Release Polling (`check-releases.yml`)

Scheduled daily to update version information.

```yaml
name: Check for New Releases

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 06:00 UTC
  workflow_dispatch:

jobs:
  poll:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Poll GitHub releases
        run: python scripts/poll-releases.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit version updates
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: update addon versions [automated]"
          file_pattern: 'addons/**/*.toml public/*.json'
```

---

## Core Scripts

### validate.py

```python
#!/usr/bin/env python3
"""Validate addon TOML files against schema and repository checks."""

import sys
import toml
import requests
from pathlib import Path
from jsonschema import validate, ValidationError

SCHEMA = {
    "type": "object",
    "required": ["addon", "source"],
    "properties": {
        "addon": {
            "type": "object",
            "required": ["slug", "name", "description", "authors", "category"],
            "properties": {
                "slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "name": {"type": "string", "minLength": 1},
                "description": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}},
                "license": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": [
                        "combat", "crafting", "dungeons", "guilds", "housing",
                        "inventory", "library", "maps", "miscellaneous", "pvp",
                        "quests", "roleplay", "social", "trading", "ui"
                    ]
                },
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        },
        "source": {
            "type": "object",
            "required": ["type", "repo"],
            "properties": {
                "type": {"type": "string", "enum": ["github", "gitlab", "custom"]},
                "repo": {"type": "string"},
                "branch": {"type": "string"},
                "release_type": {"type": "string", "enum": ["tag", "release", "branch"]}
            }
        }
    }
}


def validate_toml_file(filepath: Path) -> list[str]:
    """Validate a single TOML file. Returns list of errors."""
    errors = []
    
    try:
        data = toml.load(filepath)
    except toml.TomlDecodeError as e:
        return [f"TOML parse error: {e}"]
    
    # Schema validation
    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as e:
        errors.append(f"Schema error: {e.message}")
    
    # Check slug matches directory name
    expected_slug = filepath.parent.name
    actual_slug = data.get("addon", {}).get("slug", "")
    if actual_slug != expected_slug:
        errors.append(f"Slug '{actual_slug}' doesn't match directory '{expected_slug}'")
    
    # Check for duplicate slugs
    existing_slugs = {p.parent.name for p in Path("addons").glob("*/addon.toml")}
    if actual_slug in existing_slugs and filepath.parent.name != actual_slug:
        errors.append(f"Duplicate slug: '{actual_slug}' already exists")
    
    return errors


def check_repository(data: dict) -> list[str]:
    """Verify the source repository exists and contains a valid addon."""
    errors = []
    source = data.get("source", {})
    
    if source.get("type") == "github":
        repo = source.get("repo", "")
        api_url = f"https://api.github.com/repos/{repo}"
        
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 404:
            errors.append(f"Repository not found: {repo}")
            return errors
        
        # Check for ESO addon manifest
        contents_url = f"https://api.github.com/repos/{repo}/contents"
        resp = requests.get(contents_url, timeout=10)
        if resp.ok:
            files = [f["name"] for f in resp.json() if f["type"] == "file"]
            txt_files = [f for f in files if f.endswith(".txt")]
            if not txt_files:
                errors.append("No addon manifest (.txt) found in repository root")
    
    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate.py <file1.toml> [file2.toml ...]")
        sys.exit(1)
    
    all_errors = []
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            all_errors.append(f"{filepath}: File not found")
            continue
        
        errors = validate_toml_file(path)
        data = toml.load(path)
        errors.extend(check_repository(data))
        
        for error in errors:
            all_errors.append(f"{filepath}: {error}")
    
    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        sys.exit(1)
    
    print("All validations passed")


if __name__ == "__main__":
    main()
```

### build-index.py

```python
#!/usr/bin/env python3
"""Compile addon TOML files into a single JSON index."""

import json
import toml
import requests
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_DIR = Path("public")
ADDONS_DIR = Path("addons")


def fetch_latest_release(source: dict) -> dict | None:
    """Fetch latest release info from GitHub."""
    if source.get("type") != "github":
        return None
    
    repo = source.get("repo", "")
    release_type = source.get("release_type", "release")
    
    if release_type == "release":
        url = f"https://api.github.com/repos/{repo}/releases/latest"
    else:  # tag
        url = f"https://api.github.com/repos/{repo}/tags"
    
    try:
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            return None
        
        data = resp.json()
        if release_type == "tag":
            if not data:
                return None
            data = data[0]  # Latest tag
            return {
                "version": data["name"],
                "download_url": f"https://github.com/{repo}/archive/refs/tags/{data['name']}.zip",
                "published_at": None
            }
        else:
            return {
                "version": data.get("tag_name", "unknown"),
                "download_url": data.get("zipball_url"),
                "published_at": data.get("published_at")
            }
    except Exception:
        return None


def build_index() -> dict:
    """Build the complete addon index."""
    addons = []
    
    for toml_path in ADDONS_DIR.glob("*/addon.toml"):
        data = toml.load(toml_path)
        
        # Skip non-approved addons
        if data.get("meta", {}).get("status") != "approved":
            continue
        
        addon_entry = {
            "slug": data["addon"]["slug"],
            "name": data["addon"]["name"],
            "description": data["addon"]["description"],
            "authors": data["addon"]["authors"],
            "license": data["addon"].get("license", "Unknown"),
            "category": data["addon"]["category"],
            "tags": data["addon"].get("tags", []),
            "source": {
                "type": data["source"]["type"],
                "repo": data["source"]["repo"],
                "branch": data["source"].get("branch", "main")
            },
            "compatibility": data.get("compatibility", {}),
            "latest_release": fetch_latest_release(data["source"])
        }
        
        addons.append(addon_entry)
    
    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "addon_count": len(addons),
        "addons": sorted(addons, key=lambda x: x["name"].lower())
    }


def build_json_feed(index: dict) -> dict:
    """Build JSON Feed format for feed readers."""
    items = []
    for addon in index["addons"]:
        release = addon.get("latest_release") or {}
        items.append({
            "id": addon["slug"],
            "title": f"{addon['name']} {release.get('version', '')}".strip(),
            "url": f"https://github.com/{addon['source']['repo']}",
            "date_published": release.get("published_at"),
            "authors": [{"name": a} for a in addon["authors"]],
            "summary": addon["description"],
            "tags": addon["tags"]
        })
    
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "ESO Addon Index",
        "home_page_url": "https://github.com/your-org/eso-addon-index",
        "feed_url": "https://your-org.github.io/eso-addon-index/feed.json",
        "items": items
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    index = build_index()
    
    # Full index
    with open(OUTPUT_DIR / "index.json", "w") as f:
        json.dump(index, f, indent=2)
    
    # Minified index
    with open(OUTPUT_DIR / "index.min.json", "w") as f:
        json.dump(index, f, separators=(",", ":"))
    
    # JSON Feed
    feed = build_json_feed(index)
    with open(OUTPUT_DIR / "feed.json", "w") as f:
        json.dump(feed, f, indent=2)
    
    print(f"Built index with {index['addon_count']} addons")


if __name__ == "__main__":
    main()
```

---

## Published Index Format

### index.json

```json
{
  "version": "1.0",
  "generated_at": "2024-12-27T10:30:00Z",
  "addon_count": 150,
  "addons": [
    {
      "slug": "libaddonmenu",
      "name": "LibAddonMenu-2.0",
      "description": "A library for creating addon settings menus",
      "authors": ["sirinsidiator", "votan"],
      "license": "Artistic-2.0",
      "category": "library",
      "tags": ["settings", "ui", "library"],
      "source": {
        "type": "github",
        "repo": "sirinsidiator/ESO-LibAddonMenu",
        "branch": "master"
      },
      "compatibility": {
        "api_version": "101044",
        "game_versions": ["U44", "U43"],
        "required_dependencies": [],
        "optional_dependencies": []
      },
      "latest_release": {
        "version": "2.0r35",
        "download_url": "https://github.com/sirinsidiator/ESO-LibAddonMenu/archive/refs/tags/2.0r35.zip",
        "published_at": "2024-11-15T14:30:00Z"
      }
    }
  ]
}
```

---

## Submission Process

### For Addon Authors

1. Fork the repository
2. Create directory `addons/[your-addon-slug]/`
3. Add `addon.toml` with required fields
4. Submit pull request using the addon submission template
5. Wait for automated validation to pass
6. Address any reviewer feedback
7. PR merged after two approvals

### For Reviewers

Checklist:

- [ ] TOML schema valid
- [ ] Repository exists and is accessible
- [ ] Contains valid ESO addon manifest
- [ ] Luacheck passes (no errors, warnings acceptable)
- [ ] No obvious malicious code patterns
- [ ] Description accurate
- [ ] Category appropriate
- [ ] Not a duplicate of existing addon

---

## Security Considerations

### Automated Checks

1. **Luacheck** — Static analysis for Lua code quality
2. **Pattern scanning** — Flag suspicious patterns:
   - `os.execute`, `io.popen` (shell commands)
   - `loadstring`, `load` with external input
   - Network calls to non-ESO domains
   - File operations outside addon directory

### Manual Review

- Source code inspection for non-trivial addons
- Check commit history for suspicious changes
- Verify author identity matches addon credits

---

## Luacheck Configuration

### .luacheckrc

```lua
-- ESO Addon Luacheck Configuration
std = "lua51"
max_line_length = 200

-- ESO global functions and namespaces
globals = {
    "SLASH_COMMANDS",
    "EVENT_MANAGER",
    "SCENE_MANAGER",
    "CALLBACK_MANAGER",
    "LibAddonMenu2",
    "LibStub",
    "ZO_SavedVars",
    "ZO_Dialogs_ShowDialog",
    "ZO_Dialogs_RegisterCustomDialog",
    "d",  -- Debug output
    "df", -- Debug format
}

read_globals = {
    -- ESO API
    "GetAPIVersion",
    "GetDisplayName",
    "GetUnitName",
    "GetMapPlayerPosition",
    "GetCurrentMapZoneIndex",
    -- Add more as needed from ESO API docs
}

-- Ignore common ESO patterns
ignore = {
    "212",  -- Unused argument (common in event handlers)
    "213",  -- Unused loop variable
}
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- GitHub account with repository access
- (Optional) Custom domain for GitHub Pages

### Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/eso-addon-index.git
cd eso-addon-index

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install toml requests jsonschema

# Enable GitHub Pages (Settings > Pages > Source: gh-pages branch)
```

### Adding First Addon

```bash
mkdir -p addons/example-addon
cat > addons/example-addon/addon.toml << 'EOF'
[addon]
slug = "example-addon"
name = "Example Addon"
description = "An example addon for testing"
authors = ["your-username"]
license = "MIT"
category = "miscellaneous"
tags = ["example"]

[source]
type = "github"
repo = "your-username/eso-example-addon"
release_type = "release"

[meta]
submitted_by = "your-username"
submitted_date = 2024-12-27
status = "approved"
EOF

# Validate
python scripts/validate.py addons/example-addon/addon.toml

# Build index
python scripts/build-index.py
```

---

## References

- [ESO API Documentation](https://wiki.esoui.com/API)
- [JSON Feed Specification](https://jsonfeed.org/version/1.1)
- [Luacheck Documentation](https://luacheck.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
