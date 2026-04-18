import { useState, useEffect, useCallback, useRef } from "react";

// ═══════════════════════════════════════════════════════════════
// SOUL TOWER — Browser Prototype
// A standalone game viewer + card rendering engine
// No server required. All data is local.
// ═══════════════════════════════════════════════════════════════

// ── Game Data (shaped like Google Sheets export) ──────────────

const HEROES = {
  akiem: {
    name: "Akiem",
    alignment: "Blessed",
    health: 5, might: 4, speed: 6, luck: 3, arcana: 4,
    passive: "Whenever you Order #, Foe Set Agony Order #",
    legendary1: "wrath_of_akiem",
    legendary2: "akiems_resolve",
  },
  dodan: {
    name: "Dodan",
    alignment: "Blessed",
    health: 4, might: 3, speed: 5, luck: 4, arcana: 6,
    passive: "Your Cards with Equip cost -1. Whenever You Slot a Card, Deal 1d4 Hero",
    legendary1: "devils_forge",
    legendary2: "dodans_anvil",
  },
  vyra: {
    name: "Vyra",
    alignment: "Cursed",
    health: 6, might: 5, speed: 3, luck: 5, arcana: 3,
    passive: "Whenever You Pray #, Drain Prayed",
    legendary1: "vyras_embrace",
    legendary2: "blood_communion",
  },
  kael: {
    name: "Kael",
    alignment: "Cursed",
    health: 3, might: 6, speed: 7, luck: 2, arcana: 4,
    passive: "Your Spells Deal +2. Whenever Crush #, Set Agony Crush #",
    legendary1: "kaels_fury",
    legendary2: "void_strike",
  },
};

const CARDS = {
  skull_crack: {
    name: "Skull Crack", type: "Brutal", subtype: "Normal", cost: 3,
    effects: ["Deal 5 Hero", "Bolster: Draw 1"],
    cursed: false, default: false,
  },
  arcane_lance: {
    name: "Arcane Lance", type: "Spell", subtype: "Instant", cost: 2,
    effects: ["Deal 3 Hero", "Mercy: You Gain 1 Mana"],
    cursed: false, default: false,
  },
  crimson_pact: {
    name: "Crimson Pact", type: "Ritual", subtype: "Entropy", cost: 4,
    effects: ["Blood Price 3: Deal 6 Hero", "Rally: Fortune 3"],
    cursed: true, default: false,
  },
  iron_ward: {
    name: "Iron Ward", type: "Brutal", subtype: "Reaction", cost: 2,
    trigger: "Reaction-You Defend",
    effects: ["Your Hero Set Toughness 3", "Ferocity 4: Deal 2 Foe"],
    cursed: false, default: false,
  },
  soul_harvest: {
    name: "Soul Harvest", type: "Spell", subtype: "Normal", cost: 5,
    effects: ["Deal 4 Hero", "Upcast 3: Deal 4 Hero", "Drain 2 Foe"],
    cursed: false, default: false,
  },
  healing_light: {
    name: "Healing Light", type: "Ritual", subtype: "Normal", cost: 2,
    effects: ["Heal 5 Hero", "Bolster: Your Hero Boost Health 1"],
    cursed: false, default: false,
  },
  void_bolt: {
    name: "Void Bolt", type: "Spell", subtype: "Normal", cost: 3,
    effects: ["Deal 3 Hero", "Threshold 2: Foe Set Burn 1"],
    cursed: false, default: false,
  },
  shadow_step: {
    name: "Shadow Step", type: "Brutal", subtype: "Normal", cost: 1,
    effects: ["Command Your Hero", "Bolster: Draw 1"],
    cursed: false, default: false,
  },
  sword_of_fortune: {
    name: "Sword of Fortune", type: "Brutal", subtype: "Normal", cost: 3,
    effects: ["Profit: Deal 3 Hero", "Equip: Nothing", "Charge 2: Fortune 1", "Catalyst:Brutal: You Lose 1 Life"],
    cursed: false, default: false,
  },
  dark_ritual: {
    name: "Dark Ritual", type: "Ritual", subtype: "Normal", cost: 4,
    effects: ["Heal 3 Hero", "Attune 2", "Embalm: Draw 2"],
    cursed: false, default: false,
  },
};

