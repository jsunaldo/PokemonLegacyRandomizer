"""
Pokemon Yellow Legacy Randomizer - Randomization Engine

Applies randomization settings to parsed Yellow Legacy data structures.
Gen 1 only — no Gen 2 filtering, no baby ban, no time-based encounters.
"""

import random
import copy
from dataclasses import dataclass, field
from typing import Optional

from constants_yellow import (
    POKEMON_CONSTANTS, POKEMON_CONST_NAMES, POKEMON_NAMES,
    LEGENDARY_IDS, BASIC_WITH_TWO_EVOLUTIONS, MIDDLE_STAGE_IDS,
    YELLOW_HM_CONSTS,
)
from static_data import POKEMON_BST, POKEMON_TYPES, POKEMON_CATCH_RATES
from parser_yellow import (
    WildSlot, WildEncounterGroup, TrainerPokemon, Trainer,
    StarterLocation, InGameTrade, EvolutionEntry, StaticEncounter,
    FieldItem, FishSlot, SuperRodSlot, SuperRodEntry, TMHMCompatEntry,
)


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class YellowRandomizerSettings:
    seed: Optional[int] = None

    # Starter — the Pokémon Oak gives at game start (replaces Pikachu in party)
    starter_mode: str = "unchanged"       # unchanged | random | random_two_stage | custom
    starter_no_legendaries: bool = True
    custom_starter: Optional[str] = None  # ASM const name for custom mode

    # Wild
    wild_mode: str = "random"             # unchanged | random | area1to1 | global1to1
    wild_rule: str = "none"               # none | similar_strength | catch_em_all | type_themed
    wild_no_legendaries: bool = False

    # Fishing (follows wild_mode; no separate toggle)
    fishing_mode: str = "random"
    fishing_no_legendaries: bool = False

    # Trainers
    trainer_mode: str = "random"          # unchanged | random | random_even | type_themed | type_themed_boss
    trainer_no_legendaries: bool = False
    trainer_boss_no_legendaries: bool = True
    trainer_force_fully_evolved: bool = False
    trainer_force_evo_level: int = 30
    boss_trainer_classes: tuple = (
        "BROCK", "MISTY", "LT_SURGE", "ERIKA", "KOGA", "SABRINA", "BLAINE", "GIOVANNI",
        "LORELEI", "BRUNO", "AGATHA", "LANCE", "BLUE", "RED",
        "GYM", "ELITE", "CHAMPION",
    )

    # Static Pokémon
    static_mode: str = "unchanged"        # unchanged | random | similar_strength

    # Trades
    trade_mode: str = "unchanged"         # unchanged | given_only | both
    trade_random_nicknames: bool = False
    trade_random_ot: bool = False         # no-op (Yellow has no OT in trade data)

    # Field items
    field_items_mode: str = "unchanged"   # unchanged | random
    field_items_ban_bad: bool = True

    # Easier evolutions (trade evos → level, high-level items → lower level)
    easier_evolutions: bool = False

    # Full HM compatibility (all species can learn all 5 Gen 1 HMs)
    full_hm_compat: bool = False

    # Starting state
    randomize_start_items: bool = False
    start_items: list = field(default_factory=list)   # [{const, qty}, ...]
    start_pc_items: list = field(default_factory=list)

    # Shop items
    zero_grinding: bool = False
    elite4_prep: bool = False

    # Internal runtime state
    _level_evo_map: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Bad field items (key items, quest items, evolution stones used as key items)
# ─────────────────────────────────────────────────────────────────────────────
BAD_FIELD_ITEMS = frozenset({
    "TOWN_MAP", "BICYCLE", "SURFBOARD", "SAFARI_BALL", "POKEDEX",
    "MOON_STONE", "BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE",
    "RAINBOWBADGE", "SOULBADGE", "MARSHBADGE", "VOLCANOBADGE", "EARTHBADGE",
    "OLD_AMBER", "FIRE_STONE", "THUNDER_STONE", "WATER_STONE", "LEAF_STONE",
    "DOME_FOSSIL", "HELIX_FOSSIL", "SECRET_KEY", "ITEM_2C", "BIKE_VOUCHER",
    "CARD_KEY", "ITEM_32", "COIN", "S_S_TICKET", "GOLD_TEETH",
    "COIN_CASE", "OAKS_PARCEL", "ITEMFINDER", "SILPH_SCOPE", "POKE_FLUTE",
    "LIFT_KEY", "OLD_ROD", "GOOD_ROD", "SUPER_ROD",
    "FLOOR_B2F", "FLOOR_B1F", "FLOOR_1F", "FLOOR_2F", "FLOOR_3F",
    "FLOOR_4F", "FLOOR_5F", "FLOOR_6F", "FLOOR_7F", "FLOOR_8F",
    "FLOOR_9F", "FLOOR_10F", "FLOOR_11F", "FLOOR_B4F",
    "EXP_ALL",
})

