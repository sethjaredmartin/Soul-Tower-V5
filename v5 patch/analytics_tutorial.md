# Analytics Tutorial

This document walks through the analytics system piece by piece. Read it in order the first time. Skim it later when you want to extend or debug.

## What you got

Two files:

- `src/analytics/query.py` — a library of reusable pandas functions
- `src/analytics/notebook.ipynb` — a Jupyter notebook that uses the library

The library does the work. The notebook is where you ask questions.

## Why split it this way

When you open a notebook and paste in thirty lines of boilerplate just to load a CSV, your exploration gets buried in setup. By putting the boilerplate in `query.py`, the notebook becomes what it should be: a sequence of questions and their answers.

If a new question becomes something you ask repeatedly, you move it from the notebook into `query.py` as a function. The library grows. The notebook stays clean.

## Running the notebook

From the project root:

```bash
pip install pandas jupyter requests
jupyter notebook src/analytics/notebook.ipynb
```

If your cache is empty, run your Python pipeline first:

```bash
python main.py --fresh
```

This pulls the latest data from Google Sheets and writes it to `data/cache/*.json`. The notebook reads from this cache — it does not hit the live sheets. That means you can work offline and your exploration doesn't slow down every time you rerun a cell.

## The query module, top to bottom

### Section 1: Loading

```python
query.load('hero')       # Returns the Hero DataFrame
query.load_all()         # Returns a dict of all five DataFrames
```

Under the hood, `load()` reads `data/cache/<sheet_name>.json` into memory and hands pandas the list of dicts. The file must exist — if it doesn't, you get a clear error telling you to run the pipeline first.

`load_all()` is just `load()` called five times. Nothing fancy.

### Section 2: Cost conversion

Card costs are strings in the spreadsheet. Most are plain numbers. Some are die expressions like `"2d4"`.

```python
query.convert_cost("2d4")
# → {'min': 2, 'max': 8, 'avg': 5.0, 'raw': '2d4', 'is_die': True}

query.convert_cost("3")
# → {'min': 3, 'max': 3, 'avg': 3.0, 'raw': '3',   'is_die': False}
```

`query.add_cost_columns(df)` applies this to an entire DataFrame, adding `cost_min`, `cost_max`, `cost_avg`, and `cost_is_die` columns. Once those exist, standard pandas aggregation works:

```python
costed = query.add_cost_columns(commons)
costed.groupby('Type')['cost_avg'].mean()
```

The regex in `convert_cost()` handles `XdY`, `XdY+Z`, and `XdY-Z`. If you ever need to support more complex cost expressions (two dice of different sizes, for example), extend the regex and add a test case in the notebook.

### Section 3: Ability search

This is the function you'll use most often.

```python
query.find_ability('Enchant')
```

Returns a DataFrame with one row per match, across every effect column in every sheet. The columns are:

- `source` — which sheet ('hero', 'common_cards', 'legendary', 'calamity', 'villain')
- `name` — the entity's display name
- `type`, `subtype`, `origin`, `cursed` — from that row, where applicable
- `matched_in` — the specific column the match was found in
- `snippet` — the first 120 characters of the matched text

The function is driven by two constants at the top of `query.py`:

```python
ABILITY_COLUMNS = {
    "hero":         ["Passive", "Passive Effect"],
    "common_cards": ["Effect", "Effect 1", "Effect 2", ...],
    ...
}

NAME_COLUMNS = {
    "hero":         "Nickname",
    "common_cards": "Name",
    ...
}
```

**When you add a new effect column to a sheet, add it to `ABILITY_COLUMNS`.** Otherwise searches won't look there.

**When you rename a sheet or add a new one**, update the `SHEETS` list at the top of `query.py` and add entries to `ABILITY_COLUMNS` and `NAME_COLUMNS`.

### Section 4: Grouping

```python
query.by_origin('hero')        # average stats per origin for heroes
query.by_origin('common_cards') # count and cost ranges for cards
query.cards_by_type()           # unions commons and legendary with a card_source column
```

`by_origin()` branches on sheet name. For Heroes, it averages the five stats. For anything else, it counts and shows cost ranges. If you add a Villain sheet grouping, extend the function.

`cards_by_type()` is useful when you want to treat commons and legendaries as one dataset. It handles the column alignment so you don't get NaN chaos.

### Section 5: Live analytics

```python
query.live_sessions()        # DataFrame of playtest sessions, or None
query.live_hero_stats()      # DataFrame of hero pick/defeat data, or None
query.with_live_analytics('hero')  # static data merged with live stats
```

These hit your Flask analytics server at `localhost:5050` by default. If the server is down, they return `None` silently — no exceptions, no broken notebook cells. This is intentional: you should be able to run the notebook offline.

## The notebook, section by section

### Section 1: Setup

Adds the project root to `sys.path` so `from src.analytics import query` works. Sets pandas display options so DataFrames don't get truncated. Calls `query.summary()` which prints a one-line status for each sheet, so you know immediately if something failed to cache.

### Section 2: Load everything

Loads all five DataFrames at once. After this cell, `heroes`, `commons`, `legends`, `calams`, and `villains` are available throughout the notebook.

### Section 3: Peek at one sheet

`.head()` shows the first five rows. `list(heroes.columns)` shows every column name so you know what's queryable.