const CRYSTALS = {
  arcane_lance_crystal: { name: "Arcane Lance", type: "Spell", cost: 0, effects: ["Deal 4 Hero"] },
  burn_the_wicked: { name: "Burn the Wicked", type: "Spell", cost: 0, effects: ["Foe Set Burn 1", "Embalm: Attune 2", "Exhume 4"] },
  glimpse_of_salvation: { name: "Glimpse of Salvation", type: "Ritual", cost: 0, effects: ["Profit: Draw 1", "Heal 3 Hero"] },
  soul_crystal: { name: "Soul Crystal", type: "Spell", cost: 0, effects: ["Conjure a Hero"] },
  cheat_death: { name: "Cheat Death", type: "Brutal", cost: 0, effects: ["Deny 11", "Ferocity 3: Your Hero Set Indestructible 1"] },
  shield_bash: { name: "Shield Bash", type: "Brutal", cost: 0, effects: ["Deal 4 Foe", "Upcast 2: Your Hero Set Toughness 3"] },
};

// ── Color System ──────────────────────────────────────────────

const COLORS = {
  bg: "#0d0f14",
  surface: "#161920",
  surfaceHover: "#1c2029",
  border: "#2a2e3a",
  borderLight: "#3a3f4d",
  text: "#e8e6e1",
  textMuted: "#8a8d96",
  brutal: { primary: "#c44040", bg: "#2a1515", border: "#6b2222", text: "#f0a0a0" },
  ritual: { primary: "#3da556", bg: "#152a18", border: "#226b2e", text: "#a0f0b0" },
  spell:  { primary: "#4a7bc4", bg: "#151d2a", border: "#22446b", text: "#a0c0f0" },
  crystal: { primary: "#9b6fd4", bg: "#1f152a", border: "#5b3d8b", text: "#c8a0f0" },
  status: {
    toughness: "#6b8ccc", regen: "#5cb85c", indestructible: "#f0c040",
    agony: "#cc4444", doom: "#880088", burn: "#e06020",
    silence: "#888888", condemn: "#666666",
  },
  stat: {
    health: "#e05050", might: "#e09030", speed: "#50c0e0",
    luck: "#e0d050", arcana: "#b060e0",
  },
  modified: "#ffcc00",
};

const TYPE_COLORS = { Brutal: COLORS.brutal, Ritual: COLORS.ritual, Spell: COLORS.spell };

// ── Game State Engine ─────────────────────────────────────────

function createInitialState() {
  return {
    turn: 1,
    phase: "wake_up",
    summoner: {
      life: 30, mana: 4, pillar: 0, presence: 0, pain: 1,
      champion: null,
      hand: [],
      deck: [],
      pitch: [],
      crystalToken: true, orderToken: true, crushToken: true, prayToken: true,
    },
    villain: {
      life: 60, mana: 0, spirit: 0, pillar: 0, presence: 0,
      henchman: null,
      hand: [],
    },
    championState: null,
    henchmanState: null,
    log: [],
  };
}

function createHeroState(heroKey) {
  const hero = HEROES[heroKey];
  if (!hero) return null;
  return {
    key: heroKey,
    name: hero.name,
    baseStats: { health: hero.health, might: hero.might, speed: hero.speed, luck: hero.luck, arcana: hero.arcana },
    activeStats: { health: hero.health, might: hero.might, speed: hero.speed, luck: hero.luck, arcana: hero.arcana },
    hp: hero.health * 3,
    maxHp: hero.health * 3,
    power: hero.might,
    energy: hero.speed,
    initiative: 0,
    favor: 0,
    sorcery: [],
    statuses: { toughness: 0, regen: 0, indestructible: 0, agony: 0, doom: 0, burn: 0 },
    boostPending: { health: 0, might: 0, speed: 0, luck: 0, arcana: 0 },
    weakenPending: { health: 0, might: 0, speed: 0, luck: 0, arcana: 0 },
    equip: null, runic: null, enchant: null,
    passive: hero.passive,
  };
}

function rollDie(sides) {
  return Math.floor(Math.random() * sides) + 1;
}

function rollLuck(luck) {
  let favor = 0;
  let current = luck;
  while (current > 0) {
    const roll = rollDie(6);
    if (roll <= current) { favor++; current -= 2; }
    else break;
  }
  return favor;
}

function rollSpeed(speed) {
  let initiative = 0;
  let current = speed;
  while (current > 0) {
    initiative += rollDie(current);
    current -= 2;
  }
  return initiative;
}

function rollArcana(arcana) {
  const tokens = [];
  let current = arcana;
  let chance = 0;
  while (current > 0) {
    const roll = rollDie(4);
    if ((roll - chance) <= 2) {
      tokens.push(current);
      current -= 2;
    } else {
      current -= 2;
      chance++;
    }
  }
  return tokens;
}

