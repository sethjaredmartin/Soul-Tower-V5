"""
config.py
Central configuration for the Soul Tower data pipeline.
All sheet URLs, column mappings, file paths, and constants live here.
Adding a new sheet means adding it here — nothing else needs to change.
"""

from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).parent
DATA_DIR   = ROOT_DIR / "data"
CACHE_DIR  = DATA_DIR / "cache"
LUA_DIR    = DATA_DIR / "game_lua_data"
DOCS_DIR   = ROOT_DIR / "docs"

# Ensure directories exist
for _dir in [CACHE_DIR, LUA_DIR, DOCS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ── Google Sheet Published CSV URLs ───────────────────────────────────────────
# Each key matches the sheet's canonical name used throughout the pipeline.
# Set these to your actual published CSV URLs.

SHEET_URLS: dict[str, str] = {
    "Hero":         "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFZHLVSPZY2WDUPRW2V9alQtJNhofrrheyro8akAIbUIZ7Ls1kFQ_iCLtOYUjIbjCTVgQ8x3Mvbm3H/pub?gid=1026068971&single=true&output=csv",   # TODO: add URL
    "Common Cards": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFZHLVSPZY2WDUPRW2V9alQtJNhofrrheyro8akAIbUIZ7Ls1kFQ_iCLtOYUjIbjCTVgQ8x3Mvbm3H/pub?gid=415672083&single=true&output=csv",   # TODO: add URL
    "Legendary":    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFZHLVSPZY2WDUPRW2V9alQtJNhofrrheyro8akAIbUIZ7Ls1kFQ_iCLtOYUjIbjCTVgQ8x3Mvbm3H/pub?gid=848380877&single=true&output=csv",   # TODO: add URL
    "Calamity":     "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFZHLVSPZY2WDUPRW2V9alQtJNhofrrheyro8akAIbUIZ7Ls1kFQ_iCLtOYUjIbjCTVgQ8x3Mvbm3H/pub?gid=1104042&single=true&output=csv",   # TODO: add URL
    "Villain":      "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFZHLVSPZY2WDUPRW2V9alQtJNhofrrheyro8akAIbUIZ7Ls1kFQ_iCLtOYUjIbjCTVgQ8x3Mvbm3H/pub?gid=19054288&single=true&output=csv",   # TODO: add URL
}


# ── Column Mappings ───────────────────────────────────────────────────────────
# Defines which columns from each sheet are included in the Lua data block.
# Order matters — this determines the named key order in the output.

SHEET_COLUMNS: dict[str, list[str]] = {
    "Hero": [
        "Health", "Might", "Speed", "Luck", "Arcana",
        "Card1 Name", "Card2 Name", "Alignment",
    ],
    "Common Cards": [
        "Origin", "Type", "Subtype", "Cost",
        "Flavor Text", "Cursed", "Villain Default",
    ],
    "Legendary": [
        "Origin", "Type", "Subtype", "Cost",
        "Flavor Text", "Cursed", "Villain Default",
    ],
    "Calamity": [
        "Curse Source", "Hint",
    ],
    "Villain": [
        "Origin",
    ],
}


# ── Key Field Names ───────────────────────────────────────────────────────────
# The field used as the primary lookup key in each Lua data block.
# For most sheets this is "Name". Heroes use "Nickname" since that's
# what appears in TTS as the object's display name.

SHEET_KEY_FIELD: dict[str, str] = {
    "Hero":         "Nickname",
    "Common Cards": "Name",
    "Legendary":    "Name",
    "Calamity":     "Name",
    "Villain":      "Name",
}


# ── Game Name Field ───────────────────────────────────────────────────────────
# The column that holds the snake_case unique identifier used for
# image filenames, GMNotes, and internal lookups.

GAME_NAME_FIELD = "Game Name"


# ── Hero Stats ────────────────────────────────────────────────────────────────

HERO_STATS = ["Health", "Might", "Speed", "Luck", "Arcana"]


# ── TTS Player/Henchman Colors ────────────────────────────────────────────────

CHAMPION_COLORS  = ["Yellow", "Red", "Pink", "Orange"]
HENCHMAN_COLORS  = ["Green", "Teal", "Blue", "Purple"]
VILLAIN_COLOR    = "White"

ALL_COLORS = CHAMPION_COLORS + HENCHMAN_COLORS + [VILLAIN_COLOR]


# ── Cache Settings ────────────────────────────────────────────────────────────

# When True, pipeline reads from local cache instead of fetching live.
# Set to False to force a fresh fetch and overwrite the cache.
USE_CACHE = True

# Cache file extension
CACHE_EXT = ".json"


# ── Request Settings ──────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 30  # seconds
