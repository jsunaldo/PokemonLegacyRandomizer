"""
Pokemon Emerald Legacy Randomizer — Randomization Engine

Applies randomization to parsed data objects. All methods return
new copies; original parsed data is never mutated.
"""

import copy
import random
from dataclasses import dataclass, field
from typing import Optional

from constants_emerald import (
    EMERALD_LEGENDARY_SPECIES, EMERALD_SPECIES_SKIP,
    EMERALD_WILD_TYPES, EMERALD_FISHING_GROUPS,
    EMERALD_BOSS_CLASS_KEYWORDS,
    EMERALD_FIELD_ITEMS_BAD,
    EMERALD_TWO_STAGE_STARTERS,
)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass
class EmeraldRandomizerSettings:
    seed: Optional[int] = None

    # ── General ────────────────────────────────────────────────────────────
    gen_filter: str = 'all'              # "all"|"gen1"|"gen3"
    easier_evolutions: bool = False
    full_hm_compat: bool = False

    # ── Starters (3 Pokémon) ───────────────────────────────────────────────
    starter_mode: str = 'random'          # "unchanged"|"random"|"random_two_stage"|"similar_strength"|"custom"
    starter_no_legendaries: bool = True
    custom_starters: list = None          # [const0, const1, const2] when mode=="custom"
    starter_rand_items: bool = False
    starter_ban_bad_items: bool = True

    # ── Wild Pokémon ───────────────────────────────────────────────────────
    wild_mode: str = 'random'             # "unchanged"|"random"|"area1to1"|"global1to1"
    wild_rule: str = 'none'              # "none"|"similar_strength"|"catch_em_all"|"type_themed"
    wild_no_legendaries: bool = False
    wild_min_catch_rate: int = 0          # 0=off; minimum catch rate value
    wild_rand_held_items: bool = False
    wild_ban_bad_held_items: bool = True

    # Rock smash / fishing follow Wild by default
    randomize_rock_smash: bool = True
    randomize_fishing: bool = True

    # ── Trainers ───────────────────────────────────────────────────────────
    trainer_mode: str = 'random'          # "unchanged"|"random"|"random_even"|"type_themed"|"type_themed_boss"
    trainer_no_legendaries: bool = False
    trainer_boss_no_legendaries: bool = True
    trainer_similar_strength: bool = False
    trainer_rival_starter: bool = False
    trainer_weight_types: bool = False
    trainer_force_fully_evolved: bool = False
    trainer_force_evo_level: int = 30

    # ── Static Pokémon ─────────────────────────────────────────────────────
    static_mode: str = 'unchanged'        # "unchanged"|"swap"|"random"|"similar_strength"

    # ── In-Game Trades (stubs) ─────────────────────────────────────────────
    trade_mode: str = 'unchanged'
    trade_rand_nicknames: bool = False
    trade_rand_ot: bool = False
    trade_rand_ivs: bool = False
    trade_rand_items_flag: bool = False

    # ── Field items ────────────────────────────────────────────────────────
    field_items_mode: str = 'unchanged'   # "unchanged"|"shuffle"|"random"|"random_even"
    field_items_ban_bad: bool = True

    # ── Starting items ─────────────────────────────────────────────────────
    randomize_start_items: bool = False
    start_items: list = None              # bag: list of {"const":..., "qty":...}
    start_pc_items: list = None           # pc:  list of {"const":..., "qty":...}

    # ── PC Pokémon ─────────────────────────────────────────────────────────
    pc_pokemon_enable: bool = False
    pc_pokemon: list = None               # list of PC mon dicts


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EmeraldRandomizerEngine:
    def __init__(self, settings: EmeraldRandomizerSettings,
                 species_consts: list, species_bst: dict, species_types: dict,
                 species_numbers: dict = None,
                 log_fn=None):
        self.settings = settings
        self.species_consts   = species_consts   # all valid SPECIES_* strings
        self.species_bst      = species_bst      # SPECIES_* → int BST
        self.species_types    = species_types    # SPECIES_* → (type1, type2)
        self.species_numbers  = species_numbers or {}  # SPECIES_* → int dex number
        self.log = log_fn or print

        seed = settings.seed if settings.seed is not None else random.randint(0, 2**31 - 1)
        self.rng = random.Random(seed)
        self.log(f"  Seed: {seed}")

        # For type-themed trainer mode: build level evo map on demand
        self._level_evo_map = {}   # species_const → evolved_const (populated externally)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_pool(self, no_legendaries: bool = False) -> list:
        pool = [s for s in self.species_consts if s not in EMERALD_SPECIES_SKIP]
        s = self.settings
        if s.gen_filter == 'gen1':
            pool = [sp for sp in pool if self.species_numbers.get(sp, 999) <= 151]
        elif s.gen_filter == 'gen3':
            pool = [sp for sp in pool if self.species_numbers.get(sp, 0) >= 252]
        if no_legendaries:
            pool = [sp for sp in pool if sp not in EMERALD_LEGENDARY_SPECIES]
        return pool

    def _pick(self, pool: list) -> str:
        return self.rng.choice(pool)

    def _pick_similar_bst(self, species: str, pool: list) -> str:
        target = self.species_bst.get(species, 400)
        sorted_pool = sorted(pool, key=lambda s: abs(self.species_bst.get(s, 400) - target))
        top_n = max(1, len(sorted_pool) // 10)
        return self.rng.choice(sorted_pool[:top_n])

    def _get_primary_type(self, species: str) -> Optional[str]:
        types = self.species_types.get(species)
        return types[0] if types else None

    def _pick_type_pool(self, primary_type: str, pool: list) -> list:
        """Return pool members matching primary_type (or full pool if none match)."""
        if not primary_type:
            return pool
        typed = [s for s in pool if primary_type in self.species_types.get(s, ())]
        return typed if typed else pool

    def _force_evolve(self, species: str, level: int) -> str:
        """Return the most-evolved form reachable at the given level."""
        visited = set()
        current = species
        while current in self._level_evo_map and current not in visited:
            evo_spec, evo_lvl = self._level_evo_map[current]
            if evo_lvl <= level:
                visited.add(current)
                current = evo_spec
            else:
                break
        return current

    # ------------------------------------------------------------------
    # Wild Pokémon
    # ------------------------------------------------------------------

    def randomize_wild(self, wild_json: dict) -> dict:
        """
        Returns a deep copy of wild_json with species replaced.
        Handles land, water, rock_smash, and fishing encounter types.
        Rock smash and fishing can be excluded via settings flags.
        """
        s = self.settings
        if s.wild_mode == 'unchanged':
            return copy.deepcopy(wild_json)

        pool = self._build_pool(no_legendaries=s.wild_no_legendaries)
        if not pool:
            self.log("  [WARN] Wild pool is empty — skipping.")
            return copy.deepcopy(wild_json)

        new_json = copy.deepcopy(wild_json)
        total = 0

        # catch_em_all: create a cycling iterator over shuffled pool
        catch_em_all_iter = None
        if s.wild_rule == 'catch_em_all':
            shuffled = list(pool)
            self.rng.shuffle(shuffled)
            # Repeat enough times to cover all slots
            catch_em_all_iter = iter(shuffled * 200)

        # global1to1: one mapping for all species across the whole file
        global_map = {}
        if s.wild_mode == 'global1to1':
            all_species = set()
            for group in new_json.get('wild_encounter_groups', []):
                for enc in group.get('encounters', []):
                    for enc_type in EMERALD_WILD_TYPES:
                        if not self._should_randomize_type(enc_type):
                            continue
                        enc_data = enc.get(enc_type)
                        if enc_data:
                            for mon in enc_data.get('mons', []):
                                all_species.add(mon.get('species', ''))
            for sp in all_species:
                if sp and sp not in EMERALD_SPECIES_SKIP:
                    global_map[sp] = self._resolve_replacement(sp, pool, s)

        for group in new_json.get('wild_encounter_groups', []):
            for enc in group.get('encounters', []):
                # area1to1: per-encounter-area mapping
                area_map = {}

                for enc_type in EMERALD_WILD_TYPES:
                    if not self._should_randomize_type(enc_type):
                        continue
                    enc_data = enc.get(enc_type)
                    if not enc_data:
                        continue

                    for mon in enc_data.get('mons', []):
                        orig = mon.get('species', '')
                        if not orig or orig in EMERALD_SPECIES_SKIP:
                            continue

                        if s.wild_mode == 'global1to1':
                            mon['species'] = global_map.get(orig, orig)
                        elif s.wild_mode == 'area1to1':
                            if orig not in area_map:
                                area_map[orig] = self._resolve_replacement(orig, pool, s, catch_em_all_iter)
                            mon['species'] = area_map[orig]
                        else:  # random
                            mon['species'] = self._resolve_replacement(orig, pool, s, catch_em_all_iter)
                        total += 1

        self.log(f"  Wild Pokémon: {total} slot(s) randomized (mode={s.wild_mode}).")
        return new_json

    def _should_randomize_type(self, enc_type: str) -> bool:
        s = self.settings
        if enc_type == 'rock_smash_mons' and not s.randomize_rock_smash:
            return False
        if enc_type == 'fishing_mons' and not s.randomize_fishing:
            return False
        return True

    def _resolve_replacement(self, orig: str, pool: list, s, catch_em_all_iter=None) -> str:
        if s.wild_rule == 'similar_strength':
            return self._pick_similar_bst(orig, pool)
        elif s.wild_rule == 'type_themed':
            primary = self._get_primary_type(orig)
            type_pool = self._pick_type_pool(primary, pool)
            return self._pick(type_pool)
        elif s.wild_rule == 'catch_em_all' and catch_em_all_iter is not None:
            try:
                return next(catch_em_all_iter)
            except StopIteration:
                return self._pick(pool)
        return self._pick(pool)

    # ------------------------------------------------------------------
    # Trainers
    # ------------------------------------------------------------------

    def randomize_trainers(self, parties: list) -> list:
        """Returns a deep copy of parties with species replaced."""
        s = self.settings
        if s.trainer_mode == 'unchanged':
            return copy.deepcopy(parties)

        new_parties = copy.deepcopy(parties)
        pool_all  = self._build_pool(no_legendaries=s.trainer_no_legendaries)
        pool_boss = self._build_pool(no_legendaries=s.trainer_boss_no_legendaries)

        # random_even: pre-shuffle pool for even distribution
        even_idx = 0
        pool_shuffled = list(pool_all)
        if s.trainer_mode == 'random_even':
            self.rng.shuffle(pool_shuffled)

        replaced = 0
        for party in new_parties:
            pool = pool_boss if party.is_boss else pool_all
            if not pool:
                continue

            if s.trainer_mode == 'random_even':
                for mon in party.mons:
                    new_sp = pool_shuffled[even_idx % len(pool_shuffled)]
                    even_idx += 1
                    if s.trainer_force_fully_evolved and self._level_evo_map:
                        new_sp = self._force_evolve(new_sp, mon.level)
                    mon.species = new_sp
                    replaced += 1

            elif s.trainer_mode in ('type_themed', 'type_themed_boss'):
                if s.trainer_mode == 'type_themed_boss' and not party.is_boss:
                    # Regular trainers get plain random in boss-themed mode
                    for mon in party.mons:
                        orig_sp = mon.species
                        if s.trainer_similar_strength:
                            new_sp = self._pick_similar_bst(orig_sp, pool)
                        else:
                            new_sp = self._pick(pool)
                        if s.trainer_force_fully_evolved and self._level_evo_map:
                            new_sp = self._force_evolve(new_sp, mon.level)
                        mon.species = new_sp
                        replaced += 1
                    continue

                # Determine theme type from first Pokémon's type (optionally weighted)
                if party.mons:
                    if s.trainer_weight_types:
                        # Weighted type selection: types with more Pokémon are more likely
                        all_types = set()
                        for sp in pool:
                            for t in self.species_types.get(sp, ()):
                                all_types.add(t)
                        type_pools = {t: [sp for sp in pool if t in self.species_types.get(sp, ())] for t in all_types}
                        weighted_types = [(t, len(p)) for t, p in type_pools.items() if p]
                        if weighted_types:
                            type_weights = [w for _, w in weighted_types]
                            chosen_type = self.rng.choices([t for t, _ in weighted_types], weights=type_weights)[0]
                            type_pool = type_pools[chosen_type]
                        else:
                            type_pool = pool
                    else:
                        primary = self._get_primary_type(party.mons[0].species)
                        type_pool = self._pick_type_pool(primary, pool)
                else:
                    type_pool = pool

                for mon in party.mons:
                    new_sp = self._pick(type_pool)
                    if s.trainer_force_fully_evolved and self._level_evo_map:
                        new_sp = self._force_evolve(new_sp, mon.level)
                    mon.species = new_sp
                    replaced += 1

            else:  # random
                for mon in party.mons:
                    orig_sp = mon.species
                    if s.trainer_similar_strength:
                        new_sp = self._pick_similar_bst(orig_sp, pool)
                    else:
                        new_sp = self._pick(pool)
                    if s.trainer_force_fully_evolved and self._level_evo_map:
                        new_sp = self._force_evolve(new_sp, mon.level)
                    mon.species = new_sp
                    replaced += 1

        self.log(f"  Trainers: {replaced} Pokémon replaced across {len(new_parties)} parties.")
        return new_parties

    # ------------------------------------------------------------------
    # Starters
    # ------------------------------------------------------------------

    def randomize_starters(self, starters: list) -> list:
        """Returns a list of 3 new species constants."""
        s = self.settings
        if s.starter_mode == 'unchanged' or not starters:
            return [st.species for st in starters]

        if s.starter_mode == 'custom':
            customs = s.custom_starters or []
            result = []
            pool = self._build_pool(no_legendaries=s.starter_no_legendaries)
            for i in range(len(starters)):
                if i < len(customs) and customs[i] and customs[i] in self.species_consts:
                    result.append(customs[i])
                else:
                    result.append(self._pick(pool))
            self.log(f"  Starters (custom): {result}")
            return result

        pool = self._build_pool(no_legendaries=s.starter_no_legendaries)
        if not pool:
            return [st.species for st in starters]

        if s.starter_mode == 'random_two_stage':
            two_stage_pool = [sp for sp in pool if sp in EMERALD_TWO_STAGE_STARTERS]
            if not two_stage_pool:
                two_stage_pool = pool
            result = []
            for _ in starters:
                available = [sp for sp in two_stage_pool if sp not in result]
                if not available:
                    available = two_stage_pool
                result.append(self._pick(available))
            self.log(f"  Starters (two-stage): {[st.species for st in starters]} → {result}")
            return result

        result = []
        for st in starters:
            if s.starter_mode == 'similar_strength':
                result.append(self._pick_similar_bst(st.species, pool))
            else:  # random
                result.append(self._pick(pool))

        self.log(f"  Starters: {[st.species for st in starters]} → {result}")
        return result

    # ------------------------------------------------------------------
    # Static encounters
    # ------------------------------------------------------------------

    def randomize_static(self, encounters: list) -> list:
        s = self.settings
        if s.static_mode == 'unchanged' or not encounters:
            return copy.deepcopy(encounters)

        pool = self._build_pool(no_legendaries=False)
        new_enc = copy.deepcopy(encounters)

        if s.static_mode == 'swap':
            # Swap species among themselves
            species_list = [e.species for e in new_enc]
            self.rng.shuffle(species_list)
            for enc, sp in zip(new_enc, species_list):
                enc.species = sp

        elif s.static_mode == 'similar_strength':
            for enc in new_enc:
                enc.species = self._pick_similar_bst(enc.species, pool)

        else:  # random
            for enc in new_enc:
                enc.species = self._pick(pool)

        replaced = sum(1 for o, n in zip(encounters, new_enc) if o.species != n.species)
        self.log(f"  Static Pokémon: {replaced} replaced (mode={s.static_mode}).")
        return new_enc

    # ------------------------------------------------------------------
    # Field items
    # ------------------------------------------------------------------

    def randomize_field_items(self, field_items: list) -> list:
        from item_data import EMERALD_FIELD_ITEM_POOL_FULL, EMERALD_FIELD_ITEM_POOL_GOOD

        s = self.settings
        if not field_items:
            self.log("  [SKIP] No field items found.")
            return []

        new_items = copy.deepcopy(field_items)
        mode = s.field_items_mode

        if mode == 'shuffle':
            consts = [e.item_const for e in field_items]
            self.rng.shuffle(consts)
            for entry, c in zip(new_items, consts):
                entry.item_const = c
            self.log(f"  Field items: shuffled {len(new_items)} item(s).")

        elif mode in ('random', 'random_even'):
            pool = EMERALD_FIELD_ITEM_POOL_GOOD if s.field_items_ban_bad \
                   else EMERALD_FIELD_ITEM_POOL_FULL
            if not pool:
                self.log("  [WARN] Field item pool is empty — skipping.")
                return new_items

            if mode == 'random':
                for entry in new_items:
                    entry.item_const = self.rng.choice(pool)
                self.log(f"  Field items: randomized {len(new_items)} item(s).")
            else:  # random_even
                shuffled = list(pool)
                self.rng.shuffle(shuffled)
                for i, entry in enumerate(new_items):
                    entry.item_const = shuffled[i % len(shuffled)]
                self.log(
                    f"  Field items: evenly distributed {len(new_items)} item(s) "
                    f"across {len(pool)}-item pool."
                )

        return new_items
