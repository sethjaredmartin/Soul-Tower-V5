# CLAUDE.md — Soul Tower

## What this project is

Soul Tower is a 2-4 player deck-building RPG for Tabletop Simulator (TTS), with a parallel Unity prototype planned. Players are Summoners who manifest Heroes to fight a shared Villain defended by Henchmen. The core loop is drafting cards, building synergies, and defeating the Villain before all Summoners are eliminated.

This repository contains the full technical stack: TTS Lua scripting, a Python data pipeline, a Flask analytics server, game data management, and documentation.

Seth is the sole designer and developer.

---

## Source of truth

**Rules_Formal** is the canonical game rules document. It contains the complete rules, all gameplay mechanics, the full Codex (terminology, keywords, stats, statuses, card play, attacks, abilities A-Z), and the design prompt history. When implementing any game logic in code, always defer to Rules_Formal. If something in this CLAUDE.md conflicts with Rules_Formal, Rules_Formal wins.

Seth will notify when Rules_Formal has been updated. Check it before implementing any logic changes.

---

## Project structure

```
soul_tower/
├── tts/                          # TTS Lua scripts
│   ├── Board.lua                 # Per-player board (v2.0, normalized coords, dynamic zones)
│   ├── Global.lua                # Thin event router, delegates to modules
│   ├── ZoneHandler.lua           # Zone events, game state, analytics transport
│   ├── WakeUp.lua                # Wake Up sequence (planned)
│   ├── Standby.lua               # Standby sequence (planned)
│   └── Attack.lua                # Attack resolution (planned)
├── backend/                      # Python backend
│   ├── analytics_server.py       # Flask server, SQLite storage, query API (port 5050)
│   └── soul_tower_analytics.db   # SQLite database (auto-created on first run)
├── src/                          # Python data pipeline
│   ├── models/                   # Typed dataclasses: hero.py, card.py, calamity.py, villain.py
│   ├── pipeline/
│   │   ├── fetcher.py            # HTTP requests, CSV parsing from Google Sheets
│   │   ├── store.py              # Local JSON cache read/write
│   │   ├── registry.py           # GameRegistry: single source of truth
│   │   └── transformer.py        # Models to Lua data block strings
│   ├── tts/                      # TTS JSON patching (planned)
│   └── api/                      # Flask game logic API (planned)
├── data/
│   ├── cache/                    # Local JSON cache of sheet data
│   └── game_lua_data/            # Generated Lua data blocks
├── assets/                       # Card art, board images, Figma exports
├── docs/                         # Architecture docs, pipeline docs
│   └── Rules_Formal              # CANONICAL game rules (source of truth)
├── config.py                     # Sheet URLs, column mappings, paths, constants
├── main.py                       # CLI entry point (--fresh, --sheet, --named)
└── CLAUDE.md                     # This file
```

---

## Key architectural decisions

### Naming conventions

- **Game Name** is the snake_case primary key for all entities (e.g., `copper_sword`). Used for image filenames, GMNotes, and internal lookups.
- **Visible Name** (also called Nickname) is the display name shown in TTS on hover.
- **GMNotes** on TTS objects stores the Game Name invisibly. Never affects the hover experience.

### Data pipeline

- `GameRegistry` in `registry.py` is the single source of truth for game data. Never bypass it.
- `transformer.py` is the only place Lua syntax lives in Python code.
- `USE_CACHE = True` reads local JSON cache. Falls back to stale cache on fetch failure.
- `--named` flag switches between positional Alpha format and named-key Beta format.
- Adding a new Google Sheet means updating `config.py` only. Nothing else changes.

### TTS board system (v2.0)

- Board.lua uses **normalized coordinates** (0 to 1 range, center = 0,0). All positions are fractions of board width/height, resolved at runtime via `getBounds()`.
- Changing the board image resolution (e.g., 2048x1024 to 4096x2048) requires zero code changes.
- Scaling the TTS object requires zero code changes.
- **Scripting zones** are spawned dynamically at runtime via `spawnObject({type='ScriptingTrigger'})`. Each zone stores identity in GMNotes: `board=<guid>;slot=<n>;color=<color>`.
- **Snap points** carry custom metadata (`slot_name`, `zone`) that TTS preserves but ignores.
- Board image is a 2:1 custom tile. Dark navy background (`#1A1E2E`).
- Known TTS issue: board image renders upside down. Flip the board object in TTS after import.

