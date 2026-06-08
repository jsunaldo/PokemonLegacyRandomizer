"""
Pokemon Yellow Legacy Randomizer - Constants
Pokemon names, ASM constant mappings, and path constants for Gen 1 (151 Pokemon).

Key Gen 1 differences from Crystal:
  - FARFETCHD   (no apostrophe/underscore)
  - MR_MIME     (single underscore)
  - NIDORAN_F / NIDORAN_M  (same as Crystal)
  - Internal IDs are scrambled (YELLOW_INTERNAL_ID gives the raw byte)
"""

# ── Pokemon names (dex order, index 1–151) ────────────────────────────────────
POKEMON_NAMES = [
    None,  # index 0 placeholder
    "Bulbasaur", "Ivysaur", "Venusaur",
    "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise",
    "Caterpie", "Metapod", "Butterfree",
    "Weedle", "Kakuna", "Beedrill",
    "Pidgey", "Pidgeotto", "Pidgeot",
    "Rattata", "Raticate",
    "Spearow", "Fearow",
    "Ekans", "Arbok",
    "Pikachu", "Raichu",
    "Sandshrew", "Sandslash",
    "Nidoran-F", "Nidorina", "Nidoqueen",
    "Nidoran-M", "Nidorino", "Nidoking",
    "Clefairy", "Clefable",
    "Vulpix", "Ninetales",
    "Jigglypuff", "Wigglytuff",
    "Zubat", "Golbat",
    "Oddish", "Gloom", "Vileplume",
    "Paras", "Parasect",
    "Venonat", "Venomoth",
    "Diglett", "Dugtrio",
    "Meowth", "Persian",
    "Psyduck", "Golduck",
    "Mankey", "Primeape",
    "Growlithe", "Arcanine",
    "Poliwag", "Poliwhirl", "Poliwrath",
    "Abra", "Kadabra", "Alakazam",
    "Machop", "Machoke", "Machamp",
    "Bellsprout", "Weepinbell", "Victreebel",
    "Tentacool", "Tentacruel",
    "Geodude", "Graveler", "Golem",
    "Ponyta", "Rapidash",
    "Slowpoke", "Slowbro",
    "Magnemite", "Magneton",
    "Farfetch'd",
    "Doduo", "Dodrio",
    "Seel", "Dewgong",
    "Grimer", "Muk",
    "Shellder", "Cloyster",
    "Gastly", "Haunter", "Gengar",
    "Onix",
    "Drowzee", "Hypno",
    "Krabby", "Kingler",
    "Voltorb", "Electrode",
    "Exeggcute", "Exeggutor",
    "Cubone", "Marowak",
    "Hitmonlee", "Hitmonchan",
    "Lickitung",
    "Koffing", "Weezing",
    "Rhyhorn", "Rhydon",
    "Chansey",
    "Tangela",
    "Kangaskhan",
    "Horsea", "Seadra",
    "Goldeen", "Seaking",
    "Staryu", "Starmie",
    "Mr. Mime",
    "Scyther",
    "Jynx",
    "Electabuzz",
    "Magmar",
    "Pinsir",
    "Tauros",
    "Magikarp", "Gyarados",
    "Lapras",
    "Ditto",
    "Eevee", "Vaporeon", "Jolteon", "Flareon",
    "Porygon",
    "Omanyte", "Omastar",
    "Kabuto", "Kabutops",
    "Aerodactyl",
    "Snorlax",
    "Articuno", "Zapdos", "Moltres",
    "Dratini", "Dragonair", "Dragonite",
    "Mewtwo",
    "Mew",
]

