# Addon Manager Client Integration Guide

This document describes how client applications (addon managers, installers, etc.) should consume the ESO Addon Index API.

**GitHub Repository**: https://github.com/brainsnorkel/eso-addon-index

---

## Index Endpoints

| Endpoint | Description |
|----------|-------------|
| `https://xop.co/eso-addon-index/index.json` | Full addon index with formatting |
| `https://xop.co/eso-addon-index/index.min.json` | Minified index (smaller payload) |
| `https://xop.co/eso-addon-index/feed.json` | JSON Feed format for updates |
| `https://xop.co/eso-addon-index/missing-dependencies.json` | Dependencies referenced but not available in index |

---

## Index Structure

### Root Object

```json
{
  "version": "1.0",
  "generated_at": "2024-12-28T10:30:00+00:00",
  "addon_count": 42,
  "addons": [...]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Index schema version |
| `generated_at` | string | ISO 8601 timestamp of last build |
| `addon_count` | integer | Total number of addons in index |
| `addons` | array | Array of addon objects (sorted by name) |

### Addon Object

```json
{
  "slug": "warmask",
  "name": "WarMask",
  "description": "Tracks Mark of Hircine from Huntsman's Warmask...",
  "authors": ["brainsnorkel"],
  "license": "MIT",
  "tags": ["pvp", "combat", "buff-tracking"],
  "url": "https://github.com/brainsnorkel/WarMask",
  "source": {
    "type": "github",
    "repo": "brainsnorkel/WarMask",
    "branch": "master"
  },
  "compatibility": {
    "api_version": "101048",
    "game_versions": ["U45"],
    "required_dependencies": ["libaddonmenu"],
    "optional_dependencies": []
  },
  "install": {
    "method": "github_archive",
    "extract_path": null,
    "target_folder": "WarMask",
    "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"]
  },
  "latest_release": {
    "version": "v1.3.0",
    "download_url": "https://github.com/brainsnorkel/WarMask/archive/refs/tags/v1.3.0.zip",
    "published_at": "2024-12-01T12:00:00Z",
    "commit_sha": "abc123def456..."
  },
  "version_info": {
    "version_normalized": {
      "major": 1,
      "minor": 3,
      "patch": 0,
      "prerelease": null
    },
    "version_sort_key": 1003000000,
    "is_prerelease": false,
    "release_channel": "stable"
  }
}
```

### Field Reference

#### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | Yes | Unique identifier (lowercase, hyphens) |
| `name` | string | Yes | Display name |
| `description` | string | Yes | Brief description |
| `authors` | array | Yes | List of author names |
| `license` | string | Yes | SPDX license identifier |
| `tags` | array | No | Tags for filtering |
| `url` | string | Yes | URL to addon homepage (GitHub/GitLab page) |

#### Source Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Source type: `github`, `gitlab`, `custom` |
| `repo` | string | Repository path (e.g., `owner/repo`) |
| `branch` | string | Branch to track |
| `path` | string | Subdirectory path if addon is not at repo root (optional) |

#### Compatibility Object

| Field | Type | Description |
|-------|------|-------------|
| `api_version` | string | ESO API version (e.g., `"101048"`) |
| `game_versions` | array | Supported game updates (e.g., `["U45"]`) |
| `required_dependencies` | array | Slugs of required addons |
| `optional_dependencies` | array | Slugs of optional addons |

#### Latest Release Object

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Version tag/number (or short SHA for branch-based) |
| `download_url` | string | Direct download URL (ZIP archive) |
| `published_at` | string | ISO 8601 publish date (may be null for tags) |
| `commit_sha` | string | Full commit SHA for precise version tracking |
| `commit_date` | string | ISO 8601 commit date (branch-based only) |
| `commit_message` | string | First line of commit message, max 100 chars (branch-based only) |

#### Version Info Object (Client Convenience)

The `version_info` object provides pre-computed version metadata to simplify client logic for version comparison and display.

| Field | Type | Description |
|-------|------|-------------|
| `version_normalized` | object/null | Parsed semver components (null if unparseable or branch-based) |
| `version_sort_key` | integer/null | Sortable integer for version ordering (null for branch-based) |
| `is_prerelease` | boolean | True if version contains alpha/beta/rc/dev |
| `release_channel` | string | One of: `stable`, `prerelease`, `branch` |
| `commit_message` | string | Commit message (branch-based only) |

**version_normalized structure:**
```json
{
  "major": 1,
  "minor": 3,
  "patch": 0,
  "prerelease": null
}
```

**Supported version formats:**
- Standard semver: `1.0.0`, `v1.0.0`, `V1.0`
- Date-based: `2025.10.11`, `2025-12-28`
- Prefixed: `Version-1.13.1`, `version_2.0.0`
- Prerelease: `1.0.0-beta.1`, `2.0.0-rc1`
- Non-parseable (returns null): `r32`, commit SHAs

**version_sort_key formula:**
`major * 10^9 + minor * 10^6 + patch * 10^3 - (1 if prerelease else 0)`

This allows simple integer comparison: `addon1.version_sort_key > addon2.version_sort_key`

#### Download Sources Array

The `download_sources` array provides multiple download options in priority order, with jsDelivr CDN as the primary source and direct GitHub as fallback.

```json
{
  "download_sources": [
    {
      "type": "jsdelivr",
      "url": "https://cdn.jsdelivr.net/gh/brainsnorkel/WarMask@v1.3.0/",
      "note": "CDN - serves individual files, no rate limits, CORS-friendly"
    },
    {
      "type": "github_archive",
      "url": "https://github.com/brainsnorkel/WarMask/archive/refs/tags/v1.3.0.zip",
      "note": "Direct GitHub ZIP archive, subject to rate limits"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Source type: `jsdelivr` or `github_archive` |
| `url` | string | Base URL for downloads |
| `note` | string | Human-readable description of this source |

**Why jsDelivr first?**
- **No rate limits**: Unlike GitHub API (60 req/hour unauthenticated)
- **CORS-friendly**: Works in browser-based addon managers
- **Global CDN**: Fast downloads worldwide
- **Bypass restrictions**: Works even if GitHub is blocked (e.g., some countries/networks)
- **Cached**: Content cached at edge, reduces load on GitHub

**Important**: jsDelivr serves files individually (not as ZIP archives). See the download implementation section for details.

#### Install Object (Pipeline Instructions)

The `install` object provides clear, actionable instructions for addon manager clients. This is the "agent-99" approach - explicit pipeline steps rather than inferring behavior.

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | Archive type: `github_archive`, `github_release`, or `branch` |
| `extract_path` | string/null | Path within archive to extract (null = extract from root) |
| `target_folder` | string | Folder name to create in AddOns directory |
| `excludes` | array | Glob patterns for files to skip during extraction |

**Method values:**

| Method | Archive Structure | URL Pattern |
|--------|-------------------|-------------|
| `github_archive` | `{repo}-{tag}/` root folder | `/archive/refs/tags/{tag}.zip` |
| `github_release` | `{repo}-{tag}/` root folder | Release `zipball_url` |
| `branch` | `{repo}-{branch}/` root folder | `/archive/refs/heads/{branch}.zip` |

**Example: Standard addon (root-level)**
```json
{
  "install": {
    "method": "github_archive",
    "extract_path": null,
    "target_folder": "WarMask",
    "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"]
  }
}
```

**Example: Subdirectory addon (library)**
```json
{
  "install": {
    "method": "github_release",
    "extract_path": "LibAddonMenu-2.0",
    "target_folder": "LibAddonMenu-2.0",
    "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"]
  }
}
```

---

## Dependency Resolution

Dependencies are specified as **slugs** referencing other addons in the index.

### Resolution Algorithm

```
For each dependency_slug in addon.compatibility.required_dependencies:
    1. Search index.addons where slug == dependency_slug
    2. If found:
        - Dependency is available in index
        - Use latest_release.download_url to download
        - Recursively resolve that addon's dependencies
    3. If not found:
        - Dependency is NOT in this index
        - Inform user to install manually
        - Provide dependency_slug as identifier
```

### Example: Resolving Dependencies

```python
def resolve_dependencies(index, addon):
    """Resolve all dependencies for an addon."""
    resolved = []
    unresolved = []

    # Build slug -> addon lookup
    addon_map = {a["slug"]: a for a in index["addons"]}

    for dep_slug in addon["compatibility"].get("required_dependencies", []):
        if dep_slug in addon_map:
            dep_addon = addon_map[dep_slug]
            resolved.append({
                "slug": dep_slug,
                "name": dep_addon["name"],
                "download_url": dep_addon.get("latest_release", {}).get("download_url")
            })
            # Recursively resolve nested dependencies
            nested = resolve_dependencies(index, dep_addon)
            resolved.extend(nested["resolved"])
            unresolved.extend(nested["unresolved"])
        else:
            unresolved.append(dep_slug)

    return {"resolved": resolved, "unresolved": unresolved}
```

### Handling Unresolved Dependencies

When a dependency slug is not found in the index:

1. **Display to user**: Show the slug/name so they know what to install
2. **Suggest sources**: Common ESO addon sources include:
   - ESOUI: `https://www.esoui.com/`
   - Minion addon manager
3. **Allow override**: Let users proceed without the dependency (at their risk)

---

## Downloading and Installing Addons

### Install Pipeline

The `install` object provides explicit instructions. Follow this pipeline:

```
1. Read install.method to understand archive structure
2. Download ZIP from latest_release.download_url
3. Determine source path within ZIP:
   - If install.extract_path is null: use archive root
   - If install.extract_path is set: use that subdirectory
4. Extract to AddOns/{install.target_folder}/
5. Skip files matching install.excludes patterns
6. Verify addon manifest exists (.txt or .addon file with ## Title:)
```

### ESO AddOns Directory

| Platform | Path |
|----------|------|
| Windows | `%USERPROFILE%\Documents\Elder Scrolls Online\live\AddOns\` |
| macOS | `~/Documents/Elder Scrolls Online/live/AddOns/` |

### Complete Extraction Algorithm

```python
import fnmatch
import zipfile
from pathlib import Path

def extract_addon(zip_path: Path, addon: dict, addons_dir: Path):
    """Extract addon using install pipeline instructions."""
    install = addon["install"]

    with zipfile.ZipFile(zip_path) as zf:
        # All GitHub archives have a root folder: {repo}-{tag}/ or {repo}-{branch}/
        root_folder = zf.namelist()[0].split('/')[0]

        # Determine source prefix within ZIP
        if install["extract_path"]:
            # Subdirectory addon: extract from specific path
            source_prefix = f"{root_folder}/{install['extract_path']}/"
        else:
            # Root addon: extract from archive root
            source_prefix = f"{root_folder}/"

        # Target folder in AddOns directory
        target_folder = install["target_folder"]
        target_dir = addons_dir / target_folder

        for member in zf.namelist():
            if not member.startswith(source_prefix):
                continue

            relative_path = member[len(source_prefix):]
            if not relative_path:  # Skip directory entry itself
                continue

            # Check excludes
            if should_exclude(relative_path, install["excludes"]):
                continue

            # Extract file
            target_path = target_dir / relative_path
            if member.endswith('/'):
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())

def should_exclude(path: str, excludes: list) -> bool:
    """Check if path matches any exclude pattern."""
    for pattern in excludes:
        # Check each path component against pattern
        for part in Path(path).parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False
```

### Example: Installing LibAddonMenu

```python
# Addon metadata from index
addon = {
    "slug": "libaddonmenu",
    "install": {
        "method": "github_release",
        "extract_path": "LibAddonMenu-2.0",
        "target_folder": "LibAddonMenu-2.0",
        "excludes": [".*", ".github", "tests", "*.md"]
    },
    "latest_release": {
        "download_url": "https://api.github.com/repos/sirinsidiator/ESO-LibAddonMenu/zipball/2.4.0"
    }
}

# ZIP structure:
# ESO-LibAddonMenu-2.4.0/
# ├── README.md                    # excluded (*.md)
# ├── .github/                     # excluded (.*)
# └── LibAddonMenu-2.0/            # <-- extract_path
#     ├── LibAddonMenu-2.0.txt
#     └── LibAddonMenu-2.0.lua

# Result in AddOns directory:
# AddOns/LibAddonMenu-2.0/         # <-- target_folder
# ├── LibAddonMenu-2.0.txt
# └── LibAddonMenu-2.0.lua
```

---

## Download Strategy: jsDelivr with GitHub Fallback

The index provides multiple download sources via `download_sources`. Clients should try sources in order, falling back on failure.

### Recommended Download Flow

```
1. Try jsDelivr (primary)
   └─ Success? → Done
   └─ Failure? → Continue to fallback

2. Try GitHub archive (fallback)
   └─ Success? → Done
   └─ Failure? → Report error to user
```

### jsDelivr Download Implementation

jsDelivr serves files individually, not as ZIP archives. Two approaches:

#### Option A: Use jsDelivr's ZIP feature (Recommended)

jsDelivr can generate a ZIP of a directory by appending `?full` or using their API:

```
# Get directory listing as JSON
https://data.jsdelivr.com/v1/package/gh/{owner}/{repo}@{version}/flat

# Download all files as ZIP (unofficial but works)
https://cdn.jsdelivr.net/gh/{owner}/{repo}@{version}/?full
```

**Note**: The `?full` parameter is unofficial. For reliability, use Option B or fall back to GitHub archive.

#### Option B: Fetch file list and download individually

```python
import requests
from pathlib import Path

def download_via_jsdelivr(addon: dict, target_dir: Path) -> bool:
    """Download addon files from jsDelivr CDN."""
    jsdelivr_source = next(
        (s for s in addon.get("download_sources", []) if s["type"] == "jsdelivr"),
        None
    )
    if not jsdelivr_source:
        return False

    base_url = jsdelivr_source["url"].rstrip("/")
    repo = addon["source"]["repo"]
    version = addon["latest_release"]["version"]

    # Get file listing from jsDelivr API
    api_url = f"https://data.jsdelivr.com/v1/package/gh/{repo}@{version}/flat"
    resp = requests.get(api_url, timeout=10)
    if not resp.ok:
        return False

    files = resp.json().get("files", [])

    # Filter to addon path if subdirectory addon
    path_prefix = addon["source"].get("path", "")
    if path_prefix:
        files = [f for f in files if f["name"].startswith(f"/{path_prefix}/")]
        strip_prefix = f"/{path_prefix}"
    else:
        strip_prefix = ""

    # Download each file
    target_folder = target_dir / addon["install"]["target_folder"]
    for file_info in files:
        file_path = file_info["name"]
        if strip_prefix:
            relative_path = file_path[len(strip_prefix):].lstrip("/")
        else:
            relative_path = file_path.lstrip("/")

        # Skip excluded patterns
        if should_exclude(relative_path, addon["install"]["excludes"]):
            continue

        # Download file
        file_url = f"https://cdn.jsdelivr.net/gh/{repo}@{version}{file_path}"
        dest = target_folder / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        file_resp = requests.get(file_url, timeout=30)
        if file_resp.ok:
            dest.write_bytes(file_resp.content)

    return True
```

### GitHub Archive Fallback

If jsDelivr fails, fall back to the GitHub archive ZIP:

```python
def download_via_github(addon: dict, target_dir: Path) -> bool:
    """Download addon from GitHub archive (fallback)."""
    github_source = next(
        (s for s in addon.get("download_sources", []) if s["type"] == "github_archive"),
        None
    )
    if not github_source:
        # Use latest_release.download_url as legacy fallback
        download_url = addon.get("latest_release", {}).get("download_url")
        if not download_url:
            return False
    else:
        download_url = github_source["url"]

    # Download and extract ZIP
    resp = requests.get(download_url, timeout=60)
    if not resp.ok:
        return False

    # Use existing extraction logic
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = Path(tmp.name)

    try:
        extract_addon(tmp_path, addon, target_dir)
        return True
    finally:
        tmp_path.unlink()
```

### Complete Download Function

```python
def download_addon(addon: dict, addons_dir: Path) -> bool:
    """Download addon using available sources with fallback."""

    # Try jsDelivr first (no rate limits, CORS-friendly)
    try:
        if download_via_jsdelivr(addon, addons_dir):
            return True
    except Exception as e:
        print(f"jsDelivr failed for {addon['slug']}: {e}")

    # Fall back to GitHub archive
    try:
        if download_via_github(addon, addons_dir):
            return True
    except Exception as e:
        print(f"GitHub failed for {addon['slug']}: {e}")

    return False
```

### When to Use Each Source

| Source | Best For | Limitations |
|--------|----------|-------------|
| **jsDelivr** | Browser clients, rate-limited environments, China/restricted networks | ~24hr cache delay for branch updates |
| **GitHub Archive** | Desktop clients, guaranteed ZIP format, immediate updates | Rate limited (60/hr unauth), may be blocked |

---

## Caching Recommendations

### Index Caching

- Cache `index.json` locally with `generated_at` timestamp
- Refresh when:
  - User manually requests update
  - Cache is older than 1 hour (suggested)
  - On application startup (background refresh)

### Conditional Requests

Use HTTP conditional requests to minimize bandwidth:

```
GET /eso-addon-index/index.json
If-Modified-Since: Sat, 28 Dec 2024 10:30:00 GMT
```

GitHub Pages supports `Last-Modified` headers.

---

## Error Handling

### Network Errors

- Retry with exponential backoff
- Fall back to cached index if available
- Show user-friendly error message

### Missing Fields

- Treat missing optional fields as empty/null
- `latest_release` may be null if no releases exist
- `published_at` may be null for tag-based releases

### Invalid Data

- Validate `slug` format: lowercase, alphanumeric, hyphens
- Validate URLs before attempting download
- Handle malformed JSON gracefully

---

## Rate Limiting

### By Source

| Source | Rate Limit | Notes |
|--------|------------|-------|
| **Index (GitHub Pages)** | None | Static files, no API limits |
| **jsDelivr CDN** | None | Designed for high traffic |
| **jsDelivr API** | Generous | File listings at `data.jsdelivr.com` |
| **GitHub Archive** | ~60/hour | Unauthenticated; 5000/hour with token |
| **GitHub API** | ~60/hour | For release info queries |

### Recommendations

1. **Use jsDelivr as primary download source** - no rate limits
2. **Cache the index locally** - reduces repeated fetches
3. **Batch GitHub operations** - if using GitHub directly
4. **Implement exponential backoff** - for rate limit errors (HTTP 429)

---

## Example Client Flow

```
1. Fetch index.json
2. Display addon list to user (searchable, filterable by tags)
3. User selects addon to install
4. Resolve dependencies:
   - Show resolved dependencies that will be installed
   - Warn about unresolved dependencies
5. User confirms installation
6. Download addon ZIP from latest_release.download_url
7. Download resolved dependency ZIPs
8. Extract all to AddOns directory
9. Prompt user to /reloadui or restart ESO
```

---

## Addon Release Types and Packaging

Addons in the index use different release strategies and packaging structures. Understanding these is essential for correctly downloading and installing addons.

### Release Types

The `release_type` field in addon metadata determines how new versions are detected:

| Type | Description | Download Source |
|------|-------------|-----------------|
| `tag` | Git tags (e.g., `v1.0.0`, `1.2.3`) | `https://github.com/{repo}/archive/refs/tags/{tag}.zip` |
| `release` | GitHub Releases (formal releases with notes) | Release `zipball_url` from GitHub API |
| `branch` | Latest commit on a branch | `https://github.com/{repo}/archive/refs/heads/{branch}.zip` |

**Examples from the index:**
- **Tag-based**: WarMask uses `release_type = "tag"` - versions are git tags like `1.0.0`
- **Release-based**: LibAddonMenu uses `release_type = "release"` - uses formal GitHub Releases with changelogs
- **Branch-based**: CrutchAlerts uses `release_type = "branch"` - tracks latest commits on `master`

**Polling behavior:**
- `tag`/`release`: Stable versioning, checked daily for new versions
- `branch`: Rolling releases, version is the commit SHA or timestamp

### Packaging Structures

Addons are packaged in two ways within their source repositories:

#### 1. Root-level Addons

The addon manifest (`.txt` file with `## Title:`) is at the repository root.

```
repo-root/
├── AddonName.txt         # Manifest file
├── AddonName.lua         # Main code
└── libs/                 # Optional libraries
```

**Download flow:**
1. Download ZIP from `latest_release.download_url`
2. ZIP contains `{repo}-{tag}/` folder
3. Extract contents to `AddOns/{slug}/`

#### 2. Subdirectory Addons

The addon lives in a subdirectory, indicated by `source.path`. Common for libraries that share a repository with other projects.

```
repo-root/
├── README.md
├── LibAddonMenu-2.0/     # <-- source.path points here
│   ├── LibAddonMenu-2.0.txt
│   └── LibAddonMenu-2.0.lua
└── other-files/
```

**Download flow:**
1. Download ZIP from `latest_release.download_url`
2. ZIP contains `{repo}-{tag}/LibAddonMenu-2.0/`
3. Extract **only** the `source.path` folder to `AddOns/LibAddonMenu-2.0/`
4. The subdirectory becomes a top-level folder in AddOns, not nested

### Release Detection Logic

The build system (`scripts/poll-releases.py`) uses this priority:

1. If `release_type = "release"`: Query GitHub Releases API
   - Falls back to tags if no releases exist
2. If `release_type = "tag"`: Query GitHub Tags API
   - Uses the first (most recent) tag
3. If `release_type = "branch"`: Track branch HEAD (not yet implemented)

**Version cache** (`public/versions.json`) stores:
```json
{
  "versions": {
    "warmask": {
      "version": "1.0.0",
      "download_url": "https://github.com/.../1.0.0.zip",
      "published_at": "2024-12-01T12:00:00Z"
    }
  },
  "last_checked": "2024-12-28T06:00:00+00:00"
}
```

---

## Version Comparison

### Using version_sort_key

For addons with parseable versions, use `version_sort_key` for simple comparison:

```python
def is_newer_version(addon_a, addon_b):
    """Check if addon_a is newer than addon_b."""
    key_a = addon_a.get("version_info", {}).get("version_sort_key")
    key_b = addon_b.get("version_info", {}).get("version_sort_key")

    if key_a is None or key_b is None:
        return None  # Cannot compare

    return key_a > key_b
```

### Comparing Branch-Based Addons

For branch-based addons (`release_channel == "branch"`), compare using `commit_sha`:

```python
def has_branch_update(cached_addon, index_addon):
    """Check if a branch-based addon has a new commit."""
    cached_sha = cached_addon.get("latest_release", {}).get("commit_sha")
    current_sha = index_addon.get("latest_release", {}).get("commit_sha")

    return cached_sha != current_sha
```

### Mixed Comparison Strategy

```python
def check_for_update(installed, latest):
    """Check if an addon has an update available."""
    channel = latest.get("version_info", {}).get("release_channel")

    if channel == "branch":
        # Compare commit SHAs
        return installed.get("commit_sha") != latest.get("latest_release", {}).get("commit_sha")
    else:
        # Compare version sort keys
        installed_key = installed.get("version_sort_key")
        latest_key = latest.get("version_info", {}).get("version_sort_key")

        if installed_key and latest_key:
            return latest_key > installed_key

        # Fallback to string comparison
        return installed.get("version") != latest.get("latest_release", {}).get("version")
```

---

## Missing Dependencies Feed

The `missing-dependencies.json` endpoint lists dependencies that are referenced by addons in the index but are not themselves available in the index. This is useful for:

- Identifying addons that should be added to complete the dependency graph
- Warning users about dependencies they'll need to install manually
- Tracking dependency naming inconsistencies (e.g., "LibAddonMenu-2.0" vs "libaddonmenu")

### Missing Dependencies Structure

```json
{
  "version": "1.0",
  "generated_at": "2024-12-30T10:30:00+00:00",
  "description": "Dependencies referenced by addons but not available in the index",
  "missing_count": 4,
  "missing_dependencies": [...]
}
```

### Missing Dependency Object

```json
{
  "slug": "LibDebugLogger",
  "slug_normalized": "libdebuglogger",
  "dependency_type": "optional",
  "needed_by": [
    {"slug": "combatmetrics", "name": "CombatMetrics"},
    {"slug": "libcombat", "name": "LibCombat"}
  ],
  "needed_by_count": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | Original dependency name as specified in addon TOML |
| `slug_normalized` | string | Lowercase version for case-insensitive matching |
| `dependency_type` | string | One of: `required`, `optional`, or `required+optional` |
| `needed_by` | array | List of addons that depend on this |
| `needed_by_count` | integer | Number of addons requiring this dependency |

### Usage Example

```python
def warn_about_missing_deps(addon, missing_deps):
    """Warn user about dependencies not in the index."""
    missing_lookup = {d["slug_normalized"]: d for d in missing_deps["missing_dependencies"]}

    for dep in addon["compatibility"].get("required_dependencies", []):
        if dep.lower() in missing_lookup:
            missing = missing_lookup[dep.lower()]
            print(f"Warning: '{dep}' is not in the addon index.")
            print(f"  You may need to install it manually from ESOUI or another source.")
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.7 | 2024-12-30 | Added `download_sources` array with jsDelivr CDN as primary, GitHub as fallback |
| 1.6 | 2024-12-30 | Added `missing-dependencies.json` endpoint for unavailable dependencies |
| 1.5 | 2024-12-30 | Removed `category` field and `categories.json` endpoint |
| 1.4 | 2024-12-29 | Added `version_info` object with normalized versions, sort keys, and release channels |
| 1.3 | 2024-12-29 | Added `install` object with explicit pipeline instructions |
| 1.2 | 2024-12-29 | Added release types and packaging documentation |
| 1.1 | 2024-12-28 | Added `source.path` for subdirectory addons |
| 1.0 | 2024-12-28 | Initial client documentation |
