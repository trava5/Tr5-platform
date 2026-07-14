"""Static loader for profiles/NNN_name/ directories."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("README.md", "prompt.txt", "actions.json", "features.json")


class ProfileError(RuntimeError):
    """Base class for profile loading/validation failures."""


class ProfileFilesMissingError(ProfileError):
    def __init__(self, profile_name: str, missing_files: list[str]) -> None:
        self.profile_name = profile_name
        self.missing_files = missing_files
        joined = ", ".join(missing_files)
        super().__init__(
            f"Profile '{profile_name}' is missing required file(s): {joined}."
        )


class UnknownToolError(ProfileError):
    def __init__(self, profile_name: str, unknown_tools: list[str]) -> None:
        self.profile_name = profile_name
        self.unknown_tools = unknown_tools
        joined = ", ".join(unknown_tools)
        super().__init__(
            f"Profile '{profile_name}' references unknown tool(s) not present "
            f"in tool_catalog: {joined}."
        )


@dataclass(frozen=True)
class Profile:
    name: str
    prompt: str
    tools: dict[str, dict[str, Any]]
    enabled_features: list[str]


def _resolve_profile_files(profile_dir: Path, profile_name: str) -> dict[str, Path]:
    missing = [
        filename
        for filename in REQUIRED_FILES
        if not (profile_dir / filename).is_file()
    ]
    if missing:
        raise ProfileFilesMissingError(profile_name, missing)
    return {filename: profile_dir / filename for filename in REQUIRED_FILES}


def load_profile(
    name: str,
    profiles_root: Path,
    tool_catalog: dict[str, dict[str, Any]],
) -> Profile:
    """Read, validate, and return the profile ``name`` under ``profiles_root``."""
    profile_dir = Path(profiles_root) / name
    if not profile_dir.is_dir():
        raise ProfileFilesMissingError(name, list(REQUIRED_FILES))

    files = _resolve_profile_files(profile_dir, name)

    prompt = files["prompt.txt"].read_text(encoding="utf-8")
    actions_data = json.loads(files["actions.json"].read_text(encoding="utf-8"))
    features_data = json.loads(files["features.json"].read_text(encoding="utf-8"))

    enabled_tools = list(actions_data.get("enabled_tools", []))
    unknown_tools = [tool for tool in enabled_tools if tool not in tool_catalog]
    if unknown_tools:
        raise UnknownToolError(name, unknown_tools)

    resolved_tools = {tool: deepcopy(tool_catalog[tool]) for tool in enabled_tools}
    enabled_features = list(features_data.get("enabled_features", []))

    return Profile(
        name=name,
        prompt=prompt,
        tools=resolved_tools,
        enabled_features=enabled_features,
    )


def list_available_profiles(profiles_root: Path) -> list[str]:
    """Return names of subdirectories under ``profiles_root`` that hold a complete profile."""
    root = Path(profiles_root)
    if not root.is_dir():
        return []

    names = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if all((entry / filename).is_file() for filename in REQUIRED_FILES):
            names.append(entry.name)
    return names
