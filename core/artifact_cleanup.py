"""
Standalone + importable module to move pipeline artifacts to a timestamped archive.

Usage:
    python -m core.artifact_cleanup [directory_path]

    Or import:
        from core.artifact_cleanup import cleanup_artifacts
        result = cleanup_artifacts("/path/to/scan")
"""

import os
import sys
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from core.config_loader import ConfigLoader


ARTIFACT_PATTERNS = ConfigLoader.get("artifact_patterns")

EXCLUDED_DIRS = set(ConfigLoader.get("ignored_dirs"))


def _matches_any_pattern(filename: str) -> bool:
    import fnmatch
    for pattern in ARTIFACT_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def find_artifacts(directory: str) -> List[str]:
    """Recursively find all pipeline artifact files in directory."""
    found: List[str] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if _matches_any_pattern(f):
                found.append(os.path.join(root, f))
    return sorted(found)


def cleanup_artifacts(directory: str, archive_base: Optional[str] = None) -> Dict:
    """Move all pipeline artifacts to a timestamped archive folder.

    Args:
        directory: Root directory to scan for artifacts.
        archive_base: Parent directory for the archive folder.
                      Defaults to <directory>/artifacts.

    Returns:
        dict with keys: archive_path, files_moved (list), count (int)
    """
    if archive_base is None:
        archive_base = os.path.join(directory, "artifacts")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = os.path.join(archive_base, timestamp)

    artifacts = find_artifacts(directory)
    moved: List[str] = []

    if not artifacts:
        return {
            "archive_path": "",
            "files_moved": [],
            "count": 0,
        }

    os.makedirs(archive_path, exist_ok=True)

    for filepath in artifacts:
        dest = os.path.join(archive_path, os.path.basename(filepath))
        # Avoid collisions by appending a suffix if dest already exists
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1
        shutil.move(filepath, dest)
        moved.append(filepath)
        print(f"  Moved: {filepath} -> {dest}")

    return {
        "archive_path": archive_path,
        "files_moved": moved,
        "count": len(moved),
    }


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning '{directory}' for pipeline artifacts...")
    result = cleanup_artifacts(directory)

    if result["count"] == 0:
        print("No artifacts found. Workspace is clean.")
    else:
        print(f"\nMoved {result['count']} file(s) to {result['archive_path']}/")

    sys.exit(0)


if __name__ == "__main__":
    main()
