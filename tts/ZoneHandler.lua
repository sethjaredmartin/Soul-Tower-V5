-- ============================================================
-- ZoneHandler.lua
-- Global module: Scripting Zone event handler + Game State
-- Tracker + Analytics pipeline
--
-- This is the Global-side brain that:
--   1. Listens for onObjectEnterZone / onObjectLeaveZone
--   2. Identifies which board and slot the zone belongs to
--   3. Maintains a centralized game state table
--   4. Fires analytics events to localhost Flask server
--   5. Provides query functions for other Global modules
--
-- ARCHITECTURE:
--   Board.lua spawns scripting zones with GMNotes like:
--     "board=abc123;slot=champion;color=Yellow"
--   This module parses those notes on every zone event,
--   routes to the right handler, updates state, and ships
--   the event to Flask.
--
-- REQUIRES: Called/required from Global.lua
-- ============================================================

local ZoneHandler = {}

-- ── Configuration ──────────────────────────────────────────────────────────────

local ANALYTICS_URL  = "http://localhost:5050/api/events"
local ANALYTICS_ON   = true   -- flip to false to silence HTTP calls during dev
local LOG_EVENTS     = true   -- print events to TTS chat for debugging

-- ── Game State ─────────────────────────────────────────────────────────────────
-- Single source of truth for the entire game session.
-- Boards register themselves here. Zone events update it.
-- Flask receives snapshots of this on every meaningful event.

local game_state = {
    session_id    = nil,      -- generated on game start
    started_at    = nil,      -- os.time() at session start
    turn_number   = 0,
    active_block  = nil,      -- which color's block is taking a turn

    -- Per-color board state, keyed by game_color
    -- Populated when boards register themselves
    boards = {
        -- ["Yellow"] = {
        --     board_guid     = "abc123",
        --     seat_color     = "White",
        --     team           = "Hearts",
        --     henchman_color = "Green",
        --     champion       = { name = nil, hero_obj_guid = nil, manifested_at = 0 },
        --     henchman       = { name = nil, hero_obj_guid = nil, manifested_at = 0 },
        --     slots          = { equip = nil, runic = nil, enchant = nil },
        --     summoner       = { life=30, mana=4, presence=0, pillar=0, pain=1, spirit=0, sorcery=0 },
        --     zone_guids     = {},
        -- },
    },

    -- Event log (ring buffer, last N events kept in memory)
    event_log     = {},
    event_log_max = 200,
}

-- Zone GUID -> { board_guid, slot_name, game_color } lookup cache
-- Rebuilt whenever a board registers or zones change
local zone_lookup = {}


-- ── Session Lifecycle ──────────────────────────────────────────────────────────

function ZoneHandler.startSession()
    game_state.session_id = _generateSessionId()
    game_state.started_at = os.time()
    game_state.turn_number = 0
    game_state.active_block = nil
    game_state.boards = {}
    game_state.event_log = {}
    zone_lookup = {}

    ZoneHandler._sendEvent("session_start", {
        session_id = game_state.session_id,
    })

    if LOG_EVENTS then
        printToAll("[Analytics] Session started: " .. game_state.session_id, {0.5, 0.8, 1})
    end
end

function ZoneHandler.endSession()
    ZoneHandler._sendEvent("session_end", {
        session_id   = game_state.session_id,
        turn_count   = game_state.turn_number,
        duration_sec = os.time() - (game_state.started_at or os.time()),
        final_state  = ZoneHandler.getStateSnapshot(),
    })

    if LOG_EVENTS then
        printToAll("[Analytics] Session ended.", {0.5, 0.8, 1})
    end
end


-- ── Board Registration ─────────────────────────────────────────────────────────
-- Called by Board.lua during _initBoard() or by Global when it discovers boards

