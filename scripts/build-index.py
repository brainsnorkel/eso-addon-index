#!/usr/bin/env python3
"""Compile addon TOML files into a single JSON index."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    import tomllib
except ImportError:
    import tomli as tomllib

OUTPUT_DIR = Path("public")
ADDONS_DIR = Path("addons")

# GitHub API headers
GITHUB_HEADERS = {}
if token := os.environ.get("GITHUB_TOKEN"):
    GITHUB_HEADERS["Authorization"] = f"token {token}"


def load_toml(filepath: Path) -> dict | None:
    """Load and parse a TOML file."""
    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}")
        return None


def fetch_latest_release(source: dict) -> dict | None:
    """Fetch latest release info from GitHub."""
    if source.get("type") != "github":
        return None

    repo = source.get("repo", "")
    release_type = source.get("release_type", "tag")

    try:
        if release_type == "release":
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)

            if not resp.ok:
                # Try tags as fallback
                return fetch_latest_tag(repo)

            data = resp.json()
            return {
                "version": data.get("tag_name", "unknown"),
                "download_url": data.get("zipball_url"),
                "published_at": data.get("published_at"),
            }
        else:
            return fetch_latest_tag(repo)

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch release for {repo}: {e}")
        return None


def fetch_latest_tag(repo: str) -> dict | None:
    """Fetch the latest tag from a GitHub repository."""
    url = f"https://api.github.com/repos/{repo}/tags"

    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)
        if not resp.ok:
            return None

        tags = resp.json()
        if not tags:
            return None

        latest_tag = tags[0]
        tag_name = latest_tag["name"]

        return {
            "version": tag_name,
            "download_url": f"https://github.com/{repo}/archive/refs/tags/{tag_name}.zip",
            "published_at": None,  # Tags don't have publish dates
        }

    except requests.RequestException:
        return None


def build_addon_url(source: dict) -> str:
    """Build the addon URL from source info."""
    source_type = source.get("type", "github")
    repo = source.get("repo", "")

    if source_type == "github":
        return f"https://github.com/{repo}"
    elif source_type == "gitlab":
        return f"https://gitlab.com/{repo}"
    else:
        # For custom sources, return repo as-is (may be a full URL)
        return repo


def build_install_info(source: dict, addon: dict) -> dict:
    """Build install pipeline instructions for addon manager clients.

    Provides clear, actionable steps for clients to:
    1. Understand the archive format (method)
    2. Know what to extract from the archive (extract_path)
    3. Know what folder name to use in AddOns/ (target_folder)
    4. Know what files to exclude (excludes)

    Archive structure notes:
    - github_archive: ZIP from /archive/refs/tags/ has {repo}-{tag}/ root folder
    - github_release: ZIP from release zipball has similar structure
    - branch: ZIP from /archive/refs/heads/ has {repo}-{branch}/ root folder

    All GitHub archives have a root folder that should be stripped.
    """
    release_type = source.get("release_type", "tag")
    source_path = source.get("path")

    # Determine install method based on release type
    if release_type == "branch":
        method = "branch"
    elif release_type == "release":
        method = "github_release"
    else:
        method = "github_archive"

    # Determine target folder name (priority: install_folder > path > name)
    install_folder = source.get("install_folder")
    if install_folder:
        target_folder = install_folder
    elif source_path:
        target_folder = source_path
    else:
        target_folder = addon["name"]

    return {
        "method": method,
        "extract_path": source_path if source_path else None,
        "target_folder": target_folder,
        "excludes": [".*", ".github", "tests", "*.md", "*.yml", "*.yaml"],
    }


def build_addon_entry(data: dict, fetch_releases: bool = True) -> dict:
    """Build a single addon entry for the index."""
    addon = data["addon"]
    source = data["source"]
    compatibility = data.get("compatibility", {})

    source_entry = {
        "type": source["type"],
        "repo": source["repo"],
        "branch": source.get("branch", "main"),
    }

    # Include path only if addon is in a subdirectory
    if source.get("path"):
        source_entry["path"] = source["path"]

    entry = {
        "slug": addon["slug"],
        "name": addon["name"],
        "description": addon["description"],
        "authors": addon["authors"],
        "license": addon.get("license", "Unknown"),
        "category": addon["category"],
        "tags": addon.get("tags", []),
        "url": build_addon_url(source),
        "source": source_entry,
        "compatibility": {
            "api_version": compatibility.get("api_version"),
            "game_versions": compatibility.get("game_versions", []),
            "required_dependencies": compatibility.get("required_dependencies", []),
            "optional_dependencies": compatibility.get("optional_dependencies", []),
        },
        "install": build_install_info(source, addon),
    }

    if fetch_releases:
        entry["latest_release"] = fetch_latest_release(source)

    return entry


def build_index(fetch_releases: bool = True) -> dict:
    """Build the complete addon index."""
    addons = []

    for toml_path in sorted(ADDONS_DIR.glob("*/addon.toml")):
        data = load_toml(toml_path)
        if data is None:
            continue

        # Skip non-approved addons
        status = data.get("meta", {}).get("status", "pending")
        if status != "approved":
            print(f"Skipping {toml_path.parent.name}: status is '{status}'")
            continue

        print(f"Processing: {toml_path.parent.name}")
        entry = build_addon_entry(data, fetch_releases=fetch_releases)
        addons.append(entry)

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "addon_count": len(addons),
        "addons": sorted(addons, key=lambda x: x["name"].lower()),
    }


def build_json_feed(index: dict) -> dict:
    """Build JSON Feed format for feed readers."""
    items = []

    for addon in index["addons"]:
        release = addon.get("latest_release") or {}
        repo = addon["source"]["repo"]

        items.append({
            "id": addon["slug"],
            "title": f"{addon['name']} {release.get('version', '')}".strip(),
            "url": f"https://github.com/{repo}",
            "date_published": release.get("published_at"),
            "authors": [{"name": a} for a in addon["authors"]],
            "summary": addon["description"],
            "tags": addon["tags"],
        })

    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "ESO Addon Index",
        "home_page_url": "https://github.com/brainsnorkel/eso-addon-index",
        "feed_url": "https://xop.co/eso-addon-index/feed.json",
        "items": items,
    }


def build_category_index(index: dict) -> dict:
    """Build an index grouped by category."""
    categories = {}

    for addon in index["addons"]:
        category = addon["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(addon["slug"])

    return {
        "version": "1.0",
        "generated_at": index["generated_at"],
        "categories": dict(sorted(categories.items())),
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build ESO addon index from TOML files")
    parser.add_argument(
        "--no-releases",
        action="store_true",
        help="Skip fetching release information (faster)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for JSON files",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(exist_ok=True)

    print("Building addon index...")
    print()

    # Build main index
    index = build_index(fetch_releases=not args.no_releases)

    # Write full index
    index_path = output_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Wrote: {index_path}")

    # Write minified index
    min_path = output_dir / "index.min.json"
    with open(min_path, "w") as f:
        json.dump(index, f, separators=(",", ":"))
    print(f"Wrote: {min_path}")

    # Write JSON Feed
    feed = build_json_feed(index)
    feed_path = output_dir / "feed.json"
    with open(feed_path, "w") as f:
        json.dump(feed, f, indent=2)
    print(f"Wrote: {feed_path}")

    # Write category index
    categories = build_category_index(index)
    cat_path = output_dir / "categories.json"
    with open(cat_path, "w") as f:
        json.dump(categories, f, indent=2)
    print(f"Wrote: {cat_path}")

    print()
    print(f"Built index with {index['addon_count']} addon(s)")


if __name__ == "__main__":
    main()
