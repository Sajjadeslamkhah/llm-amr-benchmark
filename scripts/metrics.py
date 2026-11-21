#!/usr/bin/env python3
"""Compute every number reported in the manuscript (PROTOCOL.md sections 9-10).

    python scripts/metrics.py --ref data/selection/reference_phenotypes.tsv \
        --key data/selection/blinding_key.tsv \
        --pred claude=runs/claude/rep1/predictions.tsv \
        --pred gemini=runs/gemini/rep1/predictions.tsv \
        --pred gpt=runs/gpt/rep1/predictions.tsv \
        --pred ref=runs/amrfinderplus/predictions.tsv \
        --out results/

No value in the manuscript is typed by hand. All come from this script's output.
"""
import argparse
import itertools
import math
from pathlib import Path

import pandas as pd
from scipy.stats import binomtest


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def evaluate(df: pd.DataFrame, nocall_as_error: bool = True) -> dict:
    """df columns: pheno (reference S/R), prediction (S/R/NA)."""
    d = df[df["pheno"].isin(["S", "R"])].copy()
    d["prediction"] = d["prediction"].fillna("NA").str.upper()
    if not nocall_as_error:
        d = d[d["prediction"].isin(["S", "R"])]
    n = len(d)
    agree = int((d["prediction"] == d["pheno"]).sum())
    nR = int((d["pheno"] == "R").sum())
    nS = int((d["pheno"] == "S").sum())
    vme = int(((d["pheno"] == "R") & (d["prediction"] == "S")).sum())
    me = int(((d["pheno"] == "S") & (d["prediction"] == "R")).sum())
    nocall = int((~d["prediction"].isin(["S", "R"])).sum())
    out = {"n_pairs": n, "n_ref_R": nR, "n_ref_S": nS, "no_call": nocall}
    for name, k, m in (("CA", agree, n), ("VME", vme, nR), ("ME", me, nS)):
        p, lo, hi = wilson(k, m)
        out.update({f"{name}_k": k, f"{name}_n": m, name: p, f"{name}_lo": lo, f"{name}_hi": hi})
    return out


def mcnemar_exact(correct_a: pd.Series, correct_b: pd.Series) -> tuple[int, int, float]:
    b = int((correct_a & ~correct_b).sum())
    c = int((~correct_a & correct_b).sum())
    p = 1.0 if b + c == 0 else binomtest(b, b + c, 0.5).pvalue
    return b, c, p


def holm(pvals: list[float]) -> list[float]:
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def fleiss_kappa(table: pd.DataFrame) -> float:
    """table: rows = items, columns = categories, values = number of raters choosing it."""
    n = table.sum(axis=1).iloc[0]
    N = len(table)
    p_j = table.sum(axis=0) / (N * n)
    P_i = ((table ** 2).sum(axis=1) - n) / (n * (n - 1))
    P_bar, P_e = P_i.mean(), (p_j ** 2).sum()
    return float("nan") if P_e == 1 else (P_bar - P_e) / (1 - P_e)


def load_pred(path: str, key: pd.DataFrame | None) -> pd.DataFrame:
    p = pd.read_csv(path, sep="\t", dtype=str)
    p["antibiotic"] = p["antibiotic"].str.strip().str.lower()
    if key is not None and "isolate_id" in p.columns:
        p = p.merge(key, on="isolate_id", how="left")
    return p.rename(columns={"antibiotic": "abx"})[["genome_id", "abx", "prediction"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--key")
    ap.add_argument("--pred", action="append", required=True, help="arm=path.tsv")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ref = pd.read_csv(a.ref, sep="\t", dtype=str)
    key = pd.read_csv(a.key, sep="\t", dtype=str) if a.key else None

    rows, correct, called = [], {}, {}
    for spec in a.pred:
        arm, path = spec.split("=", 1)
        m = ref.merge(load_pred(path, key), on=["genome_id", "abx"], how="left")
        for label, nc in (("primary", True), ("nocall_excluded", False)):
            rows.append({"arm": arm, "analysis": label, "abx": "ALL", **evaluate(m, nc)})
            for abx, g in m.groupby("abx"):
                rows.append({"arm": arm, "analysis": label, "abx": abx, **evaluate(g, nc)})
        mm = m[m["pheno"].isin(["S", "R"])].set_index(["genome_id", "abx"])
        pr = mm["prediction"].fillna("NA").str.upper()
        correct[arm] = pr == mm["pheno"]
        called[arm] = pr.isin(["S", "R"])
    pd.DataFrame(rows).to_csv(out / "performance.tsv", sep="\t", index=False)

    # Two comparisons. "primary" scores a no-call as an error, as pre-registered.
    # "both_called" restricts to the pairs on which BOTH arms made a call, which is the
    # only comparison of accuracy as such: without it, an arm that declines more often
    # looks less accurate when it may simply be more cautious. GPT declined 24 calls to
    # Claude's 8 and states abstention as its rule for uncertain genotypes, so the
    # primary comparison between them is in part a comparison of willingness to call.
    comps = []
    for x, y in itertools.combinations(correct, 2):
        b, c, p = mcnemar_exact(correct[x], correct[y].reindex(correct[x].index, fill_value=False))
        comps.append({"arm_a": x, "arm_b": y, "analysis": "primary",
                      "a_only_correct": b, "b_only_correct": c, "p": p})
        shared = called[x] & called[y].reindex(called[x].index, fill_value=False)
        if shared.any():
            cx = correct[x][shared]
            cy = correct[y].reindex(cx.index, fill_value=False)
            b2, c2, p2 = mcnemar_exact(cx, cy)
            comps.append({"arm_a": x, "arm_b": y, "analysis": "both_called",
                          "a_only_correct": b2, "b_only_correct": c2, "p": p2,
                          "n_pairs": int(shared.sum())})
    if comps:
        for row, padj in zip(comps, holm([r["p"] for r in comps])):
            row["p_holm"] = padj
        pd.DataFrame(comps).to_csv(out / "mcnemar.tsv", sep="\t", index=False)
    print(pd.DataFrame(rows).query("abx == 'ALL'").to_string(index=False))


if __name__ == "__main__":
    main()
