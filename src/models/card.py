"""
src/models/card.py
Dataclasses representing Cards as loaded from the spreadsheet.
Covers Common Cards and Legendary Cards.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Card:
    """
    A single card as defined in the spreadsheet.

    game_name       — snake_case unique identifier (e.g. 'copper_sword')
    name            — Visible Name displayed in TTS (e.g. 'Copper Sword')
    origin          — card origin identifier
    card_type       — 'Brutal', 'Ritual', or 'Spell'
    subtype         — 'Normal', 'Reaction', 'Instant', 'Entropy'
    cost            — raw cost string (e.g. '3', '1d6', '2d4')
    effect          — card effect text
    flavor_text     — flavor/narrative text
    is_cursed       — whether the card has the Cursed property
    is_villain_default — whether the Villain treats this as a Default card
    raw_row         — the original CSV row dict
    """

    game_name:          str
    name:               str
    origin:             str
    card_type:          str
    subtype:            str
    cost:               str
    effect:             str = ""
    flavor_text:        str = ""
    is_cursed:          bool = False
    is_villain_default: bool = False
    raw_row:            dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_row(cls, row: dict) -> "Card":
        """Build a Card from a raw CSV row dict."""
        def _bool(key: str) -> bool:
            val = row.get(key, "").strip().upper()
            return val in ("TRUE", "YES", "1", "Y")

        return cls(
            game_name          = row.get("Game Name", "").strip(),
            name               = row.get("Name", "").strip(),
            origin             = row.get("Origin", "").strip(),
            card_type          = row.get("Type", "").strip(),
            subtype            = row.get("Subtype", "").strip(),
            cost               = row.get("Cost", "0").strip(),
            effect             = row.get("Effect", "").strip(),
            flavor_text        = row.get("Flavor Text", "").strip(),
            is_cursed          = _bool("Cursed"),
            is_villain_default = _bool("Villain Default"),
            raw_row            = row,
        )

    def to_lua_named(self) -> dict[str, str]:
        """Returns a named dict for the Lua data block (Beta format)."""
        return {
            "Origin":          self.origin,
            "Type":            self.card_type,
            "Subtype":         self.subtype,
            "Cost":            self.cost,
            "FlavorText":      self.flavor_text,
            "Cursed":          str(self.is_cursed).lower(),
            "VillainDefault":  str(self.is_villain_default).lower(),
        }

    def to_lua_values(self) -> list[str]:
        """
        Returns the ordered list of values for the Lua data block.
        Order must match SHEET_COLUMNS['Common Cards'] in config.py.
        """
        return [
            self.origin,
            self.card_type,
            self.subtype,
            self.cost,
            self.flavor_text,
            str(self.is_cursed).lower(),
            str(self.is_villain_default).lower(),
        ]

    @property
    def is_reaction(self) -> bool:
        return self.subtype.startswith("Reaction")

    @property
    def is_instant(self) -> bool:
        return self.subtype == "Instant"

    @property
    def is_entropy(self) -> bool:
        return self.subtype == "Entropy"

    @property
    def converted_cost(self) -> int:
        """
        Returns the maximum possible Mana cost for Villain can_play checks.
        Dice costs (e.g. '2d4') return the maximum value (2*4=8).
        Plain integers return themselves.
        """
        cost = self.cost.strip()
        if "d" in cost:
            parts = cost.split("d")
            try:
                return int(parts[0]) * int(parts[1])
            except (ValueError, IndexError):
                return 0
        try:
            return int(cost)
        except ValueError:
            return 0


@dataclass
class LegendaryCard(Card):
    """
    A Legendary card belonging to a specific Hero.
    Inherits all Card fields and adds hero linkage.
    """
    hero_game_name: str = ""
    hero_nickname:  str = ""

    @classmethod
    def from_row(cls, row: dict) -> "LegendaryCard":
        base = Card.from_row(row)
        return cls(
            **{k: v for k, v in base.__dict__.items() if k != "raw_row"},
            hero_game_name = row.get("Hero Game Name", "").strip(),
            hero_nickname  = row.get("Hero Nickname", "").strip(),
            raw_row        = row,
        )
