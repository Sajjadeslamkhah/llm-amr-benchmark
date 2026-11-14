#!/usr/bin/env python3
"""Download laboratory-derived E. coli AMR phenotype records from the BV-BRC API.

    python scripts/01_fetch_amr.py                      # laboratory records only (default)
    python scripts/01_fetch_amr.py --evidence-survey     # count records per evidence value

Notes
- BV-BRC refuses offsets >= 100000 (HTTP 400). Each query is therefore filtered
  (antibiotic x evidence, split further by phenotype when needed).
- Most E. coli records in BV-BRC are computational predictions. PROTOCOL.md
  section 4 requires laboratory-derived phenotypes only, so the evidence filter
  is applied in the query. Run --evidence-survey once to record the exact
  evidence strings and their counts for the methods section.
- Each antibiotic is saved to data/raw/parts/ as soon as it is fetched. A rerun
  skips finished parts, so an interrupted download resumes where it stopped.

Output
    data/raw/bvbrc_genome_amr_ecoli.tsv   merged records
    data/MANIFEST.tsv                     query, date, row count, sha256
"""
import argparse
import csv
import datetime as dt
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "https://www.bv-brc.org/api/genome_amr/"
TAXON_ID = 562  # Escherichia coli
EVIDENCE = "Laboratory Method"
ANTIBIOTICS = [  # PROTOCOL.md section 5 candidates, with spelling variants
    "ampicillin", "cefotaxime", "ceftriaxone", "ceftazidime", "meropenem",
    "ciprofloxacin", "gentamicin", "trimethoprim/sulfamethoxazole",
    "sulfamethoxazole/trimethoprim", "trimethoprim-sulfamethoxazole",
]
PHENOTYPES = ["Resistant", "Susceptible", "Intermediate"]
FIELDS = [
    "id", "genome_id", "genome_name", "taxon_id", "antibiotic",
    "resistant_phenotype", "measurement", "measurement_sign",
    "measurement_value", "measurement_unit", "laboratory_typing_method",
    "laboratory_typing_platform", "testing_standard",
    "testing_standard_year", "evidence", "source", "pmid",
]
PAGE = 10000
MAX_OFFSET = 100000

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "data" / "raw" / "parts"
OUT = ROOT / "data" / "raw" / "bvbrc_genome_amr_ecoli.tsv"
MANIFEST = ROOT / "data" / "MANIFEST.tsv"


def q(v: str) -> str:
    return quote(v, safe="")


def get(query: str):
    url = BASE + "?" + query + "&http_accept=application/json"
    for attempt in range(5):
        r = requests.get(url, timeout=180)
        if r.status_code == 200:
            return r.json()
        print(f"  HTTP {r.status_code}, retry {attempt + 1}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def fetch(filters: str):
    """Page through one filtered query. Returns (rows, hit_offset_limit)."""
    rows, start = [], 0
    while start < MAX_OFFSET:
        page = get(f"{filters}&select({','.join(FIELDS)})&sort(+id)&limit({PAGE},{start})")
        rows.extend(page)
        if len(page) < PAGE:
            return rows, False
        start += PAGE
    return rows, True


def count(filters: str) -> int:
    """Number of matching records, read from the Content-Range header."""
    url = BASE + "?" + filters + "&limit(1)&http_accept=application/json"
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    rng = r.headers.get("Content-Range", "")
    return int(rng.split("/")[-1]) if "/" in rng else len(r.json())


def evidence_survey() -> None:
    """Counts per evidence value, for each candidate antibiotic (no download)."""
    print("antibiotic | evidence | n")
    for abx in ANTIBIOTICS:
        base = f"eq(taxon_id,{TAXON_ID}),eq(antibiotic,{q(abx)})"
        total = count(f"and({base})")
        lab = count(f"and({base},eq(evidence,{q(EVIDENCE)}))")
        comp = count(f"and({base},eq(evidence,{q('Computational Method')}))")
        print(f"{abx} | total | {total}\n{abx} | {EVIDENCE} | {lab}\n{abx} | Computational Method | {comp}")


def fetch_antibiotic(abx: str) -> list[dict]:
    base = f"eq(taxon_id,{TAXON_ID}),eq(antibiotic,{q(abx)}),eq(evidence,{q(EVIDENCE)})"
    rows, capped = fetch(f"and({base})")
    if capped:
        rows = []
        for ph in PHENOTYPES:
            part, capped2 = fetch(f"and({base},eq(resistant_phenotype,{ph}))")
            if capped2:
                sys.exit(f"Still >= {MAX_OFFSET} records for {abx}/{ph}; needs a finer split.")
            rows.extend(part)
    return rows


def write_tsv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (",".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-survey", action="store_true")
    if ap.parse_args().evidence_survey:
        evidence_survey()
        return

    PARTS.mkdir(parents=True, exist_ok=True)
    queries = []
    for abx in ANTIBIOTICS:
        part = PARTS / f"{abx.replace('/', '_')}.tsv"
        if part.exists():
            n = sum(1 for _ in part.open()) - 1
            print(f"{abx:32s} {n:7d} records (already downloaded)", file=sys.stderr)
        else:
            rows = fetch_antibiotic(abx)
            write_tsv(part, rows)
            n = len(rows)
            print(f"{abx:32s} {n:7d} records", file=sys.stderr)
        queries.append(f"{abx}:{n}")

    merged = {}
    for part in sorted(PARTS.glob("*.tsv")):
        with part.open() as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                merged[r["id"]] = r
    rows = list(merged.values())
    write_tsv(OUT, rows)

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if new:
            w.writerow(["date_utc", "file", "query", "n_rows", "sha256"])
        w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), OUT.relative_to(ROOT),
                    f"genome_amr taxon_id={TAXON_ID} evidence={EVIDENCE}; " + "; ".join(queries),
                    len(rows), sha])

    print(f"\nRecords: {len(rows)}  Genomes: {len({r.get('genome_id') for r in rows})}")
    for field in ("evidence", "laboratory_typing_method", "resistant_phenotype", "testing_standard"):
        print(f"\n{field}:")
        for value, n in Counter(r.get(field) for r in rows).most_common(15):
            print(f"  {n:7d}  {value}")
    print("\nantibiotic x phenotype:")
    for (a, p), n in sorted(Counter((r.get("antibiotic"), r.get("resistant_phenotype")) for r in rows).items(), key=str):
        print(f"  {n:7d}  {a} | {p}")
    if not rows:
        print(f"\nWARNING: no records with evidence = '{EVIDENCE}'. Run --evidence-survey to see the real values.")


if __name__ == "__main__":
    main()
