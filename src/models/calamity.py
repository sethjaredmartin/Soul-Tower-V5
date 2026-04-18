"""
src/models/calamity.py
Dataclass representing a Calamity card.
"""

from dataclasses import dataclass, field


@dataclass
class Calamity:
    game_name:    str
    name:         str
    curse_source: str = ""
    hint:         str = ""
    raw_row:      dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_row(cls, row: dict) -> "Calamity":
        return cls(
            game_name    = row.get("Game Name", "").strip(),
            name         = row.get("Name", "").strip(),
            curse_source = row.get("Curse Source", "").strip(),
            hint         = row.get("Hint", "").strip(),
            raw_row      = row,
        )

    def to_lua_named(self) -> dict[str, str]:
        return {
            "CurseSource": self.curse_source,
            "Hint":        self.hint,
        }

    def to_lua_values(self) -> list[str]:
        return [self.curse_source, self.hint]
