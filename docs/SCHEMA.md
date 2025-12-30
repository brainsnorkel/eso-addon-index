# Addon Metadata Schema

This document describes the TOML schema for addon metadata files.

## File Location

Each addon has a single TOML file at:
```
addons/[slug]/addon.toml
```

The `slug` must match the directory name.

## Complete Schema

```toml
# =============================================================================
# [addon] - Required
# Core addon information
# =============================================================================
[addon]
# Unique identifier
# - lowercase letters, numbers, and hyphens only
# - must match parent directory name
# - cannot be changed after approval
slug = "my-addon"  # required

# Display name shown to users
name = "My Addon"  # required

# Brief description (1-2 sentences)
description = "What this addon does"  # required

# List of author names or GitHub usernames
authors = ["author1", "author2"]  # required, at least one

# SPDX license identifier
# See: https://spdx.org/licenses/
license = "MIT"  # optional, defaults to "Unknown"

# Primary category for classification
# Valid: combat, crafting, dungeons, guilds, housing, inventory,
#        library, maps, miscellaneous, pvp, quests, roleplay, social, trading, ui
category = "combat"  # required

# Tags for search/filtering
tags = ["pvp", "buff-tracking"]  # optional

# =============================================================================
# [source] - Required
# Where the addon code lives
# =============================================================================
[source]
# Source type
type = "github"  # required: github | gitlab | custom

# Repository path (owner/repo format)
repo = "username/repo-name"  # required

# Branch to track
branch = "main"  # optional, defaults to repo's default branch

# Subdirectory path if addon is not at repo root
# Example: "LibAddonMenu-2.0" for sirinsidiator/ESO-LibAddonMenu
path = "LibAddonMenu-2.0"  # optional, omit if addon is at repo root

# Target folder name in AddOns directory
# Defaults to: path > name
install_folder = "LibAddonMenu-2.0"  # optional

# How to detect new versions
release_type = "tag"  # optional: tag | release | branch

# =============================================================================
# [compatibility] - Optional
# ESO version compatibility information
# =============================================================================
[compatibility]
# ESO API version string
api_version = "101048"  # optional

# Supported game updates
game_versions = ["U45", "U44"]  # optional

# Required addon dependencies
required_dependencies = ["LibAddonMenu-2.0"]  # optional

# Optional addon dependencies
optional_dependencies = ["LibStub"]  # optional

# =============================================================================
# [meta] - Required
# Index management metadata
# =============================================================================
[meta]
# GitHub username of submitter
submitted_by = "username"  # required

# Submission date (YYYY-MM-DD)
submitted_date = 2024-12-27  # optional

# Last review date
last_reviewed = 2024-12-27  # optional

# Current status
status = "pending"  # required: pending | approved | deprecated | removed

# List of reviewer usernames
reviewers = ["reviewer1"]  # optional
```

## Validation Rules

### Slug
- Lowercase letters, numbers, and hyphens only
- Must match parent directory name
- Must be unique across all addons
- Cannot be empty

#### Slug Transformation Rules

When deriving a slug from an addon name:

1. Convert to lowercase
2. Replace periods (`.`) with hyphens (`-`)
3. Replace spaces with hyphens
4. Remove any characters that aren't alphanumeric or hyphens

**Examples:**
| Addon Name | Slug |
|------------|------|
| `WarMask` | `warmask` |
| `LibAddonMenu-2.0` | `libaddonmenu-2-0` |
| `Combat Metrics` | `combat-metrics` |
| `Awesome_Addon` | `awesome-addon` |

**Client Implementation (JavaScript):**
```javascript
function nameToSlug(name) {
  return name
    .toLowerCase()
    .replace(/\./g, '-')
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}
```

### Repository
- Must be publicly accessible
- Must contain ESO addon manifest (`.txt` with `## Title:`)
- Must have at least one release or tag

### API Version
- Must be numeric string (e.g., "101048")
- Should match current or recent ESO version

## Example: Minimal

```toml
[addon]
slug = "simple-addon"
name = "Simple Addon"
description = "A simple example addon"
authors = ["developer"]
category = "miscellaneous"

[source]
type = "github"
repo = "developer/simple-addon"

[meta]
submitted_by = "developer"
status = "pending"
```

## Example: Complete

