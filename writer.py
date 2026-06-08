"""
Pokemon Crystal Legacy Randomizer - ASM Source Writer

Writes randomized data back to ASM source files.
Performs targeted in-line replacements to preserve all comments,
formatting, macros, and non-randomized content.
"""

import os
import re
import shutil
from typing import Optional
from constants import POKEMON_CONSTANTS, STARTER_CONSTANTS
from parser import (WildEncounterGroup, Trainer, StarterLocation, StarterItemLocation,
                    StaticEncounter, InGameTrade, EvolutionEntry, WildHeldItemEntry,
                    TMHMCompatEntry, FieldItemEntry,
                    StarterDialogueLine, StarterTextLine, FishSlot)
from constants import POKEMON_PRIMARY_TYPE, POKEMON_DISPLAY_NAME
from item_data import (BALL_ITEM_CONSTS, KEY_ITEM_CONSTS, TM_HM_ITEM_CONSTS,
                       TM_HM_TMNUM_SYMBOLS)


class SourceWriter:
    def __init__(self, source_dir: str, output_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.log = log_fn or print
        # Cache of file lines (output_dir versions)
        self._file_cache: dict[str, list] = {}

    def prepare_output_directory(self):
        """Copy the entire source tree to output_dir."""
        if os.path.exists(self.output_dir):
            self.log(f"Clearing existing output directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)
        self.log(f"Copying source tree to: {self.output_dir}")
        shutil.copytree(self.source_dir, self.output_dir, dirs_exist_ok=False)
        self.log("Copy complete.")

    def _get_output_path(self, source_path: str) -> str:
        """Convert a source path to the equivalent output path."""
        rel = os.path.relpath(source_path, self.source_dir)
        return os.path.join(self.output_dir, rel)

    def _load_file(self, source_path: str) -> list:
        """Load (or return cached) lines from the output copy of a file."""
        out_path = self._get_output_path(source_path)
        if out_path not in self._file_cache:
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                self._file_cache[out_path] = f.readlines()
        return self._file_cache[out_path]

    def _save_file(self, source_path: str):
        """Flush cached lines back to disk."""
        out_path = self._get_output_path(source_path)
        if out_path in self._file_cache:
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(self._file_cache[out_path])

    # -------------------------------------------------------------------------
    # Starters
    # -------------------------------------------------------------------------

    def write_starters(self, original: list, randomized: list):
        """
        Replace starter species in the output copy.
        original and randomized are both lists of 3 StarterLocation.
        """
        if len(original) != 3 or len(randomized) != 3:
            self.log("[WARN] Starter write skipped: need exactly 3 original + 3 randomized.")
            return

        files_written = set()
        for orig, rand in zip(original, randomized):
            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._replace_pokemon_const(old_line, orig.species_const, rand.species_const)
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
            else:
                self.log(f"  [WARN] Could not replace {orig.species_const} on line "
                         f"{orig.line_index + 1} of {orig.source_file}")

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Starter definitions updated in {len(files_written)} file(s).")

    # -------------------------------------------------------------------------
    # Starter held items
    # -------------------------------------------------------------------------

    def write_starter_items(self, original: list, randomized: list):
        """
        Replace held-item constants in givepoke lines for starters.
        original and randomized are both lists of StarterItemLocation.
        """
        files_written = set()
        replaced = 0

        for orig, rand in zip(original, randomized):
            if orig.item_const == rand.item_const:
                continue
            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._replace_givepoke_item(old_line, orig.item_const, rand.item_const)
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                replaced += 1
            else:
                self.log(
                    f"  [WARN] Could not replace item {orig.item_const} → {rand.item_const} "
                    f"on line {orig.line_index + 1} of "
                    f"{os.path.relpath(orig.source_file, self.source_dir)}"
                )

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Starter items: {replaced} replacement(s) in {len(files_written)} file(s).")

    # -------------------------------------------------------------------------
    # Starter dialogue (pokepic / cry / getmonname + Take…Text blocks)
    # -------------------------------------------------------------------------

    def write_starter_dialogue(self,
                                original_starters: list,
                                rand_starters: list,
                                dialogue_lines: list,
                                text_lines: list):
        """
        Update ElmsLab.asm (or equivalent) so the starter-selection dialogue
        reflects the randomized starters.

        Three categories of lines are updated:
          1. ``pokepic SPECIES`` / ``cry SPECIES`` / ``getmonname …, SPECIES``
             → species constant replaced with the randomized species.
          2. ``line "SPECIES, the"`` inside Take…Text blocks
             → display name replaced (e.g. "CYNDAQUIL" → "BULBASAUR").
          3. ``cont "type #MON?"`` inside Take…Text blocks
             → type string replaced with the randomized species' primary type.
        """
        if not dialogue_lines and not text_lines:
            self.log("  Starter dialogue: nothing to update.")
            return

        files_written: set = set()
        changed = 0

        # Map original species → randomized species (for category 1)
        orig_to_rand = {
            orig.species_const: rand.species_const
            for orig, rand in zip(original_starters, rand_starters)
        }

        # ── 1. Script macros (pokepic / cry / getmonname) ─────────────────
        for entry in dialogue_lines:
            new_species = orig_to_rand.get(entry.species_const)
            if not new_species or new_species == entry.species_const:
                continue
            lines = self._load_file(entry.source_file)
            old_line = lines[entry.line_index]
            new_line = self._replace_pokemon_const(
                old_line, entry.species_const, new_species
            )
            if new_line != old_line:
                lines[entry.line_index] = new_line
                files_written.add(entry.source_file)
                changed += 1
            else:
                self.log(
                    f"  [WARN] Could not replace {entry.species_const} in "
                    f"{entry.macro} on line {entry.line_index + 1}"
                )

        # ── 2 & 3. Text blocks (species name + type string) ───────────────
        for entry in text_lines:
            new_species_const = rand_starters[entry.slot_index].species_const

            if entry.line_type == 'species':
                new_display = POKEMON_DISPLAY_NAME.get(
                    new_species_const, new_species_const
                )
                old_display = entry.text_value
                if new_display == old_display:
                    continue
                lines = self._load_file(entry.source_file)
                old_line = lines[entry.line_index]
                # Replace the quoted name, preserving ", the" suffix
                new_line = old_line.replace(
                    f'"{old_display}, the"',
                    f'"{new_display}, the"',
                    1,
                )
                if new_line != old_line:
                    lines[entry.line_index] = new_line
                    files_written.add(entry.source_file)
                    changed += 1

            elif entry.line_type == 'type':
                new_type = POKEMON_PRIMARY_TYPE.get(
                    new_species_const, entry.text_value
                )
                old_type = entry.text_value
                if new_type == old_type:
                    continue
                lines = self._load_file(entry.source_file)
                old_line = lines[entry.line_index]
                # Replace the quoted type, preserving " #MON?" suffix
                new_line = old_line.replace(
                    f'"{old_type} #MON?"',
                    f'"{new_type} #MON?"',
                    1,
                )
                if new_line != old_line:
                    lines[entry.line_index] = new_line
                    files_written.add(entry.source_file)
                    changed += 1

        for sf in files_written:
            self._save_file(sf)

        self.log(
            f"  Starter dialogue: {changed} line(s) updated "
            f"in {len(files_written)} file(s)."
        )

    # -------------------------------------------------------------------------
    # Wild Pokemon
    # -------------------------------------------------------------------------

    def write_wild_encounters(self, original: list, randomized: list):
        """
        Replace species names in wild encounter blocks.
        Matches each slot in the randomized group to the corresponding
        source line by walking through the block and counting db-slot lines.
        """
        files_written = set()

        for orig_grp, rand_grp in zip(original, randomized):
            lines = self._load_file(orig_grp.source_file)
            rand_iter = iter(rand_grp.slots)

            for li in range(orig_grp.line_start, min(orig_grp.line_end + 1, len(lines))):
                line = lines[li]
                slot = self._parse_wild_slot_line_text(line)
                if slot is None:
                    continue
                try:
                    rand_slot = next(rand_iter)
                except StopIteration:
                    break
                if slot != rand_slot.species_const:
                    lines[li] = self._replace_pokemon_const(line, slot, rand_slot.species_const)

            files_written.add(orig_grp.source_file)

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Wild encounters updated in {len(files_written)} file(s).")

    def write_fish_encounters(self, original: list, randomized: list):
        """
        Replace species names in Crystal Legacy's data/wild/fish.asm.

        Fish slots may share a line_index (TimeFishGroups rows have two species
        per line: col=0 for day, col=1 for night).  We process slots in the
        order they appear, using count=1 replacement so that when two slots
        share a line we replace each species position independently without
        inadvertently clobbering the other position.

        Key invariant: slots in `original` and `randomized` are in the same
        order (produced by _parse_fish_asm which walks lines top-to-bottom),
        so iterating zip(original, randomized) visits each position in
        file order — meaning col=0 is always processed before col=1 for the
        same line.
        """
        files_written = set()

        for orig_slot, rand_slot in zip(original, randomized):
            lines = self._load_file(orig_slot.source_file)

            if orig_slot.line_index >= len(lines):
                continue

            old_species = orig_slot.species_const
            new_species = rand_slot.species_const

            # Always apply the replacement (even when old==new) using count=1
            # so that positional tracking stays correct for shared lines.
            # This is critical for TimeFishGroups rows where two slots share
            # the same line_index: the first replacement (col=0) consumes the
            # first occurrence of the old species; the second (col=1) then
            # finds and replaces the next occurrence.
            lines[orig_slot.line_index] = re.sub(
                r'\b' + re.escape(old_species) + r'\b',
                new_species,
                lines[orig_slot.line_index],
                count=1,
            )

            files_written.add(orig_slot.source_file)

        for sf in files_written:
            self._save_file(sf)

        changed = sum(
            1 for o, r in zip(original, randomized)
            if o.species_const != r.species_const
        )
        self.log(f"  Fish encounters updated: {changed} slot(s) changed in {len(files_written)} file(s).")

    def _parse_wild_slot_line_text(self, line: str) -> Optional[str]:
        """Extract species const from a wild slot line, or None if not a slot."""
        clean = re.sub(r';.*$', '', line).strip()
        m = re.match(r'db\s+\d+\s*,\s*([A-Z][A-Z0-9_]+)', clean)
        if m and m.group(1) in POKEMON_CONSTANTS:
            return m.group(1)
        return None

    # -------------------------------------------------------------------------
    # Trainers
    # -------------------------------------------------------------------------

    def write_trainers(self, original: list, randomized: list):
        """
        Replace species names in trainer party lines.
        Uses line-by-line comparison within each trainer's block.
        """
        files_written = set()

        for orig_tr, rand_tr in zip(original, randomized):
            lines = self._load_file(orig_tr.source_file)
            rand_iter = iter(rand_tr.party)

            for li in range(orig_tr.line_start, min(orig_tr.line_end + 1, len(lines))):
                line = lines[li]
                slot = self._parse_trainer_poke_line_text(line)
                if slot is None:
                    continue
                try:
                    rand_poke = next(rand_iter)
                except StopIteration:
                    break
                if slot != rand_poke.species_const:
                    lines[li] = self._replace_pokemon_const(line, slot, rand_poke.species_const)

            files_written.add(orig_tr.source_file)

        for sf in files_written:
            self._save_file(sf)
        self.log(f"  Trainer parties updated in {len(files_written)} file(s).")

    def _parse_trainer_poke_line_text(self, line: str) -> Optional[str]:
        """Extract species const from a trainer party db line."""
        clean = re.sub(r';.*$', '', line).strip()
        # Pattern: "db level, SPECIES[, ...]" but NOT "db -1" or "db NAME@"
        m = re.match(r'db\s+(\d+)\s*,\s*([A-Z][A-Z0-9_]+)', clean)
        if m and m.group(2) in POKEMON_CONSTANTS:
            return m.group(2)
        return None

    # -------------------------------------------------------------------------
    # In-game trades
    # -------------------------------------------------------------------------

    def write_trades(self, original: list, randomized: list):
        """
        Apply in-game trade changes to the output copy.

        Each InGameTrade stores the exact file path and line index for every
        field, so replacement is a direct targeted edit — no scanning needed.

        Special case: when given_line == requested_line (script-format
        `trade GIVEN, REQUESTED` on one line), both species are replaced
        on that single line sequentially.
        """
        files_written = set()
        changes = 0

        for orig, rand in zip(original, randomized):
            lines = self._load_file(orig.source_file)

            def patch(line_idx, do_it, apply_fn):
                """Apply apply_fn to lines[line_idx] if do_it and index valid."""
                if do_it and 0 <= line_idx < len(lines):
                    lines[line_idx] = apply_fn(lines[line_idx])
                    files_written.add(orig.source_file)

            # ── given species (what player receives) ──────────────────────
            given_changed = orig.given_species != rand.given_species
            patch(
                orig.given_line,
                given_changed,
                lambda ln: self._replace_pokemon_const(ln, orig.given_species,
                                                       rand.given_species),
            )
            if given_changed:
                changes += 1

            # ── requested species (what player gives) ─────────────────────
            req_changed = orig.requested_species != rand.requested_species
            if req_changed and orig.requested_line >= 0:
                if orig.requested_line == orig.given_line:
                    # Script `trade GIVEN, REQUESTED` — both on one line;
                    # given was already replaced above, now replace requested
                    # (use rand.given_species as old value in case it changed)
                    lines[orig.requested_line] = self._replace_pokemon_const(
                        lines[orig.requested_line],
                        orig.requested_species,
                        rand.requested_species,
                    )
                else:
                    lines[orig.requested_line] = self._replace_pokemon_const(
                        lines[orig.requested_line],
                        orig.requested_species,
                        rand.requested_species,
                    )
                files_written.add(orig.source_file)
                changes += 1

            # ── nickname ──────────────────────────────────────────────────
            patch(
                orig.nickname_line,
                rand.nickname and rand.nickname != orig.nickname,
                lambda ln: self._replace_quoted_string(ln, rand.nickname),
            )

            # ── OT name ───────────────────────────────────────────────────
            patch(
                orig.ot_line,
                rand.ot_name and rand.ot_name != orig.ot_name,
                lambda ln: self._replace_quoted_string(ln, rand.ot_name),
            )

            # ── DVs ───────────────────────────────────────────────────────
            patch(
                orig.dvs_line,
                rand.dvs_raw != orig.dvs_raw and orig.dvs_line >= 0,
                lambda ln: self._replace_dw_value(ln, rand.dvs_raw),
            )

            # ── item ──────────────────────────────────────────────────────
            patch(
                orig.item_line,
                rand.item != orig.item and orig.item_line >= 0,
                lambda ln: self._replace_pokemon_const(ln, orig.item, rand.item),
            )

            # ── gender constraint (npctrade same-line format) ─────────────
            # When species are randomized on a single-line npctrade macro,
            # relax TRADE_GENDER_MALE / TRADE_GENDER_FEMALE to TRADE_GENDER_EITHER
            # so the player can always trigger the trade regardless of gender.
            if (given_changed or req_changed) and orig.given_line >= 0:
                old_ln = lines[orig.given_line]
                new_ln = re.sub(
                    r'\bTRADE_GENDER_(MALE|FEMALE)\b',
                    'TRADE_GENDER_EITHER',
                    old_ln,
                )
                if new_ln != old_ln:
                    lines[orig.given_line] = new_ln
                    files_written.add(orig.source_file)

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  In-game trades: {changes} species change(s) across "
            f"{len(files_written)} file(s)."
        )

    # -------------------------------------------------------------------------
    # Static Pokemon
    # -------------------------------------------------------------------------

    def write_static_encounters(self, original: list, randomized: list):
        """
        Replace species constants for static encounter lines in the output copy.
        Each StaticEncounter stores the exact file path and line number, so
        replacement is a direct targeted edit — no scanning needed.
        """
        files_written = set()
        replaced = 0

        for orig, rand in zip(original, randomized):
            if orig.species_const == rand.species_const:
                continue  # unchanged — skip
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

    # -------------------------------------------------------------------------
    # Evolutions
    # -------------------------------------------------------------------------

    # Regex that captures all parts of an evolve macro call so we can
    # rebuild it with different type/param fields.
    # Groups: (1) "evolve " keyword+whitespace, (2) type, (3) ", " separator,
    #         (4) target species, (5) ", " separator, (6) param token
    # Crystal Legacy / pret-disassembly format: db EVOLVE_TYPE, PARAM, SPECIES
    # Groups: (1)prefix  (2)TYPE  (3)sep  (4)PARAM  (5)sep  (6)SPECIES
    _EVOLVE_LINE_RE = re.compile(
        r'(\bdb\s+)(EVOLVE_[A-Z_]+)(\s*,\s*)([A-Z0-9_-]+)(\s*,\s*)([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    def write_evolutions(self, original: list, modified: list):
        """
        Rewrite evolution entries in the output copy where type or param changed.

        original and modified are both lists of EvolutionEntry.
        Only lines where (evo_type, param) actually changed are touched.
        """
        files_written = set()
        replaced = 0

        for orig, mod in zip(original, modified):
            if orig.evo_type == mod.evo_type and orig.param == mod.param:
                continue   # nothing changed for this entry

            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._rewrite_evolve_line(old_line, mod.evo_type, mod.param)

            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                replaced += 1
            else:
                self.log(
                    f"  [WARN] Could not rewrite evolution on line "
                    f"{orig.line_index + 1} of "
                    f"{os.path.relpath(orig.source_file, self.source_dir)}"
                )

        for sf in files_written:
            self._save_file(sf)
        self.log(
            f"  Evolutions: {replaced} line(s) updated across "
            f"{len(files_written)} file(s)."
        )

    # -------------------------------------------------------------------------
    # Shared utility
    # -------------------------------------------------------------------------

    def _rewrite_evolve_line(self, line: str, new_type: str, new_param: str) -> str:
        """
        Replace the type and param fields in a ``db EVOLVE_TYPE, PARAM, SPECIES``
        line, preserving all surrounding whitespace and comments.
        Groups: (1)prefix (2)TYPE (3)sep (4)PARAM (5)sep (6)SPECIES
        """
        def repl(m):
            # m.group(6) is the target species — always kept unchanged
            return (m.group(1) + new_type + m.group(3)
                    + new_param + m.group(5) + m.group(6))
        return self._EVOLVE_LINE_RE.sub(repl, line, count=1)

    def _replace_givepoke_item(self, line: str, old_item: str, new_item: str) -> str:
        """
        Replace the item argument (3rd field) in a givepoke macro call.
        Pattern: ``givepoke SPECIES, level, OLD_ITEM``
        Uses a targeted regex to avoid colliding with the species or level fields.
        """
        pattern = (
            r'(givepoke\s+[A-Z][A-Z0-9_]+\s*,\s*\d+\s*,\s*)'
            + re.escape(old_item)
            + r'\b'
        )
        return re.sub(pattern, r'\g<1>' + new_item, line, count=1, flags=re.IGNORECASE)

    def _replace_pokemon_const(self, line: str, old_const: str, new_const: str) -> str:
        """Replace a Pokemon constant name in a line, preserving whitespace."""
        # Use word-boundary replacement to avoid partial matches (e.g. MEW vs MEWTWO)
        return re.sub(r'\b' + re.escape(old_const) + r'\b', new_const, line)

    def _replace_quoted_string(self, line: str, new_value: str) -> str:
        """
        Replace the first @-terminated quoted string in a line.
        Crystal text strings end with @ as a terminator, e.g. db "MARC@".
        Handles both padded ("MARC     @") and unpadded ("MARC@") forms.
        """
        return re.sub(r'"[^"]*@"', f'"{new_value}@"', line, count=1)

    def _replace_dw_value(self, line: str, new_value: str) -> str:
        """Replace the operand of a 'dw VALUE' line with new_value."""
        # Matches `  dw $XXXX  ; comment` or `  dw 0` etc.
        return re.sub(
            r'(^\s+dw\s+)\S+',
            lambda m: m.group(1) + new_value,
            line,
        )

    # -------------------------------------------------------------------------
    # TM/HM compatibility
    # -------------------------------------------------------------------------

    def write_tmhm_compat(self, original: list, modified: list):
        """
        Rewrite the ``tmhm`` macro line for Pokémon whose learnset changed.

        The line is reconstructed with the same leading indentation as the
        original so the diff stays minimal.  Any trailing ``; comment`` on the
        original line is preserved.
        """
        if not original or not modified:
            return

        files_written = set()
        changed = 0
        for orig, mod in zip(original, modified):
            if set(orig.moves) == set(mod.moves):
                continue   # nothing to change

            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]

            # Preserve original indentation
            indent = len(old_line) - len(old_line.lstrip())
            indent_str = old_line[:indent]

            # Preserve any trailing comment from the original line
            comment_m = re.search(r'\s*(;.*)$', old_line)
            comment   = ('  ' + comment_m.group(1).rstrip()) if comment_m else ''

            new_line = f"{indent_str}tmhm {', '.join(mod.moves)}{comment}\n"
            lines[orig.line_index] = new_line
            files_written.add(orig.source_file)
            changed += 1

        for sf in files_written:
            self._save_file(sf)

        self.log(f"  Updated TM/HM compatibility for {changed} Pokémon.")

    # -------------------------------------------------------------------------
    # Wild held items
    # -------------------------------------------------------------------------

    def write_wild_held_items(self, original: list, randomized: list):
        """
        Replace wild Pokémon held items in the output copy of the held-items file.

        Each WildHeldItemEntry carries its source_file, line_index, and the
        original line text.  We replace COMMON_ITEM and RARE_ITEM in-place using
        a targeted regex that anchors on the species constant, so we never touch
        unrelated lines.
        """
        if not original or not randomized:
            return

        files_written = set()
        changed = 0
        for orig, rand in zip(original, randomized):
            if orig.common_item == rand.common_item and orig.rare_item == rand.rare_item:
                continue   # nothing changed

            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]
            new_line = self._replace_held_items_line(
                old_line,
                orig.species_const,
                rand.common_item,
                rand.rare_item,
                orig.common_item,
                orig.rare_item,
            )
            if new_line != old_line:
                lines[orig.line_index] = new_line
                files_written.add(orig.source_file)
                changed += 1
            else:
                self.log(
                    f"  [WARN] Could not replace held items for {orig.species_const} "
                    f"on line {orig.line_index + 1}"
                )

        for sf in files_written:
            self._save_file(sf)

        self.log(f"  Updated {changed} wild held item line(s).")

    # Two-item format: db SPECIES, COMMON, RARE
    _HELD_ITEM_TWO_RE = re.compile(
        r'^(\s*db\s+[A-Z][A-Z0-9_]*\s*,\s*)([A-Z_][A-Z0-9_]*)(\s*,\s*)([A-Z_][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    # One-item format: db SPECIES, ITEM
    _HELD_ITEM_ONE_RE = re.compile(
        r'^(\s*db\s+[A-Z][A-Z0-9_]*\s*,\s*)([A-Z_][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    def _replace_held_items_line(self, line: str,
                                  species_const: str,
                                  new_common: str,
                                  new_rare: str,
                                  old_common: str,
                                  old_rare: str) -> str:
        """Replace held item constants in a wild held-items line."""
        # Try two-item format first
        m = self._HELD_ITEM_TWO_RE.match(line)
        if m:
            return m.group(1) + new_common + m.group(3) + new_rare + line[m.end():]
        # Fall back to one-item format
        m = self._HELD_ITEM_ONE_RE.match(line)
        if m:
            return m.group(1) + new_common + line[m.end():]
        return line   # no match — leave unchanged

    # -------------------------------------------------------------------------
    # Field items
    # -------------------------------------------------------------------------

    # Matches:  finditem ITEM   or   itemball ITEM
    _VISIBLE_FIELD_RE = re.compile(
        r'^(\s*(?:finditem|itemball)\s+)([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    # Matches:  hiddenitem ITEM, ...
    _HIDDEN_FIELD_RE = re.compile(
        r'^(\s*hiddenitem\s+)([A-Z][A-Z0-9_]*)',
        re.IGNORECASE,
    )

    def write_field_items(self, original: list, modified: list):
        """
        Replace field item constants in the output copy of each script file.

        Both visible (finditem/itemball) and hidden (hiddenitem) macros are
        handled.  The substitution only touches the item constant — all
        surrounding whitespace, arguments, and comments are preserved.
        """
        if not original or not modified:
            return

        files_written = set()
        changed = 0

        for orig, mod in zip(original, modified):
            if orig.item_const == mod.item_const:
                continue  # unchanged

            lines = self._load_file(orig.source_file)
            old_line = lines[orig.line_index]

            if orig.item_type == "visible":
                pattern = self._VISIBLE_FIELD_RE
            else:
                pattern = self._HIDDEN_FIELD_RE

            m = pattern.match(old_line)
            if m:
                # Replace only the item constant; preserve everything after
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
    # Starting items (bag + PC)
    # -------------------------------------------------------------------------

    def write_starting_items(self, bag_items: list, pc_items: list, intro_menu_src_path: str):
        """
        Inject custom starting bag, PC, and TM/HM items into intro_menu.asm.

        bag_items / pc_items: list of {"const": "ITEM_CONST", "qty": N} dicts
        intro_menu_src_path:  absolute path to the file in the SOURCE tree

        Crystal Legacy has four bag pockets, each backed by separate WRAM:
          ITEM_POCKET    — wNumItems / wItems        (item_id, qty pairs)
          BALL_POCKET    — wNumBalls / wBalls        (item_id, qty pairs)
          KEY_ITEM_POCKET — wNumKeyItems / wKeyItems  (item_id only, no qty)
          TM_HM_POCKET   — wTMsHMs byte array        (qty at 0-based TMNUM index)

        Strategy
        --------
        _ResetWRAM calls .InitList for each pocket count byte in sequence:
            ld hl, wNumItems     ; call .InitList
            ld hl, wNumKeyItems  ; call .InitList
            ld hl, wNumBalls     ; call .InitList
            ld hl, wNumPCItems   ; call .InitList
        We replace each .InitList call with our custom loader, and inject
        TM/HM setup inline alongside the items-pocket replacement.
        All data tables and subroutines are appended at the end of the file.

        GBZ80 subroutines added
        -----------------------
        RandomizerLoadItemList  (items / balls / PC)
          hl = source table (db ITEM, QTY … db $ff)
          de = count byte (wNumItems, wNumBalls, or wNumPCItems)

        RandomizerLoadKeyItemList  (key items)
          hl = source table (db ITEM_ID … db $ff)
          writes to wNumKeyItems / wKeyItems directly

        RandomizerLoadTMHMList  (TM/HM pocket)
          hl = source table (db TMNUM, QTY … db $ff)
          writes quantities to wTMsHMs[TMNUM-1]
        """
        if not bag_items and not pc_items:
            return

        # ── Categorize bag items by pocket ────────────────────────────────────
        items_pocket = [i for i in bag_items
                        if i["const"] not in BALL_ITEM_CONSTS
                        and i["const"] not in KEY_ITEM_CONSTS
                        and i["const"] not in TM_HM_ITEM_CONSTS]
        balls_pocket = [i for i in bag_items if i["const"] in BALL_ITEM_CONSTS]
        key_pocket   = [i for i in bag_items if i["const"] in KEY_ITEM_CONSTS]
        tmhm_pocket  = [i for i in bag_items if i["const"] in TM_HM_ITEM_CONSTS]

        # Validate / clamp per-pocket limits
        MAX_ITEMS   = 84   # wItems: MAX_ITEMS * 2 + 1
        MAX_BALLS   = 12   # MAX_BALLS constant
        MAX_KEY     = 25   # MAX_KEY_ITEMS constant
        MAX_PC      = 50
        items_pocket = [i for i in items_pocket if 1 <= int(i["qty"]) <= 99][:MAX_ITEMS]
        balls_pocket = [i for i in balls_pocket if 1 <= int(i["qty"]) <= 99][:MAX_BALLS]
        key_pocket   = [i for i in key_pocket   if 1 <= int(i["qty"]) <= 99][:MAX_KEY]
        tmhm_pocket  = [i for i in tmhm_pocket  if 1 <= int(i["qty"]) <= 99]
        pc_items     = [i for i in pc_items     if 1 <= int(i["qty"]) <= 99][:MAX_PC]

        out_path = self._get_output_path(intro_menu_src_path)
        if not os.path.isfile(out_path):
            self.log(f"  [WARN] intro_menu.asm not found in output — skipping starting items.")
            return

        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        # ── 1. Patch each pocket's .InitList call site ────────────────────────
        # Items pocket — also inline TM/HM load if any TMs/HMs were requested
        bag_pattern = re.compile(
            r'([ \t]+ld\s+hl,\s+wNumItems[ \t]*\n[ \t]+)call\s+\.InitList',
        )
        balls_pattern = re.compile(
            r'([ \t]+ld\s+hl,\s+wNumBalls[ \t]*\n[ \t]+)call\s+\.InitList',
        )
        key_pattern = re.compile(
            r'([ \t]+ld\s+hl,\s+wNumKeyItems[ \t]*\n[ \t]+)call\s+\.InitList',
        )
        pc_pattern = re.compile(
            r'([ \t]+ld\s+hl,\s+wNumPCItems[ \t]*\n[ \t]+)call\s+\.InitList',
        )

        def _bag_repl(m):
            indent = re.match(r'[ \t]+', m.group(1)).group()
            lines = [
                f"{indent}ld hl, RandomizerStartItemData",
                f"{indent}ld de, wNumItems",
                f"{indent}call RandomizerLoadItemList",
            ]
            # TM/HM injection is appended here so it runs right after items init
            if tmhm_pocket:
                lines += [
                    f"{indent}ld hl, RandomizerStartTMHMData",
                    f"{indent}call RandomizerLoadTMHMList",
                ]
            return "\n".join(lines)

        def _balls_repl(m):
            indent = re.match(r'[ \t]+', m.group(1)).group()
            return (
                f"{indent}ld hl, RandomizerStartBallData\n"
                f"{indent}ld de, wNumBalls\n"
                f"{indent}call RandomizerLoadItemList"
            )

        def _key_repl(m):
            indent = re.match(r'[ \t]+', m.group(1)).group()
            return (
                f"{indent}ld hl, RandomizerStartKeyItemData\n"
                f"{indent}call RandomizerLoadKeyItemList"
            )

        def _pc_repl(m):
            indent = re.match(r'[ \t]+', m.group(1)).group()
            return (
                f"{indent}ld hl, RandomizerStartPCData\n"
                f"{indent}ld de, wNumPCItems\n"
                f"{indent}call RandomizerLoadItemList"
            )

        new_text, bag_subs   = bag_pattern.subn(_bag_repl,   text)
        new_text, balls_subs = balls_pattern.subn(_balls_repl, new_text)
        new_text, key_subs   = key_pattern.subn(_key_repl,   new_text)
        new_text, pc_subs    = pc_pattern.subn(_pc_repl,     new_text)

        any_patched = bag_subs or balls_subs or key_subs or pc_subs
        if not any_patched:
            self.log("  [WARN] No .InitList injection points found — starting items skipped.")
            return

        if bag_subs:   self.log("  ✓ Items pocket injection point patched.")
        else:          self.log("  [WARN] wNumItems .InitList not found — items pocket skipped.")
        if balls_subs: self.log("  ✓ Balls pocket injection point patched.")
        else:          self.log("  [WARN] wNumBalls .InitList not found — balls pocket skipped.")
        if key_subs:   self.log("  ✓ Key items injection point patched.")
        else:          self.log("  [WARN] wNumKeyItems .InitList not found — key items skipped.")
        if pc_subs:    self.log("  ✓ PC items injection point patched.")
        else:          self.log("  [WARN] wNumPCItems .InitList not found — PC items skipped.")

        # ── 2. Build data tables ──────────────────────────────────────────────
        def _item_table(items):
            """(ITEM_CONST, QTY) pairs terminated by $ff — for items/balls/PC pockets."""
            rows = "".join(f"\tdb {i['const']}, {int(i['qty'])}\n" for i in items)
            return rows + "\tdb $ff\n"

        def _key_table(items):
            """Item IDs only (no qty) terminated by $ff — for key items pocket."""
            rows = "".join(f"\tdb {i['const']}\n" for i in items)
            return rows + "\tdb $ff\n"

        def _tmhm_table(items):
            """(TMNUM_SYMBOL, QTY) pairs terminated by $ff — for wTMsHMs array."""
            rows = ""
            for i in items:
                sym = TM_HM_TMNUM_SYMBOLS.get(i["const"])
                if sym:
                    rows += f"\tdb {sym}, {int(i['qty'])}\n"
            return rows + "\tdb $ff\n"

        # ── 3. Build all subroutines ──────────────────────────────────────────
        # Shared item/qty-pair loader (items pocket, balls pocket, PC pocket)
        rll_sub = (
            "RandomizerLoadItemList:\n"
            "; hl = source table (db ITEM, QTY ... db $ff)\n"
            "; de = destination count byte (wNumItems, wNumBalls, or wNumPCItems)\n"
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

        # Key items loader (item IDs only, no qty)
        rkl_sub = (
            "RandomizerLoadKeyItemList:\n"
            "; hl = source table (db ITEM_ID ... db $ff)\n"
            "; writes to wNumKeyItems / wKeyItems\n"
            "\tld de, wNumKeyItems\n"
            "\tpush de\n"
            "\tinc de\n"
            "\txor a\n"
            "\tld b, a\n"
            ".rkl_loop:\n"
            "\tld a, [hli]\n"
            "\tcp $ff\n"
            "\tjr z, .rkl_done\n"
            "\tld [de], a\n"
            "\tinc de\n"
            "\tinc b\n"
            "\tjr .rkl_loop\n"
            ".rkl_done:\n"
            "\tld a, $ff\n"
            "\tld [de], a\n"
            "\tpop de\n"
            "\tld a, b\n"
            "\tld [de], a\n"
            "\tret\n"
        )

        # TM/HM loader (writes qty to wTMsHMs[TMNUM-1])
        rtm_sub = (
            "RandomizerLoadTMHMList:\n"
            "; hl = source table (db TMNUM, QTY ... db $ff)\n"
            "; sets wTMsHMs[TMNUM-1] = QTY for each entry\n"
            ".rtm_loop:\n"
            "\tld a, [hli]\n"
            "\tcp $ff\n"
            "\tret z\n"
            "\tdec a\n"
            "\tld c, a\n"
            "\tld b, 0\n"
            "\tld a, [hli]\n"
            "\tpush hl\n"
            "\tld hl, wTMsHMs\n"
            "\tadd hl, bc\n"
            "\tld [hl], a\n"
            "\tpop hl\n"
            "\tjr .rtm_loop\n"
        )

        # ── 4. Assemble final append block ────────────────────────────────────
        append = "\n; ---- Randomizer: starting item injection ----------------------------\n"

        append += "RandomizerStartItemData:\n"    + _item_table(items_pocket)
        append += "RandomizerStartBallData:\n"    + _item_table(balls_pocket)
        append += "RandomizerStartKeyItemData:\n" + _key_table(key_pocket)
        if tmhm_pocket:
            append += "RandomizerStartTMHMData:\n" + _tmhm_table(tmhm_pocket)
        append += "RandomizerStartPCData:\n"      + _item_table(pc_items)
        append += "\n"
        append += rll_sub + "\n"
        if key_subs:
            append += rkl_sub + "\n"
        if tmhm_pocket:
            append += rtm_sub + "\n"

        # ── 5. Write out ──────────────────────────────────────────────────────
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += append

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(new_text)

        # Logging summary
        def _fmt(items, names=None):
            if not items:
                return "(none)"
            return ", ".join(f"{i['const']}×{i['qty']}" for i in items)

        self.log(f"  Items pocket  : {_fmt(items_pocket)}")
        self.log(f"  Balls pocket  : {_fmt(balls_pocket)}")
        self.log(f"  Key Items     : {_fmt(key_pocket)}")
        self.log(f"  TMs / HMs     : {_fmt(tmhm_pocket)}")
        self.log(f"  PC Items      : {_fmt(pc_items)}")

    # -------------------------------------------------------------------------
    # PC Pokémon SRAM injection
    # -------------------------------------------------------------------------

    # Crystal GBC text encoding table
    _CRYSTAL_CHARMAP = dict(
        **{chr(0x41 + i): 0x80 + i for i in range(26)},   # A-Z → $80-$99
        **{chr(0x61 + i): 0xA0 + i for i in range(26)},   # a-z → $A0-$B9
        **{chr(0x30 + i): 0xF6 + i for i in range(10)},   # 0-9 → $F6-$FF
        **{' ': 0x7F, '.': 0xE8, ',': 0xF0, "'": 0xE2,
           '-': 0xE3, '!': 0xE9, '?': 0xEA,
           '♂': 0xEF, '♀': 0xF5},                # ♂ ♀
    )
    _CRYSTAL_TERM = 0x50  # string terminator
    _CRYSTAL_FILL = 0xFF  # padding after terminator

    # Default Crystal-style uppercase names for species with special chars
    _SPECIES_NAME_OVERRIDES = {
        'NIDORAN_F': 'NIDORAN♀',
        'NIDORAN_M': 'NIDORAN♂',
        'FARFETCH_D': "FARFETCH'D",
        'MR__MIME':  'MR. MIME',
        'HO_OH':     'HO-OH',
    }

    def _encode_crystal_str(self, s: str, length: int) -> list:
        """Encode *s* in Crystal GBC character set, pad to exactly *length* bytes."""
        result = []
        for ch in s[:length - 1]:
            result.append(self._CRYSTAL_CHARMAP.get(ch, 0x7F))
        result.append(self._CRYSTAL_TERM)
        while len(result) < length:
            result.append(self._CRYSTAL_FILL)
        return result

    def _species_default_name(self, species_const: str) -> str:
        """Return the default uppercase display name for a species constant."""
        if species_const in self._SPECIES_NAME_OVERRIDES:
            return self._SPECIES_NAME_OVERRIDES[species_const]
        return species_const.replace('_', ' ').strip()[:10]

    def _load_move_pp_table(self) -> dict:
        """Parse data/moves/moves.asm and return {MOVE_CONST: pp_value} dict."""
        moves_path = os.path.join(self.source_dir, "data", "moves", "moves.asm")
        if not os.path.isfile(moves_path):
            moves_path = os.path.join(self.source_dir, "data", "move", "moves.asm")
        pp = {}
        if not os.path.isfile(moves_path):
            return pp
        pat = re.compile(
            r'^\s+move\s+(\w+)\s*,\s*\w+\s*,\s*\d+\s*,\s*\w+\s*,\s*\d+\s*,\s*(\d+)',
            re.MULTILINE,
        )
        with open(moves_path, 'r', encoding='utf-8', errors='replace') as fh:
            for m in pat.finditer(fh.read()):
                pp[m.group(1)] = int(m.group(2))
        return pp

    def _gen_mon_writes(self, box_prefix: str, mon_num: int, mon: dict,
                        pp_table: dict) -> list:
        """
        Return a list of ASM instruction strings for one box Pokémon.

        box_prefix: SRAM symbol prefix, e.g. 'sBox1' or 'sBox' (active box).
        mon_num:    1-based index within the box (matches the sBox*Mon{n} names).
        """
        lines = []
        species  = mon.get('species', 'BULBASAUR')
        item     = (mon.get('heldItem') or '').strip()
        moves    = list(mon.get('moves') or [])
        while len(moves) < 4:
            moves.append('NO_MOVE')
        level   = max(1, min(100, int(mon.get('level') or 5)))
        dv_atk  = max(0, min(15, int(mon.get('dvAtk') or 15)))
        dv_def  = max(0, min(15, int(mon.get('dvDef') or 15)))
        dv_spd  = max(0, min(15, int(mon.get('dvSpd') or 15)))
        dv_spc  = max(0, min(15, int(mon.get('dvSpc') or 15)))
        nickname = (mon.get('nickname') or '').strip()
        if not nickname:
            nickname = self._species_default_name(species)

        # Experience: level³ (Medium Fast approximation)
        exp      = level ** 3
        exp_b2   = (exp >> 16) & 0xFF
        exp_b1   = (exp >>  8) & 0xFF
        exp_b0   =  exp        & 0xFF

        # PP for each move
        pp_vals = [
            pp_table.get(mv, 35) if (mv and mv != 'NO_MOVE') else 0
            for mv in moves
        ]

        # Packed DVs
        dv1 = (dv_atk << 4) | dv_def
        dv2 = (dv_spd << 4) | dv_spc

        # CaughtLevel byte: low 6 bits = level (capped at 63), high 2 = 0 (morning)
        caught_lv = min(63, level)

        # OT name: "TRAINER" in Crystal encoding
        ot_bytes   = self._encode_crystal_str('TRAINER', 11)
        nick_bytes = self._encode_crystal_str(nickname.upper(), 11)

        # Symbol names use the box_prefix, e.g. sBox1Mon1 or sBoxMon1
        mon_sym  = f'{box_prefix}Mon{mon_num}'

        lines.append(f'\t; {mon_sym}: {species} Lv{level}')
        lines.append(f'\tld hl, {mon_sym}')

        # byte 00: Species
        lines.append(f'\tld a, {species}')
        lines.append('\tld [hli], a')

        # byte 01: Item
        if item and item != 'NO_ITEM':
            lines.append(f'\tld a, {item}')
        else:
            lines.append('\txor a')
        lines.append('\tld [hli], a')

        # bytes 02-05: Moves
        for mv in moves:
            if mv and mv != 'NO_MOVE':
                lines.append(f'\tld a, {mv}')
            else:
                lines.append('\txor a')
            lines.append('\tld [hli], a')

        # bytes 06-07: OT ID  (placeholder 0; patched from wPlayerID below)
        lines.append('\txor a')
        lines.append('\tld [hli], a')
        lines.append('\tld [hli], a')

        # bytes 08-0A: Exp (3 bytes big-endian)
        lines.append(f'\tld a, ${exp_b2:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${exp_b1:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${exp_b0:02x}')
        lines.append('\tld [hli], a')

        # bytes 0B-14: Stat EXP (10 bytes of 0)
        lines.append('\txor a')
        for _ in range(10):
            lines.append('\tld [hli], a')

        # bytes 15-16: DVs
        lines.append(f'\tld a, ${dv1:02x}')
        lines.append('\tld [hli], a')
        lines.append(f'\tld a, ${dv2:02x}')
        lines.append('\tld [hli], a')

        # bytes 17-1A: PP
        for pp in pp_vals:
            lines.append(f'\tld a, {pp}')
            lines.append('\tld [hli], a')

        # byte 1B: Happiness
        lines.append('\tld a, 70')
        lines.append('\tld [hli], a')

        # byte 1C: Pokerus
        lines.append('\txor a')
        lines.append('\tld [hli], a')

        # byte 1D: CaughtLevel (low 6 bits = level; high 2 = time, 0=morning)
        lines.append(f'\tld a, {caught_lv}')
        lines.append('\tld [hli], a')

        # byte 1E: CaughtLocation
        lines.append('\tld a, LANDMARK_GIFT')
        lines.append('\tld [hli], a')

        # byte 1F: Level
        lines.append(f'\tld a, {level}')
        lines.append('\tld [hli], a')

        # Patch OT ID from wPlayerID (so the mon obeys the player)
        lines.append(f'\tld hl, {mon_sym}ID')
        lines.append('\tld a, [wPlayerID]')
        lines.append('\tld [hli], a')
        lines.append('\tld a, [wPlayerID + 1]')
        lines.append('\tld [hl], a')

        # Write OT name
        lines.append(f'\tld hl, {mon_sym}OT')
        for b in ot_bytes:
            lines.append(f'\tld a, ${b:02x}')
            lines.append('\tld [hli], a')

        # Write nickname
        lines.append(f'\tld hl, {mon_sym}Nickname')
        for b in nick_bytes:
            lines.append(f'\tld a, ${b:02x}')
            lines.append('\tld [hli], a')

        return lines

    def _gen_box_writes(self, box_prefix: str, box_n: int, mons: list,
                        pp_table: dict) -> list:
        """
        Return ASM lines that initialise one PC box.

        box_prefix: SRAM symbol prefix, e.g. 'sBox1' for archived box 1 or
                    'sBox' for the active box.
        box_n:      The 1-based box number (used only for labelling comments and
                    for the per-mon symbol names when targeting archived boxes).
                    For the active-box writes (box_prefix='sBox') pass box_n=1
                    and the struct names use 'sBoxMon1', 'sBoxMon1OT', etc.
        """
        lines = []
        n = len(mons)
        lines.append(f'\t; {box_prefix}: {n} mon(s)')
        lines.append(f'\tld a, {n}')
        lines.append(f'\tld [{box_prefix}Count], a')
        # Species array + $FF terminator
        for i, mon in enumerate(mons):
            lines.append(f'\tld a, {mon["species"]}')
            lines.append(f'\tld [{box_prefix}Species + {i}], a')
        lines.append('\tld a, $ff')
        lines.append(f'\tld [{box_prefix}Species + {n}], a')
        # Per-mon struct, OT, nickname
        for idx, mon in enumerate(mons):
            lines.extend(self._gen_mon_writes(box_prefix, idx + 1, mon, pp_table))
        return lines

    def write_pc_pokemon(self, pc_mons: list, intro_menu_src_path: str):
        """
        Inject a GBZ80 subroutine into intro_menu.asm that writes user-specified
        Pokémon into PC boxes during new-game initialisation (_ResetWRAM).

        Crystal's PC storage system uses an "active box" (sBox) as the working
        copy of whatever box is currently selected (wCurBox).  On a new game,
        wCurBox=0 (box 1) and _ResetWRAM clears sBox to empty.  The box-display
        code reads sBox for the current box, not sBox1 directly — so we must
        write box-1 data to BOTH sBox (active) and sBox1 (archived).  Boxes 2-14
        only need the archived write.
        """
        if not pc_mons:
            return

        # Group by box number (1–14); cap each box at 20 mons
        box_mons: dict[int, list] = {}
        for mon in pc_mons:
            try:
                box = int(mon.get('box', 1))
                if not (1 <= box <= 14):
                    continue
                if not mon.get('species'):
                    continue
                box_mons.setdefault(box, [])
                if len(box_mons[box]) < 20:
                    box_mons[box].append(mon)
            except (ValueError, TypeError):
                continue

        if not box_mons:
            return

        pp_table = self._load_move_pp_table()

        out_path = self._get_output_path(intro_menu_src_path)
        with open(out_path, 'r', encoding='utf-8', errors='replace') as fh:
            text = fh.read()

        # Injection point: just before the `ret` that ends _ResetWRAM.
        # The function's last two meaningful lines are:
        #     call ResetGameTime
        #     ret
        injection_pat = re.compile(
            r'(\tcall ResetGameTime\n)(\tret\n)',
            re.MULTILINE,
        )
        if not injection_pat.search(text):
            self.log(
                "[WARN] Could not find _ResetWRAM injection point in intro_menu.asm"
                " — PC Pokémon injection skipped."
            )
            return

        self.log("  ✓ _ResetWRAM injection point found and patched.")
        # Use callfar: the routine lives in its own floating ROMX section
        # (see below), which the linker may place in a different bank than
        # intro_menu.asm.  A plain `call` only reaches the same bank / home,
        # so it would jump to the wrong bank for large mon lists.
        new_text = injection_pat.sub(
            r'\1\tcallfar RandomizerInitPCMons\n\2', text, count=1
        )

        # Split boxes into the two SRAM banks (1-7 share a bank, 8-14 share another)
        bank2 = {n: m for n, m in box_mons.items() if 1 <= n <= 7}
        bank3 = {n: m for n, m in box_mons.items() if 8 <= n <= 14}

        # Own floating section so a large routine can't overflow intro_menu's bank.
        asm = ['; ---- Randomizer: PC Pokémon injection ----',
               'SECTION "Randomizer PC Mons", ROMX',
               'RandomizerInitPCMons::']

        if bank2:
            asm.append('\tld a, BANK(sBox1)')
            asm.append('\tcall OpenSRAM')
            for box_n in sorted(bank2):
                asm.extend(self._gen_box_writes(f'sBox{box_n}', box_n,
                                                bank2[box_n], pp_table))
            asm.append('\tcall CloseSRAM')

        if bank3:
            asm.append('\tld a, BANK(sBox8)')
            asm.append('\tcall OpenSRAM')
            for box_n in sorted(bank3):
                asm.extend(self._gen_box_writes(f'sBox{box_n}', box_n,
                                                bank3[box_n], pp_table))
            asm.append('\tcall CloseSRAM')

        # --- Active box (sBox) patch ---
        # On a new game, wCurBox=0 (box 1) and _ResetWRAM empties sBox.
        # The PC storage system displays sBox for the current box, so box-1
        # data must ALSO be written to sBox (active box).  Without this, the
        # player sees an empty box 1 until they switch away and back.
        if 1 in box_mons:
            asm.append('\t; Also populate sBox (active box) so box 1 is visible immediately')
            asm.append('\tld a, BANK(sBox)')
            asm.append('\tcall OpenSRAM')
            asm.extend(self._gen_box_writes('sBox', 1, box_mons[1], pp_table))
            asm.append('\tcall CloseSRAM')

        asm.append('\tret')

        if not new_text.endswith('\n'):
            new_text += '\n'
        new_text += '\n'.join(asm) + '\n'

        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(new_text)

        total = sum(len(m) for m in box_mons.values())
        self.log(f"  PC Pokémon: {total} Pokémon across {len(box_mons)} box(es)")

    # -------------------------------------------------------------------------
    # Shop item patches (Zero Grinding / Elite 4 Prep)
    # -------------------------------------------------------------------------

    def _patch_item_prices(self, attrs_src: str, price_map: dict):
        """
        Set buy prices for named items in data/items/attributes.asm.
        price_map: { "ITEM_CONST_NAME": price_int, ... }
        Each entry in attributes.asm looks like:
            ; ITEM_CONST_NAME
                item_attribute PRICE, ...
        """
        lines    = self._load_file(attrs_src)
        remaining = set(price_map.keys())
        for i, line in enumerate(lines):
            for item_const in list(remaining):
                if f"; {item_const}" in line:
                    next_i = i + 1
                    if next_i < len(lines):
                        m = re.match(r'(\s*item_attribute\s+)(\d+)(,.*)', lines[next_i])
                        if m:
                            lines[next_i] = m.group(1) + str(price_map[item_const]) + m.group(3)
                            self.log(f"  {item_const} price → ${price_map[item_const]}")
                            remaining.discard(item_const)
        for item_const in remaining:
            self.log(f"  [WARN] Could not find {item_const} in attributes.asm — price unchanged")

    def _add_items_to_mart(self, marts_src: str, mart_label_substr: str, item_consts: list):
        """
        Add items to ALL marts whose label contains mart_label_substr
        (case-insensitive).  Some shops have multiple definitions for different
        game states (e.g. Cherrygrove before/after the opening sequence) — every
        matching definition is patched.  Items already present in a mart are skipped.
        """
        lines = self._load_file(marts_src)
        found = 0

        # Collect all matching mart start indices first (scanning forward only)
        i = 0
        offset = 0  # cumulative line offset from insertions
        starts = []
        for idx, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.endswith(':') and mart_label_substr.lower() in stripped.lower():
                starts.append(idx)

        if not starts:
            self.log(f"  [WARN] No mart matching '{mart_label_substr}' found in marts.asm")
            return

        # Process each match; track insertion offset so indices stay valid
        inserted_so_far = 0
        for raw_start in starts:
            start = raw_start + inserted_so_far
            mart_name = lines[start].rstrip().rstrip(':')

            # Find db -1 terminator
            end = None
            for j in range(start + 1, len(lines)):
                if re.match(r'\s*db\s+-1', lines[j]):
                    end = j
                    break
            if end is None:
                self.log(f"  [WARN] Could not find terminator for {mart_name} — skipped")
                continue

            # Items already in this mart definition
            existing = set()
            for k in range(start + 1, end):
                m = re.match(r'\s*db\s+(\w+)', lines[k])
                if m:
                    existing.add(m.group(1))

            to_add = [ic for ic in item_consts if ic not in existing]
            if not to_add:
                self.log(f"  {mart_name}: all items already present — skipped")
                continue

            # Increment the item count line (immediately after the label)
            count_i = start + 1
            mc = re.match(r'(\s*db\s+)(\d+)(\s*;.*)', lines[count_i])
            if mc:
                lines[count_i] = mc.group(1) + str(int(mc.group(2)) + len(to_add)) + mc.group(3)

            # Insert new items just before db -1
            indent = re.match(r'(\s*)', lines[end]).group(1)
            for ic in reversed(to_add):
                lines.insert(end, indent + f"db {ic}\n")
                self.log(f"  Added {ic} to {mart_name}")

            inserted_so_far += len(to_add)
            found += 1

        if found == 0:
            self.log(f"  [WARN] Could not patch any mart matching '{mart_label_substr}'")

    def write_zero_grinding(self):
        """
        Zero Grinding: add Rare Candy ($10) to the Cherrygrove Mart so it is
        purchasable from the very start of the game.
        """
        attrs_src = os.path.join(self.source_dir, "data", "items", "attributes.asm")
        marts_src = os.path.join(self.source_dir, "data", "items", "marts.asm")
        self._patch_item_prices(attrs_src, {"RARE_CANDY": 10})
        self._add_items_to_mart(marts_src, "Cherrygrove", ["RARE_CANDY"])

    def write_elite4_prep(self):
        """
        Elite 4 Prep: stock the Indigo Plateau Mart with Rare Candy, Full Restore,
        Max Elixir, and Max Revive — all at $10 each.
        """
        attrs_src = os.path.join(self.source_dir, "data", "items", "attributes.asm")
        marts_src = os.path.join(self.source_dir, "data", "items", "marts.asm")
        self._patch_item_prices(attrs_src, {
            "RARE_CANDY":   10,
            "FULL_RESTORE": 10,
            "MAX_ELIXER":   10,
            "MAX_REVIVE":   10,
        })
        self._add_items_to_mart(marts_src, "IndigoPlateau", [
            "RARE_CANDY", "FULL_RESTORE", "MAX_ELIXER", "MAX_REVIVE",
        ])

    # -------------------------------------------------------------------------

    def flush_all(self):
        """Write all cached file changes to disk."""
        for out_path, lines in self._file_cache.items():
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        self.log(f"Flushed {len(self._file_cache)} file(s) to output directory.")
