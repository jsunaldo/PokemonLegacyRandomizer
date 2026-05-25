"""
Item pools for the Pokemon Crystal Legacy Randomizer.

All item constant names match Crystal Legacy's item_constants.asm exactly.

Field items are items found as overworld pickups:
  - Visible items (Pokéball sprites on the ground) — finditem / itemball macros
  - Hidden items (found with the Itemfinder) — hiddenitem macros / hidden item tables

The "ban bad items" option removes cheap, situational consumables from the pool
so that every replaced item is at least somewhat useful.
"""

# ---------------------------------------------------------------------------
# Items that must NEVER be replaced (key items / quest-critical / HMs)
# ---------------------------------------------------------------------------
FIELD_ITEMS_SKIP = {
    # HMs
    "HM_CUT", "HM_FLY", "HM_SURF", "HM_STRENGTH", "HM_FLASH",
    "HM_WHIRLPOOL", "HM_WATERFALL",
    # Key items
    "BICYCLE", "OLD_ROD", "GOOD_ROD", "SUPER_ROD",
    "SQUIRTBOTTLE", "MYSTERY_EGG", "CARD_KEY", "MACHINE_PART",
    "LOST_ITEM", "RED_SCALE", "S_S_TICKET", "PASS", "RAINBOW_WING",
    "SILVER_WING", "BASEMENT_KEY", "CLEAR_BELL",
    "COIN_CASE", "ITEMFINDER", "BLUE_CARD", "TOWN_MAP",
    "EXP_SHARE", "POKE_FLUTE", "SECRETPOTION",
    "SILVER_LEAF", "GOLD_LEAF",
}

# ---------------------------------------------------------------------------
# "Bad" items excluded when "Ban Bad Items" is enabled
# ---------------------------------------------------------------------------
FIELD_ITEMS_BAD = {
    "POTION", "ANTIDOTE", "BURN_HEAL", "ICE_HEAL", "AWAKENING",
    "PARLYZ_HEAL", "FULL_HEAL",
    "REPEL",
    "ESCAPE_ROPE", "POKE_DOLL",
    "POKE_BALL",
}

# ---------------------------------------------------------------------------
# Full item pool — all items safe to place in the field.
# Names match Crystal Legacy item_constants.asm exactly.
# ---------------------------------------------------------------------------
FIELD_ITEM_POOL_FULL = [
    # Poké Balls
    "POKE_BALL", "GREAT_BALL", "ULTRA_BALL", "MASTER_BALL",
    "LEVEL_BALL", "LURE_BALL", "MOON_BALL", "FRIEND_BALL",
    "LOVE_BALL", "HEAVY_BALL", "FAST_BALL", "PARK_BALL",

    # Recovery
    "POTION", "SUPER_POTION", "HYPER_POTION", "MAX_POTION", "FULL_RESTORE",
    "ANTIDOTE", "BURN_HEAL", "ICE_HEAL", "AWAKENING", "PARLYZ_HEAL",
    "FULL_HEAL", "REVIVE", "MAX_REVIVE",
    "ETHER", "MAX_ETHER", "ELIXER", "MAX_ELIXER",
    "FRESH_WATER", "SODA_POP", "LEMONADE", "MOOMOO_MILK",

    # Battle items
    "X_ATTACK", "X_DEFEND", "X_SPEED", "X_ACCURACY", "X_SPECIAL",
    "GUARD_SPEC", "DIRE_HIT",

    # Repels
    "REPEL", "SUPER_REPEL", "MAX_REPEL",

    # Escape
    "ESCAPE_ROPE",

    # Vitamins / stat boosts
    "HP_UP", "PROTEIN", "IRON", "CARBOS", "CALCIUM", "PP_UP",
    "RARE_CANDY",

    # Evolution stones
    "FIRE_STONE", "WATER_STONE", "THUNDERSTONE", "LEAF_STONE",
    "MOON_STONE", "SUN_STONE",

    # Held items — type-boosting
    "BRIGHTPOWDER", "QUICK_CLAW",
    "SOFT_SAND", "SHARP_BEAK", "POISON_BARB", "NEVERMELTICE",
    "SPELL_TAG", "TWISTEDSPOON", "CHARCOAL", "DRAGON_FANG",
    "BLACKBELT_I", "MAGNET", "MYSTIC_WATER",
    "HARD_STONE", "SILVERPOWDER", "BLACKGLASSES",
    "MIRACLE_SEED", "PINK_BOW", "POLKADOT_BOW",

    # Held items — special
    "LEFTOVERS", "KINGS_ROCK", "AMULET_COIN", "LUCKY_EGG",
    "SCOPE_LENS", "THICK_CLUB", "DRAGON_SCALE", "METAL_COAT",
    "UP_GRADE", "METAL_POWDER", "LIGHT_BALL", "LUCKY_PUNCH",
    "BERSERK_GENE", "FOCUS_BAND",

    # Berries
    "BERRY", "GOLD_BERRY", "MYSTERYBERRY", "PSNCUREBERRY", "PRZCUREBERRY",

    # Sellables / nuggets
    "NUGGET", "STARDUST", "STAR_PIECE", "BIG_MUSHROOM", "TINYMUSHROOM",
    "BIG_PEARL", "PEARL",
]

