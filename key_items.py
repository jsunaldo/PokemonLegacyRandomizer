"""
Key items that must never be moved or replaced by any randomizer feature.

A field item ball / hidden item holding one of these is left exactly where
the game put it. Losing one can make a run unwinnable — e.g. Yellow's Lift
Key in Rocket Hideout B4F (no elevator → no Giovanni → no Silph Scope →
Pokémon Tower is impassable).

The list for each game is read from the game's OWN source, so items a Legacy
version adds or moves are covered automatically:
  Yellow   data/items/key_items.asm   KeyItemFlags rows marked TRUE
  Crystal  data/items/attributes.asm  entries in the KEY_ITEM pocket
  Emerald  src/data/items.h           entries in POCKET_KEY_ITEMS
plus every HM in all three games. A hard-coded fallback list is merged in so a
missing or reformatted source file can never make the protection disappear.
"""

import os
import re

# Fallbacks — always protected, even if the source can't be read.
_FALLBACK = {
    "yellow": {
        "TOWN_MAP", "BICYCLE", "SURFBOARD", "SAFARI_BALL", "POKEDEX",
        "BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE", "RAINBOWBADGE",
        "SOULBADGE", "MARSHBADGE", "VOLCANOBADGE", "EARTHBADGE",
        "OLD_AMBER", "DOME_FOSSIL", "HELIX_FOSSIL", "SECRET_KEY",
        "BIKE_VOUCHER", "CARD_KEY", "S_S_TICKET", "GOLD_TEETH",
        "COIN_CASE", "OAKS_PARCEL", "ITEMFINDER", "SILPH_SCOPE",
        "POKE_FLUTE", "LIFT_KEY", "EXP_ALL", "OLD_ROD", "GOOD_ROD",
        "SUPER_ROD",
        "HM_CUT", "HM_FLY", "HM_SURF", "HM_STRENGTH", "HM_FLASH",
    },
    "crystal": {
        "BICYCLE", "OLD_ROD", "GOOD_ROD", "SUPER_ROD", "SQUIRTBOTTLE",
        "MYSTERY_EGG", "CARD_KEY", "MACHINE_PART", "LOST_ITEM", "RED_SCALE",
        "S_S_TICKET", "PASS", "RAINBOW_WING", "SILVER_WING", "BASEMENT_KEY",
        "CLEAR_BELL", "COIN_CASE", "ITEMFINDER", "BLUE_CARD", "TOWN_MAP",
        "EXP_SHARE", "POKE_FLUTE", "SECRETPOTION", "SILVER_LEAF", "GOLD_LEAF",
        "GS_BALL", "EGG_TICKET", "OLD_AMBER", "DOME_FOSSIL", "HELIX_FOSSIL",
        "HM_CUT", "HM_FLY", "HM_SURF", "HM_STRENGTH", "HM_FLASH",
        "HM_WHIRLPOOL", "HM_WATERFALL",
    },
    "emerald": {
        "ITEM_MACH_BIKE", "ITEM_ACRO_BIKE", "ITEM_COIN_CASE", "ITEM_ITEMFINDER",
        "ITEM_OLD_ROD", "ITEM_GOOD_ROD", "ITEM_SUPER_ROD", "ITEM_SS_TICKET",
        "ITEM_CONTEST_PASS", "ITEM_WAILMER_PAIL", "ITEM_DEVON_GOODS",
        "ITEM_SOOT_SACK", "ITEM_BASEMENT_KEY", "ITEM_POKEBLOCK_CASE",
        "ITEM_LETTER", "ITEM_EON_TICKET", "ITEM_RED_ORB", "ITEM_BLUE_ORB",
        "ITEM_SCANNER", "ITEM_GO_GOGGLES", "ITEM_METEORITE",
        "ITEM_ROOM_1_KEY", "ITEM_ROOM_2_KEY", "ITEM_ROOM_4_KEY",
        "ITEM_ROOM_6_KEY", "ITEM_STORAGE_KEY", "ITEM_ROOT_FOSSIL",
        "ITEM_CLAW_FOSSIL", "ITEM_DEVON_SCOPE", "ITEM_MAGMA_EMBLEM",
        "ITEM_OLD_SEA_MAP", "ITEM_AURORA_TICKET", "ITEM_MYSTIC_TICKET",
        "ITEM_POWDER_JAR",
        "ITEM_HM01", "ITEM_HM02", "ITEM_HM03", "ITEM_HM04",
        "ITEM_HM05", "ITEM_HM06", "ITEM_HM07", "ITEM_HM08",
    },
}


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _hms_gb(src):
    text = _read(os.path.join(src, "constants", "item_constants.asm"))
    return {f"HM_{m}" for m in re.findall(r"^\s*add_hm\s+(\w+)", text, re.M)}


def _yellow(src):
    text = _read(os.path.join(src, "data", "items", "key_items.asm"))
    keys = set(re.findall(r"dbit\s+TRUE\s*;\s*(\w+)", text))
    return keys | _hms_gb(src)


def _crystal(src):
    text = _read(os.path.join(src, "data", "items", "attributes.asm"))
    keys = set(re.findall(r";\s*(\w+)\s*\n\s*item_attribute[^\n]*\bKEY_ITEM\b", text))
    return keys | _hms_gb(src)


def _emerald(src):
    text = _read(os.path.join(src, "src", "data", "items.h"))
    keys = set()
    for m in re.finditer(r"\[(ITEM_\w+)\]\s*=\s*\{(.*?)\n\s*\},", text, re.S):
        if "POCKET_KEY_ITEMS" in m.group(2) or re.match(r"ITEM_HM\d", m.group(1)):
            keys.add(m.group(1))
    return keys


_READERS = {"yellow": _yellow, "crystal": _crystal, "emerald": _emerald}
_cache = {}


def key_items(game, source_dir=None):
    """Every item constant that must never be moved or replaced for `game`."""
    game = game.lower()
    ck = (game, os.path.realpath(source_dir) if source_dir else None)
    if ck not in _cache:
        keys = set(_FALLBACK.get(game, set()))
        if source_dir and game in _READERS:
            keys |= _READERS[game](source_dir)
        _cache[ck] = frozenset(keys)
    return _cache[ck]


def check_field_items(game, source_dir, original, randomized, get_item):
    """Last line of defence before anything is written.

    Raises RuntimeError if a randomized field-item list moved or replaced a key
    item, or placed one somewhere new. `get_item(entry)` returns its constant.
    """
    keys = key_items(game, source_dir)
    problems = []
    for o, r in zip(original, randomized):
        a, b = get_item(o), get_item(r)
        if a == b:
            continue
        if a in keys:
            problems.append(f"{a} would be replaced by {b}")
        elif b in keys:
            problems.append(f"{b} would be placed where {a} was")
    if problems:
        raise RuntimeError(
            "Stopped before writing anything: the field-item randomizer tried to "
            "move a key item, which could make the game impossible to finish.\n  "
            + "\n  ".join(problems[:6])
            + "\nYour source folder is untouched. Set Items → Field Items to "
              "Unchanged to continue, and please report this with your "
              "settings_used.json so it can be fixed."
        )
