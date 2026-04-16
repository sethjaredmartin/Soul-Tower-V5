# Soul Tower Developer Kit

Welcome to the Soul Tower project. This kit contains everything you need to get the TTS scripting environment and analytics backend running.

## What's inside

```
soul_tower_kit/
├── CLAUDE.md              # Project instructions for Claude Code / Claude AI
├── README.md              # You are here
├── tts/
│   ├── Board.lua          # Player board script (v2.0, normalized coordinates)
│   ├── Global.lua         # TTS Global script (thin event router)
│   └── ZoneHandler.lua    # Zone event handler + game state + analytics
├── backend/
│   ├── analytics_server.py  # Flask server for gameplay analytics
│   └── requirements.txt     # Python dependencies
└── docs/
    └── ARCHITECTURE.md    # System architecture and data flow diagram
```

## Quick start: analytics server

The analytics server receives gameplay events from TTS and stores them in SQLite for balance analysis.

### 1. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the server

```bash
python analytics_server.py
```

The server runs at `http://localhost:5050`. TTS sends events to `POST /api/events`.

### 3. Verify it works

```bash
curl http://localhost:5050/api/health
```

You should see a JSON response with event and session counts.

### 4. Useful endpoints

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/api/health` | GET | Server status and counts |
| `/api/sessions` | GET | List all playtest sessions |
| `/api/sessions/<id>` | GET | Full detail for one session |
| `/api/sessions/<id>/timeline` | GET | High-value events only (no zone noise) |
| `/api/heroes` | GET | Hero pick rates across all sessions |
| `/api/damage` | GET | Damage breakdown (optional `?session_id=`) |
| `/api/events/raw` | GET | Raw events with filters (`?event_type=`, `?game_color=`, `?limit=`) |
| `/api/snapshots/<id>/latest` | GET | Most recent game state snapshot |
| `/api/sessions/<id>/notes` | PUT | Add playtest notes (JSON body: `{"notes": "..."}`) |

## Quick start: TTS Lua scripts

### With TTS Tools (VS Code extension)

If you have the TTS Tools bundler set up:

1. Place the `tts/` folder in your project
2. Global.lua uses `require("ZoneHandler")` to load modules
3. Board.lua is an object script attached to each player board tile
4. Build and push to TTS via the extension

### Without TTS Tools

If you are pasting directly into the TTS scripting editor:

1. Open Global.lua in TTS (Scripting > Global)
2. Paste ZoneHandler.lua code above Global.lua (replace the `require` line)
3. Open each board tile's script and paste Board.lua

### Board setup

Each board is a 2:1 custom tile. Import your board image (supports up to 4096x2048). The board self-configures on first placement: it prompts for a Champion color, assigns the team and henchman color automatically, spawns scripting zones, and generates snap points.

Board image renders upside down in TTS. Flip the board object after import.

## Project conventions

Read `CLAUDE.md` for the full list. The key ones:

- **Game Name** is snake_case (e.g., `copper_sword`). Used everywhere internally.
- **No em dashes** in any documentation or generated text.
- **Sentence case** for headings (not Title Case).
- **Rules_Formal** is the canonical game rules document. Code follows it.

## Architecture overview

Read `docs/ARCHITECTURE.md` for the full three-layer diagram. In short:

```
TTS (Board.lua + Global.lua + ZoneHandler.lua)
    │ HTTP POST (JSON)
    ▼
Flask (analytics_server.py)
    │ SQLite
    ▼
soul_tower_analytics.db
```

Every meaningful game event (hero manifested, damage dealt, turn start, defeat) is captured with a full game state snapshot. This feeds into balance analysis via Python (pandas, matplotlib).

## For Nikkoli

The Unity prototype will eventually consume the same game data and rules. The Python data pipeline (`src/` directory, not included in this kit yet) fetches hero and card data from Google Sheets and produces typed models. The same models can generate Lua data blocks for TTS or C# data classes for Unity.

The CLAUDE.md file works with Claude Code. Drop it in the project root and run `claude` from that directory. Claude will read it automatically and understand the project.

## Questions?

Check CLAUDE.md first, then ARCHITECTURE.md. If you are implementing game logic, check Rules_Formal.
