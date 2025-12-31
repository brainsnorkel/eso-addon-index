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
PREVIOUS_INDEX_PATH = OUTPUT_DIR / "index.json"
VERSION_HISTORY_PATH = OUTPUT_DIR / "version-history.json"

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


def load_previous_index() -> dict:
    """Load the previous index.json if it exists.

    Returns a dict mapping slug -> addon entry for easy lookup.
    """
    if not PREVIOUS_INDEX_PATH.exists():
        return {}

    try:
        with open(PREVIOUS_INDEX_PATH) as f:
            previous = json.load(f)
        return {addon["slug"]: addon for addon in previous.get("addons", [])}
    except Exception as e:
        print(f"Warning: Failed to load previous index: {e}")
        return {}


def load_version_history() -> dict:
    """Load the existing version history if it exists.

    Returns a dict mapping slug -> list of version entries.
    Each version entry contains: version, published_at, detected_at, commit_sha
    """
    if not VERSION_HISTORY_PATH.exists():
        return {}

    try:
        with open(VERSION_HISTORY_PATH) as f:
            data = json.load(f)
        return data.get("addons", {})
    except Exception as e:
        print(f"Warning: Failed to load version history: {e}")
        return {}


def update_version_history(
    history: dict,
    slug: str,
    current_entry: dict,
    previous_entry: dict | None,
    now: str,
) -> list[dict]:
    """Update version history for an addon and return any new version events.

    Returns a list of version change events (for the Atom feed).
    """
    events = []

    # Get or create history for this addon
    addon_history = history.get(slug, [])

    # Get current version info
    release = current_entry.get("latest_release")
    if not release:
        return events

    current_version = release.get("version")
    current_sha = release.get("commit_sha")
    published_at = release.get("published_at")

    if not current_version:
        return events

    # Check if this version already exists in history
    existing_versions = {h.get("version"): h for h in addon_history}

    if current_version not in existing_versions:
        # New version detected
        new_entry = {
            "version": current_version,
            "published_at": published_at,
            "detected_at": now,
            "commit_sha": current_sha,
        }
        addon_history.insert(0, new_entry)  # Most recent first

        # Create event for Atom feed
        previous_version = None
        if previous_entry and previous_entry.get("latest_release"):
            previous_version = previous_entry["latest_release"].get("version")

        # Only create an event if this is a genuine new version (not just initializing history)
        # Skip if the old and new versions are the same
        if previous_version != current_version:
            events.append({
                "slug": slug,
                "name": current_entry.get("name", slug),
                "url": current_entry.get("url", ""),
                "old_version": previous_version,
                "new_version": current_version,
                "published_at": published_at,
                "detected_at": now,
            })

    # Update history
    history[slug] = addon_history

    return events


def has_addon_changed(current: dict, previous: dict) -> tuple[bool, str]:
    """Compare two addon entries to detect changes.

    Returns (changed: bool, reason: str).
    Ignores last_updated field when comparing.
    """
    # Fields to compare for metadata changes
    metadata_fields = [
        "name", "description", "authors", "license", "tags",
        "source", "compatibility", "install"
    ]

    # Check version change first
    current_version = current.get("latest_release", {}).get("version") if current.get("latest_release") else None
    previous_version = previous.get("latest_release", {}).get("version") if previous.get("latest_release") else None

    if current_version != previous_version:
        return True, "version"

    # Check commit SHA for branch-based addons
    current_sha = current.get("latest_release", {}).get("commit_sha") if current.get("latest_release") else None
    previous_sha = previous.get("latest_release", {}).get("commit_sha") if previous.get("latest_release") else None

    if current_sha != previous_sha:
        return True, "commit"

    # Check metadata fields
    for field in metadata_fields:
        if current.get(field) != previous.get(field):
            return True, f"metadata:{field}"

    return False, "unchanged"


def compute_last_updated(current: dict, previous: dict | None, now: str) -> str:
    """Compute the last_updated timestamp for an addon.

    Logic:
    - New addon: use current timestamp
    - Version/commit changed: use published_at from release (or now if unavailable)
    - Metadata changed: use current timestamp
    - No changes: preserve previous last_updated
    """
    if previous is None:
        # New addon
        return now

    changed, reason = has_addon_changed(current, previous)

    if not changed:
        # Preserve previous last_updated
        return previous.get("last_updated", now)

    if reason in ("version", "commit"):
        # Use published_at from the new release if available
        release = current.get("latest_release", {})
        published_at = release.get("published_at") if release else None
        return published_at or now

    # Metadata changed, use current timestamp
    return now


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


