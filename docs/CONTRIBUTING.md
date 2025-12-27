# Contributing to ESO Addon Index

Thank you for your interest in contributing to the ESO Addon Index! This document explains how to submit addons and contribute to the project.

## Submitting an Addon

There are two ways to submit an addon:

### Option 1: Issue Template (Recommended for beginners)

1. Go to [Issues](https://github.com/brainsnorkel/eso-addon-index/issues/new/choose)
2. Select "Addon Submission"
3. Fill out the form with your addon details
4. A maintainer will create the TOML file and open a PR

### Option 2: Pull Request (For experienced contributors)

1. Fork the repository
2. Create a new directory: `addons/[your-addon-slug]/`
3. Add an `addon.toml` file (see [SCHEMA.md](SCHEMA.md) for format)
4. Submit a pull request

## Addon Requirements

Your addon must meet these requirements:

### Repository Requirements

- [ ] Publicly accessible GitHub or GitLab repository
- [ ] Contains a valid ESO addon manifest (`.txt` file with `## Title:`)
- [ ] Has at least one release or tag
- [ ] No obvious malicious code

### Metadata Requirements

- [ ] Unique slug (lowercase, alphanumeric, hyphens only)
- [ ] Accurate description
- [ ] Correct category
- [ ] Valid author information
- [ ] Current ESO API version compatibility

## TOML File Format

Create `addons/[slug]/addon.toml`:

```toml
[addon]
slug = "my-addon"
name = "My Addon"
description = "What the addon does"
authors = ["your-username"]
license = "MIT"
category = "combat"
tags = ["pvp", "combat"]

[source]
type = "github"
repo = "username/repo-name"
branch = "main"
release_type = "tag"

[compatibility]
api_version = "101048"
game_versions = ["U45"]
required_dependencies = []
optional_dependencies = []

[meta]
submitted_by = "your-username"
submitted_date = 2024-12-27
status = "pending"
```

## Review Process

1. Automated checks run on your PR:
   - TOML schema validation
   - Repository accessibility
   - ESO manifest detection
   - Luacheck static analysis
   - Security pattern scan

2. A maintainer reviews your submission
3. Address any feedback
4. PR merged after approval

## Categories

Choose the most appropriate category:

| Category | Description |
|----------|-------------|
| `combat` | Combat-related features, damage meters, buffs |
| `crafting` | Crafting assistance, research tracking |
| `dungeons` | Dungeon/trial helpers, mechanics |
| `guilds` | Guild management, rosters |
| `housing` | Housing features, furniture |
| `inventory` | Inventory management, bag tools |
| `library` | Shared libraries for other addons |
| `maps` | Map enhancements, navigation |
| `miscellaneous` | Other addons |
| `pvp` | PvP-specific features |
| `quests` | Quest tracking, objectives |
| `roleplay` | RP tools, emotes |
| `social` | Chat, friends, communication |
| `trading` | Trading, guild stores, pricing |
| `ui` | UI modifications, themes |

## Code of Conduct

- Be respectful and constructive
- No malicious or harmful addons
- Credit original authors appropriately
- Follow ESO's Terms of Service

## Questions?

Open an issue or reach out to the maintainers.
