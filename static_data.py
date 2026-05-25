"""
Static encounter data for Pokemon Crystal Legacy.

Static encounters are Pokemon found at fixed overworld locations —
not in wild grass/water slots, not in trainer parties.
Examples: Red Gyarados, Sudowoodo, Lugia, Ho-Oh, roaming Raikou/Entei,
          gift Pokemon (Eevee, Dratini, fossils), Snorlax, Lapras.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Base Stat Totals for all 251 Pokemon (1-indexed; index 0 is unused padding)
# Values are Gen 2 BSTs (approximate for non-critical entries).
# Legendaries, starters, and pseudo-legendaries are verified accurate.
# ─────────────────────────────────────────────────────────────────────────────
POKEMON_BST = [
    0,   # index 0 — unused
    # Gen 1 (#1 Bulbasaur → #151 Mew)
    318, 405, 525, 309, 405, 534, 314, 405, 530, 195,  #   1- 10
    205, 395, 195, 205, 395, 251, 349, 479, 253, 413,  #  11- 20
    262, 442, 288, 438, 320, 485, 300, 450, 275, 365,  #  21- 30
    505, 273, 365, 505, 323, 473, 299, 505, 270, 435,  #  31- 40
    245, 455, 320, 395, 520, 285, 405, 305, 450, 265,  #  41- 50
    425, 290, 440, 320, 500, 305, 455, 350, 555, 300,  #  51- 60
    385, 510, 310, 400, 500, 305, 405, 505, 300, 390,  #  61- 70
    490, 335, 515, 300, 390, 495, 410, 500, 315, 490,  #  71- 80
    325, 465, 352, 310, 450, 325, 475, 325, 500, 305,  #  81- 90
    525, 310, 405, 500, 385, 328, 483, 325, 475, 330,  #  91-100
    480, 325, 520, 320, 425, 455, 455, 385, 340, 490,  # 101-110
    345, 485, 450, 395, 490, 295, 440, 320, 450, 340,  # 111-120
    520, 460, 500, 360, 490, 495, 500, 490, 200, 540,  # 121-130
    535, 288, 325, 525, 525, 525, 395, 355, 495, 355,  # 131-140
    495, 515, 540, 580, 580, 580, 300, 420, 600, 680,  # 141-150
    600,                                                # 151 Mew
    # Gen 2 (#152 Chikorita → #251 Celebi)
    318, 405, 525, 309, 405, 534, 314, 405, 530, 288,  # 152-161
    415, 262, 452, 265, 390, 270, 390, 535, 330, 460,  # 162-171
    205, 218, 210, 245, 405, 320, 470, 280, 365, 510,  # 172-181
    490, 250, 420, 410, 500, 250, 340, 460, 360, 180,  # 182-191
    425, 390, 210, 430, 525, 525, 405, 490, 355, 336,  # 192-201
    405, 455, 290, 465, 415, 430, 510, 300, 450, 430,  # 202-211
    500, 385, 500, 430, 325, 500, 250, 410, 250, 450,  # 212-221
    410, 330, 480, 330, 485, 465, 330, 500, 540, 330,  # 222-231
    500, 515, 500, 380, 210, 455, 305, 360, 365, 490,  # 232-241
    540, 580, 580, 580, 300, 410, 600, 680, 680, 600,  # 242-251
]

# ─────────────────────────────────────────────────────────────────────────────
# Known static encounter species
# ─────────────────────────────────────────────────────────────────────────────

# Legendary/mythical species that can appear as static encounters
STATIC_LEGENDARY_SPECIES = frozenset({
    "LUGIA", "HO_OH",
    "SUICUNE", "RAIKOU", "ENTEI",
    "CELEBI",
    "ARTICUNO", "ZAPDOS", "MOLTRES",
    "MEWTWO",
    "MEW",        # Crystal Legacy adds Mew on Route 24
})

# Standard (non-legendary) species that appear as static encounters
STATIC_STANDARD_SPECIES = frozenset({
    "GYARADOS",    # Red Gyarados at Lake of Rage
    "SUDOWOODO",
    "LAPRAS",
    "SNORLAX",
    "EEVEE",       # Gift from Bill in Goldenrod
    "DRATINI",     # Gift from Dragon's Den elder
    "TOGEPI",      # Egg from Mr. Pokemon
    "AERODACTYL",  # Old Amber fossil
    "OMANYTE",     # Dome Fossil
    "KABUTO",      # Helix Fossil
    "SHUCKLE",     # Loaned by man in Cianwood
    "ELECTRODE",   # Kanto Power Plant (if static in Crystal Legacy)
    "PORYGON",     # If available as a static gift
})

ALL_STATIC_SPECIES = STATIC_LEGENDARY_SPECIES | STATIC_STANDARD_SPECIES

# ─────────────────────────────────────────────────────────────────────────────
# Pokemon types (Gen 2 / Crystal typings) — used for Type Themed Areas
# Each entry is a tuple of 1 or 2 type strings.
# Clefairy, Marill, Snubbull etc. use their Gen 2 types (pre-Fairy).
# Magnemite/Magneton are Electric/Steel (received Steel type in Gen 2).
# ─────────────────────────────────────────────────────────────────────────────
POKEMON_TYPES = {
    # ── Gen 1 (#1–151) ───────────────────────────────────────────────────────
    1:   ("Grass", "Poison"),    # Bulbasaur
    2:   ("Grass", "Poison"),    # Ivysaur
    3:   ("Grass", "Poison"),    # Venusaur
    4:   ("Fire",),              # Charmander
    5:   ("Fire",),              # Charmeleon
    6:   ("Fire",  "Flying"),    # Charizard
    7:   ("Water",),             # Squirtle
    8:   ("Water",),             # Wartortle
    9:   ("Water",),             # Blastoise
    10:  ("Bug",),               # Caterpie
    11:  ("Bug",),               # Metapod
    12:  ("Bug",  "Flying"),     # Butterfree
    13:  ("Bug",  "Poison"),     # Weedle
    14:  ("Bug",  "Poison"),     # Kakuna
    15:  ("Bug",  "Poison"),     # Beedrill
    16:  ("Normal","Flying"),    # Pidgey
    17:  ("Normal","Flying"),    # Pidgeotto
    18:  ("Normal","Flying"),    # Pidgeot
    19:  ("Normal",),            # Rattata
    20:  ("Normal",),            # Raticate
    21:  ("Normal","Flying"),    # Spearow
    22:  ("Normal","Flying"),    # Fearow
    23:  ("Poison",),            # Ekans
    24:  ("Poison",),            # Arbok
    25:  ("Electric",),          # Pikachu
    26:  ("Electric",),          # Raichu
    27:  ("Ground",),            # Sandshrew
    28:  ("Ground",),            # Sandslash
    29:  ("Poison",),            # Nidoran-F
    30:  ("Poison",),            # Nidorina
    31:  ("Poison","Ground"),    # Nidoqueen
    32:  ("Poison",),            # Nidoran-M
    33:  ("Poison",),            # Nidorino
    34:  ("Poison","Ground"),    # Nidoking
    35:  ("Normal",),            # Clefairy
    36:  ("Normal",),            # Clefable
    37:  ("Fire",),              # Vulpix
    38:  ("Fire",),              # Ninetales
    39:  ("Normal",),            # Jigglypuff
    40:  ("Normal",),            # Wigglytuff
    41:  ("Poison","Flying"),    # Zubat
    42:  ("Poison","Flying"),    # Golbat
    43:  ("Grass", "Poison"),    # Oddish
    44:  ("Grass", "Poison"),    # Gloom
    45:  ("Grass", "Poison"),    # Vileplume
    46:  ("Bug",  "Grass"),      # Paras
    47:  ("Bug",  "Grass"),      # Parasect
    48:  ("Bug",  "Poison"),     # Venonat
    49:  ("Bug",  "Poison"),     # Venomoth
    50:  ("Ground",),            # Diglett
    51:  ("Ground",),            # Dugtrio
    52:  ("Normal",),            # Meowth
    53:  ("Normal",),            # Persian
    54:  ("Water",),             # Psyduck
    55:  ("Water",),             # Golduck
    56:  ("Fighting",),          # Mankey
    57:  ("Fighting",),          # Primeape
    58:  ("Fire",),              # Growlithe
    59:  ("Fire",),              # Arcanine
    60:  ("Water",),             # Poliwag
    61:  ("Water",),             # Poliwhirl
    62:  ("Water","Fighting"),   # Poliwrath
    63:  ("Psychic",),           # Abra
    64:  ("Psychic",),           # Kadabra
    65:  ("Psychic",),           # Alakazam
    66:  ("Fighting",),          # Machop
    67:  ("Fighting",),          # Machoke
    68:  ("Fighting",),          # Machamp
    69:  ("Grass", "Poison"),    # Bellsprout
    70:  ("Grass", "Poison"),    # Weepinbell
    71:  ("Grass", "Poison"),    # Victreebel
    72:  ("Water","Poison"),     # Tentacool
    73:  ("Water","Poison"),     # Tentacruel
    74:  ("Rock", "Ground"),     # Geodude
    75:  ("Rock", "Ground"),     # Graveler
    76:  ("Rock", "Ground"),     # Golem
    77:  ("Fire",),              # Ponyta
    78:  ("Fire",),              # Rapidash
    79:  ("Water","Psychic"),    # Slowpoke
    80:  ("Water","Psychic"),    # Slowbro
    81:  ("Electric","Steel"),   # Magnemite
    82:  ("Electric","Steel"),   # Magneton
    83:  ("Normal","Flying"),    # Farfetch'd
    84:  ("Normal","Flying"),    # Doduo
    85:  ("Normal","Flying"),    # Dodrio
    86:  ("Water",),             # Seel
    87:  ("Water","Ice"),        # Dewgong
    88:  ("Poison",),            # Grimer
    89:  ("Poison",),            # Muk
    90:  ("Water",),             # Shellder
    91:  ("Water","Ice"),        # Cloyster
    92:  ("Ghost","Poison"),     # Gastly
    93:  ("Ghost","Poison"),     # Haunter
    94:  ("Ghost","Poison"),     # Gengar
    95:  ("Rock", "Ground"),     # Onix
    96:  ("Psychic",),           # Drowzee
    97:  ("Psychic",),           # Hypno
    98:  ("Water",),             # Krabby
    99:  ("Water",),             # Kingler
    100: ("Electric",),          # Voltorb
    101: ("Electric",),          # Electrode
    102: ("Grass","Psychic"),    # Exeggcute
    103: ("Grass","Psychic"),    # Exeggutor
    104: ("Ground",),            # Cubone
    105: ("Ground",),            # Marowak
    106: ("Fighting",),          # Hitmonlee
    107: ("Fighting",),          # Hitmonchan
    108: ("Normal",),            # Lickitung
    109: ("Poison",),            # Koffing
    110: ("Poison",),            # Weezing
    111: ("Ground","Rock"),      # Rhyhorn
    112: ("Ground","Rock"),      # Rhydon
    113: ("Normal",),            # Chansey
    114: ("Grass",),             # Tangela
    115: ("Normal",),            # Kangaskhan
    116: ("Water",),             # Horsea
    117: ("Water",),             # Seadra
    118: ("Water",),             # Goldeen
    119: ("Water",),             # Seaking
    120: ("Water",),             # Staryu
    121: ("Water","Psychic"),    # Starmie
    122: ("Psychic",),           # Mr. Mime
    123: ("Bug",  "Flying"),     # Scyther
    124: ("Ice",  "Psychic"),    # Jynx
    125: ("Electric",),          # Electabuzz
    126: ("Fire",),              # Magmar
    127: ("Bug",),               # Pinsir
    128: ("Normal",),            # Tauros
    129: ("Water",),             # Magikarp
    130: ("Water","Flying"),     # Gyarados
    131: ("Water","Ice"),        # Lapras
    132: ("Normal",),            # Ditto
    133: ("Normal",),            # Eevee
    134: ("Water",),             # Vaporeon
    135: ("Electric",),          # Jolteon
    136: ("Fire",),              # Flareon
    137: ("Normal",),            # Porygon
    138: ("Rock", "Water"),      # Omanyte
    139: ("Rock", "Water"),      # Omastar
    140: ("Rock", "Water"),      # Kabuto
    141: ("Rock", "Water"),      # Kabutops
    142: ("Rock", "Flying"),     # Aerodactyl
    143: ("Normal",),            # Snorlax
    144: ("Ice",  "Flying"),     # Articuno
    145: ("Electric","Flying"),  # Zapdos
    146: ("Fire", "Flying"),     # Moltres
    147: ("Dragon",),            # Dratini
    148: ("Dragon",),            # Dragonair
    149: ("Dragon","Flying"),    # Dragonite
    150: ("Psychic",),           # Mewtwo
    151: ("Psychic",),           # Mew
    # ── Gen 2 (#152–251) ─────────────────────────────────────────────────────
    152: ("Grass",),             # Chikorita
    153: ("Grass",),             # Bayleef
    154: ("Grass",),             # Meganium
    155: ("Fire",),              # Cyndaquil
    156: ("Fire",),              # Quilava
    157: ("Fire",),              # Typhlosion
    158: ("Water",),             # Totodile
    159: ("Water",),             # Croconaw
    160: ("Water",),             # Feraligatr
    161: ("Normal",),            # Sentret
    162: ("Normal",),            # Furret
    163: ("Normal","Flying"),    # Hoothoot
    164: ("Normal","Flying"),    # Noctowl
    165: ("Bug",  "Flying"),     # Ledyba
    166: ("Bug",  "Flying"),     # Ledian
    167: ("Bug",  "Poison"),     # Spinarak
    168: ("Bug",  "Poison"),     # Ariados
    169: ("Poison","Flying"),    # Crobat
    170: ("Water","Electric"),   # Chinchou
    171: ("Water","Electric"),   # Lanturn
    172: ("Electric",),          # Pichu
    173: ("Normal",),            # Cleffa
    174: ("Normal",),            # Igglybuff
    175: ("Normal",),            # Togepi
    176: ("Normal","Flying"),    # Togetic
    177: ("Psychic","Flying"),   # Natu
    178: ("Psychic","Flying"),   # Xatu
    179: ("Electric",),          # Mareep
    180: ("Electric",),          # Flaaffy
    181: ("Electric",),          # Ampharos
    182: ("Grass",),             # Bellossom
    183: ("Water",),             # Marill
    184: ("Water",),             # Azumarill
    185: ("Rock",),              # Sudowoodo
    186: ("Water",),             # Politoed
    187: ("Grass","Flying"),     # Hoppip
    188: ("Grass","Flying"),     # Skiploom
    189: ("Grass","Flying"),     # Jumpluff
    190: ("Normal",),            # Aipom
    191: ("Grass",),             # Sunkern
    192: ("Grass",),             # Sunflora
    193: ("Bug",  "Flying"),     # Yanma
    194: ("Water","Ground"),     # Wooper
    195: ("Water","Ground"),     # Quagsire
    196: ("Psychic",),           # Espeon
    197: ("Dark",),              # Umbreon
    198: ("Dark", "Flying"),     # Murkrow
    199: ("Water","Psychic"),    # Slowking
    200: ("Ghost",),             # Misdreavus
    201: ("Psychic",),           # Unown
    202: ("Psychic",),           # Wobbuffet
    203: ("Normal","Psychic"),   # Girafarig
    204: ("Bug",),               # Pineco
    205: ("Bug",  "Steel"),      # Forretress
    206: ("Normal",),            # Dunsparce
    207: ("Ground","Flying"),    # Gligar
    208: ("Steel","Ground"),     # Steelix
    209: ("Normal",),            # Snubbull
    210: ("Normal",),            # Granbull
    211: ("Water","Poison"),     # Qwilfish
    212: ("Bug",  "Steel"),      # Scizor
    213: ("Bug",  "Rock"),       # Shuckle
    214: ("Bug",  "Fighting"),   # Heracross
    215: ("Dark", "Ice"),        # Sneasel
    216: ("Normal",),            # Teddiursa
    217: ("Normal",),            # Ursaring
    218: ("Fire",),              # Slugma
    219: ("Fire", "Rock"),       # Magcargo
    220: ("Ice",  "Ground"),     # Swinub
    221: ("Ice",  "Ground"),     # Piloswine
    222: ("Water","Rock"),       # Corsola
    223: ("Water",),             # Remoraid
    224: ("Water",),             # Octillery
    225: ("Ice",  "Flying"),     # Delibird
    226: ("Water","Flying"),     # Mantine
    227: ("Steel","Flying"),     # Skarmory
    228: ("Dark", "Fire"),       # Houndour
    229: ("Dark", "Fire"),       # Houndoom
    230: ("Water","Dragon"),     # Kingdra
    231: ("Ground",),            # Phanpy
    232: ("Ground",),            # Donphan
    233: ("Normal",),            # Porygon2
    234: ("Normal",),            # Stantler
    235: ("Normal",),            # Smeargle
    236: ("Fighting",),          # Tyrogue
    237: ("Fighting",),          # Hitmontop
    238: ("Ice",  "Psychic"),    # Smoochum
    239: ("Electric",),          # Elekid
    240: ("Fire",),              # Magby
    241: ("Normal",),            # Miltank
    242: ("Normal",),            # Blissey
    243: ("Electric",),          # Raikou
    244: ("Fire",),              # Entei
    245: ("Water",),             # Suicune
    246: ("Rock", "Ground"),     # Larvitar
    247: ("Rock", "Ground"),     # Pupitar
    248: ("Rock", "Dark"),       # Tyranitar
    249: ("Psychic","Flying"),   # Lugia
    250: ("Fire", "Flying"),     # Ho-Oh
    251: ("Psychic","Grass"),    # Celebi
}

# ─────────────────────────────────────────────────────────────────────────────
# Catch rates for all 251 Pokemon (Gen 2 values, 0–255; higher = easier)
# Used to filter the wild pool for the "Set Minimum Catch Rate" option.
# ─────────────────────────────────────────────────────────────────────────────
POKEMON_CATCH_RATES = {
    # ── Gen 1 (#1–151) ───────────────────────────────────────────────────────
    1:  45,  2:  45,  3:  45,   # Bulbasaur, Ivysaur, Venusaur
    4:  45,  5:  45,  6:  45,   # Charmander, Charmeleon, Charizard
    7:  45,  8:  45,  9:  45,   # Squirtle, Wartortle, Blastoise
    10: 255, 11: 120, 12:  45,  # Caterpie, Metapod, Butterfree
    13: 255, 14: 120, 15:  45,  # Weedle, Kakuna, Beedrill
    16: 255, 17: 120, 18:  45,  # Pidgey, Pidgeotto, Pidgeot
    19: 255, 20:  90,            # Rattata, Raticate
    21: 255, 22:  90,            # Spearow, Fearow
    23: 255, 24:  90,            # Ekans, Arbok
    25: 190, 26:  75,            # Pikachu, Raichu
    27: 255, 28:  90,            # Sandshrew, Sandslash
    29: 235, 30: 120, 31:  45,  # Nidoran-F, Nidorina, Nidoqueen
    32: 235, 33: 120, 34:  45,  # Nidoran-M, Nidorino, Nidoking
    35: 150, 36:  25,            # Clefairy, Clefable
    37: 190, 38:  75,            # Vulpix, Ninetales
    39: 170, 40:  50,            # Jigglypuff, Wigglytuff
    41: 255, 42:  90,            # Zubat, Golbat
    43: 255, 44: 120, 45:  45,  # Oddish, Gloom, Vileplume
    46: 190, 47:  75,            # Paras, Parasect
    48: 190, 49:  75,            # Venonat, Venomoth
    50: 255, 51:  50,            # Diglett, Dugtrio
    52: 255, 53:  90,            # Meowth, Persian
    54: 190, 55:  75,            # Psyduck, Golduck
    56: 190, 57:  75,            # Mankey, Primeape
    58: 190, 59:  75,            # Growlithe, Arcanine
    60: 255, 61: 120, 62:  45,  # Poliwag, Poliwhirl, Poliwrath
    63: 200, 64: 100, 65:  50,  # Abra, Kadabra, Alakazam
    66: 180, 67:  90, 68:  45,  # Machop, Machoke, Machamp
    69: 255, 70: 120, 71:  45,  # Bellsprout, Weepinbell, Victreebel
    72: 190, 73:  60,            # Tentacool, Tentacruel
    74: 255, 75: 120, 76:  45,  # Geodude, Graveler, Golem
    77: 190, 78:  60,            # Ponyta, Rapidash
    79: 190, 80:  75,            # Slowpoke, Slowbro
    81: 190, 82:  60,            # Magnemite, Magneton
    83:  45,                     # Farfetch'd
    84: 190, 85:  75,            # Doduo, Dodrio
    86: 190, 87:  75,            # Seel, Dewgong
    88: 190, 89:  75,            # Grimer, Muk
    90: 190, 91:  60,            # Shellder, Cloyster
    92: 190, 93:  90, 94:  45,  # Gastly, Haunter, Gengar
    95:  45,                     # Onix
    96: 190, 97:  75,            # Drowzee, Hypno
    98: 225, 99:  60,            # Krabby, Kingler
    100: 190, 101:  60,          # Voltorb, Electrode
    102:  90, 103:  45,          # Exeggcute, Exeggutor
    104: 190, 105:  75,          # Cubone, Marowak
    106:  45, 107:  45,          # Hitmonlee, Hitmonchan
    108:  45,                    # Lickitung
    109: 190, 110:  60,          # Koffing, Weezing
    111: 120, 112:  60,          # Rhyhorn, Rhydon
    113:  30,                    # Chansey
    114:  45,                    # Tangela
    115:  45,                    # Kangaskhan
    116: 225, 117:  75,          # Horsea, Seadra
    118: 225, 119:  60,          # Goldeen, Seaking
    120: 225, 121:  60,          # Staryu, Starmie
    122:  45,                    # Mr. Mime
    123:  45,                    # Scyther
    124:  45,                    # Jynx
    125:  45,                    # Electabuzz
    126:  45,                    # Magmar
    127:  45,                    # Pinsir
    128:  45,                    # Tauros
    129: 255, 130:  45,          # Magikarp, Gyarados
    131:  45,                    # Lapras
    132:  35,                    # Ditto
    133:  45,                    # Eevee
    134:  45, 135:  45, 136:  45, # Vaporeon, Jolteon, Flareon
    137:  45,                    # Porygon
    138:  45, 139:  45,          # Omanyte, Omastar
    140:  45, 141:  45,          # Kabuto, Kabutops
    142:  45,                    # Aerodactyl
    143:  25,                    # Snorlax
    144:   3, 145:   3, 146:   3, # Articuno, Zapdos, Moltres
    147:  45, 148:  45, 149:  45, # Dratini, Dragonair, Dragonite
    150:   3,                    # Mewtwo
    151:  45,                    # Mew
    # ── Gen 2 (#152–251) ─────────────────────────────────────────────────────
    152:  45, 153:  45, 154:  45, # Chikorita, Bayleef, Meganium
    155:  45, 156:  45, 157:  45, # Cyndaquil, Quilava, Typhlosion
    158:  45, 159:  45, 160:  45, # Totodile, Croconaw, Feraligatr
    161: 255, 162:  90,           # Sentret, Furret
    163: 255, 164:  90,           # Hoothoot, Noctowl
    165: 255, 166:  90,           # Ledyba, Ledian
    167: 255, 168:  90,           # Spinarak, Ariados
    169:  90,                     # Crobat
    170: 190, 171:  75,           # Chinchou, Lanturn
    172: 190,                     # Pichu
    173: 150,                     # Cleffa
    174: 170,                     # Igglybuff
    175: 190,                     # Togepi
    176:  75,                     # Togetic
    177: 190, 178:  75,           # Natu, Xatu
    179: 235, 180: 120, 181:  45, # Mareep, Flaaffy, Ampharos
    182:  45,                     # Bellossom
    183: 190, 184:  75,           # Marill, Azumarill
    185:  65,                     # Sudowoodo
    186:  45,                     # Politoed
    187: 255, 188: 120, 189:  45, # Hoppip, Skiploom, Jumpluff
    190:  45,                     # Aipom
    191: 235, 192: 120,           # Sunkern, Sunflora
    193:  75,                     # Yanma
    194: 255, 195:  90,           # Wooper, Quagsire
    196:  45,                     # Espeon
    197:  45,                     # Umbreon
    198:  30,                     # Murkrow
    199:  70,                     # Slowking
    200:  45,                     # Misdreavus
    201: 225,                     # Unown
    202:  45,                     # Wobbuffet
    203:  60,                     # Girafarig
    204: 190, 205:  75,           # Pineco, Forretress
    206: 190,                     # Dunsparce
    207:  60,                     # Gligar
    208:  25,                     # Steelix
    209: 190, 210:  75,           # Snubbull, Granbull
    211:  45,                     # Qwilfish
    212:  25,                     # Scizor
    213: 190,                     # Shuckle
    214:  45,                     # Heracross
    215:  60,                     # Sneasel
    216: 120, 217:  60,           # Teddiursa, Ursaring
    218: 190, 219:  75,           # Slugma, Magcargo
    220: 225, 221:  75,           # Swinub, Piloswine
    222: 120,                     # Corsola
    223: 190, 224:  75,           # Remoraid, Octillery
    225:  45,                     # Delibird
    226:  25,                     # Mantine
    227:  25,                     # Skarmory
    228: 190, 229:  75,           # Houndour, Houndoom
    230:  45,                     # Kingdra
    231: 120, 232:  60,           # Phanpy, Donphan
    233:  45,                     # Porygon2
    234:  45,                     # Stantler
    235:  45,                     # Smeargle
    236:  75,                     # Tyrogue
    237:  45,                     # Hitmontop
    238:  45,                     # Smoochum
    239:  45,                     # Elekid
    240:  45,                     # Magby
    241:  45,                     # Miltank
    242:  30,                     # Blissey
    243:   3, 244:   3, 245:   3, # Raikou, Entei, Suicune
    246:  45, 247:  45, 248:  45, # Larvitar, Pupitar, Tyranitar
    249:   3, 250:   3,           # Lugia, Ho-Oh
    251:  45,                     # Celebi
}

# All type strings used (for area-theme picking)
ALL_TYPES = (
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic",
    "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel",
)

# Script macro names used in Crystal Legacy for wild-encounter-style static battles
# and for gift Pokemon — these appear literally in .asm script files.
# Crystal Legacy uses  loadwildmon SPECIES, level  (followed by startbattle)
# rather than the standard pret  battle SPECIES, level, item  macro.
STATIC_BATTLE_MACROS = frozenset({"battle", "loadwildmon"})
STATIC_GIFT_MACROS   = frozenset({"givepoke", "giveegg"})
ALL_STATIC_MACROS    = STATIC_BATTLE_MACROS | STATIC_GIFT_MACROS

# ─────────────────────────────────────────────────────────────────────────────
# Yellow Legacy (Gen 1) static encounter species
# ─────────────────────────────────────────────────────────────────────────────

# Legendary Pokémon that appear as static encounters in Gen 1
# (stored in data/maps/objects/ via object_event ... SPECIES, LEVEL)
YELLOW_STATIC_LEGENDARY_SPECIES = frozenset({
    "ARTICUNO",   # Seafoam Islands B4F  (object_event ... ARTICUNO, 50)
    "ZAPDOS",     # Power Plant          (object_event ... ZAPDOS, 50)
    "MOLTRES",    # Victory Road 2F      (object_event ... MOLTRES, 50)
    "MEWTWO",     # Cerulean Cave B1F    (object_event ... MEWTWO, 70)
})

# Standard (non-legendary) species found as scripted static or gift encounters.
#
# Yellow Legacy uses two parseable patterns:
#   • "lb bc, SPECIES, level" (gift Pokémon via call GivePokemon)
#       BULBASAUR, SQUIRTLE, CHARMANDER, LAPRAS, EEVEE, KABUTO, OMANYTE, MAGIKARP
#   • "ld a, SPECIES" immediately followed by "ld [wCurOpponent], a" (scripted battle)
#       SNORLAX (Route 12 and Route 16)
#
# NOT included (too complex to randomize cleanly):
#   AERODACTYL — fossil revival uses wFossilMon RAM variable, not a patchable constant
#   HITMONLEE/HITMONCHAN — Fighting Dojo script uses wcf91 RAM, not directly patchable
YELLOW_STATIC_STANDARD_SPECIES = frozenset({
    # Starter gifts (Yellow Legacy additions)
    "BULBASAUR",    # Cerulean Melanie's House (lb bc, BULBASAUR, 10)
    "SQUIRTLE",     # Vermilion City gift      (lb bc, SQUIRTLE, 15)
    "CHARMANDER",   # Route 24 gift            (lb bc, CHARMANDER, 13)
    # Other gift Pokémon
    "LAPRAS",       # Silph Co. 7F             (lb bc, LAPRAS, 35)
    "EEVEE",        # Celadon Mansion Roof     (lb bc, EEVEE, 25)
    "KABUTO",       # Fuchsia Good Rod House   (lb bc, KABUTO, 10)
    "OMANYTE",      # Fuchsia Good Rod House   (lb bc, OMANYTE, 10)
    "MAGIKARP",     # Mt. Moon Pokécenter      (lb bc, MAGIKARP, 5)
    # Scripted wild battles
    "SNORLAX",      # Route 12 & Route 16      (ld a, SNORLAX → ld [wCurOpponent], a)
})

YELLOW_ALL_STATIC_SPECIES = (
    YELLOW_STATIC_LEGENDARY_SPECIES | YELLOW_STATIC_STANDARD_SPECIES
)

# NOTE: Yellow Legacy does NOT use "battle" or "givepoke" macros.
# The parser uses three dedicated patterns instead (see parser_yellow._parse_static_encounters).