function ZoneHandler.registerBoard(params)
    -- params = {
    --     board_guid, game_color, seat_color, team, henchman_color,
    --     zone_guids = { champion = "guid", henchman = "guid", ... }
    -- }
    local gc = params.game_color
    if not gc then return end

    game_state.boards[gc] = {
        board_guid     = params.board_guid,
        seat_color     = params.seat_color,
        team           = params.team,
        henchman_color = params.henchman_color,
        champion       = { name = nil, hero_obj_guid = nil, manifested_at = 0 },
        henchman       = { name = nil, hero_obj_guid = nil, manifested_at = 0 },
        slots          = { equip = nil, runic = nil, enchant = nil },
        summoner       = { life = 30, mana = 4, presence = 0, pillar = 0, pain = 1, spirit = 0, sorcery = 0 },
        zone_guids     = params.zone_guids or {},
    }

    -- Rebuild zone lookup cache
    _rebuildZoneLookup()

    ZoneHandler._sendEvent("board_registered", {
        game_color = gc,
        team       = params.team,
        seat_color = params.seat_color,
    })
end


-- ── Zone Event Handlers (called from Global event hooks) ───────────────────────

function ZoneHandler.onObjectEnterZone(zone, entering_obj)
    local zone_info = _identifyZone(zone)
    if not zone_info then return end  -- not one of our board zones

    local slot  = zone_info.slot_name
    local gc    = zone_info.game_color
    local board = game_state.boards[gc]
    if not board then return end

    local obj_type = entering_obj.type  -- "Card", "Deck", etc.
    local obj_name = entering_obj.getName()
    local obj_guid = entering_obj.getGUID()

    -- Route to slot-specific handler
    if slot == "champion" then
        _onHeroEnterSlot(board, "champion", entering_obj, gc)

    elseif slot == "henchman" then
        _onHeroEnterSlot(board, "henchman", entering_obj, gc)

    elseif slot == "equip" or slot == "runic" or slot == "enchant" then
        _onCardEnterSlotColumn(board, slot, entering_obj, gc)

    elseif slot == "crystal_deck" then
        _onCrystalZoneEnter(board, entering_obj, gc)
    end

    -- Fire analytics for every zone entry
    ZoneHandler._sendEvent("zone_enter", {
        game_color = gc,
        slot       = slot,
        obj_type   = obj_type,
        obj_name   = obj_name,
        obj_guid   = obj_guid,
    })
end

function ZoneHandler.onObjectLeaveZone(zone, leaving_obj)
    local zone_info = _identifyZone(zone)
    if not zone_info then return end

    local slot  = zone_info.slot_name
    local gc    = zone_info.game_color
    local board = game_state.boards[gc]
    if not board then return end

    local obj_name = leaving_obj.getName()
    local obj_guid = leaving_obj.getGUID()

    -- Handle departure from hero slots
    if slot == "champion" and board.champion.hero_obj_guid == obj_guid then
        board.champion = { name = nil, hero_obj_guid = nil, manifested_at = 0 }
        -- Notify the board object to update buttons
        local board_obj = getObjectFromGUID(board.board_guid)
        if board_obj then board_obj.call("onChampionDefeated") end

    elseif slot == "henchman" and board.henchman.hero_obj_guid == obj_guid then
        board.henchman = { name = nil, hero_obj_guid = nil, manifested_at = 0 }
        local board_obj = getObjectFromGUID(board.board_guid)
        if board_obj then board_obj.call("onHenchmanDefeated") end

    elseif slot == "equip" or slot == "runic" or slot == "enchant" then
        if board.slots[slot] == obj_guid then
            board.slots[slot] = nil
        end
    end

    ZoneHandler._sendEvent("zone_leave", {
        game_color = gc,
        slot       = slot,
        obj_name   = obj_name,
        obj_guid   = obj_guid,
    })
end


-- ── Slot-Specific Handlers ─────────────────────────────────────────────────────

