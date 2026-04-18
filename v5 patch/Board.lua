-- ============================================================
-- Board.lua  (v2.0)
-- Soul Tower Player Board
-- One board per player block (Champion + Henchman + Summoner)
--
-- KEY CHANGES FROM v1:
--   1. Normalized coordinate system (0-1 range) — survives
--      any board scale or image resolution change
--   2. Dynamic scripting zones — spawned at runtime, detect
--      cards entering/leaving Champion, Henchman, Equip, etc.
--   3. Snap points carry metadata (slot_name, zone) so you
--      can identify what snapped where without position math
--   4. getBounds()-driven layout — no hardcoded unit sizes
--   5. Clean separation: LAYOUT defines the board, functions
--      read from LAYOUT, nothing else knows pixel positions
-- ============================================================

local BOARD_VERSION = "2.0"

-- ── Normalized Layout Definition ──────────────────────────────────────────────
-- All positions expressed as fractions of board width (x) and height (z).
-- Origin (0,0) = board center. Range: -0.5 to +0.5 on each axis.
-- Y is always a small offset above the board surface.
--
-- To adjust any position: change the fraction here. That's it.
-- To scale the board image from 2048x1024 to 4096x2048: change nothing.
-- To scale the TTS object larger: change nothing.
--
-- Conversion at runtime:
--   world_pos = self.positionToWorld({nx * board_w, y_offset, nz * board_h})
-- where board_w and board_h come from getBounds().size

local Y_SNAP    = 0.15   -- snap point hover height (local units above surface)
local Y_BUTTON  = 0.40   -- button hover height
local Y_ZONE    = 0.50   -- scripting zone center height

local LAYOUT = {
    -- ── Hero Slots (top ~70% of board) ────────────────────────
    champion = {
        snap = { nx =  0.22, nz = -0.25 },
        zone = { nx =  0.22, nz = -0.25, sx = 0.22, sz = 0.30 },
        -- zone sx/sz = fractional width/height of the scripting zone
    },
    henchman = {
        snap = { nx = -0.22, nz = -0.25 },
        zone = { nx = -0.22, nz = -0.25, sx = 0.22, sz = 0.30 },
    },

    -- ── Slot Column (right of champion) ───────────────────────
    equip = {
        snap = { nx =  0.38, nz = -0.35 },
        zone = { nx =  0.38, nz = -0.35, sx = 0.10, sz = 0.10 },
    },
    runic = {
        snap = { nx =  0.38, nz = -0.22 },
        zone = { nx =  0.38, nz = -0.22, sx = 0.10, sz = 0.10 },
    },
    enchant = {
        snap = { nx =  0.38, nz = -0.10 },
        zone = { nx =  0.38, nz = -0.10, sx = 0.10, sz = 0.10 },
    },

    -- ── Summoner Strip (bottom ~30%) ──────────────────────────
    deck = {
        snap = { nx = -0.30, nz =  0.35 },
    },
    discard = {
        snap = { nx = -0.18, nz =  0.35 },
    },
    crystal_deck = {
        snap = { nx =  0.30, nz =  0.35 },
        zone = { nx =  0.30, nz =  0.35, sx = 0.18, sz = 0.12 },
    },

    -- ── Legendary delivery offsets (from champion world pos) ──
    legendary_1 = { offset = { nx =  0.09, nz =  0.00 } },
    legendary_2 = { offset = { nx =  0.09, nz =  0.10 } },
}