# ---------------------------------------------------------------------------
# Human-readable display names for every item in the pool
# ---------------------------------------------------------------------------
ITEM_DISPLAY_NAMES = {
    # Poké Balls
    "POKE_BALL":     "Poké Ball",
    "GREAT_BALL":    "Great Ball",
    "ULTRA_BALL":    "Ultra Ball",
    "MASTER_BALL":   "Master Ball",
    "LEVEL_BALL":    "Level Ball",
    "LURE_BALL":     "Lure Ball",
    "MOON_BALL":     "Moon Ball",
    "FRIEND_BALL":   "Friend Ball",
    "LOVE_BALL":     "Love Ball",
    "HEAVY_BALL":    "Heavy Ball",
    "FAST_BALL":     "Fast Ball",
    "PARK_BALL":     "Park Ball",
    # Recovery
    "POTION":        "Potion",
    "SUPER_POTION":  "Super Potion",
    "HYPER_POTION":  "Hyper Potion",
    "MAX_POTION":    "Max Potion",
    "FULL_RESTORE":  "Full Restore",
    "ANTIDOTE":      "Antidote",
    "BURN_HEAL":     "Burn Heal",
    "ICE_HEAL":      "Ice Heal",
    "AWAKENING":     "Awakening",
    "PARLYZ_HEAL":   "Parlyz Heal",
    "FULL_HEAL":     "Full Heal",
    "REVIVE":        "Revive",
    "MAX_REVIVE":    "Max Revive",
    "ETHER":         "Ether",
    "MAX_ETHER":     "Max Ether",
    "ELIXER":        "Elixir",
    "MAX_ELIXER":    "Max Elixir",
    "FRESH_WATER":   "Fresh Water",
    "SODA_POP":      "Soda Pop",
    "LEMONADE":      "Lemonade",
    "MOOMOO_MILK":   "MooMoo Milk",
    # Battle items
    "X_ATTACK":      "X Attack",
    "X_DEFEND":      "X Defend",
    "X_SPEED":       "X Speed",
    "X_ACCURACY":    "X Accuracy",
    "X_SPECIAL":     "X Special",
    "GUARD_SPEC":    "Guard Spec.",
    "DIRE_HIT":      "Dire Hit",
    # Repels / escape
    "REPEL":         "Repel",
    "SUPER_REPEL":   "Super Repel",
    "MAX_REPEL":     "Max Repel",
    "ESCAPE_ROPE":   "Escape Rope",
    # Vitamins
    "HP_UP":         "HP Up",
    "PROTEIN":       "Protein",
    "IRON":          "Iron",
    "CARBOS":        "Carbos",
    "CALCIUM":       "Calcium",
    "PP_UP":         "PP Up",
    "RARE_CANDY":    "Rare Candy",
    # Evolution stones
    "FIRE_STONE":    "Fire Stone",
    "WATER_STONE":   "Water Stone",
    "THUNDERSTONE":  "Thunderstone",
    "LEAF_STONE":    "Leaf Stone",
    "MOON_STONE":    "Moon Stone",
    "SUN_STONE":     "Sun Stone",
    # Held items — type-boosting
    "BRIGHTPOWDER":  "BrightPowder",
    "QUICK_CLAW":    "Quick Claw",
    "SOFT_SAND":     "Soft Sand",
    "SHARP_BEAK":    "Sharp Beak",
    "POISON_BARB":   "Poison Barb",
    "NEVERMELTICE":  "NeverMeltIce",
    "SPELL_TAG":     "Spell Tag",
    "TWISTEDSPOON":  "TwistedSpoon",
    "CHARCOAL":      "Charcoal",
    "DRAGON_FANG":   "Dragon Fang",
    "BLACKBELT_I":   "Black Belt",
    "MAGNET":        "Magnet",
    "MYSTIC_WATER":  "Mystic Water",
    "HARD_STONE":    "Hard Stone",
    "SILVERPOWDER":  "SilverPowder",
    "BLACKGLASSES":  "BlackGlasses",
    "MIRACLE_SEED":  "Miracle Seed",
    "PINK_BOW":      "Pink Bow",
    "POLKADOT_BOW":  "Polkadot Bow",
    # Held items — special
    "LEFTOVERS":     "Leftovers",
    "KINGS_ROCK":    "King's Rock",
    "AMULET_COIN":   "Amulet Coin",
    "LUCKY_EGG":     "Lucky Egg",
    "SCOPE_LENS":    "Scope Lens",
    "THICK_CLUB":    "Thick Club",
    "DRAGON_SCALE":  "Dragon Scale",
    "METAL_COAT":    "Metal Coat",
    "UP_GRADE":      "Up-Grade",
    "METAL_POWDER":  "Metal Powder",
    "LIGHT_BALL":    "Light Ball",
    "LUCKY_PUNCH":   "Lucky Punch",
    "BERSERK_GENE":  "Berserk Gene",
    "FOCUS_BAND":    "Focus Band",
    # Berries
    "BERRY":         "Berry",
    "GOLD_BERRY":    "Gold Berry",
    "MYSTERYBERRY":  "MysteryBerry",
    "PSNCUREBERRY":  "PSNCureberry",
    "PRZCUREBERRY":  "PRZCureberry",
    # Sellables
    "NUGGET":        "Nugget",
    "STARDUST":      "Stardust",
    "STAR_PIECE":    "Star Piece",
    "BIG_MUSHROOM":  "Big Mushroom",
    "TINYMUSHROOM":  "TinyMushroom",
    "BIG_PEARL":     "Big Pearl",
    "PEARL":         "Pearl",
}

