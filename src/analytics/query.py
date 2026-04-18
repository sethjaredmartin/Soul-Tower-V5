"""
src/analytics/query.py

Reusable pandas query helpers for Soul Tower analytics.

The goal: open a Jupyter notebook, import this module, and have a clean
interface to every piece of game data without writing CSV parsing or
JSON loading boilerplate in every cell.

How it works:

1. `load(sheet_name)` reads the cache JSON for one sheet and returns a DataFrame.
2. `load_all()` loads every sheet into a single dict of DataFrames.
3. `find_ability(name)` searches every sheet's effect columns for a keyword
   and returns a unified view across sources.
4. `convert_cost(cost_str)` parses card cost expressions like "2d4" and
   returns numeric bounds.
5. `with_live_analytics()` optionally merges static card data with live
   event data from the Flask analytics server.

This is a teaching file. Every function is commented so you can read it
top to bottom and understand both what it does and why. Feel free to
extend it. When you add a new helper, add a docstring that explains the
shape of the input and output, then add it to the `__all__` list at the
bottom.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Union

import pandas as pd


# ── Configuration ─────────────────────────────────────────────────────────────
# If your cache lives somewhere other than soul_tower/data/cache, adjust this.
# The default assumes this file lives at src/analytics/query.py.

_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# The canonical list of sheets. Order matches the pipeline config.
SHEETS = ["hero", "common_cards", "legendary", "calamity", "villain"]

# Columns that may contain ability text, by sheet. Used by find_ability().
# When a new column is added to a sheet, add it here.
ABILITY_COLUMNS = {
    "hero":         ["Passive", "Passive Effect"],
    "common_cards": ["Effect", "Effect 1", "Effect 2", "Effect 3", "Effect 4"],
    "legendary":    ["Effect", "Effect 1", "Effect 2", "Effect 3", "Effect 4"],
    "calamity":     ["Effect", "Curse Source", "Hint"],
    "villain":      ["Passive", "Effect"],
}

# Columns that identify a row uniquely, for display purposes.
NAME_COLUMNS = {
    "hero":         "Nickname",
    "common_cards": "Name",
    "legendary":    "Name",
    "calamity":     "Name",
    "villain":      "Name",
}


# ── Loading helpers ───────────────────────────────────────────────────────────

def load(sheet_name: str, cache_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load a single sheet from cache.

    Parameters
    ----------
    sheet_name : str
        One of SHEETS ('hero', 'common_cards', 'legendary', 'calamity', 'villain').
    cache_dir : Path, optional
        Override the cache directory. Defaults to soul_tower/data/cache.

    Returns
    -------
    pd.DataFrame
        One row per entity. Missing cells become NaN.

    Raises
    ------
    FileNotFoundError
        If the cache file does not exist. Run `python main.py --fresh` first.
    """
    cache_dir = cache_dir or CACHE_DIR
    path = cache_dir / f"{sheet_name}.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Cache file not found: {path}\n"
            f"Run your Python pipeline with --fresh to populate the cache."
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(data)


def load_all(cache_dir: Optional[Path] = None) -> dict[str, pd.DataFrame]:
    """
    Load every sheet into a dict keyed by sheet name.

    Useful in notebook cells where you want all five DataFrames available:

        sheets = query.load_all()
        sheets['hero']           # heroes
        sheets['common_cards']   # commons
    """
    return {name: load(name, cache_dir) for name in SHEETS}


# ── Cost conversion ───────────────────────────────────────────────────────────