def build_download_sources(source: dict, release_info: dict | None) -> list[dict]:
    """Build download source URLs with jsDelivr as primary and GitHub as fallback.

    jsDelivr is a free CDN that mirrors GitHub content:
    - No rate limits
    - CORS-friendly (works in browsers)
    - Works even if GitHub is blocked (e.g., in some countries/networks)
    - Caches content globally for faster downloads

    Returns a list of download sources in priority order.
    """
    if source.get("type") != "github" or not release_info:
        return []

    repo = source.get("repo", "")
    branch = source.get("branch", "main")
    path = source.get("path")
    version = release_info.get("version", "")
    release_type = source.get("release_type", "tag")

    sources = []

    # Determine the ref (tag or branch)
    if release_type == "branch":
        ref = branch
    else:
        ref = version

    if not ref:
        return []

    # Primary: jsDelivr CDN
    # Note: jsDelivr serves files individually, not as archives.
    # For directory-based downloads, clients fetch the file list and download each file.
    # The base_url points to the addon root within the repo.
    if path:
        jsdelivr_base = f"https://cdn.jsdelivr.net/gh/{repo}@{ref}/{path}/"
    else:
        jsdelivr_base = f"https://cdn.jsdelivr.net/gh/{repo}@{ref}/"

    sources.append({
        "type": "jsdelivr",
        "url": jsdelivr_base,
        "note": "CDN - serves individual files, no rate limits, CORS-friendly",
    })

    # Fallback: Direct GitHub archive (ZIP)
    github_url = release_info.get("download_url", "")
    if github_url:
        sources.append({
            "type": "github_archive",
            "url": github_url,
            "note": "Direct GitHub ZIP archive, subject to rate limits",
        })

    return sources


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

        # Add download sources (jsDelivr primary, GitHub fallback)
        entry["download_sources"] = build_download_sources(source, release_info)

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


def build_index(fetch_releases: bool = True) -> tuple[dict, dict, list[dict]]:
    """Build the complete addon index.

    Returns:
        tuple: (index_data, version_history, version_events)
        - index_data: The main index.json structure
        - version_history: Updated version history for all addons
        - version_events: List of version change events for Atom feed
    """
    addons = []

    # Load previous index for last_updated comparison
    previous_index = load_previous_index()

    # Load existing version history
    version_history = load_version_history()

    # Track version change events for Atom feed
    all_version_events = []

    now = datetime.now(timezone.utc).isoformat()

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

        # Compute last_updated
        slug = entry["slug"]
        previous_entry = previous_index.get(slug)
        entry["last_updated"] = compute_last_updated(entry, previous_entry, now)

        # Update version history and collect events
        events = update_version_history(
            version_history, slug, entry, previous_entry, now
        )
        all_version_events.extend(events)

        addons.append(entry)

    index_data = {
        "version": "1.0",
        "generated_at": now,
        "addon_count": len(addons),
        "addons": sorted(addons, key=lambda x: x["name"].lower()),
    }

    return index_data, version_history, all_version_events


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
            "date_modified": addon.get("last_updated"),
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