-- Button positions (normalized)
local BTN_LAYOUT = {
    unlock = {
        pos = { nx = -0.47, nz = -0.45 },
        label = "⚙", tooltip = "Unlock / Reposition Board",
        w = 300, h = 300, font = 200,
        color = {0.3, 0.3, 0.3}, font_color = {1, 1, 1},
        func = "btn_toggleLock",
        always = true,  -- visible regardless of board state
    },
    manifest_champion = {
        pos = { nx =  0.22, nz = -0.25 },
        label = "Manifest\nChampion",
        tooltip = "Choose a Hero to Manifest as Champion",
        w = 900, h = 500, font = 120,
        color = {0.2, 0.5, 0.9}, font_color = {1, 1, 1},
        func = "btn_manifestChampion",
        show_when = function(s) return not s.champion_present end,
    },
    manifest_henchman = {
        pos = { nx = -0.22, nz = -0.25 },
        label = "Manifest\nHenchman",
        tooltip = "Shuffle Cursed pile and draw top Henchman",
        w = 900, h = 500, font = 120,
        color = {0.7, 0.2, 0.2}, font_color = {1, 1, 1},
        func = "btn_manifestHenchman",
        show_when = function(s) return not s.henchman_present end,
    },
    block_wakeup = {
        pos = { nx =  0.00, nz = -0.40 },
        label = "⚡ Block\nWake Up",
        tooltip = "Wake Up both Champion and Henchman, compare Initiative",
        w = 900, h = 500, font = 130,
        color = {0.15, 0.55, 0.3}, font_color = {1, 1, 1},
        func = "btn_blockWakeUp",
        show_when = function(s) return s.champion_present and s.henchman_present end,
    },
    standby = {
        pos = { nx =  0.12, nz = -0.40 },
        label = "🌙 Stand\nBy",
        tooltip = "Resolve Standby for this block",
        w = 900, h = 500, font = 130,
        color = {0.4, 0.2, 0.6}, font_color = {1, 1, 1},
        func = "btn_standBy",
        show_when = function(s) return s.champion_present and s.henchman_present end,
    },
    attack = {
        pos = { nx =  0.22, nz =  0.08 },
        label = "⚔ Attack",
        tooltip = "Perform Command Attack",
        w = 800, h = 400, font = 150,
        color = {0.8, 0.3, 0.1}, font_color = {1, 1, 1},
        func = "btn_attack",
        show_when = function(s) return s.champion_present and s.henchman_present end,
    },
    crystal_toggle = {
        pos = { nx =  0.30, nz =  0.25 },
        label = "💎 Crystals",
        tooltip = "Toggle Crystal spread / stack view",
        w = 700, h = 350, font = 120,
        color = {0.1, 0.4, 0.6}, font_color = {1, 1, 1},
        func = "btn_toggleCrystals",
        always = true,
    },
}

-- Camera defaults
local CAMERA = {
    PITCH    = 40,
    DISTANCE = 28,
}

-- Teams: TTS team name -> { champion_color, henchman_color }
local TEAMS = {
    Hearts   = { champion = "Yellow", henchman = "Green"  },
    Clubs    = { champion = "Red",    henchman = "Teal"   },
    Diamonds = { champion = "Pink",   henchman = "Blue"   },
    Spades   = { champion = "Orange", henchman = "Purple" },
}


-- ── Board State ────────────────────────────────────────────────────────────────

local state = {
    game_color     = nil,
    seat_color     = nil,
    team           = nil,
    henchman_color = nil,

    champion_present  = false,
    henchman_present  = false,
    crystals_spread   = false,
    locked            = true,

    -- Summoner resources
    summoner = {
        life     = 30,
        mana     = 4,
        presence = 0,
        pillar   = 0,
        pain     = 1,
        spirit   = 0,
        sorcery  = 0,
    },
}

-- Runtime references (not saved)
local board_w    = 1   -- physical width  in TTS units (from getBounds)
local board_h    = 1   -- physical height in TTS units (from getBounds)
local zones      = {}  -- slot_name -> zone object reference
local zone_guids = {}  -- slot_name -> guid (for save/load)


-- ── Lifecycle ──────────────────────────────────────────────────────────────────

function onLoad(saved_state)
    if saved_state and saved_state ~= "" then
        local ok, decoded = pcall(JSON.decode, saved_state)
        if ok and decoded then
            if decoded.state then state = decoded.state end
            if decoded.zone_guids then zone_guids = decoded.zone_guids end
        end
    end

    _parseGMNotes()
    _measureBoard()

    if state.game_color then
        _initBoard()
    else
        _promptColorSelection()
    end
end

function onSave()
    return JSON.encode({
        state      = state,
        zone_guids = zone_guids,
    })
end


