#!/usr/bin/env python3
"""Run one agent arm on the isolate set and record everything it did.

    python scripts/05_run_agent.py --arm claude --rep 1
    python scripts/05_run_agent.py --arm claude --rep 0 --pilot 3   # pilot, discarded

Creates runs/<arm>/rep<N>/ with:
    workspace/data/genomes/ISO_###.fasta   the only genomes the agent sees
    workspace/data/antibiotics.txt
    workspace/output/                      where the agent writes its answers
    events.jsonl                           the harness event stream, verbatim
    stdout.txt                             everything the CLI printed
    meta.json                              arm, replicate, command, versions, timing

The event stream is kept verbatim; scripts/06_parse_run.py turns it into the
transcript.txt and commands.log that scripts/hallucination_audit.py reads.

Each harness is invoked through its own official CLI with its own flags, which
is a design choice recorded in PROTOCOL.md section 8. Network handling differs
per harness and is recorded in meta.json rather than assumed:
  codex   --sandbox workspace-write     commands run without network
  claude  --disallowed-tools WebSearch WebFetch
  agy     --sandbox                     terminal restrictions
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()

ARMS = {
    "claude": {
        "vendor": "Anthropic",
        "bin": [str(HOME / ".local/bin/claude"), "claude"],
        "network_note": "web tools disabled via --disallowed-tools; shell commands are not OS-sandboxed on macOS",
        "args": lambda prompt, model: (
            ["-p", prompt, "--output-format", "stream-json", "--verbose",
             "--permission-mode", "bypassPermissions",
             "--disallowed-tools", "WebSearch", "WebFetch"]
            + (["--model", model] if model else [])),
    },
    "gemini": {
        "vendor": "Google",
        "bin": [str(HOME / ".local/bin/agy"), "agy"],
        "network_note": "--sandbox enables terminal restrictions; no documented web-tool switch",
        "args": lambda prompt, model: (
            ["--print", prompt, "--output-format", "stream-json",
             "--dangerously-skip-permissions", "--sandbox"]
            + (["--model", model] if model else [])),
    },
    "gpt": {
        "vendor": "OpenAI",
        "bin": [str(HOME / "miniforge3/bin/codex"), "codex"],
        "network_note": "--sandbox workspace-write blocks network for model-run commands; web search not enabled",
        "args": lambda prompt, model: (
            ["exec", prompt, "--json", "--sandbox", "workspace-write",
             "--skip-git-repo-check"]
            + (["--model", model] if model else [])),
    },
}


def find_bin(candidates: list[str]) -> str:
    for c in candidates:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit(f"None of these executables was found: {candidates}")


def build_workspace(run: Path, pilot: int | None) -> int:
    src = ROOT / "sandbox" / "data"
    genomes = sorted((src / "genomes").glob("ISO_*.fasta"))
    if not genomes:
        sys.exit(f"No genomes in {src / 'genomes'}. Run scripts/03_fetch_genomes.py first.")
    if pilot:
        genomes = genomes[:pilot]
    ws = run / "workspace"
    (ws / "data" / "genomes").mkdir(parents=True, exist_ok=True)
    (ws / "output").mkdir(parents=True, exist_ok=True)
    for g in genomes:
        shutil.copy2(g, ws / "data" / "genomes" / g.name)
    shutil.copy2(src / "antibiotics.txt", ws / "data" / "antibiotics.txt")
    return len(genomes)


def tool_versions() -> dict:
    out = {}
    for name, cmd in (("amrfinder", ["amrfinder", "--version"]),
                      ("amrfinder_db", ["amrfinder", "--database_version"])):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            out[name] = (p.stdout + p.stderr).strip().splitlines()[-1] if p.returncode == 0 else f"error {p.returncode}"
        except Exception as e:  # noqa: BLE001 - recorded, not raised
            out[name] = f"unavailable: {e}"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--rep", type=int, required=True, help="replicate number; use 0 for a pilot")
    ap.add_argument("--model", default="", help="pin a model; empty uses the harness default")
    ap.add_argument("--pilot", type=int, help="use only the first N isolates (pilot, discarded)")
    ap.add_argument("--timeout", type=int, default=7200, help="seconds before the run is abandoned")
    ap.add_argument("--force", action="store_true", help="rerun even if the run directory exists")
    a = ap.parse_args()

    spec = ARMS[a.arm]
    run = ROOT / "runs" / a.arm / f"rep{a.rep}"
    if run.exists() and not a.force:
        if (run / "workspace" / "output" / "predictions.tsv").exists():
            sys.exit(f"{run} already has predictions. Use --force to rerun.")
        print(f"{run} exists without predictions; continuing into it.", file=sys.stderr)
    run.mkdir(parents=True, exist_ok=True)

    n = build_workspace(run, a.pilot)
    prompt = (ROOT / "prompts" / "task_prompt.md").read_text(encoding="utf-8")
    binary = find_bin(spec["bin"])
    cmd = [binary] + spec["args"](prompt, a.model)

    env = dict(os.environ)
    env["PATH"] = f"{HOME}/miniforge3/envs/amr/bin:{HOME}/miniforge3/bin:{HOME}/.local/bin:" + env.get("PATH", "")
    env.pop("OPENAI_API_KEY", None)      # force subscription auth, never API billing
    env.pop("ANTHROPIC_API_KEY", None)

    meta = {
        "arm": a.arm, "vendor": spec["vendor"], "replicate": a.rep,
        "pilot": bool(a.pilot), "n_isolates": n,
        "binary": binary, "command": cmd[:1] + ["<task prompt>" if x == prompt else x for x in cmd[1:]],
        "model_requested": a.model or "(harness default)",
        "network_note": spec["network_note"],
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "tool_versions": tool_versions(),
    }
    (run / "meta.json").write_text(json.dumps(meta, indent=2))

    print(f"[{a.arm} rep{a.rep}] {n} isolates; running {binary}", file=sys.stderr)
    t0 = time.time()
    with (run / "events.jsonl").open("w") as ev, (run / "stdout.txt").open("w") as so:
        p = subprocess.Popen(cmd, cwd=run / "workspace", env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in p.stdout:
                so.write(line)
                so.flush()
                s = line.strip()
                if s.startswith("{"):
                    ev.write(s + "\n")
                    ev.flush()
            p.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            meta["timed_out"] = True

    meta["exit_code"] = p.returncode
    meta["wall_clock_seconds"] = round(time.time() - t0, 1)
    meta["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    preds = run / "workspace" / "output" / "predictions.tsv"
    meta["predictions_written"] = preds.exists()
    if preds.exists():
        meta["prediction_rows"] = sum(1 for _ in preds.open()) - 1
    (run / "meta.json").write_text(json.dumps(meta, indent=2))

    print(json.dumps({k: meta[k] for k in ("exit_code", "wall_clock_seconds",
                                           "predictions_written", "prediction_rows")
                      if k in meta}, indent=2))
    if not preds.exists():
        print("\nNo predictions.tsv. Check stdout.txt and events.jsonl in " + str(run), file=sys.stderr)


if __name__ == "__main__":
    main()
