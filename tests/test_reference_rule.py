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
    """A row as AMRFinderPlus 4.x writes it: Type / Subtype / Element symbol."""
    return {"Element symbol": symbol, "Class": cls, "Subclass": sub,
            "Type": etype, "Subtype": subtype}


def eski_row(symbol, cls, sub, etype="AMR"):
    """A row as older AMRFinderPlus versions wrote it, still accepted."""
    return {"Gene symbol": symbol, "Class": cls, "Subclass": sub, "Element type": etype}


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


def test_real_amrfinder_4x_report_is_read(tmp_path):
    """The 4.x header must be understood: with 'Element type' only, every call came back S."""
    header = ("Protein id\tContig id\tStart\tStop\tStrand\tElement symbol\tElement name\tScope\t"
              "Type\tSubtype\tClass\tSubclass\tMethod")
    lines = [header,
             "NA\tcontig_164\t6070\t6942\t+\tblaCTX-M-15\tESBL CTX-M-15\tcore\tAMR\tAMR\t"
             "BETA-LACTAM\tCEPHALOSPORIN\tALLELEX",
             "NA\tcontig_2\t24062\t26686\t-\tgyrA_S83L\tquinolone resistant GyrA\tcore\tAMR\tPOINT\t"
             "QUINOLONE\tQUINOLONE\tPOINTX",
             "NA\tcontig_22\t6414\t7250\t-\tsul1\tSul1\tcore\tAMR\tAMR\tSULFONAMIDE\tSULFONAMIDE\tEXACTX",
             "NA\tcontig_22\t8719\t9189\t-\tdfrA17\tDfrA17\tcore\tAMR\tAMR\tTRIMETHOPRIM\tTRIMETHOPRIM\tEXACTX",
             "NA\tcontig_22\t7247\t7591\t-\tqacEdelta1\tQacE delta 1\tcore\tSTRESS\tBIOCIDE\t"
             "QUATERNARY AMMONIUM\tQUATERNARY AMMONIUM\tALLELEX"]
    p = tmp_path / "ISO_001.amrfinder.tsv"
    p.write_text("\n".join(lines) + "\n")
    rows = ref.read_report(p)
    calls = {a: ref.call(rows, a)[0] for a in ref.ANTIBIOTICS}
    assert calls["ampicillin"] == "R"
    assert calls["cefotaxime"] == "R"
    assert calls["ciprofloxacin"] == "R"
    assert calls["trimethoprim/sulfamethoxazole"] == "R"
    assert calls["meropenem"] == "S"
    assert calls["gentamicin"] == "S"


def test_older_column_names_still_work():
    assert ref.call([eski_row("blaCTX-M-15", "BETA-LACTAM", "CEPHALOSPORIN")], "cefotaxime")[0] == "R"
    assert ref.call([eski_row("blaX", "BETA-LACTAM", "CARBAPENEM", etype="STRESS")], "meropenem")[0] == "S"


def test_clean_genome_is_susceptible_everywhere():
    assert all(ref.call([], a) == ("S", "no determinant found") for a in ref.ANTIBIOTICS)
