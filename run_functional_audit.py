#!/usr/bin/env python3
"""
Functional audit for all three randomizers.

Runs each game's full pipeline (parse → randomize → write, no ROM build)
across several representative setting profiles and seeds, and reports any
job error or exception. This is the regression gate used before releases.

Usage:
    python3 run_functional_audit.py

Source trees are located via the environment variables CRYSTAL_SRC,
YELLOW_SRC and EMERALD_SRC, falling back to the paths below.
"""

import os
import shutil
import tempfile
import traceback

import main

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

G2_SP = ["CHARMANDER", "PIKACHU", "GASTLY"]
G3_SP = ["SPECIES_CHARMANDER", "SPECIES_PIKACHU", "SPECIES_GASTLY"]


def _reset():
    main._job_error = None
    main._log_lines = []


def _pcmon(g2):
    if g2:
        return [{"species": G2_SP[0], "box": 1, "level": 50, "nickname": "AUDIT",
                 "heldItem": "RARE_CANDY", "moves": ["TACKLE", "EMBER"],
                 "dvAtk": 15, "dvDef": 15, "dvSpd": 15, "dvSpc": 15}]
    return [{"species": G3_SP[0], "level": 50, "nickname": "AUDIT",
             "heldItem": "ITEM_RARE_CANDY", "moves": ["MOVE_TACKLE", "MOVE_EMBER"],
             "ivHP": 31, "ivAtk": 31, "ivDef": 31,
             "ivSpAtk": 31, "ivSpDef": 31, "ivSpd": 31}]


def _items(g2):
    return [{"const": "RARE_CANDY" if g2 else "ITEM_RARE_CANDY", "qty": 99}]


def _profiles(game):
    g2 = game in ("crystal", "yellow")
    base = dict(buildRom=False, sourceDir=SRC[game])
    unchanged = dict(base, wildMode="unchanged", trainerMode="unchanged",
                     starterMode="unchanged", staticMode="unchanged",
                     fieldItemsMode="unchanged", tradeMode="unchanged")
    max_features = dict(
        base,
        wildMode="random", wildRule="catch_em_all", wildNoLegendaries=True,
        wildRandHeldItems=True, wildBanBadHeldItems=True, wildTimeBased=True,
        trainerMode="random", trainerNoLegend=True, trainerBossNoLegend=True,
        trainerNoBaby=True, trainerSimilarStrength=True, trainerRivalStarter=True,
        trainerForceEvolved=True, trainerForceEvoLevel=40,
        starterMode="random", starterNoLegendaries=True,
        starterRandItems=True, starterBanBadItems=True,
        staticMode="random", fieldItemsMode="random", fieldItemsBanBad=True,
        tradeMode="both", tradeRandNicknames=True, tradeRandOT=True,
        tradeRandIVs=True, tradeRandItems=True,
        fullHMCompat=True, easierEvolutions=True, removeTimeEvolutions=True,
        zeroGrinding=True, elite4Prep=True,
        genFilter="all", includeGen1=True, includeGen2=True, includeGen3=True,
        pcPokemonEnable=True, pcPokemon=_pcmon(g2),
        startingItemsEnable=True, startItemsEnable=True,
        startingBagItems=_items(g2), startingPCItems=_items(g2),
        startBagItems=_items(g2), startPcItems=_items(g2),
    )
    alt_modes = dict(base, wildMode="area1to1", wildRule="type_themed",
                     trainerMode="type_themed_boss", starterMode="random_two_stage",
                     staticMode="swap", fieldItemsMode="shuffle",
                     tradeMode="given_only", fullHMCompat=True)
    custom = dict(base, starterMode="custom",
                  customStarters=(G2_SP if g2 else G3_SP),
                  customStarter=(G2_SP if g2 else G3_SP)[0],
                  wildMode="unchanged", trainerMode="unchanged",
                  staticMode="unchanged", fieldItemsMode="unchanged",
                  tradeMode="unchanged")
    return [("unchanged", unchanged), ("max-features", max_features),
            ("alt-modes", alt_modes), ("custom-starter", custom)]


def run():
    total = fails = 0
    for game in ["crystal", "yellow", "emerald"]:
        if not os.path.isdir(SRC[game]):
            print(f"  SKIP {game}: source not found at {SRC[game]}")
            continue
        for name, payload in _profiles(game):
            seeds = [1] if name in ("unchanged", "custom-starter") else [1, 2, 3, 4, 5]
            for seed in seeds:
                total += 1
                out = tempfile.mkdtemp(prefix=f"aud_{game}_")
                try:
                    _reset()
                    RUN[game](dict(payload, outputDir=out, seed=str(seed)))
                    if main._job_error:
                        fails += 1
                        print(f"FAIL {game}/{name}/seed{seed}: {main._job_error}")
                except Exception as e:
                    fails += 1
                    print(f"EXC  {game}/{name}/seed{seed}: {e}")
                    traceback.print_exc()
                finally:
                    shutil.rmtree(out, ignore_errors=True)
            print(f"  ok: {game}/{name}")
    print(f"\n==== {total} runs, {fails} failures ====")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
