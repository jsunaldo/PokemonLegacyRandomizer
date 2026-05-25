"""
Pokemon Crystal Legacy Randomizer - Constants
Pokemon names, move names, and ASM constant mappings for Gen 1+2 (251 Pokemon).
"""

# Pokemon names indexed 1-251 (index 0 is placeholder)
POKEMON_NAMES = [
    None,
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
    # Gen 2 (152-251)
    "Chikorita", "Bayleef", "Meganium",
    "Cyndaquil", "Quilava", "Typhlosion",
    "Totodile", "Croconaw", "Feraligatr",
    "Sentret", "Furret",
    "Hoothoot", "Noctowl",
    "Ledyba", "Ledian",
    "Spinarak", "Ariados",
    "Crobat",
    "Chinchou", "Lanturn",
    "Pichu",
    "Cleffa",
    "Igglybuff",
    "Togepi", "Togetic",
    "Natu", "Xatu",
    "Mareep", "Flaaffy", "Ampharos",
    "Bellossom",
    "Marill", "Azumarill",
    "Sudowoodo",
    "Politoed",
    "Hoppip", "Skiploom", "Jumpluff",
    "Aipom",
    "Sunkern", "Sunflora",
    "Yanma",
    "Wooper", "Quagsire",
    "Espeon", "Umbreon",
    "Murkrow",
    "Slowking",
    "Misdreavus",
    "Unown",
    "Wobbuffet",
    "Girafarig",
    "Pineco", "Forretress",
    "Dunsparce",
    "Gligar",
    "Steelix",
    "Snubbull", "Granbull",
    "Qwilfish",
    "Scizor",
    "Shuckle",
    "Heracross",
    "Sneasel",
    "Teddiursa", "Ursaring",
    "Slugma", "Magcargo",
    "Swinub", "Piloswine",
    "Corsola",
    "Remoraid", "Octillery",
    "Delibird",
    "Mantine",
    "Skarmory",
    "Houndour", "Houndoom",
    "Kingdra",
    "Phanpy", "Donphan",
    "Porygon2",
    "Stantler",
    "Smeargle",
    "Tyrogue",
    "Hitmontop",
    "Smoochum",
    "Elekid",
    "Magby",
    "Miltank",
    "Blissey",
    "Raikou", "Entei", "Suicune",
    "Larvitar", "Pupitar", "Tyranitar",
    "Lugia",
    "Ho-Oh",
    "Celebi",
]

