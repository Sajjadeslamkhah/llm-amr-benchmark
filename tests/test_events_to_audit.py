"""The adapter must read all three vendors' event shapes, and must refuse to
write an empty commands.log: a silent zero would make the hallucination audit
clear an arm whose commands were never read."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "events_to_audit.py"
spec = importlib.util.spec_from_file_location("e2a", SCRIPT)
e2a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2a)

CLAUDE = [
    {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Scanning ISO_001."},
        {"type": "tool_use", "id": "toolu_01", "name": "Bash",
         "input": {"command": "amrfinder -n data/genomes/ISO_001.fasta"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "toolu_01",
         "content": [{"type": "text", "text": "blaCTX-M-15\tCEPHALOSPORIN"}]}]}},
]
AGY = [
    {"event": "step_update", "step_update": {"tool_name": "run_command", "tool_info": {
        "parameters": {"CommandLine": "ls data/genomes"}, "output": "ISO_001.fasta"}}},
]
CODEX = [
    {"type": "item.completed", "item": {"type": "command_execution",
     "command": "head -1 out.tsv", "aggregated_output": "ok", "exit_code": 0}},
]


def write(tmp_path, events, batch="batch_001"):
    d = tmp_path / batch
    d.mkdir(parents=True)
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return tmp_path


def test_claude_command_and_its_separately_sent_output(tmp_path):
    cmds, text, _ = e2a.extract(write(tmp_path, CLAUDE) / "batch_001" / "events.jsonl")
    assert len(cmds) == 1
    assert cmds[0]["cmd"].startswith("amrfinder -n")
    assert cmds[0]["tool"] == "bash"              # not "input", the key it sits under
    assert "blaCTX-M-15" in cmds[0]["stdout"]     # matched back by tool_use_id
    assert any("Scanning ISO_001" in t for t in text)


def test_antigravity_command_and_sibling_output(tmp_path):
    cmds, _, _ = e2a.extract(write(tmp_path, AGY) / "batch_001" / "events.jsonl")
    assert cmds[0]["cmd"] == "ls data/genomes"
    assert cmds[0]["tool"] == "run_command"       # not "parameters"
    assert cmds[0]["stdout"] == "ISO_001.fasta"   # one dict above the command


def test_codex_command_with_exit_code(tmp_path):
    cmds, _, _ = e2a.extract(write(tmp_path, CODEX) / "batch_001" / "events.jsonl")
    assert cmds[0]["cmd"] == "head -1 out.tsv"
    assert cmds[0]["exit_code"] == 0
    assert cmds[0]["stdout"] == "ok"


def test_all_three_shapes_in_one_log(tmp_path):
    cmds, _, seen = e2a.extract(write(tmp_path, CLAUDE + AGY + CODEX) / "batch_001" / "events.jsonl")
    assert len(cmds) == 3
    assert set(seen) == {"bash", "run_command", "command_execution"}


def test_refuses_to_write_an_empty_commands_log(tmp_path):
    write(tmp_path, [{"event": "nothing_useful"}])
    r = subprocess.run([sys.executable, str(SCRIPT), "--run", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "Not writing commands.log" in r.stderr
    assert not (tmp_path / "commands.log").exists()


def test_writes_the_three_files_when_commands_are_found(tmp_path):
    write(tmp_path, CLAUDE + AGY)
    (tmp_path / "batch_001" / "output").mkdir()
    (tmp_path / "batch_001" / "output" / "methods.md").write_text("AMRFinderPlus 4.2.7 was run.")
    r = subprocess.run([sys.executable, str(SCRIPT), "--run", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert len((tmp_path / "commands.log").read_text().splitlines()) == 2
    assert "Scanning ISO_001" in (tmp_path / "transcript.txt").read_text()
    assert "AMRFinderPlus 4.2.7" in (tmp_path / "methods.md").read_text()


def test_every_command_records_which_batch_it_came_from(tmp_path):
    write(tmp_path, CLAUDE, "batch_003")
    r = subprocess.run([sys.executable, str(SCRIPT), "--run", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rows = [json.loads(x) for x in (tmp_path / "commands.log").read_text().splitlines()]
    assert rows[0]["batch"] == "batch_003"
