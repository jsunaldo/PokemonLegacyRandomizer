"""
Pokemon Emerald Legacy Randomizer — ASM/C/JSON Source Parser

Parses Emerald Legacy (GBA / pret disassembly) source files to extract:
  - Wild encounters (land, water, rock_smash, fishing) from JSON
  - Trainer parties from C header (src/data/trainer_parties.h)
  - Trainer class mapping from C header (src/data/trainers.h)
  - Starter Pokémon from C source (src/starter_choose.c)
  - Field items from ASM script (data/scripts/item_ball_scripts.inc)
  - Static encounters from ASM scripts (data/scripts/*.inc)
  - Species constants + BST + types from C headers
"""

import copy
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from constants_emerald import (
    EMERALD_SPECIES_FILE, EMERALD_ITEMS_FILE, EMERALD_SPECIES_INFO_FILE,
    EMERALD_WILD_FILE, EMERALD_PARTIES_FILE, EMERALD_TRAINERS_FILE,
    EMERALD_STARTER_FILE, EMERALD_ITEM_SCRIPTS_FILE, EMERALD_SCRIPTS_DIR,
    EMERALD_LEGENDARY_SPECIES, EMERALD_SPECIES_SKIP, EMERALD_UNOWN_PREFIX,
    EMERALD_WILD_TYPES, EMERALD_FIELD_ITEMS_SKIP,
    EMERALD_BOSS_CLASS_KEYWORDS,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmeraldWildSlot:
    """One slot in a wild encounter table (any type)."""
    species: str        # "SPECIES_WURMPLE"
    min_level: int
    max_level: int
    enc_type: str       # "land_mons" | "water_mons" | "rock_smash_mons" | "fishing_mons"
    map_name: str       # "MAP_ROUTE101"
    group_idx: int      # index in wild_encounter_groups list
    encounter_idx: int  # index in encounters list
    slot_idx: int       # index in mons list


@dataclass
class EmeraldTrainerMon:
    """One Pokémon in a trainer party."""
    species: str        # "SPECIES_GRAVELER"
    level: int
    party_name: str     # "sParty_Sawyer1"
    mon_idx: int        # 0-based index within party
    line_index: int     # line in trainer_parties.h with .species = ...
    full_line: str


@dataclass
class EmeraldTrainerParty:
    """One trainer party array."""
    party_name: str     # "sParty_Sawyer1"
    trainer_class: str  # "TRAINER_CLASS_HIKER" (from trainers.h lookup)
    is_boss: bool
    mons: list          # list[EmeraldTrainerMon]


@dataclass
class EmeraldStarterLocation:
    """One starter species reference in starter_choose.c."""
    species: str        # "SPECIES_TREECKO"
    idx: int            # 0, 1, or 2
    line_index: int
    full_line: str


@dataclass
class EmeraldFieldItem:
    """One field item pickup (finditem macro in item_ball_scripts.inc)."""
    item_const: str     # "ITEM_RARE_CANDY"
    source_file: str
    line_index: int
    full_line: str


@dataclass
class EmeraldStaticEncounter:
    """One static encounter or gift Pokémon found in a script file."""
    species: str        # "SPECIES_KECLEON"
    level: int          # 0 for giveegg
    macro_type: str     # "setwildbattle" | "giveegg"
    is_legendary: bool
    source_file: str
    line_index: int
    full_line: str
    label: str          # nearest preceding label


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class EmeraldLegacyParser:
    def __init__(self, source_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.log = log_fn or print

        # Parsed data
        self.wild_json: dict          = {}    # full parsed wild_encounters.json
        self.wild_slots: list         = []    # list[EmeraldWildSlot] (flat)
        self.trainer_parties: list    = []    # list[EmeraldTrainerParty]
        self.starters: list           = []    # list[EmeraldStarterLocation]
        self.field_items: list        = []    # list[EmeraldFieldItem]
        self.static_encounters: list  = []    # list[EmeraldStaticEncounter]

        # Species metadata (populated by _parse_species_data)
        self.species_consts: list     = []    # ordered list of valid SPECIES_* strings
        self.species_bst: dict        = {}    # SPECIES_* → int BST
        self.species_types: dict      = {}    # SPECIES_* → [type1, type2]
        self.species_numbers: dict    = {}    # SPECIES_* → int dex number
        self.all_items: list          = []    # list of ITEM_* const strings

    # ------------------------------------------------------------------
    def parse_all(self):
        """Run all parsers. Returns True if starters were found."""
        self.log("Parsing species constants and BST data...")
        self._parse_species_data()

        self.log("Parsing item constants...")
        self._parse_item_consts()

        self.log("Parsing wild encounters...")
        self._parse_wild_encounters()

        self.log("Parsing trainer parties...")
        self._parse_trainer_parties()

        self.log("Parsing starters...")
        self._parse_starters()

        self.log("Scanning field items...")
        self._parse_field_items()

        self.log("Scanning static encounters...")
        self._parse_static_encounters()

        land   = sum(1 for s in self.wild_slots if s.enc_type == 'land_mons')
        water  = sum(1 for s in self.wild_slots if s.enc_type == 'water_mons')
        rsmash = sum(1 for s in self.wild_slots if s.enc_type == 'rock_smash_mons')
        fish   = sum(1 for s in self.wild_slots if s.enc_type == 'fishing_mons')
        leg    = sum(1 for e in self.static_encounters if e.is_legendary)
        std    = sum(1 for e in self.static_encounters if not e.is_legendary)
        fi_count = len(self.field_items)

        self.log(
            f"Parse complete: "
            f"{land} land + {water} water + {rsmash} rock smash + {fish} fishing wild slots, "
            f"{len(self.trainer_parties)} trainer parties, "
            f"{len(self.starters)} starter ref(s), "
            f"{fi_count} field item(s), "
            f"{len(self.static_encounters)} static encounter(s) ({leg} legendary, {std} standard), "
            f"{len(self.species_consts)} species in pool."
        )
        return len(self.starters) > 0

    # ------------------------------------------------------------------
    # Species constants, BST, and type data
    # ------------------------------------------------------------------

    _SPECIES_DEFINE_RE = re.compile(
        r'^#define\s+(SPECIES_\w+)\s+(\d+)', re.MULTILINE
    )
    _BST_BLOCK_RE = re.compile(
        r'\[(?P<spec>SPECIES_\w+)\]\s*=\s*\{(?P<block>[^}]+?)\}'
        r'(?=\s*(?:,|\[|//|/\*))',
        re.DOTALL,
    )
    _STAT_RE = {
        'hp':   re.compile(r'\.baseHP\s*=\s*(\d+)'),
        'atk':  re.compile(r'\.baseAttack\s*=\s*(\d+)'),
        'def':  re.compile(r'\.baseDefense\s*=\s*(\d+)'),
        'spd':  re.compile(r'\.baseSpeed\s*=\s*(\d+)'),
        'spa':  re.compile(r'\.baseSpAttack\s*=\s*(\d+)'),
        'spd2': re.compile(r'\.baseSpDefense\s*=\s*(\d+)'),
    }
    _TYPES_RE = re.compile(
        r'\.types\s*=\s*\{\s*(TYPE_\w+)\s*,\s*(TYPE_\w+)\s*\}'
    )

    def _parse_species_data(self):
        spec_path = os.path.join(self.source_dir, EMERALD_SPECIES_FILE)
        info_path = os.path.join(self.source_dir, EMERALD_SPECIES_INFO_FILE)

        # --- Step 1: read all SPECIES_* → int from species.h ---
        id_map = {}   # SPECIES_* → int
        if os.path.isfile(spec_path):
            with open(spec_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            for m in self._SPECIES_DEFINE_RE.finditer(text):
                name, val = m.group(1), int(m.group(2))
                id_map[name] = val
        else:
            self.log(f"  [WARN] species.h not found: {EMERALD_SPECIES_FILE}")

        # Build ordered, filtered list of valid species consts
        valid = []
        for name in sorted(id_map, key=lambda n: id_map[n]):
            if name in EMERALD_SPECIES_SKIP:
                continue
            if name.startswith(EMERALD_UNOWN_PREFIX):
                continue
            if id_map[name] == 0:
                continue
            valid.append(name)
        self.species_consts = valid

        # Build species_numbers dict: SPECIES_* → dex number (int)
        self.species_numbers = {
            name: num for name, num in id_map.items()
            if name not in EMERALD_SPECIES_SKIP
            and not name.startswith(EMERALD_UNOWN_PREFIX)
            and num > 0
        }
        self.log(f"  Species constants: {len(valid)} valid entries.")

        # --- Step 2: parse BST and types from species_info.h ---
        if not os.path.isfile(info_path):
            self.log(f"  [WARN] species_info.h not found: {EMERALD_SPECIES_INFO_FILE}")
            return

        with open(info_path, 'r', encoding='utf-8', errors='replace') as f:
            info_text = f.read()

        bst_map = {}
        type_map = {}

        # Find each [SPECIES_*] = { ... } block
        # We scan line by line to find [SPECIES_X] = then collect until matching }
        lines = info_text.split('\n')
        i = 0
        spec_re = re.compile(r'^\s*\[(\bSPECIES_\w+\b)\]\s*=')
        open_brace = re.compile(r'\{')
        close_brace = re.compile(r'\}')

        while i < len(lines):
            m = spec_re.match(lines[i])
            if m:
                spec = m.group(1)
                # Collect block until balanced closing brace
                depth = 0
                block_lines = []
                while i < len(lines):
                    line = lines[i]
                    depth += len(open_brace.findall(line))
                    depth -= len(close_brace.findall(line))
                    block_lines.append(line)
                    i += 1
                    if depth <= 0:
                        break
                block = '\n'.join(block_lines)

                # Extract stats
                hp  = int(self._STAT_RE['hp'].search(block).group(1))   if self._STAT_RE['hp'].search(block)   else 0
                atk = int(self._STAT_RE['atk'].search(block).group(1))  if self._STAT_RE['atk'].search(block)  else 0
                dfs = int(self._STAT_RE['def'].search(block).group(1))  if self._STAT_RE['def'].search(block)  else 0
                spd = int(self._STAT_RE['spd'].search(block).group(1))  if self._STAT_RE['spd'].search(block)  else 0
                spa = int(self._STAT_RE['spa'].search(block).group(1))  if self._STAT_RE['spa'].search(block)  else 0
                spd2= int(self._STAT_RE['spd2'].search(block).group(1)) if self._STAT_RE['spd2'].search(block) else 0
                bst_map[spec] = hp + atk + dfs + spd + spa + spd2

                # Extract types
                tm = self._TYPES_RE.search(block)
                if tm:
                    type_map[spec] = (tm.group(1), tm.group(2))
            else:
                i += 1

        self.species_bst   = bst_map
        self.species_types = type_map
        self.log(f"  BST data: {len(bst_map)} entries parsed.")

    # ------------------------------------------------------------------
    # Item constants
    # ------------------------------------------------------------------

    _ITEM_DEFINE_RE = re.compile(r'^#define\s+(ITEM_\w+)\s+\d+', re.MULTILINE)

    def _parse_item_consts(self):
        path = os.path.join(self.source_dir, EMERALD_ITEMS_FILE)
        if not os.path.isfile(path):
            self.log(f"  [WARN] items.h not found: {EMERALD_ITEMS_FILE}")
            return
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        items = []
        for m in self._ITEM_DEFINE_RE.finditer(text):
            name = m.group(1)
            # Skip placeholder items (ITEM_034, ITEM_035, etc.)
            if re.match(r'^ITEM_\d+$', name):
                continue
            if name in EMERALD_FIELD_ITEMS_SKIP:
                continue
            if name == 'ITEM_NONE':
                continue
            items.append(name)
        self.all_items = items
        self.log(f"  Item constants: {len(items)} valid entries.")

    # ------------------------------------------------------------------
    # Wild encounters (JSON)
    # ------------------------------------------------------------------

    def _parse_wild_encounters(self):
        path = os.path.join(self.source_dir, EMERALD_WILD_FILE)
        if not os.path.isfile(path):
            self.log(f"  [WARN] wild_encounters.json not found.")
            return

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)

        self.wild_json = data
        slots = []

        for g_idx, group in enumerate(data.get('wild_encounter_groups', [])):
            for e_idx, enc in enumerate(group.get('encounters', [])):
                map_name = enc.get('map', '')
                for enc_type in EMERALD_WILD_TYPES:
                    enc_data = enc.get(enc_type)
                    if not enc_data:
                        continue
                    for s_idx, mon in enumerate(enc_data.get('mons', [])):
                        spec = mon.get('species', '')
                        if not spec or spec in EMERALD_SPECIES_SKIP:
                            continue
                        slots.append(EmeraldWildSlot(
                            species=spec,
                            min_level=mon.get('min_level', 1),
                            max_level=mon.get('max_level', 1),
                            enc_type=enc_type,
                            map_name=map_name,
                            group_idx=g_idx,
                            encounter_idx=e_idx,
                            slot_idx=s_idx,
                        ))

        self.wild_slots = slots
        maps = len({s.map_name for s in slots})
        self.log(f"  Wild slots: {len(slots)} across {maps} maps.")

    # ------------------------------------------------------------------
    # Trainer parties (C header)
    # ------------------------------------------------------------------

    _PARTY_DECL_RE = re.compile(
        r'static\s+const\s+struct\s+TrainerMon\s+(sParty_\w+)\s*\[\]'
    )
    _SPECIES_LINE_RE = re.compile(
        r'^\s*\.species\s*=\s*(SPECIES_\w+)\s*,?\s*$'
    )
    _LEVEL_LINE_RE = re.compile(
        r'^\s*\.lvl\s*=\s*(\d+)\s*,?\s*$'
    )

    def _parse_trainer_parties(self):
        parties_path = os.path.join(self.source_dir, EMERALD_PARTIES_FILE)
        trainers_path = os.path.join(self.source_dir, EMERALD_TRAINERS_FILE)

        if not os.path.isfile(parties_path):
            self.log(f"  [WARN] trainer_parties.h not found.")
            return

        # --- Step 1: build party_name → trainer_class from trainers.h ---
        class_map = {}   # "sParty_Sawyer1" → "TRAINER_CLASS_HIKER"
        if os.path.isfile(trainers_path):
            with open(trainers_path, 'r', encoding='utf-8', errors='replace') as f:
                t_text = f.read()
            # Find each trainer block: look for .trainerClass and .party = TRAINER_MON(sParty_*)
            tr_block_re = re.compile(
                r'\.trainerClass\s*=\s*(TRAINER_CLASS_\w+).*?'
                r'\.party\s*=\s*TRAINER_MON\(\s*(sParty_\w+)\s*\)',
                re.DOTALL,
            )
            for m in tr_block_re.finditer(t_text):
                cls, party = m.group(1), m.group(2)
                class_map[party] = cls

        # --- Step 2: parse trainer_parties.h line by line ---
        with open(parties_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        parties = []
        current_party_name = None
        current_mons = []
        current_level = 5
        in_party = False
        brace_depth = 0

        for i, raw in enumerate(lines):
            line = raw.rstrip('\n')

            # Detect party array declaration
            dm = self._PARTY_DECL_RE.search(line)
            if dm:
                # Save previous party if any
                if current_party_name and current_mons:
                    trainer_cls = class_map.get(current_party_name, '')
                    is_boss = any(k == trainer_cls for k in EMERALD_BOSS_CLASS_KEYWORDS)
                    parties.append(EmeraldTrainerParty(
                        party_name=current_party_name,
                        trainer_class=trainer_cls,
                        is_boss=is_boss,
                        mons=current_mons,
                    ))
                current_party_name = dm.group(1)
                current_mons = []
                current_level = 5
                in_party = True
                brace_depth = 0
                continue

            if not in_party:
                continue

            brace_depth += line.count('{') - line.count('}')

            # Detect level
            lm = self._LEVEL_LINE_RE.match(line)
            if lm:
                current_level = int(lm.group(1))
                continue

            # Detect species
            sm = self._SPECIES_LINE_RE.match(line)
            if sm:
                spec = sm.group(1)
                mon_idx = len(current_mons)
                current_mons.append(EmeraldTrainerMon(
                    species=spec,
                    level=current_level,
                    party_name=current_party_name,
                    mon_idx=mon_idx,
                    line_index=i,
                    full_line=raw,
                ))
                continue

            # End of party array
            if brace_depth < 0 or (brace_depth == 0 and '}' in line and ';' in line):
                in_party = False

        # Save last party
        if current_party_name and current_mons:
            trainer_cls = class_map.get(current_party_name, '')
            is_boss = any(k == trainer_cls for k in EMERALD_BOSS_CLASS_KEYWORDS)
            parties.append(EmeraldTrainerParty(
                party_name=current_party_name,
                trainer_class=trainer_cls,
                is_boss=is_boss,
                mons=current_mons,
            ))

        self.trainer_parties = parties
        total_mons = sum(len(p.mons) for p in parties)
        self.log(f"  Trainer parties: {len(parties)} parties, {total_mons} party members.")

    # ------------------------------------------------------------------
    # Starters
    # ------------------------------------------------------------------

    _STARTER_ARRAY_RE = re.compile(
        r'sStarterMon\s*\[.*?\]\s*=\s*\{([^}]+)\}', re.DOTALL
    )
    _STARTER_SPECIES_RE = re.compile(r'(SPECIES_\w+)')

    def _parse_starters(self):
        path = os.path.join(self.source_dir, EMERALD_STARTER_FILE)
        if not os.path.isfile(path):
            self.log(f"  [WARN] starter_choose.c not found.")
            return

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        text = ''.join(lines)

        m = self._STARTER_ARRAY_RE.search(text)
        if not m:
            self.log("  [WARN] sStarterMon array not found in starter_choose.c.")
            return

        array_body = m.group(1)
        species_list = self._STARTER_SPECIES_RE.findall(array_body)

        # Find line indices for each species
        starters = []
        found_count = 0
        for i, raw in enumerate(lines):
            for sp in species_list:
                if sp in raw and found_count < len(species_list):
                    # Make sure this is within the sStarterMon array context
                    if 'SPECIES_' in raw and '//' not in raw.split('SPECIES_')[0]:
                        idx = species_list.index(sp) if sp in species_list else found_count
                        if not any(s.line_index == i for s in starters):
                            starters.append(EmeraldStarterLocation(
                                species=sp,
                                idx=len(starters),
                                line_index=i,
                                full_line=raw,
                            ))
                            found_count += 1
                            break

        self.starters = starters
        self.log(f"  Starters: {[s.species for s in starters]}")

    # ------------------------------------------------------------------
    # Field items
    # ------------------------------------------------------------------

    _FINDITEM_RE = re.compile(
        r'^\s*finditem\s+(ITEM_\w+)', re.IGNORECASE
    )

    def _parse_field_items(self):
        path = os.path.join(self.source_dir, EMERALD_ITEM_SCRIPTS_FILE)
        if not os.path.isfile(path):
            self.log(f"  [WARN] item_ball_scripts.inc not found.")
            return

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        results = []
        for i, raw in enumerate(lines):
            line_nc = re.sub(r';.*$', '', raw)
            m = self._FINDITEM_RE.match(line_nc)
            if m:
                item = m.group(1).upper()
                if item in EMERALD_FIELD_ITEMS_SKIP:
                    continue
                results.append(EmeraldFieldItem(
                    item_const=item,
                    source_file=path,
                    line_index=i,
                    full_line=raw,
                ))

        self.field_items = results
        self.log(f"  Field items: {len(results)} finditem entries.")

    # ------------------------------------------------------------------
    # Static encounters (scan all .inc files)
    # ------------------------------------------------------------------

    _STATIC_BATTLE_RE  = re.compile(
        r'^\s*setwildbattle\s+(SPECIES_\w+)\s*,\s*(\d+)', re.IGNORECASE
    )
    _STATIC_GIVEEGG_RE = re.compile(
        r'^\s*giveegg\s+(SPECIES_\w+)', re.IGNORECASE
    )
    _LABEL_RE = re.compile(r'^(\w+)::', )

    def _parse_static_encounters(self):
        scripts_dir = os.path.join(self.source_dir, EMERALD_SCRIPTS_DIR)
        if not os.path.isdir(scripts_dir):
            self.log(f"  [WARN] scripts dir not found: {EMERALD_SCRIPTS_DIR}")
            return

        results = []
        for fname in sorted(os.listdir(scripts_dir)):
            if not fname.endswith('.inc'):
                continue
            # Skip the field item scripts (handled separately)
            if fname == 'item_ball_scripts.inc':
                continue
            fpath = os.path.join(scripts_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except OSError:
                continue

            last_label = ''
            for i, raw in enumerate(lines):
                lm = self._LABEL_RE.match(raw)
                if lm:
                    last_label = lm.group(1)

                line_nc = re.sub(r';.*$', '', raw)

                # setwildbattle SPECIES_X, level
                bm = self._STATIC_BATTLE_RE.match(line_nc)
                if bm:
                    spec = bm.group(1)
                    lvl  = int(bm.group(2))
                    results.append(EmeraldStaticEncounter(
                        species=spec,
                        level=lvl,
                        macro_type='setwildbattle',
                        is_legendary=(spec in EMERALD_LEGENDARY_SPECIES),
                        source_file=fpath,
                        line_index=i,
                        full_line=raw,
                        label=last_label,
                    ))
                    continue

                # giveegg SPECIES_X
                em = self._STATIC_GIVEEGG_RE.match(line_nc)
                if em:
                    spec = em.group(1)
                    results.append(EmeraldStaticEncounter(
                        species=spec,
                        level=0,
                        macro_type='giveegg',
                        is_legendary=(spec in EMERALD_LEGENDARY_SPECIES),
                        source_file=fpath,
                        line_index=i,
                        full_line=raw,
                        label=last_label,
                    ))

        self.static_encounters = results
        leg = sum(1 for e in results if e.is_legendary)
        self.log(
            f"  Static encounters: {len(results)} "
            f"({leg} legendary, {len(results)-leg} standard)."
        )
        for e in results:
            rel = os.path.relpath(e.source_file, self.source_dir)
            self.log(f"    [{e.macro_type}] {e.species} lv{e.level} — {rel}:{e.line_index+1}")
