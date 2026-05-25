"""
Pokemon Emerald Legacy Randomizer — Source Writer

Writes randomized data back to a copy of the Emerald Legacy source tree.
The original source directory is never modified; all changes go to output_dir.
"""

import copy
import json
import os
import re
import shutil


class EmeraldSourceWriter:
    def __init__(self, source_dir: str, output_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.log = log_fn or print
        self._file_cache: dict = {}   # abs_output_path → list[str]

    # ------------------------------------------------------------------
    # Output directory management
    # ------------------------------------------------------------------

    def prepare_output_directory(self):
        """Copy source to output_dir (skipping build artifacts)."""
        if os.path.abspath(self.source_dir) == os.path.abspath(self.output_dir):
            self.log("  [INFO] Source and output are the same directory — modifying in-place.")
            return

        SKIP_DIRS  = {'.git', 'build', '.github'}
        SKIP_EXTS  = {'.o', '.gba', '.elf', '.map', '.d'}

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        self.log(f"  Copying source → {os.path.basename(self.output_dir)} …")
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            rel = os.path.relpath(root, self.source_dir)
            out_root = os.path.join(self.output_dir, rel)
            os.makedirs(out_root, exist_ok=True)
            for fname in files:
                if os.path.splitext(fname)[1] in SKIP_EXTS:
                    continue
                shutil.copy2(os.path.join(root, fname), os.path.join(out_root, fname))
        self.log("  Copy complete.")

    def _src_to_out(self, src_abs: str) -> str:
        rel = os.path.relpath(src_abs, self.source_dir)
        return os.path.join(self.output_dir, rel)

    def _load_lines(self, src_abs: str) -> list:
        out = self._src_to_out(src_abs)
        if out not in self._file_cache:
            with open(out, 'r', encoding='utf-8', errors='replace') as f:
                self._file_cache[out] = f.readlines()
        return self._file_cache[out]

    def _save_lines(self, src_abs: str):
        out = self._src_to_out(src_abs)
        if out in self._file_cache:
            with open(out, 'w', encoding='utf-8') as f:
                f.writelines(self._file_cache[out])

    def flush_all(self):
        for out_path, lines in self._file_cache.items():
            with open(out_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        self._file_cache.clear()

    # ------------------------------------------------------------------
    # Wild encounters (JSON)
    # ------------------------------------------------------------------

    def write_wild_encounters(self, new_json: dict):
        """Write the randomized wild_encounters.json to the output directory."""
        from constants_emerald import EMERALD_WILD_FILE
        src_path = os.path.join(self.source_dir, EMERALD_WILD_FILE)
        out_path = self._src_to_out(src_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(new_json, f, indent=2)
            f.write('\n')

        total = 0
        for group in new_json.get('wild_encounter_groups', []):
            for enc in group.get('encounters', []):
                for enc_type in ('land_mons', 'water_mons', 'rock_smash_mons', 'fishing_mons'):
                    ed = enc.get(enc_type)
                    if ed:
                        total += len(ed.get('mons', []))
        self.log(f"  Wild encounters: wrote {total} slot(s) to {EMERALD_WILD_FILE}.")

    # ------------------------------------------------------------------
    # Trainer parties (C header — line-level replacement)
    # ------------------------------------------------------------------

    _SPECIES_LINE_RE = re.compile(
        r'^(\s*\.species\s*=\s*)(SPECIES_\w+)(\s*,?\s*)$'
    )

    def write_trainer_parties(self, original: list, randomized: list):
        """
        Replace .species = SPECIES_X lines in trainer_parties.h.
        original / randomized: list[EmeraldTrainerParty]
        """
        from constants_emerald import EMERALD_PARTIES_FILE
        src_path = os.path.join(self.source_dir, EMERALD_PARTIES_FILE)
        lines = self._load_lines(src_path)

        changed = 0
        for orig_party, rand_party in zip(original, randomized):
            for orig_mon, rand_mon in zip(orig_party.mons, rand_party.mons):
                if orig_mon.species == rand_mon.species:
                    continue
                old_line = lines[orig_mon.line_index]
                m = self._SPECIES_LINE_RE.match(old_line)
                if m:
                    lines[orig_mon.line_index] = (
                        m.group(1) + rand_mon.species + m.group(3) + '\n'
                        if not old_line.endswith('\n')
                        else m.group(1) + rand_mon.species + m.group(3)
                    )
                    # Preserve original newline
                    lines[orig_mon.line_index] = (
                        m.group(1) + rand_mon.species + m.group(3).rstrip('\n') + '\n'
                    )
                    changed += 1
                else:
                    # Fallback: simple string replace
                    lines[orig_mon.line_index] = old_line.replace(
                        orig_mon.species, rand_mon.species, 1
                    )
                    changed += 1

        self._save_lines(src_path)
        self.log(f"  Trainer parties: {changed} species replacement(s).")

    # ------------------------------------------------------------------
    # Starters
    # ------------------------------------------------------------------

    _STARTER_SPECIES_RE = re.compile(r'(SPECIES_\w+)')

    def write_starters(self, original: list, new_species: list):
        """
        Replace species in the sStarterMon array in starter_choose.c.
        original: list[EmeraldStarterLocation]
        new_species: list of 3 SPECIES_* strings
        """
        from constants_emerald import EMERALD_STARTER_FILE
        src_path = os.path.join(self.source_dir, EMERALD_STARTER_FILE)
        lines = self._load_lines(src_path)

        changed = 0
        for loc, new_sp in zip(original, new_species):
            if loc.species == new_sp:
                continue
            old_line = lines[loc.line_index]
            new_line = self._STARTER_SPECIES_RE.sub(new_sp, old_line, count=1)
            lines[loc.line_index] = new_line
            changed += 1

        self._save_lines(src_path)
        orig_names = [s.species for s in original]
        self.log(f"  Starters: {orig_names} → {new_species} ({changed} line(s) updated).")

    # ------------------------------------------------------------------
    # Field items
    # ------------------------------------------------------------------

    _FINDITEM_LINE_RE = re.compile(
        r'^(\s*finditem\s+)(ITEM_\w+)(.*)',
        re.IGNORECASE,
    )

    def write_field_items(self, original: list, modified: list):
        """Replace finditem ITEM_* constants in item_ball_scripts.inc."""
        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if orig.item_const == mod.item_const:
                continue
            lines = self._load_lines(orig.source_file)
            old_line = lines[orig.line_index]
            m = self._FINDITEM_LINE_RE.match(old_line)
            if m:
                lines[orig.line_index] = m.group(1) + mod.item_const + m.group(3)
                if not lines[orig.line_index].endswith('\n'):
                    lines[orig.line_index] += '\n'
                files_written.add(orig.source_file)
                changed += 1
            else:
                self.log(
                    f"  [WARN] Could not replace {orig.item_const} "
                    f"on line {orig.line_index + 1} of "
                    f"{os.path.basename(orig.source_file)}"
                )

        for sf in files_written:
            self._save_lines(sf)
        self.log(f"  Field items: {changed} replacement(s).")

    # ------------------------------------------------------------------
    # Static encounters
    # ------------------------------------------------------------------

    _STATIC_SPECIES_RE = re.compile(r'(SPECIES_\w+)')

    def write_static_encounters(self, original: list, randomized: list):
        """Replace species in setwildbattle / giveegg lines."""
        files_written = set()
        changed = 0

        for orig, rand in zip(original, randomized):
            if orig.species == rand.species:
                continue
            lines = self._load_lines(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._STATIC_SPECIES_RE.sub(rand.species, old_line, count=1)
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1
            else:
                self.log(
                    f"  [WARN] Could not replace static {orig.species} "
                    f"on line {orig.line_index + 1}"
                )

        for sf in files_written:
            self._save_lines(sf)
        self.log(
            f"  Static encounters: {changed} replacement(s) across "
            f"{len(files_written)} file(s)."
        )