# ASM constant name -> pokedex number (uppercase, special chars replaced)
POKEMON_CONSTANTS = {
    "BULBASAUR": 1, "IVYSAUR": 2, "VENUSAUR": 3,
    "CHARMANDER": 4, "CHARMELEON": 5, "CHARIZARD": 6,
    "SQUIRTLE": 7, "WARTORTLE": 8, "BLASTOISE": 9,
    "CATERPIE": 10, "METAPOD": 11, "BUTTERFREE": 12,
    "WEEDLE": 13, "KAKUNA": 14, "BEEDRILL": 15,
    "PIDGEY": 16, "PIDGEOTTO": 17, "PIDGEOT": 18,
    "RATTATA": 19, "RATICATE": 20,
    "SPEAROW": 21, "FEAROW": 22,
    "EKANS": 23, "ARBOK": 24,
    "PIKACHU": 25, "RAICHU": 26,
    "SANDSHREW": 27, "SANDSLASH": 28,
    "NIDORAN_F": 29, "NIDORINA": 30, "NIDOQUEEN": 31,
    "NIDORAN_M": 32, "NIDORINO": 33, "NIDOKING": 34,
    "CLEFAIRY": 35, "CLEFABLE": 36,
    "VULPIX": 37, "NINETALES": 38,
    "JIGGLYPUFF": 39, "WIGGLYTUFF": 40,
    "ZUBAT": 41, "GOLBAT": 42,
    "ODDISH": 43, "GLOOM": 44, "VILEPLUME": 45,
    "PARAS": 46, "PARASECT": 47,
    "VENONAT": 48, "VENOMOTH": 49,
    "DIGLETT": 50, "DUGTRIO": 51,
    "MEOWTH": 52, "PERSIAN": 53,
    "PSYDUCK": 54, "GOLDUCK": 55,
    "MANKEY": 56, "PRIMEAPE": 57,
    "GROWLITHE": 58, "ARCANINE": 59,
    "POLIWAG": 60, "POLIWHIRL": 61, "POLIWRATH": 62,
    "ABRA": 63, "KADABRA": 64, "ALAKAZAM": 65,
    "MACHOP": 66, "MACHOKE": 67, "MACHAMP": 68,
    "BELLSPROUT": 69, "WEEPINBELL": 70, "VICTREEBEL": 71,
    "TENTACOOL": 72, "TENTACRUEL": 73,
    "GEODUDE": 74, "GRAVELER": 75, "GOLEM": 76,
    "PONYTA": 77, "RAPIDASH": 78,
    "SLOWPOKE": 79, "SLOWBRO": 80,
    "MAGNEMITE": 81, "MAGNETON": 82,
    "FARFETCH_D": 83,
    "DODUO": 84, "DODRIO": 85,
    "SEEL": 86, "DEWGONG": 87,
    "GRIMER": 88, "MUK": 89,
    "SHELLDER": 90, "CLOYSTER": 91,
    "GASTLY": 92, "HAUNTER": 93, "GENGAR": 94,
    "ONIX": 95,
    "DROWZEE": 96, "HYPNO": 97,
    "KRABBY": 98, "KINGLER": 99,
    "VOLTORB": 100, "ELECTRODE": 101,
    "EXEGGCUTE": 102, "EXEGGUTOR": 103,
    "CUBONE": 104, "MAROWAK": 105,
    "HITMONLEE": 106, "HITMONCHAN": 107,
    "LICKITUNG": 108,
    "KOFFING": 109, "WEEZING": 110,
    "RHYHORN": 111, "RHYDON": 112,
    "CHANSEY": 113,
    "TANGELA": 114,
    "KANGASKHAN": 115,
    "HORSEA": 116, "SEADRA": 117,
    "GOLDEEN": 118, "SEAKING": 119,
    "STARYU": 120, "STARMIE": 121,
    "MR__MIME": 122,
    "SCYTHER": 123,
    "JYNX": 124,
    "ELECTABUZZ": 125,
    "MAGMAR": 126,
    "PINSIR": 127,
    "TAUROS": 128,
    "MAGIKARP": 129, "GYARADOS": 130,
    "LAPRAS": 131,
    "DITTO": 132,
    "EEVEE": 133, "VAPOREON": 134, "JOLTEON": 135, "FLAREON": 136,
    "PORYGON": 137,
    "OMANYTE": 138, "OMASTAR": 139,
    "KABUTO": 140, "KABUTOPS": 141,
    "AERODACTYL": 142,
    "SNORLAX": 143,
    "ARTICUNO": 144, "ZAPDOS": 145, "MOLTRES": 146,
    "DRATINI": 147, "DRAGONAIR": 148, "DRAGONITE": 149,
    "MEWTWO": 150,
    "MEW": 151,
    "CHIKORITA": 152, "BAYLEEF": 153, "MEGANIUM": 154,
    "CYNDAQUIL": 155, "QUILAVA": 156, "TYPHLOSION": 157,
    "TOTODILE": 158, "CROCONAW": 159, "FERALIGATR": 160,
    "SENTRET": 161, "FURRET": 162,
    "HOOTHOOT": 163, "NOCTOWL": 164,
    "LEDYBA": 165, "LEDIAN": 166,
    "SPINARAK": 167, "ARIADOS": 168,
    "CROBAT": 169,
    "CHINCHOU": 170, "LANTURN": 171,
    "PICHU": 172,
    "CLEFFA": 173,
    "IGGLYBUFF": 174,
    "TOGEPI": 175, "TOGETIC": 176,
    "NATU": 177, "XATU": 178,
    "MAREEP": 179, "FLAAFFY": 180, "AMPHAROS": 181,
    "BELLOSSOM": 182,
    "MARILL": 183, "AZUMARILL": 184,
    "SUDOWOODO": 185,
    "POLITOED": 186,
    "HOPPIP": 187, "SKIPLOOM": 188, "JUMPLUFF": 189,
    "AIPOM": 190,
    "SUNKERN": 191, "SUNFLORA": 192,
    "YANMA": 193,
    "WOOPER": 194, "QUAGSIRE": 195,
    "ESPEON": 196, "UMBREON": 197,
    "MURKROW": 198,
    "SLOWKING": 199,
    "MISDREAVUS": 200,
    "UNOWN": 201,
    "WOBBUFFET": 202,
    "GIRAFARIG": 203,
    "PINECO": 204, "FORRETRESS": 205,
    "DUNSPARCE": 206,
    "GLIGAR": 207,
    "STEELIX": 208,
    "SNUBBULL": 209, "GRANBULL": 210,
    "QWILFISH": 211,
    "SCIZOR": 212,
    "SHUCKLE": 213,
    "HERACROSS": 214,
    "SNEASEL": 215,
    "TEDDIURSA": 216, "URSARING": 217,
    "SLUGMA": 218, "MAGCARGO": 219,
    "SWINUB": 220, "PILOSWINE": 221,
    "CORSOLA": 222,
    "REMORAID": 223, "OCTILLERY": 224,
    "DELIBIRD": 225,
    "MANTINE": 226,
    "SKARMORY": 227,
    "HOUNDOUR": 228, "HOUNDOOM": 229,
    "KINGDRA": 230,
    "PHANPY": 231, "DONPHAN": 232,
    "PORYGON2": 233,
    "STANTLER": 234,
    "SMEARGLE": 235,
    "TYROGUE": 236,
    "HITMONTOP": 237,
    "SMOOCHUM": 238,
    "ELEKID": 239,
    "MAGBY": 240,
    "MILTANK": 241,
    "BLISSEY": 242,
    "RAIKOU": 243, "ENTEI": 244, "SUICUNE": 245,
    "LARVITAR": 246, "PUPITAR": 247, "TYRANITAR": 248,
    "LUGIA": 249,
    "HO_OH": 250,
    "CELEBI": 251,
}