# ── ASM constant name → Pokédex number ───────────────────────────────────────
# NOTE: Yellow uses FARFETCHD (no underscore) and MR_MIME (single underscore).
POKEMON_CONSTANTS = {
    "BULBASAUR": 1,   "IVYSAUR": 2,      "VENUSAUR": 3,
    "CHARMANDER": 4,  "CHARMELEON": 5,   "CHARIZARD": 6,
    "SQUIRTLE": 7,    "WARTORTLE": 8,    "BLASTOISE": 9,
    "CATERPIE": 10,   "METAPOD": 11,     "BUTTERFREE": 12,
    "WEEDLE": 13,     "KAKUNA": 14,      "BEEDRILL": 15,
    "PIDGEY": 16,     "PIDGEOTTO": 17,   "PIDGEOT": 18,
    "RATTATA": 19,    "RATICATE": 20,
    "SPEAROW": 21,    "FEAROW": 22,
    "EKANS": 23,      "ARBOK": 24,
    "PIKACHU": 25,    "RAICHU": 26,
    "SANDSHREW": 27,  "SANDSLASH": 28,
    "NIDORAN_F": 29,  "NIDORINA": 30,   "NIDOQUEEN": 31,
    "NIDORAN_M": 32,  "NIDORINO": 33,   "NIDOKING": 34,
    "CLEFAIRY": 35,   "CLEFABLE": 36,
    "VULPIX": 37,     "NINETALES": 38,
    "JIGGLYPUFF": 39, "WIGGLYTUFF": 40,
    "ZUBAT": 41,      "GOLBAT": 42,
    "ODDISH": 43,     "GLOOM": 44,      "VILEPLUME": 45,
    "PARAS": 46,      "PARASECT": 47,
    "VENONAT": 48,    "VENOMOTH": 49,
    "DIGLETT": 50,    "DUGTRIO": 51,
    "MEOWTH": 52,     "PERSIAN": 53,
    "PSYDUCK": 54,    "GOLDUCK": 55,
    "MANKEY": 56,     "PRIMEAPE": 57,
    "GROWLITHE": 58,  "ARCANINE": 59,
    "POLIWAG": 60,    "POLIWHIRL": 61,  "POLIWRATH": 62,
    "ABRA": 63,       "KADABRA": 64,    "ALAKAZAM": 65,
    "MACHOP": 66,     "MACHOKE": 67,    "MACHAMP": 68,
    "BELLSPROUT": 69, "WEEPINBELL": 70, "VICTREEBEL": 71,
    "TENTACOOL": 72,  "TENTACRUEL": 73,
    "GEODUDE": 74,    "GRAVELER": 75,   "GOLEM": 76,
    "PONYTA": 77,     "RAPIDASH": 78,
    "SLOWPOKE": 79,   "SLOWBRO": 80,
    "MAGNEMITE": 81,  "MAGNETON": 82,
    "FARFETCHD": 83,
    "DODUO": 84,      "DODRIO": 85,
    "SEEL": 86,       "DEWGONG": 87,
    "GRIMER": 88,     "MUK": 89,
    "SHELLDER": 90,   "CLOYSTER": 91,
    "GASTLY": 92,     "HAUNTER": 93,    "GENGAR": 94,
    "ONIX": 95,
    "DROWZEE": 96,    "HYPNO": 97,
    "KRABBY": 98,     "KINGLER": 99,
    "VOLTORB": 100,   "ELECTRODE": 101,
    "EXEGGCUTE": 102, "EXEGGUTOR": 103,
    "CUBONE": 104,    "MAROWAK": 105,
    "HITMONLEE": 106, "HITMONCHAN": 107,
    "LICKITUNG": 108,
    "KOFFING": 109,   "WEEZING": 110,
    "RHYHORN": 111,   "RHYDON": 112,
    "CHANSEY": 113,
    "TANGELA": 114,
    "KANGASKHAN": 115,
    "HORSEA": 116,    "SEADRA": 117,
    "GOLDEEN": 118,   "SEAKING": 119,
    "STARYU": 120,    "STARMIE": 121,
    "MR_MIME": 122,
    "SCYTHER": 123,
    "JYNX": 124,
    "ELECTABUZZ": 125,
    "MAGMAR": 126,
    "PINSIR": 127,
    "TAUROS": 128,
    "MAGIKARP": 129,  "GYARADOS": 130,
    "LAPRAS": 131,
    "DITTO": 132,
    "EEVEE": 133,     "VAPOREON": 134,  "JOLTEON": 135,  "FLAREON": 136,
    "PORYGON": 137,
    "OMANYTE": 138,   "OMASTAR": 139,
    "KABUTO": 140,    "KABUTOPS": 141,
    "AERODACTYL": 142,
    "SNORLAX": 143,
    "ARTICUNO": 144,  "ZAPDOS": 145,   "MOLTRES": 146,
    "DRATINI": 147,   "DRAGONAIR": 148, "DRAGONITE": 149,
    "MEWTWO": 150,
    "MEW": 151,
}