-- ── Board Measurement ──────────────────────────────────────────────────────────
-- getBounds().size gives us the actual physical footprint of the board in world
-- units. For a 2:1 tile, size.x is the width, size.z is the height.
-- This runs once on load and gives us the multipliers for normalized coords.

function _measureBoard()
    local bounds = self.getBounds()
    board_w = bounds.size.x
    board_h = bounds.size.z

    -- Sanity check: if bounds are suspiciously small (object still loading),
    -- fall back to reasonable defaults and re-measure after a delay
    if board_w < 1 or board_h < 1 then
        board_w = 30
        board_h = 15
        Wait.frames(function()
            local b = self.getBounds()
            if b.size.x > 1 then
                board_w = b.size.x
                board_h = b.size.z
                -- Rebuild everything with correct measurements
                _buildSnapPoints()
                _buildButtons()
                _rebuildZones()
            end
        end, 15)
    end
end


-- ── Coordinate Helpers ─────────────────────────────────────────────────────────
-- These convert normalized fractions to local positions that work with
-- self.positionToWorld() and self.setSnapPoints()

-- Normalized -> local position on the board surface
function _localPos(nx, nz, y)
    return {
        x = nx * board_w,
        y = y or Y_SNAP,
        z = nz * board_h,
    }
end

-- Normalized -> world position
function _worldPos(nx, nz, y)
    return self.positionToWorld(_localPos(nx, nz, y))
end

-- Normalized size -> world scale for a scripting zone
-- Zone scale is in world units, not local, so we need to account for
-- the object's actual scale
function _zoneScale(sx, sz)
    local obj_scale = self.getScale()
    return {
        x = sx * board_w * obj_scale.x,
        y = 3,  -- tall enough to catch cards placed on board
        z = sz * board_h * obj_scale.z,
    }
end


-- ── Initialization ─────────────────────────────────────────────────────────────

function _parseGMNotes()
    local notes = self.getGMNotes() or ""
    for key, val in notes:gmatch("(%w+)=([%w_]+)") do
        if key == "game_color"     then state.game_color     = val end
        if key == "seat_color"     then state.seat_color     = val end
        if key == "team"           then state.team           = val end
        if key == "henchman_color" then state.henchman_color = val end
    end
end

function _writeGMNotes()
    local parts = {
        "game_color="     .. (state.game_color     or ""),
        "seat_color="     .. (state.seat_color     or ""),
        "team="           .. (state.team           or ""),
        "henchman_color=" .. (state.henchman_color or ""),
    }
    self.setGMNotes(table.concat(parts, ";"))
end

function _promptColorSelection()
    local options = {"Yellow", "Red", "Pink", "Orange"}
    local placer  = _getPlacerColor()

    if placer and Player[placer] then
        Player[placer].showOptionsDialog(
            "Choose your Champion color for this board:",
            options,
            1,
            function(choice, index, p_color)
                _assignColor(choice, p_color)
            end
        )
    end
end

function _assignColor(game_color, seat_color)
    for team, colors in pairs(TEAMS) do
        if colors.champion == game_color then
            state.team           = team
            state.henchman_color = colors.henchman
            break
        end
    end

    state.game_color = game_color
    state.seat_color = seat_color

    _writeGMNotes()
    _initBoard()
    _focusCamera()

    printToColor(
        string.format("[Board] %s board created. Team: %s. Henchman: %s.",
            game_color, state.team or "?", state.henchman_color or "?"),
        seat_color
    )
end

function _initBoard()
    self.setName((state.game_color or "?") .. " Board")
    self.interactable = not state.locked

    _buildSnapPoints()
    _buildButtons()
    _buildXmlUI()
    _rebuildZones()
    _generateHandZones()
end


-- ── Snap Points ────────────────────────────────────────────────────────────────
-- Each snap point carries metadata:
--   slot_name  = "champion", "equip", "deck", etc.
--   zone       = "hero" | "slot" | "summoner"
-- TTS ignores unknown keys, but we can read them with getSnapPoints()

