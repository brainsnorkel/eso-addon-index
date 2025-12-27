# ESO Addon Index

A curated, peer-reviewed registry of Elder Scrolls Online addon metadata.

**[View the Index](https://xop.co/eso-addon-index/index.json)** | **[JSON Feed](https://xop.co/eso-addon-index/feed.json)**

## About

This repository maintains a curated index of ESO addon metadata. The index stores only metadata—addon source code remains in author-owned repositories.

### Features

- **Curated Registry**: Peer-reviewed addon submissions
- **Automated Updates**: Daily polling for new versions
- **Static JSON API**: Published via GitHub Pages
- **Security Scanning**: Automated checks for suspicious patterns

## For Addon Authors

### Submit Your Addon

1. **Via Issue**: [Open an Addon Submission](https://github.com/brainsnorkel/eso-addon-index/issues/new?template=addon-submission.yml)
2. **Via PR**: Fork the repo and add `addons/[slug]/addon.toml`

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

### Requirements

- Public GitHub/GitLab repository
- Valid ESO addon manifest (`.txt` with `## Title:`)
- At least one release or tag
- No malicious code

## For Developers

### Using the Index

```bash
# Full index
curl https://xop.co/eso-addon-index/index.json

# Minified
curl https://xop.co/eso-addon-index/index.min.json

# JSON Feed (for feed readers)
curl https://xop.co/eso-addon-index/feed.json

# Categories
curl https://xop.co/eso-addon-index/categories.json
```

### Index Format

```json
{
  "version": "1.0",
  "generated_at": "2024-12-27T10:00:00Z",
  "addon_count": 1,
  "addons": [
    {
      "slug": "warmask",
      "name": "WarMask",
      "description": "Tracks Mark of Hircine...",
      "authors": ["brainsnorkel"],
      "category": "combat",
      "source": {
        "type": "github",
        "repo": "brainsnorkel/WarMask"
      },
      "latest_release": {
        "version": "v1.3.0",
        "download_url": "https://github.com/..."
      }
    }
  ]
}
```

## Local Development

```bash
# Clone repository
git clone https://github.com/brainsnorkel/eso-addon-index.git
cd eso-addon-index

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Validate an addon
python scripts/validate.py addons/warmask/addon.toml

# Build the index
python scripts/build-index.py
```

## Documentation

- [Contributing Guide](docs/CONTRIBUTING.md)
- [Review Process](docs/REVIEW_PROCESS.md)
- [Schema Reference](docs/SCHEMA.md)

## License

MIT License - See [LICENSE](LICENSE) for details.