# Sorted list of (const, display_name) for the UI item picker
STARTING_ITEM_POOL = sorted(
    [(c, ITEM_DISPLAY_NAMES[c]) for c in FIELD_ITEM_POOL_FULL if c in ITEM_DISPLAY_NAMES],
    key=lambda x: x[1],
)

# ===========================================================================
# Crystal Legacy — pocket categorization for starting-item injection
# ===========================================================================

# Items that belong in the Balls pocket (wNumBalls / wBalls)
BALL_ITEM_CONSTS = {
    "POKE_BALL", "GREAT_BALL", "ULTRA_BALL", "MASTER_BALL",
    "LEVEL_BALL", "LURE_BALL", "MOON_BALL", "FRIEND_BALL",
    "LOVE_BALL", "HEAVY_BALL", "FAST_BALL", "PARK_BALL",
}

# Items that belong in the Key Items pocket (wNumKeyItems / wKeyItems)
KEY_ITEM_CONSTS = {
    "OLD_ROD", "GOOD_ROD", "SUPER_ROD",
    "BICYCLE", "EXP_SHARE", "ITEMFINDER", "COIN_CASE", "TOWN_MAP",
    "POKE_FLUTE", "BLUE_CARD", "PASS", "S_S_TICKET",
    "RAINBOW_WING", "SILVER_WING", "SQUIRTBOTTLE",
    "CLEAR_BELL", "BASEMENT_KEY", "SECRETPOTION",
    "MYSTERY_EGG", "MACHINE_PART", "LOST_ITEM", "CARD_KEY",
    "RED_SCALE", "SILVER_LEAF", "GOLD_LEAF",
}

# Items that belong in the TM/HM pocket (wTMsHMs byte array)
# Maps item const → ASM symbol for the 1-based TMNUM
# (defined via add_tmnum macro in constants/item_constants.asm)
TM_HM_TMNUM_SYMBOLS = {
    "TM_DYNAMICPUNCH": "DYNAMICPUNCH_TMNUM",
    "TM_HEADBUTT":     "HEADBUTT_TMNUM",
    "TM_CURSE":        "CURSE_TMNUM",
    "TM_ROLLOUT":      "ROLLOUT_TMNUM",
    "TM_ROAR":         "ROAR_TMNUM",
    "TM_TOXIC":        "TOXIC_TMNUM",
    "TM_ZAP_CANNON":   "ZAP_CANNON_TMNUM",
    "TM_ROCK_SMASH":   "ROCK_SMASH_TMNUM",
    "TM_PSYCH_UP":     "PSYCH_UP_TMNUM",
    "TM_HIDDEN_POWER": "HIDDEN_POWER_TMNUM",
    "TM_SUNNY_DAY":    "SUNNY_DAY_TMNUM",
    "TM_SWEET_SCENT":  "SWEET_SCENT_TMNUM",
    "TM_SNORE":        "SNORE_TMNUM",
    "TM_BLIZZARD":     "BLIZZARD_TMNUM",
    "TM_HYPER_BEAM":   "HYPER_BEAM_TMNUM",
    "TM_ICY_WIND":     "ICY_WIND_TMNUM",
    "TM_PROTECT":      "PROTECT_TMNUM",
    "TM_RAIN_DANCE":   "RAIN_DANCE_TMNUM",
    "TM_GIGA_DRAIN":   "GIGA_DRAIN_TMNUM",
    "TM_ENDURE":       "ENDURE_TMNUM",
    "TM_FRUSTRATION":  "FRUSTRATION_TMNUM",
    "TM_SOLARBEAM":    "SOLARBEAM_TMNUM",
    "TM_IRON_TAIL":    "IRON_TAIL_TMNUM",
    "TM_DRAGONBREATH": "DRAGONBREATH_TMNUM",
    "TM_THUNDER":      "THUNDER_TMNUM",
    "TM_EARTHQUAKE":   "EARTHQUAKE_TMNUM",
    "TM_RETURN":       "RETURN_TMNUM",
    "TM_DIG":          "DIG_TMNUM",
    "TM_PSYCHIC_M":    "PSYCHIC_M_TMNUM",
    "TM_SHADOW_BALL":  "SHADOW_BALL_TMNUM",
    "TM_MUD_SLAP":     "MUD_SLAP_TMNUM",
    "TM_DOUBLE_TEAM":  "DOUBLE_TEAM_TMNUM",
    "TM_ICE_PUNCH":    "ICE_PUNCH_TMNUM",
    "TM_SWAGGER":      "SWAGGER_TMNUM",
    "TM_SLEEP_TALK":   "SLEEP_TALK_TMNUM",
    "TM_SLUDGE_BOMB":  "SLUDGE_BOMB_TMNUM",
    "TM_SANDSTORM":    "SANDSTORM_TMNUM",
    "TM_FIRE_BLAST":   "FIRE_BLAST_TMNUM",
    "TM_SWIFT":        "SWIFT_TMNUM",
    "TM_DEFENSE_CURL": "DEFENSE_CURL_TMNUM",
    "TM_THUNDERPUNCH": "THUNDERPUNCH_TMNUM",
    "TM_DREAM_EATER":  "DREAM_EATER_TMNUM",
    "TM_DETECT":       "DETECT_TMNUM",
    "TM_REST":         "REST_TMNUM",
    "TM_ATTRACT":      "ATTRACT_TMNUM",
    "TM_THIEF":        "THIEF_TMNUM",
    "TM_STEEL_WING":   "STEEL_WING_TMNUM",
    "TM_FIRE_PUNCH":   "FIRE_PUNCH_TMNUM",
    "TM_FURY_CUTTER":  "FURY_CUTTER_TMNUM",
    "TM_NIGHTMARE":    "NIGHTMARE_TMNUM",
    "HM_CUT":          "CUT_TMNUM",
    "HM_FLY":          "FLY_TMNUM",
    "HM_SURF":         "SURF_TMNUM",
    "HM_STRENGTH":     "STRENGTH_TMNUM",
    "HM_FLASH":        "FLASH_TMNUM",
    "HM_WHIRLPOOL":    "WHIRLPOOL_TMNUM",
    "HM_WATERFALL":    "WATERFALL_TMNUM",
}

