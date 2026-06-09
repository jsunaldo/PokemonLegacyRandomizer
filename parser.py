"""
Pokemon Crystal Legacy Randomizer - ASM Source Parser

Parses Crystal Legacy source files to extract:
  - Wild Pokemon encounters (grass, water, fishing, headbutt)
  - Trainer parties (with Crystal Legacy extended TRAINERTYPE flags)
  - Starter Pokemon definitions
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional
from constants import (
    POKEMON_CONSTANTS, POKEMON_CONST_NAMES, TRAINERTYPE_NAMES,
    TRAINERTYPE_MOVES, TRAINERTYPE_ITEM, TRAINERTYPE_ITEM_MOVES,
    TRAINERTYPE_NICKNAME, TRAINERTYPE_DVS, TRAINERTYPE_STAT_EXP,
    TRAINERTYPE_VARIABLE, TRAINERTYPE_HAPPINESS,
    WILD_ENCOUNTER_FILES, TRAINER_PARTIES_FILE,
    STARTER_FILE_CANDIDATES, STARTER_CONSTANTS,
    EVOLUTION_DATA_FILE_CANDIDATES,
    POKEMON_PRIMARY_TYPE, POKEMON_DISPLAY_NAME,
)


@dataclass
class WildSlot:
    level: int
    species_const: str  # e.g. "RATTATA"

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class WildEncounterGroup:
    """Grass or water encounter group (one location, all time periods)."""
    location: str
    encounter_type: str   # 'grass', 'water', 'fish', 'headbutt', 'bug_contest'
    slots: list           # list of WildSlot (morning + day + night concatenated)
    rates: list           # [morning_rate, day_rate, night_rate]
    source_file: str
    line_start: int       # line index in source file where block begins
    line_end: int         # line index where block ends
    slots_per_period: int = 1   # slots in each time period; len(slots)//len(rates)


@dataclass
class TrainerPokemon:
    level: int
    species_const: str
    moves: list = field(default_factory=list)    # 4 move constants or []
    item: Optional[str] = None
    nickname: Optional[str] = None
    dvs: Optional[str] = None
    stat_exp: Optional[str] = None

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class Trainer:
    name: str
    trainer_type_const: str    # e.g. "TRAINERTYPE_MOVES"
    trainer_type_value: int
    party: list                # list of TrainerPokemon
    trainer_class: str
    source_file: str
    line_start: int
    line_end: int              # line of the "db -1" terminator


@dataclass
class StarterLocation:
    """Describes where a starter Pokemon is defined in the ASM source."""
    species_const: str
    source_file: str
    line_index: int            # 0-based line index
    full_line: str             # original line text


@dataclass
class InGameTrade:
    """
    One in-game trade record found in the ASM source.

    Crystal trade data blocks typically follow this layout:
        db GIVEN_SPECIES      ; Pokemon the NPC gives (player receives)
        db REQUESTED_SPECIES  ; Pokemon the NPC wants (player gives)
        dw DVS_WORD           ; Gen 2 DV values (Attack|Def, Spd|Spc nibbles)
        db "NICKNAME@"        ; Nickname of the received Pokemon
        db "OT_NAME@"         ; OT of the received Pokemon
        db ITEM_CONST         ; Held item (NO_ITEM if none)

    Line indices of -1 mean that field was not found in the source.
    """
    source_file: str

    # Core species fields (always present)
    given_species: str      # species player receives
    given_line: int
    given_full_line: str

    requested_species: str  # species player gives
    requested_line: int
    requested_full_line: str

    # Optional fields (line = -1 if not found)
    dvs_raw: str = "0"
    dvs_line: int = -1
    dvs_full_line: str = ""

    nickname: str = ""
    nickname_line: int = -1
    nickname_full_line: str = ""

    ot_name: str = ""
    ot_line: int = -1
    ot_full_line: str = ""

    item: str = "NO_ITEM"
    item_line: int = -1
    item_full_line: str = ""


@dataclass
class EvolutionEntry:
    """
    One ``evolve`` macro line in the evolution/attacks data file.

    Crystal / pokecrystal format::

        evolve TYPE, TARGET_SPECIES, PARAM

    where TYPE is one of: LEVEL, ITEM, TRADE, TRADE_ITEM,
    HAPPINESS, HAPPINESS_DAY, HAPPINESS_NIGHT, STAT
    (with or without an ``EVOLVE_`` prefix depending on the source version).
    PARAM is a level number, item constant, or ``0`` for type-only evolutions.
    """
    evo_type: str    # e.g. "TRADE", "EVOLVE_TRADE", "HAPPINESS_DAY"
    target: str      # species being evolved to, e.g. "ALAKAZAM"
    param: str       # level, item const, or "0"
    source_file: str
    line_index: int
    full_line: str


@dataclass
class StarterItemLocation:
    """
    A givepoke macro call in an ASM script that gives a starter Pokémon
    with a held item.  Format: ``givepoke SPECIES, level, ITEM``
    """
    species_const: str   # starter species in this call (e.g. "CYNDAQUIL")
    item_const: str      # current item constant (e.g. "NO_ITEM")
    source_file: str     # absolute path to the .asm file
    line_index: int      # 0-based line index
    full_line: str       # original line text


@dataclass
class TMHMCompatEntry:
    """
    The ``tmhm`` macro line from a Pokémon's base stats file.

    Crystal Legacy format (one line per Pokémon at the end of its base stats):
        tmhm TM_05, TM_06, HM_01, HM_04, ...

    The ``moves`` list contains each TM/HM constant exactly as it appears in
    the source, preserving case so the writer can reproduce it faithfully.
    """
    species_const: str   # e.g. "BULBASAUR"
    source_file: str
    line_index: int
    full_line: str       # original line text (without trailing newline)
    moves: list          # list of TM/HM constant strings


@dataclass
class FishSlot:
    """
    A single randomizable species slot in Crystal Legacy's data/wild/fish.asm.

    Crystal Legacy uses a centralized fish encounter file with named sublists
    (e.g. .Shore_Old, .Shore_Good, .Shore_Super) and a separate TimeFishGroups
    table for time-of-day variants.  Neither format matches the normal
    def_fishwildmons … end_fishwildmons macro the standard parser expects.

    Two source line layouts:
      Sublist entry:     db <chance_expr>, SPECIES, LEVEL
      TimeFishGroups:    db DAY_SPECIES, DAY_LEVEL, NIGHT_SPECIES, NIGHT_LEVEL ; N

    Each FishSlot represents ONE species position in ONE source line.
    Multiple FishSlots may share the same line_index (TimeFishGroups rows
    contribute two slots: col=0 for day, col=1 for night).
    """
    species_const: str   # e.g. "MAGIKARP"
    source_file: str
    line_index: int      # 0-based line number in source file
    col: int             # 0 = first/only species on line; 1 = second (night) species
    full_line: str       # original line text (for context)

    @property
    def species_id(self):
        return POKEMON_CONSTANTS.get(self.species_const, 0)


@dataclass
class WildHeldItemEntry:
    """
    One wild Pokémon held-item entry from the held items data file.

    Crystal format (one per Pokémon):
        db SPECIES, COMMON_ITEM, RARE_ITEM

    COMMON_ITEM is held 50 % of the time; RARE_ITEM is held 5 % of the time.
    They are often the same constant.
    """
    species_const: str   # e.g. "CHANSEY"
    common_item: str     # e.g. "LUCKY_EGG"
    rare_item: str       # e.g. "LUCKY_EGG"
    source_file: str
    line_index: int
    full_line: str


@dataclass
class StaticEncounter:
    """
    A Pokemon encountered at a fixed overworld location.
    Not a wild slot, not a trainer party member.
    Examples: Red Gyarados, Sudowoodo, Lugia, Ho-Oh, roaming legendaries,
              gift Pokemon (Eevee, Dratini, fossils).
    """
    species_const: str   # e.g. "LUGIA"
    is_legendary: bool
    source_file: str     # absolute path to the .asm file
    line_index: int      # 0-based line index
    full_line: str       # original line text (without trailing newline)
    macro_type: str      # "battle", "givepoke", or "db_roam"
    label: str = ""      # nearest preceding label for context / deduplication


@dataclass
class FieldItemEntry:
    """
    An item placed in the overworld — either a visible Pokéball sprite
    (finditem / itemball macro) or a hidden item (hiddenitem macro).

    Crystal Legacy ASM patterns captured:
        finditem  ITEM_CONST       ; visible item
        itemball  ITEM_CONST       ; alternate macro for same
        hiddenitem ITEM_CONST, x, y, ... ; hidden item
    """
    item_const: str      # e.g. "RARE_CANDY"
    item_type: str       # "visible" or "hidden"
    source_file: str     # absolute path to the .asm file
    line_index: int      # 0-based line index
    full_line: str       # original line text (with newline preserved)


@dataclass
class StarterDialogueLine:
    """
    A ``pokepic``, ``cry``, or ``getmonname`` macro line in the starter script.
    These reference the starter species directly and must be updated when
    starters are randomized (e.g. ElmsLab.asm CyndaquilPokeBallScript block).
    """
    macro: str          # "pokepic", "cry", or "getmonname"
    species_const: str  # current species (e.g. "CYNDAQUIL")
    source_file: str    # absolute path
    line_index: int     # 0-based line index
    full_line: str      # original line text


@dataclass
class StarterTextLine:
    """
    A hardcoded text string in the starter-selection dialogue that names the
    starter or its type.

    Crystal Legacy ElmsLab.asm has three text blocks::

        TakeCyndaquilText:        ; slot 0
            line "CYNDAQUIL, the"   ← line_type "species"
            cont "fire #MON?"       ← line_type "type"
        TakeTotodileText: ...       ; slot 1
        TakeChikoritaText: ...      ; slot 2

    ``slot_index`` matches the STARTER_CONSTANTS order:
        0 = CYNDAQUIL, 1 = TOTODILE, 2 = CHIKORITA
    """
    slot_index: int     # 0, 1, or 2
    line_type: str      # "species" or "type"
    source_file: str
    line_index: int
    full_line: str
    text_value: str     # current value — display name (e.g. "CYNDAQUIL") or type ("fire")


class CrystalLegacyParser:
    def __init__(self, source_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.log = log_fn or print
        self.wild_encounters = []      # list[WildEncounterGroup]
        self.wild_held_items = []      # list[WildHeldItemEntry]
        self.tmhm_compat = []          # list[TMHMCompatEntry]
        self.level_evo_map = {}        # {source_species_id: [(target_id, min_level), ...]}
        self.trainers = []             # list[Trainer]
        self.starters = []             # list[StarterLocation], exactly 3
        self.starter_dialogue_lines = []  # list[StarterDialogueLine]
        self.starter_text_lines = []      # list[StarterTextLine]
        self.field_items = []          # list[FieldItemEntry]
        self.starter_items = []        # list[StarterItemLocation]
        self.static_encounters = []    # list[StaticEncounter]
        self.trades = []               # list[InGameTrade]
        self.evolution_entries = []    # list[EvolutionEntry] (LEVEL + TRADE + HAPPINESS types)
        self.fish_slots = []           # list[FishSlot] — Crystal Legacy centralized fish.asm slots
        self.intro_menu_path = None    # str | None — path to engine/menus/intro_menu.asm
        self._errors = []

    def parse_all(self):
        """Parse all relevant source files. Returns True if starters were found."""
        self.log("Parsing wild encounter files...")
        for rel_path in WILD_ENCOUNTER_FILES:
            full_path = os.path.join(self.source_dir, rel_path)
            if os.path.exists(full_path):
                self._parse_wild_file(full_path)
            else:
                self.log(f"  [SKIP] Not found: {rel_path}")

        self.log("Parsing trainer parties...")
        trainer_path = os.path.join(self.source_dir, TRAINER_PARTIES_FILE)
        if os.path.exists(trainer_path):
            self._parse_trainer_parties(trainer_path)
        else:
            self.log(f"  [WARN] Not found: {TRAINER_PARTIES_FILE}")

        self.log("Searching for starter definitions...")
        self._find_starters()

        self.log("Scanning for starter dialogue lines...")
        self.starter_dialogue_lines, self.starter_text_lines = self._find_starter_dialogue()

        self.log("Scanning for starter givepoke scripts...")
        self.starter_items = self._find_starter_items()

        self.log("Scanning for static encounters...")
        self._parse_static_encounters()

        self.log("Scanning for evolution data...")
        self.evolution_entries = self._parse_evolutions()

        self.log("Scanning for in-game trades...")
        self._parse_trades()

        self.log("Scanning for wild held items...")
        self.wild_held_items = self._parse_wild_held_items()

        self.log("Scanning for TM/HM compatibility...")
        self.tmhm_compat = self._parse_tmhm_compat()

        self.log("Scanning for field items...")
        self.field_items = self._parse_field_items()

        self.log("Locating new-game initialization file...")
        self._find_intro_menu()

        trade_evos  = sum(1 for e in self.evolution_entries if "TRADE" in e.evo_type.upper())
        time_evos   = sum(1 for e in self.evolution_entries if "HAPPINESS_DAY" in e.evo_type.upper()
                          or "HAPPINESS_NIGHT" in e.evo_type.upper())
        vis_items   = sum(1 for e in self.field_items if e.item_type == "visible")
        hid_items   = sum(1 for e in self.field_items if e.item_type == "hidden")
        self.log(
            f"Parse complete: {len(self.wild_encounters)} encounter groups, "
            f"{len(self.trainers)} trainers, "
            f"{len(self.static_encounters)} static encounters "
            f"({sum(1 for e in self.static_encounters if e.is_legendary)} legendary, "
            f"{sum(1 for e in self.static_encounters if not e.is_legendary)} standard), "
            f"{len(self.trades)} in-game trade(s), "
            f"{len(self.starter_items)} starter item line(s), "
            f"{len(self.wild_held_items)} wild held item entry/entries, "
            f"{vis_items} visible + {hid_items} hidden field item(s), "
            f"{trade_evos} trade evolution(s) + {time_evos} time-based evolution(s), "
            f"starters={'yes' if len(self.starters) == 3 else 'NOT FOUND'}."
        )
        return len(self.starters) == 3

    # -------------------------------------------------------------------------
    # New-game item initialization
    # -------------------------------------------------------------------------

    def _find_intro_menu(self):
        """Locate engine/menus/intro_menu.asm and confirm it has the expected
        wNumItems / wNumPCItems InitList patterns."""
        candidates = [
            os.path.join(self.source_dir, "engine", "menus", "intro_menu.asm"),
            os.path.join(self.source_dir, "engine", "menu", "intro_menu.asm"),
        ]
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                if "wNumItems" in text and ".InitList" in text:
                    self.intro_menu_path = path
                    self.log(f"  intro_menu.asm found: {os.path.relpath(path, self.source_dir)}")
                    return
            except OSError:
                pass
        self.log("  [WARN] intro_menu.asm not found — starting-item edits will be skipped.")

    # -------------------------------------------------------------------------
    # Wild encounter parsing
    # -------------------------------------------------------------------------

    def _parse_wild_file(self, filepath: str):
        rel = os.path.relpath(filepath, self.source_dir)

        # Crystal Legacy uses a centralized fish.asm with a custom format
        # (named sublists + TimeFishGroups table) — delegate to its own parser.
        if os.path.basename(filepath) == "fish.asm":
            self._parse_fish_asm(filepath)
            return

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        # Determine encounter type from filename
        fname = os.path.basename(filepath)
        if "grass" in fname:
            enc_type = "grass"
            slots_per_period = 7
        elif "water" in fname:
            enc_type = "water"
            slots_per_period = 3
        elif "fish" in fname:
            enc_type = "fish"
            slots_per_period = 3
        elif "treemon" in fname and "map" not in fname:
            enc_type = "headbutt"
            slots_per_period = 6
        elif "bug_contest" in fname:
            enc_type = "bug_contest"
            slots_per_period = 7
        elif "swarm" in fname and "grass" in fname:
            enc_type = "swarm_grass"
            slots_per_period = 2
        elif "swarm" in fname:
            enc_type = "swarm_water"
            slots_per_period = 2
        else:
            enc_type = "other"
            slots_per_period = 7

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Look for macro start
            m = re.match(r'def_\w+wildmons\s+(\w+)', line)
            if m:
                location = m.group(1)
                block_start = i
                slots = []
                rates = []

                i += 1
                # Next non-blank non-comment line should be rates
                while i < len(lines):
                    l = lines[i].strip()
                    if l and not l.startswith(';'):
                        # Rates line: "db 20, 20, 20"
                        rates = self._parse_db_ints(l)
                        i += 1
                        break
                    i += 1

                # Collect all db level, SPECIES lines until end macro
                while i < len(lines):
                    l = lines[i].strip()
                    if re.match(r'end_\w+wildmons', l):
                        block_end = i
                        # Compute how many slots belong to each time period
                        n_periods = max(len(rates), 1)
                        spp = len(slots) // n_periods if n_periods else len(slots)
                        group = WildEncounterGroup(
                            location=location,
                            encounter_type=enc_type,
                            slots=slots,
                            rates=rates,
                            source_file=filepath,
                            line_start=block_start,
                            line_end=block_end,
                            slots_per_period=spp,
                        )
                        self.wild_encounters.append(group)
                        i += 1
                        break

                    # Parse "db  2, HOOTHOOT" style lines
                    slot = self._parse_wild_slot_line(l)
                    if slot:
                        slots.append(slot)
                    i += 1
            else:
                i += 1

    def _parse_wild_slot_line(self, line: str) -> Optional[WildSlot]:
        """Parse a line like 'db  2, HOOTHOOT' or 'db 5, PIDGEY ; comment'."""
        # Strip comments
        line = re.sub(r';.*$', '', line).strip()
        m = re.match(r'db\s+(\d+)\s*,\s*([A-Z][A-Z0-9_]*)', line)
        if m:
            level = int(m.group(1))
            species = m.group(2)
            if species in POKEMON_CONSTANTS:
                return WildSlot(level=level, species_const=species)
        return None

    def _parse_fish_asm(self, filepath: str):
        """
        Parse Crystal Legacy's centralized data/wild/fish.asm.

        Two kinds of species-bearing lines:

        1. Sublist entry (chance expression first):
               db  70 percent + 1, MAGIKARP,   10
               db 100 percent,     time_group 0   ← skip (time_group expands to 0)
           Pattern: starts with 'db <digit>...', 2nd comma-field is the species.
           Skip lines where the species field is not a valid Pokémon constant
           (handles 'time_group N' and other non-species tokens).

        2. TimeFishGroups entry (species first):
               db CORSOLA,    20,  STARYU,     20 ; 0
           Pattern: starts with 'db <UPPER_LETTER>...', 4 comma-separated fields
           where fields 1 and 3 are species constants and 2 and 4 are levels.
           Each row produces TWO FishSlots (col=0 for day, col=1 for night).

        Appends all discovered FishSlot objects to self.fish_slots.
        """
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Regex for sublist entries: db <chance_expr>, SPECIES, LEVEL
        # The chance expression begins with a digit and may contain spaces/+/%
        RE_SUBLIST = re.compile(
            r'^db\s+\d[^,]*,\s*([A-Z][A-Z0-9_]+)\s*,\s*\d+'
        )
        # Regex for TimeFishGroups rows: db SPECIES, LEVEL, SPECIES, LEVEL
        # First field starts with an uppercase letter (a Pokémon constant)
        RE_TIME = re.compile(
            r'^db\s+([A-Z][A-Z0-9_]+)\s*,\s*\d+\s*,\s*([A-Z][A-Z0-9_]+)\s*,\s*\d+'
        )

        added = 0
        for i, raw_line in enumerate(lines):
            clean = re.sub(r';.*$', '', raw_line).strip()
            if not clean.startswith('db'):
                continue

            m_time = RE_TIME.match(clean)
            if m_time:
                # TimeFishGroups row — two species per line
                day_species   = m_time.group(1)
                night_species = m_time.group(2)
                if day_species in POKEMON_CONSTANTS:
                    self.fish_slots.append(FishSlot(
                        species_const=day_species,
                        source_file=filepath,
                        line_index=i,
                        col=0,
                        full_line=raw_line,
                    ))
                    added += 1
                if night_species in POKEMON_CONSTANTS:
                    self.fish_slots.append(FishSlot(
                        species_const=night_species,
                        source_file=filepath,
                        line_index=i,
                        col=1,
                        full_line=raw_line,
                    ))
                    added += 1
                continue

            m_sub = RE_SUBLIST.match(clean)
            if m_sub:
                species = m_sub.group(1)
                if species in POKEMON_CONSTANTS:
                    self.fish_slots.append(FishSlot(
                        species_const=species,
                        source_file=filepath,
                        line_index=i,
                        col=0,
                        full_line=raw_line,
                    ))
                    added += 1
                # else: time_group placeholder or unknown token — skip

        self.log(f"  fish.asm: {added} fish slot(s) parsed.")

    def _parse_db_ints(self, line: str) -> list:
        """Parse 'db 20, 20, 20' -> [20, 20, 20]."""
        line = re.sub(r';.*$', '', line).strip()
        m = re.match(r'db\s+(.*)', line)
        if m:
            parts = m.group(1).split(',')
            result = []
            for p in parts:
                p = p.strip()
                try:
                    result.append(int(p))
                except ValueError:
                    pass
            return result
        return []

    # -------------------------------------------------------------------------
    # Trainer parsing
    # -------------------------------------------------------------------------

    def _parse_trainer_parties(self, filepath: str):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        current_class = "UNKNOWN"
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Detect trainer class from comments like "; Falkner" or section labels
            class_m = re.match(r';\s*(.+)', stripped)
            if class_m and not re.search(r'db\s', stripped):
                candidate = class_m.group(1).strip()
                if candidate and not candidate.startswith('.'):
                    current_class = candidate

            # Detect trainer definition: db "NAME@", TRAINERTYPE_xxx
            trainer_m = re.match(r'\s*db\s+"([^"]*?)@"\s*,\s*(\w+)', line)
            if trainer_m:
                trainer_name = trainer_m.group(1)
                type_const = trainer_m.group(2)
                type_value = self._resolve_trainertype(type_const)
                line_start = i
                party = []
                i += 1

                # Parse party until "db -1"
                while i < len(lines):
                    pline = lines[i].strip()
                    pline_stripped = re.sub(r';.*$', '', pline).strip()

                    if re.match(r'db\s+-1', pline_stripped):
                        # End of trainer
                        trainer = Trainer(
                            name=trainer_name,
                            trainer_type_const=type_const,
                            trainer_type_value=type_value,
                            party=party,
                            trainer_class=current_class,
                            source_file=filepath,
                            line_start=line_start,
                            line_end=i,
                        )
                        self.trainers.append(trainer)
                        i += 1
                        break

                    # Try to parse a Pokemon entry
                    poke = self._parse_trainer_poke_line(pline_stripped, type_value)
                    if poke:
                        party.append(poke)
                    i += 1

                continue  # already incremented i

            i += 1

    def _resolve_trainertype(self, const_name: str) -> int:
        """Resolve a TRAINERTYPE constant name to its integer value."""
        if const_name in TRAINERTYPE_NAMES:
            return TRAINERTYPE_NAMES[const_name]
        # Handle combined constants via OR (uncommon but possible)
        return 0

    def _parse_trainer_poke_line(self, line: str, trainer_type: int) -> Optional[TrainerPokemon]:
        """
        Parse a trainer party line based on the trainer type flags.
        Handles all Crystal Legacy TRAINERTYPE combinations.
        """
        if not line.startswith("db"):
            return None

        # Tokenize the db arguments
        m = re.match(r'db\s+(.*)', line)
        if not m:
            return None

        tokens = [t.strip() for t in m.group(1).split(',')]
        if len(tokens) < 2:
            return None

        try:
            level = int(tokens[0])
        except ValueError:
            return None

        species_const = tokens[1] if len(tokens) > 1 else None
        if not species_const or species_const not in POKEMON_CONSTANTS:
            return None

        poke = TrainerPokemon(level=level, species_const=species_const)

        # Parse additional fields based on type flags
        # Bits determine what follows: item, moves, dvs, etc.
        idx = 2  # next token index

        has_moves = bool(trainer_type & TRAINERTYPE_MOVES)
        has_item  = bool(trainer_type & TRAINERTYPE_ITEM)

        if has_item and idx < len(tokens):
            poke.item = tokens[idx]
            idx += 1

        if has_moves:
            moves = []
            for _ in range(4):
                if idx < len(tokens):
                    moves.append(tokens[idx])
                    idx += 1
            poke.moves = moves

        return poke

    # -------------------------------------------------------------------------
    # Starter finding
    # -------------------------------------------------------------------------

    def _find_starters(self):
        """
        Search for starter Pokemon definitions in the ASM source.
        Tries known file locations first, then falls back to a full search.
        """
        # Try priority candidate files
        for rel_path in STARTER_FILE_CANDIDATES:
            full_path = os.path.join(self.source_dir, rel_path)
            if os.path.exists(full_path):
                found = self._search_starters_in_file(full_path)
                if len(found) == 3:
                    self.starters = found
                    self.log(f"  Starters found in {rel_path}")
                    return

        # Fall back: scan all .asm files
        self.log("  Candidate files not found; scanning all .asm files for starters...")
        for root, dirs, files in os.walk(self.source_dir):
            # Skip purely asset / binary directories; keep maps + engine
            skip_dirs = {'gfx', 'audio', 'mobile', 'vc', 'lib'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                if not fname.endswith('.asm'):
                    continue
                full_path = os.path.join(root, fname)
                found = self._search_starters_in_file(full_path)
                if len(found) == 3:
                    self.starters = found
                    rel = os.path.relpath(full_path, self.source_dir)
                    self.log(f"  Starters found in {rel}")
                    return

        # If we still haven't found all 3, try any file with at least one starter
        if len(self.starters) < 3:
            self.log("  [WARN] Could not locate all 3 starter definitions.")

    # Matches:  givepoke SPECIES, level, ITEM   or   givepoke SPECIES, level
    _GIVEPOKE_RE = re.compile(
        r'^\s*givepoke\s+([A-Z][A-Z0-9_]+)\s*,', re.IGNORECASE
    )

    def _search_starters_in_file(self, filepath: str) -> list:
        """
        Search a single file for starter Pokémon definitions.
        Handles several source layouts:
          - StarterMon: label + db lines  (vanilla Crystal)
          - givepoke SPECIES, level, ITEM  (Crystal Legacy / ElmsLab.asm)
          - Window of 3 starter constants within 15 lines
          - ld a, SPECIES  pattern

        Returns list of StarterLocation (len 0 or 3).
        """
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return []

        found = []

        # Strategy 0: givepoke SPECIES, ... — Crystal Legacy ElmsLab style
        givepoke_hits = {}
        for i, line in enumerate(lines):
            m = self._GIVEPOKE_RE.match(line)
            if m:
                species = m.group(1).upper()
                if species in STARTER_CONSTANTS and species not in givepoke_hits:
                    givepoke_hits[species] = StarterLocation(
                        species_const=species,
                        source_file=filepath,
                        line_index=i,
                        full_line=line,
                    )
        if len(givepoke_hits) == 3:
            return [givepoke_hits[sc] for sc in STARTER_CONSTANTS]

        # Strategy 1: look for a StarterMon: label followed by 3 db lines
        for i, line in enumerate(lines):
            if re.search(r'StarterMon\s*:', line, re.IGNORECASE):
                candidates = []
                j = i + 1
                while j < len(lines) and j < i + 10:
                    m = re.match(r'\s*db\s+([A-Z][A-Z0-9_]+)', lines[j].strip())
                    if m and m.group(1) in POKEMON_CONSTANTS:
                        candidates.append(StarterLocation(
                            species_const=m.group(1),
                            source_file=filepath,
                            line_index=j,
                            full_line=lines[j],
                        ))
                    j += 1
                if len(candidates) >= 3:
                    return candidates[:3]

        # Strategy 2: look for any block where all 3 default starters appear
        # within a 15-line window
        starter_set = set(STARTER_CONSTANTS)
        for i in range(len(lines)):
            window = lines[i:i+15]
            window_starters = {}
            for j, wline in enumerate(window):
                for sc in starter_set:
                    m = re.search(r'\b' + sc + r'\b', wline)
                    if m and sc not in window_starters:
                        window_starters[sc] = StarterLocation(
                            species_const=sc,
                            source_file=filepath,
                            line_index=i + j,
                            full_line=wline,
                        )
            if len(window_starters) == 3:
                return [window_starters[sc] for sc in STARTER_CONSTANTS]

        # Strategy 3: look for load-immediate pattern: ld a, CYNDAQUIL
        for sc in STARTER_CONSTANTS:
            for i, line in enumerate(lines):
                if re.search(r'ld\s+a\s*,\s*' + sc + r'\b', line):
                    found.append(StarterLocation(
                        species_const=sc,
                        source_file=filepath,
                        line_index=i,
                        full_line=line,
                    ))
                    break
        if len(found) == 3:
            return found

        return []

    # -------------------------------------------------------------------------
    # Starter dialogue parsing
    # -------------------------------------------------------------------------

    # pokepic / cry macro:   pokepic SPECIES   or   cry SPECIES
    _POKEPIC_CRY_RE = re.compile(
        r'^\s*(pokepic|cry)\s+([A-Z][A-Z0-9_]+)',
        re.IGNORECASE,
    )
    # getmonname macro:  getmonname DEST, SPECIES
    _GETMONNAME_RE = re.compile(
        r'^\s*(getmonname)\s+\S+\s*,\s*([A-Z][A-Z0-9_]+)',
        re.IGNORECASE,
    )

    def _find_starter_dialogue(self) -> tuple:
        """
        Scan the starter source file (ElmsLab.asm) for script macros and
        hardcoded text that name each starter Pokémon.

        Captures three categories:

        1. ``pokepic SPECIES`` / ``cry SPECIES`` / ``getmonname …, SPECIES``
           — returned as StarterDialogueLine objects.

        2. Text labels ``Take{TitleCase}Text:`` followed by:
               line "SPECIES, the"   → StarterTextLine(line_type="species")
               cont "type #MON?"     → StarterTextLine(line_type="type")

        Returns (dialogue_lines, text_lines).
        If starters were not found, returns ([], []).
        """
        if not self.starters:
            return [], []

        starter_file = self.starters[0].source_file
        starter_set  = set(STARTER_CONSTANTS)

        try:
            with open(starter_file, 'r', encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
        except OSError:
            return [], []

        dialogue_lines: list = []
        text_lines:     list = []

        # Build the lookup of text-block labels → slot index.
        # STARTER_CONSTANTS[0] = "CYNDAQUIL" → label "takecyndaquilttext"
        # STARTER_CONSTANTS[1] = "TOTODILE"  → label "taketotodiletext"
        # STARTER_CONSTANTS[2] = "CHIKORITA" → label "takechikoritatext"
        take_labels = {}
        for idx, sc in enumerate(STARTER_CONSTANTS):
            title = sc[0] + sc[1:].lower()   # e.g. "Cyndaquil"
            take_labels[f"take{title.lower()}text"] = idx

        # Regex inside text blocks
        text_macro_re  = re.compile(r'^\s*(line|cont)\s+"([^"]*)"', re.IGNORECASE)
        # "SPECIES, the"  — species can include spaces, hyphens, apostrophes
        species_text_re = re.compile(r"^(.+?),\s+the$", re.IGNORECASE)
        # "type #MON?"    — type is one lowercase word
        type_text_re    = re.compile(r'^([a-z]+)\s+#MON\?$', re.IGNORECASE)
        # ASM label line
        label_re        = re.compile(r'^([A-Za-z_]\w*)\s*:')

        current_slot = -1   # which text block we're currently inside (-1 = none)

        for i, raw in enumerate(lines):
            # Strip inline comment for pattern matching, keep raw for storage
            line_nc = re.sub(r';.*$', '', raw)

            # ── script macros: pokepic / cry ─────────────────────────────
            m_pc = self._POKEPIC_CRY_RE.match(line_nc)
            if m_pc:
                species = m_pc.group(2).upper()
                if species in starter_set:
                    dialogue_lines.append(StarterDialogueLine(
                        macro=m_pc.group(1).lower(),
                        species_const=species,
                        source_file=starter_file,
                        line_index=i,
                        full_line=raw,
                    ))

            # ── script macros: getmonname ─────────────────────────────────
            m_gm = self._GETMONNAME_RE.match(line_nc)
            if m_gm:
                species = m_gm.group(2).upper()
                if species in starter_set:
                    dialogue_lines.append(StarterDialogueLine(
                        macro='getmonname',
                        species_const=species,
                        source_file=starter_file,
                        line_index=i,
                        full_line=raw,
                    ))

            # ── label detection (tracks which text block we're in) ────────
            lm = label_re.match(raw.strip())
            if lm:
                label_key  = lm.group(1).lower()
                current_slot = take_labels.get(label_key, -1)

            # ── text macros inside a Take…Text block ──────────────────────
            if current_slot >= 0:
                m_tm = text_macro_re.match(raw)
                if m_tm:
                    macro_kw = m_tm.group(1).lower()   # "line" or "cont"
                    content  = m_tm.group(2)

                    if macro_kw == 'line':
                        ms = species_text_re.match(content)
                        if ms:
                            text_lines.append(StarterTextLine(
                                slot_index=current_slot,
                                line_type='species',
                                source_file=starter_file,
                                line_index=i,
                                full_line=raw,
                                text_value=ms.group(1),
                            ))
                    elif macro_kw == 'cont':
                        mt = type_text_re.match(content)
                        if mt:
                            text_lines.append(StarterTextLine(
                                slot_index=current_slot,
                                line_type='type',
                                source_file=starter_file,
                                line_index=i,
                                full_line=raw,
                                text_value=mt.group(1).lower(),
                            ))

        self.log(
            f"  Starter dialogue: {len(dialogue_lines)} script macro line(s), "
            f"{len(text_lines)} text line(s) found."
        )
        return dialogue_lines, text_lines

    # -------------------------------------------------------------------------
    # Evolution parsing
    # -------------------------------------------------------------------------

    # Evolution types we capture (with and without EVOLVE_ prefix).
    # LEVEL entries are needed for the "Make Evolutions Easier" level-cap feature.
    # TRADE entries are kept in case the source still has them (some Crystal Legacy
    # builds retain trade evolutions rather than converting them).
    # TIME entries are needed for "Remove Time-Based Evolutions".
    _RELEVANT_EVO_TYPES = frozenset({
        "LEVEL",          "EVOLVE_LEVEL",
        "TRADE",          "EVOLVE_TRADE",
        "TRADE_ITEM",     "EVOLVE_TRADE_ITEM",
        "HAPPINESS_DAY",  "EVOLVE_HAPPINESS_DAY",
        "HAPPINESS_NIGHT","EVOLVE_HAPPINESS_NIGHT",
    })

    # Regex: Crystal Legacy / pret-disassembly format:
    #   db EVOLVE_LEVEL, 16, IVYSAUR        (TYPE, PARAM, SPECIES)
    #   db EVOLVE_ITEM, MOON_STONE, NIDOQUEEN
    #   db EVOLVE_HAPPINESS, TR_MORNDAY, ESPEON
    # param is a number, negative number, or ALL-CAPS constant; target starts with letter.
    _EVOLVE_RE = re.compile(
        r'\bdb\s+(EVOLVE_[A-Z_]+)\s*,\s*([A-Z0-9_-]+)\s*,\s*([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    def _parse_evolutions(self) -> list:
        """
        Parse evolution entries from the source tree.

        Searches candidate file paths first, then falls back to scanning all
        .asm files.  Records entries whose type needs potential modification:
        LEVEL (for Make Evolutions Easier cap), TRADE / TRADE_ITEM (conversion
        to level), and HAPPINESS_DAY / HAPPINESS_NIGHT (Remove Time Evolutions).

        Also builds self.level_evo_map = {source_id: [(target_id, level), ...]}
        for all LEVEL evolutions — used by the rival starter feature.

        Returns a list of EvolutionEntry objects.
        """
        # Try candidate paths first
        for rel in EVOLUTION_DATA_FILE_CANDIDATES:
            full = os.path.join(self.source_dir, rel)
            if os.path.exists(full):
                entries, evo_map = self._scan_evolve_file(full)
                self.level_evo_map = evo_map
                if entries:
                    self.log(f"  Evolution data: {len(entries)} relevant entry/entries in {rel}")
                    return entries
                self.log(f"  Evolution data found in {rel} (no trade/time evolutions).")
                return entries

        # Fallback: walk the tree looking for any file with evolve macro lines
        self.log("  Evolution candidates not found; scanning source tree...")
        skip_dirs = {'gfx', 'audio', 'mobile', 'vc', 'lib'}
        all_entries = []
        merged_map = {}
        found_files = set()
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                if not fname.endswith('.asm'):
                    continue
                filepath = os.path.join(root, fname)
                entries, evo_map = self._scan_evolve_file(filepath)
                if entries:
                    all_entries.extend(entries)
                    found_files.add(os.path.relpath(filepath, self.source_dir))
                for src_id, targets in evo_map.items():
                    merged_map.setdefault(src_id, []).extend(targets)

        self.level_evo_map = merged_map
        if all_entries:
            self.log(
                f"  Found {len(all_entries)} relevant evolution entry/entries "
                f"across {len(found_files)} file(s)."
            )
        else:
            self.log("  [WARN] No modifiable evolution entries found — "
                     "evolution features will be skipped.")
        return all_entries

    # Label regex for evolution blocks: e.g. "ChikoritaEvos:" or "BulbasaurEvolutionData:"
    _EVO_LABEL_RE = re.compile(
        r'^([A-Za-z][A-Za-z0-9_]*?)(?:Evos?|EvolutionData|EvolutionInfo|Evolution|Data)?::?$',
        re.IGNORECASE,
    )
    # Common suffixes to strip when deriving a Pokémon name from a label.
    # Crystal Legacy uses "BulbasaurEvosAttacks:", so include compound forms.
    _EVO_LABEL_SUFFIXES = (
        'evosattacks', 'evolutiondata', 'evolutioninfo', 'evolution',
        'evos', 'evo', 'attacks', 'data',
    )

    def _label_to_species_id(self, label: str) -> int:
        """Try to derive a species ID from an ASM label. Returns 0 if not found."""
        name = label.upper()
        # Direct lookup first
        if name in POKEMON_CONSTANTS:
            return POKEMON_CONSTANTS[name]
        # Strip known suffixes
        lower = label.lower()
        for suffix in self._EVO_LABEL_SUFFIXES:
            if lower.endswith(suffix):
                stem = label[:len(label) - len(suffix)].upper()
                if stem in POKEMON_CONSTANTS:
                    return POKEMON_CONSTANTS[stem]
                break
        return 0

    def _scan_evolve_file(self, filepath: str):
        """
        Return (relevant_entries, level_evo_map) from a single file.

        relevant_entries — list[EvolutionEntry] for LEVEL / TRADE / HAPPINESS types
        level_evo_map    — dict {source_id: [(target_id, level), ...]} for LEVEL types
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except OSError:
            return [], {}

        entries   = []
        level_map = {}           # {source_id: [(target_id, level)]}
        current_source_id = 0    # species whose evo block we're in

        label_re = re.compile(r'^([A-Za-z][A-Za-z0-9_]*)::?$')

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip blank lines and full-line comments
            if not stripped or stripped.startswith(';'):
                continue

            # Track label lines to know which Pokémon's block we're in
            lm = label_re.match(stripped)
            if lm:
                sid = self._label_to_species_id(lm.group(1))
                if sid:
                    current_source_id = sid
                continue

            m = self._EVOLVE_RE.search(line)
            if not m:
                continue

            # Crystal Legacy format: db EVOLVE_TYPE, PARAM, SPECIES
            evo_type = m.group(1).upper()
            param    = m.group(2).upper()   # level number, item const, or TR_* const
            target   = m.group(3).upper()   # target species constant

            # Synthesize day/night sub-type from HAPPINESS param so the engine
            # can distinguish time-based from always-happiness evolutions.
            if evo_type == 'EVOLVE_HAPPINESS':
                if param in ('TR_MORNDAY', 'TR_DAY'):
                    evo_type = 'EVOLVE_HAPPINESS_DAY'
                elif param == 'TR_NITE':
                    evo_type = 'EVOLVE_HAPPINESS_NIGHT'
                # TR_ANYTIME stays as EVOLVE_HAPPINESS (not time-based → skipped)

            # Build level_evo_map from LEVEL evolutions
            if evo_type in ('LEVEL', 'EVOLVE_LEVEL') and current_source_id:
                target_id = POKEMON_CONSTANTS.get(target, 0)
                if target_id:
                    try:
                        lv = int(param)
                        level_map.setdefault(current_source_id, []).append((target_id, lv))
                    except ValueError:
                        pass

            # Collect modifiable entries (TRADE / HAPPINESS)
            if evo_type not in self._RELEVANT_EVO_TYPES:
                continue
            entries.append(EvolutionEntry(
                evo_type=evo_type,
                target=target,
                param=param,
                source_file=filepath,
                line_index=i,
                full_line=line,
            ))

        return entries, level_map

    # -------------------------------------------------------------------------
    # Starter item parsing
    # -------------------------------------------------------------------------

    def _find_starter_items(self) -> list:
        """
        Scan script files for ``givepoke STARTER_SPECIES, level, ITEM`` lines.

        Returns a list of StarterItemLocation — one entry per matching line.
        If Crystal Legacy gives starters without a givepoke macro (e.g. via a
        data table + engine call), this returns an empty list and the feature
        is gracefully skipped.
        """
        starter_set = set(STARTER_CONSTANTS)
        skip_dirs   = {'data', 'gfx', 'audio', 'mobile', 'vc', 'lib'}
        trainer_abs = os.path.join(self.source_dir, TRAINER_PARTIES_FILE)

        # Match: givepoke SPECIES, <number>, ITEM_CONST
        _RE = re.compile(
            r'givepoke\s+([A-Z][A-Z0-9_]+)\s*,\s*\d+\s*,\s*([A-Z_][A-Z0-9_]*)',
        )

        results = []
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                if not fname.endswith('.asm'):
                    continue
                filepath = os.path.join(root, fname)
                if filepath == trainer_abs:
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                except OSError:
                    continue
                for i, line in enumerate(lines):
                    m = _RE.search(line)
                    if m:
                        species = m.group(1).upper()
                        item    = m.group(2).upper()
                        if species in starter_set:
                            results.append(StarterItemLocation(
                                species_const=species,
                                item_const=item,
                                source_file=filepath,
                                line_index=i,
                                full_line=line,
                            ))

        if results:
            self.log(f"  Found {len(results)} starter givepoke line(s) with items.")
        else:
            self.log("  No starter givepoke lines found — item randomization will be skipped.")
        return results

    # -------------------------------------------------------------------------
    # In-game trade parsing
    # -------------------------------------------------------------------------

    # Regex for Crystal Legacy single-line npctrade macro:
    #   npctrade DIALOGSET, GIVEMON, GETMON, "NICKNAME@@@", DVS1, DVS2, ITEM, OT_ID, "OT_NAME@@@", GENDER
    _NPCTRADE_RE = re.compile(
        r'^\s*npctrade\s+'
        r'(\w+)\s*,\s*'                   # group 1: dialogset
        r'([A-Z][A-Z0-9_]+)\s*,\s*'       # group 2: GIVEMON (player gives = requested_species)
        r'([A-Z][A-Z0-9_]+)\s*,\s*'       # group 3: GETMON  (player gets  = given_species)
        r'"([^"]*)"\s*,\s*'               # group 4: nickname (with @ padding)
        r'(\$?[0-9A-Fa-f]+)\s*,\s*'       # group 5: dvs byte 1
        r'(\$?[0-9A-Fa-f]+)\s*,\s*'       # group 6: dvs byte 2
        r'([A-Z_][A-Z0-9_]*)\s*,\s*'      # group 7: item constant
        r'(\d+)\s*,\s*'                   # group 8: OT ID
        r'"([^"]*)"\s*,\s*'               # group 9: OT name (with @ padding)
        r'(\w+)',                          # group 10: gender constant
        re.IGNORECASE,
    )

    def _parse_trades(self):
        """
        Search for in-game trade data blocks in the source tree.

        Strategy 1 — dedicated trade data files:
          Any .asm file whose path contains the word "trade" is scanned for
          the canonical Crystal block format:
              db GIVEN_SPECIES
              db REQUESTED_SPECIES
              dw DVS_WORD
              db "NICKNAME@"
              db "OT_NAME@"
              db ITEM_CONST

        Strategy 2 — script-embedded trades:
          All remaining .asm files are scanned for the `trade GIVEN, REQUESTED`
          script macro (gives only species; optional fields are unavailable).

        Strategy 3 — Crystal Legacy single-line npctrade macro:
          All .asm files are scanned for:
              npctrade DIALOGSET, GIVEMON, GETMON, "NICK@@@", DVS1, DVS2, ITEM, OT_ID, "OT@@@", GENDER
          This is Crystal Legacy's compact format where all trade data is on one line.

        Found trades are stored in self.trades.
        """
        found = []

        # ── collect files that look like trade data files ──────────────────
        trade_files = set()
        all_asm = []
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            for fname in sorted(files):
                if not fname.endswith('.asm'):
                    continue
                full_path = os.path.join(root, fname)
                all_asm.append(full_path)
                if 'trade' in fname.lower() or 'trade' in root.lower():
                    trade_files.add(full_path)

        # Strategy 3 (checked first): npctrade single-line macro (Crystal Legacy)
        npctrade_results = []
        for fp in all_asm:
            npctrade_results.extend(self._parse_npctrade_lines(fp))
        if npctrade_results:
            found.extend(npctrade_results)
        else:
            # Strategy 1: block format in trade-related files
            for fp in sorted(trade_files):
                found.extend(self._parse_trade_data_blocks(fp))

            # Strategy 2: `trade SPECIES, SPECIES` macro in any script file
            for fp in all_asm:
                if fp not in trade_files:
                    found.extend(self._parse_trade_script_commands(fp))

        self.trades = found
        self.log(f"  Found {len(found)} in-game trade(s).")
        for t in found:
            nick_info = f", nick={t.nickname!r}" if t.nickname else ""
            ot_info   = f", OT={t.ot_name!r}"   if t.ot_name  else ""
            self.log(f"    Gives {t.requested_species} → Receives {t.given_species}"
                     f"{nick_info}{ot_info}")

    def _parse_trade_data_blocks(self, filepath: str) -> list:
        """
        Parse a Crystal-format trade data block from a file.

        Scans for pairs of consecutive  db POKEMON_CONST  lines, then
        collects the next dw (DVs), two quoted db strings (nickname, OT),
        and one non-Pokémon db (item) from the following lines.
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
        except OSError:
            return []

        trades = []
        n = len(lines)

        poke_re = re.compile(r'^\s+db\s+([A-Z][A-Z0-9_]+)\s*(?:;.*)?$')
        dw_re   = re.compile(r'^\s+dw\s+(\S+)')
        str_re  = re.compile(r'^\s+db\s+"([^"]*?)@?"')   # nickname / OT
        item_re = re.compile(r'^\s+db\s+([A-Z][A-Z0-9_]+)\s*(?:;.*)?$')

        i = 0
        while i < n:
            m1 = poke_re.match(lines[i])
            if not (m1 and m1.group(1) in POKEMON_CONSTANTS):
                i += 1
                continue

            given_species  = m1.group(1)
            given_line     = i
            given_full     = lines[i].rstrip('\n')

            # Skip blanks / comments to find the next db line
            j = i + 1
            while j < n and not re.sub(r';.*$', '', lines[j]).strip():
                j += 1

            if j >= n:
                i += 1
                continue

            m2 = poke_re.match(lines[j])
            if not (m2 and m2.group(1) in POKEMON_CONSTANTS):
                i += 1
                continue

            requested_species = m2.group(1)
            requested_line    = j
            requested_full    = lines[j].rstrip('\n')

            trade = InGameTrade(
                source_file=filepath,
                given_species=given_species,
                given_line=given_line,
                given_full_line=given_full,
                requested_species=requested_species,
                requested_line=requested_line,
                requested_full_line=requested_full,
            )

            # Scan up to 25 lines ahead for optional fields
            k         = j + 1
            str_count = 0   # 0 = expecting nickname, 1 = expecting OT

            while k < min(n, j + 25):
                lk_clean = re.sub(r';.*$', '', lines[k]).strip()
                if not lk_clean:
                    k += 1
                    continue

                # DV word (first dw we see)
                if trade.dvs_line < 0:
                    mdv = dw_re.match(lines[k])
                    if mdv:
                        trade.dvs_raw       = mdv.group(1)
                        trade.dvs_line      = k
                        trade.dvs_full_line = lines[k].rstrip('\n')
                        k += 1
                        continue

                # Quoted strings: first = nickname, second = OT
                ms = str_re.match(lines[k])
                if ms:
                    value = ms.group(1).rstrip()
                    if str_count == 0:
                        trade.nickname      = value
                        trade.nickname_line = k
                        trade.nickname_full_line = lines[k].rstrip('\n')
                    elif str_count == 1:
                        trade.ot_name       = value
                        trade.ot_line       = k
                        trade.ot_full_line  = lines[k].rstrip('\n')
                    str_count += 1
                    k += 1
                    continue

                # Item line: a bare db CONST that is NOT a Pokémon species
                # (only check this after we've already seen both quoted strings)
                if str_count >= 2:
                    mi = item_re.match(lines[k])
                    if mi and mi.group(1) not in POKEMON_CONSTANTS:
                        trade.item          = mi.group(1)
                        trade.item_line     = k
                        trade.item_full_line = lines[k].rstrip('\n')
                    break   # stop scanning after the item slot (found or not)

                # If lk_clean starts a new label or unrelated statement, stop
                if re.match(r'^[A-Za-z_]', lk_clean) and not lk_clean.startswith('db'):
                    break

                k += 1

            trades.append(trade)
            i = j + 1   # resume just after the requested-species line

        return trades

    def _parse_trade_script_commands(self, filepath: str) -> list:
        """
        Scan a script file for the `trade GIVEN, REQUESTED` macro pattern.
        Gives only species-level information (no nickname / OT / DVs / item).
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
        except OSError:
            return []

        trades   = []
        trade_re = re.compile(
            r'^\s+trade\s+([A-Z][A-Z0-9_]+)\s*,\s*([A-Z][A-Z0-9_]+)',
            re.IGNORECASE,
        )

        for i, raw in enumerate(lines):
            m = trade_re.match(raw)
            if not m:
                continue
            given     = m.group(1).upper()
            requested = m.group(2).upper()
            if given in POKEMON_CONSTANTS and requested in POKEMON_CONSTANTS:
                # Both species occupy the same line; writer handles this correctly.
                trades.append(InGameTrade(
                    source_file=filepath,
                    given_species=given,
                    given_line=i,
                    given_full_line=raw.rstrip('\n'),
                    requested_species=requested,
                    requested_line=i,          # same line — writer is aware
                    requested_full_line=raw.rstrip('\n'),
                ))

        return trades

    def _parse_npctrade_lines(self, filepath: str) -> list:
        """
        Scan a file for Crystal Legacy's single-line ``npctrade`` macro.

        Format::
            npctrade DIALOGSET, GIVEMON, GETMON, "NICKNAME@@@", DVS1, DVS2,
                     ITEM, OT_ID, "OT_NAME@@@", GENDER

        GIVEMON = species the player gives (requested_species)
        GETMON  = species the player receives (given_species)

        All data is on one line; given_line == requested_line so the writer's
        same-line replacement path is used for species swaps.  DVs/item are
        embedded in the macro and cannot be patched independently, so their
        line indices are left at -1.
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
        except OSError:
            return []

        trades = []
        for i, raw in enumerate(lines):
            # Strip inline comments before matching
            line_nc = re.sub(r';.*$', '', raw)
            m = self._NPCTRADE_RE.match(line_nc)
            if not m:
                continue
            givemon  = m.group(2).upper()   # player gives → requested
            getmon   = m.group(3).upper()   # player gets  → given
            nickname = m.group(4).rstrip('@').rstrip()
            ot_name  = m.group(9).rstrip('@').rstrip()
            item     = m.group(7).upper()

            if givemon not in POKEMON_CONSTANTS or getmon not in POKEMON_CONSTANTS:
                continue

            trades.append(InGameTrade(
                source_file=filepath,
                given_species=getmon,          # what player receives
                given_line=i,
                given_full_line=raw.rstrip('\n'),
                requested_species=givemon,     # what player gives
                requested_line=i,              # same line as given
                requested_full_line=raw.rstrip('\n'),
                # DVs are embedded in the macro — cannot patch independently
                dvs_raw="0",
                dvs_line=-1,
                dvs_full_line="",
                nickname=nickname,
                nickname_line=-1,              # embedded — not patched separately
                nickname_full_line="",
                ot_name=ot_name,
                ot_line=-1,                    # embedded — not patched separately
                ot_full_line="",
                item=item,
                item_line=-1,                  # embedded — not patched separately
                item_full_line="",
            ))

        return trades

    # -------------------------------------------------------------------------
    # Static encounter parsing
    # -------------------------------------------------------------------------

    def _parse_static_encounters(self):
        """
        Walk all .asm source files and collect static encounter definitions.

        Looks for three patterns:
          1. ``battle SPECIES, level, item``  — scripted wild battle (e.g. Red Gyarados,
             Sudowoodo, Lugia, Ho-Oh, Suicune final encounter, Lapras, Snorlax)
          2. ``givepoke SPECIES, level, ...`` — gift Pokemon (e.g. Eevee, Dratini, fossils)
          3. ``db SPECIES``                   — bare db entry in files whose path contains
             "roam", used for roaming legendary tables (Raikou, Entei)

        Files that are known wild-encounter data or the trainer-parties file are
        skipped so we don't accidentally pick up wild or trainer entries.
        """
        from static_data import ALL_STATIC_SPECIES, STATIC_LEGENDARY_SPECIES, ALL_STATIC_MACROS

        # Absolute paths to skip
        skip_abs = set()
        for rel in WILD_ENCOUNTER_FILES:
            skip_abs.add(os.path.normpath(os.path.join(self.source_dir, rel)))
        skip_abs.add(os.path.normpath(os.path.join(self.source_dir, TRAINER_PARTIES_FILE)))

        # Regex: `battle SPECIES,` or `givepoke SPECIES,`
        macro_re = re.compile(
            r'^\s+(?P<macro>' + '|'.join(ALL_STATIC_MACROS) + r')\s+'
            r'(?P<species>[A-Z][A-Z0-9_]+)\s*,',
            re.IGNORECASE,
        )
        # Regex: bare `db SPECIES` (roaming tables only)
        roam_re = re.compile(
            r'^\s+db\s+(?P<species>[A-Z][A-Z0-9_]+)\s*(?:;.*)?$',
            re.IGNORECASE,
        )
        # Regex: assembly label line (used to track context)
        label_re = re.compile(r'^(?P<label>[A-Za-z_]\w*)\s*::?')

        found = []

        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            for fname in sorted(files):
                if not fname.endswith('.asm'):
                    continue
                full_path = os.path.join(root, fname)
                if os.path.normpath(full_path) in skip_abs:
                    continue

                # Roaming files use a separate (looser) pattern
                path_lower = full_path.lower()
                is_roam_file = 'roam' in path_lower

                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as fh:
                        lines = fh.readlines()
                except OSError:
                    continue

                last_label = ""
                for i, raw_line in enumerate(lines):
                    # Track most recent label for deduplication / context
                    lm = label_re.match(raw_line)
                    if lm:
                        last_label = lm.group('label')
                        continue

                    # Pattern 1: battle / givepoke macros
                    mm = macro_re.match(raw_line)
                    if mm:
                        species = mm.group('species').upper()
                        if species in ALL_STATIC_SPECIES:
                            found.append(StaticEncounter(
                                species_const=species,
                                is_legendary=(species in STATIC_LEGENDARY_SPECIES),
                                source_file=full_path,
                                line_index=i,
                                full_line=raw_line.rstrip('\n'),
                                macro_type=mm.group('macro').lower(),
                                label=last_label,
                            ))
                        continue

                    # Pattern 2: db SPECIES in roaming data files only
                    if is_roam_file:
                        rm = roam_re.match(raw_line)
                        if rm:
                            species = rm.group('species').upper()
                            if species in STATIC_LEGENDARY_SPECIES:
                                found.append(StaticEncounter(
                                    species_const=species,
                                    is_legendary=True,
                                    source_file=full_path,
                                    line_index=i,
                                    full_line=raw_line.rstrip('\n'),
                                    macro_type='db_roam',
                                    label=last_label,
                                ))

        self.static_encounters = found
        leg_count = sum(1 for e in found if e.is_legendary)
        std_count = len(found) - leg_count
        self.log(
            f"  Found {len(found)} static encounter(s): "
            f"{leg_count} legendary, {std_count} standard."
        )
        if found:
            seen = {}
            for e in found:
                key = f"{e.species_const} ({e.macro_type})"
                seen[key] = seen.get(key, 0) + 1
            summary = ", ".join(
                f"{k} ×{v}" if v > 1 else k for k, v in sorted(seen.items())
            )
            self.log(f"  Static species: {summary}")

    # -------------------------------------------------------------------------
    # TM/HM compatibility parsing
    # -------------------------------------------------------------------------

    # Regex: matches a "tmhm" macro line, capturing everything after "tmhm".
    # Allows bare "tmhm" (no moves) for Pokémon with empty learnsets.
    _TMHM_LINE_RE = re.compile(r'^\s*tmhm\b(.*)', re.IGNORECASE)

    def _parse_tmhm_compat(self) -> list:
        """
        Parse the ``tmhm`` macro line from each Pokémon's base stats file.

        Crystal Legacy keeps one .asm file per Pokémon under a path like
        ``data/pokemon/base_stats/BULBASAUR.asm``.  The TM/HM learnset is
        expressed as a single ``tmhm TM_XX, HM_YY, ...`` line near the bottom
        of each file.

        Returns a list of TMHMCompatEntry objects — one per Pokémon found.
        """
        # Locate the base stats directory (same search as catch-rate parser)
        base_stats_dir = None
        for candidate in ["data/pokemon/base_stats", "data/base_stats",
                          "data/pokemon/baseStats"]:
            d = os.path.join(self.source_dir, candidate)
            if os.path.isdir(d):
                base_stats_dir = d
                break

        if base_stats_dir is None:
            self.log("  [INFO] Base stats directory not found — TM/HM compatibility unavailable.")
            return []

        results = []
        for fname in sorted(os.listdir(base_stats_dir)):
            if not fname.endswith('.asm'):
                continue
            species_const = fname[:-4].upper()
            if species_const not in POKEMON_CONSTANTS:
                continue

            filepath = os.path.join(base_stats_dir, fname)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                    lines = fh.readlines()
            except OSError:
                continue

            for i, raw in enumerate(lines):
                m = self._TMHM_LINE_RE.match(raw)
                if not m:
                    continue
                # Strip any trailing comment, then parse comma-separated constants
                moves_raw = m.group(1).split(';')[0]
                moves = [mv.strip() for mv in moves_raw.split(',')
                         if mv.strip()]
                results.append(TMHMCompatEntry(
                    species_const=species_const,
                    source_file=filepath,
                    line_index=i,
                    full_line=raw.rstrip('\n'),
                    moves=moves,
                ))
                break   # only one tmhm line per file

        if results:
            self.log(f"  Found TM/HM compatibility for {len(results)} Pokémon.")
        else:
            self.log("  [INFO] No tmhm macro lines found — "
                     "Full HM Compatibility will be unavailable.")
        return results

    # -------------------------------------------------------------------------
    # Wild held item parsing
    # -------------------------------------------------------------------------

    # Candidate relative paths for wild held item tables
    _HELD_ITEM_FILE_CANDIDATES = [
        "data/wild/items.asm",
        "data/wild/held_items.asm",
        "data/items/held_items.asm",
        "data/pokemon/held_items.asm",
        "data/held_items.asm",
    ]

    def _parse_wild_held_items(self) -> list:
        """
        Parse wild Pokémon held-item entries.

        Crystal format (one per Pokémon):
            db SPECIES, COMMON_ITEM, RARE_ITEM

        The file terminates with ``db -1`` (or similar sentinel).
        Returns a list of WildHeldItemEntry objects.
        """
        # Locate the file
        filepath = None
        for rel in self._HELD_ITEM_FILE_CANDIDATES:
            candidate = os.path.join(self.source_dir, rel)
            if os.path.exists(candidate):
                filepath = candidate
                break

        if filepath is None:
            self.log("  [INFO] Wild held item file not found — held item randomization unavailable.")
            return []

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except Exception as exc:
            self.log(f"  [WARN] Could not read held items file: {exc}")
            return []

        # Patterns:
        #   db SPECIES, ITEM          — single item (common = rare)
        #   db SPECIES, COMMON, RARE  — separate common and rare
        two_items_re  = re.compile(
            r'^\s*db\s+([A-Z][A-Z0-9_]*)\s*,\s*([A-Z_][A-Z0-9_]*)\s*,\s*([A-Z_][A-Z0-9_]*)',
            re.IGNORECASE,
        )
        one_item_re   = re.compile(
            r'^\s*db\s+([A-Z][A-Z0-9_]*)\s*,\s*([A-Z_][A-Z0-9_]*)',
            re.IGNORECASE,
        )

        results = []
        for i, raw in enumerate(lines):
            # Strip comments
            line = re.sub(r';.*$', '', raw).strip()
            if not line:
                continue
            # Sentinel: db -1
            if re.match(r'db\s+-1', line):
                break

            m2 = two_items_re.match(raw)
            m1 = one_item_re.match(raw)
            if m2:
                species = m2.group(1).upper()
                common  = m2.group(2).upper()
                rare    = m2.group(3).upper()
            elif m1:
                species = m1.group(1).upper()
                common  = m1.group(2).upper()
                rare    = common
            else:
                continue

            if species not in POKEMON_CONSTANTS:
                continue

            results.append(WildHeldItemEntry(
                species_const=species,
                common_item=common,
                rare_item=rare,
                source_file=filepath,
                line_index=i,
                full_line=raw.rstrip('\n'),
            ))

        if results:
            self.log(f"  Found {len(results)} wild held item entries in {os.path.basename(filepath)}.")
        else:
            self.log(f"  Wild held item file found but no entries parsed — held item randomization unavailable.")
        return results

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_wild_species(self) -> set:
        """Return set of all species IDs currently in wild encounters."""
        ids = set()
        for grp in self.wild_encounters:
            for slot in grp.slots:
                ids.add(slot.species_id)
        return ids

    def get_trainer_species(self) -> set:
        """Return set of all species IDs currently in trainer parties."""
        ids = set()
        for tr in self.trainers:
            for poke in tr.party:
                ids.add(poke.species_id)
        return ids

    # -------------------------------------------------------------------------
    # Field item parsing
    # -------------------------------------------------------------------------

    # Matches:  finditem ITEM_CONST   or   itemball ITEM_CONST
    _VISIBLE_ITEM_RE = re.compile(
        r'^\s*(?:finditem|itemball)\s+([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    # Matches:  hiddenitem ITEM_CONST, ...   (rest of args not needed for replacement)
    _HIDDEN_ITEM_RE = re.compile(
        r'^\s*hiddenitem\s+([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    # Item constants that are definitely NOT items (skip false positives)
    _ITEM_MACRO_SKIP = {
        "NOPOKEMON", "NONE",
    }

    def _parse_field_items(self) -> list:
        """
        Scan the entire source tree for field item macros:
          - finditem / itemball  → visible item (Pokéball sprite)
          - hiddenitem           → hidden item (Itemfinder)

        Returns a list of FieldItemEntry objects (one per macro occurrence).
        Skips key items that must never be replaced.
        """
        from item_data import FIELD_ITEMS_SKIP

        results = []
        script_dirs = [
            os.path.join(self.source_dir, "maps"),
            os.path.join(self.source_dir, "engine", "items"),
            os.path.join(self.source_dir, "data", "items"),
            os.path.join(self.source_dir, "scripts"),
        ]

        # Collect all .asm files under candidate dirs, plus root-level data/maps
        asm_files = []
        for base in script_dirs:
            if os.path.isdir(base):
                for root, _dirs, files in os.walk(base):
                    for fname in files:
                        if fname.endswith(".asm"):
                            asm_files.append(os.path.join(root, fname))

        # Also scan maps/ at top level if it exists (Crystal uses maps/*.asm)
        maps_root = os.path.join(self.source_dir, "maps")
        if not os.path.isdir(maps_root):
            # Some decompilations put map scripts under data/
            alt_maps = os.path.join(self.source_dir, "data", "maps")
            if os.path.isdir(alt_maps):
                for root, _dirs, files in os.walk(alt_maps):
                    for fname in files:
                        if fname.endswith(".asm"):
                            fp = os.path.join(root, fname)
                            if fp not in asm_files:
                                asm_files.append(fp)

        if not asm_files:
            self.log("  [WARN] No script directories found — field item parsing skipped.")
            return results

        vis_count = 0
        hid_count = 0

        for filepath in asm_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue

            for i, raw in enumerate(lines):
                # Strip inline comment for matching (but keep original for storage)
                line_nc = re.sub(r';.*$', '', raw)

                mv = self._VISIBLE_ITEM_RE.match(line_nc)
                if mv:
                    item = mv.group(1).upper()
                    if item in self._ITEM_MACRO_SKIP or item in FIELD_ITEMS_SKIP:
                        continue
                    results.append(FieldItemEntry(
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
                    if item in self._ITEM_MACRO_SKIP or item in FIELD_ITEMS_SKIP:
                        continue
                    results.append(FieldItemEntry(
                        item_const=item,
                        item_type="hidden",
                        source_file=filepath,
                        line_index=i,
                        full_line=raw,
                    ))
                    hid_count += 1

        self.log(f"  Field items: {vis_count} visible, {hid_count} hidden across {len(asm_files)} script files.")
        return results
