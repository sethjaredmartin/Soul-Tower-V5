"""
src/pipeline/transformer.py
Transforms parsed game data models into Lua data block scripts.

This is the only place in the pipeline that knows about Lua syntax.
It takes typed models from the registry and produces valid Lua strings
that can be written to files or injected into TTS JSON objects.

The output format for each block is:
    local info = {
        ["KeyName"] = {field1, field2, ...},
        ...
    }
    function giveInfo(key)
        return info[key]
    end

Named key format (Beta — more readable, easier to debug):
    local info = {
        ["KeyName"] = {Health="3", Might="4", ...},
        ...
    }
"""

from typing import Union
from pathlib import Path

from config import LUA_DIR, SHEET_KEY_FIELD
from src.models.hero import Hero
from src.models.card import Card, LegendaryCard
from src.models.calamity import Calamity
from src.models.villain import Villain

# Type alias for any model that can be transformed
GameModel = Union[Hero, Card, LegendaryCard, Calamity, Villain]


# ── Public API ────────────────────────────────────────────────────────────────

def build_block(
    sheet_name: str,
    models: list[GameModel],
    named: bool = False,
) -> str:
    """
    Build a complete Lua data block string from a list of models.

    Args:
        sheet_name: Used to determine the lookup key field.
        models:     List of parsed model instances.
        named:      If True, use named keys (Beta format).
                    If False, use positional list (Alpha format).

    Returns:
        A Lua script string ready to be written to a file or injected.
    """
    lines = ["local info = {"]

    for model in models:
        key = _get_key(model, sheet_name)
        if not key:
            continue

        if named:
            values_str = _named_values(model)
        else:
            values_str = _positional_values(model)

        lines.append(f'    ["{key}"] = {{{values_str}}},')

    lines.append("}")
    lines.append("")
    lines.append("function giveInfo(key)")
    lines.append("    return info[key]")
    lines.append("end")
    lines.append("")
    lines.append("return giveInfo")
    lines.append("")

    return "\n".join(lines)


def write_block(
    sheet_name: str,
    models: list[GameModel],
    named: bool = False,
) -> Path:
    """
    Build and write a Lua data block to the game_lua_data directory.

    Args:
        sheet_name: Used for the filename and key field lookup.
        models:     List of parsed model instances.
        named:      If True, use named keys (Beta format).

    Returns:
        Path to the written .lua file.
    """
    lua_code = build_block(sheet_name, models, named=named)
    slug = sheet_name.lower().replace(" ", "_")
    path = LUA_DIR / f"{slug}_data_block.lua"

    with open(path, "w", encoding="utf-8") as f:
        f.write(lua_code)

    print(f"Wrote Lua block ({len(models)} entries) → {path}")
    return path


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _get_key(model: GameModel, sheet_name: str) -> str:
    """
    Get the lookup key for a model based on the sheet's key field.
    Heroes use Nickname, everything else uses Name/game_name.
    """
    key_field = SHEET_KEY_FIELD.get(sheet_name, "Name")

    if key_field == "Nickname" and hasattr(model, "nickname"):
        return model.nickname
    if hasattr(model, "name"):
        return model.name
    return ""


def _positional_values(model: GameModel) -> str:
    """
    Format model values as a positional Lua list.
    e.g. "3", "4", "6", "3", "2", "Card One", "Card Two", "Blessed"
    """
    values = model.to_lua_values()
    return ", ".join(f'"{_escape(v)}"' for v in values)


def _named_values(model: GameModel) -> str:
    """
    Format model values as named Lua key-value pairs.
    e.g. Health="3", Might="4", Speed="6"
    """
    named = model.to_lua_named()
    pairs = [f'{k}="{_escape(v)}"' for k, v in named.items()]
    return ", ".join(pairs)


def _escape(value: str) -> str:
    """Escape double quotes and backslashes in Lua string values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
