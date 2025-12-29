#!/usr/bin/env python3
"""Validate addon TOML files against schema and repository checks."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional

import requests

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from jsonschema import ValidationError, validate

SCHEMA = {
    "type": "object",
    "required": ["addon", "source", "meta"],
    "properties": {
        "addon": {
            "type": "object",
            "required": ["slug", "name", "description", "authors", "category"],
            "properties": {
                "slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "name": {"type": "string", "minLength": 1},
                "description": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "license": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": [
                        "combat",
                        "crafting",
                        "dungeons",
                        "guilds",
                        "housing",
                        "inventory",
                        "library",
                        "maps",
                        "miscellaneous",
                        "pvp",
                        "quests",
                        "roleplay",
                        "social",
                        "trading",
                        "ui",
                    ],
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
        "source": {
            "type": "object",
            "required": ["type", "repo"],
            "properties": {
                "type": {"type": "string", "enum": ["github", "gitlab", "custom"]},
                "repo": {"type": "string"},
                "branch": {"type": "string"},
                "path": {"type": "string"},  # Subdirectory path if addon not at repo root
                "release_type": {"type": "string", "enum": ["tag", "release", "branch"]},
            },
        },
        "compatibility": {
            "type": "object",
            "properties": {
                "api_version": {"type": "string", "pattern": "^[0-9]+$"},
                "game_versions": {"type": "array", "items": {"type": "string"}},
                "required_dependencies": {"type": "array", "items": {"type": "string"}},
                "optional_dependencies": {"type": "array", "items": {"type": "string"}},
            },
        },
        "meta": {
            "type": "object",
            "required": ["submitted_by", "status"],
            "properties": {
                "submitted_by": {"type": "string"},
                "submitted_date": {},  # Can be string or date
                "last_reviewed": {},
                "status": {
                    "type": "string",
                    "enum": ["pending", "approved", "deprecated", "removed"],
                },
                "reviewers": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

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
        return None


def validate_toml_schema(data: dict) -> list[str]:
    """Validate data against the JSON schema. Returns list of errors."""
    errors = []
    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as e:
        errors.append(f"Schema error: {e.message}")
    return errors


def validate_slug_matches_directory(filepath: Path, data: dict) -> list[str]:
    """Ensure slug matches the parent directory name."""
    errors = []
    expected_slug = filepath.parent.name
    actual_slug = data.get("addon", {}).get("slug", "")

    if actual_slug != expected_slug:
        errors.append(f"Slug '{actual_slug}' doesn't match directory '{expected_slug}'")

    return errors


def validate_no_duplicate_slugs(filepath: Path, data: dict) -> list[str]:
    """Check for duplicate slugs in the addons directory."""
    errors = []
    addons_dir = filepath.parent.parent
    actual_slug = data.get("addon", {}).get("slug", "")

    existing_slugs = set()
    for addon_toml in addons_dir.glob("*/addon.toml"):
        if addon_toml != filepath:
            existing_slugs.add(addon_toml.parent.name)

    if actual_slug in existing_slugs:
        errors.append(f"Duplicate slug: '{actual_slug}' already exists")

    return errors


def check_github_repository(repo: str) -> list[str]:
    """Verify GitHub repository exists and is accessible."""
    errors = []
    api_url = f"https://api.github.com/repos/{repo}"

    try:
        resp = requests.get(api_url, headers=GITHUB_HEADERS, timeout=10)
        if resp.status_code == 404:
            errors.append(f"Repository not found: {repo}")
        elif resp.status_code == 403:
            errors.append(f"Repository access denied (may be private): {repo}")
        elif not resp.ok:
            errors.append(f"Failed to access repository: {repo} (HTTP {resp.status_code})")
    except requests.RequestException as e:
        errors.append(f"Network error checking repository: {e}")

    return errors


def check_eso_manifest(repo: str, branch: str | None = None, path: str | None = None) -> list[str]:
    """Check if repository contains a valid ESO addon manifest.

    Args:
        repo: Repository path (owner/repo format)
        branch: Branch to check (defaults to repo's default branch)
        path: Subdirectory path if addon is not at repo root
    """
    errors = []

    # Get default branch if not specified
    if not branch:
        api_url = f"https://api.github.com/repos/{repo}"
        try:
            resp = requests.get(api_url, headers=GITHUB_HEADERS, timeout=10)
            if resp.ok:
                branch = resp.json().get("default_branch", "main")
            else:
                branch = "main"
        except requests.RequestException:
            branch = "main"

    # Build contents URL (with optional subdirectory path)
    if path:
        contents_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        location_desc = f"subdirectory '{path}'"
    else:
        contents_url = f"https://api.github.com/repos/{repo}/contents"
        location_desc = "repository root"

    try:
        resp = requests.get(contents_url, headers=GITHUB_HEADERS, timeout=10)
        if not resp.ok:
            if resp.status_code == 404 and path:
                errors.append(f"Subdirectory '{path}' not found in repository")
            else:
                errors.append(f"Could not list repository contents: HTTP {resp.status_code}")
            return errors

        files = resp.json()
        if not isinstance(files, list):
            errors.append("Unexpected repository structure")
            return errors

        # ESO manifests can be .txt or .addon files
        manifest_files = [
            f["name"] for f in files
            if f.get("type") == "file" and (f["name"].endswith(".txt") or f["name"].endswith(".addon"))
        ]

        if not manifest_files:
            errors.append(f"No addon manifest (.txt or .addon) found in {location_desc}")
            return errors

        # Check at least one manifest file has ESO manifest format
        manifest_found = False
        for manifest_file in manifest_files:
            if path:
                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}/{manifest_file}"
            else:
                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{manifest_file}"
            try:
                resp = requests.get(raw_url, timeout=10)
                if resp.ok and "## Title:" in resp.text:
                    manifest_found = True
                    break
            except requests.RequestException:
                continue

        if not manifest_found:
            errors.append("No valid ESO manifest found (missing '## Title:' header)")

    except requests.RequestException as e:
        errors.append(f"Network error checking manifest: {e}")

    return errors


def check_has_releases(repo: str, release_type: str = "tag") -> list[str]:
    """Check if repository has at least one release, tag, or valid branch."""
    errors = []

    if release_type == "release":
        url = f"https://api.github.com/repos/{repo}/releases"
    elif release_type == "branch":
        # For branch-based releases, we just need the branch to exist
        # which is already validated in check_manifest_exists
        return errors
    else:
        url = f"https://api.github.com/repos/{repo}/tags"

    try:
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=10)
        if not resp.ok:
            errors.append(f"Could not check releases/tags: HTTP {resp.status_code}")
            return errors

        data = resp.json()
        if not data:
            errors.append(f"No {release_type}s found in repository")

    except requests.RequestException as e:
        errors.append(f"Network error checking releases: {e}")

    return errors


def validate_repository(data: dict) -> list[str]:
    """Validate the source repository."""
    errors = []
    source = data.get("source", {})

    if source.get("type") != "github":
        # Only GitHub validation implemented for now
        return errors

    repo = source.get("repo", "")
    branch = source.get("branch")
    path = source.get("path")  # Subdirectory path (optional)
    release_type = source.get("release_type", "tag")

    # Check repository exists
    repo_errors = check_github_repository(repo)
    if repo_errors:
        return repo_errors  # Don't continue if repo doesn't exist

    # Check for ESO manifest (in root or subdirectory)
    errors.extend(check_eso_manifest(repo, branch, path))

    # Check for releases/tags
    errors.extend(check_has_releases(repo, release_type))

    return errors


def validate_file(filepath: Path, check_repo: bool = True) -> list[str]:
    """Validate a single TOML file. Returns list of errors."""
    errors = []

    # Check file exists
    if not filepath.exists():
        return [f"File not found: {filepath}"]

    # Parse TOML
    data = load_toml(filepath)
    if data is None:
        return [f"Failed to parse TOML: {filepath}"]

    # Schema validation
    errors.extend(validate_toml_schema(data))

    # Slug validation
    errors.extend(validate_slug_matches_directory(filepath, data))
    errors.extend(validate_no_duplicate_slugs(filepath, data))

    # Repository validation (optional, can be slow)
    if check_repo:
        errors.extend(validate_repository(data))

    return errors


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate.py <file1.toml> [file2.toml ...] [--no-repo-check]")
        print("\nOptions:")
        print("  --no-repo-check  Skip repository validation (faster)")
        sys.exit(1)

    # Parse arguments
    check_repo = "--no-repo-check" not in sys.argv
    files = [f for f in sys.argv[1:] if not f.startswith("--")]

    if not files:
        print("No files specified")
        sys.exit(1)

    all_errors = []
    for filepath_str in files:
        filepath = Path(filepath_str)
        print(f"Validating: {filepath}")

        errors = validate_file(filepath, check_repo=check_repo)
        for error in errors:
            all_errors.append(f"{filepath}: {error}")
            print(f"  ERROR: {error}")

        if not errors:
            print("  OK")

    print()
    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s)")
        sys.exit(1)
    else:
        print("All validations passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
