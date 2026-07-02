# Pokémon Legacy Randomizer

A randomizer for **SmithPlaysPokemon's Legacy ROM hacks** — **Yellow Legacy**, **Crystal Legacy**, and **Emerald Legacy** — that runs as a local web app. Pick a game, choose what to randomize (starters, wild Pokémon, trainers, items, trades, evolutions, and more), and build a ready-to-play ROM in one click.

> ⚠️ You must supply your own legally-obtained copy of each Legacy ROM hack's **source code**. This tool patches that source and compiles it — it does not contain or distribute any ROMs.

---

## Supported games

| Game | Console | Source repo |
|------|---------|-------------|
| **Yellow Legacy** | Game Boy | <https://github.com/cRz-Shadows/Pokemon_Yellow_Legacy> |
| **Crystal Legacy** | Game Boy Color | <https://github.com/cRz-Shadows/Pokemon_Crystal_Legacy> |
| **Emerald Legacy** | Game Boy Advance | <https://github.com/cRz-Shadows/Pokemon_Emerald_Legacy> |

---

## Requirements

You need two things for whichever game(s) you want to randomize:

### 1. The game's source code
Clone the matching repo and make sure it builds cleanly **on its own first**:
```bash
git clone <one of the repos above>
cd <repo>
make
```
If `make` produces a `.gb` / `.gbc` / `.gba` file, you're ready.

### 2. The build toolchain
- **Yellow & Crystal (GB/GBC):** [RGBDS](https://rgbds.gbdev.io/) — `brew install rgbds`
  - Crystal Legacy expects **RGBDS 0.5.2**; Yellow Legacy expects **0.7.0**.
- **Emerald (GBA):** [devkitARM](https://devkitpro.org/wiki/Getting_Started) + `agbcc` — the app can install these automatically on first build.

GNU Make is required for all three (comes with Xcode Command Line Tools: `xcode-select --install`).

---

## Installation

1. Download the latest **PokemonLegacyRandomizer.zip** from the [Releases](../../releases/latest) page.
2. Unzip it — you'll get `PokemonLegacyRandomizer.app`.
3. **First launch only:** right-click the app → **Open** → click **Open** in the dialog (one-time macOS Gatekeeper bypass for unsigned apps).
4. After that, double-clicking works normally.

---

### Windows / Linux (experimental)

The packaged `.app` and toolchain auto-install are macOS-only, but the app itself is a
local web server and runs anywhere Python 3 does:

```bash
git clone https://github.com/jsunaldo/PokemonLegacyRandomizer.git
cd PokemonLegacyRandomizer
python3 main.py
```

You must install the build toolchain yourself and have it on `PATH`:
[RGBDS](https://rgbds.gbdev.io/install) for Yellow/Crystal, and
[devkitARM](https://devkitpro.org/wiki/Getting_Started) + [agbcc](https://github.com/pret/agbcc)
for Emerald. The native folder picker and save dialog are replaced by typing paths
directly; the built ROM stays in your output directory.

---

## Usage

1. Launch the app — a small status window appears and your browser opens to the launcher.
2. Pick a game (Yellow / Crystal / Emerald).
3. Set your **Source Directory** (the repo root — the folder containing the `Makefile`) and an **Output Directory** (a new, empty folder for the randomized copy). *The app remembers these between runs.*
4. Configure options across the tabs, set or roll a **Seed**, and click **Randomize**.
5. When it finishes, your ROM is in the Output Directory — load it in any compatible emulator (mGBA, BGB, etc.).

Each run also writes two helper files into the output folder:
- **`spoiler_log.txt`** — what every Pokémon/item/trainer was changed into.
- **`settings_used.json`** — the exact seed + settings, so any run is fully reproducible (and perfect to attach to a bug report).

---

## What can be randomized

| Tab | Options |
|-----|---------|
| **General** | Seed, generation filter, easier evolutions, full HM/TM compatibility, remove special-condition evolutions |
| **Starters** | Unchanged / custom / random / random two-stage |
| **Wild** | Random, area 1-to-1, global 1-to-1, catch-'em-all, type-themed; legendary filter; held-item randomization |
| **Trainers** | Random / even-distribution / type-themed; similar-strength; rival carries a starter; force fully evolved |
| **Static / Gift** | Legendaries and gift Pokémon (unchanged / swap / random / similar strength) |
| **In-Game Trades** | Given/requested species, nicknames, OT names, IVs, held items |
| **Items** | Field-item randomization; custom starting bag/PC items (any item, incl. TMs/HMs/berries); shop patches |
| **Gifts / PC** | Add custom Pokémon and items to the player (with a duplicate-row shortcut) |

*Exact options vary slightly per game.*

---

## Sharing & reproducing runs

Every randomization is fully determined by its **seed + settings**. Use the 📋 button to copy the seed, **Save Settings** to export your configuration, or just hand someone the `settings_used.json` from your output folder — same inputs always produce the same ROM.

---

## Reporting bugs & requesting features

Found a problem or have an idea? Please open an issue on GitHub:

**→ [Open an issue](https://github.com/jsunaldo/PokemonLegacyRandomizer/issues/new/choose)**

To make a bug easy to fix, include:
- **Which game** (Yellow / Crystal / Emerald) and the **seed** (📋 copy button next to it)
- Your **`settings_used.json`** (saved next to your ROM) — it reproduces your exact run. For in-game issues, the `spoiler_log.txt` helps too.
- The **error output / build log** if a build failed, plus your **macOS version**

You can also click **🐛 Report a Bug** inside the app (each randomizer's *How to Use* tab, or the launcher footer).

Please search [existing issues](https://github.com/jsunaldo/PokemonLegacyRandomizer/issues) first to avoid duplicates.

---

## Support development ⚡

If you enjoy the randomizer, tips are appreciated (Bitcoin Lightning): **`salmoncobra1@primal.net`** — also available on the **Donate** tab in the app.

---

## Troubleshooting

**"make failed" / compile error**
- Verify the toolchain is installed (`rgbasm --version` for GB/GBC; devkitARM for GBA).
- Make sure the game's source builds cleanly on its own *before* randomizing.

**App won't open / "damaged app" warning**
- Right-click → **Open** instead of double-clicking (one-time Gatekeeper bypass), or run: `xattr -cr PokemonLegacyRandomizer.app`

**0 wild encounters / starters found**
- Make sure the Source Directory points to the repo root — the folder that contains the `Makefile`.

---

## Building from source

```bash
git clone https://github.com/jsunaldo/PokemonLegacyRandomizer.git
cd PokemonLegacyRandomizer
pip3 install pyinstaller
bash build.sh
```

The built app lands in `dist/PokemonLegacyRandomizer.app`, with a zippable `PokemonLegacyRandomizer.zip` release asset.

---

## Credits

- **Legacy ROM hacks** by [SmithPlaysPokemon](https://www.youtube.com/@smithplayspokemon) and contributors (repos hosted by [cRz-Shadows](https://github.com/cRz-Shadows)).
- Built on the [pret](https://github.com/pret) disassemblies (pokeyellow / pokecrystal / pokeemerald).

---

## License

Released under the [MIT License](LICENSE) — free to use, modify, and share.

This is a fan-made tool that patches **your own** copy of each Legacy ROM hack's
source code. It contains no game ROMs or copyrighted game assets.
