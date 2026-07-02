"""
Pokemon Yellow Legacy Randomizer - Source Writer

Writes randomized data back to Yellow Legacy ASM source files
in a copied output directory (source directory is never modified).
"""

import os
import re
import shutil
import glob
from constants_yellow import (
    POKEMON_CONSTANTS, POKEMON_CONST_NAMES, YELLOW_INTERNAL_ID,
    YELLOW_INTERNAL_ID_BY_DEX,
    INIT_PLAYER_DATA_FILE, PRICES_FILE,
    VIRIDIAN_MART_FILE, INDIGO_PLATEAU_LOBBY_FILE,
)
from static_data import POKEMON_TYPES, POKEMON_CATCH_RATES


class YellowSourceWriter:
    """Copy source tree → output dir, then patch files in place."""

    def __init__(self, source_dir: str, output_dir: str, log_fn=None):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.log        = log_fn or print
        self._cache: dict[str, list[str]] = {}  # rel_path → lines

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _out(self, rel_path: str) -> str:
        return os.path.join(self.output_dir, rel_path)

    def _load(self, rel_path: str) -> list[str]:
        if rel_path in self._cache:
            return self._cache[rel_path]
        out_path = self._out(rel_path)
        if not os.path.isfile(out_path):
            self.log(f"  [WARN] File not found in output: {rel_path}")
            return []
        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        self._cache[rel_path] = lines
        return lines

    def _mark_dirty(self, rel_path: str):
        """Ensure file is in cache (will be written on flush)."""
        self._load(rel_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Directory setup
    # ─────────────────────────────────────────────────────────────────────────

    def prepare_output_directory(self):
        """
        Copy the entire source tree to output_dir.
        If output_dir already exists, remove it first.
        """
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        shutil.copytree(self.source_dir, self.output_dir)
        self.log(f"  Copied source → {self.output_dir}")

    # ─────────────────────────────────────────────────────────────────────────
    # Starters
    # ─────────────────────────────────────────────────────────────────────────

    def write_starter(self, starters: list, new_const: str):
        """
        Replace every starter gift file's lb bc, SPECIES, LEVEL  and
        ld a, SPECIES lines with the new species constant.
        """
        for loc in starters:
            lines = self._load(loc.source_file)
            if not lines:
                continue

            old_const = loc.species_const
            self.log(f"  Starter {old_const} → {new_const} in {loc.source_file}")

            # Patch lb bc, SPECIES, LEVEL
            i = loc.lb_line
            if i < len(lines):
                lines[i] = re.sub(
                    r'\b' + re.escape(old_const) + r'\b',
                    new_const, lines[i],
                )

            # Patch all ld a, SPECIES lines
            for j in loc.ld_lines:
                if j < len(lines):
                    lines[j] = re.sub(
                        r'\b' + re.escape(old_const) + r'\b',
                        new_const, lines[j],
                    )

    _OAKS_LAB_FILE = "scripts/OaksLab.asm"

    def write_oak_starter(self, species_const: str, level: int = 5):
        """
        Swap the species Oak gives at game start (normally Pikachu) for the
        chosen species, via the existing AddPartyMon flow.

        Design notes:
          • Only the species fed to AddPartyMon (the `ld a, STARTER_PIKACHU`
            immediately before `ld [wcf91], a` / `call AddPartyMon`) is changed.
          • `wPlayerStarter` is deliberately LEFT as Pikachu, so the rival's
            counter-Eevee and all Pikachu-related narrative logic stay
            consistent (the intro dialogue still references Pikachu — cosmetic).
          • The `ld a, LIGHT_BALL_GSC` / `ld [wPartyMon1CatchRate], a` lines are
            removed, since the Light Ball held-item is Pikachu-specific.
          • Result: the player has exactly ONE starter (1 Pokédex entry), so the
            Oak's-Parcel quest gate (<2 owned) is satisfied — no softlock.

        The Pikachu overworld follow-sprite stays disabled
        (DisablePikachuOverworldSpriteDrawing is left untouched).
        """
        if not species_const or species_const == "PIKACHU":
            return
        out_path = os.path.join(self.output_dir, self._OAKS_LAB_FILE)
        if not os.path.isfile(out_path):
            self.log(f"  [WARN] {self._OAKS_LAB_FILE} not found — starter swap skipped")
            return
        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        # 1) Swap the species given to AddPartyMon. Match the exact sequence so
        #    we change ONLY the party-mon species (not the wPlayerStarter store).
        give_pat = re.compile(
            r'(ld a, )STARTER_PIKACHU(\n[ \t]*ld \[wd11e\], a'
            r'\n[ \t]*ld \[wcf91\], a'
            r'\n[ \t]*call AddPartyMon)')
        if not give_pat.search(text):
            self.log("  [WARN] AddPartyMon starter sequence not found — swap skipped")
            return
        text = give_pat.sub(rf'\g<1>{species_const}\g<2>', text, count=1)

        # 2) Remove the Pikachu-specific Light Ball held-item lines.
        text = re.sub(
            r'[ \t]*ld a, LIGHT_BALL_GSC\n[ \t]*ld \[wPartyMon1CatchRate\], a\n',
            '', text, count=1)

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self._cache.pop(self._OAKS_LAB_FILE, None)
        self.log(f"  Starter swap: Oak gives {species_const} at Lv5 (replaces Pikachu in party)")

    # ─────────────────────────────────────────────────────────────────────────
    # Wild encounters
    # ─────────────────────────────────────────────────────────────────────────

    def write_wild_encounters(self, orig_groups: list, rand_groups: list):
        """
        Replace each  db LEVEL, SPECIES  line in the wild map files.
        """
        for orig, rand in zip(orig_groups, rand_groups):
            lines = self._load(orig.source_file)
            if not lines:
                continue

            # Collect original and replacement slot lines in order
            orig_slots = orig.slots
            rand_slots = rand.slots
            if len(orig_slots) != len(rand_slots):
                self.log(f"  [WARN] Slot count mismatch in {orig.source_file} — skipping")
                continue

            # Scan the block for db LEVEL, SPECIES lines and replace species
            slot_idx = 0
            for li in range(orig.line_start, min(orig.line_end + 1, len(lines))):
                s = lines[li].split(';')[0].strip()
                m = re.match(r'db\s+(\d+)\s*,\s*(\w+)', s)
                if m and slot_idx < len(orig_slots):
                    old_sp = orig_slots[slot_idx].species_const
                    new_sp = rand_slots[slot_idx].species_const
                    if old_sp != new_sp:
                        lines[li] = re.sub(
                            r'\b' + re.escape(old_sp) + r'\b',
                            new_sp, lines[li],
                        )
                    slot_idx += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Fishing
    # ─────────────────────────────────────────────────────────────────────────

    def write_fishing_simple(self, orig_slots: list, rand_slots: list, rod_name: str):
        """
        Replace species in old-rod / good-rod global table files.
        Format: db LEVEL, SPECIES
        """
        if not orig_slots:
            return
        from constants_yellow import WILD_OLD_ROD_FILE, WILD_GOOD_ROD_FILE
        rel = WILD_OLD_ROD_FILE if "Old" in rod_name else WILD_GOOD_ROD_FILE
        lines = self._load(rel)
        if not lines:
            return

        slot_idx = 0
        for i, line in enumerate(lines):
            s = line.split(';')[0].strip()
            m = re.match(r'db\s+\d+\s*,\s*(\w+)', s)
            if m and slot_idx < len(orig_slots):
                old_sp = orig_slots[slot_idx].species_const
                new_sp = rand_slots[slot_idx].species_const
                if old_sp != new_sp:
                    lines[i] = re.sub(
                        r'\b' + re.escape(old_sp) + r'\b',
                        new_sp, lines[i],
                    )
                slot_idx += 1
                if slot_idx >= len(orig_slots):
                    break

    def write_super_rod(self, orig_entries: list, rand_entries: list):
        """
        Replace species in super_rod.asm rows.
        Format: db MAP_CONST, SP1,LV1, SP2,LV2, SP3,LV3, SP4,LV4
        """
        from constants_yellow import WILD_SUPER_ROD_FILE
        if not orig_entries:
            return
        lines = self._load(WILD_SUPER_ROD_FILE)
        if not lines:
            return

        for orig, rand in zip(orig_entries, rand_entries):
            i = orig.line_index
            if i >= len(lines):
                continue
            line = lines[i]
            # Replace each old species const with new
            new_line = line
            for o_slot, r_slot in zip(orig.slots, rand.slots):
                if o_slot.species_const != r_slot.species_const:
                    new_line = re.sub(
                        r'\b' + re.escape(o_slot.species_const) + r'\b',
                        r_slot.species_const, new_line,
                    )
            lines[i] = new_line

    # ─────────────────────────────────────────────────────────────────────────
    # Trainers
    # ─────────────────────────────────────────────────────────────────────────

    def write_trainers(self, orig_trainers: list, rand_trainers: list):
        """
        Reconstruct each trainer data line with new species.
        Format A: db LEVEL, SP1, SP2, ..., 0
        Format B: db $FF, LV1, SP1, LV2, SP2, ..., 0
        """
        from constants_yellow import TRAINER_PARTIES_FILE
        lines = self._load(TRAINER_PARTIES_FILE)
        if not lines:
            return

        for orig, rand in zip(orig_trainers, rand_trainers):
            if orig.fmt == 'A':
                # Single line: db LEVEL, SP1, SP2, ..., 0
                level  = orig.party[0].level if orig.party else 5
                species = [p.species_const for p in rand.party]
                new_line = f"\tdb {level}, {', '.join(species)}, 0\n"
                i = orig.line_start
                if i < len(lines):
                    lines[i] = new_line
            else:
                # Format B: db $FF, LV1, SP1, LV2, SP2, ..., 0
                parts = ["$FF"]
                for mon in rand.party:
                    parts.append(str(mon.level))
                    parts.append(mon.species_const)
                parts.append("0")
                new_line = f"\tdb {', '.join(parts)}\n"
                i = orig.line_start
                if i < len(lines):
                    # Replace potentially multi-line entry with single line
                    lines[i] = new_line
                    # Blank out continuation lines (line_start to line_end)
                    for j in range(i + 1, min(orig.line_end + 1, len(lines))):
                        if lines[j].strip().startswith('db'):
                            lines[j] = ''

    # ─────────────────────────────────────────────────────────────────────────
    # Static encounters
    # ─────────────────────────────────────────────────────────────────────────

    def write_static_encounters(self, orig_encs: list, rand_encs: list):
        """
        Replace species in static encounter scripts.
        Battle type: patch ld a, SPECIES line.
        Gift type:   patch lb bc, SPECIES, LEVEL line.
        """
        for orig, rand in zip(orig_encs, rand_encs):
            lines = self._load(orig.source_file)
            if not lines:
                continue

            old_sp = orig.species_const
            new_sp = rand.species_const
            if old_sp == new_sp:
                continue

            if orig.encounter_type == 'battle':
                # Patch ld a, SPECIES
                i = orig.ld_a_line
                if i >= 0 and i < len(lines):
                    lines[i] = re.sub(
                        r'\b' + re.escape(old_sp) + r'\b',
                        new_sp, lines[i],
                    )
            elif orig.encounter_type == 'gift':
                # Patch lb bc, SPECIES, LEVEL
                i = orig.lb_line
                if i >= 0 and i < len(lines):
                    lines[i] = re.sub(
                        r'\b' + re.escape(old_sp) + r'\b',
                        new_sp, lines[i],
                    )
                # Also patch the companion name-display line so the "received
                # X!" text matches the mon actually given.
                ni = getattr(orig, 'name_line', -1)
                if ni is not None and ni >= 0 and ni < len(lines):
                    lines[ni] = re.sub(
                        r'\b' + re.escape(old_sp) + r'\b',
                        new_sp, lines[ni],
                    )
            self.log(f"  Static {orig.encounter_type}: {old_sp} → {new_sp}")

    # ─────────────────────────────────────────────────────────────────────────
    # In-game trades
    # ─────────────────────────────────────────────────────────────────────────

    def write_trades(self, orig_trades: list, rand_trades: list):
        """
        Replace species (and optionally nickname) in data/events/trades.asm.
        Format: db GIVE, GET, DIALOG_ID, "NICKNAME@@@@@@"
        """
        from constants_yellow import TRADES_FILE
        lines = self._load(TRADES_FILE)
        if not lines:
            return

        for orig, rand in zip(orig_trades, rand_trades):
            i = orig.line_index
            if i >= len(lines):
                continue
            line = lines[i]

            # Replace give species
            if rand.given_species != orig.given_species:
                line = re.sub(
                    r'\b' + re.escape(orig.given_species) + r'\b',
                    rand.given_species, line, count=1,
                )

            # Replace get species (second occurrence)
            if rand.requested_species != orig.requested_species:
                line = re.sub(
                    r'\b' + re.escape(orig.requested_species) + r'\b',
                    rand.requested_species, line, count=1,
                )

            # Replace nickname.
            # The trade table is `table_width 3 + NAME_LENGTH` with
            # NAME_LENGTH == 11, so the quoted string must be EXACTLY 11
            # characters (name + '@' padding).  Padding to 10 shrinks the row
            # by one byte and breaks assert_table_length.
            if rand.nickname != orig.nickname:
                NAME_LENGTH = 11
                new_nick = rand.nickname.upper()[:NAME_LENGTH]
                padded_new = new_nick.ljust(NAME_LENGTH, '@')
                # Replace the original quoted, @-padded nickname (any padding length)
                # with the correctly-sized replacement.
                line = re.sub(
                    r'"' + re.escape(orig.nickname) + r'@*"',
                    f'"{padded_new}"',
                    line,
                )

            lines[i] = line

    # ─────────────────────────────────────────────────────────────────────────
    # Field items
    # ─────────────────────────────────────────────────────────────────────────

    def write_field_items(self, orig_items: list, rand_items: list):
        """
        Replace item constants in visible poké-ball object_event lines
        and hidden_object lines.
        """
        for orig, rand in zip(orig_items, rand_items):
            lines = self._load(orig.source_file)
            if not lines:
                continue
            i = orig.line_index
            if i >= len(lines):
                continue
            if orig.item_const != rand.item_const:
                lines[i] = re.sub(
                    r'\b' + re.escape(orig.item_const) + r'\b',
                    rand.item_const, lines[i], count=1,
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Evolutions
    # ─────────────────────────────────────────────────────────────────────────

    def write_evolutions(self, orig_evos: list, rand_evos: list):
        """
        Rebuild evolution lines in data/pokemon/evos_moves.asm.

        Yellow formats:
          EVOLVE_LEVEL:  db EVOLVE_LEVEL, level, SPECIES
          EVOLVE_ITEM:   db EVOLVE_ITEM, item, min_level, SPECIES
          EVOLVE_TRADE:  db EVOLVE_TRADE, min_level, SPECIES
              (or converted to EVOLVE_LEVEL by engine)
        """
        from constants_yellow import EVOLUTION_DATA_FILE
        lines = self._load(EVOLUTION_DATA_FILE)
        if not lines:
            return

        for orig, rand in zip(orig_evos, rand_evos):
            i = orig.line_index
            if i >= len(lines):
                continue

            indent = re.match(r'(\s*)', lines[i]).group(1)
            evo_type = rand.evo_type

            if evo_type == 'EVOLVE_LEVEL':
                new_line = f"{indent}db EVOLVE_LEVEL, {rand.param}, {rand.target_const}\n"
            elif evo_type == 'EVOLVE_ITEM':
                ml = rand.min_level if rand.min_level else '1'
                new_line = f"{indent}db EVOLVE_ITEM, {rand.param}, {ml}, {rand.target_const}\n"
            elif evo_type == 'EVOLVE_TRADE':
                ml = rand.min_level if rand.min_level else '1'
                new_line = f"{indent}db EVOLVE_TRADE, {ml}, {rand.target_const}\n"
            else:
                continue

            # Preserve trailing comment if present
            comment_m = re.search(r'(;.*)$', lines[i])
            if comment_m:
                new_line = new_line.rstrip('\n') + '  ' + comment_m.group(1) + '\n'

            lines[i] = new_line

    # ─────────────────────────────────────────────────────────────────────────
    # TM/HM compatibility
    # ─────────────────────────────────────────────────────────────────────────

    def write_tmhm_compat(self, orig_entries: list, rand_entries: list):
        """
        Rewrite each species' `tmhm` macro with an updated MOVE-name list.

        Yellow's tmhm macro takes move names (e.g. SWORDS_DANCE, CUT) and
        computes the bitfield itself.  The original macro may span multiple
        lines joined by trailing backslashes; we collapse the whole block
        (line_index..end_index) into a single line with the new name list.
        """
        for orig, rand in zip(orig_entries, rand_entries):
            lines = self._load(orig.source_file)
            if not lines:
                continue
            i = orig.line_index
            if i >= len(lines):
                continue

            names = rand.move_names if rand.move_names else (orig.move_names or [])
            if not names:
                continue
            indent = re.match(r'(\s*)', lines[i]).group(1)
            new_line = f"{indent}tmhm {', '.join(names)}\n"

            # Replace the (possibly multi-line) original block with one line.
            end = orig.end_index if (orig.end_index is not None and orig.end_index >= i) else i
            end = min(end, len(lines) - 1)
            lines[i:end + 1] = [new_line]

    # ─────────────────────────────────────────────────────────────────────────
    # Starting items
    # ─────────────────────────────────────────────────────────────────────────

    # Starting items / PC Pokémon are handed out by Daisy (the rival's sister)
    # together with the Town Map, reusing the game's own gift mechanism.  This
    # is a proper text-script (text_asm) context — the same kind of script that
    # vanilla gift NPCs (Charmander on Route 24, the Fighting Dojo prize, etc.)
    # use — so GivePokemon/GiveItem run with the correct text-flow handling and
    # cannot crash.  It also happens AFTER the Oak's-Parcel quest, so it can't
    # interfere with the intro gates.
    _BLUES_HOUSE_FILE = "scripts/BluesHouse.asm"

    def write_starting_items(self, bag_items: list, pc_items: list):
        """
        Record starting bag/PC items, then (re)emit the combined extras routine.

        Items are added at new-game time using the game's OWN
        AddItemToInventory routine (the exact mechanism vanilla Yellow uses to
        give the player their starting Potion), which correctly maintains the
        list count byte, slot data, and $ff terminator.  Hand-poking the WRAM
        lists (the previous approach) produced corrupt/empty inventories.
        """
        MAX_BAG, MAX_PC = 20, 50
        self._start_bag = [
            {"const": i["const"], "qty": max(1, min(99, int(i.get("qty", 1))))}
            for i in (bag_items or []) if i.get("const")
        ][:MAX_BAG]
        self._start_pc = [
            {"const": i["const"], "qty": max(1, min(99, int(i.get("qty", 1))))}
            for i in (pc_items or []) if i.get("const")
        ][:MAX_PC]
        self._emit_yellow_extras()

    # ─────────────────────────────────────────────────────────────────────────
    # PC Pokémon
    # ─────────────────────────────────────────────────────────────────────────

    def write_pc_pokemon(self, pc_pokemon: list):
        """
        Record PC Pokémon, then (re)emit the combined extras routine.

        Pokémon are created at new-game time using the game's OWN GivePokemon
        routine (species in b, level in c).  GivePokemon runs LoadEnemyMonData
        + SendNewMonToBox, which computes correct stats/HP, sets level-up moves,
        builds a valid box_struct, and registers the Pokédex flag — fixing the
        Level-1, corrupted-sprite/HP, and missing-move problems caused by the
        previous hand-written box_struct approach.
        """
        MAX_BOX = 20
        mons = []
        for m in (pc_pokemon or []):
            sp = m.get("species", "")
            if sp not in POKEMON_CONSTANTS:
                if sp:
                    self.log(f"  [WARN] Unknown PC species: {sp!r} — skipped")
                continue
            # Normalise up to 4 custom moves; "" / "NO_MOVE" → no override.
            raw_moves = m.get("moves") or []
            moves = []
            for mv in raw_moves[:4]:
                if mv and mv != "NO_MOVE":
                    moves.append(mv)
            mons.append({
                "species": sp,
                "level": max(1, min(100, int(m.get("level", 5)))),
                "moves": moves,   # [] = keep GivePokemon's default level-up moves
            })
            if len(mons) >= MAX_BOX:
                break
        self._start_mons = mons
        self._emit_yellow_extras()

    def _emit_yellow_extras(self):
        """
        Write a single RandomizerInitExtras routine (items + PC Pokémon) into
        oak_speech.asm, called right after the default starting Potion is given
        — a point where party/box/inventory are fully initialised.

        Idempotent: re-emits the whole routine from the accumulated
        self._start_bag / _start_pc / _start_mons each time it's called, so the
        two public methods can be invoked in any order.
        """
        bag  = getattr(self, "_start_bag", [])
        pc   = getattr(self, "_start_pc", [])
        mons = getattr(self, "_start_mons", [])
        if not (bag or pc or mons):
            return

        out_path = os.path.join(self.output_dir, self._BLUES_HOUSE_FILE)
        if not os.path.isfile(out_path):
            self.log(f"  [WARN] {self._BLUES_HOUSE_FILE} not found — extras skipped")
            return

        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        # Strip any previously-injected pieces so repeat calls (bag then mons)
        # don't stack: both the call-site line and the appended routine block.
        text = re.sub(r'[ \t]*call RandomizerGiveExtras[ \t]*\n', '', text)
        text = re.sub(
            r'\n?; ==== Randomizer Extras ====.*?; ==== End Randomizer Extras ====\n',
            '', text, flags=re.S)

        # Anchor: Daisy's Town Map gift, right after SetEvent EVENT_GOT_TOWN_MAP.
        # We inject only a single `call RandomizerGiveExtras` here (a `call` is
        # absolute, so it does NOT enlarge the surrounding branchy script and
        # break its `jr` ranges — an inline block did exactly that).  The actual
        # routine is appended at the END of the file as its own label.  It runs
        # in the same text_asm context the gift NPCs use, so GiveItem /
        # GivePokemon behave correctly; gated by EVENT_GOT_TOWN_MAP (one-time)
        # and only after the Oak's-Parcel quest, so it can't break the intro.
        anchor = re.compile(r'(\n[ \t]*SetEvent EVENT_GOT_TOWN_MAP\b[^\n]*\n)')
        if not anchor.search(text):
            self.log("  [WARN] EVENT_GOT_TOWN_MAP anchor not found — extras skipped")
            return

        text = anchor.sub(lambda mm: mm.group(1) + "\tcall RandomizerGiveExtras\n",
                          text, count=1)

        # Build the routine, appended at end of file (own label, reached by an
        # absolute call → no jr-range constraints).
        L = ["\n; ==== Randomizer Extras ====\n", "RandomizerGiveExtras:\n"]

        # --- Bag items: GiveItem (b=item, c=qty) ---
        for it in bag:
            L += [f"\tlb bc, {it['const']}, {it['qty']}\n",
                  "\tcall GiveItem\n"]

        # --- PC items: AddItemToInventory targeting the PC list (wNumBoxItems) ---
        for it in pc:
            L += [f"\tld a, {it['const']}\n", "\tld [wcf91], a\n",
                  f"\tld a, {it['qty']}\n", "\tld [wItemQuantity], a\n",
                  "\tld hl, wNumBoxItems\n", "\tcall AddItemToInventory\n"]

        # --- Gift Pokémon: full GivePokemon text-script pattern (matches the
        #     Charmander gift on Route 24).  GivePokemon puts the mon in the
        #     party if there's room, else the PC box — and handles the
        #     "received/sent to BOX" text correctly. ---
        any_custom_moves = False
        for idx, m in enumerate(mons):
            lvl = max(1, min(100, int(m.get('level', 5))))
            L += [
                f"\tld a, {m['species']}\n",
                "\tld [wcf91], a\n",
                "\tld [wd11e], a\n",
                "\tcall GetMonName\n",
                "\tld a, $1\n",
                "\tld [wDoNotWaitForButtonPressAfterDisplayingText], a\n",
                # Set level explicitly too: GivePokemon copies c → wCurEnemyLVL,
                # but writing it directly first guarantees the level even if an
                # earlier call left wCurEnemyLVL in an unexpected state.
                f"\tld a, {lvl}\n",
                "\tld [wCurEnemyLVL], a\n",
                f"\tlb bc, {m['species']}, {lvl}\n",
                "\tcall GivePokemon\n",
                "\tld a, [wAddedToParty]\n",
                "\tand a\n",
                "\tcall z, WaitForTextScrollButtonPress\n",
            ]
            # Override the auto-assigned level-up moves with the user's picks.
            if m["moves"]:
                any_custom_moves = True
                # pad to 4 slots with NO_MOVE
                slots = (m["moves"] + ["NO_MOVE"] * 4)[:4]
                L += [
                    f"\tld hl, .moves_{idx}\n",
                    "\tcall RandomizerSetLastMonMoves\n",
                ]

        L += ["\tret\n"]

        # Per-mon move data tables (4 bytes each) referenced above.
        for idx, m in enumerate(mons):
            if m["moves"]:
                slots = (m["moves"] + ["NO_MOVE"] * 4)[:4]
                L.append(f".moves_{idx}: db " + ", ".join(slots) + "\n")

        # Shared helper: write 4 move IDs (hl→table) into the most recently
        # added mon (party tail if wAddedToParty, else box tail), then recompute
        # PP via the game's own LoadMovePPs.  Uses documented struct offsets
        # MON_MOVES (8) and MON_PP (29); box struct length = 33 (0x21),
        # party struct length = 44 (0x2C).
        if any_custom_moves:
            # Helper computes the just-added mon's struct base into wBuffer (a
            # 2-byte scratch pointer), then writes the 4 move ids and recomputes
            # PP.  Using a WRAM scratch pointer avoids fragile push/pop juggling.
            L += [
                "RandomizerSetLastMonMoves:\n",
                "\t; hl = pointer to 4 move-id bytes (kept in de)\n",
                "\tld d, h\n\tld e, l\n",        # de = move-id table
                "\tld a, [wAddedToParty]\n",
                "\tand a\n",
                "\tjr z, .toBox\n",
                "\tld a, [wPartyCount]\n",
                "\tdec a\n",
                "\tld bc, 44\n",
                "\tld hl, wPartyMons\n",
                "\tcall AddNTimes\n",            # hl = struct base
                "\tjr .haveStruct\n",
                ".toBox:\n",
                "\tld a, [wBoxCount]\n",
                "\tdec a\n",
                "\tld bc, 33\n",
                "\tld hl, wBoxMons\n",
                "\tcall AddNTimes\n",            # hl = struct base
                ".haveStruct:\n",
                "\t; stash struct base in wBuffer\n",
                "\tld a, l\n\tld [wBuffer], a\n",
                "\tld a, h\n\tld [wBuffer+1], a\n",
                "\t; --- write 4 move ids to base+MON_MOVES(8) ---\n",
                "\tld bc, 8\n\tadd hl, bc\n",    # hl = &MON_MOVES
                "\t; copy de(table) -> hl(moves), 4 bytes\n",
                "\tld a, [de]\n\tld [hli], a\n\tinc de\n",
                "\tld a, [de]\n\tld [hli], a\n\tinc de\n",
                "\tld a, [de]\n\tld [hli], a\n\tinc de\n",
                "\tld a, [de]\n\tld [hli], a\n",
                "\t; --- recompute PP via LoadMovePPs ---\n",
                "\t; It reads move ids from hl, and does `inc de` BEFORE each\n",
                "\t; PP write, so de must point to MON_PP-1 (offset 28), NOT\n",
                "\t; MON_PP (29).  Passing 29 made the 4th PP byte spill into\n",
                "\t; MON_LEVEL (offset 33), corrupting the level.\n",
                "\tld a, [wBuffer]\n\tld l, a\n",
                "\tld a, [wBuffer+1]\n\tld h, a\n",  # hl = struct base
                "\tld bc, 28\n\tadd hl, bc\n",     # hl = &MON_PP - 1
                "\tld d, h\n\tld e, l\n",          # de = MON_PP - 1
                "\tld a, [wBuffer]\n\tld l, a\n",
                "\tld a, [wBuffer+1]\n\tld h, a\n",  # hl = struct base
                "\tld bc, 8\n\tadd hl, bc\n",      # hl = &MON_MOVES
                "\tpredef LoadMovePPs\n",
                "\tret\n",
            ]

        L += ["; ==== End Randomizer Extras ====\n"]

        text = text.rstrip("\n") + "\n" + "".join(L)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self._cache.pop(self._BLUES_HOUSE_FILE, None)
        self.log(f"  Extras: {len(bag)} bag, {len(pc)} PC item(s), {len(mons)} gift Pokémon "
                 f"(via Daisy's Town Map gift)")

    # ─────────────────────────────────────────────────────────────────────────
    # Shop items (Zero Grinding / Elite 4 Prep)
    # ─────────────────────────────────────────────────────────────────────────

    def _patch_item_prices(self, prices: dict):
        """
        Set item prices in data/items/prices.asm.
        Format: bcd3 PRICE  ; ITEM_NAME
        prices = {"RARE_CANDY": 10, ...}
        """
        lines = self._load(PRICES_FILE)
        if not lines:
            return
        for i, line in enumerate(lines):
            s = line.split(';')[0].strip()
            m = re.match(r'bcd3\s+\d+', s)
            if m:
                # Find the item name in the comment
                comment = line.split(';', 1)[1].strip() if ';' in line else ''
                item_name = comment.strip()
                if item_name in prices:
                    indent = re.match(r'(\s*)', line).group(1)
                    lines[i] = f"{indent}bcd3 {prices[item_name]}  ; {item_name}\n"
                    self.log(f"  Price: {item_name} → ${prices[item_name]}")

    def _add_items_to_script_mart(self, rel_path: str, item_consts: list,
                                  occurrence: int = 0):
        """
        Add items to a  script_mart ITEM1, ITEM2, ...  line in a Yellow
        script file.  Items already present are skipped.

        Yellow mart format — the macro sits on its own line, e.g.:
            ViridianMartClerkText::
                script_mart POKE_BALL, POTION, ANTIDOTE, PARLYZ_HEAL

        Because the label is on a *separate* line from the macro, we locate
        the macro directly.  `occurrence` selects which script_mart in the
        file to patch (0 = first), since some files (e.g. Indigo Plateau)
        contain more than one mart.  The assembler counts args via _NARG.
        """
        lines = self._load(rel_path)
        if not lines:
            self.log(f"  [WARN] {rel_path} not found — shop patch skipped")
            return

        # Collect indices of every script_mart line
        mart_idxs = [i for i, ln in enumerate(lines)
                     if re.match(r'\s*script_mart\b', ln)]
        if not mart_idxs:
            self.log(f"  [WARN] No script_mart found in {rel_path} — skipped")
            return
        if occurrence >= len(mart_idxs):
            occurrence = 0  # fall back to the first mart

        i = mart_idxs[occurrence]
        line = lines[i]
        m = re.search(r'script_mart\s+(.*)', line)
        if not m:
            self.log(f"  [WARN] Malformed script_mart in {rel_path} — skipped")
            return

        existing_raw = m.group(1).split(';')[0]
        existing = [x.strip() for x in existing_raw.split(',') if x.strip()]
        to_add = [ic for ic in item_consts if ic not in existing]
        if not to_add:
            self.log(f"  {os.path.basename(rel_path)}: all items already present")
            return

        new_items_str = ', '.join(existing + to_add)
        prefix = line[:m.start()]
        comment = ''
        raw = m.group(1)
        if ';' in raw:
            comment = '  ;' + raw.split(';', 1)[1]
        lines[i] = f"{prefix}script_mart {new_items_str}{comment}\n"
        for ic in to_add:
            self.log(f"  Added {ic} to mart in {os.path.basename(rel_path)}")

    def write_zero_grinding(self):
        """
        Zero Grinding: add Rare Candy at $10 to Viridian City Mart
        (the first accessible shop in Yellow).
        """
        self._patch_item_prices({"RARE_CANDY": 10})
        self._add_items_to_script_mart(VIRIDIAN_MART_FILE, ["RARE_CANDY"])

    def write_elite4_prep(self):
        """
        Elite 4 Prep: stock the Indigo Plateau main mart with key healing
        items at $10 each.
        """
        self._patch_item_prices({
            "RARE_CANDY":   10,
            "FULL_RESTORE": 10,
            "MAX_ELIXER":   10,
            "MAX_REVIVE":   10,
        })
        self._add_items_to_script_mart(
            INDIGO_PLATEAU_LOBBY_FILE,
            ["RARE_CANDY", "FULL_RESTORE", "MAX_ELIXER", "MAX_REVIVE"],
            occurrence=0,   # first script_mart = the item mart
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Flush
    # ─────────────────────────────────────────────────────────────────────────

    def flush_all(self):
        """Write all cached (modified) files to the output directory."""
        for rel_path, lines in self._cache.items():
            out_path = self._out(rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.writelines(lines)
        self.log(f"  Flushed {len(self._cache)} file(s) to output directory.")
