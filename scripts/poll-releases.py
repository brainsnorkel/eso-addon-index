#!/usr/bin/env python3
"""Poll GitHub repositories for new releases and update version cache."""
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

ADDONS_DIR = Path("addons")
CACHE_FILE = Path("public/versions.json")

# GitHub API headers
GITHUB_HEADERS = {"Accept": "application/vnd.github.v3+json"}
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


def load_version_cache() -> dict:
    """Load the existing version cache."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"versions": {}, "last_checked": None}


def save_version_cache(cache: dict) -> None:
    """Save the version cache."""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_latest_release(repo: str, release_type: str = "tag") -> dict | None:
    """Fetch the latest release or tag from GitHub."""
    try:
        if release_type == "release":
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)

            if resp.status_code == 404:
                # No releases, try tags
                return get_latest_tag(repo)

            if not resp.ok:
                return None

            data = resp.json()
            return {
                "version": data.get("tag_name", "unknown"),
                "download_url": data.get("zipball_url"),
                "published_at": data.get("published_at"),
                "release_notes": data.get("body", "")[:500],  # Truncate long notes
            }
        else:
            return get_latest_tag(repo)

    except requests.RequestException as e:
        print(f"  Error fetching release for {repo}: {e}")
        return None


def get_latest_tag(repo: str) -> dict | None:
    """Fetch the latest tag from GitHub."""
    url = f"https://api.github.com/repos/{repo}/tags"

    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)
        if not resp.ok:
            return None

        tags = resp.json()
        if not tags:
            return None

        latest = tags[0]
        tag_name = latest["name"]

        # Try to get commit date for the tag
        commit_url = latest.get("commit", {}).get("url")
        published_at = None
        if commit_url:
            try:
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
            "release_notes": None,
        }

    except requests.RequestException:
        return None


def poll_all_addons() -> dict:
    """Poll all addons for their latest versions."""
    cache = load_version_cache()
    old_versions = cache.get("versions", {})
    new_versions = {}
    updates = []

    for toml_path in sorted(ADDONS_DIR.glob("*/addon.toml")):
        data = load_toml(toml_path)
        if data is None:
            continue

        # Only check approved addons
        status = data.get("meta", {}).get("status", "pending")
        if status != "approved":
            continue

        slug = data["addon"]["slug"]
        source = data["source"]
        repo = source.get("repo", "")
        release_type = source.get("release_type", "tag")

        if source.get("type") != "github":
            continue

        print(f"Checking: {slug} ({repo})")

        release_info = get_latest_release(repo, release_type)
        if release_info:
            new_versions[slug] = release_info

            # Check if version changed
            old_version = old_versions.get(slug, {}).get("version")
            new_version = release_info.get("version")

            if old_version and old_version != new_version:
                updates.append({
                    "slug": slug,
                    "old_version": old_version,
                    "new_version": new_version,
                    "repo": repo,
                })
                print(f"  Updated: {old_version} -> {new_version}")
            else:
                print(f"  Current: {new_version}")
        else:
            print("  No release found")

    return {
        "versions": new_versions,
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "updates": updates,
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Poll GitHub for new addon releases")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for updates without saving",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for version cache",
    )
    args = parser.parse_args()

    if args.output:
        global CACHE_FILE
        CACHE_FILE = args.output

    print("Polling addon repositories for updates...")
    print()

    result = poll_all_addons()

    print()
    print(f"Checked {len(result['versions'])} addon(s)")

    if result["updates"]:
        print(f"\nFound {len(result['updates'])} update(s):")
        for update in result["updates"]:
            print(f"  - {update['slug']}: {update['old_version']} -> {update['new_version']}")
    else:
        print("\nNo updates found")

    if not args.dry_run:
        save_version_cache(result)
        print(f"\nSaved version cache to: {CACHE_FILE}")
    else:
        print("\nDry run - no changes saved")


if __name__ == "__main__":
    main()
