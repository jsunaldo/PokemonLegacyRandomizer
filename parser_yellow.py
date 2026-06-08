"""
Pokemon Yellow Legacy Randomizer - ASM Source Parser

Parses Yellow Legacy source files to extract:
  - Wild Pokémon encounters (grass, water) from data/wild/maps/*.asm
  - Fishing encounters (old rod, good rod, super rod)
  - Trainer parties from data/trainers/parties.asm
  - Starter gift Pokémon (Bulbasaur, Charmander, Squirtle)
  - Static encounters (Snorlax scripted battles + gift Pokémon)
  - In-game trades from data/events/trades.asm
  - Field items (visible poké balls + hidden objects)
  - Evolution data from data/pokemon/evos_moves.asm
  - TM/HM compatibility from data/pokemon/base_stats/*.asm
"""

import os
import re
import glob
from dataclasses import dataclass, field
from typing import Optional

from constants_yellow import (
    POKEMON_CONSTANTS, POKEMON_CONST_NAMES,
    WILD_MAPS_DIR, WILD_OLD_ROD_FILE, WILD_GOOD_ROD_FILE, WILD_SUPER_ROD_FILE,
    TRAINER_PARTIES_FILE, EVOLUTION_DATA_FILE, HIDDEN_OBJECTS_FILE,
    TRADES_FILE, BASE_STATS_DIR, STARTER_FILES,
    STATIC_ENCOUNTER_FILES, INIT_PLAYER_DATA_FILE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WildSlot:
    level: int
    species_const: str

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class WildEncounterGroup:
    """One location's grass or water wild encounter block."""
    location: str
    encounter_type: str   # 'grass' | 'water'
    slots: list           # list of WildSlot
    rate: int             # encounter rate
    source_file: str
    line_start: int
    line_end: int


@dataclass
class TrainerPokemon:
    level: int
    species_const: str

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class Trainer:
    name: str
    fmt: str            # 'A' = same level  |  'B' = individual levels ($FF sentinel)
    party: list         # list of TrainerPokemon
    source_file: str
    line_start: int     # line index of first data line
    line_end: int       # line index of terminating 0


@dataclass
class StarterLocation:
    """One starter gift event location."""
    species_const: str
    level: int
    source_file: str
    lb_line: int        # line index of  lb bc, SPECIES, LEVEL
    ld_lines: list      # line indices of  ld a, SPECIES   (for name/cry calls)


@dataclass
class InGameTrade:
    """One in-game trade from data/events/trades.asm."""
    source_file: str
    give_species: str   # species player RECEIVES
    get_species: str    # species player GIVES
    dialog_id: str
    nickname: str
    line_index: int     # 0-based index in source file
    full_line: str


@dataclass
class EvolutionEntry:
    """One evolution line inside a PokémonEvosMoves block."""
    owner_const: str    # species that owns this evo (e.g. "IVYSAUR" evolves FROM "BULBASAUR")
    evo_type: str       # EVOLVE_LEVEL | EVOLVE_ITEM | EVOLVE_TRADE
    param: str          # level number (str) or item constant
    min_level: str      # only used by EVOLVE_ITEM / EVOLVE_TRADE ("1")
    target_const: str   # species this evolves INTO
    source_file: str
    line_index: int
    full_line: str


@dataclass
class StaticEncounter:
    """A static wild battle or scripted gift Pokémon."""
    species_const: str
    encounter_type: str  # 'battle' | 'gift'
    source_file: str
    # For 'battle' (ld a, SPECIES → ld [wCurOpponent], a):
    ld_a_line: int       # line index of  ld a, SPECIES
    cur_opp_line: int    # line index of  ld [wCurOpponent], a  (-1 for gifts)
    # For 'gift' (lb bc, SPECIES, LEVEL → call GivePokemon):
    lb_line: int         # line index of  lb bc, SPECIES, LEVEL  (-1 for battles)
    level: int           # 0 for battle type
    # Optional companion `ld a, SPECIES` line that feeds the name display
    # (wd11e) shortly before the gift, so the shown name matches the given mon.
    name_line: int = -1


@dataclass
class FieldItem:
    """A visible (poké ball) or hidden field item."""
    item_const: str
    item_type: str      # 'visible' | 'hidden'
    source_file: str
    line_index: int
    full_line: str


@dataclass
class FishSlot:
    """One old-rod or good-rod slot (global, not per-location)."""
    level: int
    species_const: str

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class SuperRodSlot:
    """One species entry within a super-rod location row."""
    species_const: str
    level: int

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class SuperRodEntry:
    """One location row in super_rod.asm."""
    map_const: str
    slots: list         # list of SuperRodSlot (4 per row)
    source_file: str
    line_index: int
    full_line: str


@dataclass
class TMHMCompatEntry:
    """TM/HM compatibility flags for one species."""
    species_const: str
    compat_bytes: list  # raw byte values (int) from tmhm macro (unused for Yellow)
    source_file: str
    line_index: int
    full_line: str
    move_names: list = None    # the MOVE-name args of the tmhm macro
    end_index: int = -1        # last line index of the (possibly multi-line) tmhm block


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

class YellowLegacyParser:
    """Parse a Pokemon Yellow Legacy source tree."""

    def __init__(self, source_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.log = log_fn or print

        # Parsed results
        self.wild_groups: list[WildEncounterGroup] = []
        self.trainers: list[Trainer] = []
        self.old_rod_slots: list[FishSlot] = []
        self.good_rod_slots: list[FishSlot] = []
        self.super_rod_slots: list[SuperRodEntry] = []
        self.trades: list[InGameTrade] = []
        self.starters: list[StarterLocation] = []
        self.static_encounters: list[StaticEncounter] = []
        self.field_items: list[FieldItem] = []
        self.evolutions: list[EvolutionEntry] = []
        self.tmhm_compat: list[TMHMCompatEntry] = []
        self.init_player_data_src: str = ""

    # ── helpers ───────────────────────────────────────────────────────────────

    def _path(self, *parts) -> str:
        return os.path.join(self.source_dir, *parts)

    def _read(self, rel_path: str) -> list[str]:
        """Read a file relative to source_dir; return list of lines (with newlines)."""
        full = self._path(rel_path)
        if not os.path.isfile(full):
            return []
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            return fh.readlines()

    def _strip(self, line: str) -> str:
        """Strip comment and whitespace from a line."""
        return line.split(";")[0].strip()

    # ── Wild encounters ───────────────────────────────────────────────────────

    def _parse_wild_maps(self):
        maps_dir = self._path(WILD_MAPS_DIR)
        if not os.path.isdir(maps_dir):
            self.log(f"  [WARN] Wild maps directory not found: {maps_dir}")
            return

        for asm_file in sorted(glob.glob(os.path.join(maps_dir, "*.asm"))):
            rel = os.path.relpath(asm_file, self.source_dir)
            lines = []
            with open(asm_file, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            self._parse_one_wild_file(lines, rel)

    def _parse_one_wild_file(self, lines: list[str], rel_path: str):
        """
        Parse one wild encounter file. Format:
            LocationWildMons:
                def_grass_wildmons RATE
                db LEVEL, SPECIES
                ... (10 entries)
                end_grass_wildmons
                def_water_wildmons RATE
                db LEVEL, SPECIES
                ... (or 0 entries if rate=0)
                end_water_wildmons
        """
        location = os.path.splitext(os.path.basename(rel_path))[0]  # e.g. "Route1"
        i = 0
        n = len(lines)

        while i < n:
            stripped = self._strip(lines[i])

            # Grass block
            m = re.match(r'def_grass_wildmons\s+(\d+)', stripped)
            if m:
                rate = int(m.group(1))
                start = i
                i += 1
                slots = []
                while i < n:
                    s = self._strip(lines[i])
                    if s.startswith("end_grass_wildmons"):
                        break
                    sm = re.match(r'db\s+(\d+)\s*,\s*(\w+)', s)
                    if sm:
                        level = int(sm.group(1))
                        sp = sm.group(2)
                        if sp in POKEMON_CONSTANTS:
                            slots.append(WildSlot(level, sp))
                    i += 1
                end = i
                if rate > 0 and slots:
                    self.wild_groups.append(WildEncounterGroup(
                        location=location, encounter_type='grass',
                        slots=slots, rate=rate,
                        source_file=rel_path, line_start=start, line_end=end,
                    ))
                i += 1
                continue

            # Water block
            m = re.match(r'def_water_wildmons\s+(\d+)', stripped)
            if m:
                rate = int(m.group(1))
                start = i
                i += 1
                slots = []
                while i < n:
                    s = self._strip(lines[i])
                    if s.startswith("end_water_wildmons"):
                        break
                    sm = re.match(r'db\s+(\d+)\s*,\s*(\w+)', s)
                    if sm:
                        level = int(sm.group(1))
                        sp = sm.group(2)
                        if sp in POKEMON_CONSTANTS:
                            slots.append(WildSlot(level, sp))
                    i += 1
                end = i
                if rate > 0 and slots:
                    self.wild_groups.append(WildEncounterGroup(
                        location=location, encounter_type='water',
                        slots=slots, rate=rate,
                        source_file=rel_path, line_start=start, line_end=end,
                    ))
                i += 1
                continue

            i += 1

    # ── Fishing ───────────────────────────────────────────────────────────────

    def _parse_fishing(self):
        """Parse old rod and good rod (global 2-entry tables) + super rod."""
        for rod_file, attr in [
            (WILD_OLD_ROD_FILE,  "old_rod_slots"),
            (WILD_GOOD_ROD_FILE, "good_rod_slots"),
        ]:
            lines = self._read(rod_file)
            slots = []
            for line in lines:
                s = self._strip(line)
                m = re.match(r'db\s+(\d+)\s*,\s*(\w+)', s)
                if m:
                    level = int(m.group(1))
                    sp = m.group(2)
                    if sp in POKEMON_CONSTANTS:
                        slots.append(FishSlot(level, sp))
            setattr(self, attr, slots)

        # Super rod: db MAP_CONST, SP1,LV1, SP2,LV2, SP3,LV3, SP4,LV4
        lines = self._read(WILD_SUPER_ROD_FILE)
        rel = WILD_SUPER_ROD_FILE
        for i, line in enumerate(lines):
            s = self._strip(line)
            m = re.match(
                r'db\s+(\w+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,'
                r'\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)', s
            )
            if m:
                map_const = m.group(1)
                slots = []
                for j in range(4):
                    sp  = m.group(2 + j * 2)
                    lv  = int(m.group(3 + j * 2))
                    if sp in POKEMON_CONSTANTS:
                        slots.append(SuperRodSlot(sp, lv))
                if slots:
                    self.super_rod_slots.append(SuperRodEntry(
                        map_const=map_const, slots=slots,
                        source_file=rel, line_index=i, full_line=line,
                    ))

    # ── Trainers ──────────────────────────────────────────────────────────────

    def _parse_trainers(self):
        """
        Parse data/trainers/parties.asm.

        Format A (same level):
            db LEVEL, SP1, SP2, ..., 0

        Format B (individual levels, sentinel $FF):
            db $FF, LV1, SP1, LV2, SP2, ..., 0
        """
        lines = self._read(TRAINER_PARTIES_FILE)
        rel   = TRAINER_PARTIES_FILE
        n     = len(lines)

        # Find the start of trainer data (skip pointer table at the top)
        data_start = 0
        for i, line in enumerate(lines):
            s = self._strip(line)
            if s and not s.startswith("dw ") and not s.startswith("TrainerDataPointers") \
                    and not s.startswith("table_width") and not s.startswith(";"):
                data_start = i
                break

        i = data_start
        current_name = "Unknown"
        while i < n:
            raw = lines[i]
            stripped = self._strip(raw)

            # Label line  (e.g.  BugCatcherParty1:)
            if stripped.endswith(':') and not stripped.startswith('db'):
                current_name = stripped.rstrip(':')
                i += 1
                continue

            # Format B: starts with $FF
            if re.match(r'db\s+\$FF\b', stripped, re.I):
                start = i
                tokens = []
                # Gather all db tokens until we hit 0 terminator
                j = i
                while j < n:
                    s2 = self._strip(lines[j])
                    if not s2.startswith('db'):
                        break
                    toks = [t.strip() for t in s2[2:].split(',')]
                    tokens.extend(toks)
                    if '0' in toks:
                        i = j
                        break
                    j += 1
                # Parse: $FF, LV, SP, LV, SP, ..., 0
                # tokens[0] == '$FF'
                party = []
                k = 1
                while k + 1 < len(tokens):
                    lv_s = tokens[k]
                    sp_s = tokens[k + 1]
                    if sp_s == '0':
                        break
                    try:
                        lv = int(lv_s, 0)
                    except ValueError:
                        k += 2
                        continue
                    if sp_s in POKEMON_CONSTANTS:
                        party.append(TrainerPokemon(lv, sp_s))
                    k += 2
                if party:
                    self.trainers.append(Trainer(
                        name=current_name, fmt='B', party=party,
                        source_file=rel, line_start=start, line_end=i,
                    ))
                i += 1
                continue

            # Format A: db LEVEL, SP1, SP2, ..., 0
            if re.match(r'db\s+\d+', stripped):
                start = i
                toks_raw = stripped[2:].strip()
                toks = [t.strip() for t in toks_raw.split(',')]
                try:
                    level = int(toks[0])
                except (ValueError, IndexError):
                    i += 1
                    continue
                party = []
                for sp_s in toks[1:]:
                    if sp_s == '0':
                        break
                    if sp_s in POKEMON_CONSTANTS:
                        party.append(TrainerPokemon(level, sp_s))
                if party:
                    self.trainers.append(Trainer(
                        name=current_name, fmt='A', party=party,
                        source_file=rel, line_start=start, line_end=start,
                    ))
                i += 1
                continue

            i += 1

    # ── Starters ──────────────────────────────────────────────────────────────

    def _parse_starters(self) -> bool:
        """
        Parse the three gift starter files.
        Pattern: lb bc, SPECIES, LEVEL  (gives the Pokémon)
                 ld a, SPECIES          (used for GetMonName / PlayCry — multiple occurrences)
        Returns True if at least one starter was found.
        """
        found = False
        for default_const, rel_path in STARTER_FILES.items():
            lines = self._read(rel_path)
            if not lines:
                self.log(f"  [WARN] Starter file not found: {rel_path}")
                continue

            lb_line_idx = -1
            species = default_const
            level = 10

            # Find lb bc, SPECIES, LEVEL
            for i, line in enumerate(lines):
                s = self._strip(line)
                m = re.match(r'lb\s+bc\s*,\s*(\w+)\s*,\s*(\d+)', s)
                if m and m.group(1) in POKEMON_CONSTANTS:
                    species  = m.group(1)
                    level    = int(m.group(2))
                    lb_line_idx = i
                    break

            if lb_line_idx == -1:
                self.log(f"  [WARN] Could not find lb bc starter pattern in {rel_path}")
                continue

            # Find all ld a, SPECIES lines in this file
            ld_lines = []
            for i, line in enumerate(lines):
                s = self._strip(line)
                m = re.match(r'ld\s+a\s*,\s*(\w+)$', s)
                if m and m.group(1) == species:
                    ld_lines.append(i)

            self.starters.append(StarterLocation(
                species_const=species, level=level,
                source_file=rel_path,
                lb_line=lb_line_idx,
                ld_lines=ld_lines,
            ))
            found = True

        return found

    # ── Static encounters ─────────────────────────────────────────────────────

    def _parse_static_encounters(self):
        """
        Parse static wild battles (Snorlax: ld a, SPECIES → ld [wCurOpponent], a)
        and gift Pokémon (lb bc, SPECIES, LEVEL → call GivePokemon) from
        the known static encounter script files.

        The three starter-style gift files (Charmander/Bulbasaur/Squirtle) are
        now included in STATIC_ENCOUNTER_FILES, so they are randomized as part
        of static encounters.
        """
        for rel_path in sorted(STATIC_ENCOUNTER_FILES):
            lines = self._read(rel_path)
            if not lines:
                continue

            n = len(lines)

            i = 0
            while i < n:
                s = self._strip(lines[i])

                # Battle pattern: ld a, SPECIES
                m_ld = re.match(r'ld\s+a\s*,\s*(\w+)$', s)
                if m_ld and m_ld.group(1) in POKEMON_CONSTANTS:
                    sp = m_ld.group(1)
                    # Check next non-blank line for ld [wCurOpponent], a
                    j = i + 1
                    while j < n and not self._strip(lines[j]):
                        j += 1
                    if j < n:
                        sj = self._strip(lines[j])
                        if 'wCurOpponent' in sj and '[' in sj:
                            self.static_encounters.append(StaticEncounter(
                                species_const=sp, encounter_type='battle',
                                source_file=rel_path,
                                ld_a_line=i, cur_opp_line=j,
                                lb_line=-1, level=0,
                            ))
                            i = j + 1
                            continue

                # Gift pattern: lb bc, SPECIES, LEVEL followed (within a few lines) by call GivePokemon
                m_lb = re.match(r'lb\s+bc\s*,\s*(\w+)\s*,\s*(\d+)', s)
                if m_lb and m_lb.group(1) in POKEMON_CONSTANTS:
                    sp  = m_lb.group(1)
                    lv  = int(m_lb.group(2))
                    # Look ahead for call GivePokemon (within 5 lines)
                    for j in range(i + 1, min(i + 6, n)):
                        sj = self._strip(lines[j])
                        if re.match(r'call\s+GivePokemon', sj):
                            # Look BACK (within 6 lines) for a companion
                            # `ld a, SAME_SPECIES` that feeds the name display
                            # (so the shown name matches the randomized mon).
                            name_line = -1
                            for k in range(i - 1, max(i - 7, -1), -1):
                                sk = self._strip(lines[k])
                                if re.match(r'ld\s+a\s*,\s*' + re.escape(sp) + r'$', sk):
                                    name_line = k
                                    break
                            self.static_encounters.append(StaticEncounter(
                                species_const=sp, encounter_type='gift',
                                source_file=rel_path,
                                ld_a_line=-1, cur_opp_line=-1,
                                lb_line=i, level=lv, name_line=name_line,
                            ))
                            break

                i += 1

    # ── In-game trades ────────────────────────────────────────────────────────

    def _parse_trades(self):
        """
        Parse data/events/trades.asm.
        Format: db GIVE_SPECIES, GET_SPECIES, DIALOG_ID, "NICKNAME@@@@@@"
        """
        lines = self._read(TRADES_FILE)
        rel   = TRADES_FILE

        for i, line in enumerate(lines):
            s = self._strip(line)
            # Match: db SPECIES, SPECIES, DIALOG, "NICK@@"
            m = re.match(
                r'db\s+(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*"([^"]*)"',
                s
            )
            if m:
                give = m.group(1)
                get  = m.group(2)
                dlg  = m.group(3)
                nick = m.group(4).rstrip('@')
                if give in POKEMON_CONSTANTS and get in POKEMON_CONSTANTS:
                    self.trades.append(InGameTrade(
                        source_file=rel,
                        give_species=give, get_species=get,
                        dialog_id=dlg, nickname=nick,
                        line_index=i, full_line=line,
                    ))

    # ── Field items ───────────────────────────────────────────────────────────

    def _parse_field_items(self):
        """
        Parse visible items (object_event … SPRITE_POKE_BALL … ITEM_CONST)
        from data/maps/objects/*.asm and hidden items (hidden_object … HiddenItems)
        from data/events/hidden_objects.asm.
        """
        # Visible: last token of  object_event X, Y, SPRITE_POKE_BALL, STAY, NONE, TEXT_ID, ITEM_CONST
        objects_dir = self._path("data", "maps", "objects")
        if os.path.isdir(objects_dir):
            for asm_file in sorted(glob.glob(os.path.join(objects_dir, "*.asm"))):
                rel = os.path.relpath(asm_file, self.source_dir)
                with open(asm_file, "r", encoding="utf-8", errors="replace") as fh:
                    obj_lines = fh.readlines()
                for i, line in enumerate(obj_lines):
                    s = self._strip(line)
                    if 'SPRITE_POKE_BALL' in s and s.startswith('object_event'):
                        parts = [p.strip() for p in s.split(',')]
                        if len(parts) >= 7:
                            item_const = parts[-1]
                            # Strip any trailing comment
                            item_const = item_const.split(';')[0].strip()
                            if item_const and not item_const.startswith('0'):
                                self.field_items.append(FieldItem(
                                    item_const=item_const, item_type='visible',
                                    source_file=rel, line_index=i, full_line=line,
                                ))

        # Hidden: hidden_object X, Y, ITEM_CONST, HiddenItems
        hidden_lines = self._read(HIDDEN_OBJECTS_FILE)
        rel_hidden   = HIDDEN_OBJECTS_FILE
        for i, line in enumerate(hidden_lines):
            s = self._strip(line)
            m = re.match(r'hidden_object\s+\d+\s*,\s*\d+\s*,\s*(\w+)\s*,\s*(\w+)', s)
            if m:
                item_const = m.group(1)
                routine    = m.group(2)
                if routine == 'HiddenItems':
                    self.field_items.append(FieldItem(
                        item_const=item_const, item_type='hidden',
                        source_file=rel_hidden, line_index=i, full_line=line,
                    ))

    # ── Evolutions ────────────────────────────────────────────────────────────

    def _parse_evolutions(self):
        """
        Parse data/pokemon/evos_moves.asm.

        Yellow evolution formats:
          db EVOLVE_LEVEL, level, SPECIES           (3 fields)
          db EVOLVE_ITEM, item_const, min_lvl, SPECIES  (4 fields)
          db EVOLVE_TRADE, min_lvl, SPECIES          (3 fields — unused in Yellow Legacy)
          db 0  ; no more evolutions
        """
        lines = self._read(EVOLUTION_DATA_FILE)
        rel   = EVOLUTION_DATA_FILE
        n     = len(lines)

        current_owner = None
        i = 0

        while i < n:
            raw = lines[i]
            s   = self._strip(raw)

            # Label like  BulbasaurEvosMoves:
            lm = re.match(r'(\w+)EvosMoves:', s)
            if lm:
                label_prefix = lm.group(1)
                # Convert label prefix to const name
                current_owner = self._label_to_const(label_prefix)
                i += 1
                continue

            # Evolution lines
            if current_owner and s.startswith('db '):
                tokens = [t.strip() for t in s[3:].split(',')]
                if not tokens:
                    i += 1
                    continue

                evo_type = tokens[0]

                if evo_type in ('EVOLVE_LEVEL',) and len(tokens) >= 3:
                    param  = tokens[1]  # level
                    target = tokens[2]
                    if target in POKEMON_CONSTANTS:
                        self.evolutions.append(EvolutionEntry(
                            owner_const=current_owner, evo_type=evo_type,
                            param=param, min_level='', target_const=target,
                            source_file=rel, line_index=i, full_line=raw,
                        ))

                elif evo_type in ('EVOLVE_ITEM',) and len(tokens) >= 4:
                    param     = tokens[1]  # item constant
                    min_level = tokens[2]  # always '1' in Yellow Legacy
                    target    = tokens[3]
                    if target in POKEMON_CONSTANTS:
                        self.evolutions.append(EvolutionEntry(
                            owner_const=current_owner, evo_type=evo_type,
                            param=param, min_level=min_level, target_const=target,
                            source_file=rel, line_index=i, full_line=raw,
                        ))

                elif evo_type in ('EVOLVE_TRADE',) and len(tokens) >= 3:
                    min_level = tokens[1]
                    target    = tokens[2]
                    if target in POKEMON_CONSTANTS:
                        self.evolutions.append(EvolutionEntry(
                            owner_const=current_owner, evo_type=evo_type,
                            param='', min_level=min_level, target_const=target,
                            source_file=rel, line_index=i, full_line=raw,
                        ))

                elif tokens[0] == '0':
                    # End of evolutions block; learnset follows
                    current_owner = None

            i += 1

    def _label_to_const(self, label_prefix: str) -> str:
        """
        Convert an EvosMoves label prefix to the ASM constant name.
        e.g. 'Bulbasaur' → 'BULBASAUR',  'NidoranF' → 'NIDORAN_F',
             'MrMime' → 'MR_MIME',  'Farfetchd' → 'FARFETCHD'
        """
        upper = label_prefix.upper()
        # Direct match first
        if upper in POKEMON_CONSTANTS:
            return upper
        # Try common transformations
        for candidate in [
            upper,
            upper.replace('NIDORANF', 'NIDORAN_F'),
            upper.replace('NIDORANM', 'NIDORAN_M'),
            upper.replace('MRMIME',   'MR_MIME'),
        ]:
            if candidate in POKEMON_CONSTANTS:
                return candidate
        return upper  # fallback (may not match any const, handled gracefully)

    # ── TM/HM compatibility ───────────────────────────────────────────────────

    def _parse_tmhm(self):
        """
        Parse  tmhm <bytes>  lines from data/pokemon/base_stats/*.asm
        """
        bstats_dir = self._path(BASE_STATS_DIR)
        if not os.path.isdir(bstats_dir):
            self.log(f"  [WARN] Base stats dir not found: {bstats_dir}")
            return

        for asm_file in sorted(glob.glob(os.path.join(bstats_dir, "*.asm"))):
            rel = os.path.relpath(asm_file, self.source_dir)
            # Derive species const from filename (e.g. bulbasaur.asm → BULBASAUR)
            base = os.path.splitext(os.path.basename(asm_file))[0].upper()
            species = base
            # Handle special names
            if base == 'NIDORAN_F':
                species = 'NIDORAN_F'
            elif base == 'NIDORAN_M':
                species = 'NIDORAN_M'
            elif base == 'MR_MIME':
                species = 'MR_MIME'
            elif base == 'FARFETCH_D':
                species = 'FARFETCHD'
            elif base == 'FARFETCHD':
                species = 'FARFETCHD'

            with open(asm_file, "r", encoding="utf-8", errors="replace") as fh:
                file_lines = fh.readlines()

            for i, line in enumerate(file_lines):
                s = self._strip(line)
                m = re.match(r'tmhm\s+(.*)', s)
                if m:
                    # The tmhm macro takes MOVE NAMES (e.g. SWORDS_DANCE),
                    # NOT raw bytes, and the arg list may span several lines
                    # joined by a trailing backslash.
                    arg_text = m.group(1)
                    end_i = i
                    while arg_text.rstrip().endswith('\\'):
                        arg_text = arg_text.rstrip()[:-1]  # drop the backslash
                        end_i += 1
                        if end_i < len(file_lines):
                            arg_text += ' ' + self._strip(file_lines[end_i])
                        else:
                            break
                    # Strip any trailing comment
                    arg_text = arg_text.split(';')[0]
                    names = [a.strip() for a in arg_text.split(',') if a.strip()]
                    if species in POKEMON_CONSTANTS:
                        self.tmhm_compat.append(TMHMCompatEntry(
                            species_const=species, compat_bytes=[],
                            source_file=rel, line_index=i, full_line=line,
                            move_names=names, end_index=end_i,
                        ))
                    break  # only one tmhm line per file

    # ── Top-level ─────────────────────────────────────────────────────────────

    def parse_all(self) -> bool:
        """
        Parse all source data.  Returns True if starters were found.
        """
        self.log("  Parsing wild encounters...")
        self._parse_wild_maps()
        self.log(f"    → {len(self.wild_groups)} wild groups")

        self.log("  Parsing fishing...")
        self._parse_fishing()
        self.log(f"    → {len(self.old_rod_slots)} old-rod, "
                 f"{len(self.good_rod_slots)} good-rod, "
                 f"{len(self.super_rod_slots)} super-rod entries")

        self.log("  Parsing trainers...")
        self._parse_trainers()
        self.log(f"    → {len(self.trainers)} trainer parties")

        self.log("  Parsing starters...")
        starters_found = self._parse_starters()
        self.log(f"    → {len(self.starters)} starter locations found")

        self.log("  Parsing static encounters...")
        self._parse_static_encounters()
        self.log(f"    → {len(self.static_encounters)} static encounters")

        self.log("  Parsing in-game trades...")
        self._parse_trades()
        self.log(f"    → {len(self.trades)} trades")

        self.log("  Parsing field items...")
        self._parse_field_items()
        self.log(f"    → {len(self.field_items)} field items")

        self.log("  Parsing evolutions...")
        self._parse_evolutions()
        self.log(f"    → {len(self.evolutions)} evolution entries")

        self.log("  Parsing TM/HM compatibility...")
        self._parse_tmhm()
        self.log(f"    → {len(self.tmhm_compat)} species with tmhm data")

        # Record init_player_data path for starting items / PC Pokémon
        self.init_player_data_src = self._path(INIT_PLAYER_DATA_FILE)

        return starters_found