```toml
[addon]
slug = "warmask"
name = "WarMask"
description = "Tracks Mark of Hircine from Huntsman's Warmask. Shows icon when buff is active, countdown when bash is applied to target."
authors = ["brainsnorkel"]
license = "MIT"
category = "combat"
tags = ["pvp", "buff-tracking", "mythic"]

[source]
type = "github"
repo = "brainsnorkel/WarMask"
branch = "master"
release_type = "tag"

[compatibility]
api_version = "101048"
game_versions = ["U45"]
required_dependencies = ["LibAddonMenu-2.0"]
optional_dependencies = []

[meta]
submitted_by = "brainsnorkel"
submitted_date = 2024-12-27
last_reviewed = 2024-12-27
status = "approved"
reviewers = ["brainsnorkel"]
```

## Example: Subdirectory Addon

For addons that live in a subdirectory of their repository (common for libraries):

```toml
[addon]
slug = "libaddonmenu-2-0"  # Note: dots become hyphens in slugs
name = "LibAddonMenu-2.0"
description = "A library that provides a settings/options menu for addons."
authors = ["sirinsidiator", "Seerah"]
license = "Artistic-2.0"
category = "library"
tags = ["settings", "menu"]

[source]
type = "github"
repo = "sirinsidiator/ESO-LibAddonMenu"
branch = "master"
path = "LibAddonMenu-2.0"  # Addon files are in this subdirectory
release_type = "release"

[compatibility]
api_version = "101048"
game_versions = ["U45"]
required_dependencies = []
optional_dependencies = []

[meta]
submitted_by = "maintainer"
submitted_date = 2024-12-28
status = "pending"
```

## JSON Output Format

The built index transforms TOML to JSON with additional auto-generated fields:

```json
{
  "slug": "warmask",
  "name": "WarMask",
  "description": "Tracks Mark of Hircine...",
  "authors": ["brainsnorkel"],
  "license": "MIT",
  "tags": ["pvp", "combat"],
  "url": "https://github.com/brainsnorkel/WarMask",
  "last_updated": "2024-12-22T01:15:43Z",
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
    "download_url": "https://github.com/.../v1.3.0.zip",
    "published_at": "2024-12-22T01:15:43Z",
    "commit_sha": "abc123def456..."
  },
  "download_sources": [
    {
      "type": "jsdelivr",
      "url": "https://cdn.jsdelivr.net/gh/brainsnorkel/WarMask@v1.3.0/",
      "note": "CDN - serves individual files, no rate limits, CORS-friendly"
    },
    {
      "type": "github_archive",
      "url": "https://github.com/.../v1.3.0.zip",
      "note": "Direct GitHub ZIP archive, subject to rate limits"
    }
  ],
  "version_info": {
    "version_normalized": {"major": 1, "minor": 3, "patch": 0, "prerelease": null},
    "version_sort_key": 1003000000,
    "is_prerelease": false,
    "release_channel": "stable"
  }
}
```

### Auto-Generated Fields

| Field | Description |
|-------|-------------|
| `url` | Homepage URL derived from source type and repo |
| `last_updated` | ISO 8601 timestamp of when the addon was last changed (version or metadata) |
| `install` | Pipeline instructions for addon managers |
| `download_sources` | Array of download URLs (jsDelivr primary, GitHub fallback) |
| `latest_release` | Version info fetched from GitHub |
| `version_info` | Pre-computed version metadata for client convenience |

### Subdirectory Addon Output

For addons in subdirectories, `path` is included in source and used for jsDelivr URLs:

```json
{
  "slug": "libaddonmenu-2-0",
  "name": "LibAddonMenu-2.0",
  "source": {
    "type": "github",
    "repo": "sirinsidiator/ESO-LibAddonMenu",
    "branch": "master",
    "path": "LibAddonMenu-2.0"
  },
  "install": {
    "method": "github_release",
    "extract_path": "LibAddonMenu-2.0",
    "target_folder": "LibAddonMenu-2.0",
    "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"]
  },
  "download_sources": [
    {
      "type": "jsdelivr",
      "url": "https://cdn.jsdelivr.net/gh/sirinsidiator/ESO-LibAddonMenu@r32/LibAddonMenu-2.0/",
      "note": "CDN - serves individual files, no rate limits, CORS-friendly"
    }
  ]
}
```
