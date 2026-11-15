#!/usr/bin/env python3
"""Reference arm: run AMRFinderPlus and apply the rule in scripts/reference_rule.md.

    python scripts/04_reference_arm.py --genomes sandbox/data/genomes \
        --out runs/amrfinderplus

Writes
    <out>/raw/ISO_###.amrfinder.tsv   one AMRFinderPlus report per isolate
    <out>/predictions.tsv             isolate_id, antibiotic, prediction, evidence
    <out>/commands.log                every command run, with exit code and output

The rule is fixed in scripts/reference_rule.md and frozen with the protocol.
Only `Element type = AMR` rows count; matching is case-insensitive on whole
slash-separated tokens.
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ANTIBIOTICS = ["ampicillin", "cefotaxime", "meropenem", "ciprofloxacin",
               "gentamicin", "trimethoprim/sulfamethoxazole"]


def alan(r: dict, *adlar: str) -> str:
    """İlk dolu sütun. AMRFinderPlus 4.x 'Type'/'Subtype'/'Element symbol' yazar;
    eski sürümler 'Element type'/'Element subtype'/'Gene symbol' yazıyordu."""
    for a in adlar:
        v = r.get(a)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def tokens(value: str) -> set[str]:
    """Whole slash-separated tokens, upper case. 'GENTAMICIN/TOBRAMYCIN' -> {GENTAMICIN, TOBRAMYCIN}."""
    return {t.strip().upper() for t in (value or "").split("/") if t.strip()}


def call(rows: list[dict], antibiotic: str) -> tuple[str, str]:
    """Apply the reference rule. Returns (prediction, evidence)."""
    amr = [r for r in rows if alan(r, "Type", "Element type").upper() == "AMR"]
    hits: list[tuple[dict, str]] = []

    def gene(r: dict) -> str:
        return alan(r, "Element symbol", "Gene symbol", "Element name") or "?"

    for r in amr:
        cls, sub = tokens(alan(r, "Class")), tokens(alan(r, "Subclass"))
        if antibiotic == "ampicillin" and "BETA-LACTAM" in cls:
            hits.append((r, gene(r)))
        elif antibiotic == "cefotaxime" and sub & {"CEPHALOSPORIN", "CARBAPENEM"}:
            hits.append((r, gene(r)))
        elif antibiotic == "meropenem" and "CARBAPENEM" in sub:
            hits.append((r, gene(r)))
        elif antibiotic == "ciprofloxacin" and ("QUINOLONE" in cls or "QUINOLONE" in sub):
            hits.append((r, gene(r)))
        elif antibiotic == "gentamicin" and "GENTAMICIN" in sub:
            hits.append((r, gene(r)))

    if antibiotic == "trimethoprim/sulfamethoxazole":
        tmp = [gene(r) for r in amr if "TRIMETHOPRIM" in tokens(alan(r, "Class")) | tokens(alan(r, "Subclass"))]
        sul = [gene(r) for r in amr if "SULFONAMIDE" in tokens(alan(r, "Class")) | tokens(alan(r, "Subclass"))]
        if tmp and sul:
            return "R", "trimethoprim: " + ", ".join(sorted(set(tmp))) + "; sulfonamide: " + ", ".join(sorted(set(sul)))
        found = ("trimethoprim only: " + ", ".join(sorted(set(tmp)))) if tmp else \
                ("sulfonamide only: " + ", ".join(sorted(set(sul)))) if sul else "no determinant found"
        return "S", found

    if hits:
        return "R", ", ".join(sorted({g for _, g in hits}))
    return "S", "no determinant found"


def read_report(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--genomes", default="sandbox/data/genomes")
    ap.add_argument("--out", default="runs/amrfinderplus")
    ap.add_argument("--amrfinder", default="amrfinder")
    ap.add_argument("--threads", default="4")
    a = ap.parse_args()

    genomes = sorted(Path(a.genomes).glob("ISO_*.fasta"))
    if not genomes:
        sys.exit(f"No ISO_*.fasta in {a.genomes}")
    if not shutil.which(a.amrfinder):
        sys.exit(f"{a.amrfinder} not on PATH. Activate the environment: conda activate amr")

    out = Path(a.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    log = (out / "commands.log").open("w")

    preds = []
    for fasta in genomes:
        iso = fasta.stem
        report = out / "raw" / f"{iso}.amrfinder.tsv"
        if not report.exists():
            cmd = [a.amrfinder, "-n", str(fasta), "--organism", "Escherichia",
                   "--plus", "--threads", a.threads, "-o", str(report)]
            p = subprocess.run(cmd, capture_output=True, text=True)
            log.write(json.dumps({"cmd": " ".join(cmd), "exit_code": p.returncode,
                                  "stdout": p.stdout, "stderr": p.stderr}) + "\n")
            log.flush()
            if p.returncode != 0:
                sys.exit(f"amrfinder failed on {iso}:\n{p.stderr}")
        rows = read_report(report)
        for abx in ANTIBIOTICS:
            pred, ev = call(rows, abx)
            preds.append({"isolate_id": iso, "antibiotic": abx, "prediction": pred, "evidence": ev})
        print(f"{iso}: {sum(1 for p in preds if p['isolate_id'] == iso and p['prediction'] == 'R')} R of {len(ANTIBIOTICS)}",
              file=sys.stderr)
    log.close()

    with (out / "predictions.tsv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["isolate_id", "antibiotic", "prediction", "evidence"], delimiter="\t")
        w.writeheader()
        w.writerows(preds)
    print(f"\n{len(genomes)} isolates, {len(preds)} predictions -> {out / 'predictions.tsv'}")


if __name__ == "__main__":
    main()