### TTS scripting architecture

- **Global.lua** is a thin router. All logic lives in modules.
- **ZoneHandler.lua** handles zone events, maintains centralized game state, and sends analytics to Flask via `WebRequest.custom()`.
- Board objects register with Global via `Global.call("registerBoard", {...})`.
- Zone events fire on Global (`onObjectEnterZone`, `onObjectLeaveZone`) and route through ZoneHandler.

### Analytics pipeline

- TTS POSTs JSON events to `http://localhost:5050/api/events`.
- Flask inserts into raw `events` table and runs type-specific handlers for denormalized tables (`hero_manifests`, `damage_log`, `defeats`).
- High-value events include full game state snapshots for reconstruction.
- Events are fire-and-forget: if Flask is down, TTS continues without interruption.

---

## Game rules reference (for code correctness)

This section is a condensed reference. For full details, always consult Rules_Formal.

### Teams and colors

| Team     | Champion Color | Henchman Color |
|----------|---------------|----------------|
| Hearts   | Yellow        | Green          |
| Clubs    | Red           | Teal           |
| Diamonds | Pink          | Blue           |
| Spades   | Orange        | Purple         |

### The five stats and their Wake Up resources

| Stat    | Resource       | Wake Up Behavior |
|---------|----------------|------------------|
| Health  | Hit Points     | 3 x Health on Conjure. No Wake Up generation. Boost/Weaken applies temporary HP. |
| Might   | Power          | 1:1 ratio. Each attack deals Power then reduces Power by 1 (min 1). |
| Speed   | Energy + Initiative | Energy 1:1 ratio. Initiative via repeated die rolls (Speed-sided die, reduce by 2, repeat until 0 or less). |
| Luck    | Favor + Card Draw | Roll 1d6, success if <= Luck, gain 1 Favor, reduce Luck by 2, repeat until failure. Draw 3 + Favor (Summoner) or 1 + Favor (Villain). |
| Arcana  | Sorcery Tokens | Roll 1d4, subtract Chance (starts 0). Result 1-2: gain token valued at Arcana, reduce Arcana by 2. Result 3-4: fail, reduce Arcana by 2, Chance+1. Repeat until Arcana <= 0. |

**First turn exception:** Skip the base 3-card draw (players start with 6 cards). Favor draws still happen.

**No Hero at Wake Up:** Initiative = 0, Energy = 1, no Power/Favor/Sorcery. Draw base 3 only. May only play 1 non-Crystal card.

**Sorcery baseline:** Every Summoner gets a Sorcery 1 token regardless of Arcana rolls. Henchmen get max Sorcery without rolling. No baseline bonus for Henchmen.

**Sorcery usage:** Reduce Spell Mana cost (min 1), OR increase Deal/Heal on Spells, OR pay toward Glamour.

### Stat modification

- **Boost/Weaken**: Pending modifiers applied at next Wake Up, reset at Standby. Stats capped 1-9 (except Health Weaken can be fatal).
- **Runic**: Permanent base stat modification while slotted. Immediate effect. Persists until Hero defeated. Stats capped 1-9.

### The eight statuses (Standby resolution order)

