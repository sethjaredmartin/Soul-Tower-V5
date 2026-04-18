# TAGS.md — Soul Tower Tag Vocabulary

This is the single source of truth for every tag used on every TTS object in Soul Tower. Python tags objects using these strings. Lua queries objects using these strings. Scripting zones fire on these strings. Adding a new category means adding it here first.

## Why tags

Every object on the table self-describes through its tag list. Instead of tracking GUIDs in a central map that drifts out of sync, we ask TTS directly: "Give me every object tagged `Hero` and `Yellow`." The result is always current.

Tags are combinable. `getObjectsWithAllTags({"Status", "Burn", "Red"})` returns exactly one thing: the Red Champion's Burn status object, if it exists. Generic queries work the same way. `getObjectsWithAllTags({"Hero", "Cursed"})` returns every Cursed Hero card on the table regardless of where it is.

## Design rules

1. **Tags describe identity, not position.** Do not tag things with `LeftSide` or `TopRow`. A tag should answer "what is this?" not "where does it sit?"
2. **Tags are permanent for their type, temporary for their state.** A Hero card is always tagged `Hero`. An object's color ownership may change during play (a Cursed Hero goes from Villain to Summoner side when Manifested).
3. **Tags never replace data.** Do not encode numbers in tags. `Burn5` is not a tag. `Burn` is the tag, and the stack value lives in state.
4. **One vocabulary for both languages.** Every string in this doc is used verbatim in both Python (tagger) and Lua (queries). Do not alias.
5. **Additive only.** Adding tags to this doc is always fine. Removing or renaming tags requires a sweep through both Python and Lua code.

---

## Object class tags

What is this thing at the most basic level? Every physical object gets exactly one class tag.

| Tag | Description |
|-----|-------------|
| `Hero` | A Hero card (Champion or Henchman roster card) |
| `Card` | A playable card (Brutal, Ritual, or Spell) |
| `Crystal` | A Crystal card in the Crystal Zone |
| `Calamity` | A Calamity card from the Villain's Calamity deck |
| `Villain` | The Villain character object itself |
| `Pile` | A persistent deck that lives on the table (Blessed pile, Cursed pile, Villain Deck) |
| `Deck` | A transient stack of cards (player decks, discard piles) |
| `Tile` | A UI tile (player tile, villain tile, conjure tile) |
| `Token` | A small marker object (Order/Crush/Pray tokens if used, Crystal Token) |
| `Note` | A note card used as UI surface (history log) |

Example:
```lua
-- Find every Hero card on the table
getObjectsWithAllTags({"Hero"})
```

---

## Card type tags

Every `Card` or `Crystal` carries exactly one of these.

| Tag | Description |
|-----|-------------|
| `Brutal` | Attack-oriented card type |
| `Ritual` | Healing-oriented card type |
| `Spell` | Mana/utility-oriented card type |

---

## Subtype tags

Every `Card` carries exactly one subtype tag.

| Tag | Description |
|-----|-------------|
| `Normal` | Your turn only |
| `Instant` | Any time, Spell only |
| `Entropy` | Any time, Ritual only, Foe pays cost |
| `Reaction` | Only when trigger is active, Brutal only |

---

## Card attribute tags

Additive flags on a card. A card can have zero, one, or several.

| Tag | Description |
|-----|-------------|
| `Legendary` | Belongs to a specific Hero, added when Hero is Manifested |
| `Cursed` | Cannot be exiled, triggers Pain instead |
| `Default` | Villain will not play from hand, used for Default block behavior |
| `Inspire` | Card has an Inspire cost option |
| `Starter` | Part of a starting card set (Journey, Crystals) |

---

## Tomb ability tags

Cards that interact with the Tomb carry these.

| Tag | Description |
|-----|-------------|
| `Forsake` | Has a Forsake effect, enters Tomb on first resolve |
| `Forbid` | Has a Forbid effect, locked in Tomb until Exhumed |
| `Exhume` | Has an Exhume effect |

---

## Slot ability tags

Cards that slot onto a Hero carry these.

| Tag | Description |
|-----|-------------|
| `Equip` | Slots permanently until Hero defeated |
| `Enchant` | Slots temporarily, falls off at Standby |
| `Runic` | Slots and modifies base stats |

---

## Ownership tags

Who does this object belong to? Every object that is currently in play on a specific side gets exactly one ownership tag.

| Tag | Description |
|-----|-------------|
| `Yellow` | Yellow Champion / Summoner |
| `Red` | Red Champion / Summoner |
| `Pink` | Pink Champion / Summoner |
| `Orange` | Orange Champion / Summoner |
| `Green` | Green Henchman |
| `Teal` | Teal Henchman |
| `Blue` | Blue Henchman |
| `Purple` | Purple Henchman |
| `White` | The Villain |

### The color pairing

Champion to Henchman pairings are fixed. This lets any module resolve "who is my Foe?" without a lookup table.

| Champion | Henchman |
|----------|----------|
| Yellow | Green |
| Red | Teal |
| Pink | Blue |
| Orange | Purple |

