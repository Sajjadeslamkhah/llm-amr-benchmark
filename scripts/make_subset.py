#!/usr/bin/env python3
"""Draw the pre-specified reproducibility subset (PROTOCOL.md section 8).

    python scripts/make_subset.py

Writes data/selection/reproducibility_subset.txt: 40 isolate codes drawn with
SEED = 20261114 from the QC-pass isolates, using the blinded codes only. It
refuses to overwrite an existing file, so the subset is drawn once and stays
fixed. Phenotypes are never read here: the draw cannot depend on outcomes.
"""
import random
import sys
from pathlib import Path

SEED = 20261114
N = 40
ROOT = Path(__file__).resolve().parent.parent
GENOMES = ROOT / "sandbox" / "data" / "genomes"
OUT = ROOT / "data" / "selection" / "reproducibility_subset.txt"


def main() -> None:
    if OUT.exists():
        sys.exit(f"{OUT} already exists; the subset is drawn once and not redrawn.")
    codes = sorted(p.stem for p in GENOMES.glob("ISO_*.fasta"))
    if not codes:
        sys.exit(f"No genomes in {GENOMES}. Run scripts/03_fetch_genomes.py first.")
    if len(codes) < N:
        sys.exit(f"Only {len(codes)} isolates available, need {N}.")
    chosen = sorted(random.Random(SEED).sample(codes, N))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(chosen) + "\n")
    print(f"{len(chosen)} of {len(codes)} isolates -> {OUT}")
    print(", ".join(chosen[:8]) + " ...")


if __name__ == "__main__":
    main()