1. **Toughness** clears
2. **Regen** clears
3. **Indestructible** clears
4. **Agony** clears
5. **Doom** resolves (Kill effect, before Conjure)
6. Summoner Conjure step
7. Villain Conjure step
8. **Burn** resolves (Burn # + 1d4 damage, after Conjure. No second Conjure if fatal.)
9. **Silence** clears

**Condemn** — suppression mechanic. Three contexts: embedded in a status (Agony has Condemn: Regen Healing), applied by Hero passive (permanent while Hero lives), or standalone Summoner status (design in progress). Always targets Summoner, not Hero.

### Agony interactions (critical for implementation)

- After any non-Agony hit: tick 1 Agony Damage, consume 1 Agony stack
- Toughness + Agony: Toughness reduces damage, then Agony ticks consuming an ADDITIONAL Toughness stack. One hit burns two Toughness stacks.
- Regen + Agony: Regen triggers and loses a stack but heal is suppressed (Condemn: Regen Healing).
- Indestructible + Agony: Indestructible saves, sets HP to 1, then Agony ticks 1 damage. Can immediately kill.

### Card types and subtypes

| Type   | Default Mechanic | What It Does |
|--------|-----------------|--------------|
| Brutal | Order           | Commit up to Energy # Brutals. Each = 1 attack. Deal Power, Power -1 (min 1), 1 Mana if damage dealt. |
| Ritual | Pray            | Commit any # Rituals. Heal #d2 + (# - 1). |
| Spell  | Crush           | Commit any # Spells. Gain 2 Mana per committed. |

**Subtypes and timing tiers:**
- **Normal** (Tier 0) — your turn only, nothing else happening
- **Instant** (Tier 1, Spell only) — any time, any player
- **Entropy** (Tier 1, Ritual only) — any time, Foe gains Mana equal to cost instead of you paying
- **Reaction** (Tier 2, Brutal only) — only when specific trigger is active

### Turn structure

**Block** = one Summoner + paired Henchman.

**Wake Up sequence:**
1. Boost/Weaken resolve
2. Tokens restore (Order, Crush, Pray, Crystal)
3. Pillar generates Presence
4. Stat resource rolls
5. Wake Up effects (Villain, Hero, Enchant)
6. Health death check (Weaken Health can be fatal)

**Henchman turn:** Play Phase 1 (FATE) -> Order Phase (Command + Speed flurry) -> Play Phase 2 (FATE)

**Standby sequence:**
1. Standby effects
2. Enchant falls off
3-9. Status resolution (see order above)
10. Boost/Weaken reset
11. Pillar growth (Summoner at 12 Mana)
12. Presence lost
13. Tokens expire (Order, Crush, Pray)

### FATE system (Henchman AI)

**F**ind oldest card. If Default: try appropriate Default block (one Crush, one Pray, one Reaction block per turn max).

**A**ssess first statement. Harm enemy or benefit ally? If yes, valid. Does not deep-evaluate.

**T**arget: Harmful -> Foe first (skip Doomed targets if possible). Beneficial -> self if went first, allied Henchman if went second. Silence -> enemy Summoner. Draw -> self. Pristine -> complex priority tree (see Rules_Formal).

**E**xecute or move on. Once committed, no re-evaluation.

### Execution and Opportunity Attacks

Triggered ANY time a Champion reaches 0 or fewer HP:
- **Execution Attack**: Foe Henchman deals full Might (not Power), generates 1 Mana. Independent of other attacks.
- **Opportunity Attacks**: ALL Henchmen roll Luck, successes combine into one attack per Henchman. No Mana generated. Separately respondable.

### Entity resources

**Summoners:** Life = 30 start. Mana = 4 start. Max Mana = 12. Pain = 1 start.

**Villain:** Life = 30 per Summoner. Mana = 0 start. Spirit Meter 0, caps at 8. At 8+: play Calamity, reset to 0. Calamity deck = 4 + 1 per Summoner. Opening hand = 1 card per Summoner.

**Pillar:** Max level 4. Summoner: pay 12 Mana at Standby, grow by 1, regain Mana = new level. Henchman: auto-grow when Mana would reach 12 (once per turn).

### Drafting

16 cards from personal pool of 36 (12B/12R/12S). Min 4 each type. Plus 2 Ascended Heroes (4 Legendary cards). Plus Journey. Plus 9 Crystals (separate zone). Starting deck = 21.

**Conjure Pool:** 3 + 1 per Summoner Blessed Heroes face-up. Cursed pile shuffled, top card visible.

**Ascended reconjure rule:** Must Manifest two other Heroes before reconjuring a defeated Ascended.

### Key ability behaviors for code

**Evaluators:** Bolster (succeeded), Mercy (failed), Threshold (value >= #), Catalyst (matched card type). All look at immediately preceding statement in same scope only.

**Villain always pays:** Blood Price, Charge, Upcast, Glamour (if affordable). Always does every Harness choice. Fortune: random type unless Catalyst follows (then picks Catalyst type).

**Dynamic variables:** Fortuned, Prayed, Harnessed, Drained, Consumed Sorcery, Risked, Wilded.

**Toss block:** When a bigger Toss pitches a card with a smaller Toss #, the inner Toss triggers. Creates nested Toss chain. Player controls resolution order.

**Deny:** Fumbles card play if Deny # >= card cost. Fumbles attack if Deny # >= 2x attack damage. Must be played before resolution. Denied card/attack produces no effect. Denied entity spends no resources.

**Response Stack:** Card plays generate stacks. Resolve newest to oldest. Reactions can interrupt between statements but not mid-statement.

---

## Style and writing conventions

- **No em dashes.** Use commas, colons, or sentence breaks instead.
- **Sentence case for in-page headings.** Title case for H1/page titles only.
- **Descriptive link text only.** Never "Click Here" or bare URLs.
- **Reading level target:** Grades 6-8 for web content, grade 9 for Codex/game rules.
- **Codex page structure:** "What is it / How it works / What to know / Related."

---

## Code conventions

### Python
- Python 3.10+ (type hints, dataclasses)
- Flask for web servers, SQLite for storage, `requests` for HTTP
- Dataclasses with `from_row()` classmethod
- Snake_case everywhere

### Lua (TTS)
- Underscore prefix for private functions/variables
- Public API at bottom of each file
- `self.positionToWorld()` for coordinate conversion
- Never hardcode positions. Use normalized coords or `getBounds()`.
- `Wait.frames()` for timing, `JSON.encode()`/`decode()` for serialization
- `WebRequest.custom()` for HTTP

---

## What not to change without discussion

- The normalized coordinate system in Board.lua (LAYOUT table)
- The GameRegistry pattern in the Python pipeline
- The event type schema in ZoneHandler (Flask depends on field names)
- The GMNotes format on boards and zones
- Team-to-color mappings
- The Standby resolution order
- The FATE targeting priority system

---

## Common tasks

### Add a new hero
1. Add row to Google Sheet
2. Run `python main.py --fresh` to refresh cache

### Add a new board zone
1. Add to LAYOUT in Board.lua with snap and zone definitions
2. Add to slot_meta in _buildSnapPoints()

### Add a new analytics event type
1. Call ZoneHandler._sendEvent() from Lua
2. Add @handles() function in analytics_server.py

### Test the analytics pipeline
1. `python backend/analytics_server.py`
2. `curl http://localhost:5050/api/health`
3. Start TTS game, check `GET /api/events/raw`

---

## Current status

### Completed
- Board.lua v2.0, Global.lua, ZoneHandler.lua, analytics_server.py, ARCHITECTURE.md
- Python data pipeline (config, models, fetcher, store, registry, transformer)
- Rules_Formal (Drafting, Gameplay, Codex, Abilities A-Z)

### Not yet built
- WakeUp.lua, Standby.lua, Attack.lua (Global modules)
- StateMachine.lua, TTS JSON patcher, Flask game logic API
- Villain Decision Making tab, Soul Tower overview tab

---

## For Cowork

- Assets in `/assets`: `hero_name_card_name.png` (lowercase, underscores)
- Analytics DB at `/backend/soul_tower_analytics.db` (standard SQL)
- Do not modify `.lua` or `.py` pipeline files. Use Claude Code for code.
- Cowork is for: organizing assets, generating reports, formatting docs, processing images.

## For Claude Code

- Read this file and check Rules_Formal before implementing game logic.
- Lua files designed for TTS Tools bundler (`require()`). Without bundler, paste modules inline in Global.
- When changing Board.lua LAYOUT or zones, verify ZoneHandler GMNotes parsing still works.
- When adding event types, update both ZoneHandler.lua and analytics_server.py.
- Run `python main.py --fresh` after data model changes.
