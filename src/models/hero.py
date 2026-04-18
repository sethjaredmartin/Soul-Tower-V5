"""
src/models/hero.py
Dataclass representing a Hero as loaded from the spreadsheet.
This is the canonical Python representation of a Hero — all other
pipeline stages read from and write to this structure.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HeroStats:
    """The five core stats for any Hero."""
    health:  int = 0
    might:   int = 0
    speed:   int = 0
    luck:    int = 0
    arcana:  int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "Health": self.health,
            "Might":  self.might,
            "Speed":  self.speed,
            "Luck":   self.luck,
            "Arcana": self.arcana,
        }

    @classmethod
    def from_row(cls, row: dict) -> "HeroStats":
        """Parse stats from a raw CSV row dict."""
        def _int(key: str) -> int:
            try:
                return int(row.get(key, 0))
            except (ValueError, TypeError):
                return 0
        return cls(
            health = _int("Health"),
            might  = _int("Might"),
            speed  = _int("Speed"),
            luck   = _int("Luck"),
            arcana = _int("Arcana"),
        )


@dataclass
class Hero:
    """
    A single Hero as defined in the spreadsheet.

    game_name   — snake_case unique identifier (e.g. 'akiem')
    nickname    — short display name used in TTS hover (e.g. 'Akiem')
    full_name   — full lore name (e.g. 'Akiem, Reaper of Peace')
    alignment   — 'Blessed' or 'Cursed'
    origin      — the Hero's origin identifier
    stats       — HeroStats dataclass
    card1_name  — Visible Name of first Legendary card
    card2_name  — Visible Name of second Legendary card
    raw_row     — the original CSV row dict, preserved for reference
    """

    game_name:  str
    nickname:   str
    full_name:  str
    alignment:  str
    origin:     str
    stats:      HeroStats
    card1_name: str = ""
    card2_name: str = ""
    raw_row:    dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_row(cls, row: dict) -> "Hero":
        """Build a Hero from a raw CSV row dict."""
        return cls(
            game_name  = row.get("Game Name", "").strip(),
            nickname   = row.get("Nickname", "").strip(),
            full_name  = row.get("Name", "").strip(),
            alignment  = row.get("Alignment", "").strip(),
            origin     = row.get("Origin", "").strip(),
            stats      = HeroStats.from_row(row),
            card1_name = row.get("Card1 Name", "").strip(),
            card2_name = row.get("Card2 Name", "").strip(),
            raw_row    = row,
        )

    def to_lua_values(self) -> list[str]:
        """
        Returns the ordered list of values for the Lua data block.
        Order must match SHEET_COLUMNS['Hero'] in config.py.
        """
        return [
            str(self.stats.health),
            str(self.stats.might),
            str(self.stats.speed),
            str(self.stats.luck),
            str(self.stats.arcana),
            self.card1_name,
            self.card2_name,
            self.alignment,
        ]

    def to_lua_named(self) -> dict[str, str]:
        """Returns a named dict for the Lua data block (Beta format)."""
        return {
            "Health":    str(self.stats.health),
            "Might":     str(self.stats.might),
            "Speed":     str(self.stats.speed),
            "Luck":      str(self.stats.luck),
            "Arcana":    str(self.stats.arcana),
            "Card1":     self.card1_name,
            "Card2":     self.card2_name,
            "Alignment": self.alignment,
        }