function _onHeroEnterSlot(board, role, hero_obj, gc)
    -- role = "champion" or "henchman"
    local hero_name = hero_obj.getName()
    local hero_guid = hero_obj.getGUID()

    board[role] = {
        name           = hero_name,
        hero_obj_guid  = hero_guid,
        manifested_at  = game_state.turn_number,
    }

    -- Try to read stats from the hero object if it exposes them
    local stats = hero_obj.call("getStats")
    if stats then
        board[role].stats = stats
    end

    ZoneHandler._sendEvent("hero_manifested", {
        game_color  = gc,
        role        = role,
        hero_name   = hero_name,
        hero_guid   = hero_guid,
        turn_number = game_state.turn_number,
        stats       = stats,
        snapshot    = ZoneHandler.getStateSnapshot(),
    })

    if LOG_EVENTS then
        printToAll(string.format(
            "[Analytics] %s manifested %s as %s (turn %d)",
            gc, hero_name, role, game_state.turn_number
        ), {0.6, 0.9, 0.6})
    end
end

function _onCardEnterSlotColumn(board, slot, card_obj, gc)
    local card_name = card_obj.getName()
    local card_guid = card_obj.getGUID()

    board.slots[slot] = card_guid

    ZoneHandler._sendEvent("card_slotted", {
        game_color  = gc,
        slot        = slot,
        card_name   = card_name,
        card_guid   = card_guid,
        turn_number = game_state.turn_number,
    })
end

function _onCrystalZoneEnter(board, obj, gc)
    -- Crystals entering the zone: just log it
    ZoneHandler._sendEvent("crystal_zone_change", {
        game_color = gc,
        obj_name   = obj.getName(),
        obj_type   = obj.type,
    })
end


-- ── Turn Tracking ──────────────────────────────────────────────────────────────

function ZoneHandler.advanceTurn(game_color)
    game_state.turn_number = game_state.turn_number + 1
    game_state.active_block = game_color

    ZoneHandler._sendEvent("turn_start", {
        game_color  = game_color,
        turn_number = game_state.turn_number,
        snapshot    = ZoneHandler.getStateSnapshot(),
    })
end

function ZoneHandler.recordWakeUp(params)
    -- params = { game_color, champ_initiative, hench_initiative, first = "champion"|"henchman" }
    ZoneHandler._sendEvent("wake_up", {
        game_color       = params.game_color,
        champ_initiative = params.champ_initiative,
        hench_initiative = params.hench_initiative,
        first            = params.first,
        turn_number      = game_state.turn_number,
    })
end

function ZoneHandler.recordStandby(params)
    -- params = { game_color, henchman_color, events_during = {...} }
    ZoneHandler._sendEvent("standby", {
        game_color     = params.game_color,
        henchman_color = params.henchman_color,
        turn_number    = game_state.turn_number,
        snapshot       = ZoneHandler.getStateSnapshot(),
    })
end

function ZoneHandler.recordAttack(params)
    -- params = { attacker_color, target_color, damage, attack_type, ... }
    ZoneHandler._sendEvent("attack", params)
end

function ZoneHandler.recordDamage(params)
    -- params = { target_color, role, damage, source, new_hp, ... }
    ZoneHandler._sendEvent("damage", params)
end

function ZoneHandler.recordDefeat(params)
    -- params = { game_color, role, hero_name, defeated_by, turn_number }
    params.turn_number = params.turn_number or game_state.turn_number
    params.snapshot = ZoneHandler.getStateSnapshot()
    ZoneHandler._sendEvent("hero_defeated", params)
end

function ZoneHandler.recordSummonerUpdate(game_color, key, old_val, new_val)
    local board = game_state.boards[game_color]
    if board then
        board.summoner[key] = new_val
    end

    ZoneHandler._sendEvent("summoner_update", {
        game_color  = game_color,
        resource    = key,
        old_value   = old_val,
        new_value   = new_val,
        turn_number = game_state.turn_number,
    })
end


-- ── State Snapshots ────────────────────────────────────────────────────────────
-- Full game state at a point in time, sent with high-value events

