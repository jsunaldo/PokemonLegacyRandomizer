"""
Pokemon Yellow Legacy - Constants
Gen 1 (151 Pokemon) constants for the Yellow Legacy randomizer.
Internal IDs are the Gen 1 byte values (non-sequential, NOT Pokedex order).
"""

# ---------------------------------------------------------------------------
# Pokemon constants: {ASM_CONST_NAME: internal_byte_id}
# Derived from constants/pokemon_constants.asm (const_def sequence)
# ---------------------------------------------------------------------------
YELLOW_POKEMON_CONSTANTS = {
    'RHYDON': 0x01, 'KANGASKHAN': 0x02, 'NIDORAN_M': 0x03, 'CLEFAIRY': 0x04,
    'SPEAROW': 0x05, 'VOLTORB': 0x06, 'NIDOKING': 0x07, 'SLOWBRO': 0x08,
    'IVYSAUR': 0x09, 'EXEGGUTOR': 0x0A, 'LICKITUNG': 0x0B, 'EXEGGCUTE': 0x0C,
    'GRIMER': 0x0D, 'GENGAR': 0x0E, 'NIDORAN_F': 0x0F, 'NIDOQUEEN': 0x10,
    'CUBONE': 0x11, 'RHYHORN': 0x12, 'LAPRAS': 0x13, 'ARCANINE': 0x14,
    'MEW': 0x15, 'GYARADOS': 0x16, 'SHELLDER': 0x17, 'TENTACOOL': 0x18,
    'GASTLY': 0x19, 'SCYTHER': 0x1A, 'STARYU': 0x1B, 'BLASTOISE': 0x1C,
    'PINSIR': 0x1D, 'TANGELA': 0x1E,
    'GROWLITHE': 0x21, 'ONIX': 0x22, 'FEAROW': 0x23, 'PIDGEY': 0x24,
    'SLOWPOKE': 0x25, 'KADABRA': 0x26, 'GRAVELER': 0x27, 'CHANSEY': 0x28,
    'MACHOKE': 0x29, 'MR_MIME': 0x2A, 'HITMONLEE': 0x2B, 'HITMONCHAN': 0x2C,
    'ARBOK': 0x2D, 'PARASECT': 0x2E, 'PSYDUCK': 0x2F, 'DROWZEE': 0x30,
    'GOLEM': 0x31, 'MAGMAR': 0x33, 'ELECTABUZZ': 0x35, 'MAGNETON': 0x36,
    'KOFFING': 0x37, 'MANKEY': 0x39, 'SEEL': 0x3A, 'DIGLETT': 0x3B,
    'TAUROS': 0x3C, 'FARFETCHD': 0x40, 'VENONAT': 0x41, 'DRAGONITE': 0x42,
    'DODUO': 0x46, 'POLIWAG': 0x47, 'JYNX': 0x48,
    'MOLTRES': 0x49, 'ARTICUNO': 0x4A, 'ZAPDOS': 0x4B,
    'DITTO': 0x4C, 'MEOWTH': 0x4D, 'KRABBY': 0x4E,
    'VULPIX': 0x52, 'NINETALES': 0x53, 'PIKACHU': 0x54, 'RAICHU': 0x55,
    'DRATINI': 0x58, 'DRAGONAIR': 0x59, 'KABUTO': 0x5A, 'KABUTOPS': 0x5B,
    'HORSEA': 0x5C, 'SEADRA': 0x5D,
    'SANDSHREW': 0x60, 'SANDSLASH': 0x61, 'OMANYTE': 0x62, 'OMASTAR': 0x63,
    'JIGGLYPUFF': 0x64, 'WIGGLYTUFF': 0x65, 'EEVEE': 0x66,
    'FLAREON': 0x67, 'JOLTEON': 0x68, 'VAPOREON': 0x69,
    'MACHOP': 0x6A, 'ZUBAT': 0x6B, 'EKANS': 0x6C, 'PARAS': 0x6D,
    'POLIWHIRL': 0x6E, 'POLIWRATH': 0x6F, 'WEEDLE': 0x70, 'KAKUNA': 0x71,
    'BEEDRILL': 0x72, 'DODRIO': 0x74, 'PRIMEAPE': 0x75, 'DUGTRIO': 0x76,
    'VENOMOTH': 0x77, 'DEWGONG': 0x78,
    'CATERPIE': 0x7B, 'METAPOD': 0x7C, 'BUTTERFREE': 0x7D, 'MACHAMP': 0x7E,
    'GOLDUCK': 0x80, 'HYPNO': 0x81, 'GOLBAT': 0x82, 'MEWTWO': 0x83,
    'SNORLAX': 0x84, 'MAGIKARP': 0x85, 'MUK': 0x88,
    'KINGLER': 0x8A, 'CLOYSTER': 0x8B, 'ELECTRODE': 0x8D, 'CLEFABLE': 0x8E,
    'WEEZING': 0x8F, 'PERSIAN': 0x90, 'MAROWAK': 0x91,
    'HAUNTER': 0x93, 'ABRA': 0x94, 'ALAKAZAM': 0x95,
    'PIDGEOTTO': 0x96, 'PIDGEOT': 0x97, 'STARMIE': 0x98,
    'BULBASAUR': 0x99, 'VENUSAUR': 0x9A, 'TENTACRUEL': 0x9B,
    'GOLDEEN': 0x9D, 'SEAKING': 0x9E,
    'PONYTA': 0xA3, 'RAPIDASH': 0xA4, 'RATTATA': 0xA5, 'RATICATE': 0xA6,
    'NIDORINO': 0xA7, 'NIDORINA': 0xA8, 'GEODUDE': 0xA9, 'PORYGON': 0xAA,
    'AERODACTYL': 0xAB, 'MAGNEMITE': 0xAD,
    'CHARMANDER': 0xB0, 'SQUIRTLE': 0xB1, 'CHARMELEON': 0xB2,
    'WARTORTLE': 0xB3, 'CHARIZARD': 0xB4,
    'ODDISH': 0xB9, 'GLOOM': 0xBA, 'VILEPLUME': 0xBB,
    'BELLSPROUT': 0xBC, 'WEEPINBELL': 0xBD, 'VICTREEBEL': 0xBE,
}