def build_atom_feed(version_events: list[dict], generated_at: str) -> str:
    """Build an Atom feed (XML) for version change events.

    This feed is useful for RSS readers and notification systems that want
    to track addon updates.
    """
    # XML escape helper
    def escape(s: str | None) -> str:
        if s is None:
            return ""
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    entries = []
    for event in version_events:
        slug = escape(event.get("slug", ""))
        name = escape(event.get("name", slug))
        url = escape(event.get("url", ""))
        old_version = event.get("old_version")
        new_version = escape(event.get("new_version", ""))
        detected_at = event.get("detected_at", generated_at)

        # Build title
        if old_version:
            title = f"{name} updated: {escape(old_version)} → {new_version}"
        else:
            title = f"{name} added: {new_version}"

        # Build summary
        if old_version:
            summary = f"{name} has been updated from version {escape(old_version)} to {new_version}."
        else:
            summary = f"{name} version {new_version} has been added to the index."

        # Create unique ID for this event
        entry_id = f"urn:eso-addon-index:{slug}:{new_version}"

        entries.append(f"""  <entry>
    <id>{entry_id}</id>
    <title>{title}</title>
    <link href="{url}" rel="alternate"/>
    <updated>{detected_at}</updated>
    <summary>{summary}</summary>
    <author>
      <name>ESO Addon Index</name>
    </author>
  </entry>""")

    entries_xml = "\n".join(entries) if entries else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ESO Addon Index - Version Updates</title>
  <subtitle>Track version updates for Elder Scrolls Online addons</subtitle>
  <link href="https://xop.co/eso-addon-index/releases.atom" rel="self"/>
  <link href="https://xop.co/eso-addon-index/" rel="alternate"/>
  <id>urn:eso-addon-index:releases</id>
  <updated>{generated_at}</updated>
  <author>
    <name>ESO Addon Index</name>
    <uri>https://github.com/brainsnorkel/eso-addon-index</uri>
  </author>
{entries_xml}
</feed>
"""


def build_missing_dependencies_feed(index: dict) -> dict:
    """Build a feed of dependencies that are referenced but not in the index.

    This helps identify addons that should be added to complete the dependency graph.
    """
    # Build set of available addon slugs (case-insensitive lookup)
    available_slugs = {addon["slug"].lower() for addon in index["addons"]}

    # Track missing dependencies: {slug_lower: {"original_name": str, "type": set, "needed_by": list}}
    missing: dict[str, dict] = {}

    for addon in index["addons"]:
        compatibility = addon.get("compatibility", {})
        addon_info = {"slug": addon["slug"], "name": addon["name"]}

        # Check required dependencies
        for dep in compatibility.get("required_dependencies", []):
            dep_lower = dep.lower()
            if dep_lower not in available_slugs:
                if dep_lower not in missing:
                    missing[dep_lower] = {
                        "original_name": dep,
                        "types": set(),
                        "needed_by": [],
                    }
                missing[dep_lower]["types"].add("required")
                missing[dep_lower]["needed_by"].append(addon_info)

        # Check optional dependencies
        for dep in compatibility.get("optional_dependencies", []):
            dep_lower = dep.lower()
            if dep_lower not in available_slugs:
                if dep_lower not in missing:
                    missing[dep_lower] = {
                        "original_name": dep,
                        "types": set(),
                        "needed_by": [],
                    }
                missing[dep_lower]["types"].add("optional")
                missing[dep_lower]["needed_by"].append(addon_info)

    # Convert to list format for JSON
    missing_list = []
    for slug_lower, info in sorted(missing.items()):
        # Determine if required, optional, or both
        types = sorted(info["types"])
        if "required" in types and "optional" in types:
            dep_type = "required+optional"
        elif "required" in types:
            dep_type = "required"
        else:
            dep_type = "optional"

        missing_list.append({
            "slug": info["original_name"],
            "slug_normalized": slug_lower,
            "dependency_type": dep_type,
            "needed_by": info["needed_by"],
            "needed_by_count": len(info["needed_by"]),
        })

    # Sort by count descending, then name
    missing_list.sort(key=lambda x: (-x["needed_by_count"], x["slug"].lower()))

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "description": "Dependencies referenced by addons but not available in the index",
        "missing_count": len(missing_list),
        "missing_dependencies": missing_list,
    }


def load_existing_atom_events(output_dir: Path) -> list[dict]:
    """Load existing version events from releases-history.json if it exists.

    This preserves historical events for the Atom feed across builds.
    Filters out invalid events where old_version == new_version (bug from initial seeding).
    """
    history_path = output_dir / "releases-history.json"
    if not history_path.exists():
        return []

    try:
        with open(history_path) as f:
            data = json.load(f)
        events = data.get("events", [])
        # Filter out invalid events where old and new versions are the same
        valid_events = [
            e for e in events
            if e.get("old_version") != e.get("new_version")
        ]
        if len(valid_events) < len(events):
            print(f"Filtered out {len(events) - len(valid_events)} invalid same-version event(s)")
        return valid_events
    except Exception as e:
        print(f"Warning: Failed to load existing Atom events: {e}")
        return []


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

    # Build main index (now returns version history and events too)
    index, version_history, new_version_events = build_index(
        fetch_releases=not args.no_releases
    )

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

    # Write version history
    version_history_data = {
        "version": "1.0",
        "generated_at": index["generated_at"],
        "description": "Version history for all addons in the index",
        "addons": version_history,
    }
    version_history_path = output_dir / "version-history.json"
    with open(version_history_path, "w") as f:
        json.dump(version_history_data, f, indent=2)
    print(f"Wrote: {version_history_path}")

    # Load existing Atom events and merge with new ones
    existing_events = load_existing_atom_events(output_dir)

    # Deduplicate events by (slug, version) - keep the earliest detection
    seen_events = {}
    for event in existing_events + new_version_events:
        key = (event.get("slug"), event.get("new_version"))
        if key not in seen_events:
            seen_events[key] = event

    # Sort by detected_at descending (newest first), limit to 100 entries
    all_events = sorted(
        seen_events.values(),
        key=lambda x: x.get("detected_at", ""),
        reverse=True,
    )[:100]

    # Save events history for future builds
    events_history_path = output_dir / "releases-history.json"
    with open(events_history_path, "w") as f:
        json.dump({
            "version": "1.0",
            "generated_at": index["generated_at"],
            "events": all_events,
        }, f, indent=2)
    print(f"Wrote: {events_history_path}")

    # Write Atom feed
    atom_feed = build_atom_feed(all_events, index["generated_at"])
    atom_path = output_dir / "releases.atom"
    with open(atom_path, "w", encoding="utf-8") as f:
        f.write(atom_feed)
    print(f"Wrote: {atom_path}")

    # Write JSON Feed
    feed = build_json_feed(index)
    feed_path = output_dir / "feed.json"
    with open(feed_path, "w") as f:
        json.dump(feed, f, indent=2)
    print(f"Wrote: {feed_path}")

    # Write missing dependencies feed
    missing_deps = build_missing_dependencies_feed(index)
    missing_path = output_dir / "missing-dependencies.json"
    with open(missing_path, "w") as f:
        json.dump(missing_deps, f, indent=2)
    print(f"Wrote: {missing_path}")

    print()
    print(f"Built index with {index['addon_count']} addon(s)")
    if new_version_events:
        print(f"Detected {len(new_version_events)} new version update(s)")
    if missing_deps["missing_count"] > 0:
        print(f"Found {missing_deps['missing_count']} missing dependency(s)")


if __name__ == "__main__":
    main()
