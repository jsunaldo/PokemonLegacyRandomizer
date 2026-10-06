"""
Pokemon Legacy Randomizer — Web UI entry point

Starts a local HTTP server, opens the UI in the default browser,
and shuts down cleanly when the browser tab closes or the user clicks Quit.

Requires only Python 3.6+ stdlib — no pip installs needed.
"""

import hashlib
import http.server
import json
import os
import re
import socket
import subprocess
import sys
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

APP_VERSION = "1.2.0"

# ---------------------------------------------------------------------------
# Toolchain manager — auto-download RGBDS and devkitARM on first use
# ---------------------------------------------------------------------------

# Cache sits next to main.py so it survives between app launches
_TOOLCHAIN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".toolchain_cache")

# Pinned RGBDS versions (game-specific requirements)
_RGBDS_CRYSTAL = "0.5.2"   # Crystal Legacy requires exactly 0.5.2
_RGBDS_YELLOW  = "0.7.0"   # Yellow Legacy: 0.6.0+ required; 0.8.0+ breaks EQU syntax → pin 0.7.0


def _check_runs(bin_dir: str, version: str):
    """Fail early, with the fix, when the RGBDS binaries can't execute.

    Old RGBDS releases (0.5.2 / 0.7.0) only ship Intel macOS binaries. On an
    Apple Silicon Mac without Rosetta 2 (e.g. after a macOS upgrade) every
    build would otherwise die with a cryptic "make: rgbgfx: Bad CPU type"."""
    exe = os.path.join(bin_dir, "rgbasm")
    try:
        subprocess.run([exe, "--version"], capture_output=True, timeout=20)
    except OSError as exc:
        if getattr(exc, "errno", None) == 86 or "Bad CPU type" in str(exc):
            raise RuntimeError(
                f"RGBDS v{version} (the assembler this game needs) is an Intel app, and "
                "this Mac doesn't have Rosetta 2 installed, so it can't run.\n"
                "Your source folder is untouched; the randomized source was saved to the output folder, only the ROM build failed.\n"
                "Fix (one time): open Terminal, run\n"
                "    softwareupdate --install-rosetta --agree-to-license\n"
                "enter your Mac password when asked, then click Randomize again."
            )
        raise RuntimeError(f"RGBDS v{version} could not be started ({exc}).")


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
        _check_runs(bin_dir, version)
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

    _check_runs(bin_dir, version)
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
_job_info    = {}          # game / seed / phase / rom_path / out_dir of the current job
_shutdown_ev = threading.Event()


def _append_log(msg: str):
    with _state_lock:
        _log_lines.append(msg)


def _set_info(**kw):
    """Record job facts the UI shows (seed, phase, ROM path…)."""
    with _state_lock:
        _job_info.update(kw)


# Files whose presence marks a folder as a previous randomizer output.
_OUTPUT_MARKERS = (".legacy_randomizer_output", "settings_used.json", "spoiler_log.txt")


def _mark_output_dir(out: str):
    """Drop a marker so future runs know this folder is safe to wipe."""
    try:
        with open(os.path.join(out, ".legacy_randomizer_output"), "w", encoding="utf-8") as f:
            f.write("Created by Pokemon Legacy Randomizer. This folder is wiped on every run.\n")
    except OSError:
        pass


