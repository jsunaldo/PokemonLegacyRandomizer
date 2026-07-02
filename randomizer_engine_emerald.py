"""
Pokemon Emerald Legacy Randomizer - Randomization Engine

Applies randomization settings to parsed Emerald data structures.
All operations return modified copies; originals are not mutated.
"""

import copy
import random
from dataclasses import dataclass, field
from typing import Optional

from constants_emerald import (
    ALL_SPECIES_CONSTS, GEN1_CONSTS, GEN2_CONSTS, GEN3_CONSTS,
    LEGENDARY_CONSTS, DEFAULT_STARTERS, FIELD_ITEM_POOL,
    FIELD_ITEM_BAD, HM_FIELD_NAMES, BASIC_WITH_TWO_EVOLUTIONS,
    ALL_TYPES, SPECIES_TYPES,
    WILD_HELD_ITEM_POOL_GOOD, WILD_HELD_ITEM_POOL_FULL,
)
from parser_emerald import (
    TrainerParty, TrainerMon,
    FieldItem, StaticEncounter, TMHMEntry, WildHeldItemEntry,
)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass
class EmeraldRandomizerSettings:
    seed: Optional[int] = None

    # Generation filter — any combination of gens may be enabled
    include_gen1: bool = True
    include_gen2: bool = True
    include_gen3: bool = True

    # Starters
    starter_mode: str = "random"        # "unchanged"|"custom"|"random"|"random_two_stage"
    starter_no_legendaries: bool = True
    starter_rand_items: bool = False
    starter_ban_bad_items: bool = True
    custom_starters: list = field(default_factory=lambda: [None, None, None])

    # Wild
    wild_mode: str = "random"           # "unchanged"|"random"|"area1to1"|"global1to1"
    wild_rule: str = "none"             # "none"|"similar_strength"|"type_themed"
    wild_no_legendaries: bool = False
    wild_rand_held_items: bool = False
    wild_ban_bad_held_items: bool = True
    # Rock smash and fishing are always included — no longer user-configurable

    # Trainers
    trainer_mode: str = "random"        # "unchanged"|"random"|"random_even"|"type_themed"|"type_themed_boss"
    trainer_no_legendaries: bool = False
    trainer_boss_no_legendaries: bool = True
    trainer_similar_strength: bool = False
    trainer_rival_starter: bool = False
    trainer_weight_types: bool = False
    trainer_force_fully_evolved: bool = False
    trainer_force_evo_level: int = 30

    # Static encounters
    static_mode: str = "unchanged"      # "unchanged"|"random"|"swap"

    # In-game trades (stub)
    trade_mode: str = "unchanged"
    trade_rand_nicknames: bool = False
    trade_rand_ot: bool = False
    trade_rand_ivs: bool = False
    trade_rand_items_flag: bool = False

    # Field items
    field_items_mode: str = "unchanged"
    field_items_ban_bad: bool = True

    # Evolutions
    remove_time_evolutions: bool = False  # EVO_FRIENDSHIP_DAY/NIGHT → EVO_ITEM + Sun/Moon Stone

    # TM/HM compat
    full_hm_compat: bool = False

    # Starting items
    randomize_start_items: bool = False
    start_items: list = field(default_factory=list)
    start_pc_items: list = field(default_factory=list)

    # PC Pokémon
    pc_pokemon_enable: bool = False
    pc_pokemon: list = field(default_factory=list)

    # Shop patches
    zero_grinding: bool = False   # add Rare Candy to Oldale Mart at $10
    elite4_prep: bool = False     # stock Pokémon League Mart at $10


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# Trainer classes considered "bosses" (no legendaries for them by default)
_BOSS_CLASSES = {
    "ROXANNE", "BRAWLY", "WATTSON", "FLANNERY", "NORMAN",
    "WINONA", "TATE", "LIZA", "JUAN", "WALLACE",
    "STEVEN", "CHAMPION",
    "PHOEBE", "GLACIA", "DRAKE", "SIDNEY",
    "MAXIE", "ARCHIE",
    "RIVAL",
}