# Reverse lookup: internal id -> const name
YELLOW_POKEMON_ID_TO_CONST = {v: k for k, v in YELLOW_POKEMON_CONSTANTS.items()}

# All 151 Pokémon in Pokédex order (for UI display)
YELLOW_POKEMON_CONSTS_POKEDEX_ORDER = [
    'BULBASAUR', 'IVYSAUR', 'VENUSAUR',
    'CHARMANDER', 'CHARMELEON', 'CHARIZARD',
    'SQUIRTLE', 'WARTORTLE', 'BLASTOISE',
    'CATERPIE', 'METAPOD', 'BUTTERFREE',
    'WEEDLE', 'KAKUNA', 'BEEDRILL',
    'PIDGEY', 'PIDGEOTTO', 'PIDGEOT',
    'RATTATA', 'RATICATE',
    'SPEAROW', 'FEAROW',
    'EKANS', 'ARBOK',
    'PIKACHU', 'RAICHU',
    'SANDSHREW', 'SANDSLASH',
    'NIDORAN_F', 'NIDORINA', 'NIDOQUEEN',
    'NIDORAN_M', 'NIDORINO', 'NIDOKING',
    'CLEFAIRY', 'CLEFABLE',
    'VULPIX', 'NINETALES',
    'JIGGLYPUFF', 'WIGGLYTUFF',
    'ZUBAT', 'GOLBAT',
    'ODDISH', 'GLOOM', 'VILEPLUME',
    'PARAS', 'PARASECT',
    'VENONAT', 'VENOMOTH',
    'DIGLETT', 'DUGTRIO',
    'MEOWTH', 'PERSIAN',
    'PSYDUCK', 'GOLDUCK',
    'MANKEY', 'PRIMEAPE',
    'GROWLITHE', 'ARCANINE',
    'POLIWAG', 'POLIWHIRL', 'POLIWRATH',
    'ABRA', 'KADABRA', 'ALAKAZAM',
    'MACHOP', 'MACHOKE', 'MACHAMP',
    'BELLSPROUT', 'WEEPINBELL', 'VICTREEBEL',
    'TENTACOOL', 'TENTACRUEL',
    'GEODUDE', 'GRAVELER', 'GOLEM',
    'PONYTA', 'RAPIDASH',
    'SLOWPOKE', 'SLOWBRO',
    'MAGNEMITE', 'MAGNETON',
    'FARFETCHD',
    'DODUO', 'DODRIO',
    'SEEL', 'DEWGONG',
    'GRIMER', 'MUK',
    'SHELLDER', 'CLOYSTER',
    'GASTLY', 'HAUNTER', 'GENGAR',
    'ONIX',
    'DROWZEE', 'HYPNO',
    'KRABBY', 'KINGLER',
    'VOLTORB', 'ELECTRODE',
    'EXEGGCUTE', 'EXEGGUTOR',
    'CUBONE', 'MAROWAK',
    'HITMONLEE', 'HITMONCHAN',
    'LICKITUNG',
    'KOFFING', 'WEEZING',
    'RHYHORN', 'RHYDON',
    'CHANSEY',
    'TANGELA',
    'KANGASKHAN',
    'HORSEA', 'SEADRA',
    'GOLDEEN', 'SEAKING',
    'STARYU', 'STARMIE',
    'MR_MIME',
    'SCYTHER',
    'JYNX',
    'ELECTABUZZ',
    'MAGMAR',
    'PINSIR',
    'TAUROS',
    'MAGIKARP', 'GYARADOS',
    'LAPRAS',
    'DITTO',
    'EEVEE', 'VAPOREON', 'JOLTEON', 'FLAREON',
    'PORYGON',
    'OMANYTE', 'OMASTAR',
    'KABUTO', 'KABUTOPS',
    'AERODACTYL',
    'SNORLAX',
    'ARTICUNO', 'ZAPDOS', 'MOLTRES',
    'DRATINI', 'DRAGONAIR', 'DRAGONITE',
    'MEWTWO',
    'MEW',
]

