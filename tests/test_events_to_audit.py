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


def test_claude_echoes_are_not_counted_twice(tmp_path):
    """Claude Code repeats every tool input under wire_tool_inputs. Counting the echo
    doubled the command total (249 instead of 124) and halved every per-command rate."""
    events = CLAUDE + [{"type": "assistant", "wire_tool_inputs": {
        "toolu_01": {"command": "amrfinder -n data/genomes/ISO_001.fasta"}}}]
    cmds, _, seen, dropped = e2a.extract(write(tmp_path, events) / "batch_001" / "events.jsonl")
    assert len(cmds) == 1, [c["cmd"] for c in cmds]
    assert cmds[0]["tool"] == "bash"
    assert "?" not in seen


def test_an_unnamed_duplicate_is_dropped_even_from_an_unknown_echo_shape(tmp_path):
    events = CLAUDE + [{"type": "x", "something_new": {"command": "amrfinder -n data/genomes/ISO_001.fasta"}}]
    cmds, _, _, dropped = e2a.extract(write(tmp_path, events) / "batch_001" / "events.jsonl")
    assert len(cmds) == 1
    assert dropped == 1


def test_the_same_command_run_twice_is_kept_twice(tmp_path):
    """Deduplication must not merge a command the agent genuinely ran again."""
    again = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_02", "name": "Bash",
         "input": {"command": "amrfinder -n data/genomes/ISO_001.fasta"}}]}}]
    cmds, _, _, _ = e2a.extract(write(tmp_path, CLAUDE + again) / "batch_001" / "events.jsonl")
    assert len(cmds) == 2


def test_claude_command_and_its_separately_sent_output(tmp_path):
    cmds, text, _, _ = e2a.extract(write(tmp_path, CLAUDE) / "batch_001" / "events.jsonl")
    assert len(cmds) == 1
    assert cmds[0]["cmd"].startswith("amrfinder -n")
    assert cmds[0]["tool"] == "bash"              # not "input", the key it sits under
    assert "blaCTX-M-15" in cmds[0]["stdout"]     # matched back by tool_use_id
    assert any("Scanning ISO_001" in t for t in text)


def test_antigravity_command_and_sibling_output(tmp_path):
    cmds, _, _, _ = e2a.extract(write(tmp_path, AGY) / "batch_001" / "events.jsonl")
    assert cmds[0]["cmd"] == "ls data/genomes"
    assert cmds[0]["tool"] == "run_command"       # not "parameters"
    assert cmds[0]["stdout"] == "ISO_001.fasta"   # one dict above the command


def test_codex_command_with_exit_code(tmp_path):
    cmds, _, _, _ = e2a.extract(write(tmp_path, CODEX) / "batch_001" / "events.jsonl")
    assert cmds[0]["cmd"] == "head -1 out.tsv"
    assert cmds[0]["exit_code"] == 0
    assert cmds[0]["stdout"] == "ok"


def test_all_three_shapes_in_one_log(tmp_path):
    cmds, _, seen, _ = e2a.extract(write(tmp_path, CLAUDE + AGY + CODEX) / "batch_001" / "events.jsonl")
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
    # the harness puts the agent's workspace one level down, so this is where it lands
    d = tmp_path / "batch_001" / "workspace" / "output"
    d.mkdir(parents=True)
    (d / "methods.md").write_text("AMRFinderPlus 4.2.7 was run.")
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


def test_is_error_becomes_an_exit_code(tmp_path):
    """Claude Code reports failure as is_error. Without the mapping, H4 (commands
    that did not run) would be measurable for one arm and not for another."""
    events = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "rgi main -i x"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "is_error": True,
             "content": "command not found: rgi"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "amrfinder -V"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2", "is_error": False, "content": "4.2.7"}]}},
    ]
    cmds, _, _, _ = e2a.extract(write(tmp_path, events) / "batch_001" / "events.jsonl")
    by = {c["cmd"]: c for c in cmds}
    assert by["rgi main -i x"]["exit_code"] == 1
    assert by["amrfinder -V"]["exit_code"] == 0


def test_every_command_records_its_key_path(tmp_path):
    """So double counting can be located instead of guessed at."""
    cmds, _, _, _ = e2a.extract(write(tmp_path, CLAUDE) / "batch_001" / "events.jsonl")
    assert cmds[0]["key_path"]


CODEX_PAIR = [
    {"type": "item.started", "item": {"id": "it_1", "type": "command_execution",
     "command": "amrfinder -n ISO_001.fasta"}},
    {"type": "item.completed", "item": {"id": "it_1", "type": "command_execution",
     "command": "amrfinder -n ISO_001.fasta", "aggregated_output": "blaTEM-1", "exit_code": 0}},
]


def test_codex_start_and_completed_are_one_command(tmp_path):
    """Codex writes item.started then item.completed for the same command. Counting
    both gave 651 commands where 325 ran, and left half of them with no exit code."""
    cmds, _, _, _ = e2a.extract(write(tmp_path, CODEX_PAIR) / "batch_001" / "events.jsonl")
    assert len(cmds) == 1, [(c["cmd"], c["exit_code"]) for c in cmds]
    assert cmds[0]["exit_code"] == 0
    assert cmds[0]["stdout"] == "blaTEM-1"


def test_two_codex_commands_with_different_ids_both_count(tmp_path):
    second = [{"type": "item.completed", "item": {"id": "it_2", "type": "command_execution",
               "command": "amrfinder -n ISO_002.fasta", "exit_code": 0}}]
    cmds, _, _, _ = e2a.extract(write(tmp_path, CODEX_PAIR + second) / "batch_001" / "events.jsonl")
    assert len(cmds) == 2
