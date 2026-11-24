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


def test_h3_evidence_reaches_the_end_of_the_claim(run):
    """The real cause of the truncation reader 1 reported.

    BREAKPOINT_CLAIM stops 60 characters past the concentration. On the sheet sent to
    reader 1 that cut a claim at '...is called S, and the eviden', so the row he had to
    judge ended before the conclusion the verdict depends on. A character count cannot
    know where a claim ends; the evidence now runs to the sentence boundary.
    """
    (run / "transcript.txt").write_text(
        "A single gyrA mutation on its own (typical MIC 0.125-0.5 mg/L, around the "
        "S <=0.25 breakpoint) is called S, and the evidence in this isolate shows no "
        "second QRDR substitution, so the call rests on one substitution alone. "
        "The next sentence must stay out of this row.")
    h3 = [f["evidence"] for f in audit.check(run, CATALOG)[0] if f["code"] == "H3"]
    assert h3, "the claim should still be flagged"
    claim = max(h3, key=len)
    assert "one substitution alone." in claim, "the claim must reach its own conclusion"
    assert "and the eviden" not in claim.replace("and the evidence", "")
    assert "next sentence" not in claim, "the row must stop at the sentence boundary"


def test_h3_row_names_the_isolate_and_antibiotic_it_is_about(run):
    """Both readers refused to adjudicate the H3 rows for want of this.

    Reader 2 returned Unclear on both, asking which mutation one referred to and which
    strain the other applied to; reader 1's second report named the same gap. A
    breakpoint cannot be checked without the organism and the drug, so the row carries
    them, and says whether they were stated or merely nearby.
    """
    (run / "predictions.tsv").write_text(
        "isolate_id\tantibiotic\tprediction\tevidence\n"
        "ISO_007\tciprofloxacin\tS\tA single gyrA substitution, MIC near 0.25 mg/L, so susceptible.\n")
    h3 = [f for f in audit.check(run, CATALOG)[0] if f["code"] == "H3"]
    assert h3, "the claim should be flagged"
    d = h3[0]["detail"]
    assert "ISO_007" in d and "ciprofloxacin" in d
    assert "stated" in d, "a claim inside its own prediction's evidence is stated, not guessed"


def test_h3_row_says_so_when_no_case_is_attached(run):
    """A breakpoint claim with no isolate and no drug anywhere near it is not a row the
    adjudicator should have to guess at, and the absence is itself worth seeing."""
    (run / "transcript.txt").write_text(
        "In general the committee sets the threshold at 0.25 mg/L for this class.")
    h3 = [f for f in audit.check(run, CATALOG)[0] if f["code"] == "H3"]
    assert h3
    assert "not stated" in h3[0]["detail"]
