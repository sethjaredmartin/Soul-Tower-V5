"""
Soul Tower Analytics Server
Flask app that receives game events from TTS via HTTP,
stores them in SQLite, and exposes query/analysis endpoints.

Run:  python analytics_server.py
Port: 5050 (to avoid conflict with other Flask projects)

TTS sends JSON events to POST /api/events
You query data from GET endpoints or the dashboard.
"""

import json
import sqlite3
import os
from datetime import datetime, timezone
from contextlib import contextmanager

from flask import Flask, request, jsonify, g


# ── App Setup ────────────────────────────────────────────────────────────────────

app = Flask(__name__)

DB_PATH = os.environ.get("ST_DB_PATH", "soul_tower_analytics.db")


# ── Database ─────────────────────────────────────────────────────────────────────

def get_db():
    """Get a database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        -- Raw events: every single event from TTS lands here
        CREATE TABLE IF NOT EXISTS events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            event_type    TEXT NOT NULL,
            timestamp     INTEGER NOT NULL,
            turn_number   INTEGER DEFAULT 0,
            data          TEXT,
            received_at   TEXT DEFAULT (datetime('now')),

            -- Denormalized fields for fast queries on common patterns
            game_color    TEXT,
            hero_name     TEXT,
            slot          TEXT,
            role          TEXT
        );

        -- Sessions: one row per game session
        CREATE TABLE IF NOT EXISTS sessions (
            session_id    TEXT PRIMARY KEY,
            started_at    INTEGER,
            ended_at      INTEGER,
            turn_count    INTEGER DEFAULT 0,
            final_state   TEXT,
            notes         TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        -- Hero manifest log: denormalized for quick hero analytics
        CREATE TABLE IF NOT EXISTS hero_manifests (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            game_color    TEXT NOT NULL,
            role          TEXT NOT NULL,
            hero_name     TEXT NOT NULL,
            turn_number   INTEGER DEFAULT 0,
            stats         TEXT,
            timestamp     INTEGER,

            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        -- Damage log: every damage event for balance analysis
        CREATE TABLE IF NOT EXISTS damage_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            turn_number     INTEGER DEFAULT 0,
            target_color    TEXT,
            target_role     TEXT,
            damage          INTEGER,
            source          TEXT,
            new_hp          INTEGER,
            timestamp       INTEGER,

            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        -- Defeat log: when heroes die
        CREATE TABLE IF NOT EXISTS defeats (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            game_color    TEXT NOT NULL,
            role          TEXT NOT NULL,
            hero_name     TEXT,
            defeated_by   TEXT,
            turn_number   INTEGER DEFAULT 0,
            snapshot      TEXT,
            timestamp     INTEGER,

            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        -- Indexes for common query patterns
        CREATE INDEX IF NOT EXISTS idx_events_session    ON events(session_id);
        CREATE INDEX IF NOT EXISTS idx_events_type       ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_color      ON events(game_color);
        CREATE INDEX IF NOT EXISTS idx_events_turn       ON events(turn_number);
        CREATE INDEX IF NOT EXISTS idx_manifests_hero    ON hero_manifests(hero_name);
        CREATE INDEX IF NOT EXISTS idx_manifests_session ON hero_manifests(session_id);
        CREATE INDEX IF NOT EXISTS idx_damage_session    ON damage_log(session_id);
        CREATE INDEX IF NOT EXISTS idx_defeats_hero      ON defeats(hero_name);
    """)
    db.commit()
    db.close()


# ── Event Ingestion ──────────────────────────────────────────────────────────────

# Map event types to their denormalized table handlers
EVENT_HANDLERS = {}


def handles(event_type):
    """Decorator to register a handler for a specific event type."""
    def decorator(func):
        EVENT_HANDLERS[event_type] = func
        return func
    return decorator


