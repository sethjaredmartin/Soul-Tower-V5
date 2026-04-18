# TAGS.md — Soul Tower Object Tag Reference

This document defines every tag used in Soul Tower. Tags are how objects identify themselves in TTS so that scripts, scripting zones, and queries can find them reliably without needing GUIDs or hardcoded references.

**Single source of truth.** Python (the tagger) and Lua (the runtime queries) both follow this vocabulary. Add a new tag here before using it anywhere else.

---

## How tags work

Tags are free-form strings attached to any TTS object. TTS has built-in API calls for tag queries:

```lua
getObjectsWithAllTags({"Hero", "Yellow"})      -- intersection
getObjectsWithAnyTags({"Burn", "Agony"})       -- union
obj.hasTag("Cursed")                           -- boolean check
obj.addTag("Forsake")
obj.removeTag("Default")
obj.setTags({"Hero", "Card", "Legendary"})     -- replaces all tags
```

Python writes these same tags into the TTS save JSON at the `Tags` array on each object.

---

## Tag categories

Every tag belongs to exactly one category. When you add a tag to an object, pick tags from multiple categories to fully describe it.

| Category | Purpose | Count |
|----------|---------|-------|
| Object Class | What kind of thing is this? | 12 |
| Card Type | Brutal, Ritual, Spell | 3 |
| Card Subtype | Timing category | 4 |
| Card Flags | Properties like Cursed, Default | 8 |
| Ownership | Which player color owns this? | 9 |
| Role | Champion vs Henchman | 2 |
| Alignment | Blessed vs Cursed hero | 2 |
| Status | Which status this counts as | 8 |
| Pile | Which physical pile | 6 |
| Slot | Equip, Enchant, Runic | 3 |
| Tomb | Forsake, Forbid, Exhume | 3 |
| Resource | Life, Mana, Spirit, Presence | 4 |

---

## Object Class

What kind of thing is this object?

| Tag | Applied to |
|-----|------------|
| `Hero` | Hero cards (both Blessed and Cursed) |
| `Card` | Any playable card (common, legendary, crystal, calamity) |
| `Crystal` | Crystal cards in the Crystal Zone |
| `Calamity` | Calamity cards in the Calamity deck |
| `Villain` | The active Villain object |
| `Pile` | Any face-down or face-up stack that is not a deck (e.g., the Cursed pile with its top card visible) |
| `Deck` | A deck object (shuffles, draws from top/bottom) |
| `Tile` | A player tile, villain tile, or conjure tile |
| `Zone` | Scripting zones spawned on tiles |
| `Token` | Physical tokens (Order, Crush, Pray, Crystal) if any remain physical |
| `Counter` | Physical counter objects if any remain physical |
| `DataBlock` | The Lua data block object that holds card/hero lookup data |

---

## Card Type

Exactly one of these on any card.

| Tag | Meaning |
|-----|---------|
| `Brutal` | Brutal card (Default: Order) |
| `Ritual` | Ritual card (Default: Pray) |
| `Spell` | Spell card (Default: Crush) |

---

## Card Subtype

Exactly one of these on any card. Determines timing tier.

| Tag | Tier | Playable when |
|-----|------|---------------|
| `Normal` | 0 | Your turn only, nothing else happening |
| `Instant` | 1 | Any time (Spell only) |
| `Entropy` | 1 | Any time, Foe gains Mana (Ritual only) |
| `Reaction` | 2 | Trigger condition active (Brutal only) |

---

## Card Flags

Zero or more of these on any card.

| Tag | Meaning |
|-----|---------|
| `Cursed` | Cannot be exiled. Pitches and inflicts Pain instead. |
| `Default` | Villain will not play this from hand. Used in Default block behavior. |
| `Inspire` | Has an Inspire alternate cost. Marked for exile after Inspire Play. |
| `Tomb` | Has a Tomb effect (Forsake, Forbid, or Exhume). |
| `Legendary` | Belongs to a specific Hero. Acquired via Manifest. |
| `Signature` | Alias for Legendary in some contexts. Use `Legendary` canonically. |
| `Starter` | In every player's starting deck (Journey). |
| `MarkedForExile` | Temporary flag added at runtime when a card will be exiled on leaving zone. |

---

## Ownership

Exactly one of these on any player-owned object. Two on shared tiles (e.g., Villain tile may have `Villain`).

### Champion colors (player-controlled)

| Tag | Paired Henchman |
|-----|----------------|
| `Yellow` | `Green` |
| `Red` | `Teal` |
| `Pink` | `Blue` |
| `Orange` | `Purple` |

### Henchman colors (villain-controlled)

| Tag | Paired Champion |
|-----|----------------|
| `Green` | `Yellow` |
| `Teal` | `Red` |
| `Blue` | `Pink` |
| `Purple` | `Orange` |

### Shared

| Tag | Meaning |
|-----|---------|
| `Villain` | Belongs to the Villain (not a specific Henchman) |

---

## Role

On Hero objects currently in play.

| Tag | Meaning |
|-----|---------|
| `Champion` | Currently Manifested as a player's Champion |
| `Henchman` | Currently Manifested as a Villain's Henchman |

---

## Alignment

On Hero objects, indicates which pile they originate from.

| Tag | Meaning |
|-----|---------|
| `Blessed` | Originates from the Blessed pile. Default Champion candidate. |
| `CursedHero` | Originates from the Cursed pile. Default Henchman candidate. Note: different from the `Cursed` card flag. |

*Why `CursedHero` and not `Cursed`?* The `Cursed` tag on cards means "cannot be exiled." The `CursedHero` tag on heroes means "comes from the Cursed pile." Distinct concepts, so distinct tags.

