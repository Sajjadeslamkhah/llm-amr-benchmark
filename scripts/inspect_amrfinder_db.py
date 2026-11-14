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


def read_fam(db: Path) -> list[dict]:
    """fam.tsv as dicts. Its header line starts with '#'; columns include
    type, subtype, class, subclass, gene_symbol."""
    fam = db / "fam.tsv"
    if not fam.exists():
        return []
    with fam.open(encoding="utf-8", errors="replace") as fh:
        header = fh.readline().lstrip("#").rstrip("\n").split("\t")
        return [dict(zip(header, line.rstrip("\n").split("\t")))
                for line in fh if line.strip()]


def rule_classes(db: Path) -> None:
    """The class / subclass vocabulary that scripts/reference_rule.md depends on.

    Only rows with type == AMR matter: the file also carries STRESS and
    VIRULENCE entries, which the reference rule must not treat as resistance.
    """
    rows = [r for r in read_fam(db) if (r.get("type") or "").strip().upper() == "AMR"]
    if not rows:
        print("\n### fam.tsv not readable or has no type=AMR rows")
        return
    print(f"\n### fam.tsv, type=AMR rows: {len(rows)}")

    classes = Counter((r.get("class") or "").strip() for r in rows)
    print(f"\n  -- distinct class values ({len(classes)})")
    for v, n in classes.most_common():
        print(f"       {n:7d}  {v or '(empty)'}")

    print("\n  -- subclass values, for each class used by reference_rule.md")
    for cls in RULE_CLASSES:
        sub = Counter((r.get("subclass") or "").strip()
                      for r in rows if (r.get("class") or "").strip().upper() == cls)
        print(f"\n     {cls}: {sum(sub.values())} rows, {len(sub)} distinct subclasses")
        for v, n in sub.most_common():
            print(f"       {n:7d}  {v or '(empty)'}")

    print("\n  -- subclass values mentioning an antibiotic the study uses")
    for needle in ("AMPICILLIN", "CEFOTAXIME", "MEROPENEM", "CIPROFLOXACIN",
                   "GENTAMICIN", "TRIMETHOPRIM", "SULFONAMIDE", "QUINOLONE",
                   "CEPHALOSPORIN", "CARBAPENEM"):
        hits = Counter(f"{(r.get('class') or '').strip()} / {(r.get('subclass') or '').strip()}"
                       for r in rows if needle in (r.get("subclass") or "").upper())
        if hits:
            print(f"\n     '{needle}' appears in: " + ", ".join(f"{k} (n={v})" for k, v in hits.most_common()))


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