// ── Card Text Modifier Engine ─────────────────────────────────
// This is the Legends of Runeterra pattern: hero passives modify
// what the card text DISPLAYS, not just what it does at runtime.

function applyPassiveModifiers(effects, heroState) {
  if (!heroState) return effects.map(e => ({ text: e, modified: false }));

  const passive = HEROES[heroState.key]?.passive || "";
  const modified = [];

  for (const effect of effects) {
    let text = effect;
    let isModified = false;

    // "Your Spells Deal +N" pattern
    const spellDealMatch = passive.match(/Your Spells Deal \+(\d+)/);
    if (spellDealMatch) {
      const bonus = parseInt(spellDealMatch[1]);
      text = text.replace(/Deal (\d+)/g, (match, num) => {
        isModified = true;
        return `Deal ${parseInt(num) + bonus}`;
      });
    }

    // "Your Cards with Equip cost -N" pattern
    const equipCostMatch = passive.match(/Your Cards with Equip cost -(\d+)/);
    if (equipCostMatch && text.includes("Equip")) {
      isModified = true;
    }

    modified.push({ text, modified: isModified, original: effect });
  }

  return modified;
}

function getModifiedCost(card, heroState) {
  if (!heroState) return { cost: card.cost, modified: false };
  const passive = HEROES[heroState.key]?.passive || "";

  const equipCostMatch = passive.match(/Your Cards with Equip cost -(\d+)/);
  if (equipCostMatch && card.effects?.some(e => e.includes("Equip"))) {
    const reduction = parseInt(equipCostMatch[1]);
    return { cost: Math.max(0, card.cost - reduction), modified: true };
  }

  return { cost: card.cost, modified: false };
}

// ── Components ────────────────────────────────────────────────

function StatBar({ label, value, max = 9, color, modified = false }) {
  const pips = [];
  for (let i = 0; i < max; i++) {
    pips.push(
      <div key={i} style={{
        width: 8, height: 16, borderRadius: 2,
        background: i < value ? color : "#1a1d25",
        border: `1px solid ${i < value ? color : "#2a2e3a"}`,
        opacity: i < value ? 1 : 0.3,
        transition: "all 0.3s ease",
      }}/>
    );
  }
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
      <span style={{
        fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
        color: modified ? COLORS.modified : COLORS.textMuted,
        width: 50, textTransform: "uppercase", letterSpacing: 1,
        fontWeight: modified ? 700 : 400,
      }}>{label}</span>
      <div style={{ display: "flex", gap: 2 }}>{pips}</div>
      <span style={{
        fontSize: 13, fontFamily: "'JetBrains Mono', monospace",
        color: modified ? COLORS.modified : color,
        fontWeight: 700, marginLeft: 4,
      }}>{value}</span>
    </div>
  );
}

function StatusBadge({ name, stacks }) {
  if (stacks <= 0) return null;
  const color = COLORS.status[name.toLowerCase()] || "#888";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 4,
      background: color + "22", border: `1px solid ${color}55`,
      fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
      color: color, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5,
    }}>
      {name} {stacks}
    </span>
  );
}

