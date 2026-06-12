"""
Pokemon Emerald Legacy Randomizer - Source Parser

Parses Emerald Legacy (GBA decomp) source files:
  - Wild encounters  : src/data/wild_encounters.json  (JSON)
  - Trainer parties  : src/data/trainer_parties.h     (C header)
  - Starters        : src/starter_choose.c            (C source)
  - Field items     : data/maps/*/scripts.inc          (finditem ITEM_X)
  - Static encounters: data/maps/*/scripts.inc         (setwildbattle)
  - TM/HM learnsets : src/data/pokemon/tmhm_learnsets.h
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from constants_emerald import (
    ALL_SPECIES_CONSTS, SPECIES_NUMBERS,
    SPECIES_BST, SPECIES_TYPES,
    WILD_ENCOUNTERS_FILE, TRAINER_PARTIES_FILE, STARTERS_FILE,
    TMHM_LEARNSETS_FILE, MAPS_DIR, HM_FIELD_NAMES,
    SPECIES_INFO_FILE, EVOLUTION_FILE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StarterSlot:
    """One starter slot in sStarterMon[]."""
    index: int           # 0, 1, or 2
    species: str         # SPECIES_X constant (with prefix)
    line_index: int      # 0-based line number in the starters file
    original_line: str   # verbatim source line


@dataclass
class TrainerMon:
    """One Pokémon in a trainer party."""
    species: str                   # SPECIES_X constant
    level: int
    iv: int = 0
    held_item: Optional[str] = None
    moves: list = field(default_factory=list)   # list of MOVE_X strings


@dataclass
class TrainerParty:
    """One sParty_XXX array in trainer_parties.h."""
    party_label: str               # e.g. "sParty_Sawyer1"
    mons: list                     # list of TrainerMon
    # Line numbers of each .species = SPECIES_X line (one per mon, in order)
    species_line_numbers: list     # list of int (0-based)
    source_file: str               # absolute path


@dataclass
class WildHeldItemEntry:
    """One .itemCommon / .itemRare held-item slot in species_info.h."""
    species: str         # SPECIES_X constant
    slot: str            # "common" or "rare"
    item: str            # current ITEM_X constant
    source_file: str     # absolute path
    line_index: int      # 0-based line number of the .itemCommon/.itemRare line


@dataclass
class FieldItem:
    """One field item occurrence.

    kind "finditem": a `finditem ITEM_X` line in a .inc script
         (item balls live centrally in data/scripts/item_ball_scripts.inc).
    kind "hidden":   an `"item": "ITEM_X"` line of a hidden_item bg_event
         in a map.json file."""
    item_const: str      # e.g. "ITEM_POTION"
    source_file: str     # absolute path to the .inc / map.json file
    line_index: int      # 0-based line index
    kind: str = "finditem"


@dataclass
class StaticEncounter:
    """One setwildbattle SPECIES, LEVEL occurrence in a scripts.inc file."""
    species: str         # SPECIES_X constant
    level: int
    source_file: str
    line_index: int
    # Companion `playmoncry SPECIES_X` line just above the battle (or -1).
    # Patched together with the species so the encounter cry matches.
    cry_line: int = -1


@dataclass
class TMHMEntry:
    """TM/HM learnset entry for one species (used for full-HM-compat patch)."""
    species: str         # SPECIES_X constant
    hm_fields: set       # set of HM field names that are TRUE
    # Location in source
    source_file: str
    block_start: int     # line index of "[SPECIES_X] = {"
    block_end: int       # line index of closing "} },"


@dataclass
class EmeraldInGameTrade:
    """
    One in-game trade from sIngameTrades[] in src/data/trade.h.

    Emerald struct fields used by the randomizer:
        .species          = SPECIES_X   — Pokémon player receives
        .requestedSpecies = SPECIES_X   — Pokémon player gives
        .nickname         = _("NAME")   — nickname of received Pokémon
        .otName           = _("NAME")   — OT of received Pokémon
        .ivs              = {h,a,d,sa,sd,sp}
        .heldItem         = ITEM_X
    """
    source_file: str
    trade_index: int         # index in sIngameTrades[] (for logging)
    trade_label: str         # e.g. "INGAME_TRADE_SEEDOT"

    # Core fields
    species: str             # what player receives
    species_line: int        # 0-based line in source_file
    species_full_line: str

    requested_species: str   # what player gives
    req_line: int
    req_full_line: str

    # Optional fields (line = -1 if not found)
    nickname: str = ""
    nickname_line: int = -1
    nickname_full_line: str = ""

    ot_name: str = ""
    ot_line: int = -1
    ot_full_line: str = ""

    ivs_raw: str = ""        # e.g. "{5, 4, 5, 4, 4, 4}"
    ivs_line: int = -1
    ivs_full_line: str = ""

    held_item: str = "ITEM_NONE"
    held_item_line: int = -1
    held_item_full_line: str = ""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class EmeraldLegacyParser:

    def __init__(self, src_dir: str, log_fn=None):
        self.src_dir   = src_dir
        self._log      = log_fn or (lambda msg: None)

        # Parsed data
        self.wild_json: dict        = {}   # raw parsed JSON (will be modified in-place copy)
        self.trainer_parties: list  = []   # list of TrainerParty
        self.starters: list         = []   # list of StarterSlot (3 entries)
        self.field_items: list      = []   # list of FieldItem
        self.static_encounters: list= []   # list of StaticEncounter
        self.tmhm_compat: list      = []   # list of TMHMEntry
        self.trades: list           = []   # list of EmeraldInGameTrade
        self.wild_held_items: list  = []   # list of WildHeldItemEntry
        self.evolution_to: dict     = {}   # species_const -> first evolution target const

        # Species metadata (from constants)
        self.species_consts: list   = list(ALL_SPECIES_CONSTS)
        self.species_bst: dict      = dict(SPECIES_BST)
        self.species_types: dict    = dict(SPECIES_TYPES)
        self.species_numbers: dict  = dict(SPECIES_NUMBERS)

    def _path(self, rel: str) -> str:
        return os.path.join(self.src_dir, rel)

    def _read(self, rel: str) -> Optional[str]:
        p = self._path(rel)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def parse_all(self) -> bool:
        """Parse all supported files. Returns True if starters were found."""
        self._log("  Parsing wild encounters (JSON)...")
        self._parse_wild_encounters()

        self._log("  Parsing trainer parties (C header)...")
        self._parse_trainer_parties()

        self._log("  Scanning map scripts for field items and statics...")
        self._parse_map_scripts()

        self._log("  Parsing TM/HM learnsets...")
        self._parse_tmhm_learnsets()

        self._log("  Parsing starters...")
        found = self._parse_starters()

        self._log("  Parsing in-game trades...")
        self._parse_trades()

        self._log("  Parsing wild held items...")
        self._parse_wild_held_items()

        self._log("  Parsing evolution chains...")
        self._parse_evolutions()

        return found

    # -----------------------------------------------------------------------
    # Wild encounters
    # -----------------------------------------------------------------------

    def _parse_wild_encounters(self):
        p = self._path(WILD_ENCOUNTERS_FILE)
        try:
            with open(p, "r", encoding="utf-8") as f:
                self.wild_json = json.load(f)
            # Count encounter entries for logging
            groups = self.wild_json.get("wild_encounter_groups", [])
            total = sum(len(g.get("encounters", [])) for g in groups)
            self._log(f"    Loaded {total} wild encounter area(s)")
        except FileNotFoundError:
            self._log(f"    [WARN] Wild encounters JSON not found: {p}")
        except json.JSONDecodeError as e:
            self._log(f"    [WARN] Wild encounters JSON parse error: {e}")

    # -----------------------------------------------------------------------
    # Trainer parties
    # -----------------------------------------------------------------------

    def _parse_trainer_parties(self):
        text = self._read(TRAINER_PARTIES_FILE)
        if text is None:
            self._log(f"    [WARN] Trainer parties file not found: {TRAINER_PARTIES_FILE}")
            return

        abs_path = self._path(TRAINER_PARTIES_FILE)
        lines    = text.splitlines()

        # Match party array declarations:
        #   static const struct TrainerMon sParty_Xyz[] = {
        party_decl_re = re.compile(
            r"^static const struct TrainerMon\w*\s+(\w+)\[\]\s*=\s*\{"
        )
        species_re    = re.compile(r"^\s*\.species\s*=\s*(SPECIES_\w+)\s*,")
        level_re      = re.compile(r"^\s*\.lvl\s*=\s*(\d+)\s*,")
        iv_re         = re.compile(r"^\s*\.iv\s*=\s*(\d+)\s*,")
        item_re       = re.compile(r"^\s*\.heldItem\s*=\s*(ITEM_\w+)\s*,")
        moves_re      = re.compile(r"^\s*\.moves\s*=\s*\{([^}]+)\}")

        i = 0
        while i < len(lines):
            m = party_decl_re.match(lines[i])
            if m:
                label      = m.group(1)
                mons       = []
                sp_lines   = []
                cur_species = None
                cur_level   = 5
                cur_iv      = 0
                cur_item    = None
                cur_moves   = []
                brace_depth = 1   # already opened one {
                j = i + 1

                while j < len(lines) and brace_depth > 0:
                    ln = lines[j]
                    brace_depth += ln.count("{") - ln.count("}")

                    ms = species_re.match(ln)
                    if ms:
                        cur_species = ms.group(1)
                        sp_lines.append(j)

                    ml = level_re.match(ln)
                    if ml:
                        cur_level = int(ml.group(1))

                    mi = iv_re.match(ln)
                    if mi:
                        cur_iv = int(mi.group(1))

                    mh = item_re.match(ln)
                    if mh:
                        cur_item = mh.group(1)

                    mm = moves_re.match(ln)
                    if mm:
                        raw = mm.group(1)
                        cur_moves = [m2.strip() for m2 in raw.split(",") if m2.strip()]

                    # Each } at depth 1 ends a mon struct
                    if brace_depth == 1 and ln.strip().startswith("}") and cur_species:
                        mons.append(TrainerMon(
                            species=cur_species,
                            level=cur_level,
                            iv=cur_iv,
                            held_item=cur_item,
                            moves=list(cur_moves),
                        ))
                        cur_species = None
                        cur_level   = 5
                        cur_iv      = 0
                        cur_item    = None
                        cur_moves   = []

                    j += 1

                if mons:
                    self.trainer_parties.append(TrainerParty(
                        party_label=label,
                        mons=mons,
                        species_line_numbers=sp_lines,
                        source_file=abs_path,
                    ))
                i = j
            else:
                i += 1

        self._log(f"    Found {len(self.trainer_parties)} trainer part(ies)")

    # -----------------------------------------------------------------------
    # Starters
    # -----------------------------------------------------------------------

    def _parse_starters(self) -> bool:
        text = self._read(STARTERS_FILE)
        if text is None:
            self._log(f"    [WARN] Starters file not found: {STARTERS_FILE}")
            return False

        abs_path = self._path(STARTERS_FILE)
        lines    = text.splitlines()

        # Look for:  SPECIES_TREECKO, / SPECIES_TORCHIC, / SPECIES_MUDKIP,
        # inside sStarterMon[] = { ... }
        in_array = False
        array_re = re.compile(r"sStarterMon\[")
        species_re = re.compile(r"^\s*(SPECIES_\w+)\s*,")
        idx = 0

        for li, ln in enumerate(lines):
            if not in_array and array_re.search(ln):
                in_array = True
                continue
            if in_array:
                if ln.strip().startswith("};"):
                    break
                ms = species_re.match(ln)
                if ms:
                    self.starters.append(StarterSlot(
                        index=idx,
                        species=ms.group(1),
                        line_index=li,
                        original_line=ln,
                    ))
                    idx += 1

        if len(self.starters) >= 3:
            self._log(f"    Starters: {', '.join(s.species for s in self.starters[:3])}")
            return True
        else:
            self._log(f"    [WARN] Only found {len(self.starters)} starter(s) (expected 3)")
            return len(self.starters) > 0

    # -----------------------------------------------------------------------
    # Map scripts: field items + static encounters
    # -----------------------------------------------------------------------

    _FINDITEM_RE = re.compile(r"^\s*finditem\s+(ITEM_\w+)")
    _SETWILD_RE  = re.compile(r"^\s*setwildbattle\s+(SPECIES_\w+)\s*,\s*(\d+)")
    _MONCRY_RE   = re.compile(r"^\s*playmoncry\s+(SPECIES_\w+)")

    def _scan_script_lines(self, path: str, lines: list):
        """Collect finditem field items and setwildbattle statics from one
        event-script file. For each static, also record the companion
        `playmoncry SAME_SPECIES` line just above it (so the encounter cry
        can be patched to match the randomized species)."""
        for li, ln in enumerate(lines):
            mf = self._FINDITEM_RE.match(ln)
            if mf:
                self.field_items.append(FieldItem(
                    item_const=mf.group(1),
                    source_file=path,
                    line_index=li,
                ))
            ms = self._SETWILD_RE.match(ln)
            if ms:
                species  = ms.group(1)
                cry_line = -1
                for back in range(1, 9):
                    if li - back < 0:
                        break
                    mc = self._MONCRY_RE.match(lines[li - back])
                    if mc and mc.group(1) == species:
                        cry_line = li - back
                        break
                self.static_encounters.append(StaticEncounter(
                    species=species,
                    level=int(ms.group(2)),
                    source_file=path,
                    line_index=li,
                    cry_line=cry_line,
                ))

    def _parse_map_scripts(self):
        maps_dir = self._path(MAPS_DIR)
        if not os.path.isdir(maps_dir):
            self._log(f"    [WARN] Maps directory not found: {maps_dir}")
            return

        # Hidden items: `"item": "ITEM_X",` lines inside hidden_item bg_events.
        # In map.json only hidden-item events carry an "item" key.
        hidden_re = re.compile(r'^\s*"item":\s*"(ITEM_\w+)"')

        # Shared event scripts (item balls, Kecleon roadblocks, …) live in
        # data/scripts/*.inc rather than in any single map's scripts.inc.
        scripts_dir = self._path(os.path.join("data", "scripts"))
        if os.path.isdir(scripts_dir):
            for fn in sorted(os.listdir(scripts_dir)):
                if not fn.endswith(".inc"):
                    continue
                shared_f = os.path.join(scripts_dir, fn)
                try:
                    with open(shared_f, "r", encoding="utf-8", errors="replace") as f:
                        self._scan_script_lines(shared_f, f.readlines())
                except OSError:
                    continue
        else:
            self._log(f"    [WARN] Shared scripts directory not found: {scripts_dir}")

        hidden_count = 0
        for map_name in sorted(os.listdir(maps_dir)):
            map_path  = os.path.join(maps_dir, map_name)

            # finditem / setwildbattle in the per-map scripts.inc
            script_f  = os.path.join(map_path, "scripts.inc")
            if os.path.isfile(script_f):
                try:
                    with open(script_f, "r", encoding="utf-8", errors="replace") as f:
                        self._scan_script_lines(script_f, f.readlines())
                except OSError:
                    pass

            # hidden items in map.json
            json_f = os.path.join(map_path, "map.json")
            if os.path.isfile(json_f):
                try:
                    with open(json_f, "r", encoding="utf-8", errors="replace") as f:
                        json_lines = f.readlines()
                except OSError:
                    continue
                for li, ln in enumerate(json_lines):
                    mh = hidden_re.match(ln)
                    if mh:
                        self.field_items.append(FieldItem(
                            item_const=mh.group(1),
                            source_file=json_f,
                            line_index=li,
                            kind="hidden",
                        ))
                        hidden_count += 1

        self._log(f"    Found {len(self.field_items)} field item(s) "
                  f"({hidden_count} hidden), "
                  f"{len(self.static_encounters)} static encounter(s)")

    # -----------------------------------------------------------------------
    # TM/HM learnsets (for full-HM-compat patch)
    # -----------------------------------------------------------------------

    def _parse_tmhm_learnsets(self):
        text = self._read(TMHM_LEARNSETS_FILE)
        if text is None:
            self._log(f"    [WARN] TM/HM learnsets file not found: {TMHM_LEARNSETS_FILE}")
            return

        abs_path = self._path(TMHM_LEARNSETS_FILE)
        lines    = text.splitlines()

        # Match: [SPECIES_X] = { .learnset = {
        block_start_re = re.compile(r"^\s*\[(SPECIES_\w+)\]\s*=\s*\{")
        hm_field_re    = re.compile(r"^\s*\.(" + "|".join(HM_FIELD_NAMES) + r")\s*=\s*TRUE")
        # End of a species block: "} },"
        block_end_re   = re.compile(r"^\s*\}\s*\}\s*,")

        i = 0
        while i < len(lines):
            ms = block_start_re.match(lines[i])
            if ms:
                species     = ms.group(1)
                block_start = i
                hm_set      = set()
                j = i + 1
                while j < len(lines):
                    mh = hm_field_re.match(lines[j])
                    if mh:
                        hm_set.add(mh.group(1))
                    if block_end_re.match(lines[j]):
                        self.tmhm_compat.append(TMHMEntry(
                            species=species,
                            hm_fields=hm_set,
                            source_file=abs_path,
                            block_start=block_start,
                            block_end=j,
                        ))
                        i = j + 1
                        break
                    j += 1
                else:
                    i = j
            else:
                i += 1

        self._log(f"    Found {len(self.tmhm_compat)} TM/HM learnset entries")

    # -----------------------------------------------------------------------
    # Wild held items (.itemCommon / .itemRare in species_info.h)
    # -----------------------------------------------------------------------

    def _parse_wild_held_items(self):
        """
        Collect every .itemCommon / .itemRare slot that currently holds a
        non-NONE item, tracked to its species block.  Macro-definition lines
        (which end in a backslash line-continuation) are skipped.
        """
        text = self._read(SPECIES_INFO_FILE)
        if text is None:
            self._log(f"    [WARN] species_info file not found: {SPECIES_INFO_FILE}")
            return

        abs_path = self._path(SPECIES_INFO_FILE)
        lines    = text.splitlines()

        block_start_re = re.compile(r"^\s*\[(SPECIES_\w+)\]\s*=")
        item_re        = re.compile(r"^\s*\.item(Common|Rare)\s*=\s*(ITEM_\w+)\s*,")

        current = None
        for idx, line in enumerate(lines):
            ms = block_start_re.match(line)
            if ms:
                current = ms.group(1)
                continue
            mi = item_re.match(line)
            if mi and current and "\\" not in line:
                slot = "common" if mi.group(1) == "Common" else "rare"
                item = mi.group(2)
                if item != "ITEM_NONE":
                    self.wild_held_items.append(WildHeldItemEntry(
                        species=current, slot=slot, item=item,
                        source_file=abs_path, line_index=idx,
                    ))

        self._log(f"    Found {len(self.wild_held_items)} wild held item slot(s)")

    # -----------------------------------------------------------------------
    # Evolution chains (src/data/pokemon/evolution.h)
    # -----------------------------------------------------------------------

    def _parse_evolutions(self):
        """
        Build evolution_to: species_const -> first evolution target const.
        Handles entries like:
            [SPECIES_BULBASAUR]  = {{EVO_LEVEL, 16, SPECIES_IVYSAUR}},
        Only the first evolution target is recorded (sufficient for walking a
        linear starter chain stage-by-stage).
        """
        text = self._read(EVOLUTION_FILE)
        if text is None:
            self._log(f"    [WARN] evolution file not found: {EVOLUTION_FILE}")
            return

        entry_re = re.compile(
            r"\[(SPECIES_\w+)\]\s*=\s*\{\{\s*\w+\s*,\s*[^,]+,\s*(SPECIES_\w+)"
        )
        for m in entry_re.finditer(text):
            src_sp, tgt_sp = m.group(1), m.group(2)
            if src_sp not in self.evolution_to:
                self.evolution_to[src_sp] = tgt_sp

        self._log(f"    Found {len(self.evolution_to)} evolution link(s)")

    # -----------------------------------------------------------------------
    # In-game trades (src/data/trade.h — sIngameTrades[] array)
    # -----------------------------------------------------------------------

    # Relative path within the source tree
    TRADE_DATA_FILE = os.path.join("src", "data", "trade.h")

    def _parse_trades(self):
        """
        Parse the sIngameTrades[] C array in src/data/trade.h.

        Each entry looks like:
            [INGAME_TRADE_SEEDOT] =
            {
                .nickname         = _("DOTS"),
                .species          = SPECIES_SEEDOT,
                .requestedSpecies = SPECIES_RALTS,
                .otName           = _("KOBE"),
                .ivs              = {5, 4, 5, 4, 4, 4},
                .heldItem         = ITEM_CHESTO_BERRY,
                ...
            },
        """
        abs_path = self._path(self.TRADE_DATA_FILE)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            self._log(f"    [WARN] Trade data file not found: {abs_path}")
            return

        # Locate the sIngameTrades array
        array_start = -1
        for i, line in enumerate(lines):
            if re.search(r'sIngameTrades\s*\[\s*\]', line):
                array_start = i
                break
        if array_start < 0:
            self._log("    [WARN] sIngameTrades[] not found in trade.h")
            return

        # Walk through entries: each entry starts with [INGAME_TRADE_XXX] =
        LABEL_RE      = re.compile(r'\[(\w+)\]\s*=')
        SPECIES_RE    = re.compile(r'\.species\s*=\s*(SPECIES_\w+)')
        REQ_RE        = re.compile(r'\.requestedSpecies\s*=\s*(SPECIES_\w+)')
        NICK_RE       = re.compile(r'\.nickname\s*=\s*_\("([^"]*)"\)')
        OT_RE         = re.compile(r'\.otName\s*=\s*_\("([^"]*)"\)')
        IVS_RE        = re.compile(r'\.ivs\s*=\s*(\{[^}]+\})')
        ITEM_RE       = re.compile(r'\.heldItem\s*=\s*(ITEM_\w+)')

        trade_index = 0
        i = array_start
        n = len(lines)

        while i < n:
            lm = LABEL_RE.search(lines[i])
            if not lm:
                i += 1
                continue

            label = lm.group(1)
            # Scan ahead for the closing '}, ' of this entry
            entry_lines = {}   # field_name → (line_index, full_line_text)
            brace_depth = 0
            j = i
            found_open = False
            while j < n:
                ln = lines[j]
                if '{' in ln:
                    brace_depth += ln.count('{')
                    found_open = True
                if '}' in ln:
                    brace_depth -= ln.count('}')

                for name, rx in (('species', SPECIES_RE), ('requested', REQ_RE),
                                  ('nickname', NICK_RE), ('ot', OT_RE),
                                  ('ivs', IVS_RE), ('item', ITEM_RE)):
                    if name not in entry_lines:
                        m = rx.search(ln)
                        if m:
                            entry_lines[name] = (j, ln.rstrip('\n'), m.group(1))

                if found_open and brace_depth <= 0:
                    break
                j += 1

            # Only add entries that have both required species fields
            if 'species' in entry_lines and 'requested' in entry_lines:
                sp_line, sp_full, sp_val = entry_lines['species']
                rq_line, rq_full, rq_val = entry_lines['requested']

                trade = EmeraldInGameTrade(
                    source_file=abs_path,
                    trade_index=trade_index,
                    trade_label=label,
                    species=sp_val,
                    species_line=sp_line,
                    species_full_line=sp_full,
                    requested_species=rq_val,
                    req_line=rq_line,
                    req_full_line=rq_full,
                )
                if 'nickname' in entry_lines:
                    trade.nickname_line, trade.nickname_full_line, trade.nickname = entry_lines['nickname']
                if 'ot' in entry_lines:
                    trade.ot_line, trade.ot_full_line, trade.ot_name = entry_lines['ot']
                if 'ivs' in entry_lines:
                    trade.ivs_line, trade.ivs_full_line, trade.ivs_raw = entry_lines['ivs']
                if 'item' in entry_lines:
                    trade.held_item_line, trade.held_item_full_line, trade.held_item = entry_lines['item']

                self.trades.append(trade)
                trade_index += 1

            i = j + 1

        self._log(f"    Found {len(self.trades)} in-game trade(s)")
