#!/usr/bin/env python3
"""Download the selected assemblies, apply assembly QC and anonymise them.

    python scripts/03_fetch_genomes.py

Inputs   data/selection/selected_isolates.tsv
Outputs  data/genomes_raw/<genome_id>.fasta
         sandbox/data/genomes/ISO_###.fasta    (the ONLY genome files agents see)
         sandbox/data/antibiotics.txt
         data/selection/blinding_key.tsv       (KEEP OUT of the agent sandbox)
         data/selection/qc.tsv

QC (PROTOCOL.md section 4): total length 4.5-6.0 Mb and <= 500 contigs.

The FASTA download uses the BV-BRC genome_sequence endpoint. Verify on the
first run that the returned file is valid FASTA for one genome before
running the full list.
"""
import random
import time
from pathlib import Path

import pandas as pd
import requests

SEED = 20261114
API = "https://www.bv-brc.org/api/genome_sequence/"
ROOT = Path(__file__).resolve().parent.parent
SEL = ROOT / "data" / "selection"
RAW = ROOT / "data" / "genomes_raw"
SANDBOX = ROOT / "sandbox" / "data"


def download(genome_id: str) -> Path:
    out = RAW / f"{genome_id}.fasta"
    if out.exists() and out.stat().st_size > 0:
        return out
    url = f"{API}?eq(genome_id,{genome_id})&limit(25000)&http_accept=application/dna+fasta"
    for attempt in range(5):
        r = requests.get(url, timeout=300)
        if r.status_code == 200 and r.text.startswith(">"):
            out.write_text(r.text)
            return out
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed for {genome_id}: HTTP {r.status_code}")


def read_fasta(path: Path) -> list[str]:
    seqs, cur = [], []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur)); cur = []
        else:
            cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    return seqs


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (SANDBOX / "genomes").mkdir(parents=True, exist_ok=True)
    ids = pd.read_csv(SEL / "selected_isolates.tsv", sep="\t", dtype=str)["genome_id"].tolist()
    ref = pd.read_csv(SEL / "reference_phenotypes.tsv", sep="\t", dtype=str)

    qc_rows = []
    for gid in ids:
        seqs = read_fasta(download(gid))
        length = sum(map(len, seqs))
        passed = 4_500_000 <= length <= 6_000_000 and len(seqs) <= 500
        qc_rows.append({"genome_id": gid, "length": length, "n_contigs": len(seqs), "qc_pass": passed})
        print(gid, length, len(seqs), "PASS" if passed else "FAIL")
    qc = pd.DataFrame(qc_rows)
    qc.to_csv(SEL / "qc.tsv", sep="\t", index=False)

    kept = qc.loc[qc["qc_pass"], "genome_id"].tolist()
    rng = random.Random(SEED)
    codes = [f"ISO_{i:03d}" for i in range(1, len(kept) + 1)]
    rng.shuffle(codes)
    key = pd.DataFrame({"isolate_id": codes, "genome_id": kept})
    key.to_csv(SEL / "blinding_key.tsv", sep="\t", index=False)

    for code, gid in zip(codes, kept):
        seqs = read_fasta(RAW / f"{gid}.fasta")
        with (SANDBOX / "genomes" / f"{code}.fasta").open("w") as fh:
            for i, s in enumerate(seqs, 1):
                fh.write(f">contig_{i}\n")
                for j in range(0, len(s), 80):
                    fh.write(s[j:j + 80] + "\n")

    abx = sorted(ref.loc[ref["genome_id"].isin(kept), "abx"].unique())
    (SANDBOX / "antibiotics.txt").write_text("\n".join(abx) + "\n")
    print(f"QC pass: {len(kept)}/{len(ids)}; antibiotics: {abx}")


if __name__ == "__main__":
    main()