TM_HM_ITEM_CONSTS = set(TM_HM_TMNUM_SYMBOLS.keys())

# Display names for TMs, HMs, and Key Items
TM_HM_DISPLAY_NAMES = {
    # TMs (sorted by number, named after move)
    "TM_DYNAMICPUNCH": "TM01 – Dynamic Punch",
    "TM_HEADBUTT":     "TM02 – Headbutt",
    "TM_CURSE":        "TM03 – Curse",
    "TM_ROLLOUT":      "TM04 – Rollout",
    "TM_ROAR":         "TM05 – Roar",
    "TM_TOXIC":        "TM06 – Toxic",
    "TM_ZAP_CANNON":   "TM07 – Zap Cannon",
    "TM_ROCK_SMASH":   "TM08 – Rock Smash",
    "TM_PSYCH_UP":     "TM09 – Psych Up",
    "TM_HIDDEN_POWER": "TM10 – Hidden Power",
    "TM_SUNNY_DAY":    "TM11 – Sunny Day",
    "TM_SWEET_SCENT":  "TM12 – Sweet Scent",
    "TM_SNORE":        "TM13 – Snore",
    "TM_BLIZZARD":     "TM14 – Blizzard",
    "TM_HYPER_BEAM":   "TM15 – Hyper Beam",
    "TM_ICY_WIND":     "TM16 – Icy Wind",
    "TM_PROTECT":      "TM17 – Protect",
    "TM_RAIN_DANCE":   "TM18 – Rain Dance",
    "TM_GIGA_DRAIN":   "TM19 – Giga Drain",
    "TM_ENDURE":       "TM20 – Endure",
    "TM_FRUSTRATION":  "TM21 – Frustration",
    "TM_SOLARBEAM":    "TM22 – Solar Beam",
    "TM_IRON_TAIL":    "TM23 – Iron Tail",
    "TM_DRAGONBREATH": "TM24 – Dragonbreath",
    "TM_THUNDER":      "TM25 – Thunder",
    "TM_EARTHQUAKE":   "TM26 – Earthquake",
    "TM_RETURN":       "TM27 – Return",
    "TM_DIG":          "TM28 – Dig",
    "TM_PSYCHIC_M":    "TM29 – Psychic",
    "TM_SHADOW_BALL":  "TM30 – Shadow Ball",
    "TM_MUD_SLAP":     "TM31 – Mud-Slap",
    "TM_DOUBLE_TEAM":  "TM32 – Double Team",
    "TM_ICE_PUNCH":    "TM33 – Ice Punch",
    "TM_SWAGGER":      "TM34 – Swagger",
    "TM_SLEEP_TALK":   "TM35 – Sleep Talk",
    "TM_SLUDGE_BOMB":  "TM36 – Sludge Bomb",
    "TM_SANDSTORM":    "TM37 – Sandstorm",
    "TM_FIRE_BLAST":   "TM38 – Fire Blast",
    "TM_SWIFT":        "TM39 – Swift",
    "TM_DEFENSE_CURL": "TM40 – Defense Curl",
    "TM_THUNDERPUNCH": "TM41 – ThunderPunch",
    "TM_DREAM_EATER":  "TM42 – Dream Eater",
    "TM_DETECT":       "TM43 – Detect",
    "TM_REST":         "TM44 – Rest",
    "TM_ATTRACT":      "TM45 – Attract",
    "TM_THIEF":        "TM46 – Thief",
    "TM_STEEL_WING":   "TM47 – Steel Wing",
    "TM_FIRE_PUNCH":   "TM48 – Fire Punch",
    "TM_FURY_CUTTER":  "TM49 – Fury Cutter",
    "TM_NIGHTMARE":    "TM50 – Nightmare",
    # HMs
    "HM_CUT":          "HM01 – Cut",
    "HM_FLY":          "HM02 – Fly",
    "HM_SURF":         "HM03 – Surf",
    "HM_STRENGTH":     "HM04 – Strength",
    "HM_FLASH":        "HM05 – Flash",
    "HM_WHIRLPOOL":    "HM06 – Whirlpool",
    "HM_WATERFALL":    "HM07 – Waterfall",
}

