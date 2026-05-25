"""
Pokemon Yellow Legacy Randomizer - ASM Source Writer

Writes randomized data back to Yellow Legacy ASM source files.
Performs targeted in-line replacements to preserve all comments,
formatting, macros, and non-randomized content.
"""

import os
import re
import shutil
from typing import Optional

from constants_yellow import YELLOW_POKEMON_CONSTANTS


class YellowSourceWriter:
    def __init__(self, source_dir: str, output_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.log = log_fn or print
        self._file_cache: dict[str, list] = {}

    # -------------------------------------------------------------------------
    # File cache helpers (identical pattern to Crystal writer)
    # -------------------------------------------------------------------------

    def prepare_output_directory(self):
        if os.path.exists(self.output_dir):
            self.log(f"Clearing existing output directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)
        self.log(f"Copying source tree to: {self.output_dir}")
        shutil.copytree(self.source_dir, self.output_dir, dirs_exist_ok=False)
        self.log("Copy complete.")

    def _get_output_path(self, source_path: str) -> str:
        rel = os.path.relpath(source_path, self.source_dir)
        return os.path.join(self.output_dir, rel)

    def _load_file(self, source_path: str) -> list:
        out_path = self._get_output_path(source_path)
        if out_path not in self._file_cache:
            with open(out_path, 'r', encoding='utf-8', errors='replace') as f:
                self._file_cache[out_path] = f.readlines()
        return self._file_cache[out_path]

    def _save_file(self, source_path: str):
        out_path = self._get_output_path(source_path)
        if out_path in self._file_cache:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.writelines(self._file_cache[out_path])

    def flush_all(self):
        for out_path, lines in self._file_cache.items():
            with open(out_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        self.log(f"Flushed {len(self._file_cache)} file(s) to output directory.")

    # -------------------------------------------------------------------------
    # Shared utility
    # -------------------------------------------------------------------------

    def _replace_pokemon_const(self, line: str, old_const: str, new_const: str) -> str:
        """Word-boundary replacement to avoid MEWTWO matching MEW etc."""
        return re.sub(r'\b' + re.escape(old_const) + r'\b', new_const, line)

    # -------------------------------------------------------------------------
    # Wild encounters (grass / water)
    # -------------------------------------------------------------------------

    def write_wild_encounters(self, original: list, randomized: list):
        """
        Replace species in wild encounter blocks.
        Each YellowWildGroup carries line_start/line_end so we scan only
        the relevant block lines and replace slot by slot.
        """
        slot_re = re.compile(
            r'^\s+db\s+\d+\s*,\s*([A-Z][A-Z0-9_]+)', re.IGNORECASE
        )
        files_written = set()

        for orig, rand in zip(original, randomized):
            if orig.rate == 0:
                continue   # no encounters — nothing to write
            lines     = self._load_file(orig.source_file)
            rand_iter = iter(rand.slots)

            for li in range(orig.line_start, min(orig.line_end + 1, len(lines))):
                m = slot_re.match(lines[li])
                if not m:
                    continue
                old_sp = m.group(1).upper()
                if old_sp not in YELLOW_POKEMON_CONSTANTS:
                    continue
                try:
                    rand_slot = next(rand_iter)
                except StopIteration:
                    break
                if old_sp != rand_slot.species_const:
                    lines[li] = self._replace_pokemon_const(
                        lines[li], old_sp, rand_slot.species_const
                    )
            files_written.add(orig.source_file)

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Wild encounters updated in {len(files_written)} file(s).")

    # -------------------------------------------------------------------------
    # Fishing (old rod / good rod — simple list)
    # -------------------------------------------------------------------------

    def write_fishing_simple(self, original: list, randomized: list, rod_name: str):
        """Replace species in old_rod or good_rod slot list."""
        files_written = set()
        changed = 0
        for orig, rand in zip(original, randomized):
            if orig.species_const == rand.species_const:
                continue
            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._replace_pokemon_const(old_line, orig.species_const, rand.species_const)
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1
        for sf in files_written:
            self._save_file(sf)
        self.log(f"  {rod_name}: {changed} replacement(s).")

    # -------------------------------------------------------------------------
    # Super rod
    # -------------------------------------------------------------------------

    def write_super_rod(self, original: list, randomized: list):
        """
        Replace species in super_rod.asm per-location table.
        Each slot knows its line_index and slot_index (0-3).
        We rebuild the line with new species inserted at the right position.
        """
        # Group by (source_file, line_index) — each row may have up to 4 slots
        from collections import defaultdict
        row_patches: dict = defaultdict(dict)   # (filepath, line_idx) → {slot_idx: new_sp}

        for orig, rand in zip(original, randomized):
            if orig.species_const == rand.species_const:
                continue
            key = (orig.source_file, orig.line_index)
            row_patches[key][orig.slot_index] = (orig.species_const, rand.species_const)

        files_written = set()
        changed = 0
        for (fp, li), patches in row_patches.items():
            lines    = self._load_file(fp)
            old_line = lines[li]
            new_line = old_line
            for slot_idx, (old_sp, new_sp) in patches.items():
                new_line = self._replace_pokemon_const(new_line, old_sp, new_sp)
            if new_line != old_line:
                lines[li] = new_line
                files_written.add(fp)
                changed += 1

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Super rod: {changed} row(s) updated.")

    # -------------------------------------------------------------------------
    # Trainers
    # -------------------------------------------------------------------------

    def write_trainers(self, original: list, randomized: list):
        """
        Replace species in trainer party lines.
        Handles both same-level and variable-level formats.

        For same-level (format 1):
            db LEVEL, SP1, SP2, ..., 0
        For variable-level (format 2):
            db $FF, LV1, SP1, LV2, SP2, ..., 0

        Both formats have all data on one line (line_start == line_end).
        We replace species tokens while preserving level and terminator.
        """
        files_written = set()
        changed = 0

        for orig, rand in zip(original, randomized):
            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_start]
            new_line = old_line

            # Replace each species const in order of the original party
            for orig_mon, rand_mon in zip(orig.party, rand.party):
                if orig_mon.species_const != rand_mon.species_const:
                    new_line = self._replace_pokemon_const(
                        new_line, orig_mon.species_const, rand_mon.species_const
                    )

            if new_line != old_line:
                lines[orig.line_start] = new_line
                files_written.add(orig.source_file)
                changed += 1

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  Trainer parties: {changed} line(s) updated across "
            f"{len(files_written)} file(s)."
        )

    # -------------------------------------------------------------------------
    # Starter
    # -------------------------------------------------------------------------

    def write_starter(self, original: list, new_species_const: str):
        """
        Replace STARTER_PIKACHU with the new species constant in all
        'ld a, STARTER_PIKACHU' lines found in OaksLab.asm.
        """
        files_written = set()
        changed = 0

        for loc in original:
            lines    = self._load_file(loc.source_file)
            old_line = lines[loc.line_index]
            # Replace the constant token after 'ld a,'
            new_line = re.sub(
                r'(ld\s+a\s*,\s*)STARTER_PIKACHU\b',
                r'\g<1>' + new_species_const,
                old_line,
                flags=re.IGNORECASE,
            )
            if new_line != old_line:
                lines[loc.line_index] = new_line
                files_written.add(loc.source_file)
                changed += 1

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  Starter: {changed} 'ld a, STARTER_PIKACHU' line(s) → {new_species_const}."
        )

    # -------------------------------------------------------------------------
    # In-game trades
    # -------------------------------------------------------------------------

    # Matches the quoted nickname string in a trade line: "NICKNAME@@@"
    _TRADE_NICK_RE = re.compile(r'"([^"]*)"')

    def _format_trade_nick(self, new_nick: str, original_quoted: str) -> str:
        """Re-pad new_nick with @ terminators to match the original quoted length."""
        target_len = len(original_quoted)
        name = new_nick.upper()[:10]
        padded = (name + '@' * (target_len + 1))[:target_len]
        return padded

    def write_trades(self, original: list, randomized: list):
        """
        Replace give/get species (and optionally nickname) in the TradeMons table.
        Each YellowTrade stores the exact line index.
        Format:  db GIVE, GET, DIALOG_ID, "NICKNAME@@@"
        OT names are stored in a separate table not currently parsed — skipped.
        """
        files_written = set()
        changes = 0
        nick_changes = 0
        ot_skipped = False

        for orig, rand in zip(original, randomized):
            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = old_line

            if orig.give_species != rand.give_species:
                new_line = self._replace_pokemon_const(
                    new_line, orig.give_species, rand.give_species
                )
                changes += 1

            if orig.get_species != rand.get_species:
                new_line = self._replace_pokemon_const(
                    new_line, orig.get_species, rand.get_species
                )
                changes += 1

            if orig.nickname != rand.nickname:
                m = self._TRADE_NICK_RE.search(new_line)
                if m:
                    new_nick_str = self._format_trade_nick(rand.nickname, m.group(1))
                    new_line = new_line[:m.start(1)] + new_nick_str + new_line[m.end(1):]
                    nick_changes += 1

            # OT names are in a separate table not captured by the parser
            if hasattr(rand, 'ot_name') and rand.ot_name:
                ot_skipped = True

            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  In-game trades: {changes} species change(s), "
            f"{nick_changes} nickname change(s) across {len(files_written)} file(s)."
        )
        if ot_skipped:
            self.log("  [INFO] OT name randomization skipped — OT names are in a separate table not yet supported.")

    # -------------------------------------------------------------------------
    # Evolutions
    # -------------------------------------------------------------------------

    # Matches: db EVOLVE_LEVEL, LEVEL, SPECIES
    _EVO_LEVEL_RE = re.compile(
        r'(db\s+EVOLVE_LEVEL\s*,\s*)(\d+)(\s*,\s*)([A-Z][A-Z0-9_]+)',
        re.IGNORECASE,
    )
    # Matches: db EVOLVE_ITEM, ITEM, 1, SPECIES
    _EVO_ITEM_RE = re.compile(
        r'(db\s+EVOLVE_ITEM\s*,\s*\S+\s*,\s*\d+\s*,\s*)([A-Z][A-Z0-9_]+)',
        re.IGNORECASE,
    )
    def write_static_encounters(self, original: list, randomized: list):
        """
        Replace species constants for static encounter lines in the output copy.
        Each YellowStaticEncounter stores the exact file path and line number.
        """
        files_written = set()
        replaced = 0

        for orig, rand in zip(original, randomized):
            if orig.species_const == rand.species_const:
                continue
            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._replace_pokemon_const(old_line, orig.species_const, rand.species_const)
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                replaced += 1
            else:
                self.log(
                    f"  [WARN] Could not replace {orig.species_const} → {rand.species_const} "
                    f"on line {orig.line_index + 1} of "
                    f"{os.path.relpath(orig.source_file, self.source_dir)}"
                )

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  Static encounters: {replaced} replacement(s) across "
            f"{len(files_written)} file(s)."
        )

    # Matches: db EVOLVE_TRADE, 1, SPECIES  →  rewrite as db EVOLVE_LEVEL, LEVEL, SPECIES
    _EVO_TRADE_RE = re.compile(
        r'(\s+)db\s+EVOLVE_TRADE\s*,\s*\d+\s*,\s*([A-Z][A-Z0-9_]+)',
        re.IGNORECASE,
    )

    def write_evolutions(self, original: list, modified: list):
        """
        Rewrite evolution entries where param or type changed.
        Supports:
          - Lowering EVOLVE_LEVEL thresholds (make evolutions easier)
          - Converting EVOLVE_TRADE to EVOLVE_LEVEL (with a new level param)
        """
        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if orig.evo_type == mod.evo_type and orig.param == mod.param:
                continue

            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = old_line

            if mod.evo_type == 'EVOLVE_LEVEL':
                if orig.evo_type == 'EVOLVE_LEVEL':
                    # Just change the level number
                    new_line = self._EVO_LEVEL_RE.sub(
                        lambda m: m.group(1) + mod.param + m.group(3) + m.group(4),
                        old_line, count=1,
                    )
                elif orig.evo_type == 'EVOLVE_TRADE':
                    # Rewrite trade evo as level evo
                    new_line = self._EVO_TRADE_RE.sub(
                        lambda m: m.group(1) + f'db EVOLVE_LEVEL, {mod.param}, {orig.target_species}',
                        old_line, count=1,
                    )
            elif mod.evo_type == 'EVOLVE_ITEM':
                # Item type stays; level threshold change not applicable
                pass

            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1
            else:
                if orig.evo_type != mod.evo_type or orig.param != mod.param:
                    self.log(
                        f"  [WARN] Could not rewrite evolution on line "
                        f"{orig.line_index + 1} of "
                        f"{os.path.relpath(orig.source_file, self.source_dir)}"
                    )

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Evolutions: {changed} line(s) updated across {len(files_written)} file(s).")

    # -------------------------------------------------------------------------
    # Catch rates
    # -------------------------------------------------------------------------

    def write_catch_rates(self, original: list, modified: list):
        """Replace the catch rate value in each Pokémon's base stats file."""
        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if orig.catch_rate == mod.catch_rate:
                continue
            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = re.sub(
                r'^(\s*db\s+)\d+',
                lambda m: m.group(1) + str(mod.catch_rate),
                old_line, count=1,
            )
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Updated catch rates for {changed} Pokémon.")

    # -------------------------------------------------------------------------
    # TM/HM compatibility
    # -------------------------------------------------------------------------

    def write_tmhm_compat(self, original: list, modified: list):
        """Rewrite the tmhm macro line for Pokémon whose learnset changed."""
        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if set(orig.moves) == set(mod.moves):
                continue
            lines    = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]

            indent = len(old_line) - len(old_line.lstrip())
            indent_str = old_line[:indent]
            comment_m  = re.search(r'\s*(;.*)$', old_line)
            comment    = ('  ' + comment_m.group(1).rstrip()) if comment_m else ''

            new_line = f"{indent_str}tmhm {', '.join(mod.moves)}{comment}\n"
            lines[orig.line_index] = new_line
            files_written.add(orig.source_file)
            changed += 1

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Updated TM/HM compatibility for {changed} Pokémon.")

    # -------------------------------------------------------------------------
    # Field items
    # -------------------------------------------------------------------------

    _VISIBLE_FIELD_RE = re.compile(
        r'^(\s*(?:finditem|itemball)\s+)([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    _HIDDEN_FIELD_RE = re.compile(
        r'^(\s*hiddenitem\s+)([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    def write_field_items(self, original: list, modified: list):
        """
        Replace field item constants in the output copy of each script file.
        Both visible (finditem/itemball) and hidden (hiddenitem) macros are handled.
        The substitution only touches the item constant — all surrounding
        whitespace, arguments, and comments are preserved.
        """
        if not original or not modified:
            return

        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if orig.item_const == mod.item_const:
                continue

            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]

            pattern = self._VISIBLE_FIELD_RE if orig.item_type == "visible" \
                      else self._HIDDEN_FIELD_RE

            m = pattern.match(old_line)
            if m:
                new_line = m.group(1) + mod.item_const + old_line[m.end():]
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1
            else:
                self.log(
                    f"  [WARN] Could not replace field item {orig.item_const} "
                    f"on line {orig.line_index + 1} of {os.path.basename(orig.source_file)}"
                )

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Updated {changed} field item line(s).")

    # -------------------------------------------------------------------------
    # Starting bag items (Gen 1 — bag only, no PC item box)
    # -------------------------------------------------------------------------

    def write_starting_items(self, bag_items: list, pc_items: list = None):
        """
        Inject custom starting bag and PC items into the Yellow Legacy new-game init.

        bag_items / pc_items: list of {"const": "ITEM_CONST", "qty": N} dicts

        Strategy
        --------
        Searches the same candidate files used for PC Pokémon injection for a
        usable injection point (call to ResetGameTime / InitNewGame / ClearSAV).
        Appends a shared GBZ80 subroutine ``RandomizerLoadItemList`` that writes
        an item list from a data table into WRAM, then calls it for the bag
        (wNumBagItems / wBagItems) and optionally the PC item box
        (wNumPCItems / wPCItems).

        The item WRAM layout (Gen 1 pokeyellow shares with Crystal):
            wNum*Items  DB  (count)
            w*Items     DB  ITEM, QTY, ITEM, QTY, …, $ff  (terminator)
        """
        pc_items = pc_items or []
        if not bag_items and not pc_items:
            return

        MAX_BAG = 20
        MAX_PC  = 50
        bag_items = [i for i in bag_items if 1 <= int(i.get("qty", 1)) <= 99][:MAX_BAG]
        pc_items  = [i for i in pc_items  if 1 <= int(i.get("qty", 1)) <= 99][:MAX_PC]

        if not bag_items and not pc_items:
            return

        # Find injection point (same search as write_pc_pokemon)
        init_src_path = None
        text = ''
        matched_pat = None
        injection_patterns = [
            re.compile(r'(\tcall\s+ResetGameTime\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+InitNewGame\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+ClearSAV\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+\w+\n)(\tret\n)', re.MULTILINE),
        ]
        for candidate in self._YELLOW_INIT_CANDIDATES:
            cpath = os.path.join(self.source_dir, candidate)
            if not os.path.isfile(cpath):
                continue
            out_p = self._get_output_path(cpath)
            if not os.path.isfile(out_p):
                continue
            with open(out_p, 'r', encoding='utf-8', errors='replace') as fh:
                t = fh.read()
            for pat in injection_patterns:
                if pat.search(t):
                    init_src_path = cpath
                    text = t
                    matched_pat = pat
                    break
            if init_src_path:
                break

        if init_src_path is None or matched_pat is None:
            self.log(
                "[WARN] Could not find new-game init injection point — "
                "starting items injection skipped."
            )
            return

        out_path = self._get_output_path(init_src_path)

        # If already injected (from a previous run), skip re-inject
        if 'RandomizerInitItems' in text:
            self.log(
                "  [INFO] RandomizerInitItems already present — "
                "re-run on a fresh output to regenerate."
            )
            return

        self.log(f"  ✓ Starting items injection point found in {os.path.basename(init_src_path)}")

        new_text = matched_pat.sub(
            r'\1\tcall RandomizerInitItems\n\2', text, count=1
        )

        def _table(items):
            rows = "".join(f"\tdb {i['const']}, {int(i['qty'])}\n" for i in items)
            return rows + "\tdb $ff\n"

        bag_table = _table(bag_items) if bag_items else "\tdb $ff\n"
        pc_table  = _table(pc_items)  if pc_items  else "\tdb $ff\n"

        subroutine = (
            "\n"
            "; ---- Randomizer: starting item injection ----------------------------\n"
            "RandomizerStartBagData:\n"
            + bag_table +
            "RandomizerStartPCData:\n"
            + pc_table +
            "\n"
            "RandomizerInitItems::\n"
            "; Load bag items\n"
            "\tld hl, RandomizerStartBagData\n"
            "\tld de, wNumBagItems\n"
            "\tcall RandomizerLoadItemList\n"
            "; Load PC items\n"
            "\tld hl, RandomizerStartPCData\n"
            "\tld de, wNumPCItems\n"
            "\tcall RandomizerLoadItemList\n"
            "\tret\n"
            "\n"
            "RandomizerLoadItemList:\n"
            "; Input: hl = source data table (db ITEM, QTY ... db $ff)\n"
            ";        de = destination count byte (wNumBagItems or wNumPCItems)\n"
            "\tpush de\n"
            "\tinc de\n"
            "\txor a\n"
            "\tld b, a\n"
            ".rll_loop:\n"
            "\tld a, [hli]\n"
            "\tcp $ff\n"
            "\tjr z, .rll_done\n"
            "\tld [de], a\n"
            "\tinc de\n"
            "\tld a, [hli]\n"
            "\tld [de], a\n"
            "\tinc de\n"
            "\tinc b\n"
            "\tjr .rll_loop\n"
            ".rll_done:\n"
            "\tld a, $ff\n"
            "\tld [de], a\n"
            "\tpop de\n"
            "\tld a, b\n"
            "\tld [de], a\n"
            "\tret\n"
        )

        if not new_text.endswith('\n'):
            new_text += '\n'
        new_text += subroutine

        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(new_text)

        bag_log = ", ".join(f"{i['const']}×{i['qty']}" for i in bag_items) or "(none)"
        pc_log  = ", ".join(f"{i['const']}×{i['qty']}" for i in pc_items)  or "(none)"
        self.log(f"  Starting bag items: {bag_log}")
        self.log(f"  Starting PC items : {pc_log}")

    # -------------------------------------------------------------------------
    # PC Pokémon injection (Gen 1 / pokeyellow format)
    # -------------------------------------------------------------------------

    # Gen 1 / pokeyellow character encoding (same table as Crystal)
    _GEN1_CHARMAP = dict(
        **{chr(0x41 + i): 0x80 + i for i in range(26)},   # A-Z → $80-$99
        **{chr(0x61 + i): 0xA0 + i for i in range(26)},   # a-z → $A0-$B9
        **{chr(0x30 + i): 0xF6 + i for i in range(10)},   # 0-9 → $F6-$FF
        **{' ': 0x7F, '.': 0xE8, ',': 0xF0, "'": 0xE2,
           '-': 0xE3, '!': 0xE9, '?': 0xEA,
           '♂': 0xEF, '♀': 0xF5},
    )
    _GEN1_TERM = 0x50   # string terminator
    _GEN1_FILL = 0x50   # padding (Gen 1 uses 0x50 throughout)

    _SPECIES_NAME_OVERRIDES_Y = {
        'NIDORAN_F': 'NIDORAN♀',
        'NIDORAN_M': 'NIDORAN♂',
        'FARFETCHD':  "FARFETCH'D",
        'MR_MIME':   'MR. MIME',
    }

    def _encode_gen1_str(self, s: str, length: int) -> list:
        """Encode *s* in Gen 1 character set, padded to *length* bytes."""
        result = []
        for ch in s[:length - 1]:
            result.append(self._GEN1_CHARMAP.get(ch, 0x7F))
        result.append(self._GEN1_TERM)
        while len(result) < length:
            result.append(self._GEN1_FILL)
        return result

    def _species_default_name_y(self, species_const: str) -> str:
        if species_const in self._SPECIES_NAME_OVERRIDES_Y:
            return self._SPECIES_NAME_OVERRIDES_Y[species_const]
        return species_const.replace('_', ' ').strip()[:10]

    def _load_move_pp_table_y(self, source_dir: str) -> dict:
        """Parse moves.asm and return {MOVE_CONST: pp} — falls back to 35 if not found."""
        # pokeyellow path: data/moves/moves.asm
        for sub in ('data/moves/moves.asm', 'data/move/moves.asm'):
            path = os.path.join(source_dir, sub)
            if os.path.isfile(path):
                pp = {}
                pat = re.compile(
                    r'^\s+move\s+(\w+)\s*,\s*\w+\s*,\s*\d+\s*,\s*\w+\s*,\s*\d+\s*,\s*(\d+)',
                    re.MULTILINE,
                )
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    for m in pat.finditer(fh.read()):
                        pp[m.group(1)] = int(m.group(2))
                return pp
        return {}

    def _gen1_mon_writes(self, box_n: int, mon_num: int, mon: dict, pp_table: dict) -> list:
        """Return GBZ80 ASM instruction strings for one Gen 1 box Pokémon."""
        lines = []
        species = mon.get('species', 'BULBASAUR')
        moves   = list(mon.get('moves') or [])
        while len(moves) < 4:
            moves.append('NO_MOVE')
        level    = max(1, min(100, int(mon.get('level') or 5)))
        dv_atk   = max(0, min(15, int(mon.get('dvAtk') or 15)))
        dv_def   = max(0, min(15, int(mon.get('dvDef') or 15)))
        dv_spd   = max(0, min(15, int(mon.get('dvSpd') or 15)))
        dv_spc   = max(0, min(15, int(mon.get('dvSpc') or 15)))
        nickname = (mon.get('nickname') or '').strip()
        if not nickname:
            nickname = self._species_default_name_y(species)

        # Experience: level³  (Medium Fast)
        exp = level ** 3
        exp_b2, exp_b1, exp_b0 = (exp >> 16) & 0xFF, (exp >> 8) & 0xFF, exp & 0xFF

        # PP for each move
        pp_vals = [pp_table.get(mv, 35) if (mv and mv != 'NO_MOVE') else 0 for mv in moves]

        # Packed DVs: byte1 = (Atk<<4)|Def, byte2 = (Spd<<4)|Spc
        dv1 = (dv_atk << 4) | dv_def
        dv2 = (dv_spd << 4) | dv_spc

        ot_bytes   = self._encode_gen1_str('TRAINER', 11)
        nick_bytes = self._encode_gen1_str(nickname.upper(), 11)

        label_mon  = f'sBox{box_n}Mon{mon_num}'
        label_ot   = f'sBox{box_n}Mon{mon_num}OT'
        label_nick = f'sBox{box_n}Mon{mon_num}Nickname'

        lines.append(f'\t; Box {box_n} Mon {mon_num}: {species} Lv{level}')
        lines.append(f'\tld hl, {label_mon}')

        # Byte 00: Species index
        lines.append(f'\tld a, {species}')
        lines.append('\tld [hli], a')
        # Bytes 01-02: Current HP = 0 (game recalculates on load)
        for _ in range(2):
            lines.append('\txor a')
            lines.append('\tld [hli], a')
        # Byte 03: Status
        lines.append('\txor a')
        lines.append('\tld [hli], a')
        # Bytes 04-05: Type1/Type2 = 0 (game fills from base stats)
        for _ in range(2):
            lines.append('\txor a')
            lines.append('\tld [hli], a')
        # Byte 06: Catch rate (use 0 — game fills from base stats)
        lines.append('\txor a')
        lines.append('\tld [hli], a')
        # Bytes 07-0A: Moves
        for mv in moves:
            if mv and mv != 'NO_MOVE':
                lines.append(f'\tld a, {mv}')
            else:
                lines.append('\txor a')
            lines.append('\tld [hli], a')
        # Bytes 0B-0C: OT ID (patch from wPlayerID)
        lines.append('\txor a')
        lines.append('\tld [hli], a')
        lines.append('\tld [hli], a')
        # Bytes 0D-0F: Exp (big-endian)
        lines.append(f'\tld a, ${exp_b2:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${exp_b1:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${exp_b0:02x}')
        lines.append('\tld [hli], a')
        # Bytes 10-19: Stat EXP (10 bytes, zero)
        lines.append('\txor a')
        for _ in range(10):
            lines.append('\tld [hli], a')
        # Bytes 1A-1B: DVs
        lines.append(f'\tld a, ${dv1:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${dv2:02x}')
        lines.append('\tld [hli], a')
        # Bytes 1C-1F: PP
        for pp in pp_vals:
            lines.append(f'\tld a, {pp}')
            lines.append('\tld [hli], a')
        # Byte 20: Level
        lines.append(f'\tld a, {level}')
        lines.append('\tld [hli], a')

        # Patch OT ID from wPlayerID
        lines.append(f'\tld hl, {label_mon} + 11')  # offset $0B
        lines.append('\tld a, [wPlayerID]')
        lines.append('\tld [hli], a')
        lines.append('\tld a, [wPlayerID + 1]')
        lines.append('\tld [hl], a')

        # Write OT name
        lines.append(f'\tld hl, {label_ot}')
        for b in ot_bytes:
            lines.append(f'\tld a, ${b:02x}')
            lines.append('\tld [hli], a')

        # Write nickname
        lines.append(f'\tld hl, {label_nick}')
        for b in nick_bytes:
            lines.append(f'\tld a, ${b:02x}')
            lines.append('\tld [hli], a')

        return lines

    def _gen1_box_writes(self, box_n: int, mons: list, pp_table: dict) -> list:
        """Return ASM lines that populate one Gen 1 PC box."""
        lines = []
        n = len(mons)
        lines.append(f'\t; Box {box_n}: {n} mon(s)')
        lines.append(f'\tld a, {n}')
        lines.append(f'\tld [sBox{box_n}Count], a')
        # Species list + $FF terminator
        for i, mon in enumerate(mons):
            lines.append(f'\tld a, {mon["species"]}')
            lines.append(f'\tld [sBox{box_n}Species + {i}], a')
        lines.append('\tld a, $ff')
        lines.append(f'\tld [sBox{box_n}Species + {n}], a')
        # Per-mon data, OT names, nicknames
        for idx, mon in enumerate(mons):
            lines.extend(self._gen1_mon_writes(box_n, idx + 1, mon, pp_table))
        return lines

    # Candidate source files (relative to source root) for new-game init injection
    _YELLOW_INIT_CANDIDATES = [
        'home.asm',
        'home/init.asm',
        'engine/title.asm',
        'engine/menus/intro_menu.asm',
        'engine/overworld/init.asm',
        'engine/new_game.asm',
    ]

    def write_pc_pokemon(self, pc_mons: list):
        """
        Inject a GBZ80 subroutine into the new-game init ASM that writes
        user-specified Pokémon into PC boxes.  Searches common Yellow Legacy
        source paths for a suitable injection point.
        """
        if not pc_mons:
            return

        # Group by box (1–12), cap each box at 20 Pokémon
        box_mons: dict[int, list] = {}
        for mon in pc_mons:
            try:
                box = int(mon.get('box', 1))
                if not (1 <= box <= 12) or not mon.get('species'):
                    continue
                box_mons.setdefault(box, [])
                if len(box_mons[box]) < 20:
                    box_mons[box].append(mon)
            except (ValueError, TypeError):
                continue

        if not box_mons:
            return

        pp_table = self._load_move_pp_table_y(self.source_dir)

        # Find a candidate source file with a usable injection point
        init_src_path = None
        text = ''
        matched_pat = None
        injection_patterns = [
            re.compile(r'(\tcall\s+ResetGameTime\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+InitNewGame\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+ClearSAV\n)(\tret\n)', re.MULTILINE),
            re.compile(r'(\tcall\s+\w+\n)(\tret\n)', re.MULTILINE),
        ]
        for candidate in self._YELLOW_INIT_CANDIDATES:
            cpath = os.path.join(self.source_dir, candidate)
            if not os.path.isfile(cpath):
                continue
            with open(self._get_output_path(cpath), 'r', encoding='utf-8', errors='replace') as fh:
                t = fh.read()
            for pat in injection_patterns:
                if pat.search(t):
                    init_src_path = cpath
                    text = t
                    matched_pat = pat
                    break
            if init_src_path:
                break

        if init_src_path is None or matched_pat is None:
            self.log(
                "[WARN] Could not find a new-game init injection point in common Yellow "
                "source files — PC Pokémon injection skipped."
            )
            return

        out_path = self._get_output_path(init_src_path)
        self.log(f"  ✓ New-game init injection point found in {os.path.basename(init_src_path)}")
        new_text = matched_pat.sub(
            r'\1\tcall RandomizerInitPCMons\n\2', text, count=1
        )

        # Build subroutine
        asm = ['; ---- Randomizer: PC Pokémon injection ----', 'RandomizerInitPCMons::']
        # Open SRAM bank 1 (pokeyellow uses a single SRAM bank for boxes 1-6)
        # and bank 2 for boxes 7-12
        bank_a = {n: m for n, m in box_mons.items() if 1 <= n <= 6}
        bank_b = {n: m for n, m in box_mons.items() if 7 <= n <= 12}

        if bank_a:
            asm.append('\tld a, BANK(sBox1)')
            asm.append('\tcall OpenSRAM')
            for box_n in sorted(bank_a):
                asm.extend(self._gen1_box_writes(box_n, bank_a[box_n], pp_table))
            asm.append('\tcall CloseSRAM')

        if bank_b:
            asm.append('\tld a, BANK(sBox7)')
            asm.append('\tcall OpenSRAM')
            for box_n in sorted(bank_b):
                asm.extend(self._gen1_box_writes(box_n, bank_b[box_n], pp_table))
            asm.append('\tcall CloseSRAM')

        asm.append('\tret')

        if not new_text.endswith('\n'):
            new_text += '\n'
        new_text += '\n'.join(asm) + '\n'

        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(new_text)

        total = sum(len(m) for m in box_mons.values())
        self.log(f"  PC Pokémon: {total} Pokémon across {len(box_mons)} box(es)")
