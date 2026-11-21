"""Unit tests for scripts/hallucination_audit.py on a synthetic run directory.
All content here is invented test data, not study data."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "audit", Path(__file__).resolve().parent.parent / "scripts" / "hallucination_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

CATALOG = {"blaCTX-M-15", "tet(A)", "sul1", "NG_050414.1"}


@pytest.fixture
def run(tmp_path):
    (tmp_path / "commands.log").write_text("\n".join(json.dumps(c) for c in [
        {"cmd": "amrfinder -n ISO_001.fasta --organism Escherichia",
         "exit_code": 0, "stdout": "Gene symbol\tClass\nblaCTX-M-15\tBETA-LACTAM\n", "stderr": ""},
        {"cmd": "resfinder.py -i ISO_001.fasta", "exit_code": 127,
         "stdout": "", "stderr": "command not found"},
    ]) + "\n")
    return tmp_path


def test_h1_flags_only_uncatalogued_genes(run):
    (run / "transcript.txt").write_text(
        "Found blaCTX-M-15 and sul1, plus blaZZZ-9 which confers resistance.")
    codes = [(f["code"], f["evidence"]) for f in audit.check(run, CATALOG)[0]]
    assert ("H1", "blaZZZ-9") in codes
    assert not any(e in ("blaCTX-M-15", "sul1") for c, e in codes if c == "H1")


def test_h2_flags_a_determinant_the_isolates_own_output_lacks(run):
    """H2 was rewritten on 2026-11-21. It used to compare the agent's text with
    stdout line by line, which flagged documented command templates and nothing
    useful. It now asks the sharper question: did the agent report a determinant
    for an isolate whose own tool output does not contain it?"""
    (run / "predictions.tsv").write_text(
        "isolate_id\tantibiotic\tprediction\tevidence\n"
        "ISO_001\tmeropenem\tR\tblaNDM-5 carbapenemase\n")
    d = run / "batch_001" / "workspace" / "output"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ISO_001.tsv").write_text("Element symbol\tClass\nblaTEM-1\tBETA-LACTAM\n")
    h2 = [f["evidence"] for f in audit.check(run, CATALOG)[0] if f["code"] == "H2"]
    assert h2 == ["blaNDM-5"]


def test_h4_unlogged_and_failed_commands(run):
    (run / "transcript.txt").write_text(
        "I ran `abricate --db card ISO_001.fasta` to confirm.\n"
        "Then `resfinder.py -i ISO_001.fasta` gave the resistance profile.\n")
    h4 = {f["evidence"]: f["detail"] for f in audit.check(run, CATALOG)[0] if f["code"] == "H4"}
    assert h4["abricate --db card ISO_001.fasta"] == "not in command log"
    assert h4["resfinder.py -i ISO_001.fasta"] == "exit_code=127"


def test_h5_and_h3(run):
    (run / "transcript.txt").write_text(
        "Per NG_050414.1 and NG_999999.9, the EUCAST v16.1 breakpoint is 2 mg/L.")
    out = audit.check(run, CATALOG)[0]
    assert [f["evidence"] for f in out if f["code"] == "H5"] == ["NG_999999.9"]
    assert any(f["code"] == "H3" for f in out)


def test_clean_run_has_no_h1_h2_h4(run):
    (run / "transcript.txt").write_text(
        "I ran `amrfinder -n ISO_001.fasta --organism Escherichia`.\n"
        "```\nblaCTX-M-15\tBETA-LACTAM\n```\nSo ISO_001 is resistant.\n")
    codes = {f["code"] for f in audit.check(run, CATALOG)[0]}
    assert not codes & {"H1", "H2", "H4"}


def test_catalog_reader_reads_db_directory(tmp_path):
    (tmp_path / "fam.tsv").write_text(
        "node_id\tsymbol\tclass\tsubclass\nblaCTX-M-15\tblaCTX-M-15\tBETA-LACTAM\tCEPHALOSPORIN\n")
    (tmp_path / "AMRProt.fa").write_text(">WP_000027057.1|tet(A)|TETRACYCLINE\nMKSLIV\nSECRETNOTAHEADER\n")
    (tmp_path / "AMR_DNA-Escherichia.tsv").write_text("gyrA\tS83L\tQUINOLONE\n")
    names = audit.read_catalog(tmp_path)
    assert {"blaCTX-M-15", "blactx-m-15", "CEPHALOSPORIN", "WP_000027057.1", "tet(A)", "gyrA", "S83L"} <= names
    assert "MKSLIV" not in names and "SECRETNOTAHEADER" not in names  # FASTA sequence lines skipped


def test_catalog_reader_rejects_wrong_directory(tmp_path):
    with pytest.raises(SystemExit):
        audit.read_catalog(tmp_path / "nope")


def test_evidence_is_not_cut_mid_sentence():
    """The first adjudication was done on evidence cut at 300 characters.

    The reader reported judging one row on a claim ending '...and the eviden', i.e.
    cut before the conclusion the verdict depends on. A claim of that length must now
    survive whole, and anything genuinely over the limit must be cut at a word
    boundary and say so, so the reader asks for the rest instead of judging a fragment.
    """
    claim = ("A single gyrA mutation on its own (typical MIC 0.125-0.5 mg/L, around the "
             "S <=0.25 breakpoint) is called S, and the evidence from the AMRFinderPlus "
             "output supports no second QRDR substitution in this isolate, so the call "
             "stands on one substitution alone and should be read as susceptible rather "
             "than as the borderline result a second substitution would have produced.")
    assert 300 < len(claim) <= audit.EVIDENCE_LIMIT
    assert audit.kirp(claim) == claim, "a whole claim of this length must not be cut"

    long = "word " * 400
    cut = audit.kirp(long)
    assert len(cut) < len(long)
    assert "kesildi" in cut, "a cut must be visible to the reader"
    assert not cut.split("[")[0].rstrip().endswith("wor"), "must cut at a word boundary"

    assert audit.kirp("short") == "short"
    assert audit.kirp("") == ""
