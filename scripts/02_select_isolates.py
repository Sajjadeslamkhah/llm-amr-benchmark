#!/usr/bin/env python3
"""Apply the PROTOCOL.md eligibility, antibiotic and sampling rules (sections 4-6).

    python scripts/02_select_isolates.py --evidence "<exact laboratory evidence string>"

Inputs   data/raw/bvbrc_genome_amr_ecoli.tsv
Outputs  data/selection/antibiotic_counts.tsv
         data/selection/selected_isolates.tsv
         data/selection/reference_phenotypes.tsv  (KEEP OUT of the agent sandbox)

Selection uses phenotype labels only and never model output.
Assembly QC is applied later by 03_fetch_genomes.py.
"""
import argparse
import random
from collections import defaultdict
from pathlib import Path

import pandas as pd

SEED = 20261114
CANDIDATES = [  # priority order, PROTOCOL.md section 5
    "ampicillin", "cefotaxime", "ceftriaxone", "ceftazidime",
    "meropenem", "ciprofloxacin", "gentamicin", "trimethoprim/sulfamethoxazole",
]
MIN_PER_CLASS = 20
MAX_ABX = 6
N_ISOLATES = 120

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "bvbrc_genome_amr_ecoli.tsv"
OUTDIR = ROOT / "data" / "selection"

PHENO_MAP = {"susceptible": "S", "resistant": "R", "intermediate": "I"}


def normalise_abx(name: str) -> str:
    s = str(name).strip().lower().replace("-", "/").replace(" ", "")
    aliases = {"trimethoprim/sulfamethoxazole": "trimethoprim/sulfamethoxazole",
               "sulfamethoxazole/trimethoprim": "trimethoprim/sulfamethoxazole",
               "co/trimoxazole": "trimethoprim/sulfamethoxazole"}
    return aliases.get(s, s)


def load(evidence: str) -> pd.DataFrame:
    df = pd.read_csv(RAW, sep="\t", dtype=str)
    df = df[df["evidence"].str.strip().str.lower() == evidence.strip().lower()]
    df = df[df["genome_name"].str.startswith("Escherichia coli", na=False)]
    df["abx"] = df["antibiotic"].map(normalise_abx)
    df["pheno"] = df["resistant_phenotype"].str.strip().str.lower().map(PHENO_MAP)
    df = df[df["abx"].isin(CANDIDATES) & df["pheno"].notna()]
    # one call per isolate-antibiotic pair; drop pairs with conflicting S/R records
    calls = df.groupby(["genome_id", "abx"])["pheno"].agg(lambda x: set(x))
    calls = calls[calls.map(lambda s: not {"S", "R"} <= s)]
    calls = calls.map(lambda s: "R" if "R" in s else ("S" if "S" in s else "I"))
    return calls.rename("pheno").reset_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True,
                    help="exact `evidence` value for laboratory-derived phenotypes")
    args = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    calls = load(args.evidence)
    sr = calls[calls["pheno"].isin(["S", "R"])]
    counts = sr.pivot_table(index="abx", columns="pheno", values="genome_id",
                            aggfunc="count", fill_value=0).reindex(CANDIDATES, fill_value=0)
    counts["eligible"] = (counts.get("R", 0) >= MIN_PER_CLASS) & (counts.get("S", 0) >= MIN_PER_CLASS)
    counts.to_csv(OUTDIR / "antibiotic_counts.tsv", sep="\t")
    abx = [a for a in CANDIDATES if counts.loc[a, "eligible"]][:MAX_ABX]
    print("Included antibiotics:", abx)
    if not abx:
        raise SystemExit("No antibiotic meets the inclusion rule.")

    sr = sr[sr["abx"].isin(abx)]
    by_genome = sr.groupby("genome_id")
    rng = random.Random(SEED)
    genomes = sorted(by_genome.groups)
    rng.shuffle(genomes)

    # Stratified greedy fill: first secure >= MIN_PER_CLASS R and S pairs per antibiotic,
    # then fill the remainder in the shuffled order. Deterministic given SEED.
    need = {(a, p): MIN_PER_CLASS for a in abx for p in ("S", "R")}
    chosen, chosen_set = [], set()
    pairs = {g: set(map(tuple, grp[["abx", "pheno"]].values)) for g, grp in by_genome}
    for key in sorted(need, key=lambda k: sum(k in pairs[g] for g in genomes)):
        for g in genomes:
            if len(chosen) >= N_ISOLATES or need[key] <= 0:
                break
            if g not in chosen_set and key in pairs[g]:
                chosen.append(g); chosen_set.add(g)
                for k in pairs[g]:
                    if k in need:
                        need[k] -= 1
    for g in genomes:
        if len(chosen) >= N_ISOLATES:
            break
        if g not in chosen_set:
            chosen.append(g); chosen_set.add(g)

    short = {k: v for k, v in need.items() if v > 0}
    if short:
        print("WARNING: strata below target (report as deviation if kept):", short)

    pd.Series(chosen, name="genome_id").to_csv(OUTDIR / "selected_isolates.tsv", sep="\t", index=False)
    ref = calls[calls["genome_id"].isin(chosen_set) & calls["abx"].isin(abx)]
    ref.to_csv(OUTDIR / "reference_phenotypes.tsv", sep="\t", index=False)
    print(f"Selected {len(chosen)} isolates, {len(ref)} isolate-antibiotic pairs")
    print(ref.pivot_table(index="abx", columns="pheno", values="genome_id", aggfunc="count", fill_value=0))


if __name__ == "__main__":
    main()
