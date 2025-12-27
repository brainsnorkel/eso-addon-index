#!/usr/bin/env python3
"""Run Luacheck on remote addon repositories."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# GitHub API headers
GITHUB_HEADERS = {}
if token := os.environ.get("GITHUB_TOKEN"):
    GITHUB_HEADERS["Authorization"] = f"token {token}"

# Luacheck configuration for ESO addons
LUACHECK_CONFIG = """
-- ESO Addon Luacheck Configuration
std = "lua51"
max_line_length = 200

-- ESO global functions and namespaces
globals = {
    "SLASH_COMMANDS",
    "EVENT_MANAGER",
    "SCENE_MANAGER",
    "CALLBACK_MANAGER",
    "WINDOW_MANAGER",
    "ANIMATION_MANAGER",
    "LibAddonMenu2",
    "LibStub",
    "ZO_SavedVars",
    "ZO_Dialogs_ShowDialog",
    "ZO_Dialogs_RegisterCustomDialog",
    "ZO_CreateStringId",
    "ZO_PreHook",
    "ZO_PostHook",
    "d",
    "df",
}

read_globals = {
    -- ESO API (common functions)
    "GetAPIVersion",
    "GetDisplayName",
    "GetUnitName",
    "GetMapPlayerPosition",
    "GetCurrentMapZoneIndex",
    "GetGameTimeMilliseconds",
    "GetFrameTimeMilliseconds",
    "GetString",
    "GetControl",
    "CreateControl",
    "CreateTopLevelWindow",
    "PlaySound",
    "SOUNDS",
    "IsUnitInCombat",
    "IsUnitPlayer",
    "GetUnitClass",
    "GetUnitRace",
    "GetUnitLevel",
    "GetUnitChampionPoints",
    "GetNumBuffs",
    "GetUnitBuffInfo",
    "GetAbilityName",
    "GetAbilityIcon",
    "GetAbilityDuration",
    "DoesUnitExist",
    "AreUnitsEqual",
    -- Common ZO_ functions
    "ZO_ColorDef",
    "ZO_Anchor",
    "zo_strformat",
    "zo_strlower",
    "zo_strupper",
    "zo_strlen",
    "zo_min",
    "zo_max",
    "zo_clamp",
    "zo_round",
    "zo_floor",
    "zo_ceil",
    "zo_abs",
    "zo_lerp",
    "zo_plainTableCopy",
    "zo_shallowTableCopy",
    "zo_mixin",
    "zo_callLater",
    "zo_callHandler",
    -- Events
    "EVENT_ADD_ON_LOADED",
    "EVENT_PLAYER_ACTIVATED",
    "EVENT_RETICLE_TARGET_CHANGED",
    "EVENT_EFFECT_CHANGED",
    "EVENT_COMBAT_EVENT",
    "EVENT_PLAYER_COMBAT_STATE",
    "EVENT_UNIT_DEATH_STATE_CHANGED",
    -- UI
    "CENTER",
    "TOP",
    "BOTTOM",
    "LEFT",
    "RIGHT",
    "TOPLEFT",
    "TOPRIGHT",
    "BOTTOMLEFT",
    "BOTTOMRIGHT",
    "GuiRoot",
    "ZO_WorldMap",
    -- Constants
    "SI_BINDING_NAME_",
}

-- Ignore common ESO patterns
ignore = {
    "212",  -- Unused argument (common in event handlers)
    "213",  -- Unused loop variable
    "311",  -- Value assigned to variable is unused (common pattern)
}
"""


def load_toml(filepath: Path) -> dict | None:
    """Load and parse a TOML file."""
    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}")
        return None


def download_repo(repo: str, branch: str | None = None) -> Path | None:
    """Download a repository to a temporary directory."""
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

    # Download as zip
    zip_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"

    try:
        resp = requests.get(zip_url, timeout=30)
        if not resp.ok:
            print(f"  Failed to download: HTTP {resp.status_code}")
            return None

        # Extract to temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="luacheck_"))
        zip_path = temp_dir / "repo.zip"

        with open(zip_path, "wb") as f:
            f.write(resp.content)

        # Extract
        shutil.unpack_archive(zip_path, temp_dir)
        zip_path.unlink()

        # Find extracted directory (usually repo-branch/)
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if extracted_dirs:
            return extracted_dirs[0]

        return temp_dir

    except Exception as e:
        print(f"  Error downloading repo: {e}")
        return None


def run_luacheck(directory: Path) -> tuple[int, str]:
    """Run Luacheck on a directory. Returns (exit_code, output)."""
    # Check if luacheck is available
    if not shutil.which("luacheck"):
        return -1, "Luacheck not installed"

    # Write temporary config
    config_path = directory / ".luacheckrc"
    with open(config_path, "w") as f:
        f.write(LUACHECK_CONFIG)

    try:
        result = subprocess.run(
            ["luacheck", ".", "--no-color", "--codes"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "Luacheck timed out"
    except Exception as e:
        return -1, f"Error running Luacheck: {e}"


def analyze_output(output: str) -> dict:
    """Analyze Luacheck output and categorize issues."""
    lines = output.strip().split("\n")
    errors = []
    warnings = []

    for line in lines:
        if ": (E" in line:
            errors.append(line)
        elif ": (W" in line:
            warnings.append(line)

    return {
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def check_addon(toml_path: Path) -> dict:
    """Run Luacheck on an addon from its TOML file."""
    data = load_toml(toml_path)
    if data is None:
        return {"success": False, "error": "Failed to load TOML"}

    source = data["source"]
    if source.get("type") != "github":
        return {"success": False, "error": "Only GitHub repos supported"}

    repo = source.get("repo", "")
    branch = source.get("branch")
    slug = data["addon"]["slug"]

    print(f"Checking: {slug} ({repo})")

    # Download repository
    repo_dir = download_repo(repo, branch)
    if repo_dir is None:
        return {"success": False, "error": "Failed to download repository"}

    try:
        # Run Luacheck
        exit_code, output = run_luacheck(repo_dir)

        if exit_code == -1:
            return {"success": False, "error": output}

        analysis = analyze_output(output)
        analysis["success"] = True
        analysis["exit_code"] = exit_code
        analysis["raw_output"] = output

        return analysis

    finally:
        # Cleanup
        try:
            shutil.rmtree(repo_dir.parent)
        except Exception:
            pass


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: luacheck-remote.py <addon.toml> [addon.toml ...]")
        print("\nRuns Luacheck on addon source repositories")
        sys.exit(1)

    # Check if luacheck is available
    if not shutil.which("luacheck"):
        print("Error: Luacheck is not installed")
        print("Install with: luarocks install luacheck")
        sys.exit(1)

    all_results = []
    has_errors = False

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue

        result = check_addon(filepath)
        result["file"] = str(filepath)
        all_results.append(result)

        if not result["success"]:
            print(f"  Error: {result.get('error', 'Unknown error')}")
            has_errors = True
        else:
            errors = result.get("error_count", 0)
            warnings = result.get("warning_count", 0)
            print(f"  Errors: {errors}, Warnings: {warnings}")

            if errors > 0:
                has_errors = True
                print("\n  Errors found:")
                for err in result.get("errors", [])[:10]:  # Limit output
                    print(f"    {err}")

        print()

    # Summary
    print("=" * 60)
    print("Summary:")
    for result in all_results:
        slug = Path(result["file"]).parent.name
        if result["success"]:
            status = f"E:{result['error_count']} W:{result['warning_count']}"
        else:
            status = f"FAILED: {result.get('error', 'Unknown')}"
        print(f"  {slug}: {status}")

    # Exit with error if any addon has errors
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
