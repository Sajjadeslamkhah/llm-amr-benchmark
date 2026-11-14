#!/usr/bin/env python3
"""Download E. coli AMR phenotype records from the BV-BRC public API.

    python scripts/01_fetch_amr.py

BV-BRC refuses offsets >= 100000 (HTTP 400), so records are fetched per
candidate antibiotic (and, if needed, per phenotype), each query staying
below that limit.

Output
    data/raw/bvbrc_genome_amr_ecoli.tsv   one row per AMR record
    data/MANIFEST.tsv                     query, date, row count, sha256
"""
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
OUT = ROOT / "data" / "raw" / "bvbrc_genome_amr_ecoli.tsv"
MANIFEST = ROOT / "data" / "MANIFEST.tsv"


def get(query: str) -> list[dict]:
    url = BASE + "?" + query + "&http_accept=application/json"
    for attempt in range(5):
        r = requests.get(url, timeout=180)
        if r.status_code == 200:
            return r.json()
        print(f"  HTTP {r.status_code}, retry {attempt + 1}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return []


def fetch(filters: str) -> tuple[list[dict], bool]:
    """Page through one filtered query. Returns (rows, hit_offset_limit)."""
    rows, start = [], 0
    while start < MAX_OFFSET:
        page = get(f"{filters}&select({','.join(FIELDS)})&sort(+id)&limit({PAGE},{start})")
        rows.extend(page)
        if len(page) < PAGE:
            return rows, False
        start += PAGE
    return rows, True


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows, queries = {}, []
    for abx in ANTIBIOTICS:
        base = f"and(eq(taxon_id,{TAXON_ID}),eq(antibiotic,{quote(abx, safe='')}))"
        rows, capped = fetch(base)
        if capped:  # split further by phenotype
            rows = []
            for ph in PHENOTYPES:
                part, capped2 = fetch(f"and(eq(taxon_id,{TAXON_ID}),eq(antibiotic,{quote(abx, safe='')}),eq(resistant_phenotype,{ph}))")
                if capped2:
                    sys.exit(f"Still >= {MAX_OFFSET} records for {abx}/{ph}; needs a finer split.")
                rows.extend(part)
        for r in rows:
            all_rows[r["id"]] = r
        queries.append(f"{abx}:{len(rows)}")
        print(f"{abx:32s} {len(rows):7d} records", file=sys.stderr)

    rows = list(all_rows.values())
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (",".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if new:
            w.writerow(["date_utc", "file", "query", "n_rows", "sha256"])
        w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    OUT.relative_to(ROOT), f"genome_amr taxon_id={TAXON_ID}; " + "; ".join(queries),
                    len(rows), sha])

    print(f"\nRecords: {len(rows)}  Genomes: {len({r.get('genome_id') for r in rows})}")
    for field in ("evidence", "laboratory_typing_method", "resistant_phenotype", "testing_standard"):
        print(f"\n{field}:")
        for value, n in Counter(r.get(field) for r in rows).most_common(15):
            print(f"  {n:7d}  {value}")
    print("\nantibiotic x phenotype:")
    for (a, p), n in sorted(Counter((r.get("antibiotic"), r.get("resistant_phenotype")) for r in rows).items()):
        print(f"  {n:7d}  {a} | {p}")


if __name__ == "__main__":
    main()
