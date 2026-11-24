#!/usr/bin/env python3
"""Isolate-level inference: cluster bootstrap intervals and cluster permutation tests.

    python scripts/kumelenme.py --ref ~/amr_gizli/reference_phenotypes.tsv \
        --key ~/amr_gizli/blinding_key.tsv \
        --pred claude=runs/claude/rep1/predictions.tsv \
        --pred gpt=runs/gpt/rep1/predictions.tsv \
        --pred ref=runs/amrfinderplus/predictions.tsv

Why this exists
---------------
`metrics.py` computes Wilson intervals over isolate-antibiotic pairs and an exact
McNemar test over discordant pairs, both of which treat the pairs as independent draws.
They are not: 552 scored pairs come from 118 isolates, a mean of 4.68 pairs each, and
the correlation within an isolate is the dominant structure rather than a nuisance — an
isolate carrying an ESBL plus QRDR substitutions drives correlated errors across
ampicillin, cefotaxime and ciprofloxacin at once. Declaring the pair to be the unit of
analysis, as the methods do, does not make it one.

The consequence is one-directional and worth stating precisely, because it decides
which of the manuscript's claims move:

  * The FDA verdicts do not change. Clustering widens intervals, and Claude's very
    major error upper limit is already far above the 7.5% line, so widening moves it
    further away. The major error criterion is on a point estimate, which clustering
    does not shift.
  * The categorical agreement intervals are too narrow as published and must not be
    quoted to two decimals.
  * The arm comparisons are where it bites. An exact McNemar p rests on the discordant
    pairs being independent; if they concentrate in few isolates, the p is optimistic.

So this script reports, for every estimate, the Wilson interval beside a bootstrap
interval that resamples isolates, and for every comparison the number of distinct
isolates behind the discordant pairs, a cluster-level permutation p, and the paired
difference with a cluster interval — because a difference with an interval says what
the data exclude, which a bare p-value does not.

Method
------
Cluster bootstrap: isolates are resampled with replacement, all of a drawn isolate's
pairs entering together, and the statistic is recomputed on each resample; the interval
is the 2.5th and 97.5th percentile. A resample in which a rate is undefined (no
reference-resistant pair drawn, say) is skipped and the number skipped is reported.

Cluster permutation for a pair of arms: the two arms scored the same pairs, so the
quantity is paired. For each isolate the difference in the number of correct calls is
taken over all of its pairs, and the null is built by flipping the sign of each
isolate's difference independently, which is the permutation the clustered paired
design allows. Where few isolates differ the null is enumerated exactly; otherwise it
is sampled. The exact McNemar p is reported alongside, labelled as the uncorrected one,
so the two can be compared rather than silently swapped.

ICC is the one-way random-effects estimator for unequal cluster sizes, reported for the
correctness indicator so a reader can see the design effect the intervals embody.
"""
from __future__ import annotations

import argparse
import itertools
import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest

SEED = 20261125
BOOT = 2000
PERM = 20000
EXACT_MAX = 20          # enumerate 2**k sign flips up to this many differing isolates


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def rates(df: pd.DataFrame) -> dict[str, float]:
    """CA, VME, ME on one set of pairs. A no-call counts against agreement but is not a
    very major error, which is how metrics.py scores it; the two must agree or the
    bootstrap interval would not belong to the published point estimate."""
    n = len(df)
    if n == 0:
        return {}
    called = df["prediction"].isin(["S", "R"])
    correct = called & (df["prediction"] == df["pheno"])
    nR = int((df["pheno"] == "R").sum())
    nS = int((df["pheno"] == "S").sum())
    vme = int(((df["pheno"] == "R") & (df["prediction"] == "S")).sum())
    me = int(((df["pheno"] == "S") & (df["prediction"] == "R")).sum())
    out = {"ca": correct.sum() / n}
    out["vme"] = vme / nR if nR else float("nan")
    out["me"] = me / nS if nS else float("nan")
    return out


