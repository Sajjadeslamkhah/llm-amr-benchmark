"""Tests for scripts/arsiv.py — what may and may not enter the repository."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("arsiv", ROOT / "scripts" / "arsiv.py")
ars = importlib.util.module_from_spec(spec)
sys.modules["arsiv"] = ars
spec.loader.exec_module(ars)


def test_anything_named_key_is_refused():
    """The blinding key and the adjudication key resolve which arm wrote which row, and
    the adjudication is not finished. go.sh paket already refuses these; the archive
    has to refuse them too, or the same secret leaks by another route."""
    for name in ("adjudication_sheet.key.tsv", "blinding_key.tsv", "KEY.tsv",
                 "arm_key_backup.tsv"):
        assert ars.refused(Path("results/audit") / name), name


def test_reference_phenotypes_are_refused():
    """They stay outside the tree because the agents run inside it, and replicate 4 was
    run after the freeze, so this is a live constraint and not a historical one."""
    for name in ("reference_phenotypes.tsv", "phenotypes_all.tsv", "pheno_backup.tsv"):
        assert ars.refused(Path("data") / name), name


def test_the_files_the_manuscript_reads_from_are_allowed():
    for name in ("metrics.tsv", "kumelenme.tsv", "predictions.tsv", "commands.log",
                 "transcript.txt", "ISO_001.amrfinder.tsv", "vme_mekanizma.tsv",
                 "meropenem_karbapenemaz.tsv"):
        assert not ars.refused(Path("results") / name), name


def test_patterns_cover_each_artifact_the_numbers_come_from():
    globs = {g for g, _ in ars.PATTERNS}
    for needed in ("results/*.tsv", "runs/*/rep*/predictions.tsv",
                   "runs/*/rep*/commands.log",
                   "runs/amrfinderplus/raw/*.amrfinder.tsv"):
        assert needed in globs, needed


def test_every_pattern_states_why_the_file_is_kept():
    for glob, why in ars.PATTERNS:
        assert why and len(why) > 10, glob


def test_verify_mode_exists_and_is_documented():
    """FREEZE.md told readers to verify twelve files with shasum, five no longer matched,
    and nobody noticed until a reviewer ran it. An archive whose manifest cannot be
    checked with one command repeats that."""
    import inspect
    src = inspect.getsource(ars.main)
    assert "--dogrula" in src
    assert "MANIFEST.tsv" in src
