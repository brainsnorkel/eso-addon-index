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

# Primary category (choose one)
category = "combat"  # required, see categories below

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

## Categories

| Value | Description |
|-------|-------------|
| `combat` | Combat tracking, damage meters, buff monitoring |
| `crafting` | Crafting helpers, research tracking, writs |
| `dungeons` | Dungeon/trial mechanics, timers |
| `guilds` | Guild management, rosters, events |
| `housing` | Housing tools, furniture management |
| `inventory` | Bag management, item tracking |
| `library` | Shared libraries for other addons |
| `maps` | Map enhancements, pins, navigation |
| `miscellaneous` | Other addons |
| `pvp` | PvP features, Cyrodiil, Battlegrounds |
| `quests` | Quest tracking, objectives |
| `roleplay` | RP tools, emotes, character bios |
| `social` | Chat enhancements, friends, communication |
| `trading` | Guild stores, pricing, trading |
| `ui` | Interface modifications, themes |

## Validation Rules

### Slug
- Lowercase letters, numbers, and hyphens only
- Must match parent directory name
- Must be unique across all addons
- Cannot be empty

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
tags = ["pvp", "combat", "buff-tracking", "mythic"]

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

## JSON Output Format

The built index transforms TOML to JSON:

```json
{
  "slug": "warmask",
  "name": "WarMask",
  "description": "Tracks Mark of Hircine...",
  "authors": ["brainsnorkel"],
  "license": "MIT",
  "category": "combat",
  "tags": ["pvp", "combat"],
  "source": {
    "type": "github",
    "repo": "brainsnorkel/WarMask",
    "branch": "master"
  },
  "compatibility": {
    "api_version": "101048",
    "game_versions": ["U45"],
    "required_dependencies": ["LibAddonMenu-2.0"],
    "optional_dependencies": []
  },
  "latest_release": {
    "version": "v1.3.0",
    "download_url": "https://github.com/brainsnorkel/WarMask/archive/refs/tags/v1.3.0.zip",
    "published_at": "2024-12-22T01:15:43Z"
  }
}
```