# Reverse: dex number → ASM constant name
POKEMON_CONST_NAMES = {v: k for k, v in POKEMON_CONSTANTS.items()}

# Display name (uppercase) derived from POKEMON_NAMES
POKEMON_DISPLAY_NAME = {
    const: POKEMON_NAMES[dex].upper()
    for const, dex in POKEMON_CONSTANTS.items()
}

# ── Species sets ──────────────────────────────────────────────────────────────
LEGENDARY_IDS = frozenset({144, 145, 146, 150, 151})  # Articuno/Zapdos/Moltres/Mewtwo/Mew

# Middle stage of a 3-stage Gen 1 evolution line
MIDDLE_STAGE_IDS = frozenset({
    2,   # Ivysaur    (Bulbasaur→Ivysaur→Venusaur)
    5,   # Charmeleon
    8,   # Wartortle
    11,  # Metapod
    14,  # Kakuna
    17,  # Pidgeotto
    30,  # Nidorina
    33,  # Nidorino
    44,  # Gloom
    61,  # Poliwhirl
    64,  # Kadabra
    67,  # Machoke
    70,  # Weepinbell
    75,  # Graveler
    93,  # Haunter
    148, # Dragonair
})

# First-stage Pokémon that have TWO further evolutions (3-stage Gen 1 lines)
BASIC_WITH_TWO_EVOLUTIONS = frozenset({
    1,   # Bulbasaur   → Ivysaur     → Venusaur
    4,   # Charmander  → Charmeleon  → Charizard
    7,   # Squirtle    → Wartortle   → Blastoise
    10,  # Caterpie    → Metapod     → Butterfree
    13,  # Weedle      → Kakuna      → Beedrill
    16,  # Pidgey      → Pidgeotto   → Pidgeot
    29,  # Nidoran-F   → Nidorina    → Nidoqueen
    32,  # Nidoran-M   → Nidorino    → Nidoking
    43,  # Oddish      → Gloom       → Vileplume
    60,  # Poliwag     → Poliwhirl   → Poliwrath
    63,  # Abra        → Kadabra     → Alakazam
    66,  # Machop      → Machoke     → Machamp
    69,  # Bellsprout  → Weepinbell  → Victreebel
    74,  # Geodude     → Graveler    → Golem
    92,  # Gastly      → Haunter     → Gengar
    147, # Dratini     → Dragonair   → Dragonite
})