# Reverse: dex number -> ASM constant name
POKEMON_CONST_NAMES = {v: k for k, v in POKEMON_CONSTANTS.items()}

# Pokemon that are legendaries (excluded by default from randomization pools)
LEGENDARY_IDS = {144, 145, 146, 150, 151, 243, 244, 245, 249, 250, 251}

# Baby Pokemon (pre-evolutions that are often excluded)
BABY_IDS = {172, 173, 174, 236, 238, 239, 240}

# Default Crystal Legacy starters
DEFAULT_STARTERS = [155, 158, 152]  # Cyndaquil, Totodile, Chikorita

# Trainer type flags (Crystal Legacy extended set)
TRAINERTYPE_NORMAL     = 0x00
TRAINERTYPE_MOVES      = 0x01
TRAINERTYPE_ITEM       = 0x02
TRAINERTYPE_ITEM_MOVES = 0x03
TRAINERTYPE_NICKNAME   = 0x04  # Crystal Legacy addition
TRAINERTYPE_DVS        = 0x08  # Crystal Legacy addition
TRAINERTYPE_STAT_EXP   = 0x10  # Crystal Legacy addition
TRAINERTYPE_VARIABLE   = 0x20  # Crystal Legacy addition
TRAINERTYPE_HAPPINESS  = 0x40  # Crystal Legacy addition

TRAINERTYPE_NAMES = {
    "TRAINERTYPE_NORMAL":     TRAINERTYPE_NORMAL,
    "TRAINERTYPE_MOVES":      TRAINERTYPE_MOVES,
    "TRAINERTYPE_ITEM":       TRAINERTYPE_ITEM,
    "TRAINERTYPE_ITEM_MOVES": TRAINERTYPE_ITEM_MOVES,
    "TRAINERTYPE_NICKNAME":   TRAINERTYPE_NICKNAME,
    "TRAINERTYPE_DVS":        TRAINERTYPE_DVS,
    "TRAINERTYPE_STAT_EXP":   TRAINERTYPE_STAT_EXP,
    "TRAINERTYPE_VARIABLE":   TRAINERTYPE_VARIABLE,
    "TRAINERTYPE_HAPPINESS":  TRAINERTYPE_HAPPINESS,
}

# Wild encounter file paths relative to source root
WILD_ENCOUNTER_FILES = [
    "data/wild/johto_grass.asm",
    "data/wild/johto_water.asm",
    "data/wild/kanto_grass.asm",
    "data/wild/kanto_water.asm",
    "data/wild/fish.asm",
    "data/wild/treemons.asm",
    "data/wild/bug_contest_mons.asm",
    "data/wild/swarm_grass.asm",
    "data/wild/swarm_water.asm",
]

