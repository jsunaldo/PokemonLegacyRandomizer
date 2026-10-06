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
    trainer_similar_strength: bool = False
    trainer_weight_types: bool = False
    trainer_force_fully_evolved: bool = False
    trainer_force_evo_level: int = 30
    # Matched against the party label (e.g. "LtSurgeData", "Rival2Data")
    boss_trainer_classes: tuple = (
        "BROCK", "MISTY", "LTSURGE", "LT_SURGE", "ERIKA", "KOGA", "SABRINA", "BLAINE",
        "GIOVANNI", "LORELEI", "BRUNO", "AGATHA", "LANCE", "RIVAL",
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
    evo_graph: dict = field(default_factory=dict)   # {owner_const: [(target_const, evo_type, param)]}


# ─────────────────────────────────────────────────────────────────────────────
# Field item pools live in item_data (YELLOW_FIELD_ITEM_POOL_FULL / _GOOD).
# The sets below are kept for reference only: KEY_FIELD_ITEMS must NEVER be
# placed in the overworld regardless of the "Ban Bad Items" setting.
# ─────────────────────────────────────────────────────────────────────────────
KEY_FIELD_ITEMS = frozenset({
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
        self._evo_graph: dict = dict(settings.evo_graph or {})
        self._evo_branch_choice: dict = {}

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

    # ── Type helpers (Gen 2 typings from static_data; close enough for Gen 1) ─

    def _type_pool(self, pool: list, weighted: bool = False) -> list:
        """Pick a random type and return the subset of pool having it.
        weighted=True makes common types likelier (avoids tiny pools)."""
        from static_data import POKEMON_TYPES, ALL_TYPES
        if weighted:
            counts: dict = {}
            for pid in pool:
                for t in POKEMON_TYPES.get(pid, ()):
                    counts[t] = counts.get(t, 0) + 1
            if not counts:
                return pool
            types = list(counts)
            chosen = self.rng.choices(types, weights=[counts[t] for t in types], k=1)[0]
        else:
            chosen = self.rng.choice(ALL_TYPES)
        typed = [pid for pid in pool if chosen in POKEMON_TYPES.get(pid, ())]
        return typed if typed else pool

    # ── Evolution helpers ─────────────────────────────────────────────────────

    def set_evolutions(self, evolutions: list):
        """Build the evolution graph used by Force Fully Evolved."""
        graph: dict = {}
        for evo in evolutions:
            graph.setdefault(evo.owner_const, []).append(
                (evo.target_const, evo.evo_type, evo.param))
        self._evo_graph = graph
        self._level_evo_map = self.build_level_evo_map(evolutions)

    def _final_evolution(self, species_const: str) -> str:
        """Follow the evolution graph (any method) to a final form.
        Split lines pick one branch at random, remembered per base."""
        current = species_const
        seen = set()
        while current not in seen:
            seen.add(current)
            options = self._evo_graph.get(current, [])
            if not options:
                break
            if current not in self._evo_branch_choice:
                self._evo_branch_choice[current] = self.rng.choice(options)[0]
            current = self._evo_branch_choice[current]
        return current

    def _force_evolve_party(self, party: list) -> int:
        """Replace under-evolved mons at/above the threshold with their final
        form. Returns the number of mons changed."""
        s = self.settings
        changed = 0
        for mon in party:
            if mon.level < s.trainer_force_evo_level:
                continue
            final = self._final_evolution(mon.species_const)
            if final != mon.species_const and final in POKEMON_CONSTANTS:
                mon.species_const = final
                changed += 1
        return changed

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

        def _copy_with(grp, new_slots):
            new_grp = copy.copy(grp)
            new_grp.slots = new_slots
            return new_grp

        # Catch 'Em All: shuffle the pool once and deal it across every slot
        # so every species appears at least once (pool cycles if needed).
        if rule == "catch_em_all" and mode == "random":
            deck = list(pool)
            self.rng.shuffle(deck)
            i = 0
            result = []
            for grp in wild_groups:
                new_slots = []
                for slot in grp.slots:
                    new_slots.append(WildSlot(slot.level, POKEMON_CONST_NAMES.get(deck[i % len(deck)], slot.species_const)))
                    i += 1
                result.append(_copy_with(grp, new_slots))
            self.log(f"  Catch 'Em All: {i} wild slots dealt from a {len(deck)}-species pool.")
            return result

        # Global 1-to-1 mapping: every original species maps to the same new species
        if mode == "global1to1":
            global_map: dict = {}
            used: set = set()
            result = []
            for grp in wild_groups:
                new_slots = []
                for slot in grp.slots:
                    if slot.species_const not in global_map:
                        new_id = self._pick_by_rule(slot.species_id, pool, rule, exclude=used)
                        used.add(new_id)
                        global_map[slot.species_const] = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                    new_slots.append(WildSlot(slot.level, global_map[slot.species_const]))
                result.append(_copy_with(grp, new_slots))
            self._global_map = global_map
            return result

        # Area 1-to-1: within each group, same species always maps to same new species
        if mode == "area1to1":
            result = []
            for grp in wild_groups:
                area_pool = self._type_pool(pool) if rule == "type_themed" else pool
                area_map: dict = {}
                used: set = set()
                new_slots = []
                for slot in grp.slots:
                    if slot.species_const not in area_map:
                        new_id = self._pick_by_rule(slot.species_id, area_pool, rule, exclude=used)
                        used.add(new_id)
                        area_map[slot.species_const] = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                    new_slots.append(WildSlot(slot.level, area_map[slot.species_const]))
                result.append(_copy_with(grp, new_slots))
            return result

        # Fully random (type themed = one random type per area)
        result = []
        for grp in wild_groups:
            area_pool = self._type_pool(pool) if rule == "type_themed" else pool
            new_slots = []
            for slot in grp.slots:
                new_id = self._pick_by_rule(slot.species_id, area_pool, rule)
                new_slots.append(WildSlot(slot.level, POKEMON_CONST_NAMES.get(new_id, slot.species_const)))
            result.append(_copy_with(grp, new_slots))
        return result

    def _pick_by_rule(self, original_id: int, pool: list, rule: str,
                      exclude: set = None) -> int:
        """Pick a replacement honouring the wild rule. ``exclude`` keeps 1-to-1
        mappings injective while the pool allows it."""
        cands = [p for p in pool if p not in exclude] if exclude else pool
        if not cands:
            cands = pool
        if rule == "similar_strength":
            return self._pick_similar_bst(original_id, cands)
        return self._pick(cands)

    # ── Fishing ───────────────────────────────────────────────────────────────

    def _fish_pick(self, slot_species: str, slot_id: int, pool: list) -> str:
        """Fishing follows the wild settings: global 1-to-1 reuses the land
        mapping, similar-strength stays close in BST, otherwise random."""
        s = self.settings
        if s.wild_mode == "global1to1":
            gmap = getattr(self, "_global_map", None)
            if gmap is None:
                gmap = self._global_map = {}
            if slot_species not in gmap:
                used = {POKEMON_CONSTANTS.get(v, 0) for v in gmap.values()}
                new_id = self._pick_by_rule(slot_id, pool, s.wild_rule, exclude=used)
                gmap[slot_species] = POKEMON_CONST_NAMES.get(new_id, slot_species)
            return gmap[slot_species]
        new_id = self._pick_by_rule(slot_id, pool, s.wild_rule)
        return POKEMON_CONST_NAMES.get(new_id, slot_species)

    def randomize_fishing_simple(self, slots: list, rod_name: str) -> list:
        """Randomize old-rod or good-rod global slot list."""
        s    = self.settings
        pool = self._build_pool(no_legendaries=s.fishing_no_legendaries)
        result = []
        for slot in slots:
            new_const = self._fish_pick(slot.species_const, slot.species_id, pool)
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
                new_const = self._fish_pick(slot.species_const, slot.species_id, pool)
                new_slots.append(SuperRodSlot(new_const, slot.level))
            new_entry = copy.copy(entry)
            new_entry.slots = new_slots
            result.append(new_entry)
        return result

    # ── Trainers ─────────────────────────────────────────────────────────────

    def _trainer_pick(self, orig_id: int, pool: list) -> int:
        if self.settings.trainer_similar_strength:
            return self._pick_similar_bst(orig_id, pool)
        return self._pick(pool)

    def randomize_trainers(self, trainers: list) -> list:
        s = self.settings
        pool_normal = self._build_pool(no_legendaries=s.trainer_no_legendaries)
        pool_boss   = self._build_pool(no_legendaries=s.trainer_boss_no_legendaries)

        # Even distribution: one shuffled deck dealt across every slot in the game
        deck = None
        if s.trainer_mode == "random_even":
            deck = list(pool_normal)
            self.rng.shuffle(deck)
        deal = 0

        result = []
        replaced = forced = 0
        for trainer in trainers:
            is_boss = self._is_boss(trainer)
            pool    = pool_boss if is_boss else pool_normal

            # Type themed: one random type per trainer (all trainers, or bosses only)
            themed = (s.trainer_mode == "type_themed" or
                      (s.trainer_mode == "type_themed_boss" and is_boss))
            if themed:
                pool = self._type_pool(pool, weighted=s.trainer_weight_types)

            new_party = []
            for mon in trainer.party:
                if deck is not None:
                    new_id = deck[deal % len(deck)]
                    deal += 1
                else:
                    new_id = self._trainer_pick(mon.species_id, pool)
                new_const = POKEMON_CONST_NAMES.get(new_id, mon.species_const)
                new_party.append(TrainerPokemon(level=mon.level, species_const=new_const))
                replaced += 1

            if s.trainer_force_fully_evolved:
                forced += self._force_evolve_party(new_party)

            new_trainer       = copy.copy(trainer)
            new_trainer.party = new_party
            result.append(new_trainer)

        label = {"random_even": "Even distribution", "type_themed": "Type themed",
                 "type_themed_boss": "Type themed (bosses)"}.get(s.trainer_mode, "Random")
        self.log(f"  {label}: {replaced} Pokémon replaced across {len(result)} trainers.")
        if s.trainer_force_fully_evolved:
            self.log(f"  Force fully evolved (lv ≥ {s.trainer_force_evo_level}): {forced} Pokémon evolved.")
        return result

    # ── Static encounters ─────────────────────────────────────────────────────

    def randomize_static(self, encounters: list) -> list:
        s    = self.settings
        # "random" = anything goes; swap / similar-strength keep gifts non-legendary
        pool = self._build_pool(no_legendaries=(s.static_mode != "random"))

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
        """
        Modes: shuffle (redistribute existing items), random (each slot from
        the pool), random_even (pool dealt evenly). Key items are never in
        the pool; "Ban Bad Items" additionally drops cheap consumables.
        """
        from item_data import YELLOW_FIELD_ITEM_POOL_FULL, YELLOW_FIELD_ITEM_POOL_GOOD
        s = self.settings
        mode = s.field_items_mode
        pool = list(YELLOW_FIELD_ITEM_POOL_GOOD if s.field_items_ban_bad
                    else YELLOW_FIELD_ITEM_POOL_FULL)
        if not pool:
            pool = list(GOOD_FIELD_ITEMS)

        if mode == "shuffle":
            consts = [i.item_const for i in items]
            self.rng.shuffle(consts)
            picks = consts
        elif mode == "random_even":
            deck = list(pool)
            self.rng.shuffle(deck)
            picks = [deck[i % len(deck)] for i in range(len(items))]
        else:
            picks = [self.rng.choice(pool) for _ in items]

        result = []
        for item, new_const in zip(items, picks):
            if new_const != item.item_const:
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