function ZoneHandler.getStateSnapshot()
    local snapshot = {
        session_id   = game_state.session_id,
        turn_number  = game_state.turn_number,
        active_block = game_state.active_block,
        timestamp    = os.time(),
        boards       = {},
    }

    for gc, board in pairs(game_state.boards) do
        snapshot.boards[gc] = {
            team           = board.team,
            seat_color     = board.seat_color,
            henchman_color = board.henchman_color,
            champion       = {
                name          = board.champion.name,
                manifested_at = board.champion.manifested_at,
                stats         = board.champion.stats,
            },
            henchman       = {
                name          = board.henchman.name,
                manifested_at = board.henchman.manifested_at,
                stats         = board.henchman.stats,
            },
            slots    = _copyTable(board.slots),
            summoner = _copyTable(board.summoner),
        }
    end

    return snapshot
end

function ZoneHandler.getGameState()
    return game_state
end


-- ── Analytics Transport ────────────────────────────────────────────────────────
-- Sends events to Flask via WebRequest.custom() with JSON body.
-- Fire-and-forget: if Flask is down, events are logged locally but not retried.
-- The event_log ring buffer keeps a local copy regardless.

function ZoneHandler._sendEvent(event_type, data)
    -- Build the event payload
    local event = {
        event_type  = event_type,
        session_id  = game_state.session_id,
        timestamp   = os.time(),
        turn_number = game_state.turn_number,
        data        = data or {},
    }

    -- Local ring buffer (always)
    table.insert(game_state.event_log, event)
    if #game_state.event_log > game_state.event_log_max then
        table.remove(game_state.event_log, 1)
    end

    -- HTTP to Flask (when enabled)
    if ANALYTICS_ON then
        local json_body = JSON.encode(event)
        local headers = {
            ["Content-Type"] = "application/json",
            ["Accept"]       = "application/json",
        }

        WebRequest.custom(
            ANALYTICS_URL,
            "POST",
            true,       -- download response
            json_body,
            headers,
            function(request)
                if request.is_error then
                    -- Silent fail: Flask might not be running
                    -- Could log to a local buffer for retry later
                    if LOG_EVENTS then
                        print("[Analytics] HTTP failed: " .. (request.error or "unknown"))
                    end
                end
            end
        )
    end

    -- Debug logging
    if LOG_EVENTS and event_type ~= "zone_enter" and event_type ~= "zone_leave" then
        print("[Event] " .. event_type .. ": " .. JSON.encode(data or {}))
    end
end


-- ── Zone Identification ────────────────────────────────────────────────────────
-- Parses zone GMNotes to figure out which board and slot a zone belongs to.
-- Uses a lookup cache that's rebuilt when boards register.

function _identifyZone(zone)
    local guid = zone.getGUID()

    -- Check cache first
    if zone_lookup[guid] then
        return zone_lookup[guid]
    end

    -- Parse GMNotes
    local notes = zone.getGMNotes() or ""
    if notes == "" then return nil end

    local info = {}
    for key, val in notes:gmatch("(%w+)=([%w_]+)") do
        if key == "board" then info.board_guid = val end
        if key == "slot"  then info.slot_name  = val end
        if key == "color" then info.game_color = val end
    end

    if info.slot_name and info.game_color then
        zone_lookup[guid] = info
        return info
    end

    return nil
end

function _rebuildZoneLookup()
    zone_lookup = {}
    for gc, board in pairs(game_state.boards) do
        for slot_name, zguid in pairs(board.zone_guids) do
            zone_lookup[zguid] = {
                board_guid = board.board_guid,
                slot_name  = slot_name,
                game_color = gc,
            }
        end
    end
end


-- ── Utility ────────────────────────────────────────────────────────────────────

function _generateSessionId()
    -- Compact unique-enough ID for a playtest session
    local t = os.time()
    local r = math.random(1000, 9999)
    return string.format("ST-%d-%d", t, r)
end

function _copyTable(t)
    if type(t) ~= "table" then return t end
    local copy = {}
    for k, v in pairs(t) do
        copy[k] = _copyTable(v)
    end
    return copy
end


-- ── Module Return ──────────────────────────────────────────────────────────────
return ZoneHandler