# Display names for the UI (special characters / spacing)
YELLOW_POKEMON_DISPLAY_NAME = {
    'NIDORAN_F': 'Nidoran♀',
    'NIDORAN_M': 'Nidoran♂',
    'FARFETCHD': "Farfetch'd",
    'MR_MIME':   'Mr. Mime',
}
# Fill in standard title-case names for the rest
for _c in YELLOW_POKEMON_CONSTANTS:
    if _c not in YELLOW_POKEMON_DISPLAY_NAME:
        YELLOW_POKEMON_DISPLAY_NAME[_c] = _c.replace('_', ' ').title()

# Primary type per Pokémon (used for type-matched randomization)
# Type strings match what appears in the ASM source (e.g. "ELECTRIC", "PSYCHIC_TYPE")
YELLOW_POKEMON_PRIMARY_TYPE = {
    'BULBASAUR': 'GRASS', 'IVYSAUR': 'GRASS', 'VENUSAUR': 'GRASS',
    'CHARMANDER': 'FIRE', 'CHARMELEON': 'FIRE', 'CHARIZARD': 'FIRE',
    'SQUIRTLE': 'WATER', 'WARTORTLE': 'WATER', 'BLASTOISE': 'WATER',
    'CATERPIE': 'BUG', 'METAPOD': 'BUG', 'BUTTERFREE': 'BUG',
    'WEEDLE': 'BUG', 'KAKUNA': 'BUG', 'BEEDRILL': 'BUG',
    'PIDGEY': 'NORMAL', 'PIDGEOTTO': 'NORMAL', 'PIDGEOT': 'NORMAL',
    'RATTATA': 'NORMAL', 'RATICATE': 'NORMAL',
    'SPEAROW': 'NORMAL', 'FEAROW': 'NORMAL',
    'EKANS': 'POISON', 'ARBOK': 'POISON',
    'PIKACHU': 'ELECTRIC', 'RAICHU': 'ELECTRIC',
    'SANDSHREW': 'GROUND', 'SANDSLASH': 'GROUND',
    'NIDORAN_F': 'POISON', 'NIDORINA': 'POISON', 'NIDOQUEEN': 'POISON',
    'NIDORAN_M': 'POISON', 'NIDORINO': 'POISON', 'NIDOKING': 'POISON',
    'CLEFAIRY': 'NORMAL', 'CLEFABLE': 'NORMAL',
    'VULPIX': 'FIRE', 'NINETALES': 'FIRE',
    'JIGGLYPUFF': 'NORMAL', 'WIGGLYTUFF': 'NORMAL',
    'ZUBAT': 'POISON', 'GOLBAT': 'POISON',
    'ODDISH': 'GRASS', 'GLOOM': 'GRASS', 'VILEPLUME': 'GRASS',
    'PARAS': 'BUG', 'PARASECT': 'BUG',
    'VENONAT': 'BUG', 'VENOMOTH': 'BUG',
    'DIGLETT': 'GROUND', 'DUGTRIO': 'GROUND',
    'MEOWTH': 'NORMAL', 'PERSIAN': 'NORMAL',
    'PSYDUCK': 'WATER', 'GOLDUCK': 'WATER',
    'MANKEY': 'FIGHTING', 'PRIMEAPE': 'FIGHTING',
    'GROWLITHE': 'FIRE', 'ARCANINE': 'FIRE',
    'POLIWAG': 'WATER', 'POLIWHIRL': 'WATER', 'POLIWRATH': 'WATER',
    'ABRA': 'PSYCHIC_TYPE', 'KADABRA': 'PSYCHIC_TYPE', 'ALAKAZAM': 'PSYCHIC_TYPE',
    'MACHOP': 'FIGHTING', 'MACHOKE': 'FIGHTING', 'MACHAMP': 'FIGHTING',
    'BELLSPROUT': 'GRASS', 'WEEPINBELL': 'GRASS', 'VICTREEBEL': 'GRASS',
    'TENTACOOL': 'WATER', 'TENTACRUEL': 'WATER',
    'GEODUDE': 'ROCK', 'GRAVELER': 'ROCK', 'GOLEM': 'ROCK',
    'PONYTA': 'FIRE', 'RAPIDASH': 'FIRE',
    'SLOWPOKE': 'WATER', 'SLOWBRO': 'WATER',
    'MAGNEMITE': 'ELECTRIC', 'MAGNETON': 'ELECTRIC',
    'FARFETCHD': 'NORMAL',
    'DODUO': 'NORMAL', 'DODRIO': 'NORMAL',
    'SEEL': 'WATER', 'DEWGONG': 'WATER',
    'GRIMER': 'POISON', 'MUK': 'POISON',
    'SHELLDER': 'WATER', 'CLOYSTER': 'WATER',
    'GASTLY': 'GHOST', 'HAUNTER': 'GHOST', 'GENGAR': 'GHOST',
    'ONIX': 'ROCK',
    'DROWZEE': 'PSYCHIC_TYPE', 'HYPNO': 'PSYCHIC_TYPE',
    'KRABBY': 'WATER', 'KINGLER': 'WATER',
    'VOLTORB': 'ELECTRIC', 'ELECTRODE': 'ELECTRIC',
    'EXEGGCUTE': 'GRASS', 'EXEGGUTOR': 'GRASS',
    'CUBONE': 'GROUND', 'MAROWAK': 'GROUND',
    'HITMONLEE': 'FIGHTING', 'HITMONCHAN': 'FIGHTING',
    'LICKITUNG': 'NORMAL',
    'KOFFING': 'POISON', 'WEEZING': 'POISON',
    'RHYHORN': 'GROUND', 'RHYDON': 'GROUND',
    'CHANSEY': 'NORMAL',
    'TANGELA': 'GRASS',
    'KANGASKHAN': 'NORMAL',
    'HORSEA': 'WATER', 'SEADRA': 'WATER',
    'GOLDEEN': 'WATER', 'SEAKING': 'WATER',
    'STARYU': 'WATER', 'STARMIE': 'WATER',
    'MR_MIME': 'PSYCHIC_TYPE',
    'SCYTHER': 'BUG',
    'JYNX': 'ICE',
    'ELECTABUZZ': 'ELECTRIC',
    'MAGMAR': 'FIRE',
    'PINSIR': 'BUG',
    'TAUROS': 'NORMAL',
    'MAGIKARP': 'WATER', 'GYARADOS': 'WATER',
    'LAPRAS': 'WATER',
    'DITTO': 'NORMAL',
    'EEVEE': 'NORMAL',
    'VAPOREON': 'WATER', 'JOLTEON': 'ELECTRIC', 'FLAREON': 'FIRE',
    'PORYGON': 'NORMAL',
    'OMANYTE': 'ROCK', 'OMASTAR': 'ROCK',
    'KABUTO': 'ROCK', 'KABUTOPS': 'ROCK',
    'AERODACTYL': 'ROCK',
    'SNORLAX': 'NORMAL',
    'ARTICUNO': 'ICE', 'ZAPDOS': 'ELECTRIC', 'MOLTRES': 'FIRE',
    'DRATINI': 'DRAGON', 'DRAGONAIR': 'DRAGON', 'DRAGONITE': 'DRAGON',
    'MEWTWO': 'PSYCHIC_TYPE',
    'MEW': 'PSYCHIC_TYPE',
}

