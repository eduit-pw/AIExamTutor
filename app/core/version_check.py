"""Very small GitHub release checker.

KISS: compare the local app version against the latest GitHub Release tag.
"""

from __future__ import annotations

import json
from urllib.request import urlopen

from app import __version__

GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/eduit-pw/AIExamTutor/releases/latest"


def _clean_version(version: str) -> str:
    """Strip a leading v from a Git tag."""
    return version.strip().lstrip("v")


def fetch_latest_release_version() -> str:
    """Return the latest GitHub release tag, or the current local version on failure."""
    try:
        with urlopen(GITHUB_LATEST_RELEASE_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        tag = payload.get("tag_name")
        if tag:
            return str(tag)
    except Exception:
        pass
    return f"v{__version__}"


def is_newer_version(current_version: str, latest_release: str) -> bool:
    """True when the latest GitHub release is newer than the local version."""
    current = _clean_version(current_version)
    latest = _clean_version(latest_release)
    try:
        current_tuple = tuple(int(part) for part in current.split("."))
        latest_tuple = tuple(int(part) for part in latest.split("."))
    except ValueError:
        return False

    return latest_tuple > current_tuple
