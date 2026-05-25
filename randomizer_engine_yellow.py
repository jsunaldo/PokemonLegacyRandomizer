"""
Pokemon Yellow Legacy Randomizer - Randomization Engine

Applies randomization settings to parsed Yellow Legacy data structures.
All operations return modified copies; originals are never mutated.
"""

import random
import copy
from dataclasses import dataclass, field
from typing import Optional

from constants_yellow import (
    YELLOW_POKEMON_CONSTS_POKEDEX_ORDER,
    YELLOW_POKEMON_DISPLAY_NAME,
    YELLOW_POKEMON_PRIMARY_TYPE,
    YELLOW_LEGENDARY_POKEMON,
)
from trade_data import make_random_nickname, make_random_ot


# ── Gen 1 three-stage starter chains (base forms only) ────────────────────────
# Used for "random_two_stage" starter mode — picks a Pokémon that has 2 evolutions.
_TWO_STAGE_BASES = frozenset({
    'BULBASAUR', 'CHARMANDER', 'SQUIRTLE',
    'CATERPIE', 'WEEDLE', 'PIDGEY', 'RATTATA', 'SPEAROW',
    'EKANS', 'SANDSHREW', 'NIDORAN_F', 'NIDORAN_M',
    'ODDISH', 'PARAS', 'VENONAT', 'DIGLETT', 'MEOWTH',
    'PSYDUCK', 'MANKEY', 'GROWLITHE', 'POLIWAG', 'ABRA',
    'MACHOP', 'BELLSPROUT', 'GEODUDE', 'GASTLY',
    'RHYHORN', 'HORSEA', 'GOLDEEN', 'MAGIKARP', 'DRATINI',
})

# Catch rate slider → minimum value
_CATCH_RATE_THRESHOLDS = {1: 75, 2: 128, 3: 170, 4: 210, 5: 255}

# Gen 1 types (for type_themed randomization)
_ALL_TYPES = [
    'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice',
    'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic',
    'Bug', 'Rock', 'Ghost', 'Dragon',
]


@dataclass
class YellowRandomizerSettings:
    seed: Optional[int] = None

    # ── Starter (single Pokémon in Yellow) ─────────────────────────────────────
    starter_mode: str = "random"          # "unchanged" | "custom" | "random" | "random_two_stage"
    starter_no_legendaries: bool = True
    custom_starter: Optional[str] = None  # species const string when mode == "custom"

    # ── Wild Pokémon ───────────────────────────────────────────────────────────
    wild_mode: str = "random"             # "unchanged" | "random" | "area1to1" | "global1to1"
    wild_rule: str = "none"               # "none" | "catch_em_all" | "type_themed"
    wild_no_legendaries: bool = False
    wild_min_catch_rate: int = 0          # 0=off, 1–5

    # ── Fishing ────────────────────────────────────────────────────────────────
    fishing_mode: str = "unchanged"       # "unchanged" | "random"
    fishing_no_legendaries: bool = False

    # ── Trainers ───────────────────────────────────────────────────────────────
    trainer_mode: str = "random"          # "unchanged" | "random" | "type_themed" | "type_themed_boss"
    trainer_no_legendaries: bool = False
    trainer_boss_no_legendaries: bool = True
    trainer_force_fully_evolved: bool = False
    trainer_force_evo_level: int = 30

    # ── Static encounters ──────────────────────────────────────────────────────
    static_mode: str = "unchanged"        # "unchanged" | "swap" | "random" | "similar_strength"

    # ── In-game trades ─────────────────────────────────────────────────────────
    trade_mode: str = "unchanged"         # "unchanged" | "given_only" | "both"
    trade_random_nicknames: bool = False
    trade_random_ot: bool = False

    # ── Field items ────────────────────────────────────────────────────────────
    field_items_mode: str = "unchanged"   # "unchanged" | "shuffle" | "random" | "random_even"
    field_items_ban_bad: bool = True

    # ── Starting items (bag + PC) ──────────────────────────────────────────────
    randomize_start_items: bool = False
    start_items: list = None              # bag items: list of {"const":..., "qty":...}
    start_pc_items: list = None           # PC items:  list of {"const":..., "qty":...}

    # ── Evolutions ─────────────────────────────────────────────────────────────
    easier_evolutions: bool = False       # lower level thresholds; trade→level

    # ── TM/HM compatibility ────────────────────────────────────────────────────
    full_hm_compat: bool = False

    # Boss trainer class keyword substrings (matched against class_name.upper())
    boss_trainer_classes: tuple = (
        "BROCK", "MISTY", "LT_SURGE", "ERIKA", "KOGA", "SABRINA",
        "BLAINE", "GIOVANNI", "LORELEI", "BRUNO", "AGATHA", "LANCE",
        "BLUE", "RIVAL",
    )


