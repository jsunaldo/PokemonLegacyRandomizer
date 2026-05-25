"""
Pokemon Crystal Legacy Randomizer v1.0 — Web UI entry point

Starts a local HTTP server, opens the UI in the default browser,
and shuts down cleanly when the browser tab closes or the user clicks Quit.

Requires only Python 3.6+ stdlib — no pip installs needed.
"""

import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Shared state (accessed from multiple threads)
# ---------------------------------------------------------------------------
_state_lock  = threading.Lock()
_log_lines   = []          # accumulated log output
_job_running = False       # True while randomization is in progress
_job_done    = False       # True when last job finished
_job_error   = None        # error string if job failed
_shutdown_ev = threading.Event()


def _append_log(msg: str):
    with _state_lock:
        _log_lines.append(msg)


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------
# Support both normal execution and PyInstaller frozen bundles
if getattr(sys, "frozen", False):
    _BASE_DIR = sys._MEIPASS          # PyInstaller extracts data here
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE_DIR, "static")


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence request logging

    # ---- routing ----

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
        elif path == "/crystal":
            self._serve_file(os.path.join(STATIC_DIR, "crystal.html"), "text/html")
        elif path == "/yellow":
            self._serve_file(os.path.join(STATIC_DIR, "yellow.html"), "text/html")
        elif path == "/emerald":
            self._serve_file(os.path.join(STATIC_DIR, "emerald.html"), "text/html")
        elif path == "/api/log":
            self._api_get_log()
        elif path == "/api/status":
            self._api_status()
        elif path == "/api/browse":
            self._api_browse()
        elif path == "/api/items":
            self._api_items()
        elif path == "/api/quit":
            self._send_json({"ok": True})
            threading.Thread(target=_shutdown_ev.set, daemon=True).start()
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/randomize":
            self._api_randomize(data)
        elif path == "/api/randomize_yellow":
            self._api_randomize_yellow(data)
        elif path == "/api/randomize_emerald":
            self._api_randomize_emerald(data)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ---- API handlers ----

    def _api_items(self):
        """Return the full list of items available for starting-item configuration."""
        from item_data import STARTING_ITEM_POOL_ALL
        self._send_json({"items": [{"const": c, "name": n} for c, n in STARTING_ITEM_POOL_ALL]})

    def _api_browse(self):
        """Open a native macOS folder picker via osascript."""
        try:
            r = subprocess.run(
                ["osascript", "-e",
                 'POSIX path of (choose folder with prompt "Select folder:")'],
                capture_output=True, text=True, timeout=60
            )
            folder = r.stdout.strip()
            if folder:
                self._send_json({"path": folder})
            else:
                self._send_json({"path": "", "cancelled": True})
        except Exception as e:
            self._send_json({"path": "", "error": str(e)})

    def _api_get_log(self):
        qs = parse_qs(urlparse(self.path).query)
        since = int(qs.get("since", ["0"])[0])
        with _state_lock:
            lines = _log_lines[since:]
            total = len(_log_lines)
        self._send_json({"lines": lines, "total": total})

    def _api_status(self):
        with _state_lock:
            self._send_json({
                "running": _job_running,
                "done":    _job_done,
                "error":   _job_error,
            })

    def _api_randomize(self, data: dict):
        global _job_running, _job_done, _job_error, _log_lines

        with _state_lock:
            if _job_running:
                self._send_json({"ok": False, "error": "Already running"})
                return
            _job_running = True
            _job_done    = False
            _job_error   = None
            _log_lines   = []

        self._send_json({"ok": True})
        threading.Thread(target=_run_randomizer, args=(data,), daemon=True).start()

    def _api_randomize_yellow(self, data: dict):
        global _job_running, _job_done, _job_error, _log_lines

        with _state_lock:
            if _job_running:
                self._send_json({"ok": False, "error": "Already running"})
                return
            _job_running = True
            _job_done    = False
            _job_error   = None
            _log_lines   = []

        self._send_json({"ok": True})
        threading.Thread(target=_run_randomizer_yellow, args=(data,), daemon=True).start()

    def _api_randomize_emerald(self, data: dict):
        global _job_running, _job_done, _job_error, _log_lines

        with _state_lock:
            if _job_running:
                self._send_json({"ok": False, "error": "Already running"})
                return
            _job_running = True
            _job_done    = False
            _job_error   = None
            _log_lines   = []

        self._send_json({"ok": True})
        threading.Thread(target=_run_randomizer_emerald, args=(data,), daemon=True).start()

    # ---- helpers ----

    def _serve_file(self, path: str, content_type: str):
        try:
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self._cors()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ---------------------------------------------------------------------------
# Randomization worker (runs in background thread)
# ---------------------------------------------------------------------------

