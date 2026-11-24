"""Tests for the isolate-level inference in scripts/kumelenme.py.

Each case is hand-checkable, because a statistical correction that cannot be verified by
arithmetic on a small example is not worth trusting with the manuscript's comparisons.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("kumelenme", ROOT / "scripts" / "kumelenme.py")
kum = importlib.util.module_from_spec(spec)
sys.modules["kumelenme"] = kum
spec.loader.exec_module(kum)

ABX = ["ampicillin", "cefotaxime", "ciprofloxacin", "gentamicin", "meropenem", "tmp-smx"]


def frame(wrong: set[tuple[str, str]], n_iso: int = 40) -> pd.DataFrame:
    rows = []
    for i in range(1, n_iso + 1):
        iso = f"ISO_{i:03d}"
        for abx in ABX:
            rows.append({"isolate_id": iso, "abx": abx, "pheno": "S",
                         "prediction": "R" if (iso, abx) in wrong else "S"})
    df = pd.DataFrame(rows)
    df["correct"] = (df["prediction"] == df["pheno"]).astype(int)
    return df


def diffs_by_isolate(a: pd.DataFrame, b: pd.DataFrame) -> np.ndarray:
    j = a[["isolate_id", "abx", "correct"]].merge(
        b[["isolate_id", "abx", "correct"]], on=["isolate_id", "abx"],
        suffixes=("_a", "_b"))
    return (j.groupby("isolate_id")
             .apply(lambda d: d["correct_a"].sum() - d["correct_b"].sum(),
                    include_groups=False)
             .to_numpy(dtype=float))


def test_sign_flip_matches_arithmetic_when_discordance_is_spread():
    """Three differing isolates, one pair each: 2 of the 8 sign patterns reach |3|."""
    d = diffs_by_isolate(frame(set()), frame({("ISO_001", ABX[0]),
                                              ("ISO_002", ABX[0]),
                                              ("ISO_003", ABX[0])}))
    p, k, how = kum.sign_flip(d, np.random.default_rng(0))
    assert (k, how) == (3, "exact over sign flips")
    assert p == pytest.approx(2 / 8)


def test_sign_flip_refuses_to_count_one_isolate_three_times():
    """The same three discordant pairs inside one isolate give one exchangeable unit, so
    both sign patterns reach |3| and the test cannot reject. The exact McNemar p on the
    same data is 0.25, which is the optimism this script exists to remove."""
    d = diffs_by_isolate(frame(set()), frame({("ISO_001", ABX[0]),
                                              ("ISO_001", ABX[1]),
                                              ("ISO_001", ABX[2])}))
    p, k, _ = kum.sign_flip(d, np.random.default_rng(0))
    assert k == 1
    assert p == pytest.approx(1.0)


def test_sign_flip_is_one_when_no_isolate_differs():
    p, k, how = kum.sign_flip(np.zeros(10), np.random.default_rng(0))
    assert (p, k) == (1.0, 0) and "no isolate differs" in how


def test_cluster_bootstrap_widens_only_when_errors_cluster():
    """With errors confined to whole isolates the interval must widen against Wilson;
    with errors scattered independently it must not. A correction that widens either way
    is not measuring clustering."""
    rng = np.random.default_rng(1)

    def ca(d):
        return d["correct"].mean() if len(d) else None

    scattered = frame({(f"ISO_{i:03d}", ABX[j])
                       for i, j in zip(range(1, 25), [0, 1, 2, 3, 4, 5] * 4)})
    clustered = frame({(f"ISO_{i:03d}", abx)
                       for i in range(1, 5) for abx in ABX})
    assert scattered["correct"].sum() == clustered["correct"].sum(), \
        "both arms must get the same number wrong, so only the pattern differs"

    out = {}
    for name, df in (("scattered", scattered), ("clustered", clustered)):
        k, n = int(df["correct"].sum()), len(df)
        _, wlo, whi = kum.wilson(k, n)
        blo, bhi, _ = kum.cluster_boot(df, ca, rng)
        out[name] = (bhi - blo) / (whi - wlo)

    assert out["clustered"] > out["scattered"]
    assert out["clustered"] > 1.2
    assert out["scattered"] < 1.1


def test_icc_separates_clustered_errors_from_scattered_ones():
    """ICC has to rise when the same number of errors is confined to whole isolates.

    It is not asserted to be near zero otherwise, because ICC is legitimately negative
    when within-isolate variance exceeds between-isolate variance: one error in each of
    24 isolates is more even than chance would give, and that pattern returns about
    -0.11. What the estimator has to do is order the two patterns, and put the clustered
    one well above zero.
    """
    rng = np.random.default_rng(3)
    cells = [(f"ISO_{i:03d}", abx) for i in range(1, 41) for abx in ABX]
    random_scatter = frame({cells[i] for i in
                            rng.choice(len(cells), size=24, replace=False)})
    even_scatter = frame({(f"ISO_{i:03d}", ABX[j])
                          for i, j in zip(range(1, 25), [0, 1, 2, 3, 4, 5] * 4)})
    clustered = frame({(f"ISO_{i:03d}", abx) for i in range(1, 5) for abx in ABX})

    icc_random = kum.icc_oneway(random_scatter, "correct")
    icc_even = kum.icc_oneway(even_scatter, "correct")
    icc_clustered = kum.icc_oneway(clustered, "correct")

    assert icc_clustered > 0.3
    assert icc_clustered > icc_random > icc_even
    assert icc_random < 0.1
    assert icc_even < 0, "an unnaturally even spread gives a negative ICC, by definition"


def test_rates_scores_a_no_call_against_agreement_but_not_as_a_very_major_error():
    """metrics.py scores it this way; the bootstrap interval has to belong to the
    published point estimate, so the two definitions must not drift apart."""
    df = pd.DataFrame([{"pheno": "R", "prediction": "NA"},
                       {"pheno": "R", "prediction": "R"},
                       {"pheno": "S", "prediction": "S"},
                       {"pheno": "S", "prediction": "S"}])
    r = kum.rates(df)
    assert r["ca"] == pytest.approx(0.75)
    assert r["vme"] == pytest.approx(0.0)
    assert r["me"] == pytest.approx(0.0)
