"""
Pokemon Emerald Legacy Randomizer - Source Writer

Writes randomized data back to the Emerald Legacy source tree.
Operates on a copy of the source (never modifies the original).
"""

import copy
import json
import os
import re
import shutil

from constants_emerald import (
    WILD_ENCOUNTERS_FILE, STARTERS_FILE, HM_FIELD_NAMES, ITEM_DATA_FILE,
)


class EmeraldSourceWriter:

    def __init__(self, src_dir: str, out_dir: str, log_fn=None):
        self.src_dir = src_dir
        self.out_dir = out_dir
        self._log    = log_fn or (lambda msg: None)

        # Cache of file contents keyed by absolute path in the OUTPUT tree
        # { out_path: list_of_lines }
        self._pending: dict = {}

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _src_path(self, rel: str) -> str:
        return os.path.join(self.src_dir, rel)

    def _out_path(self, rel: str) -> str:
        return os.path.join(self.out_dir, rel)

    def _src_to_out(self, src_abs: str) -> str:
        """Convert an absolute source path to the corresponding output path."""
        rel = os.path.relpath(src_abs, self.src_dir)
        return os.path.join(self.out_dir, rel)

    def _get_lines(self, out_abs: str) -> list:
        """Return (cached) list of lines for a file in the output tree."""
        if out_abs not in self._pending:
            try:
                with open(out_abs, "r", encoding="utf-8", errors="replace") as f:
                    self._pending[out_abs] = f.readlines()
            except FileNotFoundError:
                self._pending[out_abs] = []
        return self._pending[out_abs]

    def _write_lines(self, out_abs: str, lines: list):
        """Immediately write lines to the output file (also updates cache)."""
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, "w", encoding="utf-8") as f:
            f.writelines(lines)
        self._pending[out_abs] = lines

    # -----------------------------------------------------------------------
    # Directory preparation
    # -----------------------------------------------------------------------

    def prepare_output_directory(self):
        """Copy the entire source tree to the output directory."""
        if os.path.exists(self.out_dir):
            shutil.rmtree(self.out_dir)
        shutil.copytree(self.src_dir, self.out_dir)
        self._log(f"  Copied source tree to: {self.out_dir}")

    # -----------------------------------------------------------------------
    # Wild encounters (JSON)
    # -----------------------------------------------------------------------

    def write_wild_encounters(self, rand_wild_json: dict):
        """Write the randomized wild encounters JSON."""
        rel      = WILD_ENCOUNTERS_FILE
        out_path = self._out_path(rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rand_wild_json, f, indent=2)
            f.write("\n")
        self._log(f"  Wrote {rel}")

    # -----------------------------------------------------------------------
    # Trainer parties (C header)
    # -----------------------------------------------------------------------

    def write_trainer_parties(self, orig_parties: list, rand_parties: list):
        """Patch trainer_parties.h: replace each .species line by line number."""
        if not orig_parties:
            return

        # All parties live in the same file
        src_abs = orig_parties[0].source_file
        out_abs = self._src_to_out(src_abs)
        lines   = self._get_lines(out_abs)

        species_re = re.compile(r"^(\s*\.species\s*=\s*)(SPECIES_\w+)(\s*,.*)")

        # Build a mapping: line_index → new_species
        line_to_species: dict = {}
        for orig_p, rand_p in zip(orig_parties, rand_parties):
            for li, new_mon in zip(orig_p.species_line_numbers, rand_p.mons):
                line_to_species[li] = new_mon.species

        patched = 0
        for li, new_sp in line_to_species.items():
            if li >= len(lines):
                continue
            m = species_re.match(lines[li])
            if m:
                lines[li] = m.group(1) + new_sp + m.group(3) + "\n"
                if not lines[li].endswith("\n"):
                    pass  # group(3) already has the trailing comma/content
                patched += 1

        self._write_lines(out_abs, lines)
        self._log(f"  Patched {patched} species line(s) in trainer_parties.h")

    # -----------------------------------------------------------------------
    # Starters
    # -----------------------------------------------------------------------

    def write_starters(self, orig_starters: list, rand_species: list):
        """
        Patch starter_choose.c: replace SPECIES_X constants inside sStarterMon[].

        rand_species is a list of 3 SPECIES_X strings.
        """
        if not orig_starters:
            return

        src_abs = self._src_to_out(self._src_path(STARTERS_FILE))
        out_abs = src_abs  # already relative to out_dir indirectly
        # Re-derive: we need the output copy
        rel     = STARTERS_FILE
        out_abs = self._out_path(rel)
        lines   = self._get_lines(out_abs)

        species_re = re.compile(r"^(\s*)(SPECIES_\w+)(\s*,.*)")

        patched = 0
        for slot, new_sp in zip(orig_starters, rand_species):
            li = slot.line_index
            if li >= len(lines):
                continue
            m = species_re.match(lines[li])
            if m:
                old_sp = m.group(2)
                lines[li] = m.group(1) + new_sp + m.group(3) + "\n"
                self._log(f"  Starter [{slot.index}]: {old_sp} → {new_sp}")
                patched += 1

        self._write_lines(out_abs, lines)
        self._log(f"  Patched {patched} starter(s) in {STARTERS_FILE}")

    # -----------------------------------------------------------------------
    # Static encounters (setwildbattle lines)
    # -----------------------------------------------------------------------

    # Main-line patterns per static kind
    _STATIC_LINE_RES = {
        "battle": re.compile(r"^(\s*setwildbattle\s+)(SPECIES_\w+)(\s*,\s*\d+.*)"),
        "gift":   re.compile(r"^(\s*givemon\s+)(SPECIES_\w+)(\s*,\s*\d+.*)"),
        "egg":    re.compile(r"^(\s*giveegg\s+)(SPECIES_\w+)(.*)"),
        "event":  re.compile(r"^(\s*seteventmon\s+)(SPECIES_\w+)(\s*,\s*\d+.*)"),
    }

    def write_static_encounters(self, orig_statics: list, rand_statics: list):
        """Patch static Pokémon lines (setwildbattle / givemon / giveegg) in
        event scripts, plus each one's companion lines (playmoncry, setvar,
        bufferspeciesname, …) so cries and dialogue match the new species."""
        # Group by file
        file_patches: dict = {}
        for orig, rand in zip(orig_statics, rand_statics):
            out_abs = self._src_to_out(orig.source_file)
            file_patches.setdefault(out_abs, []).append((orig, rand.species))

        patched = 0
        for out_abs, patches in file_patches.items():
            lines = self._get_lines(out_abs)
            for orig, new_sp in patches:
                li = orig.line_index
                if li >= len(lines):
                    continue
                kind = getattr(orig, "kind", "battle")
                m = self._STATIC_LINE_RES.get(kind, self._STATIC_LINE_RES["battle"]).match(lines[li])
                if m:
                    lines[li] = m.group(1) + new_sp + m.group(3)
                    if not lines[li].endswith("\n"):
                        lines[li] += "\n"
                    patched += 1
                # Companion lines: word-boundary replace of the old species
                sp_re = re.compile(r"\b%s\b" % re.escape(orig.species))
                for cl in getattr(orig, "companion_lines", []):
                    if 0 <= cl < len(lines):
                        lines[cl] = sp_re.sub(new_sp, lines[cl])
            self._write_lines(out_abs, lines)

        self._log(f"  Patched {patched} static encounter(s)")

    # -----------------------------------------------------------------------
    # Field items (finditem ITEM_X lines)
    # -----------------------------------------------------------------------

    def write_field_items(self, orig_items: list, rand_items: list):
        """Patch field items: finditem lines in .inc scripts and
        `"item": "ITEM_X"` lines of hidden_item bg_events in map.json."""
        finditem_re = re.compile(r"^(\s*finditem\s+)(ITEM_\w+)(.*)")
        hidden_re   = re.compile(r'^(\s*"item":\s*")(ITEM_\w+)(".*)')

        # Group by file
        file_patches: dict = {}
        for orig, rand in zip(orig_items, rand_items):
            out_abs = self._src_to_out(orig.source_file)
            if out_abs not in file_patches:
                file_patches[out_abs] = []
            kind = getattr(orig, "kind", "finditem")
            file_patches[out_abs].append((orig.line_index, rand.item_const, kind))

        patched = 0
        for out_abs, patches in file_patches.items():
            lines = self._get_lines(out_abs)
            for li, new_item, kind in patches:
                if li >= len(lines):
                    continue
                pat = hidden_re if kind == "hidden" else finditem_re
                m = pat.match(lines[li])
                if m:
                    lines[li] = m.group(1) + new_item + m.group(3)
                    if not lines[li].endswith("\n"):
                        lines[li] += "\n"
                    patched += 1
            self._write_lines(out_abs, lines)

        self._log(f"  Patched {patched} field item(s)")

    # -----------------------------------------------------------------------
    # TM/HM learnsets (full HM compat)
    # -----------------------------------------------------------------------

    def write_tmhm_compat(self, orig_entries: list, rand_entries: list):
        """
        For each species block, ensure all HM field names appear as:
            .<HM_FIELD> = TRUE,
        We insert any missing HM lines before the closing '} },' of the block.
        """
        if not orig_entries:
            return

        src_abs = orig_entries[0].source_file
        out_abs = self._src_to_out(src_abs)
        lines   = self._get_lines(out_abs)

        # We need to work from bottom to top to preserve line numbers
        pairs = list(zip(orig_entries, rand_entries))
        pairs.sort(key=lambda p: p[0].block_end, reverse=True)

        for orig, rand in pairs:
            block_end = orig.block_end   # line index of "} },"
            if block_end >= len(lines):
                continue

            # Collect HM fields already present in the block
            already = set()
            for li in range(orig.block_start, orig.block_end + 1):
                if li >= len(lines):
                    break
                for hm in HM_FIELD_NAMES:
                    if f".{hm} = TRUE" in lines[li]:
                        already.add(hm)

            # Insert missing HMs just before block_end
            missing = [hm for hm in HM_FIELD_NAMES
                       if hm in rand.hm_fields and hm not in already]
            if missing:
                # The last existing initializer may omit its trailing comma
                # (legal C when it's the final entry before '}'). Adding more
                # lines after it would fuse two initializers, so ensure that
                # preceding line ends with a comma first.
                k = block_end - 1
                while k > orig.block_start and lines[k].strip() == "":
                    k -= 1
                stripped = lines[k].rstrip()
                if stripped.endswith("TRUE") and not stripped.endswith(","):
                    lines[k] = stripped + ",\n"
                insert_lines = [f"        .{hm} = TRUE,\n" for hm in missing]
                lines = lines[:block_end] + insert_lines + lines[block_end:]

        self._write_lines(out_abs, lines)
        self._log(f"  Applied full HM compat to {len(orig_entries)} species in learnsets")

    # -----------------------------------------------------------------------
    # Abilities (.abilities = {A, B} in species_info.h)
    # -----------------------------------------------------------------------

    def write_abilities(self, orig_entries: list, rand_entries: list):
        """Replace each species' .abilities pair with the randomized one."""
        if not orig_entries or not rand_entries:
            return

        abil_re = re.compile(
            r"^(\s*\.abilities\s*=\s*\{)(ABILITY_\w+)(,\s*)(ABILITY_\w+)(\}.*)")
        count = 0
        for orig, rand in zip(orig_entries, rand_entries):
            out_abs = self._src_to_out(orig.source_file)
            lines   = self._get_lines(out_abs)
            li      = orig.line_index
            if li < 0 or li >= len(lines):
                continue
            m = abil_re.match(lines[li])
            if m:
                lines[li] = (m.group(1) + rand.ability1 + m.group(3)
                             + rand.ability2 + m.group(5))
                if not lines[li].endswith("\n"):
                    lines[li] += "\n"
                count += 1

        touched = {self._src_to_out(o.source_file) for o in orig_entries}
        for out_abs in touched:
            self._write_lines(out_abs, self._get_lines(out_abs))
        self._log(f"  Abilities: updated {count} species line(s)")

    # -----------------------------------------------------------------------
    # Wild held items (.itemCommon / .itemRare in species_info.h)
    # -----------------------------------------------------------------------

    def write_wild_held_items(self, orig_entries: list, rand_entries: list):
        """
        Replace the ITEM_X constant on each tracked .itemCommon / .itemRare
        line with the randomized item, preserving indentation and alignment.
        """
        if not orig_entries or not rand_entries:
            return

        import re as _re
        count = 0
        for orig, rand in zip(orig_entries, rand_entries):
            out_abs = self._src_to_out(orig.source_file)
            lines   = self._get_lines(out_abs)
            li      = orig.line_index
            if li < 0 or li >= len(lines):
                continue
            line = lines[li]
            # Sanity: the line should still carry the original item constant
            new_line = _re.sub(
                r"(\.item(?:Common|Rare)\s*=\s*)ITEM_\w+",
                r"\g<1>" + rand.item,
                line, count=1,
            )
            if new_line != line:
                lines[li] = new_line
                count += 1

        # Flush every touched file
        touched = {self._src_to_out(o.source_file) for o in orig_entries}
        for out_abs in touched:
            self._write_lines(out_abs, self._get_lines(out_abs))

        self._log(f"  Wild held items: updated {count} slot(s)")

    # -----------------------------------------------------------------------
    # Shop patches (Zero Grinding / Elite 4 Prep)
    # -----------------------------------------------------------------------

    def _patch_item_prices(self, item_prices: dict):
        """
        Patch .price = X lines in src/data/items/item_data.h.
        item_prices: { "ITEM_RARE_CANDY": 10, ... }

        Each item block looks like:
            [ITEM_RARE_CANDY] =
            {
                ...
                .price = 4800,
                ...
            },
        """
        out_abs   = self._out_path(ITEM_DATA_FILE)
        lines     = self._get_lines(out_abs)
        remaining = dict(item_prices)
        price_re  = re.compile(r'^(\s*\.price\s*=\s*)(\d+)(.*)')

        i = 0
        while i < len(lines) and remaining:
            # Look for [ITEM_X] anywhere on the line
            for ic in list(remaining.keys()):
                if f"[{ic}]" in lines[i]:
                    # Scan ahead (up to 40 lines) for .price = X
                    for j in range(i + 1, min(i + 40, len(lines))):
                        m = price_re.match(lines[j])
                        if m:
                            new_line = m.group(1) + str(remaining[ic]) + m.group(3)
                            if not new_line.endswith("\n"):
                                new_line += "\n"
                            lines[j] = new_line
                            self._log(f"  {ic} price → ${remaining[ic]}")
                            del remaining[ic]
                            break
                        # Stop scanning if we hit another item entry
                        if "[ITEM_" in lines[j] and j > i + 1:
                            break
                    break
            i += 1

        for ic in remaining:
            self._log(f"  [WARN] Could not find {ic} in {ITEM_DATA_FILE} — price unchanged")

        self._write_lines(out_abs, lines)

    def _add_items_to_c_mart(self, label_substr: str, item_consts: list):
        """
        Add items to every Pokemart list in the data/maps script file whose
        contents match label_substr.

        Emerald marts live in data/maps/<Map>/scripts.inc.  A map can define
        several mart variants (e.g. Basic / Expanded / PostGame), each as:

            <MartLabel>:
                .2byte ITEM_POTION
                .2byte ITEM_NONE      (terminator)

        referenced by a `pokemart <MartLabel>` (or `mart <MartLabel>`) macro.
        Every such list in the matched file gets the new items inserted just
        before its `.2byte ITEM_NONE`, so the items are available at every
        stage of the game.
        """
        search_dir = os.path.join(self.out_dir, "data", "maps")
        macro_re   = re.compile(r'(?m)^\s*(?:pokemart|mart)\s+(\w+)')

        target = None
        for root, _dirs, files in os.walk(search_dir):
            for fn in files:
                if not fn.endswith(".inc"):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        contents = fh.read()
                except OSError:
                    continue
                if macro_re.search(contents) and label_substr.lower() in contents.lower():
                    target = path
                    break
            if target:
                break

        if not target:
            self._log(f"  [WARN] No mart found matching '{label_substr}' - shop patch skipped")
            return

        lines = self._get_lines(target)

        # Collect every distinct mart data label referenced by a macro
        mart_labels = []
        for ln in lines:
            m = macro_re.match(ln)
            if m and m.group(1) not in mart_labels:
                mart_labels.append(m.group(1))
        if not mart_labels:
            self._log(f"  [WARN] No mart macro in {os.path.basename(target)} - skipped")
            return

        total_added = 0
        for mart_label in mart_labels:
            # Find the label definition `<label>:`
            start_idx = None
            for i, ln in enumerate(lines):
                if ln.strip().startswith(mart_label + ":"):
                    start_idx = i
                    break
            if start_idx is None:
                continue

            # Find the `.2byte ITEM_NONE` terminator after the label
            term_idx = None
            for i in range(start_idx + 1, len(lines)):
                if re.search(r'\.2byte\s+ITEM_NONE', lines[i]):
                    term_idx = i
                    break
                if lines[i].strip().endswith(":"):   # hit the next label
                    break
            if term_idx is None:
                continue

            existing = set()
            for i in range(start_idx + 1, term_idx):
                mm = re.search(r'\.2byte\s+(ITEM_\w+)', lines[i])
                if mm:
                    existing.add(mm.group(1))

            indent = re.match(r'(\s*)', lines[term_idx]).group(1)
            insert_at = term_idx
            for item in item_consts:
                if item in existing:
                    continue
                lines.insert(insert_at, f"{indent}.2byte {item}\n")
                insert_at += 1
                total_added += 1

        self._write_lines(target, lines)
        self._log(f"  Added {total_added} item entry/entries across "
                  f"{len(mart_labels)} mart list(s) in {os.path.basename(target)}")


    def write_remove_time_evolutions(self):
        """
        Remove time-based evolutions from src/data/pokemon/evolution.h.

        Patches special-condition evolutions in evolution.h:
          EVO_FRIENDSHIP_DAY   → EVO_ITEM, ITEM_SUN_STONE    (Espeon)
          EVO_FRIENDSHIP_NIGHT → EVO_ITEM, ITEM_MOON_STONE   (Umbreon)
          EVO_BEAUTY           → EVO_ITEM, ITEM_SUN_STONE    (Milotic)
          EVO_LEVEL_ATK_GT_DEF → EVO_ITEM, ITEM_BLACK_BELT   (Hitmonlee)
          EVO_LEVEL_ATK_LT_DEF → EVO_ITEM, ITEM_MACHO_BRACE  (Hitmonchan)
          EVO_LEVEL_ATK_EQ_DEF → left unchanged (Hitmontop already uses ITEM_BRICK_PIECE)
        """
        rel = os.path.join("src", "data", "pokemon", "evolution.h")
        out_abs = self._out_path(rel)
        lines = self._get_lines(out_abs)

        changed = 0
        for i, line in enumerate(lines):
            if 'EVO_FRIENDSHIP_DAY' in line:
                lines[i] = line.replace('EVO_FRIENDSHIP_DAY, 0', 'EVO_ITEM, ITEM_SUN_STONE')
                changed += 1
            elif 'EVO_FRIENDSHIP_NIGHT' in line:
                lines[i] = line.replace('EVO_FRIENDSHIP_NIGHT, 0', 'EVO_ITEM, ITEM_MOON_STONE')
                changed += 1
            elif 'EVO_BEAUTY' in line:
                lines[i] = re.sub(r'EVO_BEAUTY,\s*\d+', 'EVO_ITEM, ITEM_SUN_STONE', line)
                changed += 1
            elif 'EVO_LEVEL_ATK_GT_DEF' in line:
                lines[i] = re.sub(r'EVO_LEVEL_ATK_GT_DEF,\s*\d+', 'EVO_ITEM, ITEM_BLACK_BELT', line)
                changed += 1
            elif 'EVO_LEVEL_ATK_LT_DEF' in line:
                lines[i] = re.sub(r'EVO_LEVEL_ATK_LT_DEF,\s*\d+', 'EVO_ITEM, ITEM_MACHO_BRACE', line)
                changed += 1


        if changed:
            self._write_lines(out_abs, lines)
            self._log(f"  Special-condition evolutions → item: {changed} entry/entries changed.")
            # Black Belt / Macho Brace are normally held-only items the player
            # cannot "Use". Make them usable from the party menu so they can
            # trigger the new EVO_ITEM evolutions, just like evolution stones.
            self._make_items_usable_as_evolution(["ITEM_BLACK_BELT", "ITEM_MACHO_BRACE"])
        else:
            self._log("  [WARN] No special-condition evolutions found in evolution.h")

    def _make_items_usable_as_evolution(self, item_consts):
        """
        Patch src/data/items.h so each listed held item can be USED from the
        party menu to trigger an EVO_ITEM evolution (like an evolution stone).

        For each item block, sets:
            .type        = ITEM_USE_PARTY_MENU
            .fieldUseFunc = ItemUseOutOfBattle_EvolutionStone
        The hold effect is left intact, mirroring how ITEM_BRICK_PIECE
        (Hitmontop's evolution item) is configured in the base game.
        """
        rel = os.path.join("src", "data", "items.h")
        out_abs = self._out_path(rel)
        lines = self._get_lines(out_abs)
        if not lines:
            self._log("  [WARN] items.h not found — could not make evolution items usable.")
            return

        targets   = set(item_consts)
        block_re  = re.compile(r"^\s*\[(ITEM_\w+)\]\s*=")
        cur       = None
        touched   = set()
        for i, line in enumerate(lines):
            m = block_re.match(line)
            if m:
                cur = m.group(1)
                continue
            if cur in targets:
                if "ItemUseOutOfBattle_CannotUse" in line:
                    lines[i] = line.replace("ItemUseOutOfBattle_CannotUse",
                                            "ItemUseOutOfBattle_EvolutionStone")
                    touched.add(cur)
                elif ".type" in line and "ITEM_USE_BAG_MENU" in line:
                    lines[i] = line.replace("ITEM_USE_BAG_MENU", "ITEM_USE_PARTY_MENU")
                    touched.add(cur)
                elif line.strip() == "},":
                    cur = None   # end of this item's block

        if touched:
            self._write_lines(out_abs, lines)
            self._log(f"  Made {len(touched)} item(s) usable as evolution items: "
                      f"{', '.join(sorted(touched))}")
        else:
            self._log("  [INFO] Evolution items already usable — no items.h change needed.")

    # -----------------------------------------------------------------------
    # PC Pokémon injection
    # -----------------------------------------------------------------------

    # Gen 3 character encoding table (ASCII → pokeemerald u8 encoding)
    _GEN3_CHARS = {
        ' ': 0x00, **{c: 0xBB + i for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')},
        **{c: 0xD5 + i for i, c in enumerate('abcdefghijklmnopqrstuvwxyz')},
        **{c: 0xA1 + i for i, c in enumerate('0123456789')},
        "'": 0xB4, '.': 0xAD, '!': 0xAB, '?': 0xAC, '-': 0x2D,
        '♀': 0xB5, '♂': 0xB6,  # ♀ ♂
    }
    _GEN3_EOS  = 0xFF
    _NICK_LEN  = 10   # POKEMON_NAME_LENGTH

    def _encode_nickname(self, name: str) -> list:
        """Convert an ASCII name to Gen 3 character codes, EOS-terminated, length 11."""
        codes = []
        for ch in name[:self._NICK_LEN]:
            codes.append(self._GEN3_CHARS.get(ch, 0x00))
        codes.append(self._GEN3_EOS)
        while len(codes) < self._NICK_LEN + 1:
            codes.append(self._GEN3_EOS)
        return codes

    def write_pc_pokemon(self, pc_mons: list):
        """
        Inject a list of Pokémon into the player's PC boxes at new-game start.

        Strategy:
          1. Generate src/randomizer_pc_mons.c — contains a static data array
             (sRandPCMons[]) and RandomizerInitPCMons() which iterates through
             it, creates each mon with CreateMon(), sets IVs/held-item/nickname,
             and places it in a box slot via SetBoxMonAt().
          2. Generate include/randomizer_pc_mons.h — declares the function.
          3. Patch src/new_game.c — adds #include and calls the function just
             after NewGameInitPCItems().
        """
        mons = [m for m in pc_mons if m.get('species')]
        if not mons:
            return

        # ── 1. Build the C data array ─────────────────────────────────────
        rows = []
        for m in mons:
            species  = m.get('species', 'SPECIES_NONE')
            level    = max(1, min(100, int(m.get('level', 5))))
            held     = m.get('heldItem', '') or 'ITEM_NONE'
            ivHP     = max(0, min(31, int(m.get('ivHP',    31))))
            ivAtk    = max(0, min(31, int(m.get('ivAtk',   31))))
            ivDef    = max(0, min(31, int(m.get('ivDef',   31))))
            ivSpAtk  = max(0, min(31, int(m.get('ivSpAtk', 31))))
            ivSpDef  = max(0, min(31, int(m.get('ivSpDef', 31))))
            ivSpd    = max(0, min(31, int(m.get('ivSpd',   31))))
            nick_raw = (m.get('nickname') or '').strip()
            has_nick = 1 if nick_raw else 0
            nick_bytes = self._encode_nickname(nick_raw) if nick_raw else ([self._GEN3_EOS] * (self._NICK_LEN + 1))
            nick_c   = '{' + ', '.join(f'0x{b:02X}' for b in nick_bytes) + '}'

            raw_moves  = m.get('moves', []) or []
            move_consts = [(raw_moves[i] if i < len(raw_moves) and raw_moves[i] else 'MOVE_NONE')
                           for i in range(4)]
            has_moves  = 1 if any(mc != 'MOVE_NONE' for mc in move_consts) else 0
            moves_c    = '{' + ', '.join(move_consts) + '}'

            rows.append(
                f"    {{{species}, {level}, {held}, "
                f"{ivHP}, {ivAtk}, {ivDef}, {ivSpAtk}, {ivSpDef}, {ivSpd}, "
                f"{has_nick}, {nick_c}, {has_moves}, {moves_c}}}"
            )

        data_rows = ',\n'.join(rows)

        c_src = f"""\
/* Auto-generated by the Pokemon Legacy Randomizer — do not edit by hand. */
#include "global.h"
#include "pokemon.h"
#include "battle.h"
#include "pokemon_storage_system.h"
#include "constants/species.h"
#include "constants/items.h"
#include "constants/moves.h"
#include "randomizer_pc_mons.h"

struct RandPCMonSpec {{
    u16   species;
    u8    level;
    u16   heldItem;
    u8    hpIV;
    u8    atkIV;
    u8    defIV;
    u8    spAtkIV;
    u8    spDefIV;
    u8    spdIV;
    u8    hasNickname;
    u8    nickname[POKEMON_NAME_LENGTH + 1];
    u8    hasMoves;
    u16   moves[4];
}};

static const struct RandPCMonSpec sRandPCMons[] = {{
{data_rows},
    {{SPECIES_NONE}} /* terminator */
}};

void RandomizerInitPCMons(void)
{{
    u16 totalPos;
    u8  boxId, boxPos;
    const struct RandPCMonSpec *spec;
    struct Pokemon mon;
    u8  iv;
    u16 item;

    totalPos = 0;
    for (spec = sRandPCMons; spec->species != SPECIES_NONE; spec++) {{
        if (totalPos >= TOTAL_BOXES_COUNT * IN_BOX_COUNT)
            break;

        boxId  = (u8)(totalPos / IN_BOX_COUNT);
        boxPos = (u8)(totalPos % IN_BOX_COUNT);

        /* Create the mon with all-31 IVs first (initial moveset is set automatically) */
        CreateMon(&mon, spec->species, spec->level, 31, FALSE, 0, OT_ID_PLAYER_ID, 0);

        /* Override individual IVs */
        iv = spec->hpIV;    SetMonData(&mon, MON_DATA_HP_IV,    &iv);
        iv = spec->atkIV;   SetMonData(&mon, MON_DATA_ATK_IV,   &iv);
        iv = spec->defIV;   SetMonData(&mon, MON_DATA_DEF_IV,   &iv);
        iv = spec->spAtkIV; SetMonData(&mon, MON_DATA_SPATK_IV, &iv);
        iv = spec->spDefIV; SetMonData(&mon, MON_DATA_SPDEF_IV, &iv);
        iv = spec->spdIV;   SetMonData(&mon, MON_DATA_SPEED_IV, &iv);

        /* Set held item */
        if (spec->heldItem != ITEM_NONE) {{
            item = spec->heldItem;
            SetMonData(&mon, MON_DATA_HELD_ITEM, &item);
        }}

        /* Set nickname */
        if (spec->hasNickname)
            SetMonData(&mon, MON_DATA_NICKNAME, spec->nickname);

        /* Override moves and PP if custom moves were specified */
        if (spec->hasMoves) {{
            u16 move; u8 pp;
            move = spec->moves[0]; SetMonData(&mon, MON_DATA_MOVE1, &move); pp = gBattleMoves[move].pp; SetMonData(&mon, MON_DATA_PP1, &pp);
            move = spec->moves[1]; SetMonData(&mon, MON_DATA_MOVE2, &move); pp = (move != MOVE_NONE) ? gBattleMoves[move].pp : 0; SetMonData(&mon, MON_DATA_PP2, &pp);
            move = spec->moves[2]; SetMonData(&mon, MON_DATA_MOVE3, &move); pp = (move != MOVE_NONE) ? gBattleMoves[move].pp : 0; SetMonData(&mon, MON_DATA_PP3, &pp);
            move = spec->moves[3]; SetMonData(&mon, MON_DATA_MOVE4, &move); pp = (move != MOVE_NONE) ? gBattleMoves[move].pp : 0; SetMonData(&mon, MON_DATA_PP4, &pp);
        }}

        /* Place in box */
        SetBoxMonAt(boxId, boxPos, &mon.box);
        totalPos++;
    }}
}}
"""

        # ── 2. Write the C source file ────────────────────────────────────
        c_out = self._out_path(os.path.join("src", "randomizer_pc_mons.c"))
        os.makedirs(os.path.dirname(c_out), exist_ok=True)
        with open(c_out, "w", encoding="utf-8") as f:
            f.write(c_src)

        # ── 3. Write the header ───────────────────────────────────────────
        h_out = self._out_path(os.path.join("include", "randomizer_pc_mons.h"))
        os.makedirs(os.path.dirname(h_out), exist_ok=True)
        with open(h_out, "w", encoding="utf-8") as f:
            f.write(
                "#ifndef GUARD_RANDOMIZER_PC_MONS_H\n"
                "#define GUARD_RANDOMIZER_PC_MONS_H\n\n"
                "void RandomizerInitPCMons(void);\n\n"
                "#endif // GUARD_RANDOMIZER_PC_MONS_H\n"
            )

        # ── 4. Patch src/new_game.c ───────────────────────────────────────
        ng_rel  = os.path.join("src", "new_game.c")
        ng_out  = self._out_path(ng_rel)
        ng_lines = self._get_lines(ng_out)

        # Add #include after the last existing #include line
        last_inc = -1
        for i, ln in enumerate(ng_lines):
            if ln.strip().startswith('#include'):
                last_inc = i
        if last_inc >= 0:
            ng_lines.insert(last_inc + 1, '#include "randomizer_pc_mons.h"\n')

        # Insert the call just after NewGameInitPCItems();
        for i, ln in enumerate(ng_lines):
            if 'NewGameInitPCItems()' in ln and ';' in ln:
                ng_lines.insert(i + 1, '    RandomizerInitPCMons();\n')
                break

        self._write_lines(ng_out, ng_lines)
        self._log(f"  PC Pokémon: {len(mons)} mon(s) injected into new-game init.")

    def write_starting_items(self, bag_items: list, pc_items: list):
        """
        Inject starting bag / PC items at new-game start.

        Generates src/randomizer_start_items.c with a RandomizerInitStartItems()
        function that calls AddBagItem()/AddPCItem() for each configured item,
        declares it in include/randomizer_start_items.h, and patches
        src/new_game.c to call it right after NewGameInitPCItems().

        Each item is a dict: {"const": "ITEM_X", "qty": int}.
        """
        bag = [it for it in (bag_items or []) if it.get("const")]
        pc  = [it for it in (pc_items  or []) if it.get("const")]
        if not bag and not pc:
            return

        def _clamp(q, cap):
            try:
                q = int(q)
            except (TypeError, ValueError):
                q = 1
            return max(1, min(cap, q))

        # Stack limits from the game: MAX_BAG_ITEM_CAPACITY 99, MAX_PC_ITEM_CAPACITY 999
        body = []
        for it in bag:
            body.append("    AddBagItem(%s, %d);" % (it["const"], _clamp(it.get("qty", 1), 99)))
        for it in pc:
            body.append("    AddPCItem(%s, %d);" % (it["const"], _clamp(it.get("qty", 1), 999)))

        c_src = (
            "/* Auto-generated by the Pokemon Legacy Randomizer - do not edit by hand. */\n"
            '#include "global.h"\n'
            '#include "item.h"\n'
            '#include "constants/items.h"\n'
            '#include "randomizer_start_items.h"\n'
            "\n"
            "void RandomizerInitStartItems(void)\n"
            "{\n"
            + "\n".join(body) + "\n"
            "}\n"
        )

        c_out = self._out_path(os.path.join("src", "randomizer_start_items.c"))
        os.makedirs(os.path.dirname(c_out), exist_ok=True)
        with open(c_out, "w", encoding="utf-8") as f:
            f.write(c_src)

        h_out = self._out_path(os.path.join("include", "randomizer_start_items.h"))
        os.makedirs(os.path.dirname(h_out), exist_ok=True)
        with open(h_out, "w", encoding="utf-8") as f:
            f.write(
                "#ifndef GUARD_RANDOMIZER_START_ITEMS_H\n"
                "#define GUARD_RANDOMIZER_START_ITEMS_H\n\n"
                "void RandomizerInitStartItems(void);\n\n"
                "#endif // GUARD_RANDOMIZER_START_ITEMS_H\n"
            )

        ng_out   = self._out_path(os.path.join("src", "new_game.c"))
        ng_lines = self._get_lines(ng_out)

        if not any('randomizer_start_items.h' in l for l in ng_lines):
            last_inc = -1
            for i, l in enumerate(ng_lines):
                if l.strip().startswith('#include'):
                    last_inc = i
            if last_inc >= 0:
                ng_lines.insert(last_inc + 1, '#include "randomizer_start_items.h"\n')

        for i, l in enumerate(ng_lines):
            if 'NewGameInitPCItems()' in l and ';' in l:
                ng_lines.insert(i + 1, '    RandomizerInitStartItems();\n')
                break

        self._write_lines(ng_out, ng_lines)
        self._log("  Starting items: %d bag + %d PC item(s) injected." % (len(bag), len(pc)))


    def write_zero_grinding(self):
        """
        Zero Grinding: add Rare Candy at $10 to the Oldale Town Mart —
        the first shop accessible in Emerald, available from the very start.
        """
        self._patch_item_prices({"ITEM_RARE_CANDY": 10})
        self._add_items_to_c_mart("Oldale", ["ITEM_RARE_CANDY"])

    def write_elite4_prep(self):
        """
        Elite 4 Prep: stock the Pokémon League Mart with Rare Candy,
        Full Restore, Max Elixir, and Max Revive — all at $10 each.
        """
        self._patch_item_prices({
            "ITEM_RARE_CANDY":   10,
            "ITEM_FULL_RESTORE": 10,
            "ITEM_MAX_ELIXIR":   10,
            "ITEM_MAX_REVIVE":   10,
        })
        self._add_items_to_c_mart("League", [
            "ITEM_RARE_CANDY", "ITEM_FULL_RESTORE",
            "ITEM_MAX_ELIXIR", "ITEM_MAX_REVIVE",
        ])

    # -----------------------------------------------------------------------
    # In-game trades
    # -----------------------------------------------------------------------

    def write_trades(self, original: list, randomized: list):
        """
        Patch sIngameTrades[] in src/data/trade.h in the output tree.

        Each EmeraldInGameTrade stores the exact line index for every field,
        so replacement is a direct targeted line edit — no scanning needed.
        """
        changes = 0

        for orig, rand in zip(original, randomized):
            out_abs = self._src_to_out(orig.source_file)
            lines   = self._get_lines(out_abs)

            def _patch(line_idx, condition, new_text):
                nonlocal changes
                if condition and 0 <= line_idx < len(lines):
                    lines[line_idx] = new_text + "\n"
                    changes += 1

            # .species
            if orig.species != rand.species and orig.species_line >= 0:
                new_ln = orig.species_full_line.replace(
                    orig.species, rand.species, 1)
                _patch(orig.species_line, True, new_ln)

            # .requestedSpecies
            if orig.requested_species != rand.requested_species and orig.req_line >= 0:
                new_ln = orig.req_full_line.replace(
                    orig.requested_species, rand.requested_species, 1)
                _patch(orig.req_line, True, new_ln)

            # .nickname
            if rand.nickname and rand.nickname != orig.nickname and orig.nickname_line >= 0:
                new_ln = re.sub(r'_\("[^"]*"\)', f'_("{rand.nickname}")',
                                orig.nickname_full_line)
                _patch(orig.nickname_line, True, new_ln)

            # .otName
            if rand.ot_name and rand.ot_name != orig.ot_name and orig.ot_line >= 0:
                new_ln = re.sub(r'_\("[^"]*"\)', f'_("{rand.ot_name}")',
                                orig.ot_full_line)
                _patch(orig.ot_line, True, new_ln)

            # .ivs
            if rand.ivs_raw and rand.ivs_raw != orig.ivs_raw and orig.ivs_line >= 0:
                new_ln = re.sub(r'\{[^}]+\}', rand.ivs_raw,
                                orig.ivs_full_line, count=1)
                _patch(orig.ivs_line, True, new_ln)

            # .heldItem
            if rand.held_item != orig.held_item and orig.held_item_line >= 0:
                new_ln = orig.held_item_full_line.replace(
                    orig.held_item, rand.held_item, 1)
                _patch(orig.held_item_line, True, new_ln)

        self._log(f"  Applied {changes} trade field change(s)")

    # -----------------------------------------------------------------------
    # Flush all pending file writes
    # -----------------------------------------------------------------------

    def flush_all(self):
        """Write all pending line buffers to disk."""
        written = 0
        for out_abs, lines in self._pending.items():
            os.makedirs(os.path.dirname(out_abs), exist_ok=True)
            with open(out_abs, "w", encoding="utf-8") as f:
                f.writelines(lines)
            written += 1
        self._pending.clear()
        if written:
            self._log(f"  Flushed {written} file(s) to output directory")
