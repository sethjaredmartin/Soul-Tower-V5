-- ============================================================
-- CommonCards.lua
-- Lookup module for the Common Cards data block.
-- Data is inlined at build time via the bundler — no TTS object needed.
--
-- Usage:
--   local CommonCards = require("CommonCards")
--   local card = CommonCards.lookup("Brutal Hex")
--   if card then
--       print(card.Type, card.Cost)
--   end
--
-- Fields returned (named keys, Beta format):
--   Origin, Type, Subtype, Cost, FlavorText, Cursed, VillainDefault
-- ============================================================

local _giveInfo = require("common_cards_data_block")

local CommonCards = {}

function CommonCards.lookup(card_name)
    return _giveInfo(card_name)
end

return CommonCards
