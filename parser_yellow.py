"""
Pokemon Yellow Legacy Randomizer - ASM Source Parser

Parses Yellow Legacy (Gen 1 / pokeyellow base) source files to extract:
  - Wild Pokemon encounters (grass, water, old rod, good rod, super rod)
  - Trainer parties (same-level and variable-level formats)
  - Starter Pokemon location (STARTER_PIKACHU references in OaksLab.asm)
  - In-game trades (TradeMons table)
  - Evolution entries (EVOLVE_LEVEL, EVOLVE_ITEM, EVOLVE_TRADE)
  - Catch rates and TM/HM compatibility (from per-Pokemon base stats files)
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from constants_yellow import (
    YELLOW_POKEMON_CONSTANTS, YELLOW_POKEMON_ID_TO_CONST,
    YELLOW_MOVE_CONSTANTS, YELLOW_ITEM_CONSTANTS,
    YELLOW_WILD_MAPS_DIR, YELLOW_TRAINER_PARTIES_FILE,
    YELLOW_STARTER_FILE, YELLOW_TRADES_FILE, YELLOW_EVOS_MOVES_FILE,
    YELLOW_BASE_STATS_DIR, YELLOW_OLD_ROD_FILE, YELLOW_GOOD_ROD_FILE,
    YELLOW_SUPER_ROD_FILE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class YellowWildSlot:
    level: int
    species_const: str

    @property
    def species_id(self):
        return YELLOW_POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class YellowWildGroup:
    """One encounter area (grass OR water) for a single map."""
    location: str       # e.g. "Route1"
    enc_type: str       # "grass" or "water"
    rate: int           # encounter rate (0 = no encounters)
    slots: list         # list[YellowWildSlot]
    source_file: str    # absolute path
    line_start: int     # line index of def_*_wildmons
    line_end: int       # line index of end_*_wildmons


@dataclass
class YellowFishingSlot:
    """One entry in old_rod.asm or good_rod.asm (just level, species)."""
    level: int
    species_const: str
    source_file: str
    line_index: int
    full_line: str

    @property
    def species_id(self):
        return YELLOW_POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class YellowSuperRodSlot:
    """One Pokémon entry from super_rod.asm per-location table."""
    location_const: str     # e.g. "PALLET_TOWN"
    species_const: str
    level: int
    source_file: str
    line_index: int         # line index of the whole db row
    slot_index: int         # 0-3 within that row


@dataclass
class YellowTrainerMon:
    level: int
    species_const: str

    @property
    def species_id(self):
        return YELLOW_POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class YellowTrainer:
    class_name: str         # e.g. "Youngster"
    party: list             # list[YellowTrainerMon]
    same_level: bool        # True = format 1 (all same level); False = format 2 ($FF)
    source_file: str
    line_start: int         # line index of the db ... line
    line_end: int           # line index of the terminating 0


@dataclass
class YellowStarterLocation:
    """One 'ld a, STARTER_PIKACHU' line in OaksLab.asm."""
    species_const: str      # current species (normally PIKACHU)
    source_file: str
    line_index: int
    full_line: str


@dataclass
class YellowTrade:
    """One entry in the TradeMons table in data/events/trades.asm."""
    give_species: str   # species player gives (requested)
    get_species: str    # species player receives (given)
    nickname: str       # NPC nickname for received Pokémon
    source_file: str
    line_index: int
    full_line: str


@dataclass
class YellowFieldItem:
    """An overworld item pickup found via a script macro in Yellow Legacy."""
    item_const: str     # e.g. "ULTRA_BALL", "RARE_CANDY"
    item_type: str      # "visible" or "hidden"
    source_file: str
    line_index: int
    full_line: str


@dataclass
class YellowStaticEncounter:
    """A scripted static encounter or gift Pokémon in a Yellow Legacy script file."""
    species_const: str    # e.g. "MEWTWO", "SNORLAX"
    is_legendary: bool
    source_file: str
    line_index: int
    full_line: str
    macro_type: str       # "battle" or "givepoke"
    label: str            # nearest preceding ASM label (for context)


@dataclass
class YellowEvoEntry:
    """One evolution line from data/pokemon/evos_moves.asm."""
    source_species: str     # the Pokémon that evolves (from surrounding label)
    evo_type: str           # "EVOLVE_LEVEL", "EVOLVE_ITEM", "EVOLVE_TRADE"
    target_species: str
    param: str              # level number, item const, or "1"
    item_const: str         # only set for EVOLVE_ITEM, else ""
    source_file: str
    line_index: int
    full_line: str


@dataclass
class YellowCatchRate:
    species_const: str
    catch_rate: int
    source_file: str
    line_index: int
    full_line: str


@dataclass
class YellowTMHMCompat:
    species_const: str
    moves: list             # list of move constant strings
    source_file: str
    line_index: int
    full_line: str


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class YellowLegacyParser:
    def __init__(self, source_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.log = log_fn or print

        self.wild_groups: list        = []   # list[YellowWildGroup]
        self.old_rod_slots: list      = []   # list[YellowFishingSlot]
        self.good_rod_slots: list     = []   # list[YellowFishingSlot]
        self.super_rod_slots: list    = []   # list[YellowSuperRodSlot]
        self.trainers: list           = []   # list[YellowTrainer]
        self.starters: list           = []   # list[YellowStarterLocation]
        self.trades: list             = []   # list[YellowTrade]
        self.static_encounters: list  = []   # list[YellowStaticEncounter]
        self.field_items: list        = []   # list[YellowFieldItem]
        self.evolutions: list         = []   # list[YellowEvoEntry]
        self.catch_rates: list        = []   # list[YellowCatchRate]
        self.tmhm_compat: list        = []   # list[YellowTMHMCompat]
        self.pokemon_types: dict      = {}   # {const: (type1, type2)}

    def parse_all(self):
        """Run all parsers. Returns True if starters were found."""
        self.log("Parsing wild encounters...")
        self._parse_wild_encounters()

        self.log("Parsing fishing encounters...")
        self._parse_fishing()

        self.log("Parsing trainer parties...")
        self._parse_trainers()

        self.log("Parsing starter location...")
        self._parse_starter()

        self.log("Parsing in-game trades...")
        self._parse_trades()

        self.log("Scanning for static encounters...")
        self._parse_static_encounters()

        self.log("Scanning for field items...")
        self._parse_field_items()

        self.log("Parsing evolutions...")
        self._parse_evolutions()

        self.log("Parsing base stats (catch rates, TM/HM, types)...")
        self._parse_base_stats()

        grass  = sum(1 for g in self.wild_groups if g.enc_type == 'grass' and g.rate > 0)
        water  = sum(1 for g in self.wild_groups if g.enc_type == 'water' and g.rate > 0)
        leg    = sum(1 for e in self.static_encounters if e.is_legendary)
        std    = sum(1 for e in self.static_encounters if not e.is_legendary)
        fi_vis = sum(1 for f in self.field_items if f.item_type == 'visible')
        fi_hid = sum(1 for f in self.field_items if f.item_type == 'hidden')
        self.log(
            f"Parse complete: {grass} grass + {water} water encounter areas, "
            f"{len(self.old_rod_slots)} old rod + {len(self.good_rod_slots)} good rod slots, "
            f"{len(self.super_rod_slots)} super rod slots, "
            f"{len(self.trainers)} trainers, "
            f"{len(self.starters)} starter line(s), "
            f"{len(self.trades)} trade(s), "
            f"{len(self.static_encounters)} static encounters ({leg} legendary, {std} standard), "
            f"{len(self.field_items)} field items ({fi_vis} visible, {fi_hid} hidden), "
            f"{len(self.evolutions)} evolution entr(ies), "
            f"{len(self.catch_rates)} catch rate entr(ies), "
            f"{len(self.tmhm_compat)} TM/HM compat entr(ies)."
        )
        return len(self.starters) > 0

    # -------------------------------------------------------------------------
    # Wild encounters (grass / water per map file)
    # -------------------------------------------------------------------------

    def _parse_wild_encounters(self):
        maps_dir = os.path.join(self.source_dir, YELLOW_WILD_MAPS_DIR)
        if not os.path.isdir(maps_dir):
            self.log(f"  [WARN] Wild maps dir not found: {YELLOW_WILD_MAPS_DIR}")
            return

        slot_re  = re.compile(r'^\s+db\s+(\d+)\s*,\s*([A-Z][A-Z0-9_]+)', re.IGNORECASE)
        start_grass_re = re.compile(r'^\s+def_grass_wildmons\s+(\d+)', re.IGNORECASE)
        start_water_re = re.compile(r'^\s+def_water_wildmons\s+(\d+)', re.IGNORECASE)
        end_grass_re   = re.compile(r'^\s+end_grass_wildmons', re.IGNORECASE)
        end_water_re   = re.compile(r'^\s+end_water_wildmons', re.IGNORECASE)
        label_re       = re.compile(r'^([A-Za-z]\w*)WildMons\s*:', re.IGNORECASE)

        for fname in sorted(os.listdir(maps_dir)):
            if not fname.endswith('.asm'):
                continue
            filepath = os.path.join(maps_dir, fname)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except Exception:
                continue

            location = fname[:-4]   # strip .asm → e.g. "Route1"
            # Try to get location from the label line
            for raw in lines:
                m = label_re.match(raw)
                if m:
                    location = m.group(1)
                    break

            enc_type = None
            rate = 0
            slots = []
            blk_start = 0

            for i, raw in enumerate(lines):
                line = re.sub(r';.*$', '', raw).strip()

                mg = start_grass_re.match(raw)
                if mg:
                    enc_type  = 'grass'
                    rate      = int(mg.group(1))
                    slots     = []
                    blk_start = i
                    continue

                mw = start_water_re.match(raw)
                if mw:
                    enc_type  = 'water'
                    rate      = int(mw.group(1))
                    slots     = []
                    blk_start = i
                    continue

                eg = end_grass_re.match(raw)
                if eg and enc_type == 'grass':
                    self.wild_groups.append(YellowWildGroup(
                        location=location, enc_type='grass', rate=rate,
                        slots=slots, source_file=filepath,
                        line_start=blk_start, line_end=i,
                    ))
                    enc_type = None
                    continue

                ew = end_water_re.match(raw)
                if ew and enc_type == 'water':
                    self.wild_groups.append(YellowWildGroup(
                        location=location, enc_type='water', rate=rate,
                        slots=slots, source_file=filepath,
                        line_start=blk_start, line_end=i,
                    ))
                    enc_type = None
                    continue

                if enc_type:
                    ms = slot_re.match(raw)
                    if ms:
                        lvl = int(ms.group(1))
                        sp  = ms.group(2).upper()
                        if sp in YELLOW_POKEMON_CONSTANTS:
                            slots.append(YellowWildSlot(level=lvl, species_const=sp))

    # -------------------------------------------------------------------------
    # Fishing encounters
    # -------------------------------------------------------------------------

    def _parse_fishing(self):
        self.old_rod_slots  = self._parse_simple_rod(
            os.path.join(self.source_dir, YELLOW_OLD_ROD_FILE))
        self.good_rod_slots = self._parse_simple_rod(
            os.path.join(self.source_dir, YELLOW_GOOD_ROD_FILE))
        self._parse_super_rod(
            os.path.join(self.source_dir, YELLOW_SUPER_ROD_FILE))

    def _parse_simple_rod(self, filepath: str) -> list:
        """Parse old_rod or good_rod: simple 'db LEVEL, SPECIES' list."""
        slots = []
        if not os.path.isfile(filepath):
            return slots
        slot_re = re.compile(r'^\s+db\s+(\d+)\s*,\s*([A-Z][A-Z0-9_]+)', re.IGNORECASE)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return slots
        for i, raw in enumerate(lines):
            m = slot_re.match(raw)
            if not m:
                continue
            lvl = int(m.group(1))
            sp  = m.group(2).upper()
            if sp in YELLOW_POKEMON_CONSTANTS:
                slots.append(YellowFishingSlot(
                    level=lvl, species_const=sp,
                    source_file=filepath, line_index=i, full_line=raw.rstrip('\n'),
                ))
        return slots

    def _parse_super_rod(self, filepath: str):
        """
        Parse super_rod.asm: each line is
            db LOCATION, SPECIES, LEVEL, SPECIES, LEVEL, SPECIES, LEVEL, SPECIES, LEVEL
        (4 Pokémon per location, species THEN level — reversed from grass)
        """
        if not os.path.isfile(filepath):
            return
        # Matches:  db LOCATION, SP1, LV1, SP2, LV2, SP3, LV3, SP4, LV4
        # Each (?:...) group is fully closed so the repeat produces 4 separate
        # non-capturing groups (each with 2 capturing groups: species, level).
        row_re = re.compile(
            r'^\s+db\s+(\w+)\s*'
            + r'(?:,\s*([A-Z][A-Z0-9_]+)\s*,\s*(\d+))' * 4,
            re.IGNORECASE,
        )
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return
        for i, raw in enumerate(lines):
            clean = re.sub(r';.*$', '', raw)
            m = row_re.match(clean)
            if not m:
                continue
            loc = m.group(1).upper()
            for slot_idx in range(4):
                sp  = m.group(2 + slot_idx * 2).upper()
                lvl = int(m.group(3 + slot_idx * 2))
                if sp in YELLOW_POKEMON_CONSTANTS:
                    self.super_rod_slots.append(YellowSuperRodSlot(
                        location_const=loc, species_const=sp, level=lvl,
                        source_file=filepath, line_index=i, slot_index=slot_idx,
                    ))

    # -------------------------------------------------------------------------
    # Trainer parties
    # -------------------------------------------------------------------------

    def _parse_trainers(self):
        filepath = os.path.join(self.source_dir, YELLOW_TRAINER_PARTIES_FILE)
        if not os.path.isfile(filepath):
            self.log(f"  [WARN] Trainer parties file not found: {YELLOW_TRAINER_PARTIES_FILE}")
            return

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return

        # Matches trainer class section labels, e.g.  "YoungsterData:"
        class_label_re = re.compile(r'^([A-Za-z]\w*?)Data\s*:', re.IGNORECASE)
        # Format 1: db LEVEL, SPECIES..., 0
        same_level_re  = re.compile(r'^\s+db\s+(\d+)\s*,\s*((?:[A-Z][A-Z0-9_]+\s*,\s*)+)0', re.IGNORECASE)
        # Format 2: db $FF, LV1, SP1, LV2, SP2, ..., 0
        var_level_re   = re.compile(r'^\s+db\s+\$FF\s*,(.+?)0\s*$', re.IGNORECASE)
        token_re       = re.compile(r'([A-Z][A-Z0-9_]+|\d+)', re.IGNORECASE)

        current_class = 'Unknown'

        for i, raw in enumerate(lines):
            line_nc = re.sub(r';.*$', '', raw).strip()

            lm = class_label_re.match(raw)
            if lm:
                current_class = lm.group(1)
                continue

            # Format 1: all same level
            m1 = same_level_re.match(raw)
            if m1:
                level   = int(m1.group(1))
                sp_part = m1.group(2)
                species = [s.strip() for s in sp_part.split(',') if s.strip()]
                party = [
                    YellowTrainerMon(level=level, species_const=sp.upper())
                    for sp in species
                    if sp.upper() in YELLOW_POKEMON_CONSTANTS
                ]
                if party:
                    self.trainers.append(YellowTrainer(
                        class_name=current_class, party=party, same_level=True,
                        source_file=filepath, line_start=i, line_end=i,
                    ))
                continue

            # Format 2: $FF, variable levels
            m2 = var_level_re.match(line_nc)
            if m2:
                tokens = token_re.findall(m2.group(1))
                party  = []
                j = 0
                while j + 1 < len(tokens):
                    lvl_tok = tokens[j]
                    sp_tok  = tokens[j + 1].upper()
                    try:
                        lvl = int(lvl_tok)
                    except ValueError:
                        j += 1
                        continue
                    if sp_tok in YELLOW_POKEMON_CONSTANTS:
                        party.append(YellowTrainerMon(level=lvl, species_const=sp_tok))
                    j += 2
                if party:
                    self.trainers.append(YellowTrainer(
                        class_name=current_class, party=party, same_level=False,
                        source_file=filepath, line_start=i, line_end=i,
                    ))

    # -------------------------------------------------------------------------
    # Starter
    # -------------------------------------------------------------------------

    def _parse_starter(self):
        """
        Find all  'ld a, STARTER_PIKACHU'  lines in OaksLab.asm.
        STARTER_PIKACHU = PIKACHU (defined in pokemon_constants.asm).
        """
        filepath = os.path.join(self.source_dir, YELLOW_STARTER_FILE)
        if not os.path.isfile(filepath):
            self.log(f"  [WARN] Starter file not found: {YELLOW_STARTER_FILE}")
            return

        # Matches: ld a, STARTER_PIKACHU
        starter_re = re.compile(r'^\s+ld\s+a\s*,\s*(STARTER_PIKACHU)\b', re.IGNORECASE)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return

        for i, raw in enumerate(lines):
            m = starter_re.match(raw)
            if m:
                self.starters.append(YellowStarterLocation(
                    species_const='PIKACHU',
                    source_file=filepath,
                    line_index=i,
                    full_line=raw.rstrip('\n'),
                ))

        self.log(f"  Starter: found {len(self.starters)} 'ld a, STARTER_PIKACHU' line(s).")

    # -------------------------------------------------------------------------
    # In-game trades
    # -------------------------------------------------------------------------

    def _parse_trades(self):
        """
        Parse TradeMons table in data/events/trades.asm.
        Format:
            db GIVE_MON, GET_MON, DIALOG_ID, "NICKNAME@@@@@@@@@@"
        GIVE_MON = what player gives (requested_species)
        GET_MON  = what player receives (given_species)
        """
        filepath = os.path.join(self.source_dir, YELLOW_TRADES_FILE)
        if not os.path.isfile(filepath):
            self.log(f"  [WARN] Trades file not found: {YELLOW_TRADES_FILE}")
            return

        # Matches: db GIVE, GET, DIALOGSET, "NICKNAME@@@"
        trade_re = re.compile(
            r'^\s+db\s+([A-Z][A-Z0-9_]+)\s*,\s*([A-Z][A-Z0-9_]+)\s*,\s*\w+\s*,\s*"([^"]*)"',
            re.IGNORECASE,
        )
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return

        for i, raw in enumerate(lines):
            # Skip comment-only lines or lines with "unused" in comment
            comment = ''
            m_comment = re.search(r';(.*)', raw)
            if m_comment:
                comment = m_comment.group(1).lower()
            if 'unused' in comment:
                continue

            m = trade_re.match(raw)
            if not m:
                continue
            give = m.group(1).upper()
            get  = m.group(2).upper()
            nick = m.group(3).rstrip('@').rstrip()

            if give not in YELLOW_POKEMON_CONSTANTS or get not in YELLOW_POKEMON_CONSTANTS:
                continue

            self.trades.append(YellowTrade(
                give_species=give, get_species=get, nickname=nick,
                source_file=filepath, line_index=i, full_line=raw.rstrip('\n'),
            ))

        self.log(f"  Found {len(self.trades)} in-game trade(s).")
        for t in self.trades:
            self.log(f"    Give {t.give_species} → Receive {t.get_species} (nick: {t.nickname!r})")

    # -------------------------------------------------------------------------
    # Static encounters
    # -------------------------------------------------------------------------

    def _parse_static_encounters(self):
        """
        Walk all .asm source files and collect static encounter definitions.

        Yellow Legacy (pokeyellow-based) uses three distinct patterns — none of
        them are the ``battle`` / ``givepoke`` macros used by Crystal Legacy:

        Pattern 1 — ``object_event`` with trailing SPECIES, LEVEL arguments
            Located in ``data/maps/objects/*.asm``.  Used for the four
            legendary birds / Mewtwo:
                object_event X, Y, SPRITE_ZAPDOS, STAY, UP, TEXT_..., ZAPDOS, 50

        Pattern 2 — ``lb bc, SPECIES, level`` (gift Pokémon via GivePokemon)
            Located in ``scripts/*.asm``.  Used for all given-Pokémon events:
                lb bc, LAPRAS, 35   ; followed by call GivePokemon

        Pattern 3 — ``ld a, SPECIES`` immediately followed by
                     ``ld [wCurOpponent], a`` (scripted wild battle)
            Used for Snorlax (Routes 12 and 16).
        """
        from static_data import (
            YELLOW_ALL_STATIC_SPECIES,
            YELLOW_STATIC_LEGENDARY_SPECIES,
        )

        found = []
        label_re = re.compile(r'^(?P<label>[A-Za-z_]\w*)\s*::?')

        # ── Pattern 1: object_event in data/maps/objects/ ─────────────────
        # Matches: object_event X, Y, SPRITE, DIR_OR_STAY, DIR, TEXT, SPECIES, LEVEL
        # The SPECIES is the 7th comma-separated argument (groups vary by whitespace).
        # We match 6 comma-delimited tokens before the species.
        obj_event_re = re.compile(
            r'^\s+object_event\s+'
            r'\d+\s*,\s*'          # x
            r'\d+\s*,\s*'          # y
            r'\S+\s*,\s*'          # sprite
            r'\S+\s*,\s*'          # movement
            r'\S+\s*,\s*'          # direction
            r'\S+\s*,\s*'          # text pointer
            r'(?P<species>[A-Z][A-Z0-9_]+)\s*,\s*'  # SPECIES (7th arg)
            r'\d+',                # level (8th arg)
            re.IGNORECASE,
        )
        objects_dir = os.path.normpath(
            os.path.join(self.source_dir, 'data', 'maps', 'objects')
        )
        if os.path.isdir(objects_dir):
            for fname in sorted(os.listdir(objects_dir)):
                if not fname.endswith('.asm'):
                    continue
                full_path = os.path.join(objects_dir, fname)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as fh:
                        lines = fh.readlines()
                except Exception:
                    continue
                last_label = ""
                for i, raw_line in enumerate(lines):
                    lm = label_re.match(raw_line)
                    if lm:
                        last_label = lm.group('label')
                        continue
                    mm = obj_event_re.match(raw_line)
                    if mm:
                        species = mm.group('species').upper()
                        if species in YELLOW_ALL_STATIC_SPECIES:
                            found.append(YellowStaticEncounter(
                                species_const=species,
                                is_legendary=(species in YELLOW_STATIC_LEGENDARY_SPECIES),
                                source_file=full_path,
                                line_index=i,
                                full_line=raw_line.rstrip('\n'),
                                macro_type='object_event',
                                label=last_label,
                            ))

        # ── Patterns 2 & 3: scripts/ directory ────────────────────────────
        # Pattern 2: lb bc, SPECIES, level  (gift Pokémon)
        lb_bc_re = re.compile(
            r'^\s+lb\s+bc\s*,\s*(?P<species>[A-Z][A-Z0-9_]+)\s*,\s*\d+',
            re.IGNORECASE,
        )
        # Pattern 3: ld a, SPECIES  (scripted battle — only when next line is
        #            ld [wCurOpponent], a)
        ld_a_re = re.compile(
            r'^\s+ld\s+a\s*,\s*(?P<species>[A-Z][A-Z0-9_]+)',
            re.IGNORECASE,
        )
        cur_opponent_re = re.compile(
            r'^\s+ld\s+\[wCurOpponent\]\s*,\s*a',
            re.IGNORECASE,
        )

        scripts_dir = os.path.normpath(os.path.join(self.source_dir, 'scripts'))
        if os.path.isdir(scripts_dir):
            for fname in sorted(os.listdir(scripts_dir)):
                if not fname.endswith('.asm'):
                    continue
                full_path = os.path.join(scripts_dir, fname)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as fh:
                        lines = fh.readlines()
                except Exception:
                    continue
                last_label = ""
                for i, raw_line in enumerate(lines):
                    lm = label_re.match(raw_line)
                    if lm:
                        last_label = lm.group('label')
                        continue

                    # Pattern 2: lb bc, SPECIES, level
                    mm = lb_bc_re.match(raw_line)
                    if mm:
                        species = mm.group('species').upper()
                        if species in YELLOW_ALL_STATIC_SPECIES:
                            found.append(YellowStaticEncounter(
                                species_const=species,
                                is_legendary=(species in YELLOW_STATIC_LEGENDARY_SPECIES),
                                source_file=full_path,
                                line_index=i,
                                full_line=raw_line.rstrip('\n'),
                                macro_type='givepoke',
                                label=last_label,
                            ))
                        continue

                    # Pattern 3: ld a, SPECIES  →  ld [wCurOpponent], a
                    mm = ld_a_re.match(raw_line)
                    if mm:
                        species = mm.group('species').upper()
                        if species not in YELLOW_ALL_STATIC_SPECIES:
                            continue
                        # Verify that the very next non-blank line stores to wCurOpponent
                        for j in range(i + 1, min(i + 3, len(lines))):
                            nxt = lines[j]
                            if nxt.strip() == '' or nxt.strip().startswith(';'):
                                continue
                            if cur_opponent_re.match(nxt):
                                found.append(YellowStaticEncounter(
                                    species_const=species,
                                    is_legendary=(species in YELLOW_STATIC_LEGENDARY_SPECIES),
                                    source_file=full_path,
                                    line_index=i,
                                    full_line=raw_line.rstrip('\n'),
                                    macro_type='battle',
                                    label=last_label,
                                ))
                            break  # only look at the very next non-blank line

        self.static_encounters = found
        self.log(
            f"  Found {len(found)} static encounter(s) "
            f"({sum(1 for e in found if e.is_legendary)} legendary, "
            f"{sum(1 for e in found if not e.is_legendary)} standard)."
        )
        for e in found:
            rel = os.path.relpath(e.source_file, self.source_dir)
            self.log(f"    [{e.macro_type}] {e.species_const} — {rel}:{e.line_index + 1}")

    # -------------------------------------------------------------------------
    # Field items
    # -------------------------------------------------------------------------

    _VISIBLE_ITEM_RE = re.compile(
        r'^\s*(?:finditem|itemball)\s+([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    _HIDDEN_ITEM_RE = re.compile(
        r'^\s*hiddenitem\s+([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    _ITEM_MACRO_SKIP_CONSTS = {"NOPOKEMON", "NONE"}

    def _parse_field_items(self):
        """
        Scan the Yellow source tree for field item macros:
          - finditem / itemball  → visible item (Pokéball sprite on ground)
          - hiddenitem           → hidden item (Itemfinder)

        Skips key / quest-critical items (YELLOW_FIELD_ITEMS_SKIP).
        Populates self.field_items.
        """
        from item_data import YELLOW_FIELD_ITEMS_SKIP

        # Directories that commonly hold Gen 1 script / map files
        candidate_dirs = [
            os.path.join(self.source_dir, "scripts"),
            os.path.join(self.source_dir, "maps"),
            os.path.join(self.source_dir, "data", "maps"),
            os.path.join(self.source_dir, "data", "events"),
            os.path.join(self.source_dir, "engine"),
        ]

        # Files to skip (wild, trainer, trades already handled elsewhere)
        skip_files = {
            os.path.normpath(os.path.join(self.source_dir, YELLOW_WILD_MAPS_DIR)),
            os.path.normpath(os.path.join(self.source_dir, YELLOW_TRAINER_PARTIES_FILE)),
            os.path.normpath(os.path.join(self.source_dir, YELLOW_TRADES_FILE)),
        }

        asm_files = []
        for base in candidate_dirs:
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                # Skip wild-maps directory entirely
                if os.path.normpath(root).startswith(
                    os.path.normpath(os.path.join(self.source_dir, YELLOW_WILD_MAPS_DIR))
                ):
                    continue
                for fname in files:
                    if not fname.endswith(".asm"):
                        continue
                    fp = os.path.join(root, fname)
                    if os.path.normpath(fp) not in skip_files and fp not in asm_files:
                        asm_files.append(fp)

        if not asm_files:
            self.log("  [WARN] No script directories found — field item parsing skipped.")
            return

        results = []
        vis_count = 0
        hid_count = 0

        for filepath in asm_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue

            for i, raw in enumerate(lines):
                line_nc = re.sub(r';.*$', '', raw)

                mv = self._VISIBLE_ITEM_RE.match(line_nc)
                if mv:
                    item = mv.group(1).upper()
                    if item in self._ITEM_MACRO_SKIP_CONSTS or item in YELLOW_FIELD_ITEMS_SKIP:
                        continue
                    results.append(YellowFieldItem(
                        item_const=item,
                        item_type="visible",
                        source_file=filepath,
                        line_index=i,
                        full_line=raw,
                    ))
                    vis_count += 1
                    continue

                mh = self._HIDDEN_ITEM_RE.match(line_nc)
                if mh:
                    item = mh.group(1).upper()
                    if item in self._ITEM_MACRO_SKIP_CONSTS or item in YELLOW_FIELD_ITEMS_SKIP:
                        continue
                    results.append(YellowFieldItem(
                        item_const=item,
                        item_type="hidden",
                        source_file=filepath,
                        line_index=i,
                        full_line=raw,
                    ))
                    hid_count += 1

        self.field_items = results
        self.log(
            f"  Field items: {vis_count} visible, {hid_count} hidden "
            f"across {len(asm_files)} script file(s)."
        )

    # -------------------------------------------------------------------------
    # Evolutions
    # -------------------------------------------------------------------------

    def _parse_evolutions(self):
        """
        Parse evolution entries from data/pokemon/evos_moves.asm.

        Format per Pokémon:
            db EVOLVE_LEVEL, level, TARGET_SPECIES
            db EVOLVE_ITEM,  ITEM_CONST, 1, TARGET_SPECIES
            db EVOLVE_TRADE, 1, TARGET_SPECIES
            db 0  ; end of evolutions
            db level, MOVE  ; learnset (ignored here)
            db 0  ; end of learnset
        """
        filepath = os.path.join(self.source_dir, YELLOW_EVOS_MOVES_FILE)
        if not os.path.isfile(filepath):
            self.log(f"  [WARN] Evos/moves file not found: {YELLOW_EVOS_MOVES_FILE}")
            return

        # Regex to detect a species label like "BulbasaurEvosMoves:"
        label_re = re.compile(r'^([A-Za-z]\w*)EvosMoves\s*:', re.IGNORECASE)
        # Evolution line patterns
        evo_level_re = re.compile(
            r'^\s+db\s+EVOLVE_LEVEL\s*,\s*(\d+)\s*,\s*([A-Z][A-Z0-9_]+)',
            re.IGNORECASE,
        )
        evo_item_re = re.compile(
            r'^\s+db\s+EVOLVE_ITEM\s*,\s*([A-Z_][A-Z0-9_]*)\s*,\s*\d+\s*,\s*([A-Z][A-Z0-9_]+)',
            re.IGNORECASE,
        )
        evo_trade_re = re.compile(
            r'^\s+db\s+EVOLVE_TRADE\s*,\s*\d+\s*,\s*([A-Z][A-Z0-9_]+)',
            re.IGNORECASE,
        )

        # Build a label → species const mapping by parsing label names
        # e.g. "BulbasaurEvosMoves" → "BULBASAUR"
        def _label_to_const(label: str) -> str:
            upper = label.upper()
            if upper in YELLOW_POKEMON_CONSTANTS:
                return upper
            # Try stripping common suffixes
            for suffix in ('EVOS', 'MOVES', 'EVO'):
                if upper.endswith(suffix):
                    stem = upper[:-len(suffix)]
                    if stem in YELLOW_POKEMON_CONSTANTS:
                        return stem
            # Try title-casing each word
            # e.g. "Farfetchd" → "FARFETCHD"
            return upper

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return

        current_species = None
        for i, raw in enumerate(lines):
            lm = label_re.match(raw)
            if lm:
                current_species = _label_to_const(lm.group(1))
                continue

            if current_species is None:
                continue

            m_lv = evo_level_re.match(raw)
            if m_lv:
                target = m_lv.group(2).upper()
                if target in YELLOW_POKEMON_CONSTANTS:
                    self.evolutions.append(YellowEvoEntry(
                        source_species=current_species,
                        evo_type='EVOLVE_LEVEL',
                        target_species=target,
                        param=m_lv.group(1),
                        item_const='',
                        source_file=filepath,
                        line_index=i,
                        full_line=raw.rstrip('\n'),
                    ))
                continue

            m_it = evo_item_re.match(raw)
            if m_it:
                item   = m_it.group(1).upper()
                target = m_it.group(2).upper()
                if target in YELLOW_POKEMON_CONSTANTS:
                    self.evolutions.append(YellowEvoEntry(
                        source_species=current_species,
                        evo_type='EVOLVE_ITEM',
                        target_species=target,
                        param='1',
                        item_const=item,
                        source_file=filepath,
                        line_index=i,
                        full_line=raw.rstrip('\n'),
                    ))
                continue

            m_tr = evo_trade_re.match(raw)
            if m_tr:
                target = m_tr.group(1).upper()
                if target in YELLOW_POKEMON_CONSTANTS:
                    self.evolutions.append(YellowEvoEntry(
                        source_species=current_species,
                        evo_type='EVOLVE_TRADE',
                        target_species=target,
                        param='1',
                        item_const='',
                        source_file=filepath,
                        line_index=i,
                        full_line=raw.rstrip('\n'),
                    ))

        level_evos = sum(1 for e in self.evolutions if e.evo_type == 'EVOLVE_LEVEL')
        item_evos  = sum(1 for e in self.evolutions if e.evo_type == 'EVOLVE_ITEM')
        trade_evos = sum(1 for e in self.evolutions if e.evo_type == 'EVOLVE_TRADE')
        self.log(
            f"  Found {len(self.evolutions)} evolution entries "
            f"({level_evos} level, {item_evos} item, {trade_evos} trade)."
        )

    # -------------------------------------------------------------------------
    # Base stats (catch rates, TM/HM, types)
    # -------------------------------------------------------------------------

    _TMHM_RE = re.compile(r'^\s+tmhm\b(.*)', re.IGNORECASE)
    _CATCH_RE = re.compile(r'^\s+db\s+(\d+)\s*(?:;.*)?\s*$')
    _TYPE_RE  = re.compile(r'^\s+db\s+([A-Z_]+)\s*,\s*([A-Z_]+)\s*;\s*type', re.IGNORECASE)

    def _parse_base_stats(self):
        stats_dir = os.path.join(self.source_dir, YELLOW_BASE_STATS_DIR)
        if not os.path.isdir(stats_dir):
            self.log(f"  [WARN] Base stats dir not found: {YELLOW_BASE_STATS_DIR}")
            return

        catch_comment_re = re.compile(r'catch\s*rate', re.IGNORECASE)

        # Yellow Legacy filenames omit underscores for some Pokémon
        _fname_fixup = {
            'MRMIME':   'MR_MIME',
            'NIDORANF': 'NIDORAN_F',
            'NIDORANM': 'NIDORAN_M',
        }

        for fname in sorted(os.listdir(stats_dir)):
            if not fname.endswith('.asm'):
                continue
            sp = fname[:-4].upper()
            sp = _fname_fixup.get(sp, sp)   # normalise special filenames
            if sp not in YELLOW_POKEMON_CONSTANTS:
                continue

            filepath = os.path.join(stats_dir, fname)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except Exception:
                continue

            catch_line_idx = -1
            catch_value    = -1
            tmhm_line_idx  = -1
            tmhm_moves     = []
            type1          = None

            db_count = 0
            for i, raw in enumerate(lines):
                # Type line
                if type1 is None:
                    mt = self._TYPE_RE.match(raw)
                    if mt:
                        type1 = mt.group(1).upper()
                        self.pokemon_types[sp] = (mt.group(1).upper(), mt.group(2).upper())

                # Catch rate: look for "; catch rate" comment
                if catch_line_idx < 0 and catch_comment_re.search(raw):
                    mc = self._CATCH_RE.match(raw)
                    if mc:
                        catch_value    = int(mc.group(1))
                        catch_line_idx = i

                # Fallback: count plain  db N  lines (4th = catch rate in Crystal layout)
                if catch_line_idx < 0:
                    stripped = re.sub(r';.*$', '', raw).strip()
                    if re.match(r'^db\s+\d+$', stripped):
                        db_count += 1
                        if db_count == 4:
                            mc = self._CATCH_RE.match(raw)
                            if mc:
                                catch_value    = int(mc.group(1))
                                catch_line_idx = i

                # TM/HM compatibility
                if tmhm_line_idx < 0:
                    mm = self._TMHM_RE.match(raw)
                    if mm:
                        tmhm_line_idx = i
                        raw_moves = mm.group(1)
                        # Handle multi-line backslash continuation
                        j = i + 1
                        while raw.rstrip().endswith('\\') and j < len(lines):
                            raw_moves += ' ' + lines[j]
                            if not lines[j].rstrip().endswith('\\'):
                                break
                            j += 1
                        tmhm_moves = [
                            mv.strip() for mv in re.split(r'[,\\\s]+', raw_moves)
                            if mv.strip() and not mv.strip().startswith(';')
                            and mv.strip() in YELLOW_MOVE_CONSTANTS
                        ]
                        self.tmhm_compat.append(YellowTMHMCompat(
                            species_const=sp,
                            moves=tmhm_moves,
                            source_file=filepath,
                            line_index=tmhm_line_idx,
                            full_line=raw.rstrip('\n'),
                        ))

            if catch_line_idx >= 0 and catch_value >= 0:
                # Re-read the catch line for the full_line
                try:
                    full = lines[catch_line_idx].rstrip('\n')
                except Exception:
                    full = ''
                self.catch_rates.append(YellowCatchRate(
                    species_const=sp,
                    catch_rate=catch_value,
                    source_file=filepath,
                    line_index=catch_line_idx,
                    full_line=full,
                ))

        self.log(
            f"  Base stats: {len(self.catch_rates)} catch rate(s), "
            f"{len(self.tmhm_compat)} TM/HM compat(s), "
            f"{len(self.pokemon_types)} type entries."
        )