class EmeraldRandomizerEngine:

    def __init__(
        self,
        settings: EmeraldRandomizerSettings,
        species_consts: list,
        species_bst: dict,
        species_types: dict,
        species_numbers: dict,
        log_fn=None,
    ):
        self.s        = settings
        self._bst     = species_bst
        self._types   = species_types
        self._numbers = species_numbers
        self._log     = log_fn or (lambda msg: None)

        # Seed the RNG
        if settings.seed is not None:
            random.seed(settings.seed)

        # Build the filtered species pool
        self._pool = self._build_pool(species_consts)

    # -----------------------------------------------------------------------
    # Pool construction
    # -----------------------------------------------------------------------

    def _build_pool(self, species_consts: list) -> list:
        # Build the union of all selected generations
        base = []
        if self.s.include_gen1:
            base += list(GEN1_CONSTS)
        if self.s.include_gen2:
            base += list(GEN2_CONSTS)
        if self.s.include_gen3:
            base += list(GEN3_CONSTS)

        # If nothing was selected, fall back to all species (safety net)
        if not base:
            base = list(ALL_SPECIES_CONSTS)

        # Deduplicate while preserving order, then restrict to parsed species
        seen = set()
        deduped = []
        for c in base:
            if c not in seen:
                seen.add(c)
                deduped.append(c)

        valid = set(species_consts)
        return [c for c in deduped if c in valid]

    def _filtered(self, no_legendaries: bool = False) -> list:
        pool = self._pool
        if no_legendaries:
            pool = [c for c in pool if c not in LEGENDARY_CONSTS]
        return pool or list(self._pool)  # fallback if filter too aggressive

    def _pick(self, pool: list, exclude: set = None) -> str:
        if exclude:
            filtered = [c for c in pool if c not in exclude]
            if not filtered:
                filtered = pool
        else:
            filtered = pool
        return random.choice(filtered)

    def _pick_bst(self, pool: list, target_bst: int, tolerance: float = 0.30,
                  exclude: set = None) -> str:
        """Pick a species with BST within ±tolerance of target_bst."""
        lo = target_bst * (1 - tolerance)
        hi = target_bst * (1 + tolerance)
        candidates = [c for c in pool
                      if lo <= self._bst.get(c, 400) <= hi
                      and (not exclude or c not in exclude)]
        if not candidates:
            candidates = pool
        return random.choice(candidates)

    # -----------------------------------------------------------------------
    # Starters
    # -----------------------------------------------------------------------

    def randomize_starters(self, starters: list) -> list:
        """Return list of 3 new SPECIES_X constants (strings)."""
        pool = self._filtered(self.s.starter_no_legendaries)
        mode = self.s.starter_mode

        if mode == "unchanged":
            return [sl.species for sl in starters]

        if mode == "custom":
            result = []
            for i, sl in enumerate(starters):
                custom = (self.s.custom_starters[i]
                          if i < len(self.s.custom_starters) else None)
                result.append(custom if custom else sl.species)
            return result

        if mode == "random_two_stage":
            # Restrict to first-stage Pokémon with 2 evolutions, filtered by gen
            two_stage_pool = [c for c in self._pool if c in BASIC_WITH_TWO_EVOLUTIONS]
            if self.s.starter_no_legendaries:
                two_stage_pool = [c for c in two_stage_pool if c not in LEGENDARY_CONSTS]
            if len(two_stage_pool) < 3:
                self._log("  [WARN] Two-stage pool too small after filtering; falling back to full random.")
                two_stage_pool = pool
            pool = two_stage_pool

        # "random" or "random_two_stage" — pick 3 distinct species
        chosen = []
        used   = set()
        for sl in starters:
            sp = self._pick(pool, exclude=used)
            chosen.append(sp)
            used.add(sp)
            self._log(f"  Starter {sl.index + 1}: {sl.species} → {sp}")

        return chosen

    # -----------------------------------------------------------------------
    # Wild encounters (JSON)
    # -----------------------------------------------------------------------

    def randomize_wild(self, wild_json: dict) -> dict:
        """Return a deep copy of wild_json with species randomized."""
        result = copy.deepcopy(wild_json)
        mode   = self.s.wild_mode
        rule   = self.s.wild_rule
        pool   = self._filtered(self.s.wild_no_legendaries)

        if mode == "unchanged":
            return result

        # ── Catch 'Em All: two-pass approach ──────────────────────────────
        # Collect every eligible slot reference first, then distribute.
        if rule == "catch_em_all":
            all_slots = []
            for group in result.get("wild_encounter_groups", []):
                for encounter in group.get("encounters", []):
                    for enc_type in ("land_mons", "water_mons", "rock_smash_mons"):
                        sl = encounter.get(enc_type, {})
                        if isinstance(sl, dict):
                            all_slots.extend(sl.get("mons") or [])
                    fishing = encounter.get("fishing_mons")
                    if isinstance(fishing, dict):
                        all_slots.extend(fishing.get("mons") or [])

            shuffled = list(pool)
            random.shuffle(shuffled)
            for i, slot in enumerate(all_slots):
                if slot.get("species"):
                    slot["species"] = shuffled[i % len(shuffled)]

            total = self._count_wild_slots(result)
            self._log(f"  Catch 'Em All: {total} slots distributed across {len(pool)} pool species.")
            return result

        # ── All other modes: per-area iteration ───────────────────────────
        global_map: dict = {}

        for group in result.get("wild_encounter_groups", []):
            for encounter in group.get("encounters", []):
                map_name = encounter.get("map", "?")
                area_map: dict = {}

                # Type themed: pick one type per area, filter pool to it
                if rule == "type_themed":
                    chosen_type = random.choice(ALL_TYPES)
                    area_pool = [c for c in pool
                                 if chosen_type in SPECIES_TYPES.get(c, [])]
                    area_pool = area_pool if area_pool else pool
                else:
                    area_pool = pool

                for enc_type in ("land_mons", "water_mons", "rock_smash_mons"):
                    sl = encounter.get(enc_type, {})
                    slot_list = sl.get("mons") if isinstance(sl, dict) else None
                    if not slot_list:
                        continue
                    self._randomize_slot_list(
                        slot_list, area_pool, mode, area_map, global_map, map_name
                    )

                fishing = encounter.get("fishing_mons")
                slot_list = fishing.get("mons") if isinstance(fishing, dict) else None
                if slot_list:
                    self._randomize_slot_list(
                        slot_list, area_pool, mode, area_map, global_map, map_name
                    )

        total = self._count_wild_slots(result)
        self._log(f"  Randomized {total} wild slot(s)")
        return result

    def _randomize_slot_list(self, slot_list, pool, mode, area_map, global_map, map_name):
        """Randomize species in a flat list of slot dicts (mutates in-place)."""
        rule = self.s.wild_rule
        for slot in slot_list:
            orig = slot.get("species", "")
            if not orig:
                continue

            if mode == "random":
                if rule == "similar_strength":
                    bst = self._bst.get(orig, 400)
                    new = self._pick_bst(pool, bst)
                else:
                    new = self._pick(pool)

            elif mode == "area1to1":
                if orig not in area_map:
                    area_map[orig] = self._pick(pool, exclude=set(area_map.values()))
                new = area_map[orig]

            elif mode == "global1to1":
                if orig not in global_map:
                    global_map[orig] = self._pick(pool, exclude=set(global_map.values()))
                new = global_map[orig]

            else:
                new = orig

            slot["species"] = new

    def _count_wild_slots(self, wild_json: dict) -> int:
        count = 0
        for group in wild_json.get("wild_encounter_groups", []):
            for enc in group.get("encounters", []):
                for t in ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons"):
                    sl = enc.get(t, {})
                    if isinstance(sl, dict):
                        count += len(sl.get("mons", []))
        return count

    # -----------------------------------------------------------------------
    # Trainer parties
    # -----------------------------------------------------------------------

    def randomize_trainers(self, parties: list) -> list:
        """Return a new list of TrainerParty with species randomized."""
        mode = self.s.trainer_mode
        if mode == "unchanged":
            return copy.deepcopy(parties)

        pool_normal = self._filtered(self.s.trainer_no_legendaries)
        pool_boss   = self._filtered(self.s.trainer_boss_no_legendaries)
        result  = []
        changed = 0

        # ── Random (Even Distribution) ────────────────────────────────────
        if mode == "random_even":
            all_slots = [mon for party in parties for mon in party.mons]
            shuffled  = list(pool_normal)
            random.shuffle(shuffled)
            flat_new  = [shuffled[i % len(shuffled)] for i in range(len(all_slots))]
            idx = 0
            for party in parties:
                new_mons = []
                for mon in party.mons:
                    new_mons.append(TrainerMon(
                        species=flat_new[idx], level=mon.level,
                        iv=mon.iv, held_item=mon.held_item, moves=list(mon.moves),
                    ))
                    idx += 1
                    changed += 1
                result.append(TrainerParty(
                    party_label=party.party_label, mons=new_mons,
                    species_line_numbers=list(party.species_line_numbers),
                    source_file=party.source_file,
                ))
            self._log(f"  Even distribution: {changed} trainer Pokémon across {len(result)} parties")
            return result

        # ── Type Themed helpers ───────────────────────────────────────────
        def _type_pool_for_trainer(base_pool):
            """Pick a random type and return pool filtered to it."""
            if self.s.trainer_weight_types:
                # Weight by how many Pokémon each type has
                type_counts = {}
                for c in base_pool:
                    for t in SPECIES_TYPES.get(c, []):
                        type_counts[t] = type_counts.get(t, 0) + 1
                types  = list(type_counts.keys())
                counts = [type_counts[t] for t in types]
                chosen = random.choices(types, weights=counts, k=1)[0]
            else:
                chosen = random.choice(ALL_TYPES)
            typed = [c for c in base_pool if chosen in SPECIES_TYPES.get(c, [])]
            return typed if typed else base_pool

        # ── Main loop (random / type_themed / type_themed_boss) ───────────
        for party in parties:
            is_boss = any(bc in party.party_label.upper() for bc in _BOSS_CLASSES)
            pool    = pool_boss if is_boss else pool_normal

            if mode in ("type_themed", "type_themed_boss"):
                if mode == "type_themed" or is_boss:
                    pool = _type_pool_for_trainer(pool)
                # else regular trainer in type_themed_boss → stays random

            new_mons = []
            for mon in party.mons:
                if self.s.trainer_similar_strength:
                    bst    = self._bst.get(mon.species, 400)
                    new_sp = self._pick_bst(pool, bst)
                else:
                    new_sp = self._pick(pool)

                new_mons.append(TrainerMon(
                    species=new_sp, level=mon.level,
                    iv=mon.iv, held_item=mon.held_item, moves=list(mon.moves),
                ))
                changed += 1

            result.append(TrainerParty(
                party_label=party.party_label, mons=new_mons,
                species_line_numbers=list(party.species_line_numbers),
                source_file=party.source_file,
            ))

        self._log(f"  Randomized {changed} trainer Pokémon across {len(result)} part(ies)")
        return result

    # -----------------------------------------------------------------------
    # Rival carries starter
    # -----------------------------------------------------------------------

    # Player's starter (from the party-label suffix) -> which randomized
    # starter lineage the rival carries (the type that counters the player's,
    # matching the original Treecko→Torchic→Mudkip triangle).
    _RIVAL_COUNTER = {0: 1, 1: 2, 2: 0}
    _PLAYER_SUFFIX = {"Treecko": 0, "Torchic": 1, "Mudkip": 2}

    def _evo_chain(self, base: str, evolution_to: dict) -> list:
        """Return [base, evo1, evo2, ...] following first-evolution links."""
        chain = [base]
        seen  = {base}
        cur   = base
        for _ in range(3):
            nxt = evolution_to.get(cur)
            if not nxt or nxt in seen:
                break
            chain.append(nxt)
            seen.add(nxt)
            cur = nxt
        return chain

    def apply_rival_starter(self, orig_parties: list, rand_parties: list,
                            rand_starters: list, evolution_to: dict):
        """
        Lock each rival (Brendan/May) party's starter slot to the appropriate
        evolution STAGE of the randomized starter that counters the player's
        choice.  Stage is matched by position in the original starter's chain,
        so it works regardless of the randomized starter's evolution method.

        orig_parties / rand_parties are aligned 1:1 (same order).
        rand_starters is the list of 3 randomized starter SPECIES_X constants
        in DEFAULT_STARTERS order (Treecko, Torchic, Mudkip lineage slots).
        """
        if not rand_starters or len(rand_starters) < 3:
            self._log("  [INFO] Rival starter: no randomized starters available — skipping.")
            return

        # Original starter chains (Treecko/Torchic/Mudkip lineages)
        orig_chains = [self._evo_chain(DEFAULT_STARTERS[i], evolution_to) for i in range(3)]
        rand_chains = [self._evo_chain(rand_starters[i], evolution_to) for i in range(3)]

        by_label = {p.party_label: p for p in rand_parties}
        rival_slots = 0

        for orig in orig_parties:
            label = orig.party_label
            if not (("Brendan" in label) or ("May" in label)):
                continue
            # Player's starter is encoded as the label suffix
            player_lineage = None
            for suffix, idx in self._PLAYER_SUFFIX.items():
                if label.endswith(suffix):
                    player_lineage = idx
                    break
            if player_lineage is None:
                continue

            rival_lineage = self._RIVAL_COUNTER[player_lineage]
            orig_chain    = orig_chains[rival_lineage]
            rand_chain    = rand_chains[rival_lineage]

            rand_party = by_label.get(label)
            if rand_party is None:
                continue

            # Find the slot whose ORIGINAL species belongs to the rival's
            # starter chain, then set the matching stage of the randomized one.
            for slot_idx, omon in enumerate(orig.mons):
                if omon.species in orig_chain and slot_idx < len(rand_party.mons):
                    stage = orig_chain.index(omon.species)
                    new_sp = rand_chain[min(stage, len(rand_chain) - 1)]
                    rand_party.mons[slot_idx].species = new_sp
                    rival_slots += 1

        if rival_slots:
            self._log(f"  Rival starter: locked {rival_slots} rival party slot(s) to starter lineage.")
        else:
            self._log("  [INFO] Rival starter: no rival starter slots found.")

    # -----------------------------------------------------------------------
    # Ability randomization (.abilities in species_info.h)
    # -----------------------------------------------------------------------

    def randomize_abilities(self, entries: list, pool: list) -> list:
        """
        Return copies of AbilityEntry with each non-NONE slot replaced by a
        random ability from the pool. Species with a single ability keep a
        single ability (slot 2 stays ABILITY_NONE); dual-ability species get
        two distinct random abilities.
        """
        if not entries or not pool:
            self._log("  [SKIP] No ability data found — skipping.")
            return []

        result = []
        for e in entries:
            a1 = random.choice(pool)
            if e.ability2 != "ABILITY_NONE":
                a2 = random.choice([a for a in pool if a != a1])
            else:
                a2 = "ABILITY_NONE"
            result.append(type(e)(species=e.species, ability1=a1, ability2=a2,
                                  source_file=e.source_file,
                                  line_index=e.line_index))
        self._log(f"  Abilities: randomized {len(result)} species.")
        return result

    # -----------------------------------------------------------------------
    # Wild held items (.itemCommon / .itemRare)
    # -----------------------------------------------------------------------

    def randomize_wild_held_items(self, entries: list) -> list:
        """
        Return a new list of WildHeldItemEntry with each non-NONE held-item
        slot reassigned a random item.  Uses the GOOD pool when
        wild_ban_bad_held_items is set, otherwise the FULL pool.
        """
        if not entries:
            self._log("  [SKIP] No wild held item slots found — skipping.")
            return []

        pool = (WILD_HELD_ITEM_POOL_GOOD if self.s.wild_ban_bad_held_items
                else WILD_HELD_ITEM_POOL_FULL)

        new_entries = copy.deepcopy(entries)
        for e in new_entries:
            e.item = random.choice(pool)

        self._log(f"  Wild held items: randomized {len(new_entries)} slot(s).")
        return new_entries

    # -----------------------------------------------------------------------
    # Static encounters
    # -----------------------------------------------------------------------

    def randomize_static(self, statics: list) -> list:
        """
        Return a new list of StaticEncounter with species randomized.

        Modes:
          unchanged       — no changes
          swap            — legendary statics swap with other legendaries;
                            non-legendary statics swap with non-legendaries
          random          — every encounter replaced with any Pokémon at random
          similar_strength— replaced with a Pokémon of similar Base Stat Total
        """
        mode = self.s.static_mode
        if mode == "unchanged":
            return copy.deepcopy(statics)

        pool_all    = self._filtered(no_legendaries=False)
        pool_normal = [c for c in pool_all if c not in LEGENDARY_CONSTS]
        pool_legend = [c for c in pool_all if c in LEGENDARY_CONSTS] or pool_all

        result = []

        if mode == "swap":
            # Separate into legendary and non-legendary buckets, shuffle each
            legends    = [st for st in statics if st.species in LEGENDARY_CONSTS]
            standards  = [st for st in statics if st.species not in LEGENDARY_CONSTS]

            leg_species = [st.species for st in legends]
            std_species = [st.species for st in standards]
            random.shuffle(leg_species)
            random.shuffle(std_species)

            leg_map = {id(st): sp for st, sp in zip(legends, leg_species)}
            std_map = {id(st): sp for st, sp in zip(standards, std_species)}

            for st in statics:
                new_sp = leg_map.get(id(st)) or std_map.get(id(st), st.species)
                result.append(StaticEncounter(
                    species=new_sp, level=st.level,
                    source_file=st.source_file, line_index=st.line_index,
                ))

        else:
            for st in statics:
                if mode == "similar_strength":
                    bst    = self._bst.get(st.species, 400)
                    new_sp = self._pick_bst(pool_all, bst)
                else:
                    new_sp = self._pick(pool_all)
                self._log(f"  Static {st.species} (lv{st.level}) → {new_sp}")
                result.append(StaticEncounter(
                    species=new_sp, level=st.level,
                    source_file=st.source_file, line_index=st.line_index,
                ))

        return result

    # -----------------------------------------------------------------------
    # In-game trades
    # -----------------------------------------------------------------------

    def randomize_trades(self, trades: list) -> list:
        """
        Return a new list of EmeraldInGameTrade with randomized fields.

        Modes:
          unchanged  — return originals untouched
          given_only — randomize only the species the player receives (.species)
          both       — randomize both .species and .requestedSpecies

        Sub-options (applied on top of any randomize mode):
          trade_rand_nicknames — random GBA-safe nickname (up to 10 chars)
          trade_rand_ot        — random OT name (up to 7 chars)
          trade_rand_ivs       — randomize all 6 IVs (0–31)
          trade_rand_items     — random held item from Emerald item pool
        """
        import string as _string
        from constants_emerald import FIELD_ITEM_POOL

        if self.s.trade_mode == "unchanged" or not trades:
            return copy.deepcopy(trades)

        pool = self._filtered(no_legendaries=False)
        result = copy.deepcopy(trades)

        def _rand_name(max_len: int) -> str:
            chars = _string.ascii_uppercase + _string.digits
            length = random.randint(3, max_len)
            return "".join(random.choice(chars) for _ in range(length))

        def _rand_ivs() -> str:
            vals = [str(random.randint(0, 31)) for _ in range(6)]
            return "{" + ", ".join(vals) + "}"

        replaced = 0
        for t in result:
            if pool:
                old_sp = t.species
                t.species = self._pick(pool)
                self._log(f"  Trade [{t.trade_label}] gives {old_sp} → {t.species}")
                replaced += 1

                if self.s.trade_mode == "both":
                    old_req = t.requested_species
                    t.requested_species = self._pick(pool)
                    self._log(f"    requests {old_req} → {t.requested_species}")

            if self.s.trade_rand_nicknames:
                t.nickname = _rand_name(10)

            if self.s.trade_rand_ot:
                t.ot_name = _rand_name(7)

            if self.s.trade_rand_ivs and t.ivs_line >= 0:
                t.ivs_raw = _rand_ivs()

            if self.s.trade_rand_items_flag and t.held_item_line >= 0:
                t.held_item = random.choice(list(FIELD_ITEM_POOL))

        self._log(f"  Randomized {replaced} in-game trade(s).")
        return result

    # -----------------------------------------------------------------------
    # Field items
    # -----------------------------------------------------------------------

    def randomize_field_items(self, field_items: list) -> list:
        """
        Return a new list of FieldItem with item_const randomized.

        Modes:
          unchanged     — no changes
          shuffle       — existing items shuffled among locations (no new items)
          random        — each location independently replaced from pool
          random_even   — pool distributed evenly across all locations
        """
        mode = self.s.field_items_mode
        if mode == "unchanged":
            return copy.deepcopy(field_items)

        if mode == "shuffle":
            items = [fi.item_const for fi in field_items]
            random.shuffle(items)
            result = [
                FieldItem(item_const=items[i], source_file=fi.source_file, line_index=fi.line_index)
                for i, fi in enumerate(field_items)
            ]
            self._log(f"  Shuffled {len(result)} field item(s)")
            return result

        pool = list(FIELD_ITEM_POOL)
        if self.s.field_items_ban_bad:
            pool = [i for i in pool if i not in FIELD_ITEM_BAD]
        if not pool:
            pool = list(FIELD_ITEM_POOL)

        if mode == "random_even":
            shuffled = list(pool)
            random.shuffle(shuffled)
            result = [
                FieldItem(
                    item_const=shuffled[i % len(shuffled)],
                    source_file=fi.source_file,
                    line_index=fi.line_index,
                )
                for i, fi in enumerate(field_items)
            ]
            self._log(f"  Evenly distributed {len(result)} field item(s) across {len(pool)} pool items")
            return result

        # "random"
        result = []
        for fi in field_items:
            result.append(FieldItem(
                item_const=random.choice(pool),
                source_file=fi.source_file,
                line_index=fi.line_index,
            ))
        self._log(f"  Randomized {len(result)} field item(s)")
        return result

    # -----------------------------------------------------------------------
    # TM/HM compatibility
    # -----------------------------------------------------------------------

    def apply_full_hm_compat(self, tmhm_entries: list) -> list:
        """Return copies of TMHMEntry with all HM fields set to TRUE."""
        result = []
        for entry in tmhm_entries:
            new_entry = TMHMEntry(
                species=entry.species,
                hm_fields=set(HM_FIELD_NAMES),  # all 8 HMs
                source_file=entry.source_file,
                block_start=entry.block_start,
                block_end=entry.block_end,
            )
            result.append(new_entry)
        self._log(f"  Applied full HM compat to {len(result)} species")
        return result