KEY_ITEM_DISPLAY_NAMES = {
    "OLD_ROD":       "Old Rod",
    "GOOD_ROD":      "Good Rod",
    "SUPER_ROD":     "Super Rod",
    "BICYCLE":       "Bicycle",
    "EXP_SHARE":     "Exp. Share",
    "ITEMFINDER":    "Itemfinder",
    "COIN_CASE":     "Coin Case",
    "TOWN_MAP":      "Town Map",
    "POKE_FLUTE":    "Poké Flute",
    "BLUE_CARD":     "Blue Card",
    "PASS":          "Pass",
    "S_S_TICKET":    "S.S. Ticket",
    "RAINBOW_WING":  "Rainbow Wing",
    "SILVER_WING":   "Silver Wing",
    "SQUIRTBOTTLE":  "Squirt Bottle",
    "CLEAR_BELL":    "Clear Bell",
    "BASEMENT_KEY":  "Basement Key",
    "SECRETPOTION":  "SecretPotion",
    "MYSTERY_EGG":   "Mystery Egg",
    "MACHINE_PART":  "Machine Part",
    "LOST_ITEM":     "Lost Item",
    "CARD_KEY":      "Card Key",
    "RED_SCALE":     "Red Scale",
    "SILVER_LEAF":   "Silver Leaf",
    "GOLD_LEAF":     "Gold Leaf",
}

# Full starting-item pool including TMs, HMs, and Key Items
# Sorted: TMs (TM01–TM50) first, then HMs (HM01–HM07), then Key Items (alpha),
# then all regular items (alpha) — making TMs easy to find at the top.
_TM_POOL    = list(TM_HM_DISPLAY_NAMES.keys())   # already in TM01–TM50, HM01–HM07 order
_KEY_POOL   = sorted(KEY_ITEM_DISPLAY_NAMES.keys(),  key=lambda c: KEY_ITEM_DISPLAY_NAMES[c])
_REG_POOL   = sorted(
    [c for c in FIELD_ITEM_POOL_FULL if c in ITEM_DISPLAY_NAMES],
    key=lambda c: ITEM_DISPLAY_NAMES[c],
)

STARTING_ITEM_POOL_ALL = (
    [(c, TM_HM_DISPLAY_NAMES[c])  for c in _TM_POOL]
    + [(c, KEY_ITEM_DISPLAY_NAMES[c]) for c in _KEY_POOL]
    + [(c, ITEM_DISPLAY_NAMES[c])     for c in _REG_POOL]
)

# Remove any items in SKIP from the full pool (safety net)
FIELD_ITEM_POOL_FULL = [
    i for i in FIELD_ITEM_POOL_FULL
    if i not in FIELD_ITEMS_SKIP
]

# ---------------------------------------------------------------------------
# "Good" pool — excludes bad items
# ---------------------------------------------------------------------------
FIELD_ITEM_POOL_GOOD = [
    i for i in FIELD_ITEM_POOL_FULL
    if i not in FIELD_ITEMS_BAD
]

# ===========================================================================
# Yellow Legacy (Gen 1) item data
# ===========================================================================

# Items that should never be replaced in field randomization (key / quest items)
# Mirrors YELLOW_KEY_ITEMS in constants_yellow.py — duplicated here for import convenience
YELLOW_FIELD_ITEMS_SKIP = {
    'TOWN_MAP', 'BICYCLE', 'SURFBOARD', 'SAFARI_BALL', 'POKEDEX',
    'BOULDERBADGE', 'CASCADEBADGE', 'THUNDERBADGE', 'RAINBOWBADGE',
    'SOULBADGE', 'MARSHBADGE', 'VOLCANOBADGE', 'EARTHBADGE',
    'OLD_AMBER', 'DOME_FOSSIL', 'HELIX_FOSSIL', 'SECRET_KEY',
    'BIKE_VOUCHER', 'CARD_KEY', 'S_S_TICKET', 'GOLD_TEETH',
    'COIN_CASE', 'OAKS_PARCEL', 'ITEMFINDER', 'SILPH_SCOPE',
    'POKE_FLUTE', 'LIFT_KEY', 'EXP_ALL',
    'OLD_ROD', 'GOOD_ROD', 'SUPER_ROD',
    'NO_ITEM', 'COIN',
}

