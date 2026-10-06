# Changelog

## v1.2 — unreleased (full re-review, 2026-09-11)

A top-to-bottom review of every module. Most items below are silent bugs:
options that looked like they worked but changed nothing, or changed the
wrong thing.

### Safety
- **Key items are never randomized away (all three games).** Field-item
  randomization treated item balls holding key items as ordinary items, so
  they could be replaced or shuffled. Confirmed against v1.1: Yellow's Rocket
  Hideout B4F **Lift Key** became a Super Repel and the **Silph Scope** a Max
  Repel, softlocking the game. Also exposed: Yellow's Card Key, Secret Key and
  Gold Teeth, and Emerald's Storage Key, Scanner and the four Abandoned Ship
  room keys. Key items are now read from each game's own source (Yellow
  `KeyItemFlags`, Crystal's KEY_ITEM pocket, Emerald's POCKET_KEY_ITEMS, plus
  all HMs) and left in place in every mode. A final check stops a run before
  writing anything if a key item would ever move. New regression gate:
  `run_key_item_audit.py`.
- **Clear error when Rosetta is missing.** RGBDS 0.5.2 / 0.7.0 only ship Intel
  binaries; on an Apple Silicon Mac without Rosetta (e.g. after upgrading to
  macOS 27) Yellow/Crystal builds failed with "Bad CPU type". The app now says
  so and gives the one-line fix.
- **The Output Directory is no longer wiped blindly.** A run now refuses to
  delete a folder that is non-empty unless it was created by a previous
  randomizer run (marker file `.legacy_randomizer_output`, or an older
  `settings_used.json` / `spoiler_log.txt`). Pointing Output at your home or
  Documents folder now errors instead of erasing it.
- Source inside Output (or Output inside Source) is rejected.
- The local API only accepts requests from the randomizer's own page. A web
  page open in another tab can no longer start a job or stop the server.
- The launcher window asks before closing while a build is running.
- A non-numeric seed is an error instead of silently being replaced by a
  random one. A blank seed still rolls a random one, and the seed actually
  used is shown afterwards.

### All games
- **"Get source" button** next to the Source Directory field downloads the
  game's Legacy source repo (`git clone`) into `~/Pokemon Legacy Sources/` and
  fills the field in — the number-one first-run stumble was pointing the app
  at a ROM folder. Pointing it at a folder of `.gbc`/`.gba` files now explains
  that the randomizer patches *source code*, not ROMs, and offers the button.
- **Result panel** after every run: seed, ROM path, output folder, *Reveal ROM
  in Finder* / *Open output folder* / *Copy seed*. Errors show the first
  compiler error inline with a *Show full log* button.
- Live phase in the status line (parsing → randomizing → writing → building).
- Reloading or reopening a page while a job is running reconnects to it
  (log + status), and the browser warns before closing the tab mid-build.
- The Randomize button and *Save Settings* now send the **same** settings
  object, so `settings_used.json` always round-trips. (Crystal previously
  dropped the *Customize Starting Items* flag, so a reloaded file silently
  lost its starting items.)
- `make` runs in parallel (`-jN`, retried serially if that fails). Builds are
  several times faster; Emerald in particular.
- Output folders on cloud-synced drives (Dropbox / iCloud / Google Drive /
  OneDrive) are built in a local temp folder and the ROM copied back — sync
  daemons were corrupting large builds.
- The active tab is remembered per game. Seed fields accept digits only.
- Conflict warnings cover more real no-ops (Catch 'Em All with a 1-to-1
  mapping, Rival Carries Starter with Trainers = Unchanged, PC Pokémon rows
  with no species).
- Version badge on every page; `/api/version`.
- `python3 main.py --port N --no-browser` for fixed-port / headless use.

### Crystal Legacy
- **Force Fully Evolved** only knew about level-up evolutions. Stone,
  happiness, trade and stat evolutions (Golbat, Onix, Chansey, Eevee, Gloom,
  Haunter…) now evolve too.
- **Rival Carries Starter** looked at the already-randomized party to decide
  which starter the rival had, so every rival battle used the Cyndaquil ball —
  sometimes the same Pokémon the player picked. The rival now carries the
  starter from the correct ball in every battle, and starters with stone /
  happiness evolutions (e.g. a custom Eevee) evolve at the levels the
  original lineage would have.
- With starters unchanged, the rival previously got the Totodile line while
  holding Chikorita; fixed.
- **In-game trade sub-options did nothing.** Crystal Legacy stores trades as
  single-line `npctrade` macros; nickname, OT, DV and held-item
  randomization are now written into that line (string lengths preserved).
- **Global 1-to-1** wild mapping now also applies to fishing, so a species
  fished up maps to the same replacement it has on land.
- **PC Pokémon**: nicknames with `'`, `!`, `?` or `,` were encoded with the
  wrong bytes (FARFETCH'D showed a garbage glyph); a DV of 0 became 15;
  experience was always the Medium Fast curve, so Slow / Medium Slow species
  jumped or stalled a level after their first battle. All three fixed
  (growth rates are read from the source's base stats).
- Boss / rival detection matches whole words: WILLIAM is no longer a "boss"
  because of WILL, ALFRED is not RED, and LT.SURGE, RED, Giovanni and the
  Executives are recognised.

### Yellow Legacy
- **Random (Even Distribution)** was plain random — it now deals one
  shuffled pool across every trainer slot.
- **Catch 'Em All** was plain random — every species now appears in the
  wild at least once.
- **Type Themed Areas / Type Themed trainers** matched each Pokémon's own
  type instead of giving the area / trainer one random type as described.
  *Weight Types by Number of Pokémon* and *Similar Strength* for trainers
  were accepted by the UI and ignored; both work now.
- **Force Fully Evolved** never evolved anything (it only avoided
  under-levelled picks). It now follows the real evolution data.
- **Unchecking Ban Bad Items put key items in the overworld** (badges,
  Bicycle, Pokédex, elevator floor keys…). The pools now come from the
  curated item tables; key items are never placed.
- Field items support Shuffle and Random (Evenly Distribute) as the UI
  already offered.
- Static "Random (Completely)" may now give legendaries, as described; Swap /
  Similar Strength stay non-legendary.
- Fishing follows the wild rule (similar strength, global 1-to-1).
- Lt. Surge is recognised as a boss; the rival uses the boss pool.
- Trainer party rewrites keep trailing comments.

### Emerald Legacy
- **Force Fully Evolved** was parsed and ignored — implemented using the full
  evolution table (all branches, incl. Eevee / Tyrogue / Wurmple).
- **Zero Grinding / Elite 4 Prep** picked the first map script that merely
  *mentioned* "Oldale" / "League" in unsorted directory order; they now
  patch the mart by map folder name (OldaleTown_Mart,
  EverGrandeCity_PokemonLeague_1F).
- Similar Strength is honoured in Area / Global 1-to-1 modes.
- The engine uses its own RNG instance (same results for a given seed, no
  longer dependent on the process-wide `random` state).
- Static-encounter help text updated: gifts, eggs and Legacy's event
  legendaries are randomized too.

## v1.1 — 2026-07-02
Presets (Recommended / Light / Chaos), Emerald ability randomization,
cross-platform `python3 main.py` tier.

## v1.0 — 2026-06-18
First public release: Yellow / Crystal / Emerald Legacy randomizers,
launcher, spoiler log, bug reporting.