def _is_cloud_synced_path(path: str) -> bool:
    """True when the path lives on a cloud-synced mount (Dropbox, iCloud, Drive…).

    Builds there are unreliable: the sync daemon re-stamps mtimes and can
    corrupt large writes mid-build, so we mirror to local disk instead."""
    p = os.path.realpath(path)
    markers = ("/Library/CloudStorage/", "/Dropbox/", "/Mobile Documents/",
               "/Google Drive/", "/OneDrive/", "/Box/")
    return any(m in p + "/" for m in markers)


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

    # Only the page we served may call the API. Any other website open in the
    # same browser must not be able to start a job (which wipes a folder) or
    # stop the server. Browsers send Origin / Sec-Fetch-Site on cross-site
    # requests; a same-origin page never fails this check.
    def _same_origin(self) -> bool:
        host = (self.headers.get("Host") or "").strip()
        origin = self.headers.get("Origin")
        if origin:
            if urlparse(origin).netloc != host:
                return False
        sfs = self.headers.get("Sec-Fetch-Site")
        if sfs and sfs not in ("same-origin", "none"):
            return False
        return True

    def _forbidden(self):
        body = json.dumps({"ok": False, "error": "Cross-origin request refused"}).encode()
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self._same_origin():
            self._forbidden()
            return
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
        elif path == "/api/version":
            self._send_json({"version": APP_VERSION, "platform": sys.platform})
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
        if not self._same_origin():
            self._forbidden()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}

        if path == "/api/randomize":
            self._api_randomize(data)
        elif path == "/api/randomize_yellow":
            self._api_randomize_yellow(data)
        elif path == "/api/randomize_emerald":
            self._api_randomize_emerald(data)
        elif path == "/api/reveal":
            self._api_reveal(data)
        elif path == "/api/fetch_source":
            self._api_fetch_source(data)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _api_fetch_source(self, data: dict):
        """Download (git clone) a game's Legacy source into SOURCES_ROOT."""
        global _job_running, _job_done, _job_error, _log_lines
        game = str(data.get("game", "")).lower()
        if game not in _SOURCE_REPOS:
            self._send_json({"ok": False, "error": f"Unknown game {game!r}"})
            return
        with _state_lock:
            if _job_running:
                self._send_json({"ok": False, "error": "Already running"})
                return
            _job_running = True
            _job_done    = False
            _job_error   = None
            _log_lines   = []
            _job_info.clear()
            _job_info.update({"game": game, "phase": "starting", "kind": "fetch"})
        self._send_json({"ok": True})
        threading.Thread(target=_run_fetch_source, args=(game,), daemon=True).start()

    def _api_reveal(self, data: dict):
        """Open the last job's ROM (selected in Finder) or output folder.

        Only paths the server itself produced can be opened — the request
        just says which one."""
        what = data.get("what", "rom")
        with _state_lock:
            target = _job_info.get("rom_path" if what == "rom" else "out_dir")
        if not target or not os.path.exists(target):
            self._send_json({"ok": False, "error": "Nothing to show yet."})
            return
        try:
            if sys.platform == "darwin":
                cmd = ["/usr/bin/open", "-R", target] if os.path.isfile(target) else ["/usr/bin/open", target]
            elif sys.platform.startswith("win"):
                cmd = ["explorer", "/select,", target] if os.path.isfile(target) else ["explorer", target]
            else:
                cmd = ["xdg-open", os.path.dirname(target) if os.path.isfile(target) else target]
            subprocess.Popen(cmd)
            self._send_json({"ok": True})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)})

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
            payload = {
                "running": _job_running,
                "done":    _job_done,
                "error":   _job_error,
                "version": APP_VERSION,
                "platform": sys.platform,
            }
            payload.update(_job_info)
        self._send_json(payload)

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
            _job_info.clear()
            _job_info.update({"game": "crystal", "phase": "starting"})

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
            _job_info.clear()
            _job_info.update({"game": "yellow", "phase": "starting"})

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
            _job_info.clear()
            _job_info.update({"game": "emerald", "phase": "starting"})

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
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


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


# Where "Get source" clones the Legacy repos (outside cloud-synced folders).
SOURCES_ROOT = os.path.join(os.path.expanduser("~"), "Pokemon Legacy Sources")
_SOURCE_REPOS = {
    "crystal": ("Pokemon_Crystal_Legacy", "https://github.com/cRz-Shadows/Pokemon_Crystal_Legacy.git"),
    "yellow":  ("Pokemon_Yellow_Legacy",  "https://github.com/cRz-Shadows/Pokemon_Yellow_Legacy.git"),
    "emerald": ("Pokemon_Emerald_Legacy", "https://github.com/cRz-Shadows/Pokemon_Emerald_Legacy.git"),
}
_ROM_EXTS = (".gb", ".gbc", ".gba", ".ips", ".bps", ".ups", ".sav", ".srm")