def cluster_boot(df: pd.DataFrame, stat, rng) -> tuple[float, float, int]:
    """Percentile interval from resampling isolates, not pairs."""
    groups = [g for _, g in df.groupby("isolate_id", sort=True)]
    k = len(groups)
    vals, skipped = [], 0
    for _ in range(BOOT):
        pick = rng.integers(0, k, size=k)
        s = stat(pd.concat([groups[i] for i in pick], ignore_index=True))
        if s is None or not np.isfinite(s):
            skipped += 1
            continue
        vals.append(s)
    if not vals:
        return float("nan"), float("nan"), skipped
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), skipped


def sign_flip(diffs: np.ndarray, rng) -> tuple[float, int, str]:
    """Two-sided p for the paired difference, flipping whole isolates.

    Each isolate contributes one number: how many more calls arm A got right than arm B
    across that isolate's pairs. Flipping the sign of an isolate's whole contribution is
    the exchange the design permits; flipping individual pairs would assume the
    independence this script exists to avoid.
    """
    nz = diffs[diffs != 0]
    obs = float(diffs.sum())
    if nz.size == 0:
        return 1.0, 0, "no isolate differs"
    if nz.size <= EXACT_MAX:
        hits = sum(1 for signs in itertools.product((-1, 1), repeat=nz.size)
                   if abs(float(np.dot(signs, nz))) >= abs(obs) - 1e-12)
        return hits / (2 ** nz.size), int(nz.size), "exact over sign flips"
    draws = rng.choice((-1.0, 1.0), size=(PERM, nz.size))
    null = draws @ nz
    p = (np.abs(null) >= abs(obs) - 1e-12).sum() / PERM
    return float(max(p, 1.0 / PERM)), int(nz.size), f"sampled, {PERM} draws"


