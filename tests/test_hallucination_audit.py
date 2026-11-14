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
    codes = [(f["code"], f["evidence"]) for f in audit.check(run, CATALOG)]
    assert ("H1", "blaZZZ-9") in codes
    assert not any(e in ("blaCTX-M-15", "sul1") for c, e in codes if c == "H1")


def test_h2_flags_output_absent_from_stdout(run):
    (run / "transcript.txt").write_text(
        "Output:\n```\nGene symbol\tClass\nblaNDM-5\tCARBAPENEM score 99.8\n```\n")
    h2 = [f["evidence"] for f in audit.check(run, CATALOG) if f["code"] == "H2"]
    assert any("blaNDM-5" in e for e in h2)
    assert not any(e.startswith("Gene symbol") for e in h2)  # that line is in stdout


def test_h4_unlogged_and_failed_commands(run):
    (run / "transcript.txt").write_text(
        "I ran `abricate --db card ISO_001.fasta` to confirm.\n"
        "Then `resfinder.py -i ISO_001.fasta` gave the resistance profile.\n")
    h4 = {f["evidence"]: f["detail"] for f in audit.check(run, CATALOG) if f["code"] == "H4"}
    assert h4["abricate --db card ISO_001.fasta"] == "not in command log"
    assert h4["resfinder.py -i ISO_001.fasta"] == "exit_code=127"


def test_h5_and_h3(run):
    (run / "transcript.txt").write_text(
        "Per NG_050414.1 and NG_999999.9, the EUCAST v16.1 breakpoint is 2 mg/L.")
    out = audit.check(run, CATALOG)
    assert [f["evidence"] for f in out if f["code"] == "H5"] == ["NG_999999.9"]
    assert any(f["code"] == "H3" for f in out)


def test_clean_run_has_no_h1_h2_h4(run):
    (run / "transcript.txt").write_text(
        "I ran `amrfinder -n ISO_001.fasta --organism Escherichia`.\n"
        "```\nblaCTX-M-15\tBETA-LACTAM\n```\nSo ISO_001 is resistant.\n")
    codes = {f["code"] for f in audit.check(run, CATALOG)}
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
