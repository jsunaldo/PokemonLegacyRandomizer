"""
Pokemon Crystal Legacy Randomizer - Randomization Engine

Applies randomization settings to parsed data structures.
All operations return modified copies; originals are not mutated.
"""

import random
import copy
from dataclasses import dataclass, field
from typing import Optional
from constants import (
    POKEMON_CONSTANTS, POKEMON_CONST_NAMES, POKEMON_NAMES,
    LEGENDARY_IDS, BABY_IDS, DEFAULT_STARTERS, BASIC_WITH_TWO_EVOLUTIONS,
    MIDDLE_STAGE_IDS,
)
from parser import (
    WildSlot, WildEncounterGroup, TrainerPokemon, Trainer, StarterLocation,
    EvolutionEntry, WildHeldItemEntry, TMHMCompatEntry,
    FieldItemEntry, FishSlot,
)


@dataclass
class RandomizerSettings:
    # Seed (None = use system random)
    seed: Optional[int] = None

    # Starters
    # Mode: "unchanged" | "custom" | "random" | "random_two_stage"
    starter_mode: str = "random"
    starters_no_legendaries: bool = True
    starters_no_babies: bool = True
    custom_starters: list = field(default_factory=list)  # [id, id, id] for custom mode
    starter_random_items: bool = False   # replace held items in starter givepoke calls
    starter_ban_bad_items: bool = True   # only use high-quality items when randomizing

    # Evolutions
    easier_evolutions: bool = False   # trade evolutions → level 37
    remove_time_evolutions: bool = False  # HAPPINESS_DAY/NIGHT → HAPPINESS

    # Movesets
    full_hm_compat: bool = False      # every Pokémon can learn every HM

    # In-game trades
    # Mode: "unchanged" | "given_only" | "both"
    trade_mode: str = "unchanged"
    trade_random_nicknames: bool = False
    trade_random_ot: bool = False
    trade_random_ivs: bool = False
    trade_random_items: bool = False

    # Static Pokemon
    # Mode: "unchanged" | "swap" | "random" | "similar_strength"
    static_mode: str = "unchanged"
    static_gen1_only: bool = False
    static_gen2_only: bool = False

    # Wild Pokemon
    # Mode:  "unchanged" | "random" | "area1to1" | "global1to1"
    # Rule:  "none" | "similar_strength" | "catch_em_all" | "type_themed"
    wild_mode: str = "random"
    wild_rule: str = "none"
    wild_gen1_only: bool = False
    wild_gen2_only: bool = False
    # Extra options
    wild_use_time_based: bool = True    # if False, all time periods share same species
    wild_no_legendaries: bool = False   # exclude legendaries from wild pool
    wild_random_held_items: bool = False
    wild_ban_bad_held_items: bool = True

    # Trainers
    # Mode: "unchanged"|"random"|"random_even"|"type_themed"|"type_themed_boss"
    trainer_mode: str = "random"
    trainer_no_legendaries: bool = False
    trainer_no_babies: bool = True
    trainer_boss_no_legendaries: bool = True   # gym leaders, e4 use stricter pool
    trainer_gen1_only: bool = False
    trainer_gen2_only: bool = False
    # Additional options
    trainer_similar_strength: bool = False     # prefer similar BST replacements
    trainer_rival_starter: bool = False        # rival always carries a starter
    trainer_weight_types: bool = False         # weight type theme by # of pokemon (type_themed only)
    trainer_force_fully_evolved: bool = False  # force final evo at or above threshold level
    trainer_force_evo_level: int = 30          # threshold for force-fully-evolved (30–65)
    rival_starter_ids: list = field(default_factory=list)   # [id,id,id] populated at runtime
    rival_level_evo_map: dict = field(default_factory=dict) # from parser.level_evo_map

    # Field items
    # Mode: "unchanged" | "random"
    field_items_mode: str = "unchanged"
    field_items_ban_bad: bool = True

    # What counts as "boss" trainers (trainer class prefixes)
    boss_trainer_classes: tuple = (
        "LEADER_", "CHAMPION_", "ROCKET_EXEC", "ELITE_", "RIVAL",
        "FALKNER", "BUGSY", "WHITNEY", "MORTY", "CHUCK", "JASMINE",
        "PRYCE", "CLAIR", "WILL", "KOGA", "BRUNO", "KAREN", "LANCE",
        "LT_SURGE", "MISTY", "BROCK", "ERIKA", "JANINE", "SABRINA",
        "BLAINE", "BLUE",
    )
    # What counts specifically as rival (for rival starter feature)
    rival_trainer_keywords: tuple = ("RIVAL", "SILVER", "KAMON", "HUGO")


