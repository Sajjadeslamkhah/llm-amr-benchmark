#!/usr/bin/env python3
"""Run-to-run reproducibility on the 40-isolate subset (PROTOCOL.md sections 8-9).

    python scripts/reproducibility.py --arm claude --arm gpt \
        --ref ~/amr_gizli/reference_phenotypes.tsv \
        --key ~/amr_gizli/blinding_key.tsv \
        --out results/reproducibility.tsv

For each arm, three replicates on the same 40 isolates: replicate 1 is the
corresponding part of the full run, replicates 2 and 3 are separate runs. Two
numbers per arm, both pre-registered:

  identical   the proportion of isolate-antibiotic pairs given the same call in
              all three replicates
  fleiss      Fleiss' kappa across the three replicates

A no-call is a category of its own here, not an error: the question is whether a
run repeats itself, and an agent that abstains on the same pair every time is
reproducible on that pair. Accuracy is metrics.py's question, not this one.

The script refuses to report a number when a replicate is short, because kappa
computed over whichever pairs happen to be present would look like a result.
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from pathlib import Path

import pandas as pd

import importlib.util

_spec = importlib.util.spec_from_file_location("m", Path(__file__).with_name("metrics.py"))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)


def read_tsv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def calls(path: Path) -> dict[tuple[str, str], str]:
    out = {}
    for r in read_tsv(path):
        k = ((r.get("isolate_id") or "").strip(), (r.get("antibiotic") or "").strip())
        v = (r.get("prediction") or "").strip().upper()
        out[k] = v if v in ("S", "R") else "NA"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--reps", default="1,2,3")
    ap.add_argument("--subset", default="data/selection/reproducibility_subset.txt")
    ap.add_argument("--ref")
    ap.add_argument("--key")
    ap.add_argument("--out", default="results/reproducibility.tsv")
    a = ap.parse_args()

    subset = [l.strip() for l in Path(a.subset).read_text().splitlines() if l.strip()]
    reps = [r.strip() for r in a.reps.split(",")]

    # The pairs to judge: the subset's isolates, for the antibiotics that have a
    # laboratory phenotype. Without the reference the full grid is used instead, which
    # would include pairs no analysis ever scores.
    pairs: set[tuple[str, str]] | None = None
    if a.ref and a.key:
        iso_of = {r["genome_id"]: r["isolate_id"] for r in read_tsv(Path(a.key))}
        pairs = {(iso_of[r["genome_id"]], r["abx"]) for r in read_tsv(Path(a.ref))
                 if r["genome_id"] in iso_of and r.get("pheno") in ("S", "R")}
        pairs = {p for p in pairs if p[0] in subset}

    rows = []
    problems = []
    for arm in a.arm:
        per_rep = {}
        for rep in reps:
            f = Path(a.runs) / arm / f"rep{rep}" / "predictions.tsv"
            if not f.exists():
                problems.append(f"{arm} rep{rep}: predictions.tsv yok")
                continue
            c = calls(f)
            per_rep[rep] = {k: v for k, v in c.items() if k[0] in subset}
        if len(per_rep) < len(reps):
            continue

        common = set.intersection(*(set(v) for v in per_rep.values()))
        if pairs is not None:
            common &= pairs
        expected = len(pairs & {(i, b) for i in subset for b in {p[1] for p in pairs}}) if pairs else None
        if pairs is not None and len(common) < len(pairs):
            problems.append(f"{arm}: {len(common)} of {len(pairs)} scorable subset pairs present "
                            f"in all {len(reps)} replicates")

        same = sum(1 for k in common if len({per_rep[r][k] for r in reps}) == 1)
        cats = ["S", "R", "NA"]
        table = pd.DataFrame(
            [[sum(1 for r in reps if per_rep[r][k] == c) for c in cats] for k in sorted(common)],
            columns=cats)
        kappa = _m.fleiss_kappa(table) if len(table) else float("nan")
        p, lo, hi = _m.wilson(same, len(common)) if common else (float("nan"),) * 3

        row = {"arm": arm, "replicates": len(reps), "pairs": len(common),
               "identical_all": same, "identical_prop": round(p, 4),
               "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
               "fleiss_kappa": round(kappa, 4) if kappa == kappa else ""}
        # which pairs of replicates disagree, so a single odd run is visible
        for x, y in combinations(reps, 2):
            d = sum(1 for k in common if per_rep[x][k] != per_rep[y][k])
            row[f"disagree_{x}v{y}"] = d
        rows.append(row)

    if problems:
        print("EKSIK:")
        for p_ in problems:
            print("  " + p_)
    if not rows:
        raise SystemExit(
            "\nNo arm has all replicates complete. Not reporting a number: a kappa computed\n"
            "over whichever pairs happen to be present would read as a result. Finish the\n"
            "replicates (bash go.sh tekrar) and run this again.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, sep="\t", index=False)
    for r in rows:
        print(f"{r['arm']}: {r['pairs']} pairs over {r['replicates']} replicates")
        print(f"  identical in all: {r['identical_all']}/{r['pairs']} = {r['identical_prop']:.3f} "
              f"[{r['ci_lo']:.3f}-{r['ci_hi']:.3f}]")
        print(f"  Fleiss kappa    : {r['fleiss_kappa']}")
        print("  pairwise disagreements: " +
              ", ".join(f"{k.replace('disagree_', '')}={v}" for k, v in r.items()
                        if k.startswith("disagree_")))
    print(f"\n{out}")
    if problems:
        print("Yukaridaki eksikler giderilmeden bu sayilar makaleye girmez.")


if __name__ == "__main__":
    main()