def _run_randomizer(data: dict):
    global _job_running, _job_done, _job_error

    def log(msg):
        _append_log(msg)

    try:
        import random as _random

        src = data.get("sourceDir", "").strip()
        out = data.get("outputDir", "").strip()
        seed_raw = data.get("seed", "")

        if not src or not os.path.isdir(src):
            raise ValueError(f"Source directory not found: {src!r}")
        if not out:
            raise ValueError("Output directory is required.")
        if src == out:
            raise ValueError("Source and Output directories must be different.")

        try:
            seed = int(seed_raw)
        except (ValueError, TypeError):
            seed = _random.randint(0, 999999)

        log("=" * 56)
        log(f"Crystal Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        # -- import here so path is already set --
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from parser import CrystalLegacyParser
        from randomizer_engine import RandomizerEngine, RandomizerSettings
        from writer import SourceWriter

        # Parse
        log("\nParsing source files...")
        parser = CrystalLegacyParser(src, log_fn=log)
        starters_found = parser.parse_all()

        log(f"\nFound: {len(parser.wild_encounters)} encounter groups, "
            f"{len(parser.fish_slots)} fish slot(s), "
            f"{len(parser.trainers)} trainers, "
            f"{len(parser.static_encounters)} static encounters, "
            f"starters={'yes' if starters_found else 'NOT FOUND'}")

        # Build settings from request data
        # Global generation filter (applies to all categories)
        gen_filter = data.get("genFilter", "all")   # "all" | "gen1" | "gen2"
        gen1_only  = (gen_filter == "gen1")
        gen2_only  = (gen_filter == "gen2")
        if gen_filter != "all":
            log(f"  Pokémon pool limited to: {'Gen 1 only' if gen1_only else 'Gen 2 only'}")

        s = RandomizerSettings(seed=seed)
        s.starter_mode            = data.get("starterMode", "random")   # 'unchanged'|'custom'|'random'|'random_two_stage'
        if s.starter_mode == "custom" and len(data.get("customStarters", [])) == 3:
            s.custom_starters = [int(x) for x in data["customStarters"]]
        s.starter_random_items    = data.get("starterRandItems", False)
        s.starter_ban_bad_items   = data.get("starterBanBadItems", True)
        s.easier_evolutions       = data.get("easierEvolutions", False)
        s.remove_time_evolutions  = data.get("removeTimeEvolutions", False)
        s.full_hm_compat          = data.get("fullHMCompat", False)

        s.wild_mode             = data.get("wildMode", "random")   # 'unchanged'|'random'|'area1to1'|'global1to1'
        s.wild_rule             = data.get("wildRule", "none")    # 'none'|'similar_strength'|'catch_em_all'|'type_themed'
        s.wild_gen1_only        = gen1_only
        s.wild_gen2_only        = gen2_only
        s.wild_use_time_based   = data.get("wildTimeBased", True)
        s.wild_no_legendaries   = data.get("wildNoLegendaries", False)
        s.wild_random_held_items = data.get("wildRandHeldItems", False)
        s.wild_ban_bad_held_items = data.get("wildBanBadHeldItems", True)

        s.trainer_mode                = data.get("trainerMode", "random")
        s.trainer_no_legendaries      = data.get("trainerNoLegend", False)
        s.trainer_boss_no_legendaries = data.get("trainerBossNoLegend", True)
        s.trainer_no_babies           = data.get("trainerNoBaby", True)
        s.trainer_gen1_only           = gen1_only
        s.trainer_gen2_only           = gen2_only
        s.trainer_similar_strength      = data.get("trainerSimilarStrength", False)
        s.trainer_rival_starter         = data.get("trainerRivalStarter", False)
        s.trainer_weight_types          = data.get("trainerWeightTypes", False)
        s.trainer_force_fully_evolved   = data.get("trainerForceEvolved", False)
        s.trainer_force_evo_level       = int(data.get("trainerForceEvoLevel", 30))

        s.trade_mode             = data.get("tradeMode", "unchanged")  # 'unchanged'|'given_only'|'both'
        s.trade_random_nicknames = data.get("tradeRandNicknames", False)
        s.trade_random_ot        = data.get("tradeRandOT", False)
        s.trade_random_ivs       = data.get("tradeRandIVs", False)
        s.trade_random_items     = data.get("tradeRandItems", False)

        s.static_mode     = data.get("staticMode", "unchanged")  # 'unchanged'|'swap'|'random'|'similar_strength'
        s.static_gen1_only = gen1_only
        s.static_gen2_only = gen2_only

        s.field_items_mode     = data.get("fieldItemsMode", "unchanged")  # 'unchanged'|'random'
        s.field_items_ban_bad  = data.get("fieldItemsBanBad", True)

        s.zero_grinding        = data.get("zeroGrinding", False)
        s.elite4_prep          = data.get("elite4Prep", False)

        # Starting items — list of {const, qty} dicts; empty list = unchanged
        starting_bag_items = data.get("startingBagItems", [])
        starting_pc_items  = data.get("startingPCItems",  [])

        # PC Pokémon — list of mon dicts; empty list = unchanged
        pc_pokemon = data.get("pcPokemon", []) if data.get("pcPokemonEnable", False) else []

        engine = RandomizerEngine(s, log_fn=log)

        log("\n--- Randomizing ---")
        rand_starters         = parser.starters
        rand_starter_items    = parser.starter_items
        rand_evolutions       = parser.evolution_entries
        rand_tmhm_compat      = parser.tmhm_compat
        rand_wild             = parser.wild_encounters
        rand_fish_slots       = parser.fish_slots
        rand_trainers         = parser.trainers
        rand_static           = parser.static_encounters
        rand_trades           = parser.trades
        rand_wild_held_items  = parser.wild_held_items
        rand_field_items      = parser.field_items

        if s.starter_mode != "unchanged":
            if starters_found:
                log("Starters:")
                rand_starters = engine.randomize_starters(parser.starters)
                if s.starter_random_items:
                    rand_starter_items = engine.randomize_starter_items(parser.starter_items)
            else:
                log("[WARN] Starters not found in source — skipping.")

        if s.easier_evolutions or s.remove_time_evolutions:
            log("Evolutions:")
            if parser.evolution_entries:
                rand_evolutions = engine.apply_evolution_changes(parser.evolution_entries)
            else:
                log("  [WARN] No evolution entries found — skipping evolution changes.")

        if s.full_hm_compat:
            log("TM/HM Compatibility:")
            if parser.tmhm_compat:
                rand_tmhm_compat = engine.apply_full_hm_compat(parser.tmhm_compat)
            else:
                log("  [WARN] No tmhm entries found in source — skipping.")

        if s.wild_mode != "unchanged":
            log("Wild Pokemon:")
            rand_wild = engine.randomize_wild(parser.wild_encounters)
            if parser.fish_slots:
                log("Fishing encounters:")
                rand_fish_slots = engine.randomize_fish_slots(parser.fish_slots)
            else:
                log("  [SKIP] No fish slots found — fishing randomization skipped.")

        if s.trainer_mode != "unchanged":
            log("Trainers:")
            # Always pass the level evo map — needed for rival starter AND force-evolved
            s.rival_level_evo_map = parser.level_evo_map
            if s.trainer_rival_starter:
                if starters_found and s.starter_mode != "unchanged":
                    from constants import POKEMON_CONSTANTS as _PC
                    s.rival_starter_ids = [_PC.get(sl.species_const, 0) for sl in rand_starters]
                else:
                    s.rival_starter_ids = [152, 155, 158]  # Chikorita, Cyndaquil, Totodile
            rand_trainers = engine.randomize_trainers(parser.trainers)

        if s.trade_mode != "unchanged":
            log("In-Game Trades:")
            if parser.trades:
                rand_trades = engine.randomize_trades(parser.trades)
            else:
                log("  [WARN] No in-game trades found in source — skipping.")

        if s.static_mode != "unchanged":
            log("Static Pokemon:")
            if parser.static_encounters:
                rand_static = engine.randomize_static(parser.static_encounters, s.static_mode)
            else:
                log("  [WARN] No static encounters found in source — skipping.")

        if s.wild_random_held_items:
            log("Wild Held Items:")
            if parser.wild_held_items:
                rand_wild_held_items = engine.randomize_wild_held_items(parser.wild_held_items)
            else:
                log("  [WARN] No wild held item entries found in source — skipping.")

        if s.field_items_mode != "unchanged":
            log("Field Items:")
            if parser.field_items:
                rand_field_items = engine.randomize_field_items(parser.field_items)
            else:
                log("  [WARN] No field items found in source — skipping.")

        log("\n--- Writing output ---")
        writer = SourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()

        if (s.easier_evolutions or s.remove_time_evolutions) and rand_evolutions:
            log("Writing evolution changes...")
            writer.write_evolutions(parser.evolution_entries, rand_evolutions)

        if s.full_hm_compat and parser.tmhm_compat:
            log("Writing TM/HM compatibility...")
            writer.write_tmhm_compat(parser.tmhm_compat, rand_tmhm_compat)

        if s.starter_mode != "unchanged" and starters_found:
            log("Writing starters...")
            writer.write_starters(parser.starters, rand_starters)
            if s.starter_random_items and rand_starter_items:
                log("Writing starter held items...")
                writer.write_starter_items(parser.starter_items, rand_starter_items)
            log("Writing starter dialogue...")
            writer.write_starter_dialogue(
                parser.starters, rand_starters,
                parser.starter_dialogue_lines,
                parser.starter_text_lines,
            )

        if s.wild_mode != "unchanged":
            log("Writing wild encounters...")
            writer.write_wild_encounters(parser.wild_encounters, rand_wild)
            if parser.fish_slots:
                log("Writing fishing encounters...")
                writer.write_fish_encounters(parser.fish_slots, rand_fish_slots)

        if s.trainer_mode != "unchanged":
            log("Writing trainer parties...")
            writer.write_trainers(parser.trainers, rand_trainers)

        if s.trade_mode != "unchanged" and parser.trades:
            log("Writing in-game trades...")
            writer.write_trades(parser.trades, rand_trades)

        if s.static_mode != "unchanged" and parser.static_encounters:
            log("Writing static encounters...")
            writer.write_static_encounters(parser.static_encounters, rand_static)

        if s.wild_random_held_items and parser.wild_held_items:
            log("Writing wild held items...")
            writer.write_wild_held_items(parser.wild_held_items, rand_wild_held_items)

        if s.field_items_mode != "unchanged" and parser.field_items:
            log("Writing field items...")
            writer.write_field_items(parser.field_items, rand_field_items)

        if s.zero_grinding:
            log("Zero Grinding: adding Rare Candy to Cherrygrove Mart...")
            writer.write_zero_grinding()

        if s.elite4_prep:
            log("Elite 4 Prep: stocking Indigo Plateau Mart...")
            writer.write_elite4_prep()

        # ---- Diagnostics for new-game injection features ----
        log(f"\n  intro_menu.asm: {'FOUND → ' + str(parser.intro_menu_path) if parser.intro_menu_path else 'NOT FOUND (items/PC Pokémon will be skipped)'}")
        log(f"  Starting bag items received : {len(starting_bag_items)} item(s)")
        log(f"  Starting PC  items received : {len(starting_pc_items)} item(s)")
        log(f"  PC Pokémon   received       : {len(pc_pokemon)} Pokémon")

        if (starting_bag_items or starting_pc_items) and parser.intro_menu_path:
            log("Writing starting items...")
            writer.write_starting_items(starting_bag_items, starting_pc_items,
                                        parser.intro_menu_path)
        elif (starting_bag_items or starting_pc_items) and not parser.intro_menu_path:
            log("[WARN] Starting items configured but intro_menu.asm not found — skipped.")
        elif not starting_bag_items and not starting_pc_items:
            log("  (Starting items feature not enabled or no items added — skipped.)")

        if pc_pokemon and parser.intro_menu_path:
            log("Writing PC Pokémon...")
            writer.write_pc_pokemon(pc_pokemon, parser.intro_menu_path)
        elif pc_pokemon and not parser.intro_menu_path:
            log("[WARN] PC Pokémon configured but intro_menu.asm not found — skipped.")
        elif not pc_pokemon:
            log("  (PC Pokémon feature not enabled or no Pokémon added — skipped.)")

        writer.flush_all()

        # ---- Optional ROM build ----
        build_rom = data.get("buildRom", True)
        rom_path = None

        if build_rom:
            log("\n" + "=" * 56)
            log("Building ROM with 'make'...")
            log("=" * 56)

            # Expand PATH to include common locations where RGBDS / make live
            import shutil as _shutil
            env = os.environ.copy()
            extra_paths = [
                "/usr/local/bin",          # Homebrew (Intel Mac)
                "/opt/homebrew/bin",       # Homebrew (Apple Silicon)
                "/usr/bin",
                "/bin",
            ]
            env["PATH"] = ":".join(extra_paths + env.get("PATH", "").split(":"))

            # Verify make is reachable with the expanded PATH
            make_exe = _shutil.which("make", path=env["PATH"])
            if not make_exe:
                raise RuntimeError(
                    "Could not find 'make'. "
                    "Install Xcode Command Line Tools:  xcode-select --install"
                )

            # Verify RGBDS is present and is a compatible version (0.5.x–0.9.x)
            rgbasm_exe = _shutil.which("rgbasm", path=env["PATH"])
            if not rgbasm_exe:
                raise RuntimeError(
                    "Could not find 'rgbasm'. "
                    "Install RGBDS 0.5.2: https://github.com/gbdev/rgbds/releases/tag/v0.5.2"
                )
            ver_result = subprocess.run(
                [rgbasm_exe, "--version"], capture_output=True, text=True
            )
            ver_line = (ver_result.stdout + ver_result.stderr).strip().splitlines()[0] \
                       if (ver_result.stdout + ver_result.stderr).strip() else ""
            log(f"  RGBDS: {ver_line}")
            # Warn if major version is 1+ (breaking syntax changes vs Crystal Legacy)
            import re as _re
            ver_match = _re.search(r'(\d+)\.(\d+)\.(\d+)', ver_line)
            if ver_match and int(ver_match.group(1)) >= 1:
                raise RuntimeError(
                    f"Incompatible RGBDS version detected: {ver_line}. "
                    "Crystal Legacy requires RGBDS 0.5.2. "
                    "Install it from: https://github.com/gbdev/rgbds/releases/tag/v0.5.2  "
                    "Then run: sudo cp rgbasm rgblink rgbfix rgbgfx /usr/local/bin/"
                )

            proc = subprocess.Popen(
                [make_exe],
                cwd=out,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            for line in proc.stdout:
                log(line.rstrip())
            proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"'make' failed with exit code {proc.returncode}. "
                    "Check the log above for compiler errors. "
                    "Make sure RGBDS is installed: https://rgbds.gbdev.io/"
                )

            # Remind about new-game requirement if injection features were used
            if starting_bag_items or starting_pc_items or pc_pokemon:
                log("\n⚠️  IMPORTANT: Starting Items and PC Pokémon only appear")
                log("   when you START A NEW GAME — they will NOT appear on a")
                log("   saved/continued game. Delete your save file or use a")
                log("   fresh emulator state before testing.")

            # Find the ROM — try canonical name first, then any .gbc in the dir
            candidate = os.path.join(out, "pokecrystal.gbc")
            if os.path.isfile(candidate):
                rom_path = candidate
            else:
                gbc_files = [
                    os.path.join(out, f) for f in os.listdir(out)
                    if f.endswith(".gbc")
                ]
                if gbc_files:
                    rom_path = sorted(gbc_files)[-1]  # pick most recent if multiple
                    log(f"  (ROM found as: {os.path.basename(rom_path)})")
                else:
                    raise RuntimeError(
                        "'make' succeeded but no .gbc file was found in the output directory. "
                        "Check the Makefile for the actual output filename."
                    )

            # Ask the user where to save the ROM via a native macOS save dialog
            log("\nChoose where to save the ROM…")
            default_name = f"CrystalLegacy_Randomized_{seed}.gbc"
            save_result = subprocess.run(
                ["osascript", "-e",
                 f'POSIX path of (choose file name with prompt "Save your randomized ROM:"'
                 f' default name "{default_name}")'],
                capture_output=True, text=True, timeout=120,
            )
            save_dest = save_result.stdout.strip()

            if save_dest:
                # Ensure .gbc extension
                if not save_dest.lower().endswith(".gbc"):
                    save_dest += ".gbc"
                import shutil as _shutil2
                _shutil2.copy2(rom_path, save_dest)
                rom_path = save_dest
                log(f"ROM saved to: {rom_path}")
            else:
                log(f"Save dialog cancelled — ROM remains at:\n  {rom_path}")

        log("\n" + "=" * 56)
        if build_rom and rom_path:
            log("Done! ROM built successfully:")
            log(f"  {rom_path}")
        else:
            log("Done! Randomized source saved to:")
            log(f"  {out}")
            log("\nTo compile the ROM, open Terminal in that folder and run:")
            log("  make")
            log("\nThe ROM will be: pokecrystal.gbc")
        log("=" * 56)

        with _state_lock:
            global _job_done
            _job_done = True

    except Exception as exc:
        import traceback
        log(f"\n[ERROR] {exc}")
        log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True

    finally:
        with _state_lock:
            global _job_running
            _job_running = False


# ---------------------------------------------------------------------------
# Yellow Legacy randomization worker (runs in background thread)
# ---------------------------------------------------------------------------

def _run_randomizer_yellow(data: dict):
    global _job_running, _job_done, _job_error

    def log(msg):
        _append_log(msg)

    try:
        import random as _random

        src = data.get("sourceDir", "").strip()
        out = data.get("outputDir", "").strip()
        seed_raw = data.get("seed", "")

        if not src or not os.path.isdir(src):
            raise ValueError(f"Source directory not found: {src!r}")
        if not out:
            raise ValueError("Output directory is required.")
        if src == out:
            raise ValueError("Source and Output directories must be different.")

        try:
            seed = int(seed_raw)
        except (ValueError, TypeError):
            seed = _random.randint(0, 999999)

        log("=" * 56)
        log(f"Yellow Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from parser_yellow import YellowLegacyParser
        from randomizer_engine_yellow import YellowRandomizerEngine, YellowRandomizerSettings
        from writer_yellow import YellowSourceWriter

        # ── Parse ──────────────────────────────────────────────────────────────
        log("\nParsing source files...")
        parser = YellowLegacyParser(src, log_fn=log)
        starters_found = parser.parse_all()

        log(f"\nFound: {len(parser.wild_groups)} wild groups, "
            f"{len(parser.trainers)} trainers, "
            f"{len(parser.old_rod_slots)} old-rod slots, "
            f"{len(parser.good_rod_slots)} good-rod slots, "
            f"{len(parser.super_rod_slots)} super-rod slots, "
            f"{len(parser.trades)} trade(s), "
            f"starters={'yes' if starters_found else 'NOT FOUND'}")

        # ── Build settings ─────────────────────────────────────────────────────
        s = YellowRandomizerSettings(seed=seed)
        s.starter_mode             = data.get("starterMode", "random")
        s.starter_no_legendaries   = data.get("starterNoLegendaries", True)
        if s.starter_mode == "custom":
            s.custom_starter = data.get("customStarter") or None

        s.wild_mode                = data.get("wildMode", "random")
        s.wild_rule                = data.get("wildRule", "none")
        s.wild_no_legendaries      = data.get("wildNoLegendaries", False)
        # Fishing follows Wild Pokémon — no separate tab/setting
        s.fishing_mode             = "unchanged" if s.wild_mode == "unchanged" else "random"
        s.fishing_no_legendaries   = s.wild_no_legendaries

        s.trainer_mode             = data.get("trainerMode", "random")
        s.trainer_no_legendaries   = data.get("trainerNoLegend", False)
        s.trainer_boss_no_legendaries = data.get("trainerBossNoLegend", True)
        s.trainer_force_fully_evolved = data.get("trainerForceEvolved", False)
        s.trainer_force_evo_level  = int(data.get("trainerForceEvoLevel", 30))

        s.static_mode              = data.get("staticMode", "unchanged")
        s.trade_mode               = data.get("tradeMode", "unchanged")
        s.trade_random_nicknames   = data.get("tradeRandNicknames", False)
        s.trade_random_ot          = data.get("tradeRandOT", False)

        s.field_items_mode         = data.get("fieldItemsMode", "unchanged")
        s.field_items_ban_bad      = data.get("fieldItemsBanBad", True)

        start_items_enable         = data.get("startItemsEnable", False)
        s.randomize_start_items    = start_items_enable
        s.start_items              = data.get("startBagItems", []) if start_items_enable else []
        s.start_pc_items           = data.get("startPCItems",  []) if start_items_enable else []

        s.easier_evolutions        = data.get("easierEvolutions", False)
        s.full_hm_compat           = data.get("fullHMCompat", False)
        pc_pokemon_enable          = data.get("pcPokemonEnable", False)
        pc_pokemon                 = data.get("pcPokemon", []) if pc_pokemon_enable else []

        engine = YellowRandomizerEngine(s, log_fn=log)

        # ── Randomize ──────────────────────────────────────────────────────────
        log("\n--- Randomizing ---")

        # Carry-through copies (used verbatim if the feature is "unchanged")
        rand_wild        = parser.wild_groups
        rand_old_rod     = parser.old_rod_slots
        rand_good_rod    = parser.good_rod_slots
        rand_super_rod   = parser.super_rod_slots
        rand_trainers    = parser.trainers
        rand_static      = parser.static_encounters
        rand_trades      = parser.trades
        rand_field_items = parser.field_items
        rand_evolutions  = parser.evolutions
        rand_tmhm_compat = parser.tmhm_compat
        new_starter_const = None

        if s.starter_mode != "unchanged":
            if starters_found:
                log("Starter:")
                new_starter_const = engine.randomize_starter(parser.starters)
            else:
                log("[WARN] Starter not found in source — skipping.")

        if s.wild_mode != "unchanged":
            log("Wild Pokémon:")
            rand_wild = engine.randomize_wild(parser.wild_groups)

        if s.fishing_mode != "unchanged":
            log("Fishing:")
            rand_old_rod   = engine.randomize_fishing_simple(parser.old_rod_slots, "Old Rod")
            rand_good_rod  = engine.randomize_fishing_simple(parser.good_rod_slots, "Good Rod")
            rand_super_rod = engine.randomize_super_rod(parser.super_rod_slots)

        if s.trainer_mode != "unchanged":
            log("Trainers:")
            if s.trainer_force_fully_evolved and parser.evolutions:
                engine._level_evo_map = engine.build_level_evo_map(parser.evolutions)
            rand_trainers = engine.randomize_trainers(parser.trainers)

        if s.static_mode != "unchanged":
            log("Static Pokémon:")
            if parser.static_encounters:
                rand_static = engine.randomize_static(parser.static_encounters)
            else:
                log("  [WARN] No static encounters found in source — skipping.")

        trade_any = (s.trade_mode != "unchanged" or
                     s.trade_random_nicknames or s.trade_random_ot)
        if trade_any:
            log("In-Game Trades:")
            if parser.trades:
                rand_trades = engine.randomize_trades(parser.trades)
            else:
                log("  [WARN] No in-game trades found in source — skipping.")

        if s.field_items_mode != "unchanged":
            log("Field Items:")
            if parser.field_items:
                rand_field_items = engine.randomize_field_items(parser.field_items)
            else:
                log("  [WARN] No field items found in source — skipping.")

        if s.easier_evolutions:
            log("Evolutions:")
            if parser.evolutions:
                rand_evolutions = engine.apply_evolution_changes(parser.evolutions)
            else:
                log("  [WARN] No evolution entries found — skipping.")

        if s.full_hm_compat:
            log("TM/HM Compatibility:")
            if parser.tmhm_compat:
                rand_tmhm_compat = engine.apply_full_hm_compat(parser.tmhm_compat)
            else:
                log("  [WARN] No tmhm entries found — skipping.")

        # ── Write output ───────────────────────────────────────────────────────
        log("\n--- Writing output ---")
        writer = YellowSourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()

        if s.starter_mode != "unchanged" and starters_found and new_starter_const:
            log("Writing starter...")
            writer.write_starter(parser.starters, new_starter_const)

        if s.wild_mode != "unchanged":
            log("Writing wild encounters...")
            writer.write_wild_encounters(parser.wild_groups, rand_wild)

        if s.fishing_mode != "unchanged":
            log("Writing fishing...")
            writer.write_fishing_simple(parser.old_rod_slots, rand_old_rod, "Old Rod")
            writer.write_fishing_simple(parser.good_rod_slots, rand_good_rod, "Good Rod")
            writer.write_super_rod(parser.super_rod_slots, rand_super_rod)

        if s.trainer_mode != "unchanged":
            log("Writing trainer parties...")
            writer.write_trainers(parser.trainers, rand_trainers)

        if s.static_mode != "unchanged" and parser.static_encounters:
            log("Writing static encounters...")
            writer.write_static_encounters(parser.static_encounters, rand_static)

        if trade_any and parser.trades:
            log("Writing in-game trades...")
            writer.write_trades(parser.trades, rand_trades)

        if s.field_items_mode != "unchanged" and parser.field_items:
            log("Writing field items...")
            writer.write_field_items(parser.field_items, rand_field_items)

        if s.randomize_start_items and (s.start_items or s.start_pc_items):
            log("Writing starting items...")
            writer.write_starting_items(s.start_items, s.start_pc_items)

        if s.easier_evolutions and parser.evolutions:
            log("Writing evolution changes...")
            writer.write_evolutions(parser.evolutions, rand_evolutions)

        if s.full_hm_compat and parser.tmhm_compat:
            log("Writing TM/HM compatibility...")
            writer.write_tmhm_compat(parser.tmhm_compat, rand_tmhm_compat)

        if pc_pokemon:
            log("PC Pokémon:")
            writer.write_pc_pokemon(pc_pokemon)

        writer.flush_all()

        # ── Optional ROM build ─────────────────────────────────────────────────
        build_rom = data.get("buildRom", True)
        rom_path  = None

        if build_rom:
            log("\n" + "=" * 56)
            log("Building ROM with 'make'...")
            log("=" * 56)

            import shutil as _shutil
            env = os.environ.copy()
            extra_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin"]
            env["PATH"] = ":".join(extra_paths + env.get("PATH", "").split(":"))

            make_exe = _shutil.which("make", path=env["PATH"])
            if not make_exe:
                raise RuntimeError(
                    "Could not find 'make'. "
                    "Install Xcode Command Line Tools:  xcode-select --install"
                )

            rgbasm_exe = _shutil.which("rgbasm", path=env["PATH"])
            if not rgbasm_exe:
                raise RuntimeError(
                    "Could not find 'rgbasm'. "
                    "Install RGBDS: https://github.com/gbdev/rgbds/releases"
                )
            ver_result = subprocess.run(
                [rgbasm_exe, "--version"], capture_output=True, text=True
            )
            ver_line = (ver_result.stdout + ver_result.stderr).strip().splitlines()[0] \
                       if (ver_result.stdout + ver_result.stderr).strip() else ""
            log(f"  RGBDS: {ver_line}")

            proc = subprocess.Popen(
                [make_exe],
                cwd=out,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            for line in proc.stdout:
                log(line.rstrip())
            proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"'make' failed with exit code {proc.returncode}. "
                    "Check the log above for compiler errors."
                )

            # Find the ROM — Yellow Legacy outputs pokeyellow.gbc
            candidate = os.path.join(out, "pokeyellow.gbc")
            if os.path.isfile(candidate):
                rom_path = candidate
            else:
                gbc_files = [
                    os.path.join(out, f) for f in os.listdir(out)
                    if f.endswith(".gbc")
                ]
                if gbc_files:
                    rom_path = sorted(gbc_files)[-1]
                    log(f"  (ROM found as: {os.path.basename(rom_path)})")
                else:
                    raise RuntimeError(
                        "'make' succeeded but no .gbc file found in the output directory."
                    )

            log("\nChoose where to save the ROM…")
            default_name = f"YellowLegacy_Randomized_{seed}.gbc"
            save_result = subprocess.run(
                ["osascript", "-e",
                 f'POSIX path of (choose file name with prompt "Save your randomized ROM:"'
                 f' default name "{default_name}")'],
                capture_output=True, text=True, timeout=120,
            )
            save_dest = save_result.stdout.strip()

            if save_dest:
                if not save_dest.lower().endswith(".gbc"):
                    save_dest += ".gbc"
                import shutil as _shutil2
                _shutil2.copy2(rom_path, save_dest)
                rom_path = save_dest
                log(f"ROM saved to: {rom_path}")
            else:
                log(f"Save dialog cancelled — ROM remains at:\n  {rom_path}")

        log("\n" + "=" * 56)
        if build_rom and rom_path:
            log("Done! ROM built successfully:")
            log(f"  {rom_path}")
        else:
            log("Done! Randomized source saved to:")
            log(f"  {out}")
            log("\nTo compile the ROM, open Terminal in that folder and run:")
            log("  make")
            log("\nThe ROM will be: pokeyellow.gbc")
        log("=" * 56)

        with _state_lock:
            global _job_done
            _job_done = True

    except Exception as exc:
        import traceback
        log(f"\n[ERROR] {exc}")
        log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True

    finally:
        with _state_lock:
            global _job_running
            _job_running = False


# ---------------------------------------------------------------------------
# Emerald Legacy randomization worker (runs in background thread)
# ---------------------------------------------------------------------------

def _run_randomizer_emerald(data: dict):
    global _job_running, _job_done, _job_error

    def log(msg):
        _append_log(msg)

    try:
        import random as _random

        src = data.get("sourceDir", "").strip()
        out = data.get("outputDir", "").strip()
        seed_raw = data.get("seed", "")

        if not src or not os.path.isdir(src):
            raise ValueError(f"Source directory not found: {src!r}")
        if not out:
            raise ValueError("Output directory is required.")
        if src == out:
            raise ValueError("Source and Output directories must be different.")

        try:
            seed = int(seed_raw)
        except (ValueError, TypeError):
            seed = _random.randint(0, 999999)

        log("=" * 56)
        log(f"Emerald Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from parser_emerald import EmeraldLegacyParser
        from randomizer_engine_emerald import EmeraldRandomizerEngine, EmeraldRandomizerSettings
        from writer_emerald import EmeraldSourceWriter

        # ── Parse ──────────────────────────────────────────────────────────────
        log("\nParsing source files...")
        parser = EmeraldLegacyParser(src, log_fn=log)
        starters_found = parser.parse_all()

        log(f"\nFound: {len(parser.wild_slots)} wild slot(s), "
            f"{len(parser.trainer_parties)} trainer parties, "
            f"{len(parser.field_items)} field item(s), "
            f"{len(parser.static_encounters)} static encounter(s), "
            f"starters={'yes' if starters_found else 'NOT FOUND'}")

        # ── Build settings ─────────────────────────────────────────────────────
        s = EmeraldRandomizerSettings(seed=seed)

        # General
        s.gen_filter              = data.get("genFilter", "all")
        s.easier_evolutions       = data.get("easierEvolutions", False)
        s.full_hm_compat          = data.get("fullHMCompat", False)

        # Starters
        s.starter_mode           = data.get("starterMode", "random")
        s.starter_no_legendaries = data.get("starterNoLegendaries", True)
        s.starter_rand_items     = data.get("starterRandItems", False)
        s.starter_ban_bad_items  = data.get("starterBanBadItems", True)
        if s.starter_mode == "custom":
            customs = data.get("customStarters", [None, None, None])
            s.custom_starters = [c or None for c in customs]

        # Wild
        s.wild_mode              = data.get("wildMode", "random")
        s.wild_rule              = data.get("wildRule", "none")
        s.wild_no_legendaries    = data.get("wildNoLegendaries", False)
        s.wild_rand_held_items   = data.get("wildRandHeldItems", False)
        s.wild_ban_bad_held_items = data.get("wildBanBadHeldItems", True)
        s.randomize_rock_smash   = data.get("randomizeRockSmash", True)
        s.randomize_fishing      = data.get("randomizeFishing", True)

        # Trainers
        s.trainer_mode                = data.get("trainerMode", "random")
        trainer_no_leg                = data.get("trainerNoLegend", False)
        s.trainer_no_legendaries      = trainer_no_leg
        s.trainer_boss_no_legendaries = trainer_no_leg
        s.trainer_similar_strength    = data.get("trainerSimilarStrength", False)
        s.trainer_rival_starter       = data.get("trainerRivalStarter", False)
        s.trainer_weight_types        = data.get("trainerWeightTypes", False)
        s.trainer_force_fully_evolved = data.get("trainerForceEvolved", False)
        s.trainer_force_evo_level     = int(data.get("trainerForceEvoLevel", 30))

        # Static
        s.static_mode            = data.get("staticMode", "unchanged")

        # Trades (stubs)
        s.trade_mode              = data.get("tradeMode", "unchanged")
        s.trade_rand_nicknames    = data.get("tradeRandNicknames", False)
        s.trade_rand_ot           = data.get("tradeRandOT", False)
        s.trade_rand_ivs          = data.get("tradeRandIVs", False)
        s.trade_rand_items_flag   = data.get("tradeRandItems", False)

        # Field items
        s.field_items_mode       = data.get("fieldItemsMode", "unchanged")
        s.field_items_ban_bad    = data.get("fieldItemsBanBad", True)

        # Starting items (bag + PC)
        if data.get("startItemsEnable"):
            s.randomize_start_items = True
            s.start_items    = data.get("startBagItems", [])
            s.start_pc_items = data.get("startPcItems", [])

        # PC Pokémon
        s.pc_pokemon_enable = data.get("pcPokemonEnable", False)
        s.pc_pokemon        = data.get("pcPokemon", [])

        engine = EmeraldRandomizerEngine(
            settings=s,
            species_consts=parser.species_consts,
            species_bst=parser.species_bst,
            species_types=parser.species_types,
            species_numbers=parser.species_numbers,
            log_fn=log,
        )

        # Log stub features
        if s.easier_evolutions:
            log("  [INFO] Easier Evolutions: not yet implemented for Emerald — skipped.")
        if s.full_hm_compat:
            log("  [INFO] Full HM Compatibility: not yet implemented for Emerald — skipped.")
        if s.trade_mode != 'unchanged':
            log("  [INFO] Trade randomization: not yet implemented for Emerald — skipped.")
        if s.starter_rand_items:
            log("  [INFO] Starter held items: not yet implemented for Emerald — skipped.")
        if s.wild_rand_held_items:
            log("  [INFO] Wild held item randomization: not yet implemented for Emerald — skipped.")
        if s.trainer_rival_starter:
            log("  [INFO] Rival Carries Starter: not yet implemented for Emerald — skipped.")

        # Build level evo map if needed for force-evolve
        # (Emerald doesn't have a dedicated evo parser yet — placeholder)
        # engine._level_evo_map = {}

        # ── Randomize ──────────────────────────────────────────────────────────
        log("\n--- Randomizing ---")

        rand_wild_json   = parser.wild_json
        rand_parties     = parser.trainer_parties
        rand_starters    = [st.species for st in parser.starters]
        rand_static      = parser.static_encounters
        rand_field_items = parser.field_items

        if s.wild_mode != "unchanged":
            log("Wild Pokémon:")
            rand_wild_json = engine.randomize_wild(parser.wild_json)

        if s.trainer_mode != "unchanged":
            log("Trainers:")
            rand_parties = engine.randomize_trainers(parser.trainer_parties)

        if s.starter_mode != "unchanged":
            if starters_found:
                log("Starters:")
                rand_starters = engine.randomize_starters(parser.starters)
            else:
                log("[WARN] Starters not found in source — skipping.")

        if s.static_mode != "unchanged":
            log("Static Pokémon:")
            if parser.static_encounters:
                rand_static = engine.randomize_static(parser.static_encounters)
            else:
                log("  [WARN] No static encounters found in source — skipping.")

        if s.field_items_mode != "unchanged":
            log("Field Items:")
            if parser.field_items:
                rand_field_items = engine.randomize_field_items(parser.field_items)
            else:
                log("  [WARN] No field items found in source — skipping.")

        # ── Write output ───────────────────────────────────────────────────────
        log("\n--- Writing output ---")
        writer = EmeraldSourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()

        if s.wild_mode != "unchanged":
            log("Writing wild encounters...")
            writer.write_wild_encounters(rand_wild_json)

        if s.trainer_mode != "unchanged":
            log("Writing trainer parties...")
            writer.write_trainer_parties(parser.trainer_parties, rand_parties)

        if s.starter_mode != "unchanged" and starters_found:
            log("Writing starters...")
            writer.write_starters(parser.starters, rand_starters)

        if s.static_mode != "unchanged" and parser.static_encounters:
            log("Writing static encounters...")
            writer.write_static_encounters(parser.static_encounters, rand_static)

        if s.field_items_mode != "unchanged" and parser.field_items:
            log("Writing field items...")
            writer.write_field_items(parser.field_items, rand_field_items)

        writer.flush_all()

        # ── Optional ROM build ─────────────────────────────────────────────────
        build_rom = data.get("buildRom", True)
        rom_path  = None

        if build_rom:
            log("\n" + "=" * 56)
            log("Building ROM with 'make'...")
            log("=" * 56)

            import shutil as _shutil
            env = os.environ.copy()
            extra_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin"]
            env["PATH"] = ":".join(extra_paths + env.get("PATH", "").split(":"))

            make_exe = _shutil.which("make", path=env["PATH"])
            if not make_exe:
                raise RuntimeError(
                    "Could not find 'make'. "
                    "Install Xcode Command Line Tools:  xcode-select --install"
                )

            proc = subprocess.Popen(
                [make_exe],
                cwd=out,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            for line in proc.stdout:
                log(line.rstrip())
            proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"'make' failed with exit code {proc.returncode}. "
                    "Check the log above for compiler errors. "
                    "Make sure devkitARM is installed and in your PATH."
                )

            # Find the ROM — Emerald typically outputs pokeemerald.gba
            candidate = os.path.join(out, "pokeemerald.gba")
            if os.path.isfile(candidate):
                rom_path = candidate
            else:
                gba_files = [
                    os.path.join(out, f) for f in os.listdir(out)
                    if f.endswith(".gba")
                ]
                if gba_files:
                    rom_path = sorted(gba_files)[-1]
                    log(f"  (ROM found as: {os.path.basename(rom_path)})")
                else:
                    raise RuntimeError(
                        "'make' succeeded but no .gba file found in the output directory."
                    )

            log("\nChoose where to save the ROM…")
            default_name = f"EmeraldLegacy_Randomized_{seed}.gba"
            save_result = subprocess.run(
                ["osascript", "-e",
                 f'POSIX path of (choose file name with prompt "Save your randomized ROM:"'
                 f' default name "{default_name}")'],
                capture_output=True, text=True, timeout=120,
            )
            save_dest = save_result.stdout.strip()

            if save_dest:
                if not save_dest.lower().endswith(".gba"):
                    save_dest += ".gba"
                import shutil as _shutil2
                _shutil2.copy2(rom_path, save_dest)
                rom_path = save_dest
                log(f"ROM saved to: {rom_path}")
            else:
                log(f"Save dialog cancelled — ROM remains at:\n  {rom_path}")

        log("\n" + "=" * 56)
        if build_rom and rom_path:
            log("Done! ROM built successfully:")
            log(f"  {rom_path}")
        else:
            log("Done! Randomized source saved to:")
            log(f"  {out}")
            log("\nTo compile the ROM, open Terminal in that folder and run:")
            log("  make")
            log("\nThe ROM will be: pokeemerald.gba")
        log("=" * 56)

        with _state_lock:
            global _job_done
            _job_done = True

    except Exception as exc:
        import traceback
        log(f"\n[ERROR] {exc}")
        log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True

    finally:
        with _state_lock:
            global _job_running
            _job_running = False


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------

def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    print(f"Pokemon Legacy Randomizer running at {url}", flush=True)

    # Small delay then open browser.
    # Use macOS 'open' directly — more reliable than webbrowser when launched
    # from Finder (no shell profile, no DISPLAY variable, etc.)
    def open_browser():
        import time; time.sleep(0.6)
        try:
            subprocess.Popen(["/usr/bin/open", url])
        except Exception:
            try:
                webbrowser.open(url)
            except Exception:
                pass
    threading.Thread(target=open_browser, daemon=True).start()

    # Block until the /api/quit endpoint fires the event
    _shutdown_ev.wait()
    server.shutdown()
    print("Server stopped.")


if __name__ == "__main__":
    main()