class RandomizerEngine:
    def __init__(self, settings: RandomizerSettings, log_fn=None):
        self.settings = settings
        self.log = log_fn or print
        self.rng = random.Random(settings.seed)

    def _build_pool(self, no_legendaries=True, no_babies=False,
                    gen1_only=False, gen2_only=False) -> list:
        """Build a list of valid species IDs based on filter settings."""
        pool = []
        for const, idx in POKEMON_CONSTANTS.items():
            if no_legendaries and idx in LEGENDARY_IDS:
                continue
            if no_babies and idx in BABY_IDS:
                continue
            if gen1_only and idx > 151:
                continue
            if gen2_only and idx < 152:
                continue
            pool.append(idx)
        return pool

    def _pick(self, pool: list) -> int:
        return self.rng.choice(pool)

    # -------------------------------------------------------------------------
    # Evolutions
    # -------------------------------------------------------------------------

    # Level types (with and without EVOLVE_ prefix)
    _LEVEL_TYPES = frozenset({"LEVEL", "EVOLVE_LEVEL"})
    # Trade types — kept in case any remain in the source
    _TRADE_TYPES = frozenset({"TRADE", "EVOLVE_TRADE", "TRADE_ITEM", "EVOLVE_TRADE_ITEM"})
    # Time-based types
    _DAY_TYPES   = frozenset({"HAPPINESS_DAY",   "EVOLVE_HAPPINESS_DAY"})
    _NIGHT_TYPES = frozenset({"HAPPINESS_NIGHT", "EVOLVE_HAPPINESS_NIGHT"})

    def _level_type(self, raw: str) -> str:
        """Return the LEVEL constant matching the prefix style of raw."""
        return "EVOLVE_LEVEL" if raw.startswith("EVOLVE_") else "LEVEL"

    def _item_type(self, raw: str) -> str:
        """Return the ITEM constant matching the prefix style of raw."""
        return "EVOLVE_ITEM" if raw.startswith("EVOLVE_") else "ITEM"

    def apply_evolution_changes(self, entries: list) -> list:
        """
        Returns a modified copy of the EvolutionEntry list.

        Make Evolutions Easier
        ─────────────────────
        Caps level-up evolutions:
          • If the target Pokémon is a middle stage (still evolves further) → cap at level 30
          • If the target Pokémon is a final stage → cap at level 40
        Also converts any remaining TRADE / TRADE_ITEM entries to LEVEL with the
        same cap (Crystal Legacy usually pre-converts these, but some may remain).

        Remove Time-Based Evolutions
        ────────────────────────────
        Replaces day/night happiness evolutions with stone evolutions:
          • HAPPINESS_DAY  (e.g. Eevee→Espeon)  → ITEM + SUN_STONE
          • HAPPINESS_NIGHT (e.g. Eevee→Umbreon) → ITEM + MOON_STONE
        """
        s = self.settings
        new_entries = copy.deepcopy(entries)

        level_capped  = 0
        trade_fixed   = 0
        time_changed  = 0

        for entry in new_entries:
            t = entry.evo_type   # uppercased by parser

            # ── Make Evolutions Easier ────────────────────────────────────────
            if s.easier_evolutions and t in (self._LEVEL_TYPES | self._TRADE_TYPES):
                target_id  = POKEMON_CONSTANTS.get(entry.target, 0)
                is_middle  = target_id in MIDDLE_STAGE_IDS
                cap        = 30 if is_middle else 40

                if t in self._TRADE_TYPES:
                    # Convert trade → level with appropriate cap
                    entry.evo_type = self._level_type(t)
                    entry.param    = str(cap)
                    trade_fixed += 1
                else:
                    # Level evolution — only lower if currently above cap
                    try:
                        current = int(entry.param)
                        if current > cap:
                            entry.param = str(cap)
                            level_capped += 1
                    except ValueError:
                        pass   # param is not numeric — skip

            # ── Remove Time-Based Evolutions ──────────────────────────────────
            if s.remove_time_evolutions:
                if t in self._DAY_TYPES:
                    entry.evo_type = self._item_type(t)
                    entry.param    = "SUN_STONE"
                    time_changed  += 1
                elif t in self._NIGHT_TYPES:
                    entry.evo_type = self._item_type(t)
                    entry.param    = "MOON_STONE"
                    time_changed  += 1

        if level_capped:
            self.log(f"  Level evolutions capped (≤30 mid-stage, ≤40 final): "
                     f"{level_capped} entry/entries changed.")
        if trade_fixed:
            self.log(f"  Trade evolutions converted to level (with cap): "
                     f"{trade_fixed} entry/entries changed.")
        if time_changed:
            self.log(f"  Time-based evolutions → item (Sun Stone / Moon Stone): "
                     f"{time_changed} entry/entries changed.")
        return new_entries

    # -------------------------------------------------------------------------
    # TM/HM compatibility
    # -------------------------------------------------------------------------

    def apply_full_hm_compat(self, entries: list) -> list:
        """
        Ensure every Pokémon can learn every HM move.

        Strategy
        ────────
        1. First pass over all entries: collect every constant that looks like
           an HM (starts with ``HM_`` or ``HM`` followed by digits, case-
           insensitive).  This auto-detects whatever naming convention Crystal
           Legacy uses (HM_01/HM_02 or HM_CUT/HM_FLY etc.) without hard-coding
           a fixed list.
        2. Second pass: for any entry missing one or more HM constants, append
           the missing ones.  Already-compatible Pokémon are untouched.

        Like the UPR feature, this has no effect on TM learnability — only the
        HM entries are touched.
        """
        # Crystal Legacy (pret disassembly) uses plain move names in tmhm macros,
        # not HM_01/HM_CUT-style constants.  Hard-code the Gen 2 HM set.
        all_hm_constants: set = {
            'CUT', 'FLY', 'SURF', 'STRENGTH', 'FLASH', 'WHIRLPOOL', 'WATERFALL'
        }

        self.log(f"  Full HM Compatibility: HMs detected: "
                 f"{', '.join(sorted(all_hm_constants))}")

        # Pass 2 — add missing HMs to each entry
        new_entries = copy.deepcopy(entries)
        updated = 0
        for entry in new_entries:
            existing_upper = {mv.upper() for mv in entry.moves}
            missing = sorted(hm for hm in all_hm_constants if hm not in existing_upper)
            if missing:
                # Preserve the original casing of the first occurrence we saw
                # (upper-case is fine because pokecrystal constants are upper-case)
                entry.moves.extend(missing)
                updated += 1

        self.log(f"  Full HM Compatibility: {updated} Pokémon given full HM learnability "
                 f"({len(entries) - updated} already compatible).")
        return new_entries

    # -------------------------------------------------------------------------
    # Starters
    # -------------------------------------------------------------------------

    def randomize_starters(self, starters: list) -> list:
        """
        Returns a new list of StarterLocation with updated species_const.
        Expects exactly 3 StarterLocation objects.
        Modes:
          unchanged        — return originals untouched
          custom           — use s.custom_starters [id, id, id]
          random           — pick 3 distinct from global pool
          random_two_stage — pick 3 distinct from basic-with-2-evolutions pool
        """
        if not starters or len(starters) != 3:
            self.log("[WARN] Could not randomize starters: expected 3 locations.")
            return starters

        s = self.settings
        new_starters = copy.deepcopy(starters)

        if s.starter_mode == "unchanged":
            self.log("  Starters: unchanged.")
            return new_starters

        if s.starter_mode == "custom":
            if len(s.custom_starters) == 3 and all(i > 0 for i in s.custom_starters):
                chosen_ids = s.custom_starters
                self.log(f"  Starters (custom): {[POKEMON_NAMES[i] for i in chosen_ids]}")
            else:
                self.log("[WARN] Custom starters not set properly; leaving unchanged.")
                return new_starters

        elif s.starter_mode == "random_two_stage":
            # Build pool from the "basic with 2 evolutions" set, then apply global gen filter
            base_pool = list(BASIC_WITH_TWO_EVOLUTIONS)
            if s.wild_gen1_only:
                base_pool = [i for i in base_pool if i <= 151]
            elif s.wild_gen2_only:
                base_pool = [i for i in base_pool if i >= 152]
            # Apply legendary / baby filters (mostly redundant for this set, but safe)
            if s.starters_no_legendaries:
                base_pool = [i for i in base_pool if i not in LEGENDARY_IDS]
            if s.starters_no_babies:
                base_pool = [i for i in base_pool if i not in BABY_IDS]

            if len(base_pool) < 3:
                self.log("[WARN] Two-stage pool too small after filtering; falling back to full random.")
                base_pool = self._build_pool(
                    no_legendaries=s.starters_no_legendaries,
                    no_babies=s.starters_no_babies,
                    gen1_only=s.wild_gen1_only,
                    gen2_only=s.wild_gen2_only,
                )

            chosen_ids = []
            for _ in range(3):
                remaining = [p for p in base_pool if p not in chosen_ids]
                if not remaining:
                    remaining = base_pool
                chosen_ids.append(self._pick(remaining))
            self.log(f"  Starters (random 2-evo): {[POKEMON_NAMES[i] for i in chosen_ids]}")

        else:  # "random" (completely)
            pool = self._build_pool(
                no_legendaries=s.starters_no_legendaries,
                no_babies=s.starters_no_babies,
                gen1_only=s.wild_gen1_only,
                gen2_only=s.wild_gen2_only,
            )
            chosen_ids = []
            for _ in range(3):
                remaining = [p for p in pool if p not in chosen_ids]
                if not remaining:
                    remaining = pool
                chosen_ids.append(self._pick(remaining))
            self.log(f"  Starters (random): {[POKEMON_NAMES[i] for i in chosen_ids]}")

        chosen_consts = [POKEMON_CONST_NAMES.get(i, "BULBASAUR") for i in chosen_ids]
        for i, sl in enumerate(new_starters):
            new_starters[i] = StarterLocation(
                species_const=chosen_consts[i],
                source_file=sl.source_file,
                line_index=sl.line_index,
                full_line=sl.full_line,
            )
        return new_starters

    # -------------------------------------------------------------------------
    # Starter held items
    # -------------------------------------------------------------------------

    def randomize_starter_items(self, item_locations: list) -> list:
        """
        Returns a new list of StarterItemLocation with randomized held items.
        Uses STARTER_ITEM_POOL_GOOD when starter_ban_bad_items is True,
        otherwise uses STARTER_ITEM_POOL_FULL.
        """
        from trade_data import STARTER_ITEM_POOL_GOOD, STARTER_ITEM_POOL_FULL

        if not item_locations:
            self.log("  [SKIP] No starter givepoke lines found — item randomization skipped.")
            return []

        pool = STARTER_ITEM_POOL_GOOD if self.settings.starter_ban_bad_items \
               else STARTER_ITEM_POOL_FULL

        new_locs = copy.deepcopy(item_locations)
        for loc in new_locs:
            loc.item_const = self.rng.choice(pool)

        items_str = ", ".join(loc.item_const for loc in new_locs)
        self.log(f"  Starter items: {items_str}")
        return new_locs

    # -------------------------------------------------------------------------
    # Wild Pokemon
    # -------------------------------------------------------------------------

    def randomize_wild(self, encounters: list) -> list:
        """
        Randomize wild encounter species according to wild_mode + wild_rule.

        Modes
        ─────
        random      — every slot is independently replaced (default)
        area1to1    — build a per-area species mapping; each unique species in
                      an area always maps to the same replacement within that area
        global1to1  — one consistent mapping across the entire game; a species
                      that appears in multiple areas always maps to the same
                      replacement everywhere

        Additional Rules (modify how replacements are chosen)
        ─────────────────────────────────────────────────────
        none             — pick uniformly at random from the pool
        similar_strength — pick a Pokémon with a similar Base Stat Total
        catch_em_all     — distribute pool species across all slots so every
                           Pokémon in the pool appears at least once
        type_themed      — each encounter area gets a random type; all
                           replacements in that area share that type
        """
        s = self.settings

        if s.wild_mode == "unchanged":
            return copy.deepcopy(encounters)

        pool = self._build_pool(
            no_legendaries=s.wild_no_legendaries,
            no_babies=False,
            gen1_only=s.wild_gen1_only,
            gen2_only=s.wild_gen2_only,
        )

        if not pool:
            self.log("[WARN] Wild Pokémon pool is empty after filtering.")
            return copy.deepcopy(encounters)

        new_encounters = copy.deepcopy(encounters)

        # ── Global 1-to-1 ────────────────────────────────────────────────────
        if s.wild_mode == "global1to1":
            mapping = self._build_1to1_mapping(
                [slot.species_const for grp in encounters for slot in grp.slots],
                pool,
            )
            total = 0
            for grp in new_encounters:
                for slot in grp.slots:
                    slot.species_const = mapping.get(slot.species_const, slot.species_const)
                    total += 1
            self.log(
                f"  Global 1-to-1: {len(mapping)} species mapped, "
                f"{total} slots updated across {len(new_encounters)} areas."
            )

        # ── Area 1-to-1 ───────────────────────────────────────────────────────
        elif s.wild_mode == "area1to1":
            total = 0
            for grp in new_encounters:
                area_pool = self._type_pool_for_area(pool) \
                    if s.wild_rule == "type_themed" else pool
                mapping = self._build_1to1_mapping(
                    [slot.species_const for slot in grp.slots],
                    area_pool,
                )
                for slot in grp.slots:
                    slot.species_const = mapping.get(slot.species_const, slot.species_const)
                    total += 1
            self.log(
                f"  Area 1-to-1: {total} slots updated across "
                f"{len(new_encounters)} areas."
            )

        # ── Random ────────────────────────────────────────────────────────────
        else:
            if s.wild_rule == "catch_em_all":
                self._apply_catch_em_all(new_encounters, pool)
            elif s.wild_rule == "type_themed":
                self._apply_type_themed(new_encounters, pool)
            else:
                total = 0
                for grp in new_encounters:
                    for slot in grp.slots:
                        if s.wild_rule == "similar_strength":
                            new_id = self._pick_similar_bst(slot.species_const, pool)
                        else:
                            new_id = self._pick(pool)
                        slot.species_const = POKEMON_CONST_NAMES.get(new_id, slot.species_const)
                        total += 1
                self.log(
                    f"  Random: {total} wild slots replaced across "
                    f"{len(new_encounters)} areas."
                )

        # ── Collapse time periods when "Use Time Based Encounters" is OFF ────
        if not s.wild_use_time_based:
            collapsed = 0
            for grp in new_encounters:
                n_periods = max(len(grp.rates), 1)
                spp       = grp.slots_per_period
                if n_periods <= 1 or spp <= 0 or spp * n_periods != len(grp.slots):
                    continue   # single-period group — nothing to collapse
                # Copy period-0 species into all subsequent periods
                for period_idx in range(1, n_periods):
                    for slot_offset in range(spp):
                        src_slot  = grp.slots[slot_offset]
                        dest_slot = grp.slots[period_idx * spp + slot_offset]
                        dest_slot.species_const = src_slot.species_const
                        collapsed += 1
            if collapsed:
                self.log(
                    f"  Time-based OFF: {collapsed} slot(s) across "
                    f"{len(new_encounters)} group(s) synced to morning pool."
                )

        return new_encounters

    def randomize_fish_slots(self, slots: list) -> list:
        """
        Randomize Crystal Legacy fish encounter slots from data/wild/fish.asm.

        Applies the same wild_mode and wild_rule settings as randomize_wild(),
        but operates on a flat list of FishSlot objects rather than encounter
        groups.  Fishing counts as one "area" for area1to1 mapping purposes.

        Returns a new list of FishSlot copies with updated species_const values.
        """
        s = self.settings

        if s.wild_mode == "unchanged" or not slots:
            return copy.deepcopy(slots)

        pool = self._build_pool(
            no_legendaries=s.wild_no_legendaries,
            no_babies=False,
            gen1_only=s.wild_gen1_only,
            gen2_only=s.wild_gen2_only,
        )
        if not pool:
            self.log("[WARN] Fish slot pool is empty after filtering — skipping fishing randomization.")
            return copy.deepcopy(slots)

        new_slots = copy.deepcopy(slots)

        if s.wild_mode == "global1to1":
            # Re-use the global mapping already built for wild encounters when
            # possible; here we build a fresh one just for fish (same semantics).
            mapping = self._build_1to1_mapping(
                [sl.species_const for sl in slots], pool
            )
            for sl in new_slots:
                sl.species_const = mapping.get(sl.species_const, sl.species_const)
            self.log(
                f"  Fish (global 1-to-1): {len(mapping)} species mapped, "
                f"{len(new_slots)} slot(s) updated."
            )

        elif s.wild_mode == "area1to1":
            # Treat all fishing as a single area.
            mapping = self._build_1to1_mapping(
                [sl.species_const for sl in slots], pool
            )
            for sl in new_slots:
                sl.species_const = mapping.get(sl.species_const, sl.species_const)
            self.log(
                f"  Fish (area 1-to-1): {len(mapping)} species mapped, "
                f"{len(new_slots)} slot(s) updated."
            )

        else:
            # Random / catch_em_all
            if s.wild_rule == "catch_em_all":
                # Distribute pool across all fish slots so every Pokémon
                # in the pool appears at least once.
                available = list(pool)
                self.rng.shuffle(available)
                pool_cycle = available[:]
                for sl in new_slots:
                    if not pool_cycle:
                        pool_cycle = list(pool)
                        self.rng.shuffle(pool_cycle)
                    new_id = pool_cycle.pop()
                    sl.species_const = POKEMON_CONST_NAMES.get(new_id, sl.species_const)
            else:
                total = 0
                for sl in new_slots:
                    if s.wild_rule == "similar_strength":
                        new_id = self._pick_similar_bst(sl.species_const, pool)
                    else:
                        new_id = self._pick(pool)
                    sl.species_const = POKEMON_CONST_NAMES.get(new_id, sl.species_const)
                    total += 1
                self.log(f"  Fish (random): {total} slot(s) replaced.")

        return new_slots

    # ── Wild helpers ──────────────────────────────────────────────────────────

    def _build_1to1_mapping(self, species_list: list, pool: list) -> dict:
        """
        Build a {original_const: replacement_const} mapping that is injective
        (no two originals map to the same replacement, as long as pool allows).
        Uses BST-similarity when wild_rule == "similar_strength".
        """
        s = self.settings
        unique_originals = list(dict.fromkeys(species_list))   # preserve order, dedupe
        available = list(pool)
        self.rng.shuffle(available)

        used    = set()
        mapping = {}
        for orig_const in unique_originals:
            remaining = [p for p in available if p not in used]
            if not remaining:
                remaining = available   # wrap if pool exhausted

            if s.wild_rule == "similar_strength":
                new_id = self._pick_similar_bst(orig_const, remaining)
            else:
                new_id = self.rng.choice(remaining)

            mapping[orig_const] = POKEMON_CONST_NAMES.get(new_id, orig_const)
            used.add(new_id)

        return mapping

    def _apply_catch_em_all(self, encounters: list, pool: list):
        """
        Assign pool species to all slots sequentially (after shuffling) so
        every species in the pool appears at least once across all wild areas.
        """
        all_slots = [slot for grp in encounters for slot in grp.slots]
        shuffled  = list(pool)
        self.rng.shuffle(shuffled)

        for i, slot in enumerate(all_slots):
            new_id = shuffled[i % len(shuffled)]
            slot.species_const = POKEMON_CONST_NAMES.get(new_id, slot.species_const)

        self.log(
            f"  Catch 'Em All: {len(all_slots)} slots distributed across "
            f"{len(pool)} pool species."
        )

    def _apply_type_themed(self, encounters: list, pool: list):
        """
        Assign each area a random type; all slots in that area get a Pokémon
        of that type.  Falls back to the full pool if the typed subset is empty.
        """
        for grp in encounters:
            typed_pool = self._type_pool_for_area(pool)
            for slot in grp.slots:
                new_id = self._pick(typed_pool)
                slot.species_const = POKEMON_CONST_NAMES.get(new_id, slot.species_const)

        self.log(f"  Type Themed: each of {len(encounters)} areas assigned a random type.")

    def _type_pool_for_area(self, pool: list) -> list:
        """Return a subset of pool filtered to a randomly chosen type."""
        from static_data import POKEMON_TYPES, ALL_TYPES
        chosen_type = self.rng.choice(ALL_TYPES)
        typed = [pid for pid in pool if chosen_type in POKEMON_TYPES.get(pid, ())]
        return typed if typed else pool

    # -------------------------------------------------------------------------
    # Trainers
    # -------------------------------------------------------------------------

    def randomize_trainers(self, trainers: list) -> list:
        """
        Returns a new list of Trainer with randomized party species.
        Levels, moves, and items are always preserved — only species change.

        Modes
        ─────
        unchanged         — no changes
        random            — each slot independently random from the pool;
                           boss trainers use a no-legendaries sub-pool
        random_even       — pool species distributed evenly across every slot
                           in the game (shuffle pool, assign cyclically)
        type_themed       — every trainer (including regular) is assigned a
                           random type; all their Pokémon share that type
        type_themed_boss  — only boss trainers (gym leaders, E4, rival) are
                           type-themed; regular trainers get pure random

        Additional options (stack on top of any mode)
        ─────────────────────────────────────────────
        trainer_similar_strength — prefer BST-similar replacements
        trainer_rival_starter    — rival's first slot locked to a starter
        trainer_weight_types     — type theme chosen weighted by type frequency
        """
        s = self.settings
        if s.trainer_mode == "unchanged":
            return copy.deepcopy(trainers)

        # Build shared pools
        pool_normal = self._build_pool(
            no_legendaries=s.trainer_no_legendaries,
            no_babies=s.trainer_no_babies,
            gen1_only=s.trainer_gen1_only,
            gen2_only=s.trainer_gen2_only,
        )
        pool_boss = self._build_pool(
            no_legendaries=s.trainer_boss_no_legendaries,
            no_babies=s.trainer_no_babies,
            gen1_only=s.trainer_gen1_only,
            gen2_only=s.trainer_gen2_only,
        )

        new_trainers = copy.deepcopy(trainers)

        if s.trainer_mode == "random_even":
            self._trainer_even_distribution(new_trainers, pool_normal)

        elif s.trainer_mode == "type_themed":
            self._trainer_type_themed(new_trainers, pool_normal, pool_boss, boss_only=False)

        elif s.trainer_mode == "type_themed_boss":
            self._trainer_type_themed(new_trainers, pool_normal, pool_boss, boss_only=True)

        else:  # "random"
            self._trainer_random(new_trainers, pool_normal, pool_boss)

        # Apply rival starter lock after main randomization
        if s.trainer_rival_starter:
            self._apply_rival_starter(new_trainers)

        # Force fully-evolved applies last, on top of everything else
        if s.trainer_force_fully_evolved:
            self._apply_force_fully_evolved(new_trainers)

        return new_trainers

    # ── Trainer mode helpers ──────────────────────────────────────────────────

    def _trainer_pick(self, species_const: str, pool: list) -> int:
        """Pick a replacement from pool, using similar-BST if the setting is on."""
        if self.settings.trainer_similar_strength:
            return self._pick_similar_bst(species_const, pool)
        return self._pick(pool)

    def _trainer_random(self, trainers: list, pool_normal: list, pool_boss: list):
        """Each slot picked independently; boss trainers use pool_boss."""
        total = 0
        for trainer in trainers:
            pool = pool_boss if self._is_boss_trainer(trainer) else pool_normal
            if not pool:
                continue
            for poke in trainer.party:
                new_id = self._trainer_pick(poke.species_const, pool)
                poke.species_const = POKEMON_CONST_NAMES.get(new_id, poke.species_const)
                total += 1
        self.log(f"  Random: {total} Pokémon replaced across {len(trainers)} trainers.")

    def _trainer_even_distribution(self, trainers: list, pool: list):
        """
        Distribute pool species evenly across ALL trainer slots.
        The pool is shuffled once then assigned cyclically, guaranteeing every
        species appears roughly the same number of times.
        """
        all_pokes = [poke for trainer in trainers for poke in trainer.party]
        if not pool or not all_pokes:
            return
        shuffled = list(pool)
        self.rng.shuffle(shuffled)
        for i, poke in enumerate(all_pokes):
            new_id = shuffled[i % len(shuffled)]
            poke.species_const = POKEMON_CONST_NAMES.get(new_id, poke.species_const)
        self.log(
            f"  Even distribution: {len(all_pokes)} slots filled from "
            f"{len(pool)}-species pool across {len(trainers)} trainers."
        )

    def _trainer_type_themed(self, trainers: list, pool_normal: list,
                              pool_boss: list, boss_only: bool):
        """
        Assign each trainer a random type; all their Pokémon come from that type.
        If boss_only=True, only boss trainers get a type theme — regular trainers
        get pure-random treatment instead.
        """
        s = self.settings
        total = 0
        for trainer in trainers:
            is_boss = self._is_boss_trainer(trainer)
            pool    = pool_boss if is_boss else pool_normal
            if not pool:
                continue

            if boss_only and not is_boss:
                # Regular trainers: just plain random
                for poke in trainer.party:
                    new_id = self._trainer_pick(poke.species_const, pool)
                    poke.species_const = POKEMON_CONST_NAMES.get(new_id, poke.species_const)
                    total += 1
                continue

            # Type-themed trainer: pick one type for the whole party
            typed_pool = self._trainer_type_pool(pool, weighted=s.trainer_weight_types)
            for poke in trainer.party:
                new_id = self._trainer_pick(poke.species_const, typed_pool)
                poke.species_const = POKEMON_CONST_NAMES.get(new_id, poke.species_const)
                total += 1

        label = "Type Themed (boss only)" if boss_only else "Type Themed"
        self.log(f"  {label}: {total} Pokémon themed across {len(trainers)} trainers.")

    def _trainer_type_pool(self, pool: list, weighted: bool = False) -> list:
        """
        Return pool filtered to a single randomly chosen type.
        If weighted=True, type selection probability is proportional to how many
        Pokémon of each type exist in the pool (avoids rare types leaving trainers
        with tiny pools).  Falls back to full pool if typed subset is empty.
        """
        from static_data import POKEMON_TYPES, ALL_TYPES

        if weighted:
            # Count pool members per type
            type_counts: dict = {}
            for pid in pool:
                for t in POKEMON_TYPES.get(pid, ()):
                    type_counts[t] = type_counts.get(t, 0) + 1
            if not type_counts:
                return pool
            types   = list(type_counts.keys())
            weights = [type_counts[t] for t in types]
            chosen  = self.rng.choices(types, weights=weights, k=1)[0]
        else:
            chosen = self.rng.choice(ALL_TYPES)

        typed = [pid for pid in pool if chosen in POKEMON_TYPES.get(pid, ())]
        return typed if typed else pool

    # ── Rival starter helper ──────────────────────────────────────────────────

    # Original Crystal starter lineages (base, mid, final)
    _CRYSTAL_STARTER_CHAINS = [
        (152, 153, 154),  # Chikorita → Bayleef → Meganium
        (155, 156, 157),  # Cyndaquil → Quilava → Typhlosion
        (158, 159, 160),  # Totodile → Croconaw → Feraligatr
    ]

    def _is_rival_trainer(self, trainer) -> bool:
        """Return True if this trainer is the player's rival."""
        name_upper  = trainer.name.upper()
        class_upper = trainer.trainer_class.upper()
        for kw in self.settings.rival_trainer_keywords:
            if kw in name_upper or kw in class_upper:
                return True
        return False

    def _get_level_evo_stage(self, base_id: int, level: int) -> int:
        """
        Walk the level_evo_map forward from base_id and return the highest
        evolution stage the Pokémon would have reached by `level`.
        """
        evo_map = self.settings.rival_level_evo_map
        current = base_id
        for _ in range(3):   # max 3-stage chain
            evos = evo_map.get(current, [])
            # Pick the highest-level evolution we have already reached
            best_target, best_lv = None, -1
            for (target_id, evo_level) in evos:
                if level >= evo_level and evo_level > best_lv:
                    best_target, best_lv = target_id, evo_level
            if best_target is None:
                break
            current = best_target
        return current

    def _apply_rival_starter(self, trainers: list):
        """
        Lock each rival trainer's first party slot to an appropriate evolution
        of the randomized starter assigned to the rival's lineage position.

        Crystal rival lineage mapping
        ─────────────────────────────
        Lineage 0  (Chikorita) → rival carries lineage 2 (Totodile) starter
        Lineage 1  (Cyndaquil) → rival carries lineage 0 (Chikorita) starter
        Lineage 2  (Totodile)  → rival carries lineage 1 (Cyndaquil) starter
        (i.e. the type-counter starter in the original triangle)
        """
        s = self.settings
        if not s.rival_starter_ids or len(s.rival_starter_ids) < 3:
            self.log("  [INFO] Rival starter: no randomized starters available — skipping.")
            return

        # Map every original Crystal starter ID → lineage index
        crystal_lookup: dict = {}
        for li, chain in enumerate(self._CRYSTAL_STARTER_CHAINS):
            for pid in chain:
                crystal_lookup[pid] = li

        # Counter-starter mapping: lineage_idx → which rival_starter_ids slot to use
        COUNTER = {0: 2, 1: 0, 2: 1}

        rival_count = 0
        for trainer in trainers:
            if not self._is_rival_trainer(trainer) or not trainer.party:
                continue

            slot    = trainer.party[0]
            orig_id = POKEMON_CONSTANTS.get(slot.species_const, 0)

            # Determine which original Crystal lineage the rival's slot belongs to
            lineage_idx = crystal_lookup.get(orig_id, 1)   # default: Cyndaquil line
            rand_base   = s.rival_starter_ids[COUNTER[lineage_idx]]

            # Get the right evolution stage for this battle's level
            appropriate_id = self._get_level_evo_stage(rand_base, slot.level)
            slot.species_const = POKEMON_CONST_NAMES.get(appropriate_id, slot.species_const)
            rival_count += 1

        if rival_count:
            self.log(f"  Rival starter: {rival_count} rival party slot(s) locked to starter lineage.")

    # -------------------------------------------------------------------------
    # In-game trades
    # -------------------------------------------------------------------------

    def randomize_trades(self, trades: list) -> list:
        """
        Returns a new list of InGameTrade with randomized fields.
        Modes:
          unchanged   — return originals untouched
          given_only  — randomize only the species the player receives
          both        — randomize both the given and requested species
        Sub-options (applied on top of any random mode):
          trade_random_nicknames — new random nickname for the received Pokemon
          trade_random_ot        — new random OT name
          trade_random_ivs       — random Gen 2 DV word
          trade_random_items     — random held item from TRADE_ITEM_POOL
        """
        from trade_data import (TRADE_ITEM_POOL,
                                make_random_nickname,
                                make_random_ot,
                                make_random_dvs)

        if self.settings.trade_mode == "unchanged" or not trades:
            return copy.deepcopy(trades)

        s = self.settings
        new_trades = copy.deepcopy(trades)

        # Pool uses the global gen filter (reuse trainer gen flags)
        pool = self._build_pool(
            no_legendaries=False,
            no_babies=False,
            gen1_only=s.trainer_gen1_only,
            gen2_only=s.trainer_gen2_only,
        )

        replaced = 0
        for t in new_trades:
            # ── species ────────────────────────────────────────────────────
            if pool:
                # Always randomize the given species (what player receives)
                new_id = self._pick(pool)
                t.given_species = POKEMON_CONST_NAMES.get(new_id, t.given_species)
                replaced += 1

                if s.trade_mode == "both":
                    new_id = self._pick(pool)
                    t.requested_species = POKEMON_CONST_NAMES.get(new_id, t.requested_species)

            # ── sub-options ────────────────────────────────────────────────
            if s.trade_random_nicknames:
                t.nickname = make_random_nickname(self.rng)

            if s.trade_random_ot:
                t.ot_name = make_random_ot(self.rng)

            if s.trade_random_ivs and t.dvs_line >= 0:
                t.dvs_raw = make_random_dvs(self.rng)

            if s.trade_random_items and t.item_line >= 0:
                t.item = self.rng.choice(TRADE_ITEM_POOL)

        self.log(f"  Randomized {replaced} in-game trade(s).")
        return new_trades

    # -------------------------------------------------------------------------
    # Static Pokemon
    # -------------------------------------------------------------------------

    def randomize_static(self, encounters: list, mode: str) -> list:
        """
        Returns a new list of StaticEncounter with randomized species.
        Modes:
          unchanged        — return originals untouched
          swap             — legendaries swap with legendaries,
                             standards swap with standards
          random           — any Pokemon from the full pool
          similar_strength — pick a Pokemon with a similar Base Stat Total
        """
        if mode == "unchanged" or not encounters:
            return copy.deepcopy(encounters)

        s = self.settings
        new_encounters = copy.deepcopy(encounters)

        # Legendary-only pool (filtered by global gen setting)
        legend_pool = [
            idx for idx in LEGENDARY_IDS
            if (not s.static_gen1_only or idx <= 151)
            and (not s.static_gen2_only or idx >= 152)
        ]

        # Standard (non-legendary) pool
        standard_pool = self._build_pool(
            no_legendaries=True,
            no_babies=False,
            gen1_only=s.static_gen1_only,
            gen2_only=s.static_gen2_only,
        )

        # Full pool (legendaries included) for "random" and "similar_strength"
        full_pool = self._build_pool(
            no_legendaries=False,
            no_babies=False,
            gen1_only=s.static_gen1_only,
            gen2_only=s.static_gen2_only,
        )

        total_replaced = 0
        for enc in new_encounters:
            new_id = None

            if mode == "swap":
                if enc.is_legendary and legend_pool:
                    new_id = self._pick(legend_pool)
                elif not enc.is_legendary and standard_pool:
                    new_id = self._pick(standard_pool)
                elif full_pool:
                    new_id = self._pick(full_pool)

            elif mode == "random":
                if full_pool:
                    new_id = self._pick(full_pool)

            elif mode == "similar_strength":
                new_id = self._pick_similar_bst(enc.species_const, full_pool)

            if new_id is not None:
                enc.species_const = POKEMON_CONST_NAMES.get(new_id, enc.species_const)
                total_replaced += 1

        self.log(f"  Randomized {total_replaced} static encounter(s) "
                 f"across {len(new_encounters)} location(s).")
        return new_encounters

    def _pick_similar_bst(self, species_const: str, pool: list) -> Optional[int]:
        """
        Pick a random Pokemon from pool whose BST is close to species_const's BST.
        Sorts by absolute BST difference and picks randomly from the 20 nearest.
        Falls back to a completely random pick if BST data is unavailable.
        """
        from static_data import POKEMON_BST
        if not pool:
            return None
        current_id = POKEMON_CONSTANTS.get(species_const)
        if current_id is None or not (0 < current_id < len(POKEMON_BST)):
            return self._pick(pool)
        target_bst = POKEMON_BST[current_id]

        def bst_dist(idx):
            return abs(POKEMON_BST[idx] - target_bst) if 0 < idx < len(POKEMON_BST) else 99999

        sorted_pool = sorted(pool, key=bst_dist)
        candidates = sorted_pool[:20]   # top 20 closest by BST
        return self._pick(candidates)

    def _is_boss_trainer(self, trainer: Trainer) -> bool:
        """Detect gym leaders, Elite Four, rivals, and executives."""
        name_upper = trainer.name.upper()
        class_upper = trainer.trainer_class.upper()
        for kw in self.settings.boss_trainer_classes:
            if kw in name_upper or kw in class_upper:
                return True
        return False

    # ── Force fully evolved ───────────────────────────────────────────────────

    def _get_final_evo(self, species_id: int) -> int:
        """
        Follow the level_evo_map chain from species_id to its final form.
        If a Pokémon has multiple branches (e.g. Tyrogue), one is chosen at random.
        Returns species_id unchanged if no further level evolutions exist.
        """
        evo_map = self.settings.rival_level_evo_map
        current = species_id
        visited = set()
        while True:
            if current in visited:
                break               # cycle guard
            visited.add(current)
            evos = evo_map.get(current, [])
            if not evos:
                break               # already at final form
            # Pick a branch at random (handles split evolutions like Tyrogue)
            current = self.rng.choice(evos)[0]
        return current

    def _apply_force_fully_evolved(self, trainers: list):
        """
        For every trainer Pokémon whose level is >= trainer_force_evo_level,
        replace it with its final evolution if it is not already fully evolved.
        Applied after all other randomization so it stacks cleanly.
        """
        s         = self.settings
        threshold = s.trainer_force_evo_level
        forced    = 0

        for trainer in trainers:
            for poke in trainer.party:
                if poke.level < threshold:
                    continue
                current_id = POKEMON_CONSTANTS.get(poke.species_const, 0)
                if not current_id:
                    continue
                final_id = self._get_final_evo(current_id)
                if final_id != current_id:
                    poke.species_const = POKEMON_CONST_NAMES.get(final_id, poke.species_const)
                    forced += 1

        self.log(
            f"  Force fully evolved (lv ≥ {threshold}): "
            f"{forced} Pokémon evolved to final form."
        )

    # -------------------------------------------------------------------------
    # Wild held items
    # -------------------------------------------------------------------------

    def randomize_wild_held_items(self, held_items: list) -> list:
        """
        Returns a new list of WildHeldItemEntry with randomized held items.

        Uses STARTER_ITEM_POOL_GOOD when wild_ban_bad_held_items is True,
        otherwise uses STARTER_ITEM_POOL_FULL.  Both common and rare item
        slots for each entry are independently randomized.
        """
        from trade_data import STARTER_ITEM_POOL_GOOD, STARTER_ITEM_POOL_FULL

        if not held_items:
            self.log("  [SKIP] No wild held item entries found — skipping.")
            return []

        pool = STARTER_ITEM_POOL_GOOD if self.settings.wild_ban_bad_held_items \
               else STARTER_ITEM_POOL_FULL

        new_items = copy.deepcopy(held_items)
        for entry in new_items:
            entry.common_item = self.rng.choice(pool)
            entry.rare_item   = self.rng.choice(pool)

        self.log(f"  Wild held items: randomized {len(new_items)} entries.")
        return new_items

    # -------------------------------------------------------------------------
    # Field items
    # -------------------------------------------------------------------------

    def randomize_field_items(self, field_items: list) -> list:
        """
        Returns a new list of FieldItemEntry objects with modified item constants.

        Modes (field_items_mode):
          "shuffle"      — items are shuffled among themselves; no new items enter
          "random"       — each slot independently picks from the pool
          "random_even"  — pool is shuffled then assigned cyclically so every item
                           in the pool appears as close to equally often as possible

        Ban Bad Items removes cheap/situational items from the pool for the two
        random modes.  Shuffle is not affected (it only redistributes what's there).
        """
        from item_data import FIELD_ITEM_POOL_GOOD, FIELD_ITEM_POOL_FULL

        if not field_items:
            self.log("  [SKIP] No field items found — skipping.")
            return []

        new_items = copy.deepcopy(field_items)
        mode = self.settings.field_items_mode
        vis_count = sum(1 for e in field_items if e.item_type == "visible")
        hid_count = sum(1 for e in field_items if e.item_type == "hidden")

        if mode == "shuffle":
            # Collect all current item constants, shuffle, redistribute
            all_consts = [e.item_const for e in field_items]
            self.rng.shuffle(all_consts)
            for entry, new_const in zip(new_items, all_consts):
                entry.item_const = new_const
            self.log(f"  Field items: shuffled {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden).")

        elif mode == "random":
            pool = FIELD_ITEM_POOL_GOOD if self.settings.field_items_ban_bad \
                   else FIELD_ITEM_POOL_FULL
            if not pool:
                self.log("  [WARN] Field item pool is empty — skipping.")
                return new_items
            for entry in new_items:
                entry.item_const = self.rng.choice(pool)
            self.log(f"  Field items: randomized {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden).")

        elif mode == "random_even":
            pool = FIELD_ITEM_POOL_GOOD if self.settings.field_items_ban_bad \
                   else FIELD_ITEM_POOL_FULL
            if not pool:
                self.log("  [WARN] Field item pool is empty — skipping.")
                return new_items
            # Build a shuffled pool and cycle through it so each item appears
            # as evenly as possible across all field item slots
            shuffled = list(pool)
            self.rng.shuffle(shuffled)
            for i, entry in enumerate(new_items):
                entry.item_const = shuffled[i % len(shuffled)]
            self.log(f"  Field items: evenly distributed {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden) "
                     f"across {len(pool)}-item pool.")

        return new_items