GOOD_FIELD_ITEMS = [
    "ULTRA_BALL", "GREAT_BALL", "POKE_BALL",
    "FULL_RESTORE", "MAX_POTION", "HYPER_POTION", "SUPER_POTION", "POTION",
    "ANTIDOTE", "BURN_HEAL", "ICE_HEAL", "AWAKENING", "PARLYZ_HEAL", "FULL_HEAL",
    "REVIVE", "MAX_REVIVE",
    "ESCAPE_ROPE", "REPEL", "SUPER_REPEL", "MAX_REPEL",
    "HP_UP", "PROTEIN", "IRON", "CARBOS", "CALCIUM",
    "RARE_CANDY", "NUGGET", "POKE_DOLL",
    "GUARD_SPEC", "DIRE_HIT", "X_ATTACK", "X_DEFEND", "X_SPEED", "X_SPECIAL", "X_ACCURACY",
    "FRESH_WATER", "SODA_POP", "LEMONADE",
    "MAX_ETHER", "MAX_ELIXER", "ETHER", "ELIXER",
    "PP_UP",
]

# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class YellowRandomizerEngine:
    def __init__(self, settings: YellowRandomizerSettings, log_fn=None):
        self.settings = settings
        self.log = log_fn or print
        self.rng = random.Random(settings.seed)
        self._level_evo_map: dict = {}

    # ── Pool helpers ──────────────────────────────────────────────────────────

    def _build_pool(self, no_legendaries=True) -> list[int]:
        """Build list of valid Gen 1 species dex IDs."""
        pool = []
        for const, idx in POKEMON_CONSTANTS.items():
            if no_legendaries and idx in LEGENDARY_IDS:
                continue
            pool.append(idx)
        return pool

    def _pick(self, pool: list) -> int:
        return self.rng.choice(pool)

    @staticmethod
    def _bst(dex_id: int, default: int = 400) -> int:
        """BST lookup. POKEMON_BST is a list indexed by dex number (#1–251)."""
        if isinstance(dex_id, int) and 0 <= dex_id < len(POKEMON_BST):
            val = POKEMON_BST[dex_id]
            return val if val else default
        return default

    def _pick_similar_bst(self, original_id: int, pool: list,
                          tolerance: int = 20) -> int:
        """Pick a species with similar BST to original, widening window if needed."""
        target_bst = self._bst(original_id)
        for tol in [tolerance, tolerance * 2, tolerance * 4, 9999]:
            candidates = [p for p in pool
                          if abs(self._bst(p, 0) - target_bst) <= tol]
            if candidates:
                return self.rng.choice(candidates)
        return self.rng.choice(pool)

    def _is_boss(self, trainer: Trainer) -> bool:
        name_up = trainer.name.upper()
        return any(kw in name_up for kw in self.settings.boss_trainer_classes)

    # ── Evolution helpers ─────────────────────────────────────────────────────

    def build_level_evo_map(self, evolutions: list) -> dict:
        """
        Build {species_const → min_level_to_be_fully_evolved} for
        the "force fully evolved" trainer feature.
        """
        # Build a mapping: target_const → owner_const and level required
        evo_map: dict[str, tuple[str, int]] = {}  # target → (owner, level_req)
        for evo in evolutions:
            if evo.evo_type == 'EVOLVE_LEVEL':
                try:
                    lv = int(evo.param)
                    evo_map[evo.target_const] = (evo.owner_const, lv)
                except ValueError:
                    pass

        # For each species, compute the minimum level to be the final form
        result: dict[str, int] = {}
        for const in POKEMON_CONSTANTS:
            if const in evo_map:
                # It's evolved from something — minimum level to be this form
                _, lv_req = evo_map[const]
                result[const] = lv_req
            else:
                result[const] = 1  # no evolution requirement

        return result

    def _final_evo_level(self, species_const: str) -> int:
        """Return the minimum level at which this species is fully evolved."""
        return self._level_evo_map.get(species_const, 1)

    def _has_evolution(self, species_const: str, evolutions: list) -> bool:
        """Return True if this species has at least one evolution entry."""
        return any(e.owner_const == species_const for e in evolutions)

    # ── Starters ─────────────────────────────────────────────────────────────

    def _pick_species_const(self, mode: str, custom_const: Optional[str],
                            no_legendaries: bool, label: str) -> str:
        """
        Shared chooser for a single species constant given a mode.
          mode: unchanged|custom|random|random_two_stage
        Returns an ASM constant string (defaults to PIKACHU on failure).
        """
        pool = self._build_pool(no_legendaries=no_legendaries)

        if mode == "custom" and custom_const:
            if custom_const in POKEMON_CONSTANTS:
                chosen = POKEMON_CONSTANTS[custom_const]
            else:
                chosen = self._pick(pool)
        elif mode == "random_two_stage":
            pool2 = [p for p in pool if p in BASIC_WITH_TWO_EVOLUTIONS]
            chosen = self._pick(pool2 if pool2 else pool)
        else:  # random
            chosen = self._pick(pool)

        new_const = POKEMON_CONST_NAMES.get(chosen, "PIKACHU")
        self.log(f"  {label} → {new_const} ({POKEMON_NAMES[chosen]})")
        return new_const

    def randomize_starter(self, starters: list = None) -> str:
        """The starter Oak gives at game start (Starter tab)."""
        s = self.settings
        return self._pick_species_const(
            s.starter_mode, s.custom_starter, s.starter_no_legendaries, "Oak starter")

    # ── Wild Pokémon ──────────────────────────────────────────────────────────

    def randomize_wild(self, wild_groups: list) -> list:
        s    = self.settings
        pool = self._build_pool(no_legendaries=s.wild_no_legendaries)
        mode = s.wild_mode
        rule = s.wild_rule

        # Global 1-to-1 mapping: every original species maps to the same new species
        if mode == "global1to1":
            global_map: dict[str, str] = {}
            result = []
            for grp in wild_groups:
                new_slots = []
                for slot in grp.slots:
                    if slot.species_const not in global_map:
                        new_id = self._pick_by_rule(slot.species_id, pool, rule)
                        global_map[slot.species_const] = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                    new_slots.append(WildSlot(slot.level, global_map[slot.species_const]))
                new_grp = copy.copy(grp)
                new_grp.slots = new_slots
                result.append(new_grp)
            return result

        # Area 1-to-1: within each group, same species always maps to same new species
        if mode == "area1to1":
            result = []
            for grp in wild_groups:
                area_map: dict[str, str] = {}
                new_slots = []
                for slot in grp.slots:
                    if slot.species_const not in area_map:
                        new_id = self._pick_by_rule(slot.species_id, pool, rule)
                        area_map[slot.species_const] = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                    new_slots.append(WildSlot(slot.level, area_map[slot.species_const]))
                new_grp = copy.copy(grp)
                new_grp.slots = new_slots
                result.append(new_grp)
            return result

        # Fully random
        result = []
        for grp in wild_groups:
            new_slots = []
            for slot in grp.slots:
                new_id = self._pick_by_rule(slot.species_id, pool, rule)
                new_slots.append(WildSlot(slot.level, POKEMON_CONST_NAMES.get(new_id, slot.species_const)))
            new_grp = copy.copy(grp)
            new_grp.slots = new_slots
            result.append(new_grp)
        return result

    def _pick_by_rule(self, original_id: int, pool: list, rule: str) -> int:
        if rule == "similar_strength":
            return self._pick_similar_bst(original_id, pool)
        if rule == "catch_em_all":
            return self._pick(pool)  # caller handles uniqueness if desired
        if rule == "type_themed":
            # Match primary type of original
            from static_data import POKEMON_TYPES
            orig_types = POKEMON_TYPES.get(original_id, ("normal", "normal"))
            orig_type  = orig_types[0]
            typed_pool = [p for p in pool if POKEMON_TYPES.get(p, ("normal",))[0] == orig_type]
            if typed_pool:
                return self.rng.choice(typed_pool)
        return self._pick(pool)

    # ── Fishing ───────────────────────────────────────────────────────────────

    def randomize_fishing_simple(self, slots: list, rod_name: str) -> list:
        """Randomize old-rod or good-rod global slot list."""
        s    = self.settings
        pool = self._build_pool(no_legendaries=s.fishing_no_legendaries)
        result = []
        for slot in slots:
            new_id    = self._pick(pool)
            new_const = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
            self.log(f"  {rod_name}: {slot.species_const} → {new_const}")
            result.append(FishSlot(slot.level, new_const))
        return result

    def randomize_super_rod(self, entries: list) -> list:
        """Randomize super-rod entries (4 species per location)."""
        s    = self.settings
        pool = self._build_pool(no_legendaries=s.fishing_no_legendaries)
        result = []
        for entry in entries:
            new_slots = []
            for slot in entry.slots:
                new_id    = self._pick(pool)
                new_const = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                new_slots.append(SuperRodSlot(new_const, slot.level))
            new_entry = copy.copy(entry)
            new_entry.slots = new_slots
            result.append(new_entry)
        return result

    # ── Trainers ─────────────────────────────────────────────────────────────

    def randomize_trainers(self, trainers: list) -> list:
        s = self.settings

        result = []
        for trainer in trainers:
            is_boss = self._is_boss(trainer)
            no_leg  = s.trainer_boss_no_legendaries if is_boss else s.trainer_no_legendaries
            pool    = self._build_pool(no_legendaries=no_leg)

            new_party = []
            for mon in trainer.party:
                orig_id = mon.species_id

                if s.trainer_mode in ("random", "random_even"):
                    new_id = self._pick(pool)
                elif s.trainer_mode == "type_themed":
                    from static_data import POKEMON_TYPES
                    orig_types = POKEMON_TYPES.get(orig_id, ("normal", "normal"))
                    typed_pool = [p for p in pool
                                  if POKEMON_TYPES.get(p, ("normal",))[0] == orig_types[0]]
                    new_id = self.rng.choice(typed_pool) if typed_pool else self._pick(pool)
                elif s.trainer_mode == "type_themed_boss" and is_boss:
                    from static_data import POKEMON_TYPES
                    orig_types = POKEMON_TYPES.get(orig_id, ("normal", "normal"))
                    typed_pool = [p for p in pool
                                  if POKEMON_TYPES.get(p, ("normal",))[0] == orig_types[0]]
                    new_id = self.rng.choice(typed_pool) if typed_pool else self._pick(pool)
                else:
                    new_id = self._pick(pool)

                new_const = POKEMON_CONST_NAMES.get(new_id, mon.species_const)
                level     = mon.level

                # Force fully evolved: push species to final evo if level is high enough
                if s.trainer_force_fully_evolved and self._level_evo_map:
                    min_lv = self._final_evo_level(new_const)
                    if level >= s.trainer_force_evo_level and min_lv > level:
                        # Find a species in pool that IS fully evolved at this level
                        alt_pool = [p for p in pool
                                    if self._final_evo_level(POKEMON_CONST_NAMES.get(p, '')) <= level]
                        if alt_pool:
                            new_id    = self.rng.choice(alt_pool)
                            new_const = POKEMON_CONST_NAMES.get(new_id, new_const)

                new_party.append(TrainerPokemon(level=level, species_const=new_const))

            new_trainer       = copy.copy(trainer)
            new_trainer.party = new_party
            result.append(new_trainer)
        return result

    # ── Static encounters ─────────────────────────────────────────────────────

    def randomize_static(self, encounters: list) -> list:
        s    = self.settings
        pool = self._build_pool(no_legendaries=True)  # always exclude legendaries for static

        result = []
        for enc in encounters:
            orig_id = POKEMON_CONSTANTS.get(enc.species_const, 143)

            if s.static_mode == "similar_strength":
                new_id = self._pick_similar_bst(orig_id, pool)
            else:
                new_id = self._pick(pool)

            new_const = POKEMON_CONST_NAMES.get(new_id, enc.species_const)
            self.log(f"  Static: {enc.species_const} → {new_const} ({enc.encounter_type})")
            new_enc               = copy.copy(enc)
            new_enc.species_const = new_const
            result.append(new_enc)
        return result

    # ── In-game trades ────────────────────────────────────────────────────────

    _NICKNAME_POOL = [
        "ACE", "BOLT", "BYTE", "CHIP", "CLAW", "COMET", "CREST", "DUSK",
        "ECHO", "FANG", "FIRE", "FLASH", "FLINT", "FUSE", "GEAR", "GLOW",
        "HAZE", "JADE", "JOLT", "LENS", "MIST", "NOVA", "ONYX", "PIXEL",
        "PULSE", "RAZOR", "RUNE", "RUSH", "SHADOW", "SHARD", "SONIC",
        "SPARK", "SPIKE", "SPIN", "STAR", "STORM", "SWIFT", "TIDE", "VOLT",
        "WAVE", "WILD", "WIND", "ZEAL", "ZERO", "ZEST", "ZINC", "ZONE",
    ]

    def randomize_trades(self, trades: list) -> list:
        s    = self.settings
        pool = self._build_pool(no_legendaries=True)
        result = []

        for trade in trades:
            new_trade = copy.copy(trade)

            if s.trade_mode in ("given_only", "both"):
                new_id              = self._pick(pool)
                new_trade.given_species = POKEMON_CONST_NAMES.get(new_id, trade.given_species)
                self.log(f"  Trade give: {trade.given_species} → {new_trade.given_species}")

            if s.trade_mode == "both":
                new_id              = self._pick(pool)
                new_trade.requested_species = POKEMON_CONST_NAMES.get(new_id, trade.requested_species)
                self.log(f"  Trade get:  {trade.requested_species} → {new_trade.requested_species}")

            if s.trade_random_nicknames:
                new_trade.nickname = self.rng.choice(self._NICKNAME_POOL)[:10]

            # trade_random_ot is a no-op for Yellow (no OT field in trade data)

            result.append(new_trade)
        return result

    # ── Field items ───────────────────────────────────────────────────────────

    def randomize_field_items(self, items: list) -> list:
        s = self.settings
        if s.field_items_ban_bad:
            pool = [i for i in GOOD_FIELD_ITEMS]
        else:
            pool = GOOD_FIELD_ITEMS + list(BAD_FIELD_ITEMS)

        result = []
        for item in items:
            new_const = self.rng.choice(pool)
            self.log(f"  Field item: {item.item_const} → {new_const}")
            new_item            = copy.copy(item)
            new_item.item_const = new_const
            result.append(new_item)
        return result

    # ── Evolutions ────────────────────────────────────────────────────────────

    def apply_evolution_changes(self, evolutions: list) -> list:
        """
        Easier Evolutions for Yellow:
          - EVOLVE_TRADE → EVOLVE_LEVEL at level 37
            (Yellow Legacy already converts trades to level, but handle in case)
          - High-level EVOLVE_LEVEL entries cap at sensible levels:
              mid-stage target → max level 30
              final-stage target → max level 40
        """
        result = []
        for evo in evolutions:
            new_evo = copy.copy(evo)

            if evo.evo_type == 'EVOLVE_TRADE':
                # Convert to level evo at 37
                new_evo.evo_type = 'EVOLVE_LEVEL'
                new_evo.param    = '37'
                new_evo.min_level = ''

            elif evo.evo_type == 'EVOLVE_LEVEL':
                try:
                    lv = int(evo.param)
                    target_id = POKEMON_CONSTANTS.get(evo.target_const, 0)
                    # Is the target a middle-stage species?
                    cap = 30 if target_id in MIDDLE_STAGE_IDS else 40
                    if lv > cap:
                        new_evo.param = str(cap)
                except ValueError:
                    pass

            result.append(new_evo)
        return result

    # ── TM/HM compatibility ───────────────────────────────────────────────────

    # Gen 1 HM moves (the tmhm macro takes move NAMES, not bytes)
    _HM_MOVES = ["CUT", "FLY", "SURF", "STRENGTH", "FLASH"]

    def apply_full_hm_compat(self, tmhm: list) -> list:
        """
        Make every species learn all 5 Gen 1 HMs by appending the HM move
        names (CUT, FLY, SURF, STRENGTH, FLASH) to each species' `tmhm`
        macro argument list.  Yellow's tmhm macro takes move names and
        computes the compatibility bitfield itself, so we just add any HM
        names not already present.
        """
        result = []
        for entry in tmhm:
            new_entry = copy.copy(entry)
            names = list(entry.move_names or [])
            for hm in self._HM_MOVES:
                if hm not in names:
                    names.append(hm)
            new_entry.move_names = names
            result.append(new_entry)
        return result
