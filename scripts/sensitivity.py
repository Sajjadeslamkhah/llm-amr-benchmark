#!/usr/bin/env python3
"""Pre-specified sensitivity analyses (PROTOCOL.md section 10).

    python scripts/sensitivity.py \
        --ref ~/amr_gizli/reference_phenotypes.tsv \
        --key ~/amr_gizli/blinding_key.tsv \
        --pred claude=runs/claude/rep1/predictions.tsv \
        --pred gpt=runs/gpt/rep1/predictions.tsv \
        --pred ref=runs/amrfinderplus/predictions.tsv \
        --out results/sensitivity

  (i)  intermediate phenotypes counted as non-susceptible
  (iv) stratified by the testing standard recorded for the phenotype

Analysis (iii), reinterpreting phenotypes from MIC values with EUCAST v16.1, is
not implemented here: it needs the breakpoint for each of the six antibiotics
read off the current table, and a breakpoint entered from memory would be the
one thing this study cannot afford. This script reports how many pairs carry a
usable MIC, so the work can be scoped before anyone opens the table.

The phenotype metadata lives in the raw download, not in the reference file, so
the raw records are joined back here. The raw file is the one 01_fetch_amr.py
wrote, with its checksum in data/MANIFEST.tsv.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd

_spec = importlib.util.spec_from_file_location("m", Path(__file__).with_name("metrics.py"))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)

RAW = Path("data/raw/bvbrc_genome_amr_ecoli.tsv")
NONSUSC = {"Resistant": "R", "Intermediate": "R", "Susceptible": "S"}


def load_raw(abx_of_interest: set[str]) -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(f"{RAW} not found. It is the merged download from "
                         f"01_fetch_amr.py and is needed for the phenotype metadata.")
    df = pd.read_csv(RAW, sep="\t", dtype=str, low_memory=False)
    df["abx"] = df["antibiotic"].str.strip().str.lower()
    df.loc[df["abx"] == "sulfamethoxazole/trimethoprim", "abx"] = "trimethoprim/sulfamethoxazole"
    return df[df["abx"].isin(abx_of_interest)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--pred", action="append", required=True, help="arm=path.tsv")
    ap.add_argument("--out", default="results/sensitivity")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    key = pd.read_csv(a.key, sep="\t", dtype=str)
    ref_all = pd.read_csv(a.ref, sep="\t", dtype=str)
    ref_all = ref_all[ref_all["genome_id"].isin(set(key["genome_id"]))]
    abx = set(ref_all["abx"].unique())

    preds = {}
    for spec in a.pred:
        arm, path = spec.split("=", 1)
        preds[arm] = _m.load_pred(path, key)

    def table(ref: pd.DataFrame, label: str) -> list[dict]:
        rows = []
        for arm, p in preds.items():
            merged = ref.merge(p, on=["genome_id", "abx"], how="left")
            rows.append({"analysis": label, "arm": arm, "abx": "ALL",
                         **_m.evaluate(merged, True)})
        return rows

    rows: list[dict] = []

    # (i) intermediate counted as non-susceptible. The primary analysis keeps only S
    # and R; this adds the intermediate pairs back as R.
    raw = load_raw(abx)
    lab = raw[raw["evidence"] == "Laboratory Method"]
    inter = lab[lab["resistant_phenotype"] == "Intermediate"][["genome_id", "abx"]].drop_duplicates()
    inter = inter[inter["genome_id"].isin(set(key["genome_id"]))]
    print(f"(i) intermediate pairs among the scored isolates: {len(inter)}")
    if len(inter) == 0:
        print("    none, so this analysis cannot differ from the primary one")
    ref_i = pd.concat([ref_all[ref_all["pheno"].isin(["S", "R"])],
                       inter.assign(pheno="R")], ignore_index=True).drop_duplicates(
                           subset=["genome_id", "abx"], keep="first")
    rows += table(ref_i, "i_intermediate_as_nonsusceptible")

    # (iv) stratified by the testing standard recorded for the phenotype. Standards and
    # their versions differ between submitting studies, and a disagreement that follows
    # the standard rather than the genotype is a property of the reference, not the agent.
    std = (lab[["genome_id", "abx", "testing_standard"]]
           .fillna({"testing_standard": "not stated"})
           .drop_duplicates(subset=["genome_id", "abx"], keep="first"))
    ref_s = ref_all[ref_all["pheno"].isin(["S", "R"])].merge(std, on=["genome_id", "abx"], how="left")
    # BV-BRC records the standard inconsistently: CLSI and clsi, EUCAST and eucast, and
    # both names together in either order. Left as written, one stratum was split into
    # four and three of the pieces fell below the reporting threshold.
    def norm_std(v: str) -> str:
        t = (v or "").strip().upper().replace(" ", "")
        if not t:
            return "not stated"
        names = {n for n in ("EUCAST", "CLSI") if n in t}
        if names == {"EUCAST", "CLSI"}:
            return "both named"
        if names:
            return names.pop()
        return v.strip()

    ref_s["testing_standard"] = ref_s["testing_standard"].fillna("").map(norm_std)
    print("\n(iv) pairs per recorded testing standard:")
    for s, n in ref_s["testing_standard"].value_counts().items():
        print(f"    {s}: {n}")
    # The strata are not matched on antibiotic, and a difference between them could
    # follow from which drugs fell into each one rather than from the standard. Printed
    # so the comparison is read with that in view.
    comp = (ref_s.pivot_table(index="abx", columns="testing_standard", values="genome_id",
                              aggfunc="count", fill_value=0))
    print("\n     antibiotic composition of each stratum:")
    print(comp.to_string().replace("\n", "\n     "))
    rfrac = (ref_s.assign(isR=ref_s["pheno"].eq("R"))
             .groupby("testing_standard")["isR"].mean())
    print("\n     resistant share of each stratum: " +
          ", ".join(f"{k}={v:.2f}" for k, v in rfrac.items()))
    comp.to_csv(out / "standard_composition.tsv", sep="\t")

    for s, g in ref_s.groupby("testing_standard"):
        if len(g) < 20:
            print(f"    skipped '{s}' ({len(g)} pairs, too few to report)")
            continue
        rows += table(g.drop(columns=["testing_standard"]), f"iv_standard_{s}")

    # (iii) scoping only: how many pairs carry an MIC that could be reinterpreted.
    mic = lab[(lab["measurement_unit"].fillna("").str.lower().str.contains("mg/l|ug/ml|µg/ml"))
              & lab["measurement_value"].notna()]
    mic = mic[mic["genome_id"].isin(set(key["genome_id"]))][["genome_id", "abx"]].drop_duplicates()
    print(f"\n(iii) pairs with a usable MIC value: {len(mic)} of {len(ref_all)}")
    print("    not reinterpreted here: each breakpoint must be read off the current")
    print("    EUCAST table, not entered from memory")

    df = pd.DataFrame(rows)
    df.to_csv(out / "sensitivity.tsv", sep="\t", index=False)
    cols = ["analysis", "arm", "n_pairs", "CA", "VME", "ME", "fda_all_met"]
    print("\n" + df[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\n{out / 'sensitivity.tsv'}")


if __name__ == "__main__":
    main()