function _buildSnapPoints()
    local snaps = {}

    local slot_meta = {
        champion     = "hero",
        henchman     = "hero",
        equip        = "slot",
        runic        = "slot",
        enchant      = "slot",
        deck         = "summoner",
        discard      = "summoner",
        crystal_deck = "summoner",
    }

    for slot_name, zone_type in pairs(slot_meta) do
        local def = LAYOUT[slot_name]
        if def and def.snap then
            table.insert(snaps, {
                position      = _localPos(def.snap.nx, def.snap.nz, Y_SNAP),
                rotation      = { x = 0, y = 0, z = 0 },
                rotation_snap = true,
                tags          = { state.game_color or "Board", slot_name },
                -- Custom metadata (preserved by TTS, accessible via getSnapPoints)
                slot_name     = slot_name,
                zone          = zone_type,
            })
        end
    end

    self.setSnapPoints(snaps)
end


-- ── Scripting Zones ────────────────────────────────────────────────────────────
-- Spawned dynamically, positioned relative to the board.
-- Zone GUIDs are saved so we can reconnect on reload instead of re-spawning.
--
-- Events fire on Global:
--   onObjectEnterZone(zone, object)
--   onObjectLeaveZone(zone, object)
-- Global can identify the zone's purpose via zone.getGMNotes()

function _rebuildZones()
    -- First, try to reconnect to existing zones from a save
    if next(zone_guids) then
        local all_found = true
        for slot_name, guid in pairs(zone_guids) do
            local existing = getObjectFromGUID(guid)
            if existing then
                zones[slot_name] = existing
                -- Re-position in case the board moved
                _positionZone(slot_name, existing)
            else
                all_found = false
            end
        end
        if all_found then return end
    end

    -- Destroy any stale zones before rebuilding
    _destroyAllZones()

    -- Spawn new zones for every LAYOUT entry that has a zone definition
    for slot_name, def in pairs(LAYOUT) do
        if def.zone then
            _spawnZone(slot_name, def.zone)
        end
    end
end

function _spawnZone(slot_name, zone_def)
    local world_pos   = _worldPos(zone_def.nx, zone_def.nz, Y_ZONE)
    local world_scale = _zoneScale(zone_def.sx, zone_def.sz)
    local board_rot   = self.getRotation()

    local gm_notes = string.format(
        "board=%s;slot=%s;color=%s",
        self.getGUID(),
        slot_name,
        state.game_color or ""
    )

    spawnObject({
        type     = "ScriptingTrigger",
        position = world_pos,
        rotation = { x = 0, y = board_rot.y, z = 0 },
        scale    = world_scale,
        sound    = false,
        snap_to_grid = false,
        callback_function = function(zone_obj)
            zone_obj.setGMNotes(gm_notes)
            zone_obj.setName(
                (state.game_color or "?") .. " " .. slot_name .. " Zone"
            )
            zone_obj.locked = true
            zones[slot_name]      = zone_obj
            zone_guids[slot_name] = zone_obj.getGUID()
        end,
    })
end

function _positionZone(slot_name, zone_obj)
    local def = LAYOUT[slot_name]
    if not def or not def.zone then return end

    local zd        = def.zone
    local world_pos = _worldPos(zd.nx, zd.nz, Y_ZONE)
    local board_rot = self.getRotation()

    zone_obj.setPosition(world_pos)
    zone_obj.setRotation({ x = 0, y = board_rot.y, z = 0 })
    zone_obj.setScale(_zoneScale(zd.sx, zd.sz))
end

function _destroyAllZones()
    for slot_name, zone_obj in pairs(zones) do
        if zone_obj and not zone_obj.isDestroyed() then
            zone_obj.destruct()
        end
    end
    zones      = {}
    zone_guids = {}
end


-- ── 3D Buttons ─────────────────────────────────────────────────────────────────
-- Driven entirely by BTN_LAYOUT. Each entry declares when it should be visible
-- via `always = true` or `show_when = function(state) -> bool`.

function _buildButtons()
    self.clearButtons()

    for btn_name, def in pairs(BTN_LAYOUT) do
        local show = false
        if def.always then
            show = true
        elseif def.show_when then
            show = def.show_when(state)
        end

        if show then
            local pos = _localPos(def.pos.nx, def.pos.nz, Y_BUTTON)
            self.createButton({
                label          = def.label,
                click_function = def.func,
                function_owner = self,
                position       = pos,
                height         = def.h,
                width          = def.w,
                font_size      = def.font,
                color          = def.color,
                font_color     = def.font_color,
                tooltip        = def.tooltip,
            })
        end
    end
