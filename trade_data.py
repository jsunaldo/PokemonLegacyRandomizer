"""
In-game trade data for Pokemon Crystal Legacy.

Provides the held-item pool and random name / DV generators used when
randomizing in-game trades.

All item constant names verified against Crystal Legacy item_constants.asm.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Held-item pool — Crystal Legacy constant names for trade gifts
# ─────────────────────────────────────────────────────────────────────────────
TRADE_ITEM_POOL = [
    # Berries (Crystal Legacy names)
    "BERRY",          # heals HP
    "GOLD_BERRY",     # heals more HP
    "MIRACLEBERRY",   # Lum-equivalent (cures any status)
    "MYSTERYBERRY",   # restores PP
    "PSNCUREBERRY",   # cures poison
    "PRZCUREBERRY",   # cures paralysis
    "BITTER_BERRY",   # cures confusion
    "BURNT_BERRY",    # cures freeze
    "MINT_BERRY",     # cures sleep
    "ICE_BERRY",      # cures freeze
    # Utility items
    "LEFTOVERS",
    "KINGS_ROCK",
    "QUICK_CLAW",
    "BRIGHTPOWDER",
    "FOCUS_BAND",
    "SCOPE_LENS",
    "LUCKY_EGG",
    # Type-enhancing held items
    "CHARCOAL",
    "MIRACLE_SEED",
    "MAGNET",
    "MYSTIC_WATER",
    "SHARP_BEAK",
    "POISON_BARB",
    "SOFT_SAND",
    "HARD_STONE",
    "SILVERPOWDER",
    "SPELL_TAG",
    "TWISTEDSPOON",
    "BLACKBELT_I",
    "PINK_BOW",
    "POLKADOT_BOW",
    "NEVERMELTICE",
    "DRAGON_SCALE",
]

# ─────────────────────────────────────────────────────────────────────────────
# Starter held-item pools (also used for wild held-item randomization)
# ─────────────────────────────────────────────────────────────────────────────

# Full pool — every reasonable Crystal held item
STARTER_ITEM_POOL_FULL = [
    # Recovery berries
    "BERRY",
    "GOLD_BERRY",
    "MIRACLEBERRY",
    "MYSTERYBERRY",
    "PSNCUREBERRY",
    "PRZCUREBERRY",
    "BITTER_BERRY",
    "BURNT_BERRY",
    "MINT_BERRY",
    "ICE_BERRY",
    # Battle utility
    "LEFTOVERS",
    "KINGS_ROCK",
    "QUICK_CLAW",
    "BRIGHTPOWDER",
    "FOCUS_BAND",
    "SCOPE_LENS",
    "LUCKY_EGG",
    # Type-enhancing held items
    "CHARCOAL",
    "MIRACLE_SEED",
    "MAGNET",
    "MYSTIC_WATER",
    "SHARP_BEAK",
    "POISON_BARB",
    "SOFT_SAND",
    "HARD_STONE",
    "SILVERPOWDER",
    "SPELL_TAG",
    "TWISTEDSPOON",
    "BLACKBELT_I",
    "PINK_BOW",
    "POLKADOT_BOW",
    "NEVERMELTICE",
    "DRAGON_SCALE",
]

# Good pool — only reliable / high-impact items
STARTER_ITEM_POOL_GOOD = [
    # Strong recovery
    "GOLD_BERRY",
    "MIRACLEBERRY",
    # Reliable battle utility
    "LEFTOVERS",
    "KINGS_ROCK",
    "QUICK_CLAW",
    "SCOPE_LENS",
    "LUCKY_EGG",
    # Type enhancers
    "CHARCOAL",
    "MIRACLE_SEED",
    "MAGNET",
    "MYSTIC_WATER",
    "SHARP_BEAK",
    "SOFT_SAND",
    "HARD_STONE",
    "SPELL_TAG",
    "TWISTEDSPOON",
    "BLACKBELT_I",
    "PINK_BOW",
    "POLKADOT_BOW",
    "NEVERMELTICE",
    "DRAGON_SCALE",
]

# ─────────────────────────────────────────────────────────────────────────────
# Name generators
# ─────────────────────────────────────────────────────────────────────────────
_VOWELS     = "AEIOU"
_CONSONANTS = "BCDFGHJKLMNPRSTVWXYZ"


def make_random_nickname(rng, max_len: int = 10) -> str:
    """
    Generate a random Pokémon-style nickname (uppercase, 4–8 chars).
    Alternates consonants and vowels to keep names pronounceable.
    """
    length = rng.randint(4, min(8, max_len))
    result = []
    use_consonant = rng.random() > 0.35   # usually start with a consonant
    for _ in range(length):
        result.append(rng.choice(_CONSONANTS if use_consonant else _VOWELS))
        use_consonant = not use_consonant
    return "".join(result)


def make_random_ot(rng, max_len: int = 7) -> str:
    """Generate a random OT name (uppercase, 3–5 chars)."""
    length = rng.randint(3, min(5, max_len))
    result = []
    use_consonant = rng.random() > 0.35
    for _ in range(length):
        result.append(rng.choice(_CONSONANTS if use_consonant else _VOWELS))
        use_consonant = not use_consonant
    return "".join(result)


def make_random_dvs(rng) -> str:
    """
    Generate a random Gen 2 DV word as a hex string (e.g. '$5A3F').
    The high byte encodes Attack|Defense DVs; the low byte Speed|Special DVs.
    Each nibble is 0–15, so the full word is 0x0000–0xFFFF.
    """
    return f"${rng.randint(0, 0xFFFF):04X}"
