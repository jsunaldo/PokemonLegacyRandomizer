"""
Pokemon Legacy Randomizer v1.0 — Web UI entry point

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
# Toolchain manager — auto-download RGBDS and devkitARM on first use
# ---------------------------------------------------------------------------

# Cache sits next to main.py so it survives between app launches
_TOOLCHAIN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".toolchain_cache")

# Pinned RGBDS versions (game-specific requirements)
_RGBDS_CRYSTAL = "0.5.2"   # Crystal Legacy requires exactly 0.5.2
_RGBDS_YELLOW  = "0.7.0"   # Yellow Legacy: 0.6.0+ required; 0.8.0+ breaks EQU syntax → pin 0.7.0


def _ensure_rgbds(version: str, log_fn) -> str:
    """
    Guarantee a specific RGBDS version is available, downloading it from
    GitHub Releases if not already cached.  Returns the directory that
    contains rgbasm / rgblink / rgbfix / rgbgfx.
    """
    import platform, stat, tarfile, tempfile, urllib.request, json as _json
    import shutil as _sh

    # Non-macOS: the auto-installer only ships macOS binaries. Use a
    # system-installed RGBDS from PATH instead, or explain how to get one.
    if sys.platform != "darwin":
        found = _sh.which("rgbasm")
        if found:
            log_fn(f"  RGBDS from PATH: {found} "
                   f"(make sure it is version {version} for this game)")
            return os.path.dirname(found)
        raise RuntimeError(
            f"RGBDS v{version} is required. Auto-install is only available on "
            "macOS — install RGBDS from https://rgbds.gbdev.io/install and "
            "make sure 'rgbasm' is on your PATH."
        )

    bin_dir  = os.path.join(_TOOLCHAIN_CACHE, f"rgbds-{version}")
    rgbasm   = os.path.join(bin_dir, "rgbasm")

    # Already cached and executable → done
    if os.path.isfile(rgbasm) and os.access(rgbasm, os.X_OK):
        log_fn(f"  RGBDS v{version} (cached)")
        return bin_dir

    log_fn(f"  RGBDS v{version} not found locally — fetching from GitHub…")

    # Ask the GitHub API which assets this release has
    api_url = f"https://api.github.com/repos/gbdev/rgbds/releases/tags/v{version}"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "Pokemon-Legacy-Randomizer/1.0",
                 "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            release = _json.loads(resp.read())
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach GitHub to download RGBDS v{version}: {exc}\n"
            "Check your internet connection."
        )

    machine = platform.machine().lower()   # "arm64" on Apple Silicon, "x86_64" on Intel
    assets  = release.get("assets", [])

    def _score(name: str) -> int:
        """
        Score a release asset name.  Must be a macOS binary (not source tarball,
        not Windows/Linux).  RGBDS ships macOS binaries as .zip; source as .tar.gz
        with no platform in the name — so we require 'macos' or 'darwin'.

        Naming has changed across versions:
          v0.5.2–0.8.x : rgbds-X.Y.Z-macos-x86-64.zip  (or x86_64)
          v0.9.x       : rgbds-X.Y.Z-macos.zip          (universal)
          v1.0.x+      : rgbds-macos.zip                 (universal)
        """
        nl = name.lower()
        # Must be a zip (macOS binaries) — tar.gz is always source
        if not nl.endswith(".zip"):
            return -1
        # Skip non-Mac platforms
        if any(p in nl for p in ("windows", "linux", "win32", "win64")):
            return -1
        # Require an explicit platform marker — excludes any stray non-platform zips
        if "darwin" not in nl and "macos" not in nl:
            return -1
        score = 10  # confirmed macOS binary
        # Prefer exact arch match; newer universal builds also score well
        if machine.replace("_", "-") in nl or machine in nl:
            score += 5
        elif "universal" in nl or (nl.endswith("-macos.zip") or nl == "rgbds-macos.zip"):
            score += 4   # universal / no-arch = runs natively on all Macs
        return score

    best = max(assets, key=lambda a: _score(a["name"]), default=None)
    if not best or _score(best["name"]) < 0:
        raise RuntimeError(
            f"No macOS binary found for RGBDS v{version} on GitHub.\n"
            f"Check: https://github.com/gbdev/rgbds/releases/tag/v{version}"
        )

    asset_name = best["name"]
    log_fn(f"  Downloading {asset_name} …")
    os.makedirs(bin_dir, exist_ok=True)

    # Use correct suffix so extraction logic works
    suffix = ".zip" if asset_name.lower().endswith(".zip") else ".tar.gz"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)

    try:
        urllib.request.urlretrieve(best["browser_download_url"], tmp_path)

        executables = {"rgbasm", "rgblink", "rgbfix", "rgbgfx"}

        if suffix == ".zip":
            import zipfile
            with zipfile.ZipFile(tmp_path) as zf:
                for info in zf.infolist():
                    base = os.path.basename(info.filename)
                    if base in executables and not info.is_dir():
                        info.filename = base   # flatten into bin_dir
                        zf.extract(info, bin_dir)
                        dest = os.path.join(bin_dir, base)
                        os.chmod(dest, os.stat(dest).st_mode
                                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        else:
            with tarfile.open(tmp_path) as tar:
                for member in tar.getmembers():
                    if os.path.basename(member.name) in executables and member.isfile():
                        member.name = os.path.basename(member.name)
                        tar.extract(member, bin_dir)
                        dest = os.path.join(bin_dir, member.name)
                        os.chmod(dest, os.stat(dest).st_mode
                                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        # Don't leave a partial cache directory behind
        import shutil as _shutil
        _shutil.rmtree(bin_dir, ignore_errors=True)
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not os.path.isfile(rgbasm):
        import shutil as _shutil
        _shutil.rmtree(bin_dir, ignore_errors=True)
        raise RuntimeError(
            f"Downloaded {asset_name} but could not find rgbasm inside it.\n"
            "Please report this issue with the asset name above."
        )

    log_fn(f"  RGBDS v{version} ready")
    return bin_dir


def _ensure_gba_toolchain(log_fn) -> dict:
    """
    Guarantee the full GBA build toolchain is ready:
      1. devkitARM (arm-none-eabi cross-compiler + binutils with embedded newlib)
      2. Homebrew libpng + pkg-config (needed to compile host gbagfx tool)
      3. agbcc (the GBA C compiler used by pokeemerald MODERN=0 builds)
         → built once from pret/agbcc, cached in _TOOLCHAIN_CACHE/agbcc_install/

    Returns a dict with:
      "DEVKITPRO", "DEVKITARM" — env vars for the Makefile
      "PATH"                   — prepend to PATH (devkitARM bins + tools)
      "PKG_CONFIG_PATH"        — needed so host gbagfx can find libpng headers
      "agbcc_install_dir"      — directory whose contents mirror tools/agbcc/
                                 (caller must copy into the output tree before make)
    """
    import shutil as _shutil, urllib.request, tempfile, stat

    # Non-macOS: auto-install is macOS-only. Use an existing devkitPro
    # install (DEVKITPRO env or /opt/devkitpro) + agbcc if present.
    if sys.platform != "darwin":
        dkp = os.environ.get("DEVKITPRO", "/opt/devkitpro")
        arm = os.path.join(dkp, "devkitARM", "bin", "arm-none-eabi-gcc")
        agbcc_dir = os.path.join(_TOOLCHAIN_CACHE, "agbcc_install")
        if os.path.isfile(arm) and os.path.isfile(os.path.join(agbcc_dir, "bin", "agbcc")):
            log_fn(f"  devkitARM from {dkp} (system install)")
            return {
                "DEVKITPRO": dkp,
                "DEVKITARM": os.path.join(dkp, "devkitARM"),
                "PATH": os.path.join(dkp, "devkitARM", "bin"),
                "PKG_CONFIG_PATH": os.environ.get("PKG_CONFIG_PATH", ""),
                "agbcc_install_dir": agbcc_dir,
            }
        raise RuntimeError(
            "GBA toolchain auto-install is only available on macOS. Install "
            "devkitARM (https://devkitpro.org/wiki/Getting_Started), build "
            "agbcc (https://github.com/pret/agbcc) into "
            f"{agbcc_dir}, then retry."
        )

    # ── 1. devkitARM ─────────────────────────────────────────────────────────
    devkitpro = "/opt/devkitpro"
    arm_gcc   = os.path.join(devkitpro, "devkitARM", "bin", "arm-none-eabi-gcc")

    if os.path.isfile(arm_gcc):
        log_fn("  devkitARM found")
    else:
        log_fn("  devkitARM not found — installing via devkitPro (one-time setup)…")
        log_fn("  → A macOS password prompt will appear. This installs the GBA toolchain.")
        log_fn("  → Download ~145 MB, may take several minutes. Please wait.")

        # Fetch the real asset name from the GitHub releases API
        import json as _json
        api_url = "https://api.github.com/repos/devkitPro/pacman/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Pokemon-Legacy-Randomizer/1.0",
                     "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            release = _json.loads(resp.read())
        pkg_asset = next(
            (a for a in release.get("assets", [])
             if a["name"].endswith(".pkg")),
            None,
        )
        if not pkg_asset:
            raise RuntimeError(
                "Could not find devkitPro macOS installer on GitHub.\n"
                "Check: https://github.com/devkitPro/pacman/releases"
            )

        tmp_pkg = os.path.join(tempfile.gettempdir(), pkg_asset["name"])
        log_fn(f"  Downloading {pkg_asset['name']} ({pkg_asset['size']//1_000_000} MB)…")
        urllib.request.urlretrieve(pkg_asset["browser_download_url"], tmp_pkg)

        # Run installer + gba-dev via osascript (triggers native password dialog)
        shell_cmd = (
            f"installer -pkg '{tmp_pkg}' -target / && "
            "/usr/local/bin/dkp-pacman -Syu --noconfirm && "
            "/usr/local/bin/dkp-pacman -S --noconfirm gba-dev"
        )
        osa = f'do shell script "{shell_cmd}" with administrator privileges'
        log_fn("  Waiting for password dialog…")
        result = subprocess.run(
            ["osascript", "-e", osa],
            capture_output=True, text=True, timeout=900,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "devkitARM installation failed or was cancelled.\n"
                + (f"Detail: {err}" if err else "")
            )
        log_fn("  devkitARM installed successfully!")
        if not os.path.isfile(arm_gcc):
            raise RuntimeError(
                "devkitARM install appeared to succeed but arm-none-eabi-gcc "
                "was not found. Please restart the app."
            )

    # ── 2. Homebrew libpng + pkg-config ──────────────────────────────────────
    brew = _shutil.which("brew") or "/opt/homebrew/bin/brew"
    if os.path.isfile(brew):
        for pkg in ("libpng", "pkg-config"):
            try:
                result = subprocess.run(
                    [brew, "list", pkg],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    log_fn(f"  Installing Homebrew {pkg}…")
                    subprocess.run(
                        [brew, "install", pkg],
                        capture_output=True, text=True, timeout=300,
                    )
            except Exception:
                pass  # best-effort

    # Build PKG_CONFIG_PATH: Homebrew libpng + a tiny zlib.pc shim
    hb_pkgconfig = "/opt/homebrew/lib/pkgconfig"
    zlib_shim_dir = os.path.join(_TOOLCHAIN_CACHE, "pkgconfig_shims")
    os.makedirs(zlib_shim_dir, exist_ok=True)
    zlib_pc = os.path.join(zlib_shim_dir, "zlib.pc")
    if not os.path.isfile(zlib_pc):
        with open(zlib_pc, "w") as f:
            f.write("Name: zlib\nDescription: zlib\nVersion: 1.2\nCflags:\nLibs: -lz\n")
    pkg_config_path = hb_pkgconfig + os.pathsep + zlib_shim_dir

    # ── 3. agbcc (build once, cache) ─────────────────────────────────────────
    agbcc_cache = os.path.join(_TOOLCHAIN_CACHE, "agbcc_install")
    agbcc_bin   = os.path.join(agbcc_cache, "bin", "agbcc")

    if os.path.isfile(agbcc_bin) and os.access(agbcc_bin, os.X_OK):
        log_fn("  agbcc (cached)")
    else:
        log_fn("  agbcc not found in cache — building from pret/agbcc…")
        os.makedirs(agbcc_cache, exist_ok=True)

        with tempfile.TemporaryDirectory() as build_tmp:
            # Clone agbcc
            log_fn("  Cloning pret/agbcc…")
            result = subprocess.run(
                ["git", "clone", "--depth=1",
                 "https://github.com/pret/agbcc", build_tmp],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to clone pret/agbcc: {result.stderr.strip()}\n"
                    "Check your internet connection."
                )

            # Build agbcc using devkitARM's arm-none-eabi tools
            dka_bin = os.path.join(devkitpro, "devkitARM", "bin")
            dka_tools = os.path.join(devkitpro, "tools", "bin")
            build_env = os.environ.copy()
            build_env["DEVKITPRO"] = devkitpro
            build_env["DEVKITARM"] = os.path.join(devkitpro, "devkitARM")
            build_env["PATH"] = dka_bin + os.pathsep + dka_tools + os.pathsep + build_env.get("PATH", "")

            log_fn("  Building agbcc (this takes ~30 seconds)…")
            result = subprocess.run(
                ["./build.sh"],
                cwd=build_tmp,
                capture_output=True, text=True, timeout=300,
                env=build_env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"agbcc build.sh failed:\n{result.stderr[-1000:]}"
                )

            # Install into cache: mirror what install.sh does
            import shutil as _sh
            for d in ("bin", "include", "lib"):
                os.makedirs(os.path.join(agbcc_cache, d), exist_ok=True)
            for exe in ("agbcc", "old_agbcc", "agbcc_arm"):
                src = os.path.join(build_tmp, exe)
                dst = os.path.join(agbcc_cache, "bin", exe)
                _sh.copy2(src, dst)
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            # libc/include → include/
            libc_inc = os.path.join(build_tmp, "libc", "include")
            if os.path.isdir(libc_inc):
                for item in os.listdir(libc_inc):
                    s = os.path.join(libc_inc, item)
                    d = os.path.join(agbcc_cache, "include", item)
                    if os.path.isdir(s):
                        _sh.copytree(s, d, dirs_exist_ok=True)
                    else:
                        _sh.copy2(s, d)
            # ginclude → include/
            ginclude = os.path.join(build_tmp, "ginclude")
            if os.path.isdir(ginclude):
                for item in os.listdir(ginclude):
                    _sh.copy2(os.path.join(ginclude, item),
                               os.path.join(agbcc_cache, "include", item))
            # libs
            for lib in ("libgcc.a", "libc.a"):
                src = os.path.join(build_tmp, lib)
                if os.path.isfile(src):
                    _sh.copy2(src, os.path.join(agbcc_cache, "lib", lib))

        log_fn("  agbcc built and cached successfully!")

    dka_bin   = os.path.join(devkitpro, "devkitARM", "bin")
    dka_tools = os.path.join(devkitpro, "tools", "bin")
    return {
        "DEVKITPRO":       devkitpro,
        "DEVKITARM":       os.path.join(devkitpro, "devkitARM"),
        "PATH":            dka_bin + os.pathsep + dka_tools,
        "PKG_CONFIG_PATH": pkg_config_path,
        "agbcc_install_dir": agbcc_cache,
    }


# keep old name as alias so nothing else breaks
_ensure_devkitarm = _ensure_gba_toolchain


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


def _save_rom_with_dialog(rom_path: str, default_name: str, ext: str, log) -> str:
    """
    Prompt the user (via a macOS save dialog) for where to copy the built ROM.

    Robust against the common failure modes:
      • The dialog is forced to the foreground so it can't hide behind windows.
      • A generous timeout is used; on timeout / cancel / any error the freshly
        built ROM is auto-saved to ~/Downloads (never lost) and that path is
        returned instead of crashing the whole job.

    Returns the final path the ROM lives at.
    """
    # Headless/automation mode (smoke tests, CI) and non-macOS platforms:
    # skip the native dialog and leave the ROM where the build put it.
    if os.environ.get("RANDOMIZER_NO_DIALOG") or sys.platform != "darwin":
        log(f"\nROM saved at: {rom_path}")
        return rom_path

    log("\nChoose where to save the ROM…  (a Save dialog should appear — "
        "check behind other windows if you don't see it)")

    # `tell application "System Events" to activate` forces the dialog frontmost,
    # even when the server is running as a background process.
    script = (
        'tell application "System Events" to activate\n'
        'POSIX path of (choose file name with prompt "Save your randomized ROM:" '
        f'default name "{default_name}")'
    )

    def _fallback(reason: str) -> str:
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        dest_dir  = downloads if os.path.isdir(downloads) else os.path.dirname(rom_path)
        dest = os.path.join(dest_dir, default_name)
        # Avoid clobbering an existing file
        n = 1
        while os.path.isfile(dest):
            stem = default_name[:-len(ext)] if default_name.lower().endswith(ext) else default_name
            dest = os.path.join(dest_dir, f"{stem}_{n}{ext}")
            n += 1
        try:
            import shutil as _sh
            _sh.copy2(rom_path, dest)
            log(f"  {reason} — ROM auto-saved to:\n  {dest}")
            return dest
        except Exception as exc:
            log(f"  {reason} — could not auto-save ({exc}); ROM remains at:\n  {rom_path}")
            return rom_path

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return _fallback("Save dialog timed out")
    except Exception as exc:
        return _fallback(f"Save dialog failed ({exc})")

    save_dest = result.stdout.strip()
    if not save_dest:
        # User pressed Cancel (osascript exits non-zero with empty stdout)
        return _fallback("Save dialog cancelled")

    if not save_dest.lower().endswith(ext):
        save_dest += ext
    try:
        import shutil as _sh
        _sh.copy2(rom_path, save_dest)
        log(f"ROM saved to: {save_dest}")
        return save_dest
    except Exception as exc:
        return _fallback(f"Could not write to chosen location ({exc})")


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
        elif self._serve_static(path):
            pass
        else:
            self.send_error(404)

    # Serve static assets (images, css, etc.) from the static/ folder.
    # Returns True if it handled the request.
    _STATIC_TYPES = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
        ".ico": "image/x-icon", ".css": "text/css", ".js": "text/javascript",
    }

    def _serve_static(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        ctype = self._STATIC_TYPES.get(ext)
        if not ctype:
            return False
        # Resolve safely inside STATIC_DIR (block path traversal)
        rel = path.lstrip("/")
        full = os.path.realpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(os.path.realpath(STATIC_DIR) + os.sep):
            return False
        if not os.path.isfile(full):
            return False
        self._serve_file(full, ctype)
        return True

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
        """Return the item pool for starting-item selectors (game-aware)."""
        game = (parse_qs(urlparse(self.path).query).get("game", [""])[0]).lower()
        if game == "emerald":
            from item_data import EMERALD_ALL_ITEM_POOL as POOL
        elif game == "yellow":
            try:
                from item_data import YELLOW_STARTING_ITEM_POOL as POOL
            except ImportError:
                from item_data import STARTING_ITEM_POOL_ALL as POOL
        else:
            from item_data import STARTING_ITEM_POOL_ALL as POOL
        self._send_json({"items": [{"const": c, "name": n} for c, n in POOL]})

    def _api_browse(self):
        """Open a native macOS folder picker via osascript."""
        if sys.platform != "darwin":
            self._send_json({"path": "", "unsupported": True,
                             "message": "Folder picker is macOS-only — "
                                        "type the path into the field instead."})
            return
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
# Shared pipeline helpers (used by all three game handlers)
# ---------------------------------------------------------------------------

# Wire-format aliases: the three game UIs (and their historical saved-settings
# files) spell some keys differently. Normalize both directions so any saved
# settings file works with any game handler.
_SETTINGS_ALIASES = [
    ("startingItemsEnable", "startItemsEnable"),
    ("startingBagItems",    "startBagItems"),
    ("startingPCItems",     "startPcItems"),
]


def _normalize_settings(data: dict) -> dict:
    for a, b in _SETTINGS_ALIASES:
        if a in data and b not in data:
            data[b] = data[a]
        elif b in data and a not in data:
            data[a] = data[b]
    return data


def _prep_job(data: dict):
    """Validate source/output dirs and resolve the seed.

    Returns (src, out, seed). Raises ValueError on bad input."""
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
    return src, out, seed


def _save_settings_used(data: dict, seed: int, out: str, log):
    """Auto-save the exact settings used (reproducibility). Best-effort."""
    try:
        used = {"seed": seed}
        used.update({k: v for k, v in data.items()
                     if k not in ("sourceDir", "outputDir", "seed")})
        path = os.path.join(out, "settings_used.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(used, f, indent=2)
        log(f"Settings saved: {path}")
    except Exception as e:
        log(f"[WARN] Could not save settings_used.json: {e}")


def _run_make_build(out: str, log, kind: str, rgbds_version=None):
    """Run 'make' in the output tree with the right toolchain on PATH.

    kind: "gb" (RGBDS, needs rgbds_version) or "gba" (devkitARM + agbcc).
    Streams build output to the log; raises RuntimeError on failure."""
    import shutil as _shutil

    log("\n" + "=" * 56)
    log("Building ROM with 'make'...")
    log("=" * 56)

    env = os.environ.copy()
    base_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin"]
    env["PATH"] = os.pathsep.join(base_paths + env.get("PATH", "").split(os.pathsep))

    make_exe = _shutil.which("make", path=env["PATH"])
    if not make_exe:
        raise RuntimeError(
            "Could not find 'make'. "
            "Install Xcode Command Line Tools:  xcode-select --install"
        )

    if kind == "gb":
        log("Checking RGBDS toolchain…")
        rgbds_bin = _ensure_rgbds(rgbds_version, log)
        env["PATH"] = rgbds_bin + os.pathsep + env["PATH"]
    else:  # gba
        log("Checking GBA toolchain (devkitARM + agbcc)…")
        gba_env = _ensure_gba_toolchain(log)
        env["DEVKITPRO"]       = gba_env["DEVKITPRO"]
        env["DEVKITARM"]       = gba_env["DEVKITARM"]
        env["PATH"]            = gba_env["PATH"] + os.pathsep + env["PATH"]
        env["PKG_CONFIG_PATH"] = gba_env["PKG_CONFIG_PATH"]

        # Install agbcc into the output directory (tools/agbcc/)
        agbcc_src = gba_env["agbcc_install_dir"]
        agbcc_dst = os.path.join(out, "tools", "agbcc")
        if not os.path.isfile(os.path.join(agbcc_dst, "bin", "agbcc")):
            log("  Installing agbcc into output directory…")
            _shutil.copytree(agbcc_src, agbcc_dst, dirs_exist_ok=True)

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


def _find_rom(out: str, canonical: str, ext: str, log) -> str:
    """Locate the built ROM: canonical name first, else newest *ext in out."""
    candidate = os.path.join(out, canonical)
    if os.path.isfile(candidate):
        return candidate
    rom_files = [
        os.path.join(out, f) for f in os.listdir(out)
        if f.endswith(ext)
    ]
    if rom_files:
        rom_path = sorted(rom_files)[-1]  # pick most recent if multiple
        log(f"  (ROM found as: {os.path.basename(rom_path)})")
        return rom_path
    raise RuntimeError(
        f"'make' succeeded but no {ext} file was found in the output directory. "
        "Check the Makefile for the actual output filename."
    )


def _warn_new_game_required(log):
    """Remind that injected items/Pokémon only appear on a brand-new save."""
    log("\n⚠️  IMPORTANT: Starting Items and PC Pokémon only appear")
    log("   when you START A NEW GAME — they will NOT appear on a")
    log("   saved/continued game. Delete your save file or use a")
    log("   fresh emulator state before testing.")


def _log_finish(build_rom: bool, rom_path, out: str, canonical: str, log):
    """Final success footer for a randomizer run."""
    log("\n" + "=" * 56)
    if build_rom and rom_path:
        log("Done! ROM built successfully:")
        log(f"  {rom_path}")
    else:
        log("Done! Randomized source saved to:")
        log(f"  {out}")
        log("\nTo compile the ROM, open Terminal in that folder and run:")
        log("  make")
        log(f"\nThe ROM will be: {canonical}")
    log("=" * 56)


# ---------------------------------------------------------------------------
# Randomization worker (runs in background thread)
# ---------------------------------------------------------------------------

def _run_randomizer(data: dict):
    global _job_running, _job_done, _job_error

    def log(msg):
        _append_log(msg)

    try:
        data = _normalize_settings(data)
        src, out, seed = _prep_job(data)

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
            # Accept either numeric dex IDs (sent by the Randomize button) or
            # species constant names (the format stored in saved settings).
            from constants import POKEMON_CONSTANTS as _PC
            def _to_id(x):
                if isinstance(x, int):
                    return x
                if isinstance(x, str) and x.isdigit():
                    return int(x)
                if isinstance(x, str) and x:
                    return _PC.get(x, 0)
                return 0
            s.custom_starters = [_to_id(x) for x in data["customStarters"]]
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

        # ---- Spoiler log ----
        try:
            import spoiler_log
            from constants import POKEMON_DISPLAY_NAME
            sp = spoiler_log.Spoiler("Pokemon Crystal Legacy", seed, POKEMON_DISPLAY_NAME)
            spoiler_log.build_crystal(sp, parser, {
                "starters": rand_starters, "wild": rand_wild, "trainers": rand_trainers,
                "static": rand_static, "field_items": rand_field_items,
                "trades": rand_trades, "held": rand_wild_held_items,
            })
            sp.write(out, log)
        except Exception as _sp_e:
            log(f"[WARN] Spoiler log skipped: {_sp_e}")

        _save_settings_used(data, seed, out, log)

        # ---- Optional ROM build ----
        build_rom = data.get("buildRom", True)
        rom_path = None

        if build_rom:
            _run_make_build(out, log, "gb", _RGBDS_CRYSTAL)
            if starting_bag_items or starting_pc_items or pc_pokemon:
                _warn_new_game_required(log)
            rom_path = _find_rom(out, "pokecrystal.gbc", ".gbc", log)
            rom_path = _save_rom_with_dialog(
                rom_path, f"CrystalLegacy_Randomized_{seed}.gbc", ".gbc", log)

        _log_finish(build_rom, rom_path, out, "pokecrystal.gbc", log)

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
        data = _normalize_settings(data)
        src, out, seed = _prep_job(data)

        log("=" * 56)
        log(f"Yellow Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from parser_yellow import YellowLegacyParser
            from randomizer_engine_yellow import YellowRandomizerEngine, YellowRandomizerSettings
            from writer_yellow import YellowSourceWriter
        except ImportError:
            raise RuntimeError("Yellow Legacy randomizer modules are not available in this build.")

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
        s.starter_mode             = data.get("starterMode", "unchanged")
        s.starter_no_legendaries   = data.get("starterNoLegendaries", True)
        if s.starter_mode == "custom":
            s.custom_starter = data.get("customStarter") or None
        # (The 3 Bulba/Char/Squirtle gifts are now randomized as static
        #  encounters via staticMode — no separate gift-mon setting.)

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

        start_items_enable         = data.get("startingItemsEnable", False)
        s.randomize_start_items    = start_items_enable
        s.start_items              = data.get("startingBagItems", []) if start_items_enable else []
        s.start_pc_items           = data.get("startingPCItems",  []) if start_items_enable else []

        s.easier_evolutions        = data.get("easierEvolutions", False)
        s.full_hm_compat           = data.get("fullHMCompat", False)
        pc_pokemon_enable          = data.get("pcPokemonEnable", False)
        pc_pokemon                 = data.get("pcPokemon", []) if pc_pokemon_enable else []

        s.zero_grinding            = data.get("zeroGrinding", False)
        s.elite4_prep              = data.get("elite4Prep", False)

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
            log("Oak starter (alongside Pikachu):")
            new_starter_const = engine.randomize_starter()

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

        if s.starter_mode != "unchanged" and new_starter_const:
            log("Writing Oak starter...")
            writer.write_oak_starter(new_starter_const, level=5)

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

        if s.zero_grinding:
            log("Zero Grinding: adding Rare Candy to Viridian Mart...")
            writer.write_zero_grinding()

        if s.elite4_prep:
            log("Elite 4 Prep: stocking Indigo Plateau Mart...")
            writer.write_elite4_prep()

        writer.flush_all()

        # ── Spoiler log ──
        try:
            import spoiler_log
            from constants_yellow import POKEMON_DISPLAY_NAME as _YDN
            sp = spoiler_log.Spoiler("Pokemon Yellow Legacy", seed, _YDN)
            spoiler_log.build_yellow(sp, parser, {
                "wild": rand_wild, "trainers": rand_trainers,
                "static": rand_static, "field_items": rand_field_items, "trades": rand_trades,
            })
            sp.write(out, log)
        except Exception as _sp_e:
            log(f"[WARN] Spoiler log skipped: {_sp_e}")

        _save_settings_used(data, seed, out, log)

        # ── Optional ROM build ─────────────────────────────────────────────────
        build_rom = data.get("buildRom", True)
        rom_path  = None

        if build_rom:
            _run_make_build(out, log, "gb", _RGBDS_YELLOW)
            rom_path = _find_rom(out, "pokeyellow.gbc", ".gbc", log)
            rom_path = _save_rom_with_dialog(
                rom_path, f"YellowLegacy_Randomized_{seed}.gbc", ".gbc", log)

        _log_finish(build_rom, rom_path, out, "pokeyellow.gbc", log)

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
        data = _normalize_settings(data)
        src, out, seed = _prep_job(data)

        log("=" * 56)
        log(f"Emerald Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from parser_emerald import EmeraldLegacyParser
            from randomizer_engine_emerald import EmeraldRandomizerEngine, EmeraldRandomizerSettings
            from writer_emerald import EmeraldSourceWriter
        except ImportError:
            raise RuntimeError("Emerald Legacy randomizer modules are not available in this build.")

        # ── Parse ──────────────────────────────────────────────────────────────
        log("\nParsing source files...")
        parser = EmeraldLegacyParser(src, log_fn=log)
        starters_found = parser.parse_all()

        wild_groups = parser.wild_json.get("wild_encounter_groups", [])
        wild_count  = sum(len(g.get("encounters", [])) for g in wild_groups)
        log(f"\nFound: {wild_count} wild encounter area(s), "
            f"{len(parser.trainer_parties)} trainer parties, "
            f"{len(parser.field_items)} field item(s), "
            f"{len(parser.static_encounters)} static encounter(s), "
            f"starters={'yes' if starters_found else 'NOT FOUND'}")

        # ── Build settings ─────────────────────────────────────────────────────
        s = EmeraldRandomizerSettings(seed=seed)

        # General — generation filter (multi-select checkboxes)
        s.include_gen1            = data.get("includeGen1", True)
        s.include_gen2            = data.get("includeGen2", True)
        s.include_gen3            = data.get("includeGen3", True)
        s.remove_time_evolutions  = data.get("removeTimeEvolutions", False)
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
        # Rock smash and fishing always randomized — not user-configurable

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

        # In-game trades
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

        # Shop patches
        s.zero_grinding = data.get("zeroGrinding", False)
        s.elite4_prep   = data.get("elite4Prep", False)

        engine = EmeraldRandomizerEngine(
            settings=s,
            species_consts=parser.species_consts,
            species_bst=parser.species_bst,
            species_types=parser.species_types,
            species_numbers=parser.species_numbers,
            log_fn=log,
        )

        # ── Randomize ──────────────────────────────────────────────────────────
        log("\n--- Randomizing ---")

        rand_wild_json        = parser.wild_json
        rand_parties          = parser.trainer_parties
        rand_starters         = [st.species for st in parser.starters]
        rand_static           = parser.static_encounters
        rand_field_items      = parser.field_items
        rand_trades           = parser.trades
        rand_tmhm_compat      = parser.tmhm_compat
        rand_wild_held_items  = parser.wild_held_items
        rand_abilities        = parser.species_abilities

        if s.full_hm_compat:
            log("TM/HM Compatibility:")
            if parser.tmhm_compat:
                rand_tmhm_compat = engine.apply_full_hm_compat(parser.tmhm_compat)
            else:
                log("  [WARN] No TM/HM learnsets found in source — skipping.")

        if s.wild_mode != "unchanged":
            log("Wild Pokémon:")
            rand_wild_json = engine.randomize_wild(parser.wild_json)

        if s.wild_rand_held_items:
            log("Wild Held Items:")
            if parser.wild_held_items:
                rand_wild_held_items = engine.randomize_wild_held_items(parser.wild_held_items)
            else:
                log("  [WARN] No wild held item slots found in source — skipping.")

        randomize_abilities = data.get("randomizeAbilities", False)
        if randomize_abilities:
            log("Abilities:")
            rand_abilities = engine.randomize_abilities(
                parser.species_abilities, parser.ability_pool)

        if s.trainer_mode != "unchanged":
            log("Trainers:")
            rand_parties = engine.randomize_trainers(parser.trainer_parties)

        if s.starter_mode != "unchanged":
            if starters_found:
                log("Starters:")
                rand_starters = engine.randomize_starters(parser.starters)
            else:
                log("[WARN] Starters not found in source — skipping.")

        # Rival carries starter — applied after trainers + starters are decided.
        # Mutates rand_parties in place (a fresh randomized list when trainers
        # are randomized), so it is written out by the trainer-parties writer.
        if s.trainer_rival_starter and s.trainer_mode != "unchanged":
            log("Rival Carries Starter:")
            engine.apply_rival_starter(
                parser.trainer_parties, rand_parties,
                rand_starters, parser.evolution_to,
            )

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

        if s.trade_mode != "unchanged":
            log("In-Game Trades:")
            if parser.trades:
                rand_trades = engine.randomize_trades(parser.trades)
            else:
                log("  [WARN] No in-game trades found in source — skipping.")

        # ── Write output ───────────────────────────────────────────────────────
        log("\n--- Writing output ---")
        writer = EmeraldSourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()

        if s.wild_mode != "unchanged":
            log("Writing wild encounters...")
            writer.write_wild_encounters(rand_wild_json)

        if s.wild_rand_held_items and parser.wild_held_items:
            log("Writing wild held items...")
            writer.write_wild_held_items(parser.wild_held_items, rand_wild_held_items)

        if randomize_abilities and parser.species_abilities:
            log("Writing abilities...")
            writer.write_abilities(parser.species_abilities, rand_abilities)

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

        if s.trade_mode != "unchanged" and parser.trades:
            log("Writing in-game trades...")
            writer.write_trades(parser.trades, rand_trades)

        if s.full_hm_compat and parser.tmhm_compat:
            log("Writing TM/HM compatibility...")
            writer.write_tmhm_compat(parser.tmhm_compat, rand_tmhm_compat)

        if s.pc_pokemon_enable and s.pc_pokemon:
            log("Writing PC Pokémon...")
            writer.write_pc_pokemon(s.pc_pokemon)

        if s.remove_time_evolutions:
            log("Remove Time-Based Evolutions...")
            writer.write_remove_time_evolutions()

        if s.randomize_start_items and (s.start_items or s.start_pc_items):
            log("Writing starting items...")
            writer.write_starting_items(s.start_items, s.start_pc_items)

        if s.zero_grinding:
            log("Zero Grinding: adding Rare Candy to Oldale Mart...")
            writer.write_zero_grinding()

        if s.elite4_prep:
            log("Elite 4 Prep: stocking Pokémon League Mart...")
            writer.write_elite4_prep()

        writer.flush_all()

        # ── Spoiler log ──
        try:
            import spoiler_log
            from constants_emerald import SPECIES_NAMES as _ESN
            try:
                from item_data import EMERALD_ALL_ITEM_DISPLAY_NAMES as _EIN
            except Exception:
                _EIN = {}
            sp = spoiler_log.Spoiler("Pokemon Emerald Legacy", seed, {**_ESN, **_EIN})
            spoiler_log.build_emerald(sp, parser, {
                "starters": rand_starters, "wild_json": rand_wild_json,
                "trainers": rand_parties, "static": rand_static,
                "field_items": rand_field_items, "trades": rand_trades,
                "held": rand_wild_held_items, "abilities": rand_abilities,
            })
            sp.write(out, log)
        except Exception as _sp_e:
            log(f"[WARN] Spoiler log skipped: {_sp_e}")

        _save_settings_used(data, seed, out, log)

        # ── Optional ROM build ─────────────────────────────────────────────────
        build_rom = data.get("buildRom", True)
        rom_path  = None

        if build_rom:
            _run_make_build(out, log, "gba")
            rom_path = _find_rom(out, "pokeemerald.gba", ".gba", log)
            rom_path = _save_rom_with_dialog(
                rom_path, f"EmeraldLegacy_Randomized_{seed}.gba", ".gba", log)

        _log_finish(build_rom, rom_path, out, "pokeemerald.gba", log)

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
