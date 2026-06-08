"""
Shared spoiler-log builder for all three randomizers (Crystal, Yellow, Emerald).

Each handler hands the builder the original and randomized data structures it
already has; the builder renders a human-readable text file listing what every
Pokémon / item / trainer was changed into.  Only *changed* entries are listed,
so an unchanged category produces no noise.

Every section is wrapped in try/except: a spoiler problem must never break the
randomization itself.
"""

import os
import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(const):
    """Fallback pretty-name for an item/species constant."""
    if not isinstance(const, str):
        return str(const)
    s = const
    for pre in ("SPECIES_", "ITEM_", "MOVE_"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s.replace("_", " ").title()


def _species_of(x):
    """Return the species constant from a string or a dataclass/dict."""
    if x is None:
        return None
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("species")
    return getattr(x, "species", None) or getattr(x, "species_const", None)


def _item_of(x):
    if x is None:
        return None
    if isinstance(x, str):
        return x
    return (getattr(x, "item_const", None) or getattr(x, "item", None)
            or getattr(x, "held_item", None))


class Spoiler:
    def __init__(self, game_title, seed, name_map=None):
        self.game_title = game_title
        self.seed = seed
        self.name_map = name_map or {}
        self.sections = []   # list of (title, [lines])

    # name a species/item constant for display
    def n(self, const):
        if const is None:
            return "—"
        return self.name_map.get(const, _clean(const))

    def section(self, title, lines):
        lines = [l for l in lines if l]
        if lines:
            self.sections.append((title, lines))

    # Build "orig → new" lines for a list of (orig_const, new_const) pairs,
    # skipping unchanged and empty entries.
    def changed_lines(self, pairs, prefix=""):
        out = []
        for o, nw in pairs:
            if o is None and nw is None:
                continue
            if o == nw:
                continue
            out.append(f"{prefix}{self.n(o)}  →  {self.n(nw)}")
        return out

    def render(self):
        out = []
        bar = "=" * 64
        out += [bar,
                f"  {self.game_title} — Randomizer Spoiler Log",
                f"  Seed: {self.seed}",
                f"  Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
                bar, ""]
        if not self.sections:
            out.append("(No randomization changes were made.)")
        for title, lines in self.sections:
            out.append(title)
            out.append("-" * len(title))
            out += ["  " + l for l in lines]
            out.append("")
        return "\n".join(out)

    def write(self, out_dir, log=None):
        path = os.path.join(out_dir, "spoiler_log.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.render())
            if log:
                log(f"Spoiler log written: {path}")
        except Exception as e:        # pragma: no cover - best effort
            if log:
                log(f"[WARN] Could not write spoiler log: {e}")
        return path


# ---------------------------------------------------------------------------
# Generic section builders (shared shapes)
# ---------------------------------------------------------------------------

def _starters_section(sp, orig, new):
    """orig / new are lists of species constants or objects."""
    pairs = []
    for i in range(min(len(orig), len(new))):
        pairs.append((_species_of(orig[i]), _species_of(new[i])))
    sp.section("Starters", sp.changed_lines(pairs))


def _static_section(sp, orig, new):
    pairs = [(_species_of(o), _species_of(n)) for o, n in zip(orig, new)]
    sp.section("Static / Gift Encounters", sp.changed_lines(pairs))


def _field_items_section(sp, orig, new):
    pairs = [(_item_of(o), _item_of(n)) for o, n in zip(orig, new)]
    sp.section("Field Items", sp.changed_lines(pairs))


def _held_items_section(sp, orig, new):
    lines = []
    for o, n in zip(orig, new):
        oi, ni = _item_of(o), _item_of(n)
        if oi == ni:
            continue
        who = sp.n(_species_of(o)) if _species_of(o) else ""
        slot = getattr(o, "slot", "")
        tag = f"{who} ({slot})" if who else ""
        lines.append(f"{tag + ': ' if tag else ''}{sp.n(oi)}  →  {sp.n(ni)}")
    sp.section("Wild Held Items", lines)


def _trade_given(t):
    # Crystal: given_species | Emerald: species | Yellow: give_species
    return (getattr(t, "given_species", None)
            or getattr(t, "give_species", None)
            or getattr(t, "species", None))


def _trades_section(sp, orig, new):
    lines = []
    for o, n in zip(orig, new):
        og, ng = _trade_given(o), _trade_given(n)
        if og != ng and (og or ng):
            lines.append(f"Receive {sp.n(og)}  →  {sp.n(ng)}")
    sp.section("In-Game Trades", lines)


def _trainers_section(sp, orig, new, label_attr, mons_attr):
    """One compact line per trainer whose party changed."""
    lines = []
    for o, n in zip(orig, new):
        omons = getattr(o, mons_attr, []) or []
        nmons = getattr(n, mons_attr, []) or []
        changes = []
        for om, nm in zip(omons, nmons):
            os_, ns_ = _species_of(om), _species_of(nm)
            if os_ != ns_:
                changes.append(f"{sp.n(os_)}→{sp.n(ns_)}")
        if changes:
            label = getattr(o, label_attr, "") or "?"
            lines.append(f"{label}: " + ", ".join(changes))
    sp.section("Trainers", lines)


def _wild_groups_section(sp, orig, new):
    """Gen-2 style: list of WildEncounterGroup with .slots[].species_const."""
    lines = []
    for o, n in zip(orig, new):
        oslots = getattr(o, "slots", []) or []
        nslots = getattr(n, "slots", []) or []
        seen = set()
        pairlist = []
        for os_, ns_ in zip(oslots, nslots):
            a, b = _species_of(os_), _species_of(ns_)
            if a == b or (a, b) in seen:
                continue
            seen.add((a, b))
            pairlist.append(f"{sp.n(a)}→{sp.n(b)}")
        if pairlist:
            loc = getattr(o, "location", "?")
            etype = getattr(o, "encounter_type", "")
            head = f"{loc} ({etype})" if etype else loc
            lines.append(f"{head}: " + ", ".join(pairlist))
    sp.section("Wild Encounters", lines)


def _wild_json_section(sp, orig_json, new_json):
    """Emerald style: parallel JSON walk, deduped per map."""
    lines = []
    og = orig_json.get("wild_encounter_groups", []) if orig_json else []
    ng = new_json.get("wild_encounter_groups", []) if new_json else []
    KEYS = ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons")
    for ogrp, ngrp in zip(og, ng):
        for oenc, nenc in zip(ogrp.get("encounters", []), ngrp.get("encounters", [])):
            seen = set()
            pairlist = []
            for k in KEYS:
                osl = (oenc.get(k) or {}).get("mons") or []
                nsl = (nenc.get(k) or {}).get("mons") or []
                for om, nm in zip(osl, nsl):
                    a, b = om.get("species"), nm.get("species")
                    if a == b or (a, b) in seen:
                        continue
                    seen.add((a, b))
                    pairlist.append(f"{sp.n(a)}→{sp.n(b)}")
            if pairlist:
                lines.append(f"{nenc.get('map', '?')}: " + ", ".join(pairlist))
    sp.section("Wild Encounters", lines)


def _run(fn, *a):
    try:
        fn(*a)
    except Exception:
        pass   # a single broken section must not abort the whole spoiler


# ---------------------------------------------------------------------------
# Per-game entry points
# ---------------------------------------------------------------------------

def build_crystal(sp, parser, d):
    if "starters" in d:    _run(_starters_section, sp, parser.starters, d["starters"])
    if "wild" in d:        _run(_wild_groups_section, sp, parser.wild_encounters, d["wild"])
    if "trainers" in d:    _run(_trainers_section, sp, parser.trainers, d["trainers"], "name", "party")
    if "static" in d:      _run(_static_section, sp, parser.static_encounters, d["static"])
    if "field_items" in d: _run(_field_items_section, sp, parser.field_items, d["field_items"])
    if "trades" in d:      _run(_trades_section, sp, parser.trades, d["trades"])
    if "held" in d:        _run(_held_items_section, sp, parser.wild_held_items, d["held"])


def build_yellow(sp, parser, d):
    if "starters" in d:    _run(_starters_section, sp, parser.starters, d["starters"])
    if "wild" in d:        _run(_wild_groups_section, sp, parser.wild_groups, d["wild"])
    if "trainers" in d:    _run(_trainers_section, sp, parser.trainers, d["trainers"], "name", "party")
    if "static" in d:      _run(_static_section, sp, parser.static_encounters, d["static"])
    if "field_items" in d: _run(_field_items_section, sp, parser.field_items, d["field_items"])
    if "trades" in d:      _run(_trades_section, sp, parser.trades, d["trades"])


def build_emerald(sp, parser, d):
    if "starters" in d:
        _run(_starters_section, sp, [s.species for s in parser.starters], d["starters"])
    if "wild_json" in d:   _run(_wild_json_section, sp, parser.wild_json, d["wild_json"])
    if "trainers" in d:    _run(_trainers_section, sp, parser.trainer_parties, d["trainers"], "party_label", "mons")
    if "static" in d:      _run(_static_section, sp, parser.static_encounters, d["static"])
    if "field_items" in d: _run(_field_items_section, sp, parser.field_items, d["field_items"])
    if "trades" in d:      _run(_trades_section, sp, parser.trades, d["trades"])
    if "held" in d:        _run(_held_items_section, sp, parser.wild_held_items, d["held"])