def convert_cost(cost_str: Union[str, int, float]) -> dict:
    """
    Parse a card cost string and return its bounds.

    Costs in Soul Tower can be:
      - A simple number: "3"
      - A die expression: "2d4"  (roll 2 four-sided dice, sum)
      - Mixed: "1d4+1"
      - Empty / NaN (treated as cost 0)

    Returns a dict with:
      min : int   — lowest possible cost (for die expressions, the minimum roll)
      max : int   — highest possible cost (for die expressions, the maximum roll)
      avg : float — expected value (for a player's planning)
      raw : str   — the original string
      is_die : bool — whether this cost uses dice

    Example:
      convert_cost('2d4') → {'min': 2, 'max': 8, 'avg': 5.0, 'raw': '2d4', 'is_die': True}
      convert_cost('3')   → {'min': 3, 'max': 3, 'avg': 3.0, 'raw': '3',   'is_die': False}

    This is the function the TTS Play Card flow will eventually use to show
    the range of possible costs before a player commits.
    """
    # Handle missing values
    if cost_str is None or (isinstance(cost_str, float) and pd.isna(cost_str)):
        return {"min": 0, "max": 0, "avg": 0.0, "raw": "", "is_die": False}

    raw = str(cost_str).strip()

    # Plain integer
    if raw.isdigit():
        n = int(raw)
        return {"min": n, "max": n, "avg": float(n), "raw": raw, "is_die": False}

    # Die expression: XdY optionally followed by +Z or -Z
    match = re.match(r"^(\d+)d(\d+)\s*([+-]\s*\d+)?$", raw)
    if match:
        num_dice = int(match.group(1))
        sides = int(match.group(2))
        modifier = 0
        if match.group(3):
            modifier = int(match.group(3).replace(" ", ""))

        min_val = num_dice + modifier           # all 1s
        max_val = num_dice * sides + modifier   # all max rolls
        avg = num_dice * (sides + 1) / 2 + modifier

        return {
            "min": min_val, "max": max_val, "avg": avg,
            "raw": raw, "is_die": True,
        }

    # Unknown format - return as zero so downstream math doesn't break
    return {"min": 0, "max": 0, "avg": 0.0, "raw": raw, "is_die": False}


def add_cost_columns(df: pd.DataFrame, cost_col: str = "Cost") -> pd.DataFrame:
    """
    Return a copy of df with cost_min, cost_max, cost_avg columns added.

    This makes it easy to query things like "average cost of all spells"
    without parsing strings every time.

        commons = query.load('common_cards')
        commons = query.add_cost_columns(commons)
        commons[commons['Type'] == 'Spell']['cost_avg'].mean()
    """
    df = df.copy()
    if cost_col not in df.columns:
        return df

    parsed = df[cost_col].apply(convert_cost)
    df["cost_min"] = parsed.apply(lambda d: d["min"])
    df["cost_max"] = parsed.apply(lambda d: d["max"])
    df["cost_avg"] = parsed.apply(lambda d: d["avg"])
    df["cost_is_die"] = parsed.apply(lambda d: d["is_die"])
    return df


# ── Cross-sheet queries ───────────────────────────────────────────────────────

def find_ability(
    ability: str,
    sheets: Optional[dict[str, pd.DataFrame]] = None,
    case_sensitive: bool = False,
) -> pd.DataFrame:
    """
    Find every row in every sheet that references a given ability or keyword.

    Returns a unified DataFrame with columns:
      source    — which sheet the row came from ('hero', 'legendary', etc.)
      name      — the entity's display name
      type      — card type if applicable, else ''
      subtype   — card subtype if applicable, else ''
      matched_in — which column contained the match
      snippet   — the actual text that matched

    Example:
        query.find_ability('Enchant')

        source   | name           | type   | matched_in   | snippet
        hero     | Dodan          |        | Passive      | 'Your Cards with Equip...'
        common   | Iron Crown     | Ritual | Effect 1     | 'Enchant: Wake Up: ...'
        legend   | Dodans Anvil   | Brutal | Effect 2     | 'Enchant: Deal 2 Foe'

    This is the single most powerful exploration function. Start here when
    you want to see every card that does something.
    """
    sheets = sheets or load_all()
    results = []

    pattern = re.compile(re.escape(ability), 0 if case_sensitive else re.IGNORECASE)

    for sheet_name, df in sheets.items():
        name_col = NAME_COLUMNS.get(sheet_name)
        ability_cols = ABILITY_COLUMNS.get(sheet_name, [])

        for col in ability_cols:
            if col not in df.columns:
                continue

            # Filter to rows where this column contains the pattern
            mask = df[col].astype(str).str.contains(pattern, na=False)
            matches = df[mask]

            for _, row in matches.iterrows():
                results.append({
                    "source":     sheet_name,
                    "name":       row.get(name_col, "?") if name_col else "?",
                    "type":       row.get("Type", ""),
                    "subtype":    row.get("Subtype", ""),
                    "origin":     row.get("Origin", ""),
                    "cursed":     row.get("Cursed", ""),
                    "matched_in": col,
                    "snippet":    str(row[col])[:120],
                })

    if not results:
        return pd.DataFrame(columns=[
            "source", "name", "type", "subtype", "origin",
            "cursed", "matched_in", "snippet",
        ])

    return pd.DataFrame(results)