end


-- ── XML UI Overlay (Summoner Strip) ───────────────────────────────────────────
-- Displays live counters for summoner resources.
-- Panel positioned on the board surface via XML positioning.

function _buildXmlUI()
    local fields = {
        { id = "life",    label = "Life",    color = "#ff4444", default = state.summoner.life },
        { id = "mana",    label = "Mana",    color = "#44aaff", default = state.summoner.mana },
        { id = "pres",    label = "Pres",    color = "#88ccff", default = state.summoner.presence },
        { id = "pillar",  label = "Pillar",  color = "#ffcc44", default = state.summoner.pillar },
        { id = "pain",    label = "Pain",    color = "#ff8844", default = state.summoner.pain },
        { id = "spirit",  label = "Spirit",  color = "#88ff88", default = state.summoner.spirit },
        { id = "sorcery", label = "Sorcery", color = "#cc88ff", default = state.summoner.sorcery },
    }

    local spacing = 400
    local start_x = -1 * (#fields - 1) * spacing / 2
    local children = {}

    for i, f in ipairs(fields) do
        local x = start_x + (i - 1) * spacing
        table.insert(children, string.format(
            [[<Text id="lbl_%s" text="%s" fontSize="55" color="white" position="%d 80 0"/>]],
            f.id, f.label, x
        ))
        table.insert(children, string.format(
            [[<Text id="val_%s" text="%s" fontSize="90" fontStyle="Bold" color="%s" position="%d -20 0"/>]],
            f.id, tostring(f.default), f.color, x
        ))
    end

    local xml = string.format([[
<Panel id="summoner_strip"
       position="0 -0.1 55"
       rotation="90 0 0"
       width="3200" height="300"
       color="#00000088">
  %s
</Panel>
]], table.concat(children, "\n  "))

    self.UI.setXml(xml)
end


-- ── Hand Zone Generation ───────────────────────────────────────────────────────

function _generateHandZones()
    if not state.seat_color then return end
    local p = Player[state.seat_color]
    if not p or not p.seated then return end

    local pos = self.getPosition()
    local yaw = self.getRotation().y

    -- Hand zone 1: Player draw hand (below board, facing player)
    local hand1_pos = _rotateOffset(pos, { x = 0, y = 1, z = board_h * 0.8 }, yaw)
    p.setHandTransform({
        position = hand1_pos,
        rotation = { x = 0, y = yaw, z = 0 },
        scale    = { x = board_w * 0.7, y = 5, z = 1 },
    }, 1)

    -- Hand zone 2: Tomb (left side of board)
    local hand2_pos = _rotateOffset(pos, { x = -board_w * 0.55, y = 1, z = board_h * 0.2 }, yaw)
    p.setHandTransform({
        position = hand2_pos,
        rotation = { x = 0, y = yaw + 90, z = 0 },
        scale    = { x = board_h * 0.6, y = 5, z = 1 },
    }, 2)
end


-- ── Camera ─────────────────────────────────────────────────────────────────────

function _focusCamera()
    if not state.seat_color then return end
    local p = Player[state.seat_color]
    if not p or not p.seated then return end

    Wait.frames(function()
        p.lookAt({
            position = self.getPosition(),
            pitch    = CAMERA.PITCH,
            yaw      = self.getRotation().y,
            distance = CAMERA.DISTANCE,
        })
    end, 10)
end


-- ── Button Handlers ────────────────────────────────────────────────────────────

function btn_toggleLock(player_color, alt_click)
    state.locked = not state.locked
    self.interactable = not state.locked
    local msg = state.locked and "Board locked." or "Board unlocked."
    printToColor("[Board] " .. msg, player_color)
end

function btn_manifestChampion(player_color, alt_click)
    local options = _getConjureOptions()
    if #options == 0 then
        printToColor("[Board] No heroes available in the Conjure Pool.", player_color)
        return
    end

    local names = {}
    for _, h in ipairs(options) do table.insert(names, h.name) end

    Player[player_color].showOptionsDialog(
        "Choose a Hero to Manifest as Champion:",
        names, 1,
        function(choice, index, p_color)
            _manifestChampion(options[index], p_color)
        end
    )
end

function btn_manifestHenchman(player_color, alt_click)
    local cursed_pile = getObjectsWithAllTags({"Cursed", "Hero", "Deck"})[1]
    if not cursed_pile then
        printToColor("[Board] Could not find Cursed Hero pile.", player_color)
        return
    end

    cursed_pile.shuffle()
    local snap = LAYOUT.henchman.snap
    local target_pos = _worldPos(snap.nx, snap.nz, Y_SNAP + 0.5)

    Wait.frames(function()
        cursed_pile.takeObject({
            position          = target_pos,
            rotation          = _cardRotation(),
            smooth            = true,
            callback_function = function(obj)
                _onHenchmanManifested(obj)
            end,
        })
    end, 20)
end

function btn_blockWakeUp(player_color, alt_click)
    local champion = _getHero(state.game_color)
    local henchman = _getHero(state.henchman_color)

    if not champion then
        printToColor("[Board] No Champion present.", player_color)
        return
    end
    if not henchman then
        printToColor("[Board] No Henchman present.", player_color)
        return
    end

    printToAll(string.format("[%s Block] Wake Up begins.", state.game_color), {1,1,1})

    local champ_init = champion.call("wake_up") or 0
    local hench_init = henchman.call("wake_up") or 0

    Wait.frames(function()
        _announceInitiative(champ_init, hench_init)
    end, 5)
end

function btn_standBy(player_color, alt_click)
    printToAll(string.format("[%s Block] Standby begins.", state.game_color), {1,1,1})
    Global.call("runStandby", {
        game_color    = state.game_color,
        henchman_color = state.henchman_color,
    })
end

function btn_attack(player_color, alt_click)
    local champion = _getHero(state.game_color)
    if not champion then
        printToColor("[Board] No Champion to attack with.", player_color)
        return
    end
    champion.call("command_attack")
end

function btn_toggleCrystals(player_color, alt_click)
    local crystal_deck = _getCrystalDeck()
    if not crystal_deck then
        printToColor("[Board] Crystal deck not found.", player_color)
        return
    end

    state.crystals_spread = not state.crystals_spread
    if state.crystals_spread then
        _spreadCrystals(crystal_deck)
    else
        _stackCrystals()
    end
end


-- ── Manifest Logic ─────────────────────────────────────────────────────────────

function _manifestChampion(hero_data, seat_color)
    local snap = LAYOUT.champion.snap
    local champ_pos = _worldPos(snap.nx, snap.nz, Y_SNAP + 0.5)

    if hero_data.object then
        hero_data.object.setPosition(champ_pos)
        hero_data.object.setRotation(_cardRotation())
        _onChampionManifested(hero_data.object, seat_color)
    else
        local pool = getObjectsWithAllTags({"Conjure", "Pool", "Deck"})[1]
        if not pool then
            printToColor("[Board] Conjure Pool deck not found.", seat_color)
            return
        end
        for _, contained in ipairs(pool.getObjects()) do
            if contained.name == hero_data.name then
                pool.takeObject({
                    index    = contained.index,
                    position = champ_pos,
                    rotation = _cardRotation(),
                    smooth   = true,
                    callback_function = function(obj)
                        _onChampionManifested(obj, seat_color)
                    end,
                })
                return
            end
        end
        printToColor("[Board] Hero '" .. hero_data.name .. "' not found in pool.", seat_color)
    end
end

function _onChampionManifested(hero_obj, seat_color)
    local tags = hero_obj.getTags()
    table.insert(tags, state.game_color)
    hero_obj.setTags(tags)

    state.champion_present = true
    _getLegendary(hero_obj)
    _buildButtons()

    printToAll(
        string.format("[%s] %s has been Manifested as Champion.",
            state.game_color, hero_obj.getName()),
        {0.4, 0.9, 0.4}
    )
end

function _onHenchmanManifested(hero_obj)
    local tags = hero_obj.getTags()
    table.insert(tags, state.henchman_color)
    hero_obj.setTags(tags)

    state.henchman_present = true
    _buildButtons()

    printToAll(
        string.format("[%s] %s has been Manifested as Henchman.",
            state.henchman_color, hero_obj.getName()),
        {0.9, 0.4, 0.4}
    )
end


-- ── Legendary Card Fetch ───────────────────────────────────────────────────────
-- Single-pass find, staggered take with Wait.frames to avoid index shift

function _getLegendary(hero_obj)
    local hero_name = hero_obj.getName()

    local data_block = getObjectsWithAllTags({"Hero", "Data"})[1]
    if not data_block then
        printToAll("[Board] Hero DataBlock not found.", {1,0,0})
        return
    end

    local hero_data = data_block.call("giveInfo", hero_name)
    if not hero_data then
        printToAll("[Board] No data for hero: " .. hero_name, {1,0,0})
        return
    end

    local card1_name = hero_data[6]
    local card2_name = hero_data[7]

    printToAll(string.format("[%s] Fetching Legendary: %s & %s",
        state.game_color, card1_name, card2_name), {0.8, 0.8, 0.4})

    local container = getObjectsWithAllTags({"Legendary", "Deck"})[1]
    if not container then
        printToAll("[Board] Legendary deck not found.", {1,0,0})
        return
    end

    -- Compute delivery positions using normalized offsets from champion
    local hero_pos  = hero_obj.getPosition()
    local board_yaw = self.getRotation().y
    local l1 = LAYOUT.legendary_1.offset
    local l2 = LAYOUT.legendary_2.offset
    local pos1 = _rotateOffset(hero_pos, { x = l1.nx * board_w, y = 0, z = l1.nz * board_h }, board_yaw)
    local pos2 = _rotateOffset(hero_pos, { x = l2.nx * board_w, y = 0, z = l2.nz * board_h }, board_yaw)
    local card_rot = _cardRotation()

    -- Take card 1
    for _, contained in ipairs(container.getObjects()) do
        if contained.name == card1_name then
            container.takeObject({
                index    = contained.index,
                position = pos1,
                rotation = card_rot,
                smooth   = true,
            })
            break
        end
    end

    -- Take card 2 after delay (container refreshes after removal)
    Wait.frames(function()
        local fresh = getObjectsWithAllTags({"Legendary", "Deck"})[1]
        if not fresh then return end
        for _, contained in ipairs(fresh.getObjects()) do
            if contained.name == card2_name then
                fresh.takeObject({
                    index    = contained.index,
                    position = pos2,
                    rotation = card_rot,
                    smooth   = true,
                })
                return
            end
        end
        printToAll("[Board] Could not find " .. card2_name, {1,0.5,0})
    end, 30)
end


-- ── Conjure Pool Helpers ───────────────────────────────────────────────────────

function _getConjureOptions()
    local options = {}

    local pool_objects = getObjectsWithAllTags({"Conjure", "Pool"})
    for _, obj in ipairs(pool_objects) do
        if obj.hasTag("Hero") then
            table.insert(options, {
                name   = obj.getName(),
                object = obj,
                source = "conjure_pool",
            })
        end
    end

    local ascended = getObjectsWithAllTags({"Ascended", state.game_color})
    for _, obj in ipairs(ascended) do
        table.insert(options, {
            name   = obj.getName(),
            object = obj,
            source = "ascended",
        })
    end

    return options
end


-- ── Initiative ─────────────────────────────────────────────────────────────────

function _announceInitiative(champ_init, hench_init)
    local gc = state.game_color
    local hc = state.henchman_color

    printToAll(string.format(
        "[%s Block] Initiative: Champion (%s): %d | Henchman (%s): %d",
        gc, gc, champ_init, hc, hench_init
    ), {1, 1, 0.6})

    if champ_init > hench_init then
        printToAll(string.format("  Champion goes FIRST.", gc), {0.4, 0.9, 0.4})
    elseif hench_init > champ_init then
        printToAll(string.format("  Henchman goes FIRST.", hc), {0.9, 0.4, 0.4})
    else
        printToAll("  TIE: roll again to break.", {1, 0.8, 0.2})
    end
end


-- ── Crystal Helpers ────────────────────────────────────────────────────────────

function _getCrystalDeck()
    return getObjectsWithAllTags({state.game_color, "Crystal", "Deck"})[1]
end

function _spreadCrystals(deck)
    local snap = LAYOUT.crystal_deck.snap
    local base_pos = _worldPos(snap.nx, snap.nz, Y_SNAP + 0.3)
    local count    = #deck.getObjects()
    local spacing  = 2.5

    for i = 1, count do
        local offset_x = (i - 1) * spacing - ((count - 1) * spacing / 2)
        deck.takeObject({
            index    = 0,
            position = { base_pos.x + offset_x, base_pos.y + 0.5, base_pos.z },
            rotation = _cardRotation(),
            smooth   = true,
        })
        Wait.frames(function() end, 5)
    end
end

function _stackCrystals()
    local crystals = getObjectsWithAllTags({state.game_color, "Crystal", "Card"})
    local snap     = LAYOUT.crystal_deck.snap
    local target   = _worldPos(snap.nx, snap.nz, Y_SNAP + 0.3)
    local rot      = _cardRotation()

    for i, card in ipairs(crystals) do
        Wait.frames(function()
            card.setPosition({ target.x, target.y + (i * 0.1), target.z })
            card.setRotation(rot)
        end, i * 8)
    end
end


-- ── Utility ────────────────────────────────────────────────────────────────────

function _rotateOffset(base_pos, offset, yaw_deg)
    local rad = math.rad(yaw_deg)
    local cos = math.cos(rad)
    local sin = math.sin(rad)
    return {
        x = base_pos.x + (offset.x * cos - offset.z * sin),
        y = base_pos.y + (offset.y or 0),
        z = base_pos.z + (offset.x * sin + offset.z * cos),
    }
end

function _cardRotation()
    local r = self.getRotation()
    return { x = 0, y = r.y, z = 0 }
end

function _getHero(color)
    if not color then return nil end
    return getObjectsWithAllTags({"Hero", color})[1]
end

function _getPlacerColor()
    for _, p in ipairs(Player.getPlayers()) do
        if p.seated then return p.color end
    end
    return "White"
end


-- ── Public API (callable from Global) ─────────────────────────────────────────

function getGameColor()    return state.game_color    end
function getTeam()         return state.team           end
function getSeatColor()    return state.seat_color     end
function getSummonerData() return state.summoner       end
function getZones()        return zones                end
function getZoneGuids()    return zone_guids            end

-- Update a single summoner resource and refresh the XML UI counter
function updateSummonerUI(key, value)
    state.summoner[key] = value
    -- Map state keys to UI element IDs
    local ui_map = {
        life = "val_life", mana = "val_mana", presence = "val_pres",
        pillar = "val_pillar", pain = "val_pain", spirit = "val_spirit",
        sorcery = "val_sorcery",
    }
    local ui_id = ui_map[key]
    if ui_id then
        self.UI.setAttribute(ui_id, "text", tostring(value))
    end
end

-- Query what's in a specific zone by slot name
function getZoneContents(slot_name)
    local zone_obj = zones[slot_name]
    if not zone_obj then return {} end
    return zone_obj.getObjects()
end

-- Called by Global when champion is defeated
function onChampionDefeated()
    state.champion_present = false
    _buildButtons()
    printToAll(
        string.format("[%s] Champion defeated. Conjure at Standby.", state.game_color),
        {0.9, 0.5, 0.2}
    )
end

function onHenchmanDefeated()
    state.henchman_present = false
    _buildButtons()
    printToAll(
        string.format("[%s] Henchman defeated.", state.henchman_color),
        {0.9, 0.3, 0.3}
    )
end

-- Reposition all zones (call after board is moved/scaled)
function refreshLayout()
    _measureBoard()
    _buildSnapPoints()
    _buildButtons()
    _rebuildZones()
    _generateHandZones()
end

-- Clean up zones when board is destroyed
function onDestroy()
    _destroyAllZones()
end
