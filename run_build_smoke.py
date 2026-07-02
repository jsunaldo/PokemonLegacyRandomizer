#!/usr/bin/env python3
"""
Build smoke test: randomize each game with a representative feature set and
compile a real ROM with `make`. This is the only check that catches bugs in
the *generated* source (bad assembly/C, broken JSON, overflowing banks).

Usage:
    python3 run_build_smoke.py [crystal] [yellow] [emerald]
    (no args = all three)

Runs headless (RANDOMIZER_NO_DIALOG=1): the ROM stays in the output dir.
Source trees come from CRYSTAL_SRC / YELLOW_SRC / EMERALD_SRC env vars,
falling back to the same defaults as run_functional_audit.py.
"""

import os
import shutil
import sys
import tempfile

os.environ["RANDOMIZER_NO_DIALOG"] = "1"

import main  # noqa: E402  (env var must be set before handlers run)

SRC = {
    "crystal": os.environ.get(
        "CRYSTAL_SRC",
        "/Users/jsun/Desktop/Test Randomizer/Pokemon_Crystal_Legacy-main"),
    "yellow": os.environ.get(
        "YELLOW_SRC",
        "/Users/jsun/Desktop/Test Randomizer/Pokemon_Yellow_Legacy-main"),
    "emerald": os.environ.get(
        "EMERALD_SRC",
        "/Users/jsun/Desktop/Test Randomizer/Pokemon_Emerald_Legacy-main"),
}
RUN = {
    "crystal": main._run_randomizer,
    "yellow":  main._run_randomizer_yellow,
    "emerald": main._run_randomizer_emerald,
}
ROM_EXT = {"crystal": ".gbc", "yellow": ".gbc", "emerald": ".gba"}

# One max-ish profile per game: every feature that touches generated
# source is enabled so the compiler sees all of our output.
def _profile(game):
    g2 = game in ("crystal", "yellow")
    sp = ["CHARMANDER", "PIKACHU", "GASTLY"] if g2 else \
         ["SPECIES_CHARMANDER", "SPECIES_PIKACHU", "SPECIES_GASTLY"]
    item = "RARE_CANDY" if g2 else "ITEM_RARE_CANDY"
    moves = ["TACKLE", "EMBER"] if g2 else ["MOVE_TACKLE", "MOVE_EMBER"]
    mon = ({"species": sp[0], "box": 1, "level": 50, "nickname": "SMOKE",
            "heldItem": item, "moves": moves,
            "dvAtk": 15, "dvDef": 15, "dvSpd": 15, "dvSpc": 15} if g2 else
           {"species": sp[0], "level": 50, "nickname": "SMOKE",
            "heldItem": item, "moves": moves, "ivHP": 31, "ivAtk": 31,
            "ivDef": 31, "ivSpAtk": 31, "ivSpDef": 31, "ivSpd": 31})
    return dict(
        buildRom=True, sourceDir=SRC[game], seed="12345",
        wildMode="random", wildRule="similar_strength", wildNoLegendaries=True,
        wildRandHeldItems=True, trainerMode="random", trainerRivalStarter=True,
        trainerForceEvolved=True, trainerForceEvoLevel=40,
        starterMode="random", staticMode="random",
        fieldItemsMode="random", tradeMode="both",
        tradeRandNicknames=True, tradeRandOT=True, tradeRandIVs=True,
        tradeRandItems=True, fullHMCompat=True, easierEvolutions=True,
        removeTimeEvolutions=True, zeroGrinding=True, elite4Prep=True,
        includeGen1=True, includeGen2=True, includeGen3=True,
        pcPokemonEnable=True, pcPokemon=[mon],
        startingItemsEnable=True, startItemsEnable=True,
        startingBagItems=[{"const": item, "qty": 99}], startingPCItems=[],
        startBagItems=[{"const": item, "qty": 99}], startPcItems=[],
    )


def run(games):
    fails = []
    for game in games:
        if not os.path.isdir(SRC[game]):
            print(f"SKIP {game}: source not found at {SRC[game]}")
            continue
        out = tempfile.mkdtemp(prefix=f"smoke_{game}_")
        print(f"\n########## {game}: randomize + make ##########")
        main._job_error = None
        main._log_lines = []
        try:
            RUN[game](dict(_profile(game), outputDir=out))
        except Exception as e:  # noqa: BLE001
            main._job_error = str(e)
        if main._job_error:
            fails.append(game)
            print(f"FAIL {game}: {main._job_error}")
            # Show the tail of the build log for diagnosis
            for line in main._log_lines[-25:]:
                print("   |", line)
        else:
            roms = [f for f in os.listdir(out) if f.endswith(ROM_EXT[game])]
            if roms:
                size = os.path.getsize(os.path.join(out, roms[0]))
                print(f"PASS {game}: {roms[0]} ({size/1024/1024:.1f} MB)")
            else:
                fails.append(game)
                print(f"FAIL {game}: build reported success but no ROM found")
        shutil.rmtree(out, ignore_errors=True)
    print(f"\n==== build smoke: {len(games) - len(fails)}/{len(games)} passed ====")
    return fails


if __name__ == "__main__":
    games = [g for g in sys.argv[1:] if g in RUN] or ["crystal", "yellow", "emerald"]
    raise SystemExit(1 if run(games) else 0)