# Cheap / situational items excluded by "Ban Bad Items"
YELLOW_FIELD_ITEMS_BAD = {
    'POTION', 'ANTIDOTE', 'BURN_HEAL', 'ICE_HEAL', 'AWAKENING', 'PARLYZ_HEAL',
    'FULL_HEAL', 'REPEL', 'ESCAPE_ROPE', 'POKE_DOLL', 'POKE_BALL',
}

# Human-readable display names for Gen 1 items
YELLOW_ITEM_DISPLAY_NAMES = {
    'MASTER_BALL':   'Master Ball',
    'ULTRA_BALL':    'Ultra Ball',
    'GREAT_BALL':    'Great Ball',
    'POKE_BALL':     'Poké Ball',
    'MOON_STONE':    'Moon Stone',
    'ANTIDOTE':      'Antidote',
    'BURN_HEAL':     'Burn Heal',
    'ICE_HEAL':      'Ice Heal',
    'AWAKENING':     'Awakening',
    'PARLYZ_HEAL':   'Parlyz Heal',
    'FULL_RESTORE':  'Full Restore',
    'MAX_POTION':    'Max Potion',
    'HYPER_POTION':  'Hyper Potion',
    'SUPER_POTION':  'Super Potion',
    'POTION':        'Potion',
    'ESCAPE_ROPE':   'Escape Rope',
    'REPEL':         'Repel',
    'FIRE_STONE':    'Fire Stone',
    'THUNDER_STONE': 'Thunder Stone',
    'WATER_STONE':   'Water Stone',
    'HP_UP':         'HP Up',
    'PROTEIN':       'Protein',
    'IRON':          'Iron',
    'CARBOS':        'Carbos',
    'CALCIUM':       'Calcium',
    'RARE_CANDY':    'Rare Candy',
    'X_ACCURACY':    'X Accuracy',
    'LEAF_STONE':    'Leaf Stone',
    'NUGGET':        'Nugget',
    'POKE_DOLL':     'Poké Doll',
    'FULL_HEAL':     'Full Heal',
    'REVIVE':        'Revive',
    'MAX_REVIVE':    'Max Revive',
    'GUARD_SPEC':    'Guard Spec.',
    'SUPER_REPEL':   'Super Repel',
    'MAX_REPEL':     'Max Repel',
    'DIRE_HIT':      'Dire Hit',
    'FRESH_WATER':   'Fresh Water',
    'SODA_POP':      'Soda Pop',
    'LEMONADE':      'Lemonade',
    'X_ATTACK':      'X Attack',
    'X_DEFEND':      'X Defend',
    'X_SPEED':       'X Speed',
    'X_SPECIAL':     'X Special',
    'PP_UP':         'PP Up',
    'ETHER':         'Ether',
    'MAX_ETHER':     'Max Ether',
    'ELIXER':        'Elixir',
    'MAX_ELIXER':    'Max Elixir',
}

# Full Gen 1 field item pool (excludes key / quest items)
YELLOW_FIELD_ITEM_POOL_FULL = [c for c in YELLOW_ITEM_DISPLAY_NAMES if c not in YELLOW_FIELD_ITEMS_SKIP]

# Good pool — excludes cheap / situational items
YELLOW_FIELD_ITEM_POOL_GOOD = [i for i in YELLOW_FIELD_ITEM_POOL_FULL if i not in YELLOW_FIELD_ITEMS_BAD]

# Sorted (const, display_name) list for the starting-bag UI combobox
YELLOW_STARTING_ITEM_POOL = sorted(
    [(c, YELLOW_ITEM_DISPLAY_NAMES[c]) for c in YELLOW_FIELD_ITEM_POOL_FULL],
    key=lambda x: x[1],
)

# ===========================================================================
# Emerald Legacy (Gen 3 / GBA) item data
# ===========================================================================

# Items that must NEVER be replaced (key / quest items, HMs)
# Duplicated from constants_emerald.py for import convenience
EMERALD_FIELD_ITEMS_SKIP = {
    'ITEM_HM01', 'ITEM_HM02', 'ITEM_HM03', 'ITEM_HM04',
    'ITEM_HM05', 'ITEM_HM06', 'ITEM_HM07', 'ITEM_HM08',
    'ITEM_MACH_BIKE', 'ITEM_COIN_CASE', 'ITEM_ITEMFINDER',
    'ITEM_OLD_ROD', 'ITEM_GOOD_ROD', 'ITEM_SUPER_ROD',
    'ITEM_SS_TICKET', 'ITEM_CONTEST_PASS', 'ITEM_WAILMER_PAIL',
    'ITEM_DEVON_GOODS', 'ITEM_SOOT_SACK', 'ITEM_BASEMENT_KEY',
    'ITEM_ACRO_BIKE', 'ITEM_POKENAV', 'ITEM_LETTER',
    'ITEM_EON_TICKET', 'ITEM_RED_ORB', 'ITEM_BLUE_ORB',
    'ITEM_SCANNER', 'ITEM_GO_GOGGLES', 'ITEM_METEORITE',
    'ITEM_ROOM1_KEY', 'ITEM_ROOM2_KEY', 'ITEM_ROOM4_KEY',
    'ITEM_ROOM6_KEY', 'ITEM_STORAGE_KEY',
    'ITEM_ROOT_FOSSIL', 'ITEM_CLAW_FOSSIL', 'ITEM_DEVON_SCOPE',
    'ITEM_MAGMA_EMBLEM', 'ITEM_OLD_SEA_MAP',
    'ITEM_AURORA_TICKET', 'ITEM_MYSTIC_TICKET',
    'ITEM_POWDER_JAR', 'ITEM_TM_CASE', 'ITEM_BERRY_POUCH',
    'ITEM_TEACH_TV', 'ITEM_POKEBLOCK_CASE',
    'ITEM_NONE', 'ITEM_SAFARI_BALL',
}