# ── Primary type for every Gen 1 Pokémon (used in starter dialogue) ───────────
POKEMON_PRIMARY_TYPE = {
    "BULBASAUR": "grass",    "IVYSAUR": "grass",      "VENUSAUR": "grass",
    "CHARMANDER": "fire",    "CHARMELEON": "fire",    "CHARIZARD": "fire",
    "SQUIRTLE": "water",     "WARTORTLE": "water",    "BLASTOISE": "water",
    "CATERPIE": "bug",       "METAPOD": "bug",        "BUTTERFREE": "bug",
    "WEEDLE": "bug",         "KAKUNA": "bug",         "BEEDRILL": "bug",
    "PIDGEY": "normal",      "PIDGEOTTO": "normal",   "PIDGEOT": "normal",
    "RATTATA": "normal",     "RATICATE": "normal",
    "SPEAROW": "normal",     "FEAROW": "normal",
    "EKANS": "poison",       "ARBOK": "poison",
    "PIKACHU": "electric",   "RAICHU": "electric",
    "SANDSHREW": "ground",   "SANDSLASH": "ground",
    "NIDORAN_F": "poison",   "NIDORINA": "poison",    "NIDOQUEEN": "poison",
    "NIDORAN_M": "poison",   "NIDORINO": "poison",    "NIDOKING": "poison",
    "CLEFAIRY": "normal",    "CLEFABLE": "normal",
    "VULPIX": "fire",        "NINETALES": "fire",
    "JIGGLYPUFF": "normal",  "WIGGLYTUFF": "normal",
    "ZUBAT": "poison",       "GOLBAT": "poison",
    "ODDISH": "grass",       "GLOOM": "grass",        "VILEPLUME": "grass",
    "PARAS": "bug",          "PARASECT": "bug",
    "VENONAT": "bug",        "VENOMOTH": "bug",
    "DIGLETT": "ground",     "DUGTRIO": "ground",
    "MEOWTH": "normal",      "PERSIAN": "normal",
    "PSYDUCK": "water",      "GOLDUCK": "water",
    "MANKEY": "fighting",    "PRIMEAPE": "fighting",
    "GROWLITHE": "fire",     "ARCANINE": "fire",
    "POLIWAG": "water",      "POLIWHIRL": "water",    "POLIWRATH": "water",
    "ABRA": "psychic",       "KADABRA": "psychic",    "ALAKAZAM": "psychic",
    "MACHOP": "fighting",    "MACHOKE": "fighting",   "MACHAMP": "fighting",
    "BELLSPROUT": "grass",   "WEEPINBELL": "grass",   "VICTREEBEL": "grass",
    "TENTACOOL": "water",    "TENTACRUEL": "water",
    "GEODUDE": "rock",       "GRAVELER": "rock",      "GOLEM": "rock",
    "PONYTA": "fire",        "RAPIDASH": "fire",
    "SLOWPOKE": "water",     "SLOWBRO": "water",
    "MAGNEMITE": "electric", "MAGNETON": "electric",
    "FARFETCHD": "normal",
    "DODUO": "normal",       "DODRIO": "normal",
    "SEEL": "water",         "DEWGONG": "water",
    "GRIMER": "poison",      "MUK": "poison",
    "SHELLDER": "water",     "CLOYSTER": "water",
    "GASTLY": "ghost",       "HAUNTER": "ghost",      "GENGAR": "ghost",
    "ONIX": "rock",
    "DROWZEE": "psychic",    "HYPNO": "psychic",
    "KRABBY": "water",       "KINGLER": "water",
    "VOLTORB": "electric",   "ELECTRODE": "electric",
    "EXEGGCUTE": "grass",    "EXEGGUTOR": "grass",
    "CUBONE": "ground",      "MAROWAK": "ground",
    "HITMONLEE": "fighting", "HITMONCHAN": "fighting",
    "LICKITUNG": "normal",
    "KOFFING": "poison",     "WEEZING": "poison",
    "RHYHORN": "ground",     "RHYDON": "ground",
    "CHANSEY": "normal",
    "TANGELA": "grass",
    "KANGASKHAN": "normal",
    "HORSEA": "water",       "SEADRA": "water",
    "GOLDEEN": "water",      "SEAKING": "water",
    "STARYU": "water",       "STARMIE": "water",
    "MR_MIME": "psychic",
    "SCYTHER": "bug",
    "JYNX": "ice",
    "ELECTABUZZ": "electric",
    "MAGMAR": "fire",
    "PINSIR": "bug",
    "TAUROS": "normal",
    "MAGIKARP": "water",     "GYARADOS": "water",
    "LAPRAS": "water",
    "DITTO": "normal",
    "EEVEE": "normal",       "VAPOREON": "water",     "JOLTEON": "electric",
    "FLAREON": "fire",
    "PORYGON": "normal",
    "OMANYTE": "rock",       "OMASTAR": "rock",
    "KABUTO": "rock",        "KABUTOPS": "rock",
    "AERODACTYL": "rock",
    "SNORLAX": "normal",
    "ARTICUNO": "ice",       "ZAPDOS": "electric",    "MOLTRES": "fire",
    "DRATINI": "dragon",     "DRAGONAIR": "dragon",   "DRAGONITE": "dragon",
    "MEWTWO": "psychic",
    "MEW": "psychic",
}

# ── Starter constants ─────────────────────────────────────────────────────────
DEFAULT_STARTERS = [1, 4, 7]  # Bulbasaur, Charmander, Squirtle (by dex number)
STARTER_CONSTANTS = ["BULBASAUR", "CHARMANDER", "SQUIRTLE"]

