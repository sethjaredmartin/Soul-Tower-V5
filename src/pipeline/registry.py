"""
src/pipeline/registry.py
GameRegistry — the single source of truth for all game data in the pipeline.

Responsibilities:
- Fetch or load raw data for each sheet
- Parse raw rows into typed dataclass models
- Provide lookup methods by game name, nickname, or other identifiers
- Never write to files or generate Lua (that's the transformer's job)

Usage:
    from src.pipeline.registry import GameRegistry
    registry = GameRegistry()
    registry.load_all()

    hero = registry.get_hero("akiem")          # by game name
    hero = registry.get_hero_by_nickname("Akiem")  # by nickname
    cards = registry.get_cards_for_hero("akiem")
"""

from typing import Optional

from config import SHEET_URLS, USE_CACHE, GAME_NAME_FIELD, SHEET_KEY_FIELD
from src.pipeline.fetcher import fetch_sheet, FetchError
from src.pipeline import store
from src.models.hero import Hero
from src.models.card import Card, LegendaryCard
from src.models.calamity import Calamity
from src.models.villain import Villain


class GameRegistry:
    """
    Central registry for all parsed game data.

    After calling load_all() (or individual load_* methods),
    all data is available via lookup methods.
    """

    def __init__(self, use_cache: bool = USE_CACHE):
        self.use_cache = use_cache

        # Parsed model stores — keyed by game_name
        self._heroes:     dict[str, Hero]          = {}
        self._cards:      dict[str, Card]           = {}
        self._legendaries:dict[str, LegendaryCard]  = {}
        self._calamities: dict[str, Calamity]       = {}
        self._villains:   dict[str, Villain]        = {}

        # Secondary indexes
        self._nickname_to_game_name: dict[str, str] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_all(self) -> None:
        """Load and parse all sheets."""
        self.load_heroes()
        self.load_cards()
        self.load_legendaries()
        self.load_calamities()
        self.load_villains()

    def load_heroes(self) -> None:
        rows = self._get_rows("Hero")
        for row in rows:
            hero = Hero.from_row(row)
            if hero.game_name:
                self._heroes[hero.game_name] = hero
                if hero.nickname:
                    self._nickname_to_game_name[hero.nickname] = hero.game_name
        print(f"Loaded {len(self._heroes)} heroes.")

    def load_cards(self) -> None:
        rows = self._get_rows("Common Cards")
        for row in rows:
            card = Card.from_row(row)
            if card.game_name:
                self._cards[card.game_name] = card
        print(f"Loaded {len(self._cards)} common cards.")

    def load_legendaries(self) -> None:
        rows = self._get_rows("Legendary")
        for row in rows:
            card = LegendaryCard.from_row(row)
            if card.game_name:
                self._legendaries[card.game_name] = card
        print(f"Loaded {len(self._legendaries)} legendary cards.")

    def load_calamities(self) -> None:
        rows = self._get_rows("Calamity")
        for row in rows:
            calamity = Calamity.from_row(row)
            if calamity.game_name:
                self._calamities[calamity.game_name] = calamity
        print(f"Loaded {len(self._calamities)} calamities.")

    def load_villains(self) -> None:
        rows = self._get_rows("Villain")
        for row in rows:
            villain = Villain.from_row(row)
            if villain.game_name:
                self._villains[villain.game_name] = villain
        print(f"Loaded {len(self._villains)} villains.")

    # ── Hero Lookups ──────────────────────────────────────────────────────────

    def get_hero(self, game_name: str) -> Optional[Hero]:
        """Look up a Hero by game name (snake_case)."""
        return self._heroes.get(game_name)

    def get_hero_by_nickname(self, nickname: str) -> Optional[Hero]:
        """Look up a Hero by their TTS display nickname."""
        game_name = self._nickname_to_game_name.get(nickname)
        if game_name:
            return self._heroes.get(game_name)
        return None

    def all_heroes(self) -> list[Hero]:
        return list(self._heroes.values())

    # ── Card Lookups ──────────────────────────────────────────────────────────

    def get_card(self, game_name: str) -> Optional[Card]:
        return self._cards.get(game_name)

    def get_card_by_name(self, visible_name: str) -> Optional[Card]:
        """Look up a card by its Visible Name (TTS hover name)."""
        for card in self._cards.values():
            if card.name == visible_name:
                return card
        return None

    def all_cards(self) -> list[Card]:
        return list(self._cards.values())

    def cards_by_type(self, card_type: str) -> list[Card]:
        """Return all cards of a given type: 'Brutal', 'Ritual', 'Spell'."""
        return [c for c in self._cards.values() if c.card_type == card_type]

    def get_cards_for_hero(self, hero_game_name: str) -> list[LegendaryCard]:
        """Return the two Legendary cards belonging to a Hero."""
        return [
            c for c in self._legendaries.values()
            if c.hero_game_name == hero_game_name
        ]

    # ── Calamity Lookups ──────────────────────────────────────────────────────

    def get_calamity(self, game_name: str) -> Optional[Calamity]:
        return self._calamities.get(game_name)

    def all_calamities(self) -> list[Calamity]:
        return list(self._calamities.values())

    # ── Villain Lookups ───────────────────────────────────────────────────────

    def get_villain(self, game_name: str) -> Optional[Villain]:
        return self._villains.get(game_name)

    def all_villains(self) -> list[Villain]:
        return list(self._villains.values())

    # ── Raw Row Access ────────────────────────────────────────────────────────

    def get_raw_rows(self, sheet_name: str) -> list[dict]:
        """Return cached raw rows for a sheet without parsing into models."""
        return self._get_rows(sheet_name)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_rows(self, sheet_name: str) -> list[dict]:
        """
        Get raw rows for a sheet.
        Uses cache if available and use_cache is True.
        Otherwise fetches live and saves to cache.
        """
        if self.use_cache and store.exists(sheet_name):
            rows = store.load(sheet_name)
            if rows is not None:
                return rows

        # Fetch live
        url = SHEET_URLS.get(sheet_name, "")
        try:
            rows = fetch_sheet(url, sheet_name)
            store.save(sheet_name, rows)
            return rows
        except FetchError as e:
            print(f"Error fetching '{sheet_name}': {e}")

            # Fall back to stale cache if available
            cached = store.load(sheet_name)
            if cached is not None:
                print(f"Using stale cache for '{sheet_name}'.")
                return cached

            return []
