"""
Constants for the Pokemon Emerald Legacy Randomizer.

All file paths are relative to the Emerald Legacy source root.
The source is a GBA C/ASM project (pret disassembly base).

Key data files:
  - Wild encounters : src/data/wild_encounters.json   (JSON)
  - Trainer parties : src/data/trainer_parties.h      (C struct arrays)
  - Trainer defs    : src/data/trainers.h             (C struct array)
  - Starters        : src/starter_choose.c            (C array)
  - Field items     : data/scripts/item_ball_scripts.inc (ASM scripts)
  - Static battles  : data/scripts/*.inc              (ASM scripts)
  - Species consts  : include/constants/species.h     (C #define)
  - Item consts     : include/constants/items.h       (C #define)
  - BST / types     : src/data/pokemon/species_info.h (C struct array)
"""

# ---------------------------------------------------------------------------
# Source file paths (relative to source root)
# ---------------------------------------------------------------------------
EMERALD_SPECIES_FILE      = 'include/constants/species.h'
EMERALD_ITEMS_FILE        = 'include/constants/items.h'
EMERALD_SPECIES_INFO_FILE = 'src/data/pokemon/species_info.h'
EMERALD_WILD_FILE         = 'src/data/wild_encounters.json'
EMERALD_PARTIES_FILE      = 'src/data/trainer_parties.h'
EMERALD_TRAINERS_FILE     = 'src/data/trainers.h'
EMERALD_STARTER_FILE      = 'src/starter_choose.c'
EMERALD_ITEM_SCRIPTS_FILE = 'data/scripts/item_ball_scripts.inc'
EMERALD_SCRIPTS_DIR       = 'data/scripts'

# ---------------------------------------------------------------------------
# Wild encounter JSON field keys
# ---------------------------------------------------------------------------
EMERALD_WILD_TYPES = ['land_mons', 'water_mons', 'rock_smash_mons', 'fishing_mons']

# Fishing slot indices for each rod type
EMERALD_FISHING_GROUPS = {
    'old_rod':   [0, 1],
    'good_rod':  [2, 3, 4],
    'super_rod': [5, 6, 7, 8, 9],
}

# ---------------------------------------------------------------------------
# Legendary species (SPECIES_ prefix, as defined in species.h)
# ---------------------------------------------------------------------------
EMERALD_LEGENDARY_SPECIES = frozenset({
    # Gen 1
    'SPECIES_ARTICUNO', 'SPECIES_ZAPDOS', 'SPECIES_MOLTRES',
    'SPECIES_MEWTWO', 'SPECIES_MEW',
    # Gen 2
    'SPECIES_RAIKOU', 'SPECIES_ENTEI', 'SPECIES_SUICUNE',
    'SPECIES_LUGIA', 'SPECIES_HO_OH', 'SPECIES_CELEBI',
    # Gen 3
    'SPECIES_REGIROCK', 'SPECIES_REGICE', 'SPECIES_REGISTEEL',
    'SPECIES_LATIAS', 'SPECIES_LATIOS',
    'SPECIES_LALIME',   # Latias alternate const in some Emerald Legacy builds
    'SPECIES_KYOGRE', 'SPECIES_GROUDON', 'SPECIES_RAYQUAZA',
    'SPECIES_JIRACHI', 'SPECIES_DEOXYS',
    'SPECIES_DEOXYS_SPEED', 'SPECIES_DEOXYS_ATTACK', 'SPECIES_DEOXYS_DEFENSE',
})

# Species constants that must never enter the randomization pool
EMERALD_SPECIES_SKIP = frozenset({
    'SPECIES_NONE', 'SPECIES_EGG',
})

# Prefix for Unown letter variants (filter out at parse time)
EMERALD_UNOWN_PREFIX = 'SPECIES_UNOWN_'

# ---------------------------------------------------------------------------
# Field items — skip list (key / quest items never replaced)
# ---------------------------------------------------------------------------
EMERALD_FIELD_ITEMS_SKIP = frozenset({
    # HMs
    'ITEM_HM01', 'ITEM_HM02', 'ITEM_HM03', 'ITEM_HM04',
    'ITEM_HM05', 'ITEM_HM06', 'ITEM_HM07', 'ITEM_HM08',
    # Key items
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
})

# Field items — "bad" pool excluded when Ban Bad Items is enabled
EMERALD_FIELD_ITEMS_BAD = frozenset({
    'ITEM_POTION', 'ITEM_ANTIDOTE', 'ITEM_BURN_HEAL',
    'ITEM_ICE_HEAL', 'ITEM_AWAKENING', 'ITEM_PARALYZE_HEAL',
    'ITEM_FULL_HEAL', 'ITEM_REPEL', 'ITEM_ESCAPE_ROPE',
    'ITEM_POKE_BALL', 'ITEM_FLUFFY_TAIL',
})