# Legendary / special Pokémon (excluded from certain randomization pools by default)
YELLOW_LEGENDARY_POKEMON = {'ARTICUNO', 'ZAPDOS', 'MOLTRES', 'MEWTWO', 'MEW'}

# ---------------------------------------------------------------------------
# Move constants: {ASM_CONST_NAME: move_id}
# Real moves only: 0x01 (POUND) through 0xA4 (SUBSTITUTE)
# STRUGGLE (0xA5) excluded — it's a special desperation move
# ---------------------------------------------------------------------------
YELLOW_MOVE_CONSTANTS = {
    'NO_MOVE': 0x00,
    'POUND': 0x01, 'KARATE_CHOP': 0x02, 'DOUBLESLAP': 0x03, 'COMET_PUNCH': 0x04,
    'MEGA_PUNCH': 0x05, 'PAY_DAY': 0x06, 'FIRE_PUNCH': 0x07, 'ICE_PUNCH': 0x08,
    'THUNDERPUNCH': 0x09, 'SCRATCH': 0x0A, 'VICEGRIP': 0x0B, 'GUILLOTINE': 0x0C,
    'RAZOR_WIND': 0x0D, 'SWORDS_DANCE': 0x0E, 'CUT': 0x0F, 'GUST': 0x10,
    'WING_ATTACK': 0x11, 'WHIRLWIND': 0x12, 'FLY': 0x13, 'BIND': 0x14,
    'SLAM': 0x15, 'VINE_WHIP': 0x16, 'STOMP': 0x17, 'DOUBLE_KICK': 0x18,
    'MEGA_KICK': 0x19, 'JUMP_KICK': 0x1A, 'ROLLING_KICK': 0x1B,
    'SAND_ATTACK': 0x1C, 'HEADBUTT': 0x1D, 'HORN_ATTACK': 0x1E,
    'FURY_ATTACK': 0x1F, 'HORN_DRILL': 0x20, 'TACKLE': 0x21, 'BODY_SLAM': 0x22,
    'WRAP': 0x23, 'TAKE_DOWN': 0x24, 'THRASH': 0x25, 'DOUBLE_EDGE': 0x26,
    'TAIL_WHIP': 0x27, 'POISON_STING': 0x28, 'TWINEEDLE': 0x29,
    'PIN_MISSILE': 0x2A, 'LEER': 0x2B, 'BITE': 0x2C, 'GROWL': 0x2D,
    'ROAR': 0x2E, 'SING': 0x2F, 'SUPERSONIC': 0x30, 'SONICBOOM': 0x31,
    'DISABLE': 0x32, 'ACID': 0x33, 'EMBER': 0x34, 'FLAMETHROWER': 0x35,
    'MIST': 0x36, 'WATER_GUN': 0x37, 'HYDRO_PUMP': 0x38, 'SURF': 0x39,
    'ICE_BEAM': 0x3A, 'BLIZZARD': 0x3B, 'PSYBEAM': 0x3C, 'BUBBLEBEAM': 0x3D,
    'AURORA_BEAM': 0x3E, 'HYPER_BEAM': 0x3F, 'PECK': 0x40, 'DRILL_PECK': 0x41,
    'SUBMISSION': 0x42, 'LOW_KICK': 0x43, 'COUNTER': 0x44, 'SEISMIC_TOSS': 0x45,
    'STRENGTH': 0x46, 'ABSORB': 0x47, 'MEGA_DRAIN': 0x48, 'LEECH_SEED': 0x49,
    'GROWTH': 0x4A, 'RAZOR_LEAF': 0x4B, 'SOLARBEAM': 0x4C, 'POISONPOWDER': 0x4D,
    'STUN_SPORE': 0x4E, 'SLEEP_POWDER': 0x4F, 'PETAL_DANCE': 0x50,
    'STRING_SHOT': 0x51, 'DRAGON_RAGE': 0x52, 'FIRE_SPIN': 0x53,
    'THUNDERSHOCK': 0x54, 'THUNDERBOLT': 0x55, 'THUNDER_WAVE': 0x56,
    'THUNDER': 0x57, 'ROCK_THROW': 0x58, 'EARTHQUAKE': 0x59, 'FISSURE': 0x5A,
    'DIG': 0x5B, 'TOXIC': 0x5C, 'CONFUSION': 0x5D, 'PSYCHIC_M': 0x5E,
    'HYPNOSIS': 0x5F, 'MEDITATE': 0x60, 'AGILITY': 0x61, 'QUICK_ATTACK': 0x62,
    'RAGE': 0x63, 'TELEPORT': 0x64, 'NIGHT_SHADE': 0x65, 'MIMIC': 0x66,
    'SCREECH': 0x67, 'DOUBLE_TEAM': 0x68, 'RECOVER': 0x69, 'HARDEN': 0x6A,
    'MINIMIZE': 0x6B, 'SMOKESCREEN': 0x6C, 'CONFUSE_RAY': 0x6D,
    'WITHDRAW': 0x6E, 'DEFENSE_CURL': 0x6F, 'BARRIER': 0x70,
    'LIGHT_SCREEN': 0x71, 'HAZE': 0x72, 'REFLECT': 0x73, 'FOCUS_ENERGY': 0x74,
    'BIDE': 0x75, 'METRONOME': 0x76, 'MIRROR_MOVE': 0x77, 'SELFDESTRUCT': 0x78,
    'EGG_BOMB': 0x79, 'LICK': 0x7A, 'SMOG': 0x7B, 'SLUDGE': 0x7C,
    'BONE_CLUB': 0x7D, 'FIRE_BLAST': 0x7E, 'WATERFALL': 0x7F, 'CLAMP': 0x80,
    'SWIFT': 0x81, 'SKULL_BASH': 0x82, 'SPIKE_CANNON': 0x83, 'CONSTRICT': 0x84,
    'AMNESIA': 0x85, 'KINESIS': 0x86, 'SOFTBOILED': 0x87, 'HI_JUMP_KICK': 0x88,
    'GLARE': 0x89, 'DREAM_EATER': 0x8A, 'POISON_GAS': 0x8B, 'BARRAGE': 0x8C,
    'LEECH_LIFE': 0x8D, 'LOVELY_KISS': 0x8E, 'SKY_ATTACK': 0x8F,
    'TRANSFORM': 0x90, 'BUBBLE': 0x91, 'DIZZY_PUNCH': 0x92, 'SPORE': 0x93,
    'FLASH': 0x94, 'PSYWAVE': 0x95, 'SPLASH': 0x96, 'ACID_ARMOR': 0x97,
    'CRABHAMMER': 0x98, 'EXPLOSION': 0x99, 'FURY_SWIPES': 0x9A,
    'BONEMERANG': 0x9B, 'REST': 0x9C, 'ROCK_SLIDE': 0x9D, 'HYPER_FANG': 0x9E,
    'SHARPEN': 0x9F, 'CONVERSION': 0xA0, 'TRI_ATTACK': 0xA1, 'SUPER_FANG': 0xA2,
    'SLASH': 0xA3, 'SUBSTITUTE': 0xA4, 'STRUGGLE': 0xA5,
}

