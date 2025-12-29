#!/usr/bin/env python3
"""Compile addon TOML files into a single JSON index."""
from __future__ import annotations

import json
import os
import re
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


# Version parsing regex - handles v1.0.0, 1.0.0, 1.0, 1.0.0-beta.1, etc.
VERSION_REGEX = re.compile(
    r"^(?:version[_-]?)?"  # Optional 'version-' or 'Version_' prefix
    r"[vV]?"  # Optional 'v' or 'V' prefix
    r"(?P<major>\d+)"  # Major version (required)
    r"(?:[.\-](?P<minor>\d+))?"  # Minor version (optional, . or -)
    r"(?:[.\-](?P<patch>\d+))?"  # Patch version (optional, . or -)
    r"(?:[._-]?(?P<prerelease>(?:alpha|beta|rc|dev|pre|a|b)[\d.]*))?",  # Prerelease
    re.IGNORECASE,
)


def parse_version(version_str: str | None) -> dict | None:
    """Parse a version string into semver components.

    Handles various version formats:
    - Standard: 1.0.0, v1.0.0, V1.0
    - Date-based: 2025.10.11, 2025-12-28
    - Prefixed: Version-1.13.1, version_2.0.0
    - Prerelease: 1.0.0-beta.1, 2.0.0-rc1

    Returns:
        {
            "major": int,
            "minor": int,
            "patch": int,
            "prerelease": str | None
        }
        or None if parsing fails
    """
    if not version_str:
        return None

    version_clean = version_str.strip()

    match = VERSION_REGEX.match(version_clean)
    if not match:
        return None

    return {
        "major": int(match.group("major")),
        "minor": int(match.group("minor") or 0),
        "patch": int(match.group("patch") or 0),
        "prerelease": match.group("prerelease"),
    }


def compute_version_sort_key(version_normalized: dict | None) -> int | None:
    """Compute an integer sort key for version comparison.

    Format: major * 10^9 + minor * 10^6 + patch * 10^3 + prerelease_offset

    Prerelease versions sort lower than stable versions of the same number.
    """
    if not version_normalized:
        return None

    major = version_normalized.get("major", 0)
    minor = version_normalized.get("minor", 0)
    patch = version_normalized.get("patch", 0)
    prerelease = version_normalized.get("prerelease")

    # Base sort key: higher = newer
    base_key = major * 1_000_000_000 + minor * 1_000_000 + patch * 1_000

    # Prerelease versions sort lower than stable
    if prerelease:
        # Subtract 1 to make prereleases sort before stable
        return base_key - 1
    else:
        return base_key


def detect_release_channel(version_str: str | None, install_method: str) -> str:
    """Determine the release channel for an addon.

    Returns: 'stable', 'prerelease', or 'branch'
    """
    if install_method == "branch":
        return "branch"

    if not version_str:
        return "stable"

    version_lower = version_str.lower()
    prerelease_patterns = ["alpha", "beta", "rc", "dev", "pre", "-a.", "-b."]

    for pattern in prerelease_patterns:
        if pattern in version_lower:
            return "prerelease"

    return "stable"


def is_prerelease_version(version_str: str | None) -> bool:
    """Check if a version string indicates a prerelease."""
    if not version_str:
        return False

    version_lower = version_str.lower()
    prerelease_patterns = ["alpha", "beta", "rc", "dev", "pre", "-a.", "-b."]

    return any(pattern in version_lower for pattern in prerelease_patterns)


def load_toml(filepath: Path) -> dict | None:
    """Load and parse a TOML file."""
    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}")
        return None


def fetch_latest_release(source: dict) -> dict | None:
    """Fetch latest release info from GitHub.

    For branch-based addons, fetches commit info instead of release/tag info.
    Includes commit SHA for all release types to enable precise version tracking.
    """
    if source.get("type") != "github":
        return None

    repo = source.get("repo", "")
    release_type = source.get("release_type", "tag")
    branch = source.get("branch", "main")

    try:
        # Branch-based addons track latest commit
        if release_type == "branch":
            return fetch_branch_info(repo, branch)

        if release_type == "release":
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)

            if not resp.ok:
                # Try tags as fallback
                return fetch_latest_tag(repo)

            data = resp.json()
            tag_name = data.get("tag_name", "unknown")

            # Fetch commit SHA for the release tag
            commit_sha = None
            try:
                tag_url = f"https://api.github.com/repos/{repo}/git/refs/tags/{tag_name}"
                tag_resp = requests.get(tag_url, headers=GITHUB_HEADERS, timeout=10)
                if tag_resp.ok:
                    tag_data = tag_resp.json()
                    commit_sha = tag_data.get("object", {}).get("sha")
            except requests.RequestException:
                pass

            return {
                "version": tag_name,
                "download_url": data.get("zipball_url"),
                "published_at": data.get("published_at"),
                "commit_sha": commit_sha,
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
        commit_sha = latest_tag.get("commit", {}).get("sha")

        # Try to get commit date for the tag
        published_at = None
        if commit_sha:
            try:
                commit_url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}"
                commit_resp = requests.get(commit_url, headers=GITHUB_HEADERS, timeout=10)
                if commit_resp.ok:
                    commit_data = commit_resp.json()
                    published_at = commit_data.get("commit", {}).get("committer", {}).get("date")
            except requests.RequestException:
                pass

        return {
            "version": tag_name,
            "download_url": f"https://github.com/{repo}/archive/refs/tags/{tag_name}.zip",
            "published_at": published_at,
            "commit_sha": commit_sha,
        }

    except requests.RequestException:
        return None


def fetch_branch_info(repo: str, branch: str) -> dict | None:
    """Fetch the latest commit info from a branch.

    Returns commit SHA, date, and message snippet for branch-based addons.
    """
    url = f"https://api.github.com/repos/{repo}/commits/{branch}"

    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)
        if not resp.ok:
            return None

        data = resp.json()
        commit = data.get("commit", {})
        committer = commit.get("committer", {})
        message = commit.get("message", "")

        # Truncate message to first line or 100 chars
        message_snippet = message.split("\n")[0][:100]
        if len(message.split("\n")[0]) > 100:
            message_snippet += "..."

        return {
            "version": data.get("sha", "")[:7],  # Short SHA as version
            "download_url": f"https://github.com/{repo}/archive/refs/heads/{branch}.zip",
            "published_at": committer.get("date"),
            "commit_sha": data.get("sha"),
            "commit_date": committer.get("date"),
            "commit_message": message_snippet,
        }

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch branch info for {repo}/{branch}: {e}")
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

    install_info = build_install_info(source, addon)

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
        "install": install_info,
    }

    if fetch_releases:
        release_info = fetch_latest_release(source)
        entry["latest_release"] = release_info

        # Determine release channel first (needed for version parsing logic)
        release_channel = detect_release_channel(
            release_info.get("version") if release_info else None,
            install_info["method"],
        )

        # Add version metadata for client convenience
        if release_info:
            version_str = release_info.get("version")

            # For branch-based addons, don't try to parse the commit SHA as a version
            if release_channel == "branch":
                version_normalized = None
                version_sort_key = None
            else:
                version_normalized = parse_version(version_str)
                version_sort_key = compute_version_sort_key(version_normalized)

            entry["version_info"] = {
                "version_normalized": version_normalized,
                "version_sort_key": version_sort_key,
                "is_prerelease": is_prerelease_version(version_str) if release_channel != "branch" else False,
                "release_channel": release_channel,
            }

            # Include branch-specific commit info if available
            if release_info.get("commit_message"):
                entry["version_info"]["commit_message"] = release_info["commit_message"]
        else:
            entry["version_info"] = None

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