def _run_fetch_source(game: str):
    """Background job: make sure the Legacy source repo for `game` exists
    under SOURCES_ROOT (git clone --depth=1), streaming progress to the log.
    Records the folder in _job_info['source_dir'] so the UI can fill the
    Source Directory field."""
    global _job_running, _job_done, _job_error
    import shutil as _shutil

    def log(msg):
        _append_log(msg)

    try:
        name, url = _SOURCE_REPOS[game]
        title, markers = _SOURCE_FINGERPRINTS[game]
        dest = os.path.join(SOURCES_ROOT, name)
        _set_info(phase="fetching", kind="fetch", game=game)

        if os.path.isdir(dest) and _has_markers(dest, markers):
            log(f"{title} source is already downloaded:\n  {dest}")
        else:
            path = os.pathsep.join(["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
                                    os.environ.get("PATH", "")])
            git = _shutil.which("git", path=path)
            if not git:
                raise RuntimeError(
                    "git was not found. Install Xcode Command Line Tools "
                    "(xcode-select --install) and try again, or clone the repo "
                    f"yourself:  git clone {url}")
            os.makedirs(SOURCES_ROOT, exist_ok=True)
            if os.path.isdir(dest):
                log("Removing an incomplete earlier download…")
                _shutil.rmtree(dest, ignore_errors=True)
            log(f"Downloading {title} source from GitHub")
            log(f"  {url}")
            log(f"  → {dest}")
            log("  (one-time download; Emerald is a few hundred MB, so this can take a few minutes)\n")
            proc = subprocess.Popen(
                [git, "clone", "--depth=1", "--progress", url, dest],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                env=dict(os.environ, PATH=path, GIT_TERMINAL_PROMPT="0"),
            )
            # git redraws progress with \r; log each stage once (plus its final
            # "done" line) instead of every percentage tick.
            buf, last_stage = "", None
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                if ch in "\r\n":
                    line = buf.strip()
                    buf = ""
                    if not line:
                        continue
                    stage = line.split(":")[0]
                    if stage == last_stage and not line.endswith("done."):
                        continue
                    last_stage = stage
                    log("  " + line)
                else:
                    buf += ch
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(
                    "git clone failed (see the log above). Check your internet "
                    f"connection, or clone it yourself:  git clone {url}")
            _validate_source(game, dest)
            log(f"\nDownloaded {title} source.")

        _set_info(phase="done", source_dir=dest,
                  suggested_out=dest + "_randomized")
        log(f"\nSource Directory set to:\n  {dest}")
        with _state_lock:
            _job_done = True

    except Exception as exc:
        import traceback
        log(f"\n[ERROR] {exc}")
        if not isinstance(exc, (ValueError, RuntimeError)):
            log(traceback.format_exc())
        with _state_lock:
            _job_error = str(exc)
            _job_done  = True
            _job_info["phase"] = "error"

    finally:
        with _state_lock:
            _job_running = False


# Per-game source fingerprints: files/dirs each parser fundamentally needs.
# All markers must exist (Emerald and FireRed share wild_encounters.json,
# so each also requires a hometown map dir unique to its game).
_SOURCE_FINGERPRINTS = {
    "crystal": ("Crystal Legacy", [os.path.join("data", "wild", "johto_grass.asm")]),
    "yellow":  ("Yellow Legacy",  [os.path.join("data", "wild", "grass_water.asm")]),
    "emerald": ("Emerald Legacy", [os.path.join("src", "data", "wild_encounters.json"),
                                   os.path.join("data", "maps", "LittlerootTown")]),
}


def _has_markers(root: str, markers: list) -> bool:
    return all(os.path.exists(os.path.join(root, m)) for m in markers)