def icc_oneway(df: pd.DataFrame, col: str) -> float:
    """One-way random-effects ICC for unequal cluster sizes (ANOVA estimator)."""
    g = df.groupby("isolate_id")[col]
    ni = g.size().to_numpy(dtype=float)
    mi = g.mean().to_numpy(dtype=float)
    k, N = len(ni), ni.sum()
    if k < 2 or N <= k:
        return float("nan")
    grand = df[col].mean()
    msb = float((ni * (mi - grand) ** 2).sum() / (k - 1))
    ssw = float(sum(((sub - sub.mean()) ** 2).sum() for _, sub in g))
    msw = ssw / (N - k)
    n0 = (N - (ni ** 2).sum() / N) / (k - 1)
    den = msb + (n0 - 1) * msw
    return float((msb - msw) / den) if den else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--key", required=True, help="needed to map genome_id to isolate_id")
    ap.add_argument("--pred", action="append", required=True, help="arm=path.tsv")
    ap.add_argument("--out", default="results/kumelenme.tsv")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)

    ref = pd.read_csv(a.ref, sep="\t", dtype=str)
    key = pd.read_csv(a.key, sep="\t", dtype=str)
    before = len(ref)
    ref = ref[ref["genome_id"].isin(set(key["genome_id"]))]
    if before != len(ref):
        print(f"dropped {before - len(ref)} reference pairs whose isolate is not in the "
              f"blinding key (selected, then failed QC, so never shown to any agent)")
    ref = ref[ref["pheno"].isin(["S", "R"])]

    arms: dict[str, pd.DataFrame] = {}
    for spec in a.pred:
        if "=" not in spec:
            sys.exit(f"--pred arm=path bekleniyor: {spec}")
        name, path = spec.split("=", 1)
        p = pd.read_csv(path, sep="\t", dtype=str)
        if "isolate_id" in p.columns:
            p = p.merge(key, on="isolate_id", how="left")
        m = ref.merge(p[["genome_id", "abx", "prediction"]], on=["genome_id", "abx"],
                      how="left")
        m["prediction"] = m["prediction"].fillna("NA")
        m = m.merge(key, on="genome_id", how="left", suffixes=("", "_k"))
        if m["isolate_id"].isna().any():
            sys.exit(f"{name}: bazi ciftler izolat kimligine baglanamadi; durduruldu")
        m["correct"] = (m["prediction"].isin(["S", "R"])
                        & (m["prediction"] == m["pheno"])).astype(int)
        arms[name] = m

    rows = []
    n_iso = arms[next(iter(arms))]["isolate_id"].nunique()
    n_pairs = len(arms[next(iter(arms))])
    print(f"\n{n_pairs} cift, {n_iso} izolat, izolat basina ortalama "
          f"{n_pairs / n_iso:.2f} cift")

    for name, m in arms.items():
        pt = rates(m)
        icc = icc_oneway(m, "correct")
        print(f"\n=== {name}   ICC(dogruluk) = {icc:.3f}")
        for label in ("ca", "vme", "me"):
            if label == "ca":
                k, n = int(m["correct"].sum()), len(m)
            elif label == "vme":
                sub = m[m["pheno"] == "R"]
                k, n = int((sub["prediction"] == "S").sum()), len(sub)
            else:
                sub = m[m["pheno"] == "S"]
                k, n = int((sub["prediction"] == "R").sum()), len(sub)
            _, wlo, whi = wilson(k, n)
            blo, bhi, skipped = cluster_boot(m, lambda d, l=label: rates(d).get(l), rng)
            widen = ((bhi - blo) / (whi - wlo)) if (whi - wlo) else float("nan")
            print(f"  {label.upper():3} {pt[label]*100:5.1f}%  "
                  f"Wilson [{wlo*100:.1f}-{whi*100:.1f}]  "
                  f"izolat bootstrap [{blo*100:.1f}-{bhi*100:.1f}]  "
                  f"genisleme x{widen:.2f}" + (f"  atlanan {skipped}" if skipped else ""))
            rows.append({"arm": name, "metric": label, "k": k, "n": n,
                         "estimate": pt[label], "wilson_lo": wlo, "wilson_hi": whi,
                         "cluster_lo": blo, "cluster_hi": bhi,
                         "ci_widening": widen, "boot_skipped": skipped,
                         "icc_correct": icc, "n_isolates": n_iso})

    print("\n=== kol karsilastirmalari (izolat duzeyinde)")
    for x, y in itertools.combinations(arms, 2):
        A, B = arms[x], arms[y]
        j = A[["genome_id", "abx", "isolate_id", "correct"]].merge(
            B[["genome_id", "abx", "correct"]], on=["genome_id", "abx"],
            suffixes=("_a", "_b"))
        disc = j[j["correct_a"] != j["correct_b"]]
        b = int((disc["correct_a"] == 1).sum())
        c = int((disc["correct_b"] == 1).sum())
        mcn = binomtest(b, b + c, 0.5).pvalue if (b + c) else 1.0
        per_iso = (j.groupby("isolate_id")
                     .apply(lambda d: d["correct_a"].sum() - d["correct_b"].sum(),
                            include_groups=False)
                     .to_numpy(dtype=float))
        p, k_iso, how = sign_flip(per_iso, rng)
        d_obs = j["correct_a"].mean() - j["correct_b"].mean()
        dlo, dhi, _ = cluster_boot(
            j, lambda d: d["correct_a"].mean() - d["correct_b"].mean(), rng)
        print(f"\n  {x} - {y}")
        print(f"    uyusmayan cift {len(disc)} ({b} / {c}), "
              f"{disc['isolate_id'].nunique()} ayri izolattan")
        print(f"    McNemar tam (duzeltilmemis, bagimsizlik varsayar) p = {mcn:.3g}")
        print(f"    izolat isaret testi p = {p:.3g}  ({k_iso} izolat farkli, {how})")
        print(f"    esli fark {d_obs*100:+.2f} puan, izolat bootstrap "
              f"[{dlo*100:+.2f}, {dhi*100:+.2f}]")
        rows.append({"arm": f"{x}_vs_{y}", "metric": "paired_difference",
                     "k": b, "n": b + c, "estimate": d_obs,
                     "cluster_lo": dlo, "cluster_hi": dhi,
                     "mcnemar_exact_p": mcn, "cluster_permutation_p": p,
                     "isolates_differing": k_iso, "permutation_mode": how,
                     "discordant_pairs": len(disc),
                     "isolates_in_discordant": int(disc["isolate_id"].nunique()),
                     "n_isolates": n_iso})

    out = pd.DataFrame(rows)
    out.to_csv(a.out, sep="\t", index=False)
    print(f"\nyazildi: {a.out}   (seed {SEED}, {BOOT} bootstrap)")


if __name__ == "__main__":
    main()