function CardComponent({ cardData, heroState, isInHand = false, onPlay, small = false }) {
  const [hovered, setHovered] = useState(false);
  const typeColor = TYPE_COLORS[cardData.type] || COLORS.spell;
  const modifiedEffects = applyPassiveModifiers(cardData.effects || [], heroState);
  const { cost: displayCost, modified: costModified } = getModifiedCost(cardData, heroState);

  const scale = small ? 0.75 : 1;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onPlay}
      style={{
        width: 180 * scale, minHeight: 240 * scale,
        background: typeColor.bg,
        border: `2px solid ${hovered ? typeColor.primary : typeColor.border}`,
        borderRadius: 10,
        padding: 10 * scale,
        cursor: onPlay ? "pointer" : "default",
        transition: "all 0.2s ease",
        transform: hovered && isInHand ? "translateY(-12px) scale(1.05)" : "none",
        boxShadow: hovered ? `0 8px 24px ${typeColor.primary}33` : "0 2px 8px #00000044",
        display: "flex", flexDirection: "column", gap: 6 * scale,
        position: "relative",
        flexShrink: 0,
      }}
    >
      {/* Cost badge */}
      <div style={{
        position: "absolute", top: -6, left: -6,
        width: 28 * scale, height: 28 * scale, borderRadius: "50%",
        background: costModified ? COLORS.modified : typeColor.primary,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14 * scale, fontWeight: 800, color: "#fff",
        fontFamily: "'JetBrains Mono', monospace",
        border: `2px solid ${COLORS.bg}`,
        boxShadow: costModified ? `0 0 8px ${COLORS.modified}66` : "none",
      }}>
        {displayCost}
      </div>

      {/* Cursed indicator */}
      {cardData.cursed && (
        <div style={{
          position: "absolute", top: -6, right: -6,
          padding: "1px 6px", borderRadius: 4,
          background: "#440022", border: "1px solid #880044",
          fontSize: 9 * scale, color: "#ff6699", fontWeight: 700,
          textTransform: "uppercase", letterSpacing: 1,
        }}>Cursed</div>
      )}

      {/* Name */}
      <div style={{
        fontSize: 13 * scale, fontWeight: 700,
        color: COLORS.text,
        fontFamily: "'Crimson Pro', Georgia, serif",
        marginTop: 8 * scale, lineHeight: 1.2,
      }}>{cardData.name}</div>

      {/* Type + Subtype */}
      <div style={{
        display: "flex", gap: 6, alignItems: "center",
        fontSize: 10 * scale, color: typeColor.text,
        fontFamily: "'JetBrains Mono', monospace",
        textTransform: "uppercase", letterSpacing: 1,
      }}>
        <span>{cardData.type}</span>
        <span style={{ opacity: 0.4 }}>|</span>
        <span>{cardData.subtype || "Crystal"}</span>
      </div>

      {/* Trigger */}
      {cardData.trigger && (
        <div style={{
          padding: "3px 8px", borderRadius: 4,
          background: "#331a1a", border: "1px solid #663333",
          fontSize: 10 * scale, color: "#ff8888",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {cardData.trigger}
        </div>
      )}

      {/* Effects */}
      <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 4 * scale }}>
        {modifiedEffects.map((eff, i) => (
          <div key={i} style={{
            fontSize: 11 * scale, lineHeight: 1.4,
            color: eff.modified ? COLORS.modified : COLORS.text,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontWeight: eff.modified ? 600 : 400,
            padding: "2px 6px",
            background: eff.modified ? `${COLORS.modified}11` : "transparent",
            borderRadius: 3,
            borderLeft: eff.modified ? `2px solid ${COLORS.modified}` : "2px solid transparent",
          }}>
            {eff.text}
            {eff.modified && <span style={{ fontSize: 9, marginLeft: 4, opacity: 0.5 }}>({eff.original})</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function HeroPanel({ heroState, role, passiveText }) {
  if (!heroState) {
    return (
      <div style={{
        background: COLORS.surface, border: `2px dashed ${COLORS.border}`,
        borderRadius: 12, padding: 20, textAlign: "center",
        color: COLORS.textMuted, fontFamily: "'JetBrains Mono', monospace",
        fontSize: 13,
      }}>
        No {role} manifested
      </div>
    );
  }

  const hero = HEROES[heroState.key];
  const hpPercent = Math.max(0, heroState.hp / heroState.maxHp);
  const hpColor = hpPercent > 0.6 ? "#5cb85c" : hpPercent > 0.3 ? "#e0a030" : "#cc4444";

  const activeStatuses = Object.entries(heroState.statuses).filter(([_, v]) => v > 0);

  return (
    <div style={{
      background: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 12, padding: 16,
      display: "flex", flexDirection: "column", gap: 10,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{
            fontSize: 18, fontWeight: 700, color: COLORS.text,
            fontFamily: "'Crimson Pro', Georgia, serif",
          }}>{heroState.name}</div>
          <div style={{
            fontSize: 11, color: COLORS.textMuted,
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: "uppercase", letterSpacing: 1,
          }}>
            {role} · {hero.alignment}
          </div>
        </div>
        <div style={{
          fontSize: 11, color: COLORS.textMuted,
          fontFamily: "'JetBrains Mono', monospace",
          textAlign: "right",
        }}>
          <div>PWR <span style={{ color: COLORS.stat.might, fontWeight: 700 }}>{heroState.power}</span></div>
          <div>NRG <span style={{ color: COLORS.stat.speed, fontWeight: 700 }}>{heroState.energy}</span></div>
          <div>INIT <span style={{ color: "#fff", fontWeight: 700 }}>{heroState.initiative}</span></div>
        </div>
      </div>

      {/* HP Bar */}
      <div>
        <div style={{
          display: "flex", justifyContent: "space-between", marginBottom: 3,
          fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
        }}>
          <span style={{ color: COLORS.textMuted }}>HP</span>
          <span style={{ color: hpColor, fontWeight: 700 }}>{heroState.hp}/{heroState.maxHp}</span>
        </div>
        <div style={{
          height: 8, background: "#1a1d25", borderRadius: 4,
          overflow: "hidden", border: "1px solid #2a2e3a",
        }}>
          <div style={{
            height: "100%", width: `${hpPercent * 100}%`,
            background: `linear-gradient(90deg, ${hpColor}, ${hpColor}cc)`,
            borderRadius: 4, transition: "width 0.5s ease",
          }}/>
        </div>
      </div>

      {/* Stats */}
      <div>
        <StatBar label="HLT" value={heroState.activeStats.health} color={COLORS.stat.health}
                 modified={heroState.activeStats.health !== heroState.baseStats.health} />
        <StatBar label="MGT" value={heroState.activeStats.might} color={COLORS.stat.might}
                 modified={heroState.activeStats.might !== heroState.baseStats.might} />
        <StatBar label="SPD" value={heroState.activeStats.speed} color={COLORS.stat.speed}
                 modified={heroState.activeStats.speed !== heroState.baseStats.speed} />
        <StatBar label="LCK" value={heroState.activeStats.luck} color={COLORS.stat.luck}
                 modified={heroState.activeStats.luck !== heroState.baseStats.luck} />
        <StatBar label="ARC" value={heroState.activeStats.arcana} color={COLORS.stat.arcana}
                 modified={heroState.activeStats.arcana !== heroState.baseStats.arcana} />
      </div>

      {/* Statuses */}
      {activeStatuses.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {activeStatuses.map(([name, stacks]) => (
            <StatusBadge key={name} name={name} stacks={stacks} />
          ))}
        </div>
      )}

      {/* Sorcery Tokens */}
      {heroState.sorcery.length > 0 && (
        <div style={{
          display: "flex", gap: 4, flexWrap: "wrap",
        }}>
          {heroState.sorcery.map((val, i) => (
            <span key={i} style={{
              padding: "2px 8px", borderRadius: 4,
              background: COLORS.stat.arcana + "22",
              border: `1px solid ${COLORS.stat.arcana}44`,
              fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
              color: COLORS.stat.arcana, fontWeight: 600,
            }}>S{val}</span>
          ))}
        </div>
      )}

      {/* Passive */}
      <div style={{
        padding: "8px 10px", borderRadius: 6,
        background: "#0d0e12", border: "1px solid #2a2e3a",
        fontSize: 11, color: COLORS.textMuted, lineHeight: 1.5,
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontStyle: "italic",
      }}>
        {passiveText || hero.passive}
      </div>
    </div>
  );
}

function ResourceBar({ label, value, max, color, icon }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "6px 10px", borderRadius: 6,
      background: color + "11", border: `1px solid ${color}33`,
    }}>
      <span style={{ fontSize: 16 }}>{icon}</span>
      <span style={{
        fontSize: 11, color: COLORS.textMuted, fontFamily: "'JetBrains Mono', monospace",
        textTransform: "uppercase", letterSpacing: 1, width: 60,
      }}>{label}</span>
      <span style={{
        fontSize: 18, fontWeight: 800, color,
        fontFamily: "'JetBrains Mono', monospace",
      }}>{value}</span>
      {max && <span style={{ fontSize: 11, color: COLORS.textMuted }}>/ {max}</span>}
    </div>
  );
}

function TokenIndicator({ name, available }) {
  return (
    <div style={{
      padding: "4px 10px", borderRadius: 6,
      background: available ? "#1a2a1a" : "#1a1a1a",
      border: `1px solid ${available ? "#3a6b3a" : "#2a2a2a"}`,
      fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
      color: available ? "#5cb85c" : "#555",
      textTransform: "uppercase", letterSpacing: 1, fontWeight: 600,
    }}>
      {available ? "●" : "○"} {name}
    </div>
  );
}

function GameLog({ entries }) {
  const logRef = useRef(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [entries]);

  return (
    <div ref={logRef} style={{
      background: "#0a0b0e", border: `1px solid ${COLORS.border}`,
      borderRadius: 8, padding: 10, height: 200, overflowY: "auto",
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
    }}>
      {entries.map((entry, i) => (
        <div key={i} style={{
          padding: "3px 0", borderBottom: "1px solid #1a1d25",
          color: entry.type === "damage" ? "#cc4444" :
                 entry.type === "heal" ? "#5cb85c" :
                 entry.type === "mana" ? "#4a7bc4" :
                 entry.type === "status" ? "#e0a030" :
                 entry.type === "phase" ? "#9b6fd4" :
                 COLORS.textMuted,
        }}>
          <span style={{ color: "#555", marginRight: 6 }}>T{entry.turn || 1}</span>
          {entry.text}
        </div>
      ))}
      {entries.length === 0 && (
        <div style={{ color: "#333", fontStyle: "italic" }}>Awaiting game events...</div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────

export default function SoulTower() {
  const [gameState, setGameState] = useState(createInitialState());
  const [selectedHero, setSelectedHero] = useState(null);
  const [showHeroSelect, setShowHeroSelect] = useState(true);

  const log = useCallback((text, type = "info") => {
    setGameState(prev => ({
      ...prev,
      log: [...prev.log, { text, type, turn: prev.turn, time: Date.now() }],
    }));
  }, []);

  const manifestChampion = useCallback((heroKey) => {
    const heroState = createHeroState(heroKey);
    if (!heroState) return;

    setGameState(prev => ({
      ...prev,
      summoner: { ...prev.summoner, champion: heroKey },
      championState: heroState,
    }));

    // Deal sample hand
    const sampleHand = Object.keys(CARDS).slice(0, 6);
    setGameState(prev => ({
      ...prev,
      summoner: { ...prev.summoner, hand: sampleHand, champion: heroKey },
    }));

    log(`${heroState.name} manifested as Champion`, "phase");
    setShowHeroSelect(false);
  }, [log]);

  const manifestHenchman = useCallback((heroKey) => {
    const heroState = createHeroState(heroKey);
    if (!heroState) return;

    setGameState(prev => ({
      ...prev,
      villain: { ...prev.villain, henchman: heroKey },
      henchmanState: heroState,
    }));

    log(`${heroState.name} manifested as Henchman`, "phase");
  }, [log]);

  const runWakeUp = useCallback(() => {
    if (!gameState.championState) return;

    const cs = { ...gameState.championState };
    cs.power = cs.activeStats.might;
    cs.energy = cs.activeStats.speed;
    cs.initiative = rollSpeed(cs.activeStats.speed);
    cs.favor = rollLuck(cs.activeStats.luck);
    cs.sorcery = rollArcana(cs.activeStats.arcana);
    if (cs.sorcery.length === 0 || !cs.sorcery.some(t => t >= 1)) {
      cs.sorcery = [1, ...cs.sorcery];
    }

    let henchInit = 0;
    const hs = gameState.henchmanState ? { ...gameState.henchmanState } : null;
    if (hs) {
      hs.power = hs.activeStats.might;
      hs.energy = hs.activeStats.speed;
      hs.initiative = rollSpeed(hs.activeStats.speed);
      hs.favor = rollLuck(hs.activeStats.luck);
      hs.sorcery = [hs.activeStats.arcana];
      henchInit = hs.initiative;
    }

    setGameState(prev => ({
      ...prev,
      phase: "active",
      championState: cs,
      henchmanState: hs,
      summoner: {
        ...prev.summoner,
        crystalToken: true, orderToken: true, crushToken: true, prayToken: true,
        presence: prev.summoner.pillar,
      },
    }));

    log(`Wake Up: Turn ${gameState.turn}`, "phase");
    log(`Power ${cs.power}, Energy ${cs.energy}, Initiative ${cs.initiative}`, "info");
    log(`Favor ${cs.favor} (draw ${3 + cs.favor} cards)`, "info");
    log(`Sorcery: [${cs.sorcery.join(", ")}]`, "mana");
    if (hs) {
      log(`Henchman Initiative: ${henchInit}`, "info");
      log(cs.initiative >= henchInit ? "Champion goes first" : "Henchman goes first", "phase");
    }
  }, [gameState, log]);

  const dealDamage = useCallback((target, amount) => {
    if (target === "champion" && gameState.championState) {
      const cs = { ...gameState.championState };
      let dmg = amount;
      if (cs.statuses.toughness > 0) {
        dmg = Math.max(0, dmg - cs.statuses.toughness);
        cs.statuses = { ...cs.statuses, toughness: cs.statuses.toughness - 1 };
        log(`Toughness absorbs ${amount - dmg} damage`, "status");
      }
      cs.hp -= dmg;
      if (cs.statuses.agony > 0) {
        cs.hp -= 1;
        cs.statuses = { ...cs.statuses, agony: cs.statuses.agony - 1 };
        log(`Agony ticks for 1`, "damage");
      }
      if (cs.statuses.regen > 0 && cs.hp > 0) {
        const regenHeal = rollDie(cs.statuses.regen);
        if (cs.statuses.agony <= 0) {
          cs.hp = Math.min(cs.maxHp, cs.hp + regenHeal);
          log(`Regen heals ${regenHeal}`, "heal");
        } else {
          log(`Regen suppressed by Agony`, "status");
        }
        cs.statuses = { ...cs.statuses, regen: cs.statuses.regen - 1 };
      }
      if (cs.hp <= 0 && cs.statuses.indestructible > 0) {
        cs.hp = 1;
        cs.statuses = { ...cs.statuses, indestructible: cs.statuses.indestructible - 1 };
        log(`Indestructible saves! HP set to 1`, "status");
        if (cs.statuses.agony > 0) {
          cs.hp -= 1;
          cs.statuses = { ...cs.statuses, agony: cs.statuses.agony - 1 };
          log(`Agony ticks after Indestructible save!`, "damage");
        }
      }
      log(`Champion takes ${dmg} damage (${cs.hp} HP remaining)`, "damage");
      if (cs.hp <= 0) log(`${cs.name} has been DEFEATED`, "damage");
      setGameState(prev => ({ ...prev, championState: cs }));
    }
  }, [gameState, log]);

  const setStatus = useCallback((target, status, stacks) => {
    if (target === "champion" && gameState.championState) {
      const cs = { ...gameState.championState };
      cs.statuses = { ...cs.statuses, [status]: (cs.statuses[status] || 0) + stacks };
      setGameState(prev => ({ ...prev, championState: cs }));
      log(`Champion: Set ${status} ${stacks}`, "status");
    }
    if (target === "henchman" && gameState.henchmanState) {
      const hs = { ...gameState.henchmanState };
      hs.statuses = { ...hs.statuses, [status]: (hs.statuses[status] || 0) + stacks };
      setGameState(prev => ({ ...prev, henchmanState: hs }));
      log(`Henchman: Set ${status} ${stacks}`, "status");
    }
  }, [gameState, log]);

  // ── Render ────────────────────────────────────────────────

  return (
    <div style={{
      background: COLORS.bg, color: COLORS.text, minHeight: "100vh",
      fontFamily: "'Crimson Pro', Georgia, serif",
      padding: 20,
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        textAlign: "center", marginBottom: 24, paddingBottom: 16,
        borderBottom: `1px solid ${COLORS.border}`,
      }}>
        <h1 style={{
          fontSize: 28, fontWeight: 800, margin: 0,
          background: "linear-gradient(135deg, #9b6fd4, #4a7bc4, #3da556)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          letterSpacing: 2,
        }}>SOUL TOWER</h1>
        <div style={{
          fontSize: 11, color: COLORS.textMuted,
          fontFamily: "'JetBrains Mono', monospace",
          textTransform: "uppercase", letterSpacing: 2, marginTop: 4,
        }}>
          Turn {gameState.turn} · {gameState.phase.replace("_", " ")}
        </div>
      </div>

      {/* Hero Selection Modal */}
      {showHeroSelect && (
        <div style={{
          background: COLORS.surface, border: `1px solid ${COLORS.border}`,
          borderRadius: 12, padding: 20, marginBottom: 20, maxWidth: 700, margin: "0 auto 20px",
        }}>
          <div style={{
            fontSize: 16, fontWeight: 700, marginBottom: 12, textAlign: "center",
          }}>Manifest your Champion</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
            {Object.entries(HEROES).map(([key, hero]) => (
              <div key={key} onClick={() => {
                manifestChampion(key);
                const cursedHeroes = Object.entries(HEROES).filter(([_, h]) => h.alignment === "Cursed" && key !== _);
                if (cursedHeroes.length > 0) {
                  const randomHench = cursedHeroes[Math.floor(Math.random() * cursedHeroes.length)];
                  manifestHenchman(randomHench[0]);
                }
              }} style={{
                background: hero.alignment === "Blessed" ? "#1a2a1a" : "#2a1a1a",
                border: `2px solid ${hero.alignment === "Blessed" ? "#3a6b3a" : "#6b3a3a"}`,
                borderRadius: 10, padding: 14, cursor: "pointer", width: 140,
                transition: "all 0.2s", textAlign: "center",
              }}
              onMouseEnter={e => e.currentTarget.style.transform = "translateY(-4px)"}
              onMouseLeave={e => e.currentTarget.style.transform = "none"}>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{hero.name}</div>
                <div style={{
                  fontSize: 10, color: COLORS.textMuted, marginTop: 2,
                  fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase",
                }}>{hero.alignment}</div>
                <div style={{
                  fontSize: 10, color: COLORS.textMuted, marginTop: 6,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  H{hero.health} M{hero.might} S{hero.speed} L{hero.luck} A{hero.arcana}
                </div>
                <div style={{
                  fontSize: 10, color: "#888", marginTop: 6, fontStyle: "italic",
                  lineHeight: 1.3,
                }}>{hero.passive}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Board */}
      {!showHeroSelect && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", maxWidth: 1100, margin: "0 auto" }}>
          {/* Left: Summoner side */}
          <div style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 12 }}>
            <HeroPanel heroState={gameState.championState} role="Champion" />

            {/* Summoner Resources */}
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <ResourceBar label="Life" value={gameState.summoner.life} max={30} color="#e05050" icon="❤️" />
              <ResourceBar label="Mana" value={gameState.summoner.mana} max={12} color="#4a7bc4" icon="💎" />
              <ResourceBar label="Presence" value={gameState.summoner.presence} color="#9b6fd4" icon="✨" />
              <ResourceBar label="Pain" value={gameState.summoner.pain} color="#cc4444" icon="💀" />
            </div>

            {/* Tokens */}
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              <TokenIndicator name="Order" available={gameState.summoner.orderToken} />
              <TokenIndicator name="Crush" available={gameState.summoner.crushToken} />
              <TokenIndicator name="Pray" available={gameState.summoner.prayToken} />
              <TokenIndicator name="Crystal" available={gameState.summoner.crystalToken} />
            </div>
          </div>

          {/* Center: Controls + Log */}
          <div style={{ flex: "1 1 280px", display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Action Buttons */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <button onClick={runWakeUp} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#2a4a2a", color: "#5cb85c", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>⚡ Wake Up</button>
              <button onClick={() => dealDamage("champion", 5)} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#4a2a2a", color: "#cc4444", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>Deal 5 Champion</button>
              <button onClick={() => setStatus("champion", "toughness", 3)} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#1a2a3a", color: "#6b8ccc", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>+3 Toughness</button>
              <button onClick={() => setStatus("champion", "agony", 2)} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#3a1a1a", color: "#cc4444", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>+2 Agony</button>
              <button onClick={() => setStatus("champion", "burn", 2)} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#3a2a1a", color: "#e06020", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>+2 Burn</button>
              <button onClick={() => setStatus("champion", "regen", 4)} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "#1a2a1a", color: "#5cb85c", cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700,
              }}>+4 Regen</button>
            </div>

            {/* Game Log */}
            <GameLog entries={gameState.log} />
          </div>

          {/* Right: Villain side */}
          <div style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 12 }}>
            <HeroPanel heroState={gameState.henchmanState} role="Henchman" />
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <ResourceBar label="V.Life" value={gameState.villain.life} max={60} color="#880088" icon="👹" />
              <ResourceBar label="V.Mana" value={gameState.villain.mana} max={12} color="#4a7bc4" icon="💎" />
              <ResourceBar label="Spirit" value={gameState.villain.spirit} max={8} color="#e06020" icon="🔥" />
            </div>
          </div>
        </div>
      )}

      {/* Hand */}
      {!showHeroSelect && gameState.summoner.hand.length > 0 && (
        <div style={{
          marginTop: 20, paddingTop: 16,
          borderTop: `1px solid ${COLORS.border}`,
        }}>
          <div style={{
            fontSize: 12, color: COLORS.textMuted, marginBottom: 8,
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: "uppercase", letterSpacing: 1,
          }}>Hand ({gameState.summoner.hand.length})</div>
          <div style={{
            display: "flex", gap: 10, overflowX: "auto",
            paddingBottom: 16, paddingTop: 4,
          }}>
            {gameState.summoner.hand.map((cardKey, i) => {
              const card = CARDS[cardKey];
              if (!card) return null;
              return (
                <CardComponent
                  key={i}
                  cardData={card}
                  heroState={gameState.championState}
                  isInHand={true}
                  onPlay={() => log(`Played ${card.name}`, "phase")}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Crystal Zone */}
      {!showHeroSelect && (
        <div style={{
          marginTop: 12, paddingTop: 12,
          borderTop: `1px solid ${COLORS.border}`,
        }}>
          <div style={{
            fontSize: 12, color: COLORS.textMuted, marginBottom: 8,
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: "uppercase", letterSpacing: 1,
          }}>Crystal Zone</div>
          <div style={{
            display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8,
          }}>
            {Object.entries(CRYSTALS).map(([key, crystal]) => (
              <CardComponent
                key={key}
                cardData={crystal}
                heroState={gameState.championState}
                small={true}
                onPlay={() => log(`Crystal: ${crystal.name}`, "mana")}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
