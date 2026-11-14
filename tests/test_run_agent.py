"""Unit tests for the batching and merging logic in scripts/05_run_agent.py.
No agent is launched here; only the pure functions are exercised."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "runner", Path(__file__).resolve().parent.parent / "scripts" / "05_run_agent.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

HEADER = "isolate_id\tantibiotic\tprediction\tevidence\n"


def write_batch(run, i, rows):
    d = run / f"batch_{i:03d}" / "workspace" / "output"
    d.mkdir(parents=True, exist_ok=True)
    (d / "predictions.tsv").write_text(HEADER + "".join("\t".join(r) + "\n" for r in rows))


def test_merge_concatenates_batches_in_order(tmp_path):
    write_batch(tmp_path, 1, [["ISO_001", "ampicillin", "R", "blaTEM-1"]])
    write_batch(tmp_path, 2, [["ISO_002", "ampicillin", "S", "no determinant found"]])
    assert runner.merge_predictions(tmp_path) == 2
    text = (tmp_path / "predictions.tsv").read_text()
    assert text.index("ISO_001") < text.index("ISO_002")


def test_merge_keeps_first_row_for_a_repeated_pair(tmp_path):
    write_batch(tmp_path, 1, [["ISO_001", "ampicillin", "R", "first"]])
    write_batch(tmp_path, 2, [["ISO_001", "ampicillin", "S", "second"]])
    assert runner.merge_predictions(tmp_path) == 1
    assert "first" in (tmp_path / "predictions.tsv").read_text()


def test_merge_skips_batches_without_predictions_and_blank_ids(tmp_path):
    write_batch(tmp_path, 1, [["ISO_001", "ampicillin", "R", "x"], ["", "ampicillin", "S", "y"]])
    (tmp_path / "batch_002" / "workspace" / "output").mkdir(parents=True)
    assert runner.merge_predictions(tmp_path) == 1


def test_batch_slicing_covers_every_isolate_once():
    genomes = [Path(f"ISO_{i:03d}.fasta") for i in range(1, 119)]
    size = 10
    batches = [genomes[i:i + size] for i in range(0, len(genomes), size)]
    assert len(batches) == 12
    assert sum(len(b) for b in batches) == 118
    assert [g for b in batches for g in b] == genomes


def test_every_arm_builds_a_command_without_a_model(tmp_path):
    for name, spec_ in runner.ARMS.items():
        args = spec_["args"]("PROMPT", "")
        assert "PROMPT" in args, name
        assert not any(a == "--model" for a in args), name
        assert "--model" in spec_["args"]("PROMPT", "some-model"), name
