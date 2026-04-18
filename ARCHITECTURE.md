# Soul Tower Analytics Pipeline — Architecture

## The Three Layers

```
┌─────────────────────────────────┐
│  TTS (Tabletop Simulator)       │
│                                 │
│  Board.lua (per player)         │
│    - Spawns scripting zones     │
│    - Manages snap points        │
│    - Calls Global on events     │
│                                 │
│  Global.lua (thin router)       │
│    - Wires TTS events           │
│    - Delegates to modules       │
│                                 │
│  ZoneHandler.lua (Global module)│
│    - Zone enter/leave handling  │
│    - Game state tracking        │
│    - Analytics transport        │
│    - WebRequest.custom() POST   │
│         │                       │
└─────────┼───────────────────────┘
          │ HTTP POST (JSON)
          │ localhost:5050/api/events
          ▼
┌─────────────────────────────────┐
│  Flask Analytics Server         │
│  analytics_server.py            │
│                                 │
│  POST /api/events  (ingestion)  │
│  GET  /api/sessions (list)      │
│  GET  /api/heroes  (pick rates) │
│  GET  /api/damage  (balance)    │
│  GET  /api/events/raw (debug)   │
│  GET  /api/snapshots (state)    │
│         │                       │
└─────────┼───────────────────────┘
          │ SQLite
          ▼
┌─────────────────────────────────┐
│  soul_tower_analytics.db        │
│                                 │
│  events (raw log)               │
│  sessions (per game)            │
│  hero_manifests (pick tracking) │
│  damage_log (balance data)      │
│  defeats (win/loss analysis)    │
└─────────────────────────────────┘
```

## Data Flow: What Happens When Someone Manifests a Hero

1. Player clicks "Manifest Champion" button on Board.lua
2. Board.lua takes the hero card from the Conjure Pool,
   places it at the champion snap point
3. The hero card physically enters the champion scripting zone
4. TTS fires `onObjectEnterZone(zone, hero_obj)` on Global
5. Global.lua routes to `ZoneHandler.onObjectEnterZone()`
6. ZoneHandler parses the zone's GMNotes to identify:
   board=abc123, slot=champion, color=Yellow
7. ZoneHandler calls `_onHeroEnterSlot()` which:
   a. Updates `game_state.boards["Yellow"].champion`
   b. Reads hero stats if the hero object exposes them
   c. Fires `hero_manifested` event with a full state snapshot
8. `_sendEvent()` does two things:
   a. Appends to the local ring buffer (always)
   b. POSTs JSON to Flask at localhost:5050/api/events
9. Flask receives the event and:
   a. Inserts into `events` table (raw log)
   b. Runs the `hero_manifested` handler which inserts into `hero_manifests`
10. You can now query `GET /api/heroes` to see pick rates

## Event Types

| Event Type        | When It Fires                          | Key Data Fields                        |
|-------------------|----------------------------------------|----------------------------------------|
| session_start     | Game loads                             | session_id                             |
| session_end       | Game closes                            | turn_count, duration, final_state      |
| board_registered  | Board discovered/created               | game_color, team, seat_color           |
| hero_manifested   | Hero enters champion/henchman zone     | game_color, role, hero_name, stats     |
| zone_enter        | Any object enters any board zone       | game_color, slot, obj_type, obj_name   |
| zone_leave        | Any object leaves any board zone       | game_color, slot, obj_name             |
| card_slotted      | Card enters equip/runic/enchant zone   | game_color, slot, card_name            |
| turn_start        | Block begins its turn                  | game_color, turn_number, snapshot      |
| wake_up           | Block Wake Up resolves                 | initiatives, who goes first            |
| standby           | Block Standby resolves                 | snapshot of board state                |
| attack            | Command attack fires                   | attacker, target, damage, type         |
| damage            | Any damage dealt                       | target, amount, source, remaining HP   |
| hero_defeated     | Hero HP reaches 0                      | hero_name, defeated_by, snapshot       |
| summoner_update   | Life/Mana/etc changes                  | resource, old_value, new_value         |
| crystal_zone_change | Crystal enters/leaves crystal zone   | obj_name, obj_type                     |

## State Snapshots

High-value events (hero_manifested, turn_start, standby, hero_defeated)
include a full `snapshot` of the game state at that moment. This lets you
reconstruct the board state at any point during a session by querying
snapshots chronologically.

A snapshot contains: session_id, turn_number, timestamp, and for each
board: team, champion (name, stats, manifested_at), henchman (same),
slots (equip/runic/enchant GUIDs), and summoner resources.

## Flask Query Examples

```bash
# Health check
curl http://localhost:5050/api/health

# List all sessions
curl http://localhost:5050/api/sessions

# Get full event log for a session
curl http://localhost:5050/api/sessions/ST-1712000000-1234

# Timeline (high-value events only, no zone noise)
curl http://localhost:5050/api/sessions/ST-1712000000-1234/timeline

# Hero pick rates across all sessions
curl http://localhost:5050/api/heroes

# Damage breakdown for a session
curl http://localhost:5050/api/damage?session_id=ST-1712000000-1234

# Raw event dump with filters
curl "http://localhost:5050/api/events/raw?event_type=hero_manifested&limit=20"

# Latest state snapshot for a session
curl http://localhost:5050/api/snapshots/ST-1712000000-1234/latest

# Add playtest notes to a session
curl -X PUT http://localhost:5050/api/sessions/ST-1712000000-1234/notes \
  -H "Content-Type: application/json" \
  -d '{"notes": "Akiem felt overtuned. Regen stacking was too strong by turn 5."}'
```

## What This Enables (Future Analysis)

With data in SQLite, the Python ecosystem roadmap from the project summary
connects directly:

- **pandas**: Load events/damage/defeats into DataFrames for pivot tables
  and cross-session comparison
- **matplotlib**: Damage over time curves, resource economy graphs,
  hero pick rate charts
- **scikit-learn**: Win rate prediction from draft composition,
  balance outlier detection

The database schema is intentionally denormalized for query speed over
storage efficiency. A single playtest session generates maybe a few
hundred events. Even hundreds of sessions will fit comfortably in SQLite.

## File Inventory

| File                 | Layer    | Purpose                                  |
|----------------------|----------|------------------------------------------|
| Board.lua            | TTS      | Per-player board with zones and snaps    |
| Global.lua           | TTS      | Thin event router                        |
| ZoneHandler.lua      | TTS      | Zone logic, state tracking, HTTP client  |
| analytics_server.py  | Python   | Flask server, SQLite storage, query API  |
| ARCHITECTURE.md      | Docs     | This file                                |