# ── Gen 1 scrambled internal ID mapping ──────────────────────────────────────
# Yellow internal IDs differ from dex numbers (e.g. Bulbasaur=$99, not $01).
# Used by writer_yellow.py to write raw Pokémon data (PC Pokémon injection).
YELLOW_INTERNAL_ID = {
    "RHYDON": 0x01,      "KANGASKHAN": 0x02,  "NIDORAN_M": 0x03,
    "CLEFAIRY": 0x04,    "SPEAROW": 0x05,     "VOLTORB": 0x06,
    "NIDOKING": 0x07,    "SLOWBRO": 0x08,     "IVYSAUR": 0x09,
    "EXEGGUTOR": 0x0A,   "LICKITUNG": 0x0B,   "EXEGGCUTE": 0x0C,
    "GRIMER": 0x0D,      "GENGAR": 0x0E,      "NIDORAN_F": 0x0F,
    "NIDOQUEEN": 0x10,   "CUBONE": 0x11,      "RHYHORN": 0x12,
    "LAPRAS": 0x13,      "ARCANINE": 0x14,    "MEW": 0x15,
    "GYARADOS": 0x16,    "SHELLDER": 0x17,    "TENTACOOL": 0x18,
    "GASTLY": 0x19,      "SCYTHER": 0x1A,     "STARYU": 0x1B,
    "BLASTOISE": 0x1C,   "PINSIR": 0x1D,      "TANGELA": 0x1E,
    "GROWLITHE": 0x21,   "ONIX": 0x22,        "FEAROW": 0x23,
    "PIDGEY": 0x24,      "SLOWPOKE": 0x25,    "KADABRA": 0x26,
    "GRAVELER": 0x27,    "CHANSEY": 0x28,     "MACHOKE": 0x29,
    "MR_MIME": 0x2A,     "HITMONLEE": 0x2B,   "HITMONCHAN": 0x2C,
    "ARBOK": 0x2D,       "PARASECT": 0x2E,    "PSYDUCK": 0x2F,
    "DROWZEE": 0x30,     "GOLEM": 0x31,       "MAGMAR": 0x33,
    "ELECTABUZZ": 0x35,  "MAGNETON": 0x36,    "KOFFING": 0x37,
    "MANKEY": 0x39,      "SEEL": 0x3A,        "DIGLETT": 0x3B,
    "TAUROS": 0x3C,      "FARFETCHD": 0x40,   "VENONAT": 0x41,
    "DRAGONITE": 0x42,   "DODUO": 0x46,       "POLIWAG": 0x47,
    "JYNX": 0x48,        "MOLTRES": 0x49,     "ARTICUNO": 0x4A,
    "ZAPDOS": 0x4B,      "DITTO": 0x4C,       "MEOWTH": 0x4D,
    "KRABBY": 0x4E,      "VULPIX": 0x52,      "NINETALES": 0x53,
    "PIKACHU": 0x54,     "RAICHU": 0x55,      "DRATINI": 0x58,
    "DRAGONAIR": 0x59,   "KABUTO": 0x5A,      "KABUTOPS": 0x5B,
    "HORSEA": 0x5C,      "SEADRA": 0x5D,      "SANDSHREW": 0x60,
    "SANDSLASH": 0x61,   "OMANYTE": 0x62,     "OMASTAR": 0x63,
    "JIGGLYPUFF": 0x64,  "WIGGLYTUFF": 0x65,  "EEVEE": 0x66,
    "FLAREON": 0x67,     "JOLTEON": 0x68,     "VAPOREON": 0x69,
    "MACHOP": 0x6A,      "ZUBAT": 0x6B,       "EKANS": 0x6C,
    "PARAS": 0x6D,       "POLIWHIRL": 0x6E,   "POLIWRATH": 0x6F,
    "WEEDLE": 0x70,      "KAKUNA": 0x71,      "BEEDRILL": 0x72,
    "DODRIO": 0x74,      "PRIMEAPE": 0x75,    "DUGTRIO": 0x76,
    "VENOMOTH": 0x77,    "DEWGONG": 0x78,     "CATERPIE": 0x7B,
    "METAPOD": 0x7C,     "BUTTERFREE": 0x7D,  "MACHAMP": 0x7E,
    "GOLDUCK": 0x80,     "HYPNO": 0x81,       "GOLBAT": 0x82,
    "MEWTWO": 0x83,      "SNORLAX": 0x84,     "MAGIKARP": 0x85,
    "MUK": 0x88,         "KINGLER": 0x8A,     "CLOYSTER": 0x8B,
    "ELECTRODE": 0x8D,   "CLEFABLE": 0x8E,    "WEEZING": 0x8F,
    "PERSIAN": 0x90,     "MAROWAK": 0x91,     "HAUNTER": 0x93,
    "ABRA": 0x94,        "ALAKAZAM": 0x95,    "PIDGEOTTO": 0x96,
    "PIDGEOT": 0x97,     "STARMIE": 0x98,     "BULBASAUR": 0x99,
    "VENUSAUR": 0x9A,    "TENTACRUEL": 0x9B,  "GOLDEEN": 0x9D,
    "SEAKING": 0x9E,     "PONYTA": 0xA3,      "RAPIDASH": 0xA4,
    "RATTATA": 0xA5,     "RATICATE": 0xA6,    "NIDORINO": 0xA7,
    "NIDORINA": 0xA8,    "GEODUDE": 0xA9,     "PORYGON": 0xAA,
    "AERODACTYL": 0xAB,  "MAGNEMITE": 0xAD,   "CHARMANDER": 0xB0,
    "SQUIRTLE": 0xB1,    "CHARMELEON": 0xB2,  "WARTORTLE": 0xB3,
    "CHARIZARD": 0xB4,   "ODDISH": 0xB9,      "GLOOM": 0xBA,
    "VILEPLUME": 0xBB,   "BELLSPROUT": 0xBC,  "WEEPINBELL": 0xBD,
    "VICTREEBEL": 0xBE,
}

