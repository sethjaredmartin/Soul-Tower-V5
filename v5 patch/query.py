"""
src/analytics/query.py

Shared helpers for exploring Soul Tower game data in pandas.

These functions read from the local JSON cache produced by the pipeline
(src/pipeline/store.py) and return DataFrames ready for exploration.

The notebook (notebook.ipynb) imports from this module so that reusable
logic lives in one place and the notebook stays focused on exploration.

Why this split:
  - Functions tested once here work the same in the notebook
  - When you find a useful pattern, promote it from the notebook to here
  - If Flask ever needs these same queries, they're already importable
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import requests


# ── Paths ────────────────────────────────────────────────────────────────────

# Resolve project root from this file's location.
# src/analytics/query.py → src/analytics → src → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# Sheet canonical names and their cache filenames.
SHEETS = {
    "hero":         "hero",
    "common_cards": "common_cards",
    "legendary":    "legendary",
    "calamity":     "calamity",
    "villain":      "villain",
}


# ── Loading ──────────────────────────────────────────────────────────────────

def load_sheet(name: str) -> pd.DataFrame:
    """
    Load a single cached sheet as a DataFrame.

    Args:
        name: One of "hero", "common_cards", "legendary", "calamity", "villain"

    Returns:
        DataFrame with one row per entity. Columns match the sheet headers.

    Raises:
        FileNotFoundError: If the cache file doesn't exist yet. Run the
            pipeline first with `python main.py --fresh`.
    """
    if name not in SHEETS:
        raise ValueError(f"Unknown sheet '{name}'. Valid: {list(SHEETS)}")

    path = CACHE_DIR / f"{SHEETS[name]}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Cache file not found: {path}\n"
            f"Run the pipeline first: python main.py --fresh"
        )

    with path.open() as f:
        data = json.load(f)
    return pd.DataFrame(data)


def load_all() -> dict[str, pd.DataFrame]:
    """Load every sheet as a dict of DataFrames. Useful for notebook top cell."""
    return {name: load_sheet(name) for name in SHEETS}


# ── Cost parsing ─────────────────────────────────────────────────────────────

_DIE_PATTERN = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*(?:\+\s*(\d+))?\s*$", re.IGNORECASE)
_INT_PATTERN = re.compile(r"^\s*(\d+)\s*$")


def parse_cost(cost: str | int | float | None) -> dict:
    """
    Parse a cost string into a structured representation.

    Soul Tower costs can be:
      - Fixed integers: "3", "0"
      - Die expressions: "2d4", "1d6+2"
      - None or empty (treated as 0)

    Returns a dict with:
      - raw: the original string
      - is_die: whether this is a die-based cost
      - fixed: fixed portion (int), or None if not applicable
      - dice_count: number of dice (int), or None
      - dice_size: die sides (int), or None
      - modifier: flat modifier after dice (int), or 0
      - min_cost: minimum possible value
      - max_cost: maximum possible value
      - avg_cost: expected value (float)

    Examples:
        >>> parse_cost("3")
        {'raw': '3', 'is_die': False, 'fixed': 3, ..., 'min_cost': 3, 'max_cost': 3, 'avg_cost': 3.0}

        >>> parse_cost("2d4")
        {'raw': '2d4', 'is_die': True, 'dice_count': 2, 'dice_size': 4, 'modifier': 0,
         'min_cost': 2, 'max_cost': 8, 'avg_cost': 5.0}
    """
    if cost is None or cost == "" or (isinstance(cost, float) and pd.isna(cost)):
        return {
            "raw": "", "is_die": False, "fixed": 0,
            "dice_count": None, "dice_size": None, "modifier": 0,
            "min_cost": 0, "max_cost": 0, "avg_cost": 0.0,
        }

    cost_str = str(cost).strip()

    # Try fixed integer first
    m = _INT_PATTERN.match(cost_str)
    if m:
        value = int(m.group(1))
        return {
            "raw": cost_str, "is_die": False, "fixed": value,
            "dice_count": None, "dice_size": None, "modifier": 0,
            "min_cost": value, "max_cost": value, "avg_cost": float(value),
        }

    # Try die expression
    m = _DIE_PATTERN.match(cost_str)
    if m:
        dice_count = int(m.group(1))
        dice_size = int(m.group(2))
        modifier = int(m.group(3)) if m.group(3) else 0
        min_cost = dice_count + modifier  # minimum die roll is 1
        max_cost = (dice_count * dice_size) + modifier
        avg_cost = (dice_count * (dice_size + 1) / 2) + modifier
        return {
            "raw": cost_str, "is_die": True, "fixed": None,
            "dice_count": dice_count, "dice_size": dice_size, "modifier": modifier,
            "min_cost": min_cost, "max_cost": max_cost, "avg_cost": avg_cost,
        }

    # Unrecognized format. Return zeros with raw preserved for debugging.
    return {
        "raw": cost_str, "is_die": False, "fixed": None,
        "dice_count": None, "dice_size": None, "modifier": 0,
        "min_cost": 0, "max_cost": 0, "avg_cost": 0.0,
    }


def enrich_costs(df: pd.DataFrame, cost_column: str = "Cost") -> pd.DataFrame:
    """
    Add parsed cost columns to a DataFrame.

    Adds: cost_min, cost_max, cost_avg, is_die_cost

    Args:
        df: DataFrame with a cost column
        cost_column: name of the column containing cost expressions

    Returns:
        Copy of df with new columns appended.
    """
    if cost_column not in df.columns:
        return df.copy()

    parsed = df[cost_column].apply(parse_cost)
    out = df.copy()
    out["cost_min"] = parsed.apply(lambda p: p["min_cost"])
    out["cost_max"] = parsed.apply(lambda p: p["max_cost"])
    out["cost_avg"] = parsed.apply(lambda p: p["avg_cost"])
    out["is_die_cost"] = parsed.apply(lambda p: p["is_die"])
    return out


# ── Ability search ───────────────────────────────────────────────────────────

def _effect_columns(df: pd.DataFrame) -> list[str]:
    """Find columns that likely contain card/hero effect text."""
    candidates = []
    for col in df.columns:
        lower = col.lower()
        if any(key in lower for key in ("effect", "passive", "flavor")):
            candidates.append(col)
    return candidates


def has_ability(
    ability: str,
    sheets: Optional[dict[str, pd.DataFrame]] = None,
    case_sensitive: bool = False,
) -> pd.DataFrame:
    """
    Search every sheet for rows mentioning a specific ability.

    Args:
        ability: The ability name (e.g., "Enchant", "Fortune", "Blood Price")
        sheets: Dict of preloaded sheets. If None, calls load_all().
        case_sensitive: Whether to match case exactly.

    Returns:
        Combined DataFrame with a `_source` column indicating which sheet
        each match came from, plus a `_matched_in` column showing which
        effect field contained the match.

    Example:
        >>> enchant_cards = has_ability("Enchant")
        >>> enchant_cards.groupby("_source").size()
        hero          4
        common_cards  12
        legendary     7
        calamity      2
    """
    if sheets is None:
        sheets = load_all()

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(ability), flags)

    matches = []
    for sheet_name, df in sheets.items():
        cols = _effect_columns(df)
        if not cols:
            continue
        for col in cols:
            mask = df[col].astype(str).str.contains(pattern, na=False, regex=True)
            if mask.any():
                matched = df[mask].copy()
                matched["_source"] = sheet_name
                matched["_matched_in"] = col
                matches.append(matched)

    if not matches:
        return pd.DataFrame()
    return pd.concat(matches, ignore_index=True, sort=False)


# ── Type filtering ───────────────────────────────────────────────────────────

def spells(sheets: Optional[dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """
    Return every Spell in the game, across common, legendary, and crystal.

    Combines rows from all card sheets where Type == "Spell".
    """
    if sheets is None:
        sheets = load_all()

    results = []
    for sheet_name in ("common_cards", "legendary"):
        df = sheets.get(sheet_name)
        if df is None or "Type" not in df.columns:
            continue
        mask = df["Type"].astype(str).str.strip().str.lower() == "spell"
        subset = df[mask].copy()
        subset["_source"] = sheet_name
        results.append(subset)

    if not results:
        return pd.DataFrame()
    return pd.concat(results, ignore_index=True, sort=False)


def brutals(sheets: Optional[dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """Every Brutal card across common and legendary sheets."""
    return _filter_by_type("Brutal", sheets)


def rituals(sheets: Optional[dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """Every Ritual card across common and legendary sheets."""
    return _filter_by_type("Ritual", sheets)


def _filter_by_type(
    type_name: str,
    sheets: Optional[dict[str, pd.DataFrame]] = None,
) -> pd.DataFrame:
    if sheets is None:
        sheets = load_all()
    results = []
    for sheet_name in ("common_cards", "legendary"):
        df = sheets.get(sheet_name)
        if df is None or "Type" not in df.columns:
            continue
        mask = df["Type"].astype(str).str.strip().str.lower() == type_name.lower()
        subset = df[mask].copy()
        subset["_source"] = sheet_name
        results.append(subset)
    return pd.concat(results, ignore_index=True, sort=False) if results else pd.DataFrame()


# ── Hero stat analysis ───────────────────────────────────────────────────────

STAT_COLUMNS = ["Health", "Might", "Speed", "Luck", "Arcana"]


def stat_summary(sheets: Optional[dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """
    Per-stat summary across all heroes: mean, median, min, max, std.

    Useful for spotting outliers and confirming balance targets.
    """
    if sheets is None:
        sheets = load_all()
    heroes = sheets["hero"]
    available = [c for c in STAT_COLUMNS if c in heroes.columns]
    return heroes[available].agg(["mean", "median", "min", "max", "std"]).round(2)


def heroes_by_origin(
    sheets: Optional[dict[str, pd.DataFrame]] = None,
    stat: str = "Health",
) -> pd.DataFrame:
    """
    Group heroes by Origin and show stat distribution. Useful for checking
    things like "Imanis heroes all have at least 5 Health."
    """
    if sheets is None:
        sheets = load_all()
    heroes = sheets["hero"]
    if "Origin" not in heroes.columns or stat not in heroes.columns:
        return pd.DataFrame()
    return (
        heroes.groupby("Origin")[stat]
        .agg(["count", "mean", "min", "max"])
        .round(2)
        .sort_values("mean", ascending=False)
    )


# ── Live analytics (Flask hookup) ────────────────────────────────────────────

DEFAULT_ANALYTICS_URL = "http://localhost:5050"


def live_heroes(base_url: str = DEFAULT_ANALYTICS_URL) -> pd.DataFrame:
    """
    Fetch live hero pick/defeat stats from the analytics server.

    Requires backend/analytics_server.py to be running.

    Returns DataFrame with columns: hero_name, role, pick_count,
    defeat_count, avg_defeat_turn.
    """
    try:
        resp = requests.get(f"{base_url}/api/heroes", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        return pd.DataFrame(data.get("heroes", []))
    except requests.RequestException as e:
        print(f"[live_heroes] Analytics server not reachable: {e}")
        print(f"[live_heroes] Start it with: python backend/analytics_server.py")
        return pd.DataFrame()


def live_sessions(base_url: str = DEFAULT_ANALYTICS_URL) -> pd.DataFrame:
    """Fetch all playtest sessions from the analytics server."""
    try:
        resp = requests.get(f"{base_url}/api/sessions", timeout=3)
        resp.raise_for_status()
        return pd.DataFrame(resp.json().get("sessions", []))
    except requests.RequestException as e:
        print(f"[live_sessions] Analytics server not reachable: {e}")
        return pd.DataFrame()


def merged_hero_view(
    sheets: Optional[dict[str, pd.DataFrame]] = None,
    base_url: str = DEFAULT_ANALYTICS_URL,
) -> pd.DataFrame:
    """
    Merge static hero data with live playtest stats.

    Returns one row per hero with base stats AND pick/defeat counts.
    Heroes with no playtest data get 0 for pick_count/defeat_count.
    """
    if sheets is None:
        sheets = load_all()
    heroes = sheets["hero"].copy()
    live = live_heroes(base_url)

    if live.empty:
        heroes["pick_count"] = 0
        heroes["defeat_count"] = 0
        heroes["avg_defeat_turn"] = None
        return heroes

    # Aggregate by hero name (both Champion and Henchman roles combined)
    live_agg = live.groupby("hero_name").agg(
        pick_count=("pick_count", "sum"),
        defeat_count=("defeat_count", "sum"),
        avg_defeat_turn=("avg_defeat_turn", "mean"),
    ).reset_index()

    # Merge on the hero's visible name (Nickname column)
    name_col = "Nickname" if "Nickname" in heroes.columns else "Name"
    return heroes.merge(
        live_agg,
        left_on=name_col,
        right_on="hero_name",
        how="left",
    ).fillna({"pick_count": 0, "defeat_count": 0})