# Randomizable moves (exclude NO_MOVE and STRUGGLE)
YELLOW_MOVE_CONSTS = [
    m for m, i in YELLOW_MOVE_CONSTANTS.items()
    if m not in ('NO_MOVE', 'STRUGGLE')
]

# Display names for moves (title-case from const name)
YELLOW_MOVE_DISPLAY_NAME = {}
_MOVE_DISPLAY_OVERRIDES = {
    'PSYCHIC_M': 'Psychic',
    'HI_JUMP_KICK': 'Hi Jump Kick',
    'SONICBOOM': 'SonicBoom',
    'DOUBLESLAP': 'DoubleSlap',
}
for _m in YELLOW_MOVE_CONSTANTS:
    if _m in _MOVE_DISPLAY_OVERRIDES:
        YELLOW_MOVE_DISPLAY_NAME[_m] = _MOVE_DISPLAY_OVERRIDES[_m]
    else:
        YELLOW_MOVE_DISPLAY_NAME[_m] = _m.replace('_', ' ').title()

# ---------------------------------------------------------------------------
# Item constants: {ASM_CONST_NAME: item_id}
# ---------------------------------------------------------------------------
YELLOW_ITEM_CONSTANTS = {
    'NO_ITEM': 0x00,
    'MASTER_BALL': 0x01, 'ULTRA_BALL': 0x02, 'GREAT_BALL': 0x03, 'POKE_BALL': 0x04,
    'TOWN_MAP': 0x05, 'BICYCLE': 0x06, 'SURFBOARD': 0x07, 'SAFARI_BALL': 0x08,
    'POKEDEX': 0x09, 'MOON_STONE': 0x0A, 'ANTIDOTE': 0x0B, 'BURN_HEAL': 0x0C,
    'ICE_HEAL': 0x0D, 'AWAKENING': 0x0E, 'PARLYZ_HEAL': 0x0F,
    'FULL_RESTORE': 0x10, 'MAX_POTION': 0x11, 'HYPER_POTION': 0x12,
    'SUPER_POTION': 0x13, 'POTION': 0x14, 'BOULDERBADGE': 0x15,
    'CASCADEBADGE': 0x16, 'THUNDERBADGE': 0x17, 'RAINBOWBADGE': 0x18,
    'SOULBADGE': 0x19, 'MARSHBADGE': 0x1A, 'VOLCANOBADGE': 0x1B,
    'EARTHBADGE': 0x1C, 'ESCAPE_ROPE': 0x1D, 'REPEL': 0x1E, 'OLD_AMBER': 0x1F,
    'FIRE_STONE': 0x20, 'THUNDER_STONE': 0x21, 'WATER_STONE': 0x22,
    'HP_UP': 0x23, 'PROTEIN': 0x24, 'IRON': 0x25, 'CARBOS': 0x26,
    'CALCIUM': 0x27, 'RARE_CANDY': 0x28, 'DOME_FOSSIL': 0x29,
    'HELIX_FOSSIL': 0x2A, 'SECRET_KEY': 0x2B, 'BIKE_VOUCHER': 0x2D,
    'X_ACCURACY': 0x2E, 'LEAF_STONE': 0x2F, 'CARD_KEY': 0x30, 'NUGGET': 0x31,
    'POKE_DOLL': 0x33, 'FULL_HEAL': 0x34, 'REVIVE': 0x35, 'MAX_REVIVE': 0x36,
    'GUARD_SPEC': 0x37, 'SUPER_REPEL': 0x38, 'MAX_REPEL': 0x39,
    'DIRE_HIT': 0x3A, 'COIN': 0x3B, 'FRESH_WATER': 0x3C, 'SODA_POP': 0x3D,
    'LEMONADE': 0x3E, 'S_S_TICKET': 0x3F, 'GOLD_TEETH': 0x40,
    'X_ATTACK': 0x41, 'X_DEFEND': 0x42, 'X_SPEED': 0x43, 'X_SPECIAL': 0x44,
    'COIN_CASE': 0x45, 'OAKS_PARCEL': 0x46, 'ITEMFINDER': 0x47,
    'SILPH_SCOPE': 0x48, 'POKE_FLUTE': 0x49, 'LIFT_KEY': 0x4A, 'EXP_ALL': 0x4B,
    'OLD_ROD': 0x4C, 'GOOD_ROD': 0x4D, 'SUPER_ROD': 0x4E,
    'PP_UP': 0x4F, 'ETHER': 0x50, 'MAX_ETHER': 0x51, 'ELIXER': 0x52,
    'MAX_ELIXER': 0x53,
}