def _validate_source(game: str, src: str):
    """Check the source dir actually contains this game's source tree.

    Raises ValueError with a helpful message when the folder is a different
    game's source, a parent folder of the real repo, or not a source at all."""
    name, markers = _SOURCE_FINGERPRINTS[game]
    if _has_markers(src, markers):
        return

    # Is it one of the OTHER games' sources?
    for other, (other_name, other_markers) in _SOURCE_FINGERPRINTS.items():
        if other != game and _has_markers(src, other_markers):
            raise ValueError(
                f"The Source Directory looks like {other_name} source, but this "
                f"is the {name} randomizer. Pick the {name} repo folder "
                f"(or switch to the {other_name} randomizer)."
            )

    # A folder of ROMs / patches — the most common mix-up.
    try:
        entries = os.listdir(src)
    except OSError:
        entries = []
    roms = [e for e in entries if e.lower().endswith(_ROM_EXTS)]
    if roms and not os.path.exists(os.path.join(src, "Makefile")):
        repo_url = _SOURCE_REPOS[game][1]
        raise ValueError(
            f"The Source Directory contains ROM files (e.g. {roms[0]}) but no source "
            f"code:\n  {src}\n"
            f"The randomizer doesn't patch ROMs — it patches the {name} SOURCE CODE and "
            "compiles a new ROM. Click “Get source” next to the Source Directory field "
            f"to download it, or run:  git clone {repo_url}"
        )

    # Is the real repo one level down (user picked the parent folder)?
    try:
        for entry in sorted(os.listdir(src)):
            cand = os.path.join(src, entry)
            if os.path.isdir(cand) and _has_markers(cand, markers):
                raise ValueError(
                    f"The Source Directory doesn't contain {name} source, but the "
                    f"folder inside it does — set the Source Directory to:\n  {cand}"
                )
    except OSError:
        pass

    raise ValueError(
        f"The Source Directory doesn't look like {name} source (missing "
        f"{markers[0]}):\n  {src}\n"
        "It should be the cloned repo root — the folder that contains the Makefile. "
        "Click “Get source” next to the Source Directory field to download it."
    )


def _check_output_dir_safe(out: str):
    """Refuse to wipe a folder that isn't ours.

    The output folder is deleted and re-created on every run. That is fine
    for an empty folder or one this randomizer created earlier (it carries a
    marker file), but a stray Documents/ or home folder must never be wiped."""
    if not os.path.exists(out):
        return
    if not os.path.isdir(out):
        raise ValueError(f"The Output path exists but is not a folder:\n  {out}")
    try:
        entries = [e for e in os.listdir(out) if e not in (".DS_Store", "Thumbs.db", "desktop.ini")]
    except OSError as exc:
        raise ValueError(f"Cannot read the Output Directory: {exc}")
    if not entries:
        return
    if any(m in entries for m in _OUTPUT_MARKERS):
        return
    raise ValueError(
        "The Output Directory is not empty and doesn't look like a folder this "
        "randomizer created — everything inside it would be deleted:\n"
        f"  {out}\n"
        "Choose a new or empty folder (or a previous randomizer output folder)."
    )


def _prep_job(data: dict):
    """Validate source/output dirs and resolve the seed.

    Returns (src, out, seed). Raises ValueError on bad input."""
    import random as _random

    src = os.path.expanduser(str(data.get("sourceDir", "") or "").strip())
    out = os.path.expanduser(str(data.get("outputDir", "") or "").strip())
    seed_raw = data.get("seed", "")

    if not src or not os.path.isdir(src):
        raise ValueError(f"Source directory not found: {src!r}")
    if not out:
        raise ValueError("Output directory is required.")

    src_real = os.path.realpath(src)
    out_real = os.path.realpath(out)
    if src_real == out_real:
        raise ValueError("Source and Output directories must be different.")
    if out_real.startswith(src_real + os.sep):
        raise ValueError(
            "The Output Directory must not be inside the Source Directory "
            "(the source tree is copied into the output folder)."
        )
    if src_real.startswith(out_real + os.sep):
        raise ValueError(
            "The Source Directory must not be inside the Output Directory "
            "(the output folder is wiped on every run — your source would be deleted)."
        )
    _check_output_dir_safe(out)

    if seed_raw is None or str(seed_raw).strip() == "":
        seed = _random.randint(0, 999999)
    else:
        try:
            seed = int(str(seed_raw).strip())
        except (ValueError, TypeError):
            raise ValueError(
                f"Seed must be a whole number (got {str(seed_raw).strip()!r}). "
                "Leave it blank or click 🎲 for a random seed."
            )
    _set_info(seed=seed, out_dir=out)
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


