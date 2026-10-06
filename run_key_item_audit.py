#!/usr/bin/env python3
"""
Key-item regression gate (added 2026-10-06 after Yellow's Lift Key was being
randomized away, softlocking Rocket Hideout).

Randomizes field items for all three games in every mode, with Ban Bad Items
on and off, across 5 seeds, then fails if ANY output line holding a key item
(as defined by the game's own source — see key_items.py) changed.

Usage:  python3 run_key_item_audit.py
Sources: ~/Pokemon Legacy Sources/<repo>  (override with LEGACY_SOURCES=dir)
"""
import os, sys, re, tempfile, shutil, filecmp
REPO=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, REPO); os.environ["RANDOMIZER_NO_DIALOG"]="1"
import main
from key_items import key_items
L=os.path.expanduser(os.environ.get("LEGACY_SOURCES", "~/Pokemon Legacy Sources"))
GAMES={"yellow":(main._run_randomizer_yellow,f"{L}/Pokemon_Yellow_Legacy"),
       "crystal":(main._run_randomizer,f"{L}/Pokemon_Crystal_Legacy"),
       "emerald":(main._run_randomizer_emerald,f"{L}/Pokemon_Emerald_Legacy")}
EXTS=(".asm",".inc",".json")
runs=fails=0; moved_total=0
for game,(fn,src) in GAMES.items():
    keys=key_items(game,src); tok=re.compile(r"\b(" + "|".join(sorted(map(re.escape,keys),key=len,reverse=True)) + r")\b")
    for mode in ("random","shuffle","random_even"):
        for ban in (True,False):
            for seed in (1,2,3,4,5):
                out=tempfile.mkdtemp(prefix="ke2e_"); main._job_error=None; main._log_lines=[]
                fn(dict(sourceDir=src,outputDir=out,seed=str(seed),buildRom=False,wildMode="unchanged",trainerMode="unchanged",
                        starterMode="unchanged",staticMode="unchanged",tradeMode="unchanged",fieldItemsMode=mode,fieldItemsBanBad=ban))
                runs+=1
                if main._job_error: fails+=1; print("ERROR",game,mode,ban,seed,main._job_error[:200]); continue
                changed=bad=0
                for root,_,files in os.walk(src):
                    if "/.git" in root: continue
                    for f in files:
                        if not f.endswith(EXTS): continue
                        a=os.path.join(root,f); b=os.path.join(out,os.path.relpath(a,src))
                        if not os.path.exists(b) or filecmp.cmp(a,b,shallow=False): continue
                        la=open(a,errors="replace").read().splitlines(); lb=open(b,errors="replace").read().splitlines()
                        for x,y in zip(la,lb):
                            if x!=y:
                                changed+=1
                                if tok.search(x) or tok.search(y):
                                    bad+=1; print("  KEY ITEM TOUCHED",game,mode,seed,os.path.relpath(a,src),"|",x.strip()[:90],"→",y.strip()[:90])
                if bad: fails+=1
                moved_total+=changed
                shutil.rmtree(out,ignore_errors=True)
        print(f"  {game}/{mode}: done")
print(f"\n==== {runs} runs, {fails} failing, {moved_total} field-item lines changed in total, key-item lines changed: {'SOME' if fails else 0} ====")

raise SystemExit(1 if fails else 0)
