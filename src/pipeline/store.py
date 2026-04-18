"""
src/pipeline/store.py
Handles reading and writing raw sheet data to/from local JSON cache files.

The cache stores raw row dicts — not parsed models. This keeps the store
simple and model-agnostic. Parsing happens in the registry.

Cache files live in data/cache/<sheet_name_slug>.json
"""

import json
from pathlib import Path
from typing import Optional

from config import CACHE_DIR, CACHE_EXT


def _cache_path(sheet_name: str) -> Path:
    """Convert a sheet name to its cache file path."""
    slug = sheet_name.lower().replace(" ", "_")
    return CACHE_DIR / f"{slug}{CACHE_EXT}"


def save(sheet_name: str, rows: list[dict]) -> Path:
    """
    Save raw row dicts to the local cache.

    Args:
        sheet_name: The canonical sheet name (e.g. 'Hero', 'Common Cards').
        rows:       List of raw row dicts to cache.

    Returns:
        Path to the written cache file.
    """
    path = _cache_path(sheet_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Cached {len(rows)} rows → {path}")
    return path


def load(sheet_name: str) -> Optional[list[dict]]:
    """
    Load raw row dicts from the local cache.

    Returns None if the cache file does not exist.

    Args:
        sheet_name: The canonical sheet name.

    Returns:
        List of raw row dicts, or None if not cached.
    """
    path = _cache_path(sheet_name)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    print(f"Loaded {len(rows)} rows from cache ← {path}")
    return rows


def exists(sheet_name: str) -> bool:
    """Check whether a cache file exists for the given sheet."""
    return _cache_path(sheet_name).exists()


def clear(sheet_name: str) -> bool:
    """
    Delete the cache file for a sheet.

    Returns True if the file existed and was deleted, False otherwise.
    """
    path = _cache_path(sheet_name)
    if path.exists():
        path.unlink()
        print(f"Cleared cache for '{sheet_name}'")
        return True
    return False


def clear_all() -> int:
    """
    Delete all cache files.

    Returns the number of files deleted.
    """
    count = 0
    for path in CACHE_DIR.glob(f"*{CACHE_EXT}"):
        path.unlink()
        count += 1
    print(f"Cleared {count} cache files.")
    return count