def by_origin(
    sheet_name: str,
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Group a sheet by its Origin column and return summary stats.

    For heroes, this shows average stats per origin (useful for checking
    that Imanis heroes meet the 5 Health minimum, for example).
    For cards, this shows count and average cost per origin.
    """
    df = load(sheet_name, cache_dir)

    if "Origin" not in df.columns:
        raise ValueError(f"Sheet '{sheet_name}' has no Origin column")

    cols_to_fix = ["Health", "Might", "Speed", "Luck", "Arcana"]

    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if sheet_name == "hero":
        # Average stats per origin
        return df.groupby("Origin")[["Health", "Might", "Speed", "Luck", "Arcana"]].agg(
            ["mean", "min", "max"]
        )

    # For card sheets, count and average cost
    df = add_cost_columns(df)
    return df.groupby("Origin").agg(
        count=("Name", "count"),
        avg_cost=("cost_avg", "mean"),
        min_cost=("cost_min", "min"),
        max_cost=("cost_max", "max"),
    )


def cards_by_type(cache_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Union of Common Cards, Legendary, and Crystals (if tracked) with a
    unified schema. Useful for "give me every playable card" queries.

    Returns a DataFrame with a 'card_source' column indicating origin sheet.
    """
    commons = load("common_cards", cache_dir).copy()
    commons["card_source"] = "common"

    legends = load("legendary", cache_dir).copy()
    legends["card_source"] = "legendary"

    # Align columns before concat
    all_cols = sorted(set(commons.columns) | set(legends.columns))
    for col in all_cols:
        if col not in commons.columns: commons[col] = None
        if col not in legends.columns: legends[col] = None

    combined = pd.concat([commons[all_cols], legends[all_cols]], ignore_index=True)
    return add_cost_columns(combined)


# ── Live analytics integration ────────────────────────────────────────────────

def live_hero_stats(
    flask_url: str = "http://localhost:5050",
    timeout: float = 2.0,
) -> Optional[pd.DataFrame]:
    """
    Pull live hero pick/defeat data from the Flask analytics server.

    Returns None if the server is not reachable (no exception raised).
    Use this when you want to see which heroes are getting played and
    which are getting killed across playtest sessions.

        live = query.live_hero_stats()
        heroes = query.load('hero')
        combined = heroes.merge(live, left_on='Nickname', right_on='hero_name', how='left')
    """
    try:
        import requests
        r = requests.get(f"{flask_url}/api/heroes", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return pd.DataFrame(data.get("heroes", []))
    except Exception:
        return None


def live_sessions(
    flask_url: str = "http://localhost:5050",
    timeout: float = 2.0,
) -> Optional[pd.DataFrame]:
    """
    List all playtest sessions recorded by the Flask analytics server.
    """
    try:
        import requests
        r = requests.get(f"{flask_url}/api/sessions", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return pd.DataFrame(data.get("sessions", []))
    except Exception:
        return None


def with_live_analytics(
    sheet_name: str = "hero",
    flask_url: str = "http://localhost:5050",
) -> pd.DataFrame:
    """
    Load the static sheet data and merge live analytics where possible.

    Currently only supports 'hero' — for other sheets, returns the static
    DataFrame with a note. As analytics endpoints grow (damage per card,
    calamity trigger rates, etc.), extend this function.
    """
    static = load(sheet_name)

    if sheet_name == "hero":
        live = live_hero_stats(flask_url)
        if live is None or live.empty:
            return static
        return static.merge(live, left_on="Nickname", right_on="hero_name", how="left")

    return static


# ── Convenience: summary cell for notebooks ───────────────────────────────────

def summary():
    """
    Print a quick summary of what's in the cache.

    Call this at the top of a notebook to confirm everything loaded.
    """
    print("Soul Tower cache summary")
    print("=" * 40)
    for name in SHEETS:
        try:
            df = load(name)
            print(f"  {name:20s} {len(df):4d} rows   cols: {list(df.columns)[:5]}...")
        except FileNotFoundError:
            print(f"  {name:20s} <not cached>")
    print()
    print(f"Cache dir: {CACHE_DIR}")


__all__ = [
    "load", "load_all",
    "convert_cost", "add_cost_columns",
    "find_ability", "by_origin", "cards_by_type",
    "live_hero_stats", "live_sessions", "with_live_analytics",
    "summary",
    "SHEETS", "CACHE_DIR",
]
