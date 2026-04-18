"""
src/models/villain.py
Dataclass representing a Villain.
"""

from dataclasses import dataclass, field


@dataclass
class Villain:
    game_name: str
    name:      str
    origin:    str = ""
    raw_row:   dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_row(cls, row: dict) -> "Villain":
        return cls(
            game_name = row.get("Game Name", "").strip(),
            name      = row.get("Name", "").strip(),
            origin    = row.get("Origin", "").strip(),
            raw_row   = row,
        )

    def to_lua_named(self) -> dict[str, str]:
        return {"Origin": self.origin}

    def to_lua_values(self) -> list[str]:
        return [self.origin]