@app.route("/api/events", methods=["POST"])
def receive_event():
    """
    Main event ingestion endpoint.
    TTS sends one JSON event per request.
    """
    event = request.get_json(silent=True)
    if not event:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("event_type", "unknown")
    session_id = event.get("session_id", "")
    timestamp  = event.get("timestamp", 0)
    turn       = event.get("turn_number", 0)
    data       = event.get("data", {})

    db = get_db()

    # Extract denormalized fields from data
    game_color = data.get("game_color")
    hero_name  = data.get("hero_name")
    slot       = data.get("slot")
    role       = data.get("role")

    # Insert into raw events table (always)
    db.execute("""
        INSERT INTO events (session_id, event_type, timestamp, turn_number,
                            data, game_color, hero_name, slot, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, event_type, timestamp, turn,
        json.dumps(data), game_color, hero_name, slot, role
    ))

    # Run type-specific handler if one exists
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        try:
            handler(db, session_id, timestamp, turn, data)
        except Exception as e:
            print(f"[Handler Error] {event_type}: {e}")

    db.commit()

    return jsonify({"status": "ok", "event_type": event_type}), 201


# ── Type-Specific Handlers ───────────────────────────────────────────────────────

@handles("session_start")
def _handle_session_start(db, session_id, timestamp, turn, data):
    db.execute("""
        INSERT OR IGNORE INTO sessions (session_id, started_at)
        VALUES (?, ?)
    """, (session_id, timestamp))


@handles("session_end")
def _handle_session_end(db, session_id, timestamp, turn, data):
    final_state = json.dumps(data.get("final_state", {}))
    db.execute("""
        UPDATE sessions
        SET ended_at = ?, turn_count = ?, final_state = ?
        WHERE session_id = ?
    """, (timestamp, data.get("turn_count", turn), final_state, session_id))


@handles("hero_manifested")
def _handle_hero_manifested(db, session_id, timestamp, turn, data):
    stats = json.dumps(data.get("stats", {}))
    db.execute("""
        INSERT INTO hero_manifests
            (session_id, game_color, role, hero_name, turn_number, stats, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        data.get("game_color"),
        data.get("role"),
        data.get("hero_name"),
        turn,
        stats,
        timestamp,
    ))


@handles("damage")
def _handle_damage(db, session_id, timestamp, turn, data):
    db.execute("""
        INSERT INTO damage_log
            (session_id, turn_number, target_color, target_role,
             damage, source, new_hp, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, turn,
        data.get("target_color"),
        data.get("target_role"),
        data.get("damage", 0),
        data.get("source"),
        data.get("new_hp"),
        timestamp,
    ))


@handles("hero_defeated")
def _handle_defeat(db, session_id, timestamp, turn, data):
    snapshot = json.dumps(data.get("snapshot", {}))
    db.execute("""
        INSERT INTO defeats
            (session_id, game_color, role, hero_name,
             defeated_by, turn_number, snapshot, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        data.get("game_color"),
        data.get("role"),
        data.get("hero_name"),
        data.get("defeated_by"),
        turn,
        snapshot,
        timestamp,
    ))


