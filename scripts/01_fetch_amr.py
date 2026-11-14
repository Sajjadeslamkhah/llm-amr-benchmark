#!/usr/bin/env python3
"""Download E. coli AMR phenotype records from the BV-BRC public API.

Run on a machine with internet access:
    python scripts/01_fetch_amr.py

Output
    data/raw/bvbrc_genome_amr_ecoli.tsv   one row per AMR record
    data/MANIFEST.tsv                     query, date, row count, sha256

After the first run, check the printed `evidence` and
`laboratory_typing_method` value counts. Then write the exact
laboratory-evidence string into PROTOCOL.md section 4 before the freeze.

API syntax follows the BV-BRC API README (RQL over HTTP GET).
Field names follow the BV-BRC `genome_amr` data type documentation.
"""
import csv
import datetime as dt
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

BASE = "https://www.bv-brc.org/api/genome_amr/"
TAXON_ID = 562  # Escherichia coli (NCBI Taxonomy)
FIELDS = [
    "id", "genome_id", "genome_name", "taxon_id", "antibiotic",
    "resistant_phenotype", "measurement", "measurement_sign",
    "measurement_value", "measurement_unit", "laboratory_typing_method",
    "laboratory_typing_platform", "testing_standard",
    "testing_standard_year", "evidence", "source", "pmid",
]
PAGE = 10000

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "bvbrc_genome_amr_ecoli.tsv"
MANIFEST = ROOT / "data" / "MANIFEST.tsv"


def fetch_page(start: int) -> list[dict]:
    query = (
        f"eq(taxon_id,{TAXON_ID})"
        f"&select({','.join(FIELDS)})"
        f"&sort(+id)"
        f"&limit({PAGE},{start})"
        f"&http_accept=application/json"
    )
    for attempt in range(5):
        r = requests.get(BASE + "?" + query, timeout=120)
        if r.status_code == 200:
            return r.json()
        print(f"HTTP {r.status_code} at start={start}, retry {attempt + 1}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return []


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows, start = [], 0
    while True:
        page = fetch_page(start)
        if not page:
            break
        rows.extend(page)
        print(f"fetched {len(rows)} records", file=sys.stderr)
        if len(page) < PAGE:
            break
        start += PAGE

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            row = {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in row.items()}
            w.writerow(row)

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if new:
            w.writerow(["date_utc", "file", "query", "n_rows", "sha256"])
        w.writerow([
            dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            OUT.relative_to(ROOT), f"genome_amr eq(taxon_id,{TAXON_ID})", len(rows), sha,
        ])

    print(f"\nRecords: {len(rows)}  Genomes: {len({r.get('genome_id') for r in rows})}")
    for field in ("evidence", "laboratory_typing_method", "resistant_phenotype", "testing_standard"):
        print(f"\n{field}:")
        for value, n in Counter(r.get(field) for r in rows).most_common(15):
            print(f"  {n:7d}  {value}")
    print("\nTop antibiotics:")
    for value, n in Counter(r.get("antibiotic") for r in rows).most_common(30):
        print(f"  {n:7d}  {value}")


if __name__ == "__main__":
    main()
