"""
main.py
Entry point for the Soul Tower data pipeline.

Run this to:
  - Fetch all sheet data (or load from cache)
  - Parse into typed models
  - Generate Lua data block files

Usage:
    python main.py                  # use cache if available
    python main.py --fresh          # force re-fetch all sheets
    python main.py --sheet Hero     # only process one sheet
    python main.py --named          # use named key Lua format (Beta)
"""

import argparse
from src.pipeline.registry import GameRegistry
from src.pipeline.transformer import write_block
from src.pipeline import store


def parse_args():
    parser = argparse.ArgumentParser(description="Soul Tower data pipeline")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force re-fetch all sheets, ignoring cache",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Only process a specific sheet (e.g. 'Hero', 'Common Cards')",
    )
    parser.add_argument(
        "--named",
        action="store_true",
        help="Use named key format in Lua output (Beta format)",
    )
    return parser.parse_args()


def run(fresh: bool = False, sheet_filter: str = None, named: bool = False):
    if fresh:
        if sheet_filter:
            store.clear(sheet_filter)
        else:
            store.clear_all()

    registry = GameRegistry(use_cache=not fresh)

    # Determine which sheets to process
    all_sheets = ["Hero", "Common Cards", "Legendary", "Calamity", "Villain"]
    sheets = [sheet_filter] if sheet_filter else all_sheets

    for sheet_name in sheets:
        print(f"\n── Processing: {sheet_name} ──")

        if sheet_name == "Hero":
            registry.load_heroes()
            models = registry.all_heroes()
        elif sheet_name == "Common Cards":
            registry.load_cards()
            models = registry.all_cards()
        elif sheet_name == "Legendary":
            registry.load_legendaries()
            models = list(registry._legendaries.values())
        elif sheet_name == "Calamity":
            registry.load_calamities()
            models = registry.all_calamities()
        elif sheet_name == "Villain":
            registry.load_villains()
            models = registry.all_villains()
        else:
            print(f"Unknown sheet: {sheet_name}")
            continue

        if not models:
            print(f"No data found for '{sheet_name}' — skipping Lua generation.")
            continue

        write_block(sheet_name, models, named=named)

    print("\nDone.")


if __name__ == "__main__":
    args = parse_args()
    run(
        fresh=args.fresh,
        sheet_filter=args.sheet,
        named=args.named,
    )
