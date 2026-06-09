#!/usr/bin/env python3
"""
Independent local-model audit driver.
Feeds each source file to a local Ollama model and collects an audit report.
No project context is given to the model beyond the file itself + a fixed brief,
so the review is genuinely independent.
"""
import json, os, sys, time, urllib.request, datetime

MODEL    = os.environ.get("AUDIT_MODEL", "qwen2.5-coder:32b")
NUM_CTX  = int(os.environ.get("AUDIT_NUM_CTX", "16384"))
OLLAMA   = "http://localhost:11434/api/generate"
HERE     = os.path.dirname(os.path.abspath(__file__))
OUT      = os.path.join(HERE, "LOCAL_AUDIT_REPORT.md")

# Source-of-truth files only (skip build copies, empties, this script).
FILES = [
    "main.py", "parser.py", "writer.py", "randomizer_engine.py", "constants.py",
    "static_data.py", "item_data.py", "trade_data.py", "launcher_gui.py",
    "parser_yellow.py", "writer_yellow.py", "randomizer_engine_yellow.py", "constants_yellow.py",
    "parser_emerald.py", "writer_emerald.py", "randomizer_engine_emerald.py", "constants_emerald.py",
    "spoiler_log.py",
]

# Lines per chunk so a chunk + prompt + reply fits comfortably in NUM_CTX.
MAX_LINES = 850

BRIEF = (
    "You are a senior Python engineer doing an INDEPENDENT code audit of a "
    "Pokemon ROM randomizer. You are seeing this file in isolation. Review it for:\n"
    "1. Correctness bugs and logic errors\n"
    "2. Crash risks / unhandled edge cases (bad input, missing keys, off-by-one, encoding)\n"
    "3. ROM-safety issues (writing out of bounds, checksum/pointer mistakes, data corruption)\n"
    "4. Security or file-handling concerns\n"
    "5. Code quality / maintainability problems worth flagging\n\n"
    "Be concrete: cite the function or line. Prioritize real findings over style nitpicks. "
    "If a section looks correct, say so briefly. Use short bullet points.\n\n"
)

def ask(prompt):
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False,
        "options": {"num_ctx": NUM_CTX, "temperature": 0.2},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)["response"]

def chunks(lines):
    for i in range(0, len(lines), MAX_LINES):
        yield i // MAX_LINES + 1, lines[i:i + MAX_LINES], (len(lines) + MAX_LINES - 1) // MAX_LINES

def main():
    started = datetime.datetime.now()
    with open(OUT, "w") as out:
        out.write(f"# Local Model Audit — {MODEL}\n\n")
        out.write(f"Generated {started:%Y-%m-%d %H:%M} · context {NUM_CTX} tokens\n\n")
        out.write("Each file was reviewed independently by the local model.\n\n---\n\n")
    summaries = []
    for fn in FILES:
        path = os.path.join(HERE, fn)
        if not os.path.exists(path):
            print(f"SKIP (missing): {fn}"); continue
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        print(f"[{datetime.datetime.now():%H:%M:%S}] Reviewing {fn} ({len(lines)} lines)...", flush=True)
        file_review = []
        for n, chunk, total in chunks(lines):
            t0 = time.time()
            tag = f"{fn}" if total == 1 else f"{fn} (part {n}/{total})"
            prompt = BRIEF + f"FILE: {tag}\n```python\n" + "\n".join(chunk) + "\n```\n"
            try:
                review = ask(prompt)
            except Exception as e:
                review = f"_(model error: {e})_"
            dt = time.time() - t0
            print(f"    part {n}/{total} done in {dt:.0f}s", flush=True)
            file_review.append((tag, review))
        with open(OUT, "a") as out:
            out.write(f"## {fn}\n\n")
            for tag, review in file_review:
                if len(file_review) > 1:
                    out.write(f"### {tag}\n\n")
                out.write(review.strip() + "\n\n")
            out.write("---\n\n")
        summaries.append((fn, "\n".join(r for _, r in file_review)))

    # Final synthesis pass across all per-file findings.
    print("Synthesizing overall audit...", flush=True)
    joined = "\n\n".join(f"=== {fn} ===\n{rev}" for fn, rev in summaries)
    # Trim if enormous so the synthesis fits.
    if len(joined) > 40000:
        joined = joined[:40000] + "\n...[truncated]..."
    synth_prompt = (
        "Below are independent per-file audit notes for a Pokemon ROM randomizer. "
        "Write an EXECUTIVE SUMMARY: the top 10 most important issues across the whole "
        "codebase ranked by severity (Critical/High/Medium/Low), each with the file and a "
        "one-line fix suggestion. Then a short overall assessment of code health.\n\n" + joined
    )
    try:
        synthesis = ask(synth_prompt)
    except Exception as e:
        synthesis = f"_(synthesis error: {e})_"
    with open(OUT, "r") as f:
        existing = f.read()
    with open(OUT, "w") as out:
        out.write(f"# Local Model Audit — {MODEL}\n\n")
        out.write("## Executive Summary\n\n" + synthesis.strip() + "\n\n---\n\n")
        # re-append the per-file detail (skip the old title line)
        out.write(existing.split("\n\n", 2)[-1])
    elapsed = datetime.datetime.now() - started
    print(f"DONE in {elapsed}. Report: {OUT}", flush=True)

if __name__ == "__main__":
    main()
