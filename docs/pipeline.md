# Soul Tower Data Pipeline

## Overview

The data pipeline transforms Soul Tower spreadsheet data into Lua data blocks used by Tabletop Simulator objects. It is designed to be modular, cached, and Flask-ready for future HTTP-based triggering.

---

## Pipeline Stages

```
Google Sheets (CSV)
        │
        ▼
   [fetcher.py]          ← HTTP request, CSV parsing, row filtering
        │
        ▼
   [store.py]            ← local JSON cache read/write
        │
        ▼
   [registry.py]         ← parse raw rows into typed models, lookup methods
        │
        ▼
   [transformer.py]      ← models → Lua data block strings
        │
        ▼
  data/game_lua_data/    ← .lua files ready for TTS injection
```

---

## Running the Pipeline

```bash
# Use cache if available, generate all Lua blocks
python main.py

# Force fresh fetch from Google Sheets
python main.py --fresh

# Only process one sheet
python main.py --sheet Hero

# Use named key format (Beta — more readable)
python main.py --named

# Fresh fetch, named format, Heroes only
python main.py --fresh --sheet Hero --named
```

---

## File Responsibilities

| File | Responsibility |
|------|---------------|
| `config.py` | All URLs, column mappings, paths, constants |
| `src/pipeline/fetcher.py` | HTTP requests, CSV parsing |
| `src/pipeline/store.py` | Local cache read/write |
| `src/pipeline/registry.py` | Single source of truth, model lookups |
| `src/pipeline/transformer.py` | Models → Lua string generation |
| `src/models/*.py` | Typed dataclasses per game entity |
| `main.py` | CLI entry point |

---

## Adding a New Sheet

1. Add the URL to `SHEET_URLS` in `config.py`
2. Add the columns to `SHEET_COLUMNS` in `config.py`
3. Add the key field to `SHEET_KEY_FIELD` in `config.py`
4. Create a dataclass in `src/models/` with `from_row()`, `to_lua_values()`, and `to_lua_named()`
5. Add a `load_*` method and lookup methods to `registry.py`
6. Add the sheet to the processing loop in `main.py`

---

## Cache Behavior

- Cache files live in `data/cache/<sheet_name>.json`
- When `USE_CACHE = True` in `config.py` and a cache file exists, the pipeline reads from cache instead of fetching live
- `--fresh` flag clears the cache before running
- If a live fetch fails, the pipeline falls back to the stale cache with a warning
- This means the pipeline can run offline as long as at least one successful fetch has been made

---

## Lua Output Formats

### Alpha Format (positional)
```lua
local info = {
    ["Akiem"] = {"3", "4", "6", "3", "2", "Demise of the Blight", "Message for Peace", "Blessed"},
}
```

### Beta Format (named keys — `--named` flag)
```lua
local info = {
    ["Akiem"] = {Health="3", Might="4", Speed="6", Luck="3", Arcana="2", Card1="Demise of the Blight", Card2="Message for Peace", Alignment="Blessed"},
}
```

Named format is preferred for Beta — it makes debugging significantly easier and removes the risk of positional index errors.

---

## Flask Integration (Future)

The registry and transformer are stateless enough to be called from Flask routes directly:

```python
# Future: src/api/routes.py
from flask import Flask, jsonify
from src.pipeline.registry import GameRegistry
from src.pipeline.transformer import build_block

app = Flask(__name__)
registry = GameRegistry()

@app.route("/api/block/<sheet_name>")
def get_block(sheet_name):
    registry.load_all()
    models = registry.get_raw_rows(sheet_name)
    lua = build_block(sheet_name, models)
    return jsonify({"lua": lua})
```

The pipeline is also accessible from TTS via `localhost` requests using TTS's `WebRequest` API — the same approach used in earlier prototypes.
