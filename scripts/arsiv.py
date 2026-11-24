#!/usr/bin/env python3
"""Copy the study's primary output into the repository, with checksums.

    python scripts/arsiv.py            # see what would be copied
    python scripts/arsiv.py --yaz      # copy it

Why this exists
---------------
No primary output of this study has ever been under version control. The statistics
review found `results/` holding nothing but a `.gitkeep` and `runs/` a single
`VERSIONS.txt`, and said plainly that a reader cannot check one denominator — which is
self-undermining in a paper arguing that knowing what was measured matters as much as
how well it performed. It is not only a reviewer's problem: `results/audit/` has
vanished twice during this work, both times unnoticed, and the sheet one adjudicator
had already worked from was lost with it.

So the files the manuscript's numbers come from are copied into `archive/`, which git
tracks, next to a manifest giving each one's SHA-256 and byte count. The manifest is
what a reader verifies against, and what tells us if a file changes under us.

What is deliberately left out
-----------------------------
Anything whose name contains "key": the blinding key and the adjudication key resolve
which arm produced which row, and the adjudication is not finished.

The reference phenotypes. They stay outside the repository tree for the reason they
were put there — the agents run inside this tree, and a scored run that can read the
answers is not a scored run. Replicate 4 was run after the freeze and others may be,
so this is a live constraint rather than a historical one. They are published with the
Zenodo deposit at submission, which is where they belong: outside the agents' reach and
inside the record.

Genome FASTA copies under each batch's workspace. They are copies of public BV-BRC
assemblies, they dominate the byte count, and `data/MANIFEST.tsv` already identifies
every one by genome id and checksum.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "archive"
MAX_MB = 25          # per file; anything larger is listed and skipped, not silently dropped

# (glob, why it is kept)
PATTERNS: list[tuple[str, str]] = [
    ("results/*.tsv", "the tables every number in the manuscript is read from"),
    ("results/audit/*.tsv", "hallucination screen candidates and the blinded sheet"),
    ("runs/*/rep*/predictions.tsv", "each arm's calls, per replicate"),
    ("runs/*/rep*/commands.log", "every command an agent ran, with exit code"),
    ("runs/*/rep*/transcript.txt", "the agent's narrative, as the screen read it"),
    ("runs/*/rep*/methods.md", "the methods each agent wrote for itself"),
    ("runs/*/rep*/harness.txt", "harness version recorded before the run"),
    ("runs/*/rep*/events.jsonl", "the raw event stream, before normalisation"),
    ("runs/amrfinderplus/raw/*.amrfinder.tsv", "the determinant report per isolate"),
    ("runs/*/VERSIONS.txt", "tool versions"),
    ("data/MANIFEST.tsv", "genome ids and checksums for the assemblies"),
    ("data/summary/*", "selection summaries and the catalogue vocabulary"),
]

FORBIDDEN = ("key",)                      # substring, case-insensitive, in the file name
FORBIDDEN_STEMS = ("reference_phenotypes", "pheno")


def refused(p: Path) -> str:
    low = p.name.lower()
    for f in FORBIDDEN:
        if f in low:
            return f"adi '{f}' iceriyor"
    for f in FORBIDDEN_STEMS:
        if low.startswith(f):
            return f"referans fenotipleri depo agacinin disinda kalir ('{f}')"
    return ""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaz", action="store_true", help="copy; without it, only report")
    ap.add_argument("--dogrula", action="store_true",
                    help="recompute every checksum in archive/MANIFEST.tsv and report")
    ap.add_argument("--max-mb", type=float, default=MAX_MB)
    a = ap.parse_args()

    if a.dogrula:
        man = DEST / "MANIFEST.tsv"
        if not man.exists():
            sys.exit(f"{man} yok. Once: python scripts/arsiv.py --yaz")
        with man.open(encoding="utf-8") as fh:
            entries = list(csv.DictReader(fh, delimiter="\t"))
        missing, changed = [], []
        for e in entries:
            f = DEST / e["path"]
            if not f.exists():
                missing.append(e["path"])
            elif sha256(f) != e["sha256"]:
                changed.append(e["path"])
        print(f"{len(entries)} kayit kontrol edildi")
        for label, items in (("EKSIK", missing), ("DEGISMIS", changed)):
            for it in items:
                print(f"  {label}: {it}")
        if missing or changed:
            # FREEZE.md told readers to verify twelve files with shasum and five of them
            # no longer matched, which nobody noticed until a reviewer ran it. A
            # mismatch here is an error, not a warning.
            sys.exit(f"\n{len(missing)} eksik, {len(changed)} degismis. "
                     f"Her birini PROTOCOL.md bolum 12'ye bagla ya da arsivi yenile.")
        print("Hepsi manifestle uyusuyor.")
        return

    keep, skipped, blocked = [], [], []
    for pattern, why in PATTERNS:
        for src in sorted(ROOT.glob(pattern)):
            if not src.is_file():
                continue
            why_not = refused(src)
            if why_not:
                blocked.append((src, why_not))
                continue
            mb = src.stat().st_size / 1e6
            if mb > a.max_mb:
                skipped.append((src, mb))
                continue
            keep.append((src, why, mb))

    if blocked:
        print("DISARIDA BIRAKILDI (kasitli):")
        for src, why_not in blocked:
            print(f"  {src.relative_to(ROOT)}  -  {why_not}")
        print()
    if skipped:
        print(f"BUYUK OLDUGU ICIN ATLANDI (> {a.max_mb} MB), Zenodo'ya gidecek:")
        for src, mb in skipped:
            print(f"  {src.relative_to(ROOT)}  {mb:.1f} MB")
        print()

    total = sum(mb for _, _, mb in keep)
    print(f"{len(keep)} dosya, {total:.1f} MB")
    if not keep:
        sys.exit("Arsivlenecek dosya bulunamadi; once analizleri kosun.")
    if not a.yaz:
        for src, why, mb in keep[:12]:
            print(f"  {src.relative_to(ROOT)}  ({mb:.2f} MB)  {why}")
        if len(keep) > 12:
            print(f"  ... ve {len(keep) - 12} dosya daha")
        print("\nKopyalamak icin: python scripts/arsiv.py --yaz")
        return

    rows = []
    for src, why, _ in keep:
        rel = src.relative_to(ROOT)
        dst = DEST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({"path": str(rel), "bytes": src.stat().st_size,
                     "sha256": sha256(src), "why_kept": why})

    DEST.mkdir(exist_ok=True)
    with (DEST / "MANIFEST.tsv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256", "why_kept"],
                           delimiter="\t")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["path"]))
    print(f"\n{len(rows)} dosya kopyalandi -> {DEST.relative_to(ROOT)}/")
    print(f"MANIFEST.tsv yazildi ({len(rows)} kayit).")
    print("Dogrulamak icin:  python scripts/arsiv.py --dogrula")


if __name__ == "__main__":
    main()