This is always worth running after a pipeline update, because if a column name changed, you'll see it here before it breaks something downstream.

### Section 4: Find every card that uses an ability

The showcase cell. `query.find_ability('Enchant')` and you see every Hero passive, every card effect, every calamity text that mentions Enchant, across every sheet.

The follow-up cells show two common next steps: filter by source (`source == 'legendary'` gets you just Legendary cards), or group by source to see counts.

### Section 5: Card cost analysis

Takes the `commons` DataFrame and runs it through `add_cost_columns()`. Now you can do things like "average cost per card type" in a single pandas expression.

The "which cards use die-based costs" cell is useful for QA — it shows you every card where the TTS cost display needs to handle a range.

### Section 6: All playable cards

Unions commons and legendary into one DataFrame. Useful when you want to see patterns across the whole card pool without writing two queries.

### Section 7: Group by Origin

First shows you the aggregated view. Then has two cells that specifically check the Imanis 5-Health rule — one that shows you the Imanis heroes, one that flags any violations. This pattern (show data, then flag violations) is how you should write all your data validation checks.

### Section 8: Find cards a specific Hero connects to

A tiny helper function defined inline. Shows that simple queries don't need to live in `query.py` — inline helpers are fine for notebook-specific exploration.

### Section 9: Live analytics hook

Tests whether the Flask server is reachable and shows you sessions if so. The cell gracefully handles the offline case.

### Section 10: Your scratchpad

Empty cells and examples for your own exploration. When you write something here that you'll want to reuse, move it to `query.py`.

## How to add a new analytics function

Let's say you want a function that shows every card that does damage, with the damage amount parsed out.

### Step 1: Prototype in the notebook

Open a scratchpad cell and write it there first:

```python
import re

def damage_cards():
    all_cards = query.cards_by_type()
    results = []
    for _, row in all_cards.iterrows():
        for col in ['Effect 1', 'Effect 2', 'Effect 3', 'Effect 4']:
            if col not in row or pd.isna(row[col]):
                continue
            match = re.search(r'Deal (\d+)', str(row[col]))
            if match:
                results.append({
                    'name': row['Name'],
                    'type': row['Type'],
                    'damage': int(match.group(1)),
                    'effect': row[col]
                })
    return pd.DataFrame(results)

damage_cards().nlargest(10, 'damage')
```

Run it. Refine until it gives you what you want.

### Step 2: Promote it to query.py

Open `src/analytics/query.py` and add it as a proper function:

```python
def find_damage_cards(min_damage: int = 0) -> pd.DataFrame:
    """
    Return every card with a 'Deal N' effect, where N >= min_damage.

    Returns columns: name, type, damage, effect.
    """
    all_cards = cards_by_type()
    results = []
    for _, row in all_cards.iterrows():
        for col in ["Effect 1", "Effect 2", "Effect 3", "Effect 4"]:
            if col not in row or pd.isna(row[col]):
                continue
            match = re.search(r"Deal (\d+)", str(row[col]))
            if match:
                dmg = int(match.group(1))
                if dmg >= min_damage:
                    results.append({
                        "name":   row["Name"],
                        "type":   row["Type"],
                        "damage": dmg,
                        "effect": str(row[col])[:80],
                    })
    return pd.DataFrame(results)
```

### Step 3: Add it to `__all__`

At the bottom of `query.py`:

```python
__all__ = [
    ...
    "find_damage_cards",
]
```

### Step 4: Restart the notebook kernel

Jupyter caches imports. After editing `query.py`, click Kernel → Restart and rerun the setup cell. Now `query.find_damage_cards()` works in any cell.

## Debugging

**"FileNotFoundError: Cache file not found"**
Run `python main.py --fresh` to populate the cache. If that fails, your sheet URLs in `config.py` are probably empty or broken.

**"KeyError: 'Some Column'"**
The column name changed in the spreadsheet. Open the JSON file in `data/cache/` directly and look at the keys — that's ground truth. Update `ABILITY_COLUMNS` or whatever referenced the old name.

**Live analytics returns None even when Flask is running**
Check that Flask is on port 5050. Check that the endpoints exist (`/api/sessions`, `/api/heroes`). The function catches every exception and returns None, which is intentional but can hide real errors. If you're stuck, temporarily remove the try/except to see the actual error.

**Changes to `query.py` don't show up in the notebook**
Restart the kernel. Python caches imports.

**Everything is NaN**
Usually means the JSON cache is empty or malformed. Check `data/cache/<sheet>.json` directly — it should be a list of dicts, not a dict with one key.

## What comes next

With the analytics foundation in place, the natural next pieces are:

1. **The Python tagger** (`src/tts/tagger.py`) that reads the cache and adds tags to TTS JSON objects. This is where TAGS.md earns its keep.

2. **The JSON patcher** (`src/tts/json_patcher.py`) that takes a TTS save file, finds every Hero card, Common card, and Legendary card, and writes their tags into the GMNotes and Tags fields.

3. **The Lua TagRegistry** that mirrors the vocabulary for TTS-side queries.

You can keep using the notebook throughout — it becomes your sanity check. After running the tagger, the notebook can also verify coverage: "did every Hero card get a `Hero` tag?"