# ── Query Endpoints ──────────────────────────────────────────────────────────────

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """List all sessions, most recent first."""
    db = get_db()
    rows = db.execute("""
        SELECT session_id, started_at, ended_at, turn_count, notes, created_at
        FROM sessions ORDER BY started_at DESC
    """).fetchall()

    return jsonify({
        "count": len(rows),
        "sessions": [dict(r) for r in rows],
    })


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get full detail for a single session including all events."""
    db = get_db()

    session = db.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not session:
        return jsonify({"error": "Session not found"}), 404

    events = db.execute("""
        SELECT event_type, timestamp, turn_number, data,
               game_color, hero_name, slot, role
        FROM events WHERE session_id = ?
        ORDER BY timestamp, id
    """, (session_id,)).fetchall()

    return jsonify({
        "session": dict(session),
        "events": [dict(e) for e in events],
        "event_count": len(events),
    })


@app.route("/api/sessions/<session_id>/timeline", methods=["GET"])
def session_timeline(session_id):
    """
    Chronological timeline of high-value events for a session.
    Filters out noisy zone_enter/zone_leave events.
    """
    db = get_db()
    rows = db.execute("""
        SELECT event_type, timestamp, turn_number, data,
               game_color, hero_name, role
        FROM events
        WHERE session_id = ?
          AND event_type NOT IN ('zone_enter', 'zone_leave')
        ORDER BY timestamp, id
    """, (session_id,)).fetchall()

    timeline = []
    for r in rows:
        entry = dict(r)
        if entry["data"]:
            entry["data"] = json.loads(entry["data"])
        timeline.append(entry)

    return jsonify({"session_id": session_id, "timeline": timeline})


@app.route("/api/heroes", methods=["GET"])
def hero_stats():
    """
    Aggregate hero statistics across all sessions.
    How often each hero is picked, win/loss, average survival turns.
    """
    db = get_db()

    # Pick rates
    picks = db.execute("""
        SELECT hero_name, role, COUNT(*) as pick_count
        FROM hero_manifests
        GROUP BY hero_name, role
        ORDER BY pick_count DESC
    """).fetchall()

    # Defeat rates
    defeats = db.execute("""
        SELECT hero_name, role, COUNT(*) as defeat_count,
               AVG(turn_number) as avg_defeat_turn
        FROM defeats
        GROUP BY hero_name, role
    """).fetchall()

    # Build combined view
    hero_data = {}
    for p in picks:
        key = f"{p['hero_name']}_{p['role']}"
        hero_data[key] = {
            "hero_name": p["hero_name"],
            "role": p["role"],
            "pick_count": p["pick_count"],
            "defeat_count": 0,
            "avg_defeat_turn": None,
        }

    for d in defeats:
        key = f"{d['hero_name']}_{d['role']}"
        if key in hero_data:
            hero_data[key]["defeat_count"] = d["defeat_count"]
            hero_data[key]["avg_defeat_turn"] = round(d["avg_defeat_turn"], 1)

    return jsonify({
        "heroes": list(hero_data.values()),
    })


@app.route("/api/damage", methods=["GET"])
def damage_analysis():
    """
    Damage analytics. Optionally filter by session_id query param.
    """
    db = get_db()
    session_filter = request.args.get("session_id")

    if session_filter:
        rows = db.execute("""
            SELECT target_color, target_role, SUM(damage) as total_damage,
                   COUNT(*) as hit_count, AVG(damage) as avg_damage,
                   source
            FROM damage_log WHERE session_id = ?
            GROUP BY target_color, target_role, source
            ORDER BY total_damage DESC
        """, (session_filter,)).fetchall()
    else:
        rows = db.execute("""
            SELECT target_color, target_role, SUM(damage) as total_damage,
                   COUNT(*) as hit_count, AVG(damage) as avg_damage,
                   source
            FROM damage_log
            GROUP BY target_color, target_role, source
            ORDER BY total_damage DESC
        """).fetchall()

    return jsonify({
        "damage_breakdown": [dict(r) for r in rows],
    })


@app.route("/api/events/raw", methods=["GET"])
def raw_events():
    """
    Raw event dump. Supports filters:
      ?session_id=X
      ?event_type=hero_manifested
      ?game_color=Yellow
      ?limit=50
    """
    db = get_db()

    query = "SELECT * FROM events WHERE 1=1"
    params = []

    sid = request.args.get("session_id")
    if sid:
        query += " AND session_id = ?"
        params.append(sid)

    etype = request.args.get("event_type")
    if etype:
        query += " AND event_type = ?"
        params.append(etype)

    color = request.args.get("game_color")
    if color:
        query += " AND game_color = ?"
        params.append(color)

    query += " ORDER BY timestamp DESC, id DESC"

    limit = request.args.get("limit", 100, type=int)
    query += " LIMIT ?"
    params.append(min(limit, 1000))

    rows = db.execute(query, params).fetchall()

    return jsonify({
        "count": len(rows),
        "events": [dict(r) for r in rows],
    })


@app.route("/api/snapshots/<session_id>/latest", methods=["GET"])
def latest_snapshot(session_id):
    """
    Get the most recent state snapshot from a session.
    Snapshots are embedded in high-value events like hero_manifested, standby, etc.
    """
    db = get_db()
    row = db.execute("""
        SELECT data FROM events
        WHERE session_id = ?
          AND json_extract(data, '$.snapshot') IS NOT NULL
        ORDER BY timestamp DESC, id DESC
        LIMIT 1
    """, (session_id,)).fetchone()

    if not row:
        return jsonify({"error": "No snapshots found for session"}), 404

    data = json.loads(row["data"])
    return jsonify({
        "session_id": session_id,
        "snapshot": data.get("snapshot", {}),
    })


# ── Health Check ─────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    db = get_db()
    event_count = db.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
    session_count = db.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
    return jsonify({
        "status": "ok",
        "db_path": DB_PATH,
        "event_count": event_count,
        "session_count": session_count,
    })


# ── Session Notes (for post-playtest annotations) ───────────────────────────────

@app.route("/api/sessions/<session_id>/notes", methods=["PUT"])
def update_session_notes(session_id):
    """Add or update notes on a session after playtesting."""
    body = request.get_json(silent=True)
    if not body or "notes" not in body:
        return jsonify({"error": "Provide 'notes' in JSON body"}), 400

    db = get_db()
    db.execute(
        "UPDATE sessions SET notes = ? WHERE session_id = ?",
        (body["notes"], session_id)
    )
    db.commit()
    return jsonify({"status": "ok", "session_id": session_id})


# ── Run ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print(f"[Soul Tower Analytics] Database: {DB_PATH}")
    print(f"[Soul Tower Analytics] Listening on http://localhost:5050")
    print(f"[Soul Tower Analytics] TTS should POST to http://localhost:5050/api/events")
    app.run(host="0.0.0.0", port=6060, debug=True)
