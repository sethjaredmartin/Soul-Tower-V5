-- ============================================================
-- Global.lua
-- Soul Tower — Global Script Hub
--
-- This is the thin entry point. It wires TTS lifecycle events
-- to the appropriate module. All game logic lives in modules;
-- Global.lua is just routing.
--
-- MODULE LOADING:
--   With TTS Tools bundling (VS Code extension), each module
--   is a separate .lua file that returns a table.
--   require() works via the bundler at build time.
--
--   Without bundling, paste module code above this file
--   or use the single-file fallback pattern at the bottom.
-- ============================================================

-- ── Module Imports ─────────────────────────────────────────────────────────────
-- If using TTS Tools bundler, these are real require() calls.
-- If pasting into TTS editor directly, define modules inline above.

local ZoneHandler = require("ZoneHandler")
-- local WakeUp    = require("WakeUp")      -- future module
-- local Standby   = require("Standby")     -- future module
-- local Attack    = require("Attack")       -- future module


-- ── TTS Lifecycle ──────────────────────────────────────────────────────────────

function onLoad(saved_state)
    -- Start a new analytics session
    ZoneHandler.startSession()

    -- Discover existing boards and register them
    Wait.frames(function()
        _discoverBoards()
    end, 30)  -- wait for board objects to finish their own onLoad

    print("[Global] Soul Tower loaded. Session: " ..
        (ZoneHandler.getGameState().session_id or "?"))
end

function onSave()
    -- Global state is reconstructed from board objects on load,
    -- but we save the event log and session info for continuity
    local gs = ZoneHandler.getGameState()
    return JSON.encode({
        session_id  = gs.session_id,
        started_at  = gs.started_at,
        turn_number = gs.turn_number,
    })
end


-- ── Zone Events (routed to ZoneHandler) ────────────────────────────────────────

function onObjectEnterZone(zone, obj)
    ZoneHandler.onObjectEnterZone(zone, obj)
end

function onObjectLeaveZone(zone, obj)
    ZoneHandler.onObjectLeaveZone(zone, obj)
end


-- ── Board Discovery ────────────────────────────────────────────────────────────
-- Scans all objects for boards (identified by GMNotes pattern) and registers
-- them with ZoneHandler. Called on load and can be called manually.

function _discoverBoards()
    for _, obj in ipairs(getAllObjects()) do
        local notes = obj.getGMNotes() or ""
        if notes:find("game_color=") and notes:find("team=") then
            -- This is a Soul Tower board
            local info = {}
            for key, val in notes:gmatch("(%w+)=([%w_]+)") do
                info[key] = val
            end

            if info.game_color then
                -- Get zone GUIDs from the board
                local zone_guids = {}
                local ok, zg = pcall(function()
                    return obj.call("getZoneGuids")
                end)
                if ok and zg then zone_guids = zg end

                ZoneHandler.registerBoard({
                    board_guid     = obj.getGUID(),
                    game_color     = info.game_color,
                    seat_color     = info.seat_color,
                    team           = info.team,
                    henchman_color = info.henchman_color,
                    zone_guids     = zone_guids,
                })
            end
        end
    end
end


-- ── Public API (called by Board.lua and other objects) ─────────────────────────

-- Board.lua calls this after self-registration
function registerBoard(params)
    ZoneHandler.registerBoard(params)
end

-- Board.lua calls this during Standby
function runStandby(params)
    -- params = { game_color, henchman_color }
    -- TODO: implement full Standby sequence in Standby.lua
    ZoneHandler.recordStandby(params)
    printToAll(string.format("[%s Block] Standby resolved.", params.game_color), {0.7, 0.5, 0.9})
end

-- Turn management (called by turn controller or manually)
function advanceTurn(game_color)
    ZoneHandler.advanceTurn(game_color)
end

-- Summoner resource changes should go through here for tracking
function updateSummoner(params)
    -- params = { game_color, key, value }
    local board_obj = _getBoardByColor(params.game_color)
    if not board_obj then return end

    -- Get old value for delta tracking
    local gs = ZoneHandler.getGameState()
    local board_state = gs.boards[params.game_color]
    local old_val = board_state and board_state.summoner[params.key] or 0

    -- Update the board UI
    board_obj.call("updateSummonerUI", { key = params.key, value = params.value })

    -- Record for analytics
    ZoneHandler.recordSummonerUpdate(params.game_color, params.key, old_val, params.value)
end

-- Get full game state (for debugging, or for other modules)
function getGameState()
    return ZoneHandler.getGameState()
end

-- Get state snapshot (for external tools)
function getSnapshot()
    return ZoneHandler.getStateSnapshot()
end

-- End session (call before closing)
function endSession()
    ZoneHandler.endSession()
end


-- ── Utility ────────────────────────────────────────────────────────────────────

function _getBoardByColor(game_color)
    local gs = ZoneHandler.getGameState()
    local board_data = gs.boards[game_color]
    if not board_data then return nil end
    return getObjectFromGUID(board_data.board_guid)
end
