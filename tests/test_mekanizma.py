"""Tests for scripts/mekanizma.py.

The first version of the family patterns anchored on \\b and so did not match "blaNDM-5",
because there is no word boundary between "bla" and "NDM". An NDM-positive isolate was
classified as carrying no carbapenemase, which overstated the share of meropenem
resistance that no assembly-based method could have found — the very conclusion the
table was written to test. These cases pin the symbols as AMRFinderPlus writes them.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mekanizma", ROOT / "scripts" / "mekanizma.py")
mek = importlib.util.module_from_spec(spec)
sys.modules["mekanizma"] = mek
spec.loader.exec_module(mek)


def test_strong_carbapenemase_matches_the_bla_prefixed_symbols():
    for sym in ("blaNDM-5", "blaKPC-2", "blaVIM-1", "blaIMP-26", "NDM-1"):
        assert mek.STRONG_CARBAPENEMASE.search(sym), sym


def test_strong_carbapenemase_does_not_match_unrelated_symbols():
    for sym in ("blaOXA-48", "blaCTX-M-15", "blaEC", "mcr-1.1", "sul1", "aac(3)-IId"):
        assert not mek.STRONG_CARBAPENEMASE.search(sym), sym


def test_oxa48_like_is_separate_from_other_oxa_enzymes():
    for sym in ("blaOXA-48", "blaOXA-181", "blaOXA-232", "blaOXA-244"):
        assert mek.OXA48_LIKE.search(sym), sym
    for sym in ("blaOXA-1", "blaOXA-9", "blaOXA-10"):
        assert not mek.OXA48_LIKE.search(sym), sym


def test_esbl_and_ampc_match_the_bla_prefixed_symbols():
    for sym in ("blaCTX-M-15", "blaSHV-12", "blaCMY-2", "blaDHA-1", "blaTEM-1"):
        assert mek.ESBL_OR_AMPC.search(sym), sym
    assert not mek.ESBL_OR_AMPC.search("blaNDM-5")


def test_relevant_uses_the_catalogue_subclass_for_the_drug():
    rows = [{"symbol": "blaCTX-M-15", "cls": "BETA-LACTAM", "subclass": "CEPHALOSPORIN"},
            {"symbol": "sul1", "cls": "SULFONAMIDE", "subclass": "SULFONAMIDE"},
            {"symbol": "gyrA_S83L", "cls": "QUINOLONE", "subclass": "QUINOLONE"}]
    assert mek.relevant(rows, "cefotaxime") == ["blaCTX-M-15"]
    assert mek.relevant(rows, "ciprofloxacin") == ["gyrA_S83L"]
    assert mek.relevant(rows, "meropenem") == []
    assert mek.relevant(rows, "trimethoprim/sulfamethoxazole") == ["sul1"]


def test_every_scored_drug_has_a_token_mapping():
    """A drug missing from DRUG_TOKENS would raise mid-table, after the earlier tables
    had printed, which is how a partial result gets copied into a draft."""
    expected = {"ampicillin", "cefotaxime", "meropenem", "ciprofloxacin",
                "gentamicin", "trimethoprim/sulfamethoxazole"}
    assert expected <= set(mek.DRUG_TOKENS)