TRAINER_PARTIES_FILE = "data/trainers/parties.asm"

# Evolution data file (candidate paths, tried in order)
EVOLUTION_DATA_FILE_CANDIDATES = [
    "data/pokemon/evos_attacks.asm",
    "data/evos_attacks.asm",
    "data/pokemon/evolutions.asm",
]

# Starter search candidates (in priority order)
STARTER_FILE_CANDIDATES = [
    "maps/ElmsLab.asm",                       # Crystal Legacy
    "engine/overworld/choose_starter.asm",
    "engine/events/choose_starter.asm",
    "engine/menus/choose_starter.asm",
    "engine/overworld/elm.asm",
]

# Known starter constants (default Crystal)
STARTER_CONSTANTS = ["CYNDAQUIL", "TOTODILE", "CHIKORITA"]

# Pokemon that are the MIDDLE stage of a 3-stage evolution line.
# Used by the "Make Evolutions Easier" feature to determine the correct
# level cap: middle-stage targets → level 30, final-stage targets → level 40.
# Covers all Gen 1+2 three-stage lines available in Crystal.
MIDDLE_STAGE_IDS = frozenset({
    # Gen 1
    2,   # Ivysaur    (Bulbasaur→Ivysaur→Venusaur)
    5,   # Charmeleon
    8,   # Wartortle
    11,  # Metapod
    14,  # Kakuna
    17,  # Pidgeotto
    25,  # Pikachu    (Pichu→Pikachu→Raichu)
    30,  # Nidorina
    33,  # Nidorino
    35,  # Clefairy   (Cleffa→Clefairy→Clefable)
    39,  # Jigglypuff (Igglybuff→Jigglypuff→Wigglytuff)
    42,  # Golbat     (Zubat→Golbat→Crobat)
    44,  # Gloom      (Oddish→Gloom→Vileplume/Bellossom)
    61,  # Poliwhirl  (Poliwag→Poliwhirl→Poliwrath/Politoed)
    64,  # Kadabra
    67,  # Machoke
    70,  # Weepinbell
    75,  # Graveler
    93,  # Haunter
    117, # Seadra     (Horsea→Seadra→Kingdra)
    148, # Dragonair
    # Gen 2
    153, # Bayleef
    156, # Quilava
    159, # Croconaw
    180, # Flaaffy    (Mareep→Flaaffy→Ampharos)
    188, # Skiploom   (Hoppip→Skiploom→Jumpluff)
    247, # Pupitar    (Larvitar→Pupitar→Tyranitar)
})

