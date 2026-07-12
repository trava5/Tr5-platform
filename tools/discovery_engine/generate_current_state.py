"""Tr5 Discovery Engine v1.0.

Scans the repository, classifies artifacts, and generates
TR5_CURRENT_STATE.md. See tools/discovery_engine/README.md.
"""

import os
import sys
from pathlib import Path

GENERATOR_NAME = "Tr5 Discovery Engine"
GENERATOR_VERSION = "1.0"
OUTPUT_FILE_NAME = "TR5_CURRENT_STATE.md"

# Directories that are not Tr5 platform content (VCS internals, virtual
# environment, IDE state). Excluded so the Current State document reflects
# the platform, not incidental local tooling.
EXCLUDED_DIRECTORY_NAMES = {".git", ".venv", ".idea"}


def classify_artifact(path):
    if path.is_dir():
        return "Directory"

    suffix = path.suffix.lower()
    if suffix == ".md":
        return "Markdown Document"
    if suffix == ".py":
        return "Python Source"
    if suffix == ".json":
        return "JSON Document"
    if suffix in (".yaml", ".yml"):
        return "YAML Document"
    return "Unknown"


def scan_repository(repository_root):
    artifacts = []

    for dirpath, dirnames, filenames in os.walk(repository_root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in EXCLUDED_DIRECTORY_NAMES
        )
        current_dir = Path(dirpath)

        for name in dirnames + sorted(filenames):
            full_path = current_dir / name
            artifacts.append(
                {
                    "name": name,
                    "relative_path": full_path.relative_to(
                        repository_root
                    ).as_posix(),
                    "type": classify_artifact(full_path),
                }
            )

    artifacts.sort(key=lambda artifact: artifact["relative_path"])
    return artifacts


def _build_tree(artifacts):
    tree = {}
    for artifact in artifacts:
        parts = artifact["relative_path"].split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault(parts[-1], {} if artifact["type"] == "Directory" else None)
    return tree


def _render_tree(node, prefix=""):
    lines = []
    directories = sorted(name for name, value in node.items() if value is not None)
    files = sorted(name for name, value in node.items() if value is None)

    for name in directories:
        lines.append(f"{prefix}- {name}/")
        lines.extend(_render_tree(node[name], prefix + "  "))
    for name in files:
        lines.append(f"{prefix}- {name}")

    return lines


def render_markdown(artifacts):
    lines = [
        "# TR5 Current State",
        "",
        f"Generator: {GENERATOR_NAME} v{GENERATOR_VERSION}",
        "",
        "---",
        "",
        "## Repository Structure",
        "",
    ]
    lines.extend(_render_tree(_build_tree(artifacts)))
    lines.extend(
        [
            "",
            "---",
            "",
            "## Artifacts",
            "",
            "| Name | Relative Path | Type |",
            "|---|---|---|",
        ]
    )
    for artifact in artifacts:
        lines.append(
            f"| {artifact['name']} | {artifact['relative_path']} | {artifact['type']} |"
        )
    lines.append("")

    return "\n".join(lines)


def save_current_state(repository_root, content):
    output_path = repository_root / OUTPUT_FILE_NAME
    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
    return output_path


def main():
    if len(sys.argv) > 1:
        repository_root = Path(sys.argv[1]).resolve()
    else:
        repository_root = Path(__file__).resolve().parents[2]

    artifacts = scan_repository(repository_root)
    content = render_markdown(artifacts)
    save_current_state(repository_root, content)


if __name__ == "__main__":
    main()
