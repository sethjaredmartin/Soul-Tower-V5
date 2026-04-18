"""
src/pipeline/fetcher.py
Responsible for one thing: fetching raw CSV data from a URL
and returning it as a list of dicts.

Nothing about game logic, models, or Lua lives here.
This module is the boundary between the outside world and the pipeline.
"""

import csv
import io
import requests
from typing import Optional

from config import REQUEST_TIMEOUT, GAME_NAME_FIELD


class FetchError(Exception):
    """Raised when a sheet cannot be fetched."""
    pass


def fetch_sheet(url: str, sheet_name: str = "") -> list[dict]:
    """
    Fetch a published Google Sheet CSV from a URL.
    Returns a list of dicts, one per row, skipping rows with no Game Name.

    Args:
        url:        The published CSV URL.
        sheet_name: Optional label for error messages.

    Returns:
        List of row dicts with string values.

    Raises:
        FetchError: If the request fails or returns non-200.
    """
    label = sheet_name or url

    if not url:
        raise FetchError(f"No URL provided for sheet: {label}")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise FetchError(f"Request timed out for sheet: {label}")
    except requests.exceptions.RequestException as e:
        raise FetchError(f"Request failed for sheet '{label}': {e}")

    return _parse_csv(response.text, label)


def _parse_csv(text: str, label: str = "") -> list[dict]:
    """
    Parse CSV text into a list of row dicts.
    Skips rows where Game Name is missing or empty.
    """
    reader = csv.DictReader(io.StringIO(text))
    rows = []

    for row in reader:
        game_name = row.get(GAME_NAME_FIELD, "").strip()
        if not game_name:
            continue
        # Strip all values
        cleaned = {k: v.strip() for k, v in row.items()}
        rows.append(cleaned)

    if not rows:
        print(f"Warning: No valid rows found in sheet '{label}'.")

    return rows