---

## Status

For UI rendering and ability queries. Status state lives in `HeroState` in Global, not as physical objects, but tags appear on status-related tokens if we introduce any.

| Tag | What it is |
|-----|------------|
| `Toughness` | Damage reduction |
| `Regen` | Heal on surviving damage |
| `Indestructible` | Fatal damage intercept |
| `Agony` | Damage acceleration |
| `Doom` | Kill at Standby |
| `Burn` | Delayed damage at Standby |
| `Silence` | Condemn: Card Play |
| `Condemn` | Suppression mechanic |

---

## Pile

Identifies which physical pile an object is.

| Tag | Meaning |
|-----|---------|
| `BlessedPile` | The Blessed Hero pile |
| `CursedPile` | The Cursed Hero pile |
| `ConjurePool` | The face-up shared Conjure Pool |
| `CalamityDeck` | The active Calamity deck |
| `VillainDeck` | The shared Villain Deck |
| `VillainTomb` | The shared Villain Tomb |

**Pile ownership:** Piles that belong to a player (e.g., Yellow's Deck, Yellow's Pitch) also carry their color tag.

| Example combination | Finds |
|---------------------|-------|
| `{"Deck", "Yellow"}` | Yellow's draw deck |
| `{"Pile", "Pitch", "Yellow"}` | Yellow's Pitch pile |
| `{"Pile", "Tomb", "Yellow"}` | Yellow's Tomb |
| `{"Zone", "Crystal", "Yellow"}` | Yellow's Crystal Zone |

---

## Slot

On slotted cards currently in play.

| Tag | Meaning |
|-----|---------|
| `Equip` | Slotted as an Equip card |
| `Enchant` | Slotted as an Enchant card |
| `Runic` | Slotted as a Runic card |

---

## Tomb

On cards with Tomb abilities.

| Tag | Meaning |
|-----|---------|
| `Forsake` | Has a Forsake effect |
| `Forbid` | Has a Forbid effect |
| `Exhume` | Has an Exhume effect |

---

## Resource

On any UI element or counter that tracks a resource.

| Tag | Meaning |
|-----|---------|
| `Life` | Life total |
| `Mana` | Mana pool |
| `Spirit` | Villain Spirit meter |
| `Presence` | Pillar-generated temporary mana |

---

## Example combinations

Real queries you will run in Lua.

### Find a player's Champion

```lua
getObjectsWithAllTags({"Hero", "Yellow", "Champion"})
```

### Find all Cursed cards currently in a specific hand

```lua
for _, card in ipairs(player.getHandObjects()) do
    if card.hasTag("Cursed") then
        -- handle cursed card
    end
end
```

### Find the Blessed pile

```lua
getObjectsWithAllTags({"Pile", "Hero", "BlessedPile"})[1]
```

### Find all Legendary cards belonging to a specific hero

Legendary cards are identified by name in GMNotes rather than tag, since there are many. Use GMNotes for hero name lookup, tags for type filtering:

```lua
local candidates = getObjectsWithAllTags({"Card", "Legendary"})
for _, card in ipairs(candidates) do
    local notes = JSON.decode(card.getGMNotes())
    if notes.hero == "Akiem" then
        -- found Akiem's legendary
    end
end
```

### Find all objects on the table with a given status

Status objects are not planned as physical objects in v2 (everything is UI). But if we introduce physical status chips later, they would query like:

```lua
getObjectsWithAllTags({"Status", "Burn", "Red"})  -- Red's Burn counter
```

### Find all cards of a specific type across all zones

```lua
getObjectsWithAllTags({"Card", "Brutal", "Reaction"})  -- all Reaction Brutals
```

---

## GMNotes vs Tags: when to use which

**Tags are for categorical queries.** Things you filter by in bulk.

**GMNotes are for unique identifiers and rich data.** Things you look up by key.

| Use Tags for | Use GMNotes for |
|--------------|------------------|
| Card type | Card game_name (`copper_sword`) |
| Subtype | Hero passive reference |
| Ownership color | Slotted card's parent hero |
| Role (Champion/Henchman) | Custom per-card state (Forsake counters) |
| Status name | Link to data block entry |

**Example:** A Legendary card for Akiem carries tags `{"Card", "Brutal", "Normal", "Legendary"}` and GMNotes `{"game_name": "wrath_of_akiem", "hero": "Akiem"}`. The tags let you filter for Legendary Brutal Normals. The GMNotes let you identify exactly which card it is and who it belongs to.

---

## Adding new tags

When you need a new tag:

1. Add it to the appropriate category in this document
2. Update the Python tagger (`src/tts/tagger.py`) to apply it where needed
3. Update `TagRegistry.lua` in Global modules if Lua needs to reference it as a constant
4. Rerun the save patcher on your save file

Never hardcode a string tag in Lua without adding it here first. If the tag lives in more than one place in the codebase, it is drift waiting to happen.

---

## Reserved / deprecated tags

| Tag | Status | Reason |
|-----|--------|--------|
| `Hearts`, `Clubs`, `Diamonds`, `Spades` | Deprecated | Color pairings supersede team tags |
| `Ascended` | Reserved | For future Ascended Hero tracking, not yet implemented |

---

## Tag hygiene rules

1. **Never duplicate.** If an object has `Hero`, do not also give it `HeroCard`. Pick one canonical name and stick with it.
2. **Never conflict.** A card cannot be both `Cursed` (uncontactable) and something that contradicts it. Check your combinations.
3. **Always test the query.** When you add a new tag, query for it in Lua and confirm you find the right objects.
4. **Comment your tag lists.** In code, annotate tag arrays so someone reading it knows why.