class YellowRandomizerEngine:
    def __init__(self, settings: YellowRandomizerSettings, log_fn=None):
        self.settings = settings
        self.log = log_fn or print
        self.rng = random.Random(settings.seed)
        self._level_evo_map: dict = {}   # populated externally before calling trainers

    # ─────────────────────────────────────────────────────────────────────────
    # Pool helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_pool(self, no_legendaries: bool = False) -> list:
        """Return list of valid species constants (all 151 Gen 1 Pokémon by default)."""
        pool = []
        for const in YELLOW_POKEMON_CONSTS_POKEDEX_ORDER:
            if no_legendaries and const in YELLOW_LEGENDARY_POKEMON:
                continue
            pool.append(const)
        return pool

    def _pick(self, pool: list) -> str:
        return self.rng.choice(pool)

    def _pokedex_num(self, const: str) -> int:
        """Return 1-based Pokédex number for a const (0 if not found)."""
        try:
            return YELLOW_POKEMON_CONSTS_POKEDEX_ORDER.index(const) + 1
        except ValueError:
            return 0

    # ─────────────────────────────────────────────────────────────────────────
    # BST-based similarity
    # ─────────────────────────────────────────────────────────────────────────

    def _pick_similar_bst(self, species_const: str, pool: list) -> str:
        """
        Pick from pool preferring a similar Base Stat Total.
        Uses Crystal's static_data POKEMON_BST array indexed by Pokédex number —
        valid for Gen 1 Pokémon (1–151) since Crystal's IDs match Pokédex order there.
        Falls back to uniform random if BST data is unavailable.
        """
        try:
            from static_data import POKEMON_BST
            target_dex = self._pokedex_num(species_const)
            if not (0 < target_dex < len(POKEMON_BST)):
                return self._pick(pool)
            target_bst = POKEMON_BST[target_dex]

            def dist(c: str) -> int:
                d = self._pokedex_num(c)
                return abs(POKEMON_BST[d] - target_bst) if 0 < d < len(POKEMON_BST) else 99999

            sorted_pool = sorted(pool, key=dist)
            return self._pick(sorted_pool[:20])
        except Exception:
            return self._pick(pool)

    # ─────────────────────────────────────────────────────────────────────────
    # 1-to-1 mapping
    # ─────────────────────────────────────────────────────────────────────────

    def _build_1to1_mapping(self, species_list: list, pool: list) -> dict:
        """
        Build an injective {original_const: replacement_const} mapping
        (no two originals map to the same replacement, while pool allows it).
        Uses BST-similarity when wild_rule == "similar_strength".
        """
        s = self.settings
        unique = list(dict.fromkeys(species_list))   # dedupe, preserve order
        available = list(pool)
        self.rng.shuffle(available)
        used: set = set()
        mapping: dict = {}
        for orig in unique:
            remaining = [p for p in available if p not in used]
            if not remaining:
                remaining = available
            if s.wild_rule == "similar_strength":
                chosen = self._pick_similar_bst(orig, remaining)
            else:
                chosen = self.rng.choice(remaining)
            mapping[orig] = chosen
            used.add(chosen)
        return mapping

    # ─────────────────────────────────────────────────────────────────────────
    # Type pool helper
    # ─────────────────────────────────────────────────────────────────────────

    def _type_pool_for_area(self, pool: list) -> list:
        """Pick a random Gen 1 type and return pool filtered to that type."""
        chosen_type = self.rng.choice(_ALL_TYPES)
        typed = [c for c in pool
                 if YELLOW_POKEMON_PRIMARY_TYPE.get(c, '') == chosen_type]
        return typed if typed else pool

    # ─────────────────────────────────────────────────────────────────────────
    # Starter
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_starter(self, starters: list) -> Optional[str]:
        """
        Pick a new species constant for the single Yellow starter.
        Returns the chosen const, or None if mode is "unchanged".
        """
        s = self.settings
        if s.starter_mode == "unchanged":
            return None

        if s.starter_mode == "custom":
            if s.custom_starter and s.custom_starter in YELLOW_POKEMON_CONSTS_POKEDEX_ORDER:
                self.log(f"  Starter (custom): {YELLOW_POKEMON_DISPLAY_NAME.get(s.custom_starter, s.custom_starter)}")
                return s.custom_starter
            self.log("  [WARN] Custom starter not set or invalid — falling back to random.")
            pool = self._build_pool(no_legendaries=s.starter_no_legendaries)
        elif s.starter_mode == "random_two_stage":
            pool = [c for c in _TWO_STAGE_BASES
                    if c in YELLOW_POKEMON_CONSTS_POKEDEX_ORDER
                    and (not s.starter_no_legendaries or c not in YELLOW_LEGENDARY_POKEMON)]
        else:  # "random"
            pool = self._build_pool(no_legendaries=s.starter_no_legendaries)

        if not pool:
            self.log("  [WARN] Starter pool empty after filtering — leaving unchanged.")
            return None

        chosen = self._pick(pool)
        self.log(f"  Starter: {YELLOW_POKEMON_DISPLAY_NAME.get(chosen, chosen)}")
        return chosen

    # ─────────────────────────────────────────────────────────────────────────
    # Wild encounters
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_wild(self, encounters: list) -> list:
        """
        Randomize wild encounter species.

        Modes
        ─────
        random      — every slot independently replaced
        area1to1    — per-area consistent mapping (each unique species in an area
                      always maps to the same replacement within that area)
        global1to1  — one mapping across the whole game

        Rules (stack on top of any mode except global1to1 where only
        similar_strength applies per-slot)
        ─────
        none         — uniform random from pool
        catch_em_all — distribute pool species across all slots cyclically
        type_themed  — each area gets a random type; all slots share that type
        """
        s = self.settings
        if s.wild_mode == "unchanged":
            return copy.deepcopy(encounters)

        pool = self._build_pool(no_legendaries=s.wild_no_legendaries)
        if not pool:
            self.log("[WARN] Wild Pokémon pool empty after filtering.")
            return copy.deepcopy(encounters)

        new_encounters = copy.deepcopy(encounters)

        if s.wild_mode == "global1to1":
            all_species = [sl.species_const for grp in encounters for sl in grp.slots]
            mapping = self._build_1to1_mapping(all_species, pool)
            total = 0
            for grp in new_encounters:
                for sl in grp.slots:
                    sl.species_const = mapping.get(sl.species_const, sl.species_const)
                    total += 1
            self.log(f"  Global 1-to-1: {len(mapping)} species mapped, "
                     f"{total} slots updated across {len(new_encounters)} areas.")

        elif s.wild_mode == "area1to1":
            total = 0
            for grp in new_encounters:
                area_pool = self._type_pool_for_area(pool) \
                    if s.wild_rule == "type_themed" else pool
                mapping = self._build_1to1_mapping(
                    [sl.species_const for sl in grp.slots], area_pool)
                for sl in grp.slots:
                    sl.species_const = mapping.get(sl.species_const, sl.species_const)
                    total += 1
            self.log(f"  Area 1-to-1: {total} slots updated across "
                     f"{len(new_encounters)} areas.")

        else:  # "random"
            if s.wild_rule == "catch_em_all":
                all_slots = [sl for grp in new_encounters for sl in grp.slots]
                shuffled = list(pool)
                self.rng.shuffle(shuffled)
                for i, sl in enumerate(all_slots):
                    sl.species_const = shuffled[i % len(shuffled)]
                self.log(f"  Catch 'Em All: {len(all_slots)} slots distributed "
                         f"across {len(pool)}-species pool.")
            elif s.wild_rule == "type_themed":
                for grp in new_encounters:
                    typed_pool = self._type_pool_for_area(pool)
                    for sl in grp.slots:
                        sl.species_const = self._pick(typed_pool)
                self.log(f"  Type Themed: {len(new_encounters)} areas randomized.")
            elif s.wild_rule == "similar_strength":
                total = 0
                for grp in new_encounters:
                    for sl in grp.slots:
                        sl.species_const = self._pick_similar_bst(sl.species_const, pool)
                        total += 1
                self.log(f"  Similar Strength: {total} wild slots replaced across "
                         f"{len(new_encounters)} areas.")
            else:
                total = 0
                for grp in new_encounters:
                    for sl in grp.slots:
                        sl.species_const = self._pick(pool)
                        total += 1
                self.log(f"  Random: {total} wild slots replaced across "
                         f"{len(new_encounters)} areas.")

        return new_encounters

    # ─────────────────────────────────────────────────────────────────────────
    # Static encounters
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_static(self, encounters: list) -> list:
        """
        Returns a new list of YellowStaticEncounter with randomized species.
        Modes:
          unchanged        — return originals untouched
          swap             — legendaries swap with legendaries, standards with standards
          random           — any Pokémon from the full pool
          similar_strength — pick a Pokémon with a similar Base Stat Total
        """
        from static_data import YELLOW_STATIC_LEGENDARY_SPECIES

        s = self.settings
        mode = s.static_mode
        if mode == "unchanged" or not encounters:
            return copy.deepcopy(encounters)

        new_encounters = copy.deepcopy(encounters)

        legend_pool   = [c for c in YELLOW_POKEMON_CONSTS_POKEDEX_ORDER
                         if c in YELLOW_LEGENDARY_POKEMON]
        standard_pool = self._build_pool(no_legendaries=True)
        full_pool     = self._build_pool(no_legendaries=False)

        total_replaced = 0
        for enc in new_encounters:
            chosen = None

            if mode == "swap":
                if enc.is_legendary and legend_pool:
                    chosen = self._pick(legend_pool)
                elif not enc.is_legendary and standard_pool:
                    chosen = self._pick(standard_pool)
                elif full_pool:
                    chosen = self._pick(full_pool)

            elif mode == "random":
                if full_pool:
                    chosen = self._pick(full_pool)

            elif mode == "similar_strength":
                chosen = self._pick_similar_bst(enc.species_const, full_pool)

            if chosen is not None:
                enc.species_const = chosen
                total_replaced += 1

        self.log(f"  Randomized {total_replaced} static encounter(s) "
                 f"across {len(new_encounters)} location(s).")
        return new_encounters

    # ─────────────────────────────────────────────────────────────────────────
    # Fishing
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_fishing_simple(self, slots: list, rod_name: str) -> list:
        """Randomize old_rod or good_rod slot list."""
        s = self.settings
        if s.fishing_mode == "unchanged":
            return copy.deepcopy(slots)
        pool = self._build_pool(no_legendaries=s.fishing_no_legendaries)
        if not pool:
            return copy.deepcopy(slots)
        new_slots = copy.deepcopy(slots)
        for sl in new_slots:
            sl.species_const = self._pick(pool)
        self.log(f"  {rod_name}: {len(new_slots)} slot(s) randomized.")
        return new_slots

    def randomize_super_rod(self, slots: list) -> list:
        """Randomize super rod slots (all 4 species per location)."""
        s = self.settings
        if s.fishing_mode == "unchanged":
            return copy.deepcopy(slots)
        pool = self._build_pool(no_legendaries=s.fishing_no_legendaries)
        if not pool:
            return copy.deepcopy(slots)
        new_slots = copy.deepcopy(slots)
        for sl in new_slots:
            sl.species_const = self._pick(pool)
        self.log(f"  Super Rod: {len(new_slots)} slot(s) randomized.")
        return new_slots

    # ─────────────────────────────────────────────────────────────────────────
    # Trainers
    # ─────────────────────────────────────────────────────────────────────────

    def _is_boss_trainer(self, trainer) -> bool:
        class_upper = trainer.class_name.upper()
        for kw in self.settings.boss_trainer_classes:
            if kw in class_upper:
                return True
        return False

    def build_level_evo_map(self, evolutions: list) -> dict:
        """Build {species_const: [(target_const, level), ...]} from evolution entries."""
        evo_map: dict = {}
        for entry in evolutions:
            if entry.evo_type.upper() in ('EVOLVE_LEVEL', 'LEVEL'):
                try:
                    lv = int(entry.param)
                except (ValueError, TypeError):
                    continue
                evo_map.setdefault(entry.source_species, []).append(
                    (entry.target_species, lv))
        return evo_map

    def randomize_trainers(self, trainers: list) -> list:
        """
        Returns a new list of YellowTrainer with randomized party species.
        Levels are preserved; only species change.

        Modes
        ─────
        unchanged        — no changes
        random           — each slot independently random; boss trainers
                           use the no-legendaries pool when that setting is on
        type_themed      — every trainer gets a random type; all Pokémon share it
        type_themed_boss — only boss trainers are type-themed; others are random
        """
        s = self.settings
        if s.trainer_mode == "unchanged":
            return copy.deepcopy(trainers)

        pool_normal = self._build_pool(no_legendaries=s.trainer_no_legendaries)
        pool_boss   = self._build_pool(no_legendaries=s.trainer_boss_no_legendaries)
        new_trainers = copy.deepcopy(trainers)

        if s.trainer_mode in ("type_themed", "type_themed_boss"):
            boss_only = (s.trainer_mode == "type_themed_boss")
            total = 0
            for trainer in new_trainers:
                is_boss = self._is_boss_trainer(trainer)
                pool    = pool_boss if is_boss else pool_normal
                if not pool:
                    continue
                if boss_only and not is_boss:
                    # Non-boss trainers: plain random
                    for poke in trainer.party:
                        poke.species_const = self._pick(pool)
                        total += 1
                else:
                    typed_pool = self._type_pool_for_area(pool)
                    for poke in trainer.party:
                        poke.species_const = self._pick(typed_pool)
                        total += 1
            label = "Type Themed (boss only)" if boss_only else "Type Themed"
            self.log(f"  {label}: {total} Pokémon across {len(new_trainers)} trainers.")

        else:  # "random"
            total = 0
            for trainer in new_trainers:
                pool = pool_boss if self._is_boss_trainer(trainer) else pool_normal
                if not pool:
                    continue
                for poke in trainer.party:
                    poke.species_const = self._pick(pool)
                    total += 1
            self.log(f"  Random: {total} Pokémon replaced across {len(new_trainers)} trainers.")

        # Force fully evolved — applied last
        if s.trainer_force_fully_evolved:
            self._apply_force_fully_evolved(new_trainers)

        return new_trainers

    def _get_final_evo(self, const: str) -> str:
        """Walk _level_evo_map forward to find the final evolution."""
        current = const
        visited: set = set()
        while True:
            if current in visited:
                break
            visited.add(current)
            evos = self._level_evo_map.get(current, [])
            if not evos:
                break
            # Pick one branch at random (handles split evolutions)
            current = self.rng.choice(evos)[0]
        return current

    def _apply_force_fully_evolved(self, trainers: list):
        """Replace non-final-form Pokémon at or above the level threshold."""
        s = self.settings
        threshold = s.trainer_force_evo_level
        forced = 0
        for trainer in trainers:
            for poke in trainer.party:
                if poke.level < threshold:
                    continue
                final = self._get_final_evo(poke.species_const)
                if final != poke.species_const:
                    poke.species_const = final
                    forced += 1
        self.log(f"  Force fully evolved (lv ≥ {threshold}): {forced} Pokémon updated.")

    # ─────────────────────────────────────────────────────────────────────────
    # In-game trades
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_trades(self, trades: list) -> list:
        """
        Modes:
          unchanged   — return originals untouched
          given_only  — randomize only get_species (what the player receives)
          both        — also randomize give_species (what the player gives)
        """
        s = self.settings
        any_active = (s.trade_mode != "unchanged" or
                      s.trade_random_nicknames or s.trade_random_ot)
        if not any_active or not trades:
            return copy.deepcopy(trades)

        pool = self._build_pool(no_legendaries=False)
        new_trades = copy.deepcopy(trades)
        replaced = 0
        for t in new_trades:
            if s.trade_mode != "unchanged" and pool:
                t.get_species = self._pick(pool)
                replaced += 1
                if s.trade_mode == "both":
                    t.give_species = self._pick(pool)
            if s.trade_random_nicknames:
                t.nickname = make_random_nickname(self.rng, max_len=10)
            if s.trade_random_ot:
                t.ot_name = make_random_ot(self.rng, max_len=7)
        self.log(f"  Randomized {replaced} in-game trade(s).")
        if s.trade_random_nicknames:
            self.log(f"  Nicknames randomized.")
        if s.trade_random_ot:
            self.log(f"  OT names randomized.")
        return new_trades

    # ─────────────────────────────────────────────────────────────────────────
    # Field items
    # ─────────────────────────────────────────────────────────────────────────

    def randomize_field_items(self, field_items: list) -> list:
        """
        Returns a new list of YellowFieldItem objects with modified item constants.

        Modes (field_items_mode):
          "shuffle"      — items are shuffled among themselves; no new items enter
          "random"       — each slot independently picks from the pool
          "random_even"  — pool is shuffled then assigned cyclically so every item
                           appears as close to equally often as possible

        Ban Bad Items removes cheap / situational items from the pool for the
        two random modes.  Shuffle is not affected (it only redistributes what's there).
        """
        from item_data import YELLOW_FIELD_ITEM_POOL_FULL, YELLOW_FIELD_ITEM_POOL_GOOD

        if not field_items:
            self.log("  [SKIP] No field items found — skipping.")
            return []

        new_items = copy.deepcopy(field_items)
        mode = self.settings.field_items_mode
        vis_count = sum(1 for e in field_items if e.item_type == "visible")
        hid_count = sum(1 for e in field_items if e.item_type == "hidden")

        if mode == "shuffle":
            all_consts = [e.item_const for e in field_items]
            self.rng.shuffle(all_consts)
            for entry, new_const in zip(new_items, all_consts):
                entry.item_const = new_const
            self.log(f"  Field items: shuffled {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden).")

        elif mode == "random":
            pool = YELLOW_FIELD_ITEM_POOL_GOOD if self.settings.field_items_ban_bad \
                   else YELLOW_FIELD_ITEM_POOL_FULL
            if not pool:
                self.log("  [WARN] Field item pool is empty — skipping.")
                return new_items
            for entry in new_items:
                entry.item_const = self.rng.choice(pool)
            self.log(f"  Field items: randomized {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden).")

        elif mode == "random_even":
            pool = YELLOW_FIELD_ITEM_POOL_GOOD if self.settings.field_items_ban_bad \
                   else YELLOW_FIELD_ITEM_POOL_FULL
            if not pool:
                self.log("  [WARN] Field item pool is empty — skipping.")
                return new_items
            shuffled = list(pool)
            self.rng.shuffle(shuffled)
            for i, entry in enumerate(new_items):
                entry.item_const = shuffled[i % len(shuffled)]
            self.log(f"  Field items: evenly distributed {len(new_items)} items "
                     f"({vis_count} visible + {hid_count} hidden) "
                     f"across {len(pool)}-item pool.")

        else:  # "unchanged"
            pass

        return new_items

    # ─────────────────────────────────────────────────────────────────────────
    # Evolutions
    # ─────────────────────────────────────────────────────────────────────────

    def apply_evolution_changes(self, entries: list) -> list:
        """
        Make Evolutions Easier:
          • Cap level-up evolutions (middle stage ≤ 30, final stage ≤ 40)
          • Convert any remaining EVOLVE_TRADE entries to EVOLVE_LEVEL
            (Yellow Legacy already converts these, but handled as a safety net)
        """
        s = self.settings
        if not s.easier_evolutions:
            return copy.deepcopy(entries)

        # Identify which target species still evolve further (= middle stages)
        all_sources = {e.source_species for e in entries}

        new_entries = copy.deepcopy(entries)
        level_capped = 0
        trade_fixed  = 0

        for entry in new_entries:
            t = entry.evo_type.upper()
            is_middle = entry.target_species in all_sources
            cap = 30 if is_middle else 40

            if t in ('EVOLVE_LEVEL', 'LEVEL'):
                try:
                    if int(entry.param) > cap:
                        entry.param = str(cap)
                        level_capped += 1
                except (ValueError, TypeError):
                    pass

            elif t in ('EVOLVE_TRADE', 'TRADE'):
                entry.evo_type = 'EVOLVE_LEVEL'
                entry.param    = str(cap)
                trade_fixed += 1

        if level_capped:
            self.log(f"  Level evolutions capped: {level_capped} entry/entries changed.")
        if trade_fixed:
            self.log(f"  Trade evolutions → EVOLVE_LEVEL: {trade_fixed} entry/entries changed.")
        return new_entries

    # ─────────────────────────────────────────────────────────────────────────
    # Catch rates
    # ─────────────────────────────────────────────────────────────────────────

    def apply_catch_rate_minimum(self, catch_rates: list) -> list:
        """
        Raise every catch rate below the selected threshold to the threshold.
        Slider: 1=Normal(≥75) 2=Easy(≥128) 3=Very Easy(≥170) 4=Near-certain(≥210) 5=Guaranteed(255)
        """
        s = self.settings
        threshold = _CATCH_RATE_THRESHOLDS.get(s.wild_min_catch_rate, 0)
        if threshold <= 0:
            return copy.deepcopy(catch_rates)

        new_rates = copy.deepcopy(catch_rates)
        changed = 0
        for entry in new_rates:
            if entry.catch_rate < threshold:
                entry.catch_rate = threshold
                changed += 1

        label = {1: "Normal (≥75)", 2: "Easy (≥128)", 3: "Very Easy (≥170)",
                 4: "Near-certain (≥210)", 5: "Guaranteed (255)"}
        self.log(f"  Catch rate minimum — "
                 f"{label.get(s.wild_min_catch_rate, str(threshold))}: "
                 f"{changed} Pokémon raised.")
        return new_rates

    # ─────────────────────────────────────────────────────────────────────────
    # TM/HM compatibility
    # ─────────────────────────────────────────────────────────────────────────

    def apply_full_hm_compat(self, entries: list) -> list:
        """
        Ensure every Pokémon can learn every HM.
        Auto-detects HM constants by matching the prefix HM_ or HM + digits.
        """
        # Yellow Legacy (pret disassembly) uses plain move names in tmhm macros,
        # not HM_01/HM_CUT-style constants.  Hard-code the Gen 1 HM set.
        all_hm: set = {'CUT', 'FLY', 'SURF', 'STRENGTH', 'FLASH'}

        self.log(f"  Full HM Compatibility: HMs detected: {', '.join(sorted(all_hm))}")

        new_entries = copy.deepcopy(entries)
        updated = 0
        for entry in new_entries:
            existing = {mv.upper() for mv in entry.moves}
            missing = sorted(hm for hm in all_hm if hm not in existing)
            if missing:
                entry.moves.extend(missing)
                updated += 1

        self.log(f"  Full HM Compatibility: {updated} Pokémon given full HM learnability "
                 f"({len(entries) - updated} already compatible).")
        return new_entries