# Key items that should never be field-item randomized
YELLOW_KEY_ITEMS = {
    'TOWN_MAP', 'BICYCLE', 'SURFBOARD', 'SAFARI_BALL', 'POKEDEX',
    'BOULDERBADGE', 'CASCADEBADGE', 'THUNDERBADGE', 'RAINBOWBADGE',
    'SOULBADGE', 'MARSHBADGE', 'VOLCANOBADGE', 'EARTHBADGE',
    'OLD_AMBER', 'DOME_FOSSIL', 'HELIX_FOSSIL', 'SECRET_KEY',
    'BIKE_VOUCHER', 'CARD_KEY', 'S_S_TICKET', 'GOLD_TEETH',
    'COIN_CASE', 'OAKS_PARCEL', 'ITEMFINDER', 'SILPH_SCOPE',
    'POKE_FLUTE', 'LIFT_KEY', 'EXP_ALL',
    'OLD_ROD', 'GOOD_ROD', 'SUPER_ROD',
    'NO_ITEM',
}

# Evolution constants
YELLOW_EVOLVE_LEVEL = 'EVOLVE_LEVEL'
YELLOW_EVOLVE_ITEM  = 'EVOLVE_ITEM'
YELLOW_EVOLVE_TRADE = 'EVOLVE_TRADE'  # may be unused in Yellow Legacy

# ---------------------------------------------------------------------------
# Source file / directory paths (relative to source root)
# ---------------------------------------------------------------------------
YELLOW_WILD_MAPS_DIR        = 'data/wild/maps'
YELLOW_TRAINER_PARTIES_FILE = 'data/trainers/parties.asm'
YELLOW_STARTER_FILE         = 'scripts/OaksLab.asm'
YELLOW_TRADES_FILE          = 'data/events/trades.asm'
YELLOW_EVOS_MOVES_FILE      = 'data/pokemon/evos_moves.asm'
YELLOW_BASE_STATS_DIR       = 'data/pokemon/base_stats'
YELLOW_OLD_ROD_FILE         = 'data/wild/old_rod.asm'
YELLOW_GOOD_ROD_FILE        = 'data/wild/good_rod.asm'
YELLOW_SUPER_ROD_FILE       = 'data/wild/super_rod.asm'

# Output ROM filename (from Makefile)
YELLOW_ROM_FILENAME         = 'pokeyellow.gbc'
