"""Unit tests for the reference rule in scripts/04_reference_arm.py.

Rows below use the Class/Subclass vocabulary verified against AMRFinderPlus
database 2026-10-29.1 on 2026-11-14."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "ref", Path(__file__).resolve().parent.parent / "scripts" / "04_reference_arm.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def row(symbol, cls, sub, etype="AMR", subtype="AMR"):
    return {"Element symbol": symbol, "Class": cls, "Subclass": sub,
            "Element type": etype, "Element subtype": subtype}


def test_tokens_are_whole_words():
    assert ref.tokens("GENTAMICIN/TOBRAMYCIN") == {"GENTAMICIN", "TOBRAMYCIN"}
    assert "GENTAMICIN" not in ref.tokens("APRAMYCIN")


def test_narrow_penicillinase_is_ampicillin_only():
    rows = [row("blaTEM-1", "BETA-LACTAM", "BETA-LACTAM")]
    assert ref.call(rows, "ampicillin")[0] == "R"
    assert ref.call(rows, "cefotaxime")[0] == "S"
    assert ref.call(rows, "meropenem")[0] == "S"


def test_esbl_hits_ampicillin_and_cefotaxime_not_meropenem():
    rows = [row("blaCTX-M-15", "BETA-LACTAM", "CEPHALOSPORIN")]
    assert ref.call(rows, "ampicillin")[0] == "R"
    assert ref.call(rows, "cefotaxime")[0] == "R"
    assert ref.call(rows, "meropenem")[0] == "S"


def test_carbapenemase_hits_all_three_beta_lactam_agents():
    rows = [row("blaNDM-5", "BETA-LACTAM", "CARBAPENEM")]
    assert [ref.call(rows, a)[0] for a in ("ampicillin", "cefotaxime", "meropenem")] == ["R", "R", "R"]


def test_generic_aminoglycoside_subclass_does_not_call_gentamicin():
    assert ref.call([row("aph(3')-Ia", "AMINOGLYCOSIDE", "AMINOGLYCOSIDE")], "gentamicin")[0] == "S"
    assert ref.call([row("aac(3)-IId", "AMINOGLYCOSIDE", "GENTAMICIN/TOBRAMYCIN")], "gentamicin")[0] == "R"


def test_quinolone_matches_class_or_subclass_and_point_mutations():
    assert ref.call([row("qnrS1", "QUINOLONE", "QUINOLONE")], "ciprofloxacin")[0] == "R"
    assert ref.call([row("gyrA_S83L", "QUINOLONE", "QUINOLONE", subtype="POINT")], "ciprofloxacin")[0] == "R"
    assert ref.call([row("aac(6')-Ib-cr5", "AMINOGLYCOSIDE/QUINOLONE",
                         "AMIKACIN/KANAMYCIN/QUINOLONE/TOBRAMYCIN")], "ciprofloxacin")[0] == "R"


def test_cotrimoxazole_needs_both_components():
    tmp = row("dfrA17", "TRIMETHOPRIM", "TRIMETHOPRIM")
    sul = row("sul1", "SULFONAMIDE", "SULFONAMIDE")
    assert ref.call([tmp], "trimethoprim/sulfamethoxazole")[0] == "S"
    assert ref.call([sul], "trimethoprim/sulfamethoxazole")[0] == "S"
    pred, ev = ref.call([tmp, sul], "trimethoprim/sulfamethoxazole")
    assert pred == "R" and "dfrA17" in ev and "sul1" in ev


def test_stress_and_virulence_rows_are_ignored():
    rows = [row("blaX", "BETA-LACTAM", "CARBAPENEM", etype="STRESS"),
            row("vfX", "BETA-LACTAM", "CARBAPENEM", etype="VIRULENCE")]
    assert all(ref.call(rows, a)[0] == "S" for a in ref.ANTIBIOTICS)


def test_clean_genome_is_susceptible_everywhere():
    assert all(ref.call([], a) == ("S", "no determinant found") for a in ref.ANTIBIOTICS)
