#!/usr/bin/env python3
"""Print the Class/Subclass vocabulary of an AMRFinderPlus database.

    python scripts/inspect_amrfinder_db.py "$DB" > data/summary/amrfinder_vocab_<version>.txt

PROTOCOL.md requires the mapping in scripts/reference_rule.md to be checked
against the installed database before the freeze, because these strings
change between database versions. This script reads the catalogue files and
reports, for each column with a small number of distinct values, what those
values are, plus the gene symbols carrying the classes the reference rule uses.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

MAX_DISTINCT = 60
RULE_CLASSES = ["BETA-LACTAM", "QUINOLONE", "AMINOGLYCOSIDE", "TRIMETHOPRIM", "SULFONAMIDE"]


def columns(path: Path) -> None:
    with path.open(encoding="utf-8", errors="replace") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t") if r]
    if not rows:
        return
    header, body = rows[0], rows[1:]
    width = max(len(r) for r in rows)
    print(f"\n### {path.name}  ({len(body)} rows, {width} columns)")
    print("header:", " | ".join(f"{i+1}:{h}" for i, h in enumerate(header)))
    for i in range(width):
        vals = Counter(r[i].strip() for r in body if i < len(r) and r[i].strip())
        if 0 < len(vals) <= MAX_DISTINCT:
            name = header[i] if i < len(header) else f"col{i+1}"
            print(f"\n  -- column {i+1} ({name}): {len(vals)} distinct")
            for v, n in vals.most_common():
                print(f"       {n:7d}  {v}")


def rule_classes(db: Path) -> None:
    """Which gene symbols carry each class the reference rule depends on."""
    fam = db / "fam.tsv"
    if not fam.exists():
        return
    with fam.open(encoding="utf-8", errors="replace") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t") if r]
    hits: dict[str, Counter] = defaultdict(Counter)
    for r in rows[1:]:
        upper = [c.strip().upper() for c in r]
        for cls in RULE_CLASSES:
            if cls in upper:
                # record the subclass values that co-occur with this class
                for c in upper:
                    if c and c != cls and c.replace("-", "").replace("/", "").isalpha() and c.isupper():
                        hits[cls][c] += 1
    print("\n### Subclass values co-occurring with each class used by reference_rule.md")
    for cls in RULE_CLASSES:
        print(f"\n  {cls}: {sum(hits[cls].values())} rows")
        for v, n in hits[cls].most_common(25):
            print(f"       {n:7d}  {v}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: inspect_amrfinder_db.py <AMRFinderPlus database directory>")
    db = Path(sys.argv[1])
    if not db.is_dir():
        sys.exit(f"not a directory: {db}")
    version = db / "version.txt"
    print(f"database directory: {db}")
    if version.exists():
        print(f"database version:   {version.read_text().strip()}")
    for name in ("fam.tsv", "taxgroup.tsv", "AMR_DNA-Escherichia.tsv"):
        p = db / name
        if p.exists():
            columns(p)
    rule_classes(db)


if __name__ == "__main__":
    main()