# Cheap / situational items excluded by "Ban Bad Items"
EMERALD_FIELD_ITEMS_BAD = {
    'ITEM_POTION', 'ITEM_ANTIDOTE', 'ITEM_BURN_HEAL',
    'ITEM_ICE_HEAL', 'ITEM_AWAKENING', 'ITEM_PARALYZE_HEAL',
    'ITEM_FULL_HEAL', 'ITEM_REPEL', 'ITEM_ESCAPE_ROPE',
    'ITEM_POKE_BALL', 'ITEM_FLUFFY_TAIL',
}

# Human-readable display names for Gen 3 Emerald items
EMERALD_ITEM_DISPLAY_NAMES = {
    # Poké Balls
    'ITEM_POKE_BALL':      'Poké Ball',
    'ITEM_GREAT_BALL':     'Great Ball',
    'ITEM_ULTRA_BALL':     'Ultra Ball',
    'ITEM_MASTER_BALL':    'Master Ball',
    'ITEM_NET_BALL':       'Net Ball',
    'ITEM_DIVE_BALL':      'Dive Ball',
    'ITEM_NEST_BALL':      'Nest Ball',
    'ITEM_REPEAT_BALL':    'Repeat Ball',
    'ITEM_TIMER_BALL':     'Timer Ball',
    'ITEM_LUXURY_BALL':    'Luxury Ball',
    'ITEM_PREMIER_BALL':   'Premier Ball',
    # Recovery
    'ITEM_POTION':         'Potion',
    'ITEM_SUPER_POTION':   'Super Potion',
    'ITEM_HYPER_POTION':   'Hyper Potion',
    'ITEM_MAX_POTION':     'Max Potion',
    'ITEM_FULL_RESTORE':   'Full Restore',
    'ITEM_ANTIDOTE':       'Antidote',
    'ITEM_BURN_HEAL':      'Burn Heal',
    'ITEM_ICE_HEAL':       'Ice Heal',
    'ITEM_AWAKENING':      'Awakening',
    'ITEM_PARALYZE_HEAL':  'Paralyze Heal',
    'ITEM_FULL_HEAL':      'Full Heal',
    'ITEM_REVIVE':         'Revive',
    'ITEM_MAX_REVIVE':     'Max Revive',
    'ITEM_ETHER':          'Ether',
    'ITEM_MAX_ETHER':      'Max Ether',
    'ITEM_ELIXIR':         'Elixir',
    'ITEM_MAX_ELIXIR':     'Max Elixir',
    'ITEM_FRESH_WATER':    'Fresh Water',
    'ITEM_SODA_POP':       'Soda Pop',
    'ITEM_LEMONADE':       'Lemonade',
    'ITEM_MOOMOO_MILK':    'MooMoo Milk',
    # Battle items
    'ITEM_X_ATTACK':       'X Attack',
    'ITEM_X_DEFEND':       'X Defend',
    'ITEM_X_SPEED':        'X Speed',
    'ITEM_X_ACCURACY':     'X Accuracy',
    'ITEM_X_SPECIAL':      'X Special',
    'ITEM_GUARD_SPEC':     'Guard Spec.',
    'ITEM_DIRE_HIT':       'Dire Hit',
    # Repels
    'ITEM_REPEL':          'Repel',
    'ITEM_SUPER_REPEL':    'Super Repel',
    'ITEM_MAX_REPEL':      'Max Repel',
    # Escape
    'ITEM_ESCAPE_ROPE':    'Escape Rope',
    'ITEM_FLUFFY_TAIL':    'Fluffy Tail',
    # Vitamins
    'ITEM_HP_UP':          'HP Up',
    'ITEM_PROTEIN':        'Protein',
    'ITEM_IRON':           'Iron',
    'ITEM_CARBOS':         'Carbos',
    'ITEM_CALCIUM':        'Calcium',
    'ITEM_ZINC':           'Zinc',
    'ITEM_PP_UP':          'PP Up',
    'ITEM_PP_MAX':         'PP Max',
    'ITEM_RARE_CANDY':     'Rare Candy',
    # Evolution stones
    'ITEM_FIRE_STONE':     'Fire Stone',
    'ITEM_WATER_STONE':    'Water Stone',
    'ITEM_THUNDER_STONE':  'Thunder Stone',
    'ITEM_LEAF_STONE':     'Leaf Stone',
    'ITEM_MOON_STONE':     'Moon Stone',
    'ITEM_SUN_STONE':      'Sun Stone',
    # Held items — type-boosting
    'ITEM_BRIGHTPOWDER':   'BrightPowder',
    'ITEM_QUICK_CLAW':     'Quick Claw',
    'ITEM_CHARCOAL':       'Charcoal',
    'ITEM_MYSTIC_WATER':   'Mystic Water',
    'ITEM_MAGNET':         'Magnet',
    'ITEM_MIRACLE_SEED':   'Miracle Seed',
    'ITEM_NEVERMELTICE':   'NeverMeltIce',
    'ITEM_SOFT_SAND':      'Soft Sand',
    'ITEM_HARD_STONE':     'Hard Stone',
    'ITEM_SILVERPOWDER':   'SilverPowder',
    'ITEM_SPELL_TAG':      'Spell Tag',
    'ITEM_TWISTEDSPOON':   'TwistedSpoon',
    'ITEM_SHARP_BEAK':     'Sharp Beak',
    'ITEM_POISON_BARB':    'Poison Barb',
    'ITEM_BLACKBELT':      'Black Belt',
    'ITEM_BLACKGLASSES':   'BlackGlasses',
    'ITEM_DRAGON_FANG':    'Dragon Fang',
    # Held items — special
    'ITEM_LEFTOVERS':      'Leftovers',
    'ITEM_KINGS_ROCK':     "King's Rock",
    'ITEM_AMULET_COIN':    'Amulet Coin',
    'ITEM_LUCKY_EGG':      'Lucky Egg',
    'ITEM_SCOPE_LENS':     'Scope Lens',
    'ITEM_METAL_COAT':     'Metal Coat',
    'ITEM_DRAGON_SCALE':   'Dragon Scale',
    'ITEM_UP_GRADE':       'Up-Grade',
    'ITEM_CHOICE_BAND':    'Choice Band',
    'ITEM_FOCUS_BAND':     'Focus Band',
    'ITEM_LAXINCENSE':     'Lax Incense',
    'ITEM_SEAINCENSE':     'Sea Incense',
    'ITEM_LUCKY_PUNCH':    'Lucky Punch',
    'ITEM_THICK_CLUB':     'Thick Club',
    'ITEM_LIGHT_BALL':     'Light Ball',
    'ITEM_METAL_POWDER':   'Metal Powder',
    'ITEM_DEEP_SEA_SCALE': 'DeepSeaScale',
    'ITEM_DEEP_SEA_TOOTH': 'DeepSeaTooth',
    # Berries
    'ITEM_ORAN_BERRY':     'Oran Berry',
    'ITEM_SITRUS_BERRY':   'Sitrus Berry',
    'ITEM_LUM_BERRY':      'Lum Berry',
    'ITEM_LEPPA_BERRY':    'Leppa Berry',
    'ITEM_PECHA_BERRY':    'Pecha Berry',
    'ITEM_RAWST_BERRY':    'Rawst Berry',
    'ITEM_CHESTO_BERRY':   'Chesto Berry',
    'ITEM_PERSIM_BERRY':   'Persim Berry',
    'ITEM_SALAC_BERRY':    'Salac Berry',
    'ITEM_PETAYA_BERRY':   'Petaya Berry',
    'ITEM_GANLON_BERRY':   'Ganlon Berry',
    'ITEM_LIECHI_BERRY':   'Liechi Berry',
    'ITEM_APICOT_BERRY':   'Apicot Berry',
    'ITEM_LANSAT_BERRY':   'Lansat Berry',
    'ITEM_STARF_BERRY':    'Starf Berry',
    # Sellables
    'ITEM_NUGGET':         'Nugget',
    'ITEM_BIG_NUGGET':     'Big Nugget',
    'ITEM_STARDUST':       'Stardust',
    'ITEM_STAR_PIECE':     'Star Piece',
    'ITEM_BIG_MUSHROOM':   'Big Mushroom',
    'ITEM_TINY_MUSHROOM':  'Tiny Mushroom',
    'ITEM_BIG_PEARL':      'Big Pearl',
    'ITEM_PEARL':          'Pearl',
}

# Full Gen 3 field item pool (all items safe to place in the field)
EMERALD_FIELD_ITEM_POOL_FULL = [
    c for c in EMERALD_ITEM_DISPLAY_NAMES
    if c not in EMERALD_FIELD_ITEMS_SKIP
]

# Good pool — excludes cheap / situational items
EMERALD_FIELD_ITEM_POOL_GOOD = [
    c for c in EMERALD_FIELD_ITEM_POOL_FULL
    if c not in EMERALD_FIELD_ITEMS_BAD
]

# Sorted (const, display_name) list for the starting items UI combobox
EMERALD_STARTING_ITEM_POOL = sorted(
    [(c, EMERALD_ITEM_DISPLAY_NAMES[c]) for c in EMERALD_FIELD_ITEM_POOL_FULL],
    key=lambda x: x[1],
)
