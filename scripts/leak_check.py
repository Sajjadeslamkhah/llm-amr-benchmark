#!/usr/bin/env python3
"""Did any agent see the reference phenotypes or the blinding key?

    python scripts/leak_check.py                 # every run
    python scripts/leak_check.py runs/claude     # one arm

The agents work on blinded isolate codes (ISO_###) in a copied workspace, but
nothing stopped them from reading elsewhere on the disk. Two files would break
the blinding if an agent read them:

    data/selection/reference_phenotypes.tsv   genome_id -> antibiotic -> S/R
    data/selection/blinding_key.tsv           ISO_### -> genome_id

Seeing a file NAME in a directory listing is harmless. Seeing its CONTENT is
not. This script separates the two and prints the evidence for each hit, so the
decision to keep or repeat a run rests on what the logs actually show.

Exit code 0 = no content exposure found, 1 = content exposure found.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NAMES = ("reference_phenotypes", "blinding_key")
# Content signatures. The phenotype table pairs a BV-BRC genome id (562.xxxxx)
# with an antibiotic and an S/R/I call; the key pairs an ISO code with one.
HEADER_PHENO = re.compile(r"genome_id\s*\\?t\s*abx\s*\\?t\s*pheno", re.I)
HEADER_KEY = re.compile(r"isolate_id\s*\\?t\s*genome_id", re.I)
ROW_PHENO = re.compile(r"562\.\d+\s*\\?t\s*[a-z/\-]+\s*\\?t\s*[SRI]\b")
ROW_KEY = re.compile(r"ISO_\d{3}\s*\\?t\s*562\.\d+")
# A command that would read a file rather than list a directory
READERS = ("cat ", "head ", "tail ", "less ", "more ", "open ", "grep ", "awk ", "sed ",
           "cut ", "sort ", "python", "pandas", "read_csv", "read_file", "Read(")


def commands(ev: dict):
    """Yield every command string an event carries, whatever the harness."""
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("CommandLine", "command", "cmd") and isinstance(v, str):
                    yield v
                else:
                    yield from walk(v)
        elif isinstance(o, list):
            for x in o:
                yield from walk(x)
    yield from walk(ev)


def scan(path: Path) -> dict:
    name_hits, content_hits, read_attempts = [], [], []
    for n, line in enumerate(path.open(encoding="utf-8", errors="replace"), 1):
        low = line.lower()
        if not any(x in low for x in NAMES) and not ("562." in line and "ISO_" in line):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            ev = {}
        if HEADER_PHENO.search(line) or ROW_PHENO.search(line):
            content_hits.append((n, "reference phenotypes", line[:400]))
        if HEADER_KEY.search(line) or ROW_KEY.search(line):
            content_hits.append((n, "blinding key", line[:400]))
        named_in_cmd = False
        for c in commands(ev):
            if any(x in c for x in NAMES):
                named_in_cmd = True
                entry = (n, c.strip()[:300])
                if any(r in c for r in READERS):
                    read_attempts.append(entry)
                else:
                    name_hits.append(entry)
        if not named_in_cmd and any(x in low for x in NAMES):
            # the name turned up in a tool's OUTPUT, e.g. a directory listing
            i = min((low.find(x) for x in NAMES if x in low), default=0)
            name_hits.append((n, "(in tool output) ..." + line[max(0, i - 80):i + 120].strip()))
    return {"name": name_hits, "content": content_hits, "read": read_attempts}


def main() -> None:
    roots = [Path(a) for a in sys.argv[1:]] or [ROOT / "runs"]
    files = sorted(p for r in roots for p in r.rglob("events.jsonl"))
    if not files:
        sys.exit("No events.jsonl found.")
    bad, pilot_bad = [], []
    print(f"Scanned {len(files)} event logs for exposure of the reference phenotypes "
          f"or the blinding key.\n")
    for p in files:
        r = scan(p)
        if not any(r.values()):
            continue
        rel = p.relative_to(ROOT) if ROOT in p.parents else p
        # rep0 = pilot: its data is discarded by PROTOCOL.md, so it cannot compromise a result
        pilot = "rep0" in rel.parts
        print(f"=== {rel.parent}" + ("   [PILOT - data discarded]" if pilot else ""))
        for n, c in r["name"]:
            print(f"  [name only ] line {n}: {c}")
        for n, c in r["read"]:
            print(f"  [READ CMD  ] line {n}: {c}")
            (pilot_bad if pilot else bad).append(str(rel.parent))
        for n, what, snip in r["content"]:
            print(f"  [CONTENT   ] line {n}: {what} visible -> {snip}")
            (pilot_bad if pilot else bad).append(str(rel.parent))
        print()
    if pilot_bad:
        print("PILOT: " + ", ".join(sorted(set(pilot_bad))) + " read the keys. Pilot data is\n"
              "discarded by protocol, so no result depends on it — but the behaviour itself is\n"
              "reported as an outcome (answer-key seeking).\n")
    if bad:
        print("RESULT: content exposure in SCORED runs: " + ", ".join(sorted(set(bad))) +
              "\nThose runs must be repeated.")
    else:
        print("RESULT: no scored run read either file. Where the names appear, they appear in a\n"
              "directory listing or in the agent's own prose. The blinding holds: an agent that\n"
              "never saw the contents could not map a blinded code to a genome or its phenotype.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
