# Crystal Legacy Randomizer

A randomizer for [Pokémon Crystal Legacy](https://github.com/cRz-Shadows/Pokemon_Crystal_Legacy) that runs as a local web UI. Randomize starters, wild Pokémon, trainers, items, trades, evolutions, and more — then build a ready-to-play ROM in one click.

---

## Requirements

Before using the randomizer you need two things installed on your Mac:

### 1. Crystal Legacy source code
Clone the Crystal Legacy repo and make sure it builds cleanly on its own first:
```bash
git clone https://github.com/cRz-Shadows/Pokemon_Crystal_Legacy.git
cd Pokemon_Crystal_Legacy
make
```
If `make` produces a `.gbc` file, you're good.

### 2. RGBDS (Game Boy assembler toolchain)
The randomizer calls `make` to compile the ROM after patching the source. Install RGBDS via Homebrew:
```bash
brew install rgbds
```
Or download directly from [rgbds.gbdev.io](https://rgbds.gbdev.io/).

---

## Installation

1. Download the latest **CrystalLegacyRandomizer.zip** from the [Releases](../../releases/latest) page
2. Unzip it — you'll get `CrystalLegacyRandomizer.app`
3. **First launch only:** right-click the app → **Open** → click Open in the dialog
   *(macOS Gatekeeper blocks unsigned apps by default; this bypasses it once)*
4. After that, double-clicking works normally

---

## Usage

1. Launch the app — a small status window appears and your browser opens automatically
2. Under **General → Directories**, set:
   - **Source Directory** — the root of your Crystal Legacy repo (the folder containing `Makefile`)
   - **Output Directory** — where the randomized copy of the source will be written (a new folder, e.g. `crystal_legacy_randomized`)
3. Configure your options across the tabs
4. Click **Randomize & Build ROM**
5. When it finishes, find your `.gbc` ROM in the Output Directory — load it in any GBC emulator (mGBA, BGB, etc.)

> **Tip:** The Output Directory is a full copy of the source with your changes applied. You can inspect the patched ASM files or re-run `make` manually.

---

## What Can Be Randomized

| Tab | Options |
|-----|---------|
| **General** | Seed, generation filter (Gen 1 / Gen 2 / all), easier evolutions, full HM compatibility |
| **Starters** | Unchanged / custom picks / fully random, held item randomization |
| **Wild** | Random, area 1-to-1, global 1-to-1; legendary filter; time-based encounters; held items |
| **Trainers** | Random parties; similar-strength matching; rival carries a starter; force fully evolved |
| **Trades** | In-game trade species, nicknames, OT names, IVs, held items |
| **Static** | Legendary and gift Pokémon (unchanged / swap / random / similar strength) |
| **Items** | Field item randomization; custom starting bag & PC items; shop patches (see below) |
| **Randomize** | Seed entry, save/load settings presets, one-click build |

### Shop Patches (Items tab)
- **Zero Grinding** — adds Rare Candy to the Cherrygrove Mart for $10, available from the very start
- **Elite 4 Prep** — stocks the Indigo Plateau Mart with Rare Candy, Full Restore, Max Elixir, and Max Revive for $10 each

---

## Sharing Seeds

Every randomization is fully determined by its **seed**. Use **Save Settings** to export a JSON of your full configuration — share the seed + settings file and anyone can reproduce the exact same ROM.

---

## Troubleshooting

**"make failed" / compile error**
- Verify RGBDS is installed: `rgbasm --version`
- Make sure your Crystal Legacy source builds cleanly on its own before randomizing

**App won't open / "damaged app" warning**
- Right-click → Open instead of double-clicking (one-time Gatekeeper bypass)
- Or run in Terminal: `xattr -cr CrystalLegacyRandomizer.app`

**0 wild encounters or starters found**
- Make sure Source Directory points to the repo root — the folder that contains `Makefile`

---

## Building from Source

```bash
git clone <this repo>
cd crystal_legacy_randomizer
pip3 install pyinstaller
bash build.sh
```

The built app lands in `dist/CrystalLegacyRandomizer.app` and a zippable release in `CrystalLegacyRandomizer.zip`.