# Reverse: dex number → internal ID
YELLOW_INTERNAL_ID_BY_DEX = {
    POKEMON_CONSTANTS[const]: iid
    for const, iid in YELLOW_INTERNAL_ID.items()
    if const in POKEMON_CONSTANTS
}

# ── Source file paths (relative to Yellow source root) ────────────────────────
WILD_MAPS_DIR            = "data/wild/maps"          # *.asm files in this dir
WILD_OLD_ROD_FILE        = "data/wild/old_rod.asm"
WILD_GOOD_ROD_FILE       = "data/wild/good_rod.asm"
WILD_SUPER_ROD_FILE      = "data/wild/super_rod.asm"
TRAINER_PARTIES_FILE     = "data/trainers/parties.asm"
EVOLUTION_DATA_FILE      = "data/pokemon/evos_moves.asm"
HIDDEN_OBJECTS_FILE      = "data/events/hidden_objects.asm"
TRADES_FILE              = "data/events/trades.asm"
BASE_STATS_DIR           = "data/pokemon/base_stats"  # *.asm files, one per species
INIT_PLAYER_DATA_FILE    = "engine/movie/oak_speech/init_player_data.asm"
PRICES_FILE              = "data/items/prices.asm"

# Starter gift files (BULBASAUR, CHARMANDER, SQUIRTLE)
STARTER_FILES = {
    "BULBASAUR":   "scripts/CeruleanMelaniesHouse.asm",
    "CHARMANDER":  "scripts/Route24.asm",
    "SQUIRTLE":    "scripts/VermilionCity_2.asm",
}

# Static encounter script files (Snorlax battles + gift Pokémon)
STATIC_ENCOUNTER_FILES = {
    # Scripted wild battles (wCurOpponent pattern)
    "scripts/Route12.asm",
    "scripts/Route16.asm",
    # Gift Pokémon (lb bc / call GivePokemon pattern)
    "scripts/SilphCo7F.asm",             # Lapras
    "scripts/CeladonMansionRoofHouse.asm",  # Eevee
    "scripts/FuchsiaGoodRodHouse.asm",   # Kabuto or Omanyte
    "scripts/MtMoonPokecenter_2.asm",    # Magikarp
    # Starter-style gift Pokémon (folded into static randomization)
    "scripts/Route24.asm",               # Charmander
    "scripts/CeruleanMelaniesHouse.asm", # Bulbasaur
    "scripts/VermilionCity_2.asm",       # Squirtle
}

# Shop scripts for Zero Grinding / Elite 4 Prep
VIRIDIAN_MART_FILE       = "scripts/ViridianMart.asm"
INDIGO_PLATEAU_LOBBY_FILE = "scripts/IndigoPlateauLobby.asm"

# Gen 1 HM constants (5 HMs, no Whirlpool/Waterfall)
YELLOW_HM_CONSTS = {"HM_CUT", "HM_FLY", "HM_SURF", "HM_STRENGTH", "HM_FLASH"}