# ---------------------------------------------------------------------------
# Boss trainer class substrings (matched against trainerClass value)
# Used for type-themed boss mode
# ---------------------------------------------------------------------------
EMERALD_BOSS_CLASS_KEYWORDS = (
    'TRAINER_CLASS_LEADER',
    'TRAINER_CLASS_ELITE_FOUR',
    'TRAINER_CLASS_CHAMPION',
    'TRAINER_CLASS_TEAM_MAGMA_LEADER',
    'TRAINER_CLASS_TEAM_AQUA_LEADER',
)

# ---------------------------------------------------------------------------
# First-stage Pokémon from 3-stage evolution lines (Gen 1–3)
# Used for "Random (basic with 2 evolutions)" starter mode
# ---------------------------------------------------------------------------
EMERALD_TWO_STAGE_STARTERS = frozenset({
    # Gen 1 three-stage lines (first stage)
    'SPECIES_BULBASAUR','SPECIES_CHARMANDER','SPECIES_SQUIRTLE',
    'SPECIES_CATERPIE','SPECIES_WEEDLE','SPECIES_PIDGEY',
    'SPECIES_RATTATA','SPECIES_SPEAROW','SPECIES_EKANS',
    'SPECIES_SANDSHREW','SPECIES_NIDORAN_F','SPECIES_NIDORAN_M',
    'SPECIES_CLEFAIRY','SPECIES_VULPIX','SPECIES_JIGGLYPUFF',
    'SPECIES_ZUBAT','SPECIES_ODDISH','SPECIES_PARAS',
    'SPECIES_VENONAT','SPECIES_DIGLETT','SPECIES_MEOWTH',
    'SPECIES_PSYDUCK','SPECIES_MANKEY','SPECIES_GROWLITHE',
    'SPECIES_POLIWAG','SPECIES_ABRA','SPECIES_MACHOP',
    'SPECIES_BELLSPROUT','SPECIES_TENTACOOL','SPECIES_GEODUDE',
    'SPECIES_PONYTA','SPECIES_SLOWPOKE','SPECIES_MAGNEMITE',
    'SPECIES_DODUO','SPECIES_SEEL','SPECIES_GRIMER',
    'SPECIES_SHELLDER','SPECIES_GASTLY','SPECIES_DROWZEE',
    'SPECIES_KRABBY','SPECIES_VOLTORB','SPECIES_EXEGGCUTE',
    'SPECIES_CUBONE','SPECIES_KOFFING','SPECIES_RHYHORN',
    'SPECIES_HORSEA','SPECIES_GOLDEEN','SPECIES_STARYU',
    'SPECIES_MAGIKARP','SPECIES_EEVEE','SPECIES_OMANYTE',
    'SPECIES_KABUTO','SPECIES_DRATINI',
    # Gen 2 three-stage lines (first stage)
    'SPECIES_CHIKORITA','SPECIES_CYNDAQUIL','SPECIES_TOTODILE',
    'SPECIES_SENTRET','SPECIES_HOOTHOOT','SPECIES_LEDYBA',
    'SPECIES_SPINARAK','SPECIES_CHINCHOU','SPECIES_PICHU',
    'SPECIES_TOGEPI','SPECIES_NATU','SPECIES_MAREEP',
    'SPECIES_MARILL','SPECIES_HOPPIP','SPECIES_SUNKERN',
    'SPECIES_WOOPER','SPECIES_PINECO','SPECIES_SNUBBULL',
    'SPECIES_TEDDIURSA','SPECIES_SLUGMA','SPECIES_SWINUB',
    'SPECIES_REMORAID','SPECIES_HOUNDOUR','SPECIES_PHANPY',
    'SPECIES_LARVITAR',
    # Gen 3 three-stage lines (first stage)
    'SPECIES_TREECKO','SPECIES_TORCHIC','SPECIES_MUDKIP',
    'SPECIES_POOCHYENA','SPECIES_ZIGZAGOON','SPECIES_WURMPLE',
    'SPECIES_LOTAD','SPECIES_SEEDOT','SPECIES_TAILLOW',
    'SPECIES_WINGULL','SPECIES_RALTS','SPECIES_SURSKIT',
    'SPECIES_SHROOMISH','SPECIES_SLAKOTH','SPECIES_WHISMUR',
    'SPECIES_MAKUHITA','SPECIES_SKITTY','SPECIES_ARON',
    'SPECIES_MEDITITE','SPECIES_ELECTRIKE','SPECIES_GULPIN',
    'SPECIES_CARVANHA','SPECIES_WAILMER','SPECIES_NUMEL',
    'SPECIES_SPOINK','SPECIES_TRAPINCH','SPECIES_CACNEA',
    'SPECIES_SWABLU','SPECIES_BARBOACH','SPECIES_CORPHISH',
    'SPECIES_BALTOY','SPECIES_LILEEP','SPECIES_ANORITH',
    'SPECIES_SHUPPET','SPECIES_DUSKULL','SPECIES_SNORUNT',
    'SPECIES_SPHEAL','SPECIES_CLAMPERL','SPECIES_BAGON',
    'SPECIES_BELDUM',
})
