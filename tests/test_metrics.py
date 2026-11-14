"""Unit tests for scripts/metrics.py on small hand-checked toy tables.
These are synthetic test cases, not study data."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location(
    "metrics", Path(__file__).resolve().parent.parent / "scripts" / "metrics.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_counts():
    df = pd.DataFrame({
        "pheno":      ["R", "R", "R", "R", "S", "S", "S", "S", "I"],
        "prediction": ["R", "R", "S", "NA", "S", "S", "R", "S", "R"],
    })
    r = metrics.evaluate(df)                       # I row excluded
    assert r["n_pairs"] == 8 and r["n_ref_R"] == 4 and r["n_ref_S"] == 4
    assert r["CA_k"] == 5                          # 2 R + 3 S correct
    assert r["VME_k"] == 1 and r["VME"] == 0.25    # R called S
    assert r["ME_k"] == 1 and r["ME"] == 0.25      # S called R
    assert r["no_call"] == 1
    r2 = metrics.evaluate(df, nocall_as_error=False)
    assert r2["n_pairs"] == 7 and r2["CA_k"] == 5


def test_wilson_known_value():
    p, lo, hi = metrics.wilson(8, 10)              # textbook: 0.490-0.943
    assert p == 0.8
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)


def test_mcnemar_and_holm():
    a = pd.Series([True] * 10 + [False] * 0)
    b = pd.Series([False] * 10)
    k1, k2, p = metrics.mcnemar_exact(a, b)
    assert (k1, k2) == (10, 0) and p == pytest.approx(2 * 0.5 ** 10)
    assert metrics.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_fleiss_perfect_agreement():
    t = pd.DataFrame({"S": [3, 0, 3, 0], "R": [0, 3, 0, 3]})
    assert metrics.fleiss_kappa(t) == pytest.approx(1.0)