# Basic (first-stage) Pokemon that belong to a 3-stage evolution line.
# These are valid "starter-feel" picks for the random_two_stage mode.
# Verified against all Gen 1+2 evolution chains available in Crystal.
# ─────────────────────────────────────────────────────────────────────────────
# Primary type for every Gen 1+2 Pokémon (used in starter dialogue text)
# Key: ASM constant name   Value: lowercase type string for in-game text
# ─────────────────────────────────────────────────────────────────────────────
POKEMON_PRIMARY_TYPE = {
    # Gen 1 — 001-151
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
    "FARFETCH_D": "normal",
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
    "MR__MIME": "psychic",
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
    # Gen 2 — 152-251
    "CHIKORITA": "grass",    "BAYLEEF": "grass",      "MEGANIUM": "grass",
    "CYNDAQUIL": "fire",     "QUILAVA": "fire",       "TYPHLOSION": "fire",
    "TOTODILE": "water",     "CROCONAW": "water",     "FERALIGATR": "water",
    "SENTRET": "normal",     "FURRET": "normal",
    "HOOTHOOT": "normal",    "NOCTOWL": "normal",
    "LEDYBA": "bug",         "LEDIAN": "bug",
    "SPINARAK": "bug",       "ARIADOS": "bug",
    "CROBAT": "poison",
    "CHINCHOU": "water",     "LANTURN": "water",
    "PICHU": "electric",
    "CLEFFA": "normal",
    "IGGLYBUFF": "normal",
    "TOGEPI": "normal",      "TOGETIC": "normal",
    "NATU": "psychic",       "XATU": "psychic",
    "MAREEP": "electric",    "FLAAFFY": "electric",   "AMPHAROS": "electric",
    "BELLOSSOM": "grass",
    "MARILL": "water",       "AZUMARILL": "water",
    "SUDOWOODO": "rock",
    "POLITOED": "water",
    "HOPPIP": "grass",       "SKIPLOOM": "grass",     "JUMPLUFF": "grass",
    "AIPOM": "normal",
    "SUNKERN": "grass",      "SUNFLORA": "grass",
    "YANMA": "bug",
    "WOOPER": "water",       "QUAGSIRE": "water",
    "ESPEON": "psychic",     "UMBREON": "dark",
    "MURKROW": "dark",
    "SLOWKING": "water",
    "MISDREAVUS": "ghost",
    "UNOWN": "psychic",
    "WOBBUFFET": "psychic",
    "GIRAFARIG": "normal",
    "PINECO": "bug",         "FORRETRESS": "bug",
    "DUNSPARCE": "normal",
    "GLIGAR": "ground",
    "STEELIX": "steel",
    "SNUBBULL": "normal",    "GRANBULL": "normal",
    "QWILFISH": "water",
    "SCIZOR": "bug",
    "SHUCKLE": "bug",
    "HERACROSS": "bug",
    "SNEASEL": "dark",
    "TEDDIURSA": "normal",   "URSARING": "normal",
    "SLUGMA": "fire",        "MAGCARGO": "fire",
    "SWINUB": "ice",         "PILOSWINE": "ice",
    "CORSOLA": "water",
    "REMORAID": "water",     "OCTILLERY": "water",
    "DELIBIRD": "ice",
    "MANTINE": "water",
    "SKARMORY": "steel",
    "HOUNDOUR": "dark",      "HOUNDOOM": "dark",
    "KINGDRA": "water",
    "PHANPY": "ground",      "DONPHAN": "ground",
    "PORYGON2": "normal",
    "STANTLER": "normal",
    "SMEARGLE": "normal",
    "TYROGUE": "fighting",   "HITMONTOP": "fighting",
    "SMOOCHUM": "ice",
    "ELEKID": "electric",
    "MAGBY": "fire",
    "MILTANK": "normal",
    "BLISSEY": "normal",
    "RAIKOU": "electric",    "ENTEI": "fire",         "SUICUNE": "water",
    "LARVITAR": "rock",      "PUPITAR": "rock",       "TYRANITAR": "rock",
    "LUGIA": "psychic",
    "HO_OH": "fire",
    "CELEBI": "psychic",
}

# Display name for each species in dialogue text (uppercase, as shown in game).
# Derived from POKEMON_NAMES; special chars preserved (apostrophe, hyphen, period).
POKEMON_DISPLAY_NAME = {
    const: POKEMON_NAMES[dex_num].upper()
    for const, dex_num in POKEMON_CONSTANTS.items()
}

BASIC_WITH_TWO_EVOLUTIONS = {
    # Gen 1
    1,   # Bulbasaur   → Ivysaur     → Venusaur
    4,   # Charmander  → Charmeleon  → Charizard
    7,   # Squirtle    → Wartortle   → Blastoise
    10,  # Caterpie    → Metapod     → Butterfree
    13,  # Weedle      → Kakuna      → Beedrill
    29,  # Nidoran-F   → Nidorina    → Nidoqueen
    32,  # Nidoran-M   → Nidorino    → Nidoking
    41,  # Zubat       → Golbat      → Crobat
    43,  # Oddish      → Gloom       → Vileplume/Bellossom
    60,  # Poliwag     → Poliwhirl   → Poliwrath/Politoed
    63,  # Abra        → Kadabra     → Alakazam
    66,  # Machop      → Machoke     → Machamp
    69,  # Bellsprout  → Weepinbell  → Victreebel
    74,  # Geodude     → Graveler    → Golem
    92,  # Gastly      → Haunter     → Gengar
    116, # Horsea      → Seadra      → Kingdra
    147, # Dratini     → Dragonair   → Dragonite
    # Gen 2
    152, # Chikorita   → Bayleef     → Meganium
    155, # Cyndaquil   → Quilava     → Typhlosion
    158, # Totodile    → Croconaw    → Feraligatr
    172, # Pichu       → Pikachu     → Raichu
    173, # Cleffa      → Clefairy    → Clefable
    174, # Igglybuff   → Jigglypuff  → Wigglytuff
    179, # Mareep      → Flaaffy     → Ampharos
    187, # Hoppip      → Skiploom    → Jumpluff
    246, # Larvitar    → Pupitar     → Tyranitar
}
