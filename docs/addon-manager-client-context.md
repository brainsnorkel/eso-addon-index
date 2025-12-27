# Addon Manager Client Integration Guide

This document describes how client applications (addon managers, installers, etc.) should consume the ESO Addon Index API.

---

## Index Endpoints

| Endpoint | Description |
|----------|-------------|
| `https://xop.co/eso-addon-index/index.json` | Full addon index with formatting |
| `https://xop.co/eso-addon-index/index.min.json` | Minified index (smaller payload) |
| `https://xop.co/eso-addon-index/categories.json` | Addons grouped by category |
| `https://xop.co/eso-addon-index/feed.json` | JSON Feed format for updates |

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
  "category": "combat",
  "tags": ["pvp", "combat", "buff-tracking"],
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
  "latest_release": {
    "version": "1.0.0",
    "download_url": "https://github.com/brainsnorkel/WarMask/archive/refs/tags/1.0.0.zip",
    "published_at": "2024-12-01T12:00:00Z"
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
| `category` | string | Yes | Primary category |
| `tags` | array | No | Additional tags for filtering |

#### Source Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Source type: `github`, `gitlab`, `custom` |
| `repo` | string | Repository path (e.g., `owner/repo`) |
| `branch` | string | Branch to track |

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
| `version` | string | Version tag/number |
| `download_url` | string | Direct download URL (ZIP archive) |
| `published_at` | string | ISO 8601 publish date (may be null for tags) |

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

## Downloading Addons

### Download Flow

1. Fetch `latest_release.download_url`
2. Download ZIP archive
3. Extract to ESO AddOns directory
4. Verify addon manifest exists (`.txt` file with `## Title:`)

### ESO AddOns Directory

| Platform | Path |
|----------|------|
| Windows | `%USERPROFILE%\Documents\Elder Scrolls Online\live\AddOns\` |
| macOS | `~/Documents/Elder Scrolls Online/live/AddOns/` |

### ZIP Structure

GitHub release ZIPs contain a root folder named `{repo}-{tag}/`. Clients should:

1. Extract ZIP contents
2. Locate the addon folder (contains `.txt` manifest)
3. Move/rename to match the addon's expected folder name
4. Place in ESO AddOns directory

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

## Categories

Valid category values:

```
combat, crafting, dungeons, guilds, housing, inventory, library,
maps, miscellaneous, pvp, quests, roleplay, social, trading, ui
```

Use `categories.json` for a pre-grouped listing.

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

- Index is served via GitHub Pages (no strict rate limits)
- Download URLs point to GitHub releases (subject to GitHub rate limits)
- For unauthenticated requests: ~60 requests/hour to GitHub API
- Recommendation: Batch downloads, implement request queuing

---

## Example Client Flow

```
1. Fetch index.json
2. Display addon list to user (searchable, filterable by category/tags)
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

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-28 | Initial client documentation |