def _run_make_build(out: str, log, kind: str, rgbds_version=None,
                    make_args=None, local_mirror_name=None, rom_name=None,
                    rom_ext=None):
    """Run 'make' in the output tree with the right toolchain on PATH.

    kind: "gb"         — RGBDS (needs rgbds_version)
          "gba"        — devkitARM + agbcc (Emerald-style MODERN=0)
          "gba_modern" — arm-none-eabi-gcc from PATH ('make modern')

    local_mirror_name: when set, the output tree is mirrored to a local
    temp dir and built THERE, then the ROM (rom_name, or every *rom_ext
    file) is copied back. This happens automatically when the output
    folder lives on a cloud-synced mount (Dropbox/iCloud/Drive): builds
    there corrupt large writes and re-stamp mtimes.

    make runs in parallel first (-jN); if that fails the build is retried
    serially once, since a few Makefiles have latent -j race conditions.

    Streams build output to the log; raises RuntimeError on failure."""
    import shutil as _shutil

    _set_info(phase="building")
    log("\n" + "=" * 56)
    log("Building ROM with 'make'...")
    log("=" * 56)

    if local_mirror_name is None and _is_cloud_synced_path(out):
        local_mirror_name = "plr_build_" + hashlib.md5(
            os.path.realpath(out).encode("utf-8")).hexdigest()[:10]
        log("Output folder is on a cloud-synced drive — building in a local "
            "temp folder and copying the ROM back (sync daemons corrupt builds).")

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
    elif kind == "gba_modern":
        if not _shutil.which("arm-none-eabi-gcc", path=env["PATH"]):
            raise RuntimeError(
                "arm-none-eabi-gcc not found. FireRed builds with the modern "
                "toolchain:  brew install --cask gcc-arm-embedded  (or "
                "arm-none-eabi-gcc from devkitPro) and make sure it is on PATH."
            )
        log("Using arm-none-eabi-gcc from PATH (make modern)")
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

    # Cloud-mount workaround: mirror to local disk and build there
    build_dir = out
    if local_mirror_name:
        import tempfile as _tempfile
        build_dir = os.path.join(_tempfile.gettempdir(), local_mirror_name)
        log(f"Mirroring source to local build dir (cloud-sync-safe): {build_dir}")
        rsync = _shutil.which("rsync", path=env["PATH"])
        if rsync:
            r = subprocess.run(
                [rsync, "-a", "--delete", "--exclude", ".git",
                 out.rstrip("/") + "/", build_dir + "/"],
                capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"rsync to local build dir failed: {r.stderr[:300]}")
        else:
            if os.path.isdir(build_dir):
                _shutil.rmtree(build_dir, ignore_errors=True)
            _shutil.copytree(out, build_dir, ignore=_shutil.ignore_patterns(".git"))

    def _run_make(extra):
        proc = subprocess.Popen(
            [make_exe] + list(extra) + (make_args or []),
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        captured = []
        for line in proc.stdout:
            line = line.rstrip()
            captured.append(line)
            log(line)
        proc.wait()
        return proc.returncode, captured

    jobs = max(1, min(8, (os.cpu_count() or 2)))
    log(f"Running: make -j{jobs}")
    code, captured = _run_make([f"-j{jobs}"])
    if code != 0 and jobs > 1:
        log("\nParallel build failed — retrying serially (make -j1) in case "
            "the Makefile has a parallel-build race...")
        code, captured = _run_make(["-j1"])

    if code != 0:
        raise RuntimeError(_summarize_build_failure(captured, code))

    # Mirror build: bring the ROM(s) back to the user's output directory
    if local_mirror_name:
        copied = 0
        names = [rom_name] if rom_name and os.path.isfile(os.path.join(build_dir, rom_name)) else []
        if rom_ext:
            names += [f for f in os.listdir(build_dir)
                      if f.lower().endswith(rom_ext) and f not in names]
        for name in names:
            _shutil.copy2(os.path.join(build_dir, name), os.path.join(out, name))
            copied += 1
        log(f"Copied {copied} ROM file(s) back to the output directory")


# Patterns that mark a real compiler/assembler error line in a make log.
_BUILD_ERR_RE = re.compile(
    r"(^|\s)(error|fatal error)[: ]|^ERROR:|undefined (symbol|reference)|"
    r"syntax error|No such file or directory", re.IGNORECASE)


def _summarize_build_failure(lines: list, code: int) -> str:
    """Pull the first real compiler error(s) out of a failed make log so the
    user sees the cause directly instead of 'check the log above'."""
    hits = []
    for i, ln in enumerate(lines):
        if _BUILD_ERR_RE.search(ln):
            hits.append(ln.strip())
            # RGBDS prints the detail on the line after "ERROR: file(123):"
            if ln.strip().endswith(":") and i + 1 < len(lines) and lines[i + 1].strip():
                hits.append("    " + lines[i + 1].strip())
        if len(hits) >= 4:
            break
    msg = f"Build failed (make exit code {code})."
    if hits:
        msg += " First error:\n" + "\n".join(hits[:4])
    else:
        tail = [l for l in lines[-6:] if l.strip()]
        if tail:
            msg += " Last output:\n" + "\n".join(tail)
    return msg


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
        rom_path = max(rom_files, key=os.path.getmtime)  # newest build wins
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
    _set_info(phase="done", rom_path=rom_path, out_dir=out, built=bool(build_rom and rom_path))
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
        _validate_source("crystal", src)

        log("=" * 56)
        log(f"Crystal Legacy Randomizer  |  Seed: {seed}")
        log("=" * 56)

        # -- import here so path is already set --
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from parser import CrystalLegacyParser
        from randomizer_engine import RandomizerEngine, RandomizerSettings
        from writer import SourceWriter

        # Parse
        _set_info(phase="parsing")
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

        # Starting items — list of {const, qty} dicts; empty list = unchanged.
        # Older settings files have no enable flag, so a missing flag means on.
        if data.get("startingItemsEnable", True):
            starting_bag_items = data.get("startingBagItems", []) or []
            starting_pc_items  = data.get("startingPCItems",  []) or []
        else:
            starting_bag_items, starting_pc_items = [], []

        # PC Pokémon — list of mon dicts; empty list = unchanged
        pc_pokemon = data.get("pcPokemon", []) if data.get("pcPokemonEnable", False) else []

        engine = RandomizerEngine(s, log_fn=log)

        _set_info(phase="randomizing")
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
            # Always pass the evolution maps — needed for rival starter AND force-evolved
            s.rival_level_evo_map = parser.level_evo_map
            s.full_evo_map        = parser.full_evo_map
            if s.trainer_rival_starter:
                from constants import POKEMON_CONSTANTS as _PC, STARTER_CONSTANTS as _SC
                # rival_starter_ids follows STARTER_CONSTANTS order (the slot each
                # randomized starter occupies), so unchanged starters must use
                # that same order — not dex order.
                if starters_found and s.starter_mode != "unchanged":
                    s.rival_starter_ids = [_PC.get(sl.species_const, 0) for sl in rand_starters]
                elif starters_found:
                    s.rival_starter_ids = [_PC.get(sl.species_const, 0) for sl in parser.starters]
                else:
                    s.rival_starter_ids = [_PC[c] for c in _SC]
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
                from key_items import check_field_items
                check_field_items("crystal", src, parser.field_items, rand_field_items,
                                  lambda e: e.item_const)
            else:
                log("  [WARN] No field items found in source — skipping.")

        log("\n--- Writing output ---")
        _set_info(phase="writing")
        writer = SourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()
        _mark_output_dir(out)

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
            _run_make_build(out, log, "gb", _RGBDS_CRYSTAL,
                            rom_name="pokecrystal.gbc", rom_ext=".gbc")
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
        if not isinstance(exc, ValueError):      # ValueError = user-input problem, no traceback noise
            log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True
            _job_info["phase"] = "error"

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
        _validate_source("yellow", src)

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
        _set_info(phase="parsing")
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
        s.trainer_similar_strength = data.get("trainerSimilarStrength", False)
        s.trainer_weight_types     = data.get("trainerWeightTypes", False)
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
        _set_info(phase="randomizing")
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
            if parser.evolutions:
                engine.set_evolutions(parser.evolutions)
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
                from key_items import check_field_items
                check_field_items("yellow", src, parser.field_items, rand_field_items,
                                  lambda e: e.item_const)
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
        _set_info(phase="writing")
        writer = YellowSourceWriter(src, out, log_fn=log)
        writer.prepare_output_directory()
        _mark_output_dir(out)

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
            _run_make_build(out, log, "gb", _RGBDS_YELLOW,
                            rom_name="pokeyellow.gbc", rom_ext=".gbc")
            if (s.randomize_start_items and (s.start_items or s.start_pc_items)) or pc_pokemon:
                _warn_new_game_required(log)
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
        if not isinstance(exc, ValueError):      # ValueError = user-input problem, no traceback noise
            log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True
            _job_info["phase"] = "error"

    finally:
        with _state_lock:
            global _job_running
            _job_running = False


# ---------------------------------------------------------------------------
# Emerald Legacy randomization worker (runs in background thread)
# ---------------------------------------------------------------------------

# Config for the parameterized GBA pipeline handler.
_GBA_GAMES = {
    "emerald": dict(
        title="Emerald Legacy", spoiler_title="Pokemon Emerald Legacy",
        parser_mod="parser_emerald", parser_cls="EmeraldLegacyParser",
        engine_mod="randomizer_engine_emerald", engine_cls="EmeraldRandomizerEngine",
        settings_cls="EmeraldRandomizerSettings",
        writer_mod="writer_emerald", writer_cls="EmeraldSourceWriter",
        item_names="EMERALD_ALL_ITEM_DISPLAY_NAMES",
        build_kind="gba", make_args=None, mirror=None,
        rom="pokeemerald.gba", stem="EmeraldLegacy",
    ),
}


def _run_randomizer_gba(data: dict, game: str):
    global _job_running, _job_done, _job_error

    def log(msg):
        _append_log(msg)

    try:
        cfg = _GBA_GAMES[game]
        data = _normalize_settings(data)
        src, out, seed = _prep_job(data)
        _validate_source(game, src)

        log("=" * 56)
        log(f"{cfg['title']} Randomizer  |  Seed: {seed}")
        log("=" * 56)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import importlib
            _pmod = importlib.import_module(cfg["parser_mod"])
            _emod = importlib.import_module(cfg["engine_mod"])
            _wmod = importlib.import_module(cfg["writer_mod"])
            ParserCls   = getattr(_pmod, cfg["parser_cls"])
            EngineCls   = getattr(_emod, cfg["engine_cls"])
            SettingsCls = getattr(_emod, cfg["settings_cls"])
            WriterCls   = getattr(_wmod, cfg["writer_cls"])
        except ImportError:
            raise RuntimeError(f"{cfg['title']} randomizer modules are not available in this build.")

        # ── Parse ──────────────────────────────────────────────────────────────
        _set_info(phase="parsing")
        log("\nParsing source files...")
        parser = ParserCls(src, log_fn=log)
        starters_found = parser.parse_all()

        wild_groups = parser.wild_json.get("wild_encounter_groups", [])
        wild_count  = sum(len(g.get("encounters", [])) for g in wild_groups)
        log(f"\nFound: {wild_count} wild encounter area(s), "
            f"{len(parser.trainer_parties)} trainer parties, "
            f"{len(parser.field_items)} field item(s), "
            f"{len(parser.static_encounters)} static encounter(s), "
            f"starters={'yes' if starters_found else 'NOT FOUND'}")

        # ── Build settings ─────────────────────────────────────────────────────
        s = SettingsCls(seed=seed)

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

        engine = EngineCls(
            settings=s,
            species_consts=parser.species_consts,
            species_bst=parser.species_bst,
            species_types=parser.species_types,
            species_numbers=parser.species_numbers,
            log_fn=log,
        )
        if hasattr(engine, "set_evolution_graph"):
            engine.set_evolution_graph(getattr(parser, "evolution_graph", {}))

        # ── Randomize ──────────────────────────────────────────────────────────
        _set_info(phase="randomizing")
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
                from key_items import check_field_items
                check_field_items(game, src, parser.field_items, rand_field_items,
                                  lambda e: e.item_const)
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
        _set_info(phase="writing")
        writer = WriterCls(src, out, log_fn=log)
        writer.prepare_output_directory()
        _mark_output_dir(out)

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
                import item_data as _idata
                _EIN = getattr(_idata, cfg["item_names"], {})
            except Exception:
                _EIN = {}
            sp = spoiler_log.Spoiler(cfg["spoiler_title"], seed, {**_ESN, **_EIN})
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
            _run_make_build(out, log, cfg["build_kind"], make_args=cfg["make_args"],
                            local_mirror_name=cfg["mirror"], rom_name=cfg["rom"],
                            rom_ext=".gba")
            if (s.randomize_start_items and (s.start_items or s.start_pc_items)) or \
                    (s.pc_pokemon_enable and s.pc_pokemon):
                _warn_new_game_required(log)
            rom_path = _find_rom(out, cfg["rom"], ".gba", log)
            rom_path = _save_rom_with_dialog(
                rom_path, f"{cfg['stem']}_Randomized_{seed}.gba", ".gba", log)

        _log_finish(build_rom, rom_path, out, cfg["rom"], log)

        with _state_lock:
            global _job_done
            _job_done = True

    except Exception as exc:
        import traceback
        log(f"\n[ERROR] {exc}")
        if not isinstance(exc, ValueError):      # ValueError = user-input problem, no traceback noise
            log(traceback.format_exc())
        with _state_lock:
            global _job_error
            _job_error = str(exc)
            _job_done  = True
            _job_info["phase"] = "error"

    finally:
        with _state_lock:
            global _job_running
            _job_running = False



def _run_randomizer_emerald(data: dict):
    _run_randomizer_gba(data, "emerald")


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------

def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    # Optional CLI flags:  --port N   (fixed port instead of a free one)
    #                      --no-browser (don't open the browser automatically)
    args = sys.argv[1:]
    port = None
    open_in_browser = "--no-browser" not in args
    if "--port" in args:
        try:
            port = int(args[args.index("--port") + 1])
        except (IndexError, ValueError):
            print("Usage: python3 main.py [--port N] [--no-browser]")
            sys.exit(2)
    if port is None:
        port = int(os.environ.get("PLR_PORT") or 0) or find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    print(f"Pokemon Legacy Randomizer v{APP_VERSION} running at {url}", flush=True)

    # Small delay then open browser.
    # Use macOS 'open' directly — more reliable than webbrowser when launched
    # from Finder (no shell profile, no DISPLAY variable, etc.)
    def open_browser():
        import time; time.sleep(0.6)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["/usr/bin/open", url])
            else:
                webbrowser.open(url)
        except Exception:
            try:
                webbrowser.open(url)
            except Exception:
                pass
    if open_in_browser:
        threading.Thread(target=open_browser, daemon=True).start()

    # Block until the /api/quit endpoint fires the event (or Ctrl-C)
    try:
        _shutdown_ev.wait()
    except KeyboardInterrupt:
        pass
    server.shutdown()
    print("Server stopped.")


if __name__ == "__main__":
    main()