---

## Pile tags

Identifies specific piles on the table. A pile object has both `Pile` (class) and one of these.

| Tag | Description |
|-----|-------------|
| `BlessedPile` | The shared Blessed Hero pile |
| `CursedPile` | The shared Cursed Hero pile |
| `ConjurePool` | The active face-up Conjure Pool |
| `VillainDeck` | The shared Villain card pool |
| `VillainTomb` | The shared Villain Tomb pool |
| `CalamityDeck` | The Villain's Calamity deck |

Example:
```lua
-- Find the Cursed pile
local cursed_pile = getObjectsWithAllTags({"Pile", "CursedPile"})[1]
```

---

## Zone tags

Identifies specific play zones on a player tile. A scripting zone has `Zone` (class is omitted on zones, they always have `Zone`) plus its slot name plus its color.

| Tag | Description |
|-----|-------------|
| `Zone` | Any scripting zone on a tile |
| `ChampionSlot` | Where the Champion lives |
| `HenchmanSlot` | Where the Henchman lives |
| `EquipSlot` | Equip slot on the Hero |
| `EnchantSlot` | Enchant slot on the Hero |
| `RunicSlot` | Runic slot on the Hero |
| `CrystalZone` | The Crystal Zone |
| `HandZone` | The player's hand area (if scripted) |
| `PlayZone` | Where cards get played and resolved |

Example:
```lua
-- Find Yellow's Equip zone
local zone = getObjectsWithAllTags({"Zone", "EquipSlot", "Yellow"})[1]
```

---

## Tile tags

Identifies which tile is which. A tile has `Tile` (class) plus exactly one of these.

| Tag | Description |
|-----|-------------|
| `PlayerTile` | A player's UI tile (one per color) |
| `VillainTile` | The Villain's UI tile |
| `ConjureTile` | The Conjure Pool UI tile |

---

## Status tags (deprecated for physical objects)

Following your decision to eliminate counter objects entirely, status stacks now live in `HeroState` memory and render as UI pips. These tags are reserved for future use if you ever bring physical counters back.

| Tag | Status name |
|-----|-------------|
| `Status` | Any status counter object |
| `Toughness` | |
| `Regen` | |
| `Indestructible` | |
| `Agony` | |
| `Doom` | |
| `Burn` | |
| `Silence` | |

---

## Origin tags

Tags cards and heroes by their narrative origin. Useful for filtering and analytics.

The current set is driven by the spreadsheet's Origin column. Current origins include `Imanis` and others from your design. This doc should be updated as origins are added or renamed.

---

## Common tag combinations

Quick reference for the queries you will write most often.

| Goal | Tag combination |
|------|-----------------|
| Yellow's Champion | `{"Hero", "Yellow"}` |
| All Cursed cards in play | `{"Card", "Cursed"}` |
| Red's Equip slot zone | `{"Zone", "EquipSlot", "Red"}` |
| Any Legendary for Akiem | `{"Card", "Legendary", "akiem"}` — uses Game Name as tag |
| The Cursed pile | `{"Pile", "CursedPile"}` |
| Every Henchman Hero card | `{"Hero", "Green"}`, `{"Hero", "Teal"}`, etc |
| All Reaction cards | `{"Card", "Reaction"}` |
| All cards with Forsake | `{"Card", "Forsake"}` |

---

## Game Name as a tag

A card's `Game Name` (snake_case identifier from the spreadsheet, e.g. `wrath_of_akiem`) is also used as a tag. This lets a Hero's Legendary cards find themselves:

```lua
-- Fetch Akiem's Legendary cards from wherever they are
local akiem_cards = getObjectsWithAllTags({"Card", "Legendary", "akiem"})
```

Python tags cards with their Game Name automatically during patching.

---

## Tag inheritance for piles

When a card lives in a pile, it still carries its own tags. The pile is tagged with pile-level tags (`Pile`, `BlessedPile`), and the cards inside carry their individual tags (`Hero`, `Blessed`, or `Card`, `Legendary`, `akiem`).

This means queries that find cards will find them whether they are loose on the table or nested inside a deck. TTS `getObjectsWithAllTags` traverses into container objects automatically for this purpose on recent versions.

If you need to specifically query the top level of piles only, use `getAllObjects` and filter by tags yourself.

---

## Adding a new tag

1. Add the tag to this doc under the right section
2. Add it to the Python tagger in `src/tts/tagger.py`
3. If Lua modules need to reference it, add it to `TagRegistry.lua` as a constant
4. Update any relevant docs (CLAUDE.md, Rules_Formal) if it reflects a new game concept

If it is a narrative tag (new Origin, new Hero Game Name), steps 2 and 3 are often automatic because the tagger reads directly from the spreadsheet.

---

## Adding a new ownership color

If you ever need a fifth or sixth player slot:

1. Add the Champion color tag
2. Add the paired Henchman color tag
3. Add the row to the pairing table above
4. Update `CHAMPION_COLORS` and `HENCHMAN_COLORS` in `config.py`

The rest of the system reads from those lists, so the change propagates.
