#!/usr/bin/env python3
"""Run one agent arm over the isolate set, in batches, and record everything.

    python scripts/05_run_agent.py --arm claude --rep 1                 # all isolates
    python scripts/05_run_agent.py --arm claude --rep 0 --pilot 3       # pilot, discarded
    python scripts/05_run_agent.py --arm gpt --rep 2 --isolates subset  # reproducibility subset

Isolates are processed in batches, each a separate agent session, because one
session over the whole set exceeds the context window (the pilot used about
437k tokens for 3 isolates). Batches are resumable: a batch whose
predictions.tsv already exists is skipped, so an interrupted run continues
where it stopped. --max-batches stops after N batches in one sitting, for
working within a subscription's rate limits.

Layout
    runs/<arm>/rep<N>/batch_001/workspace/data/genomes/ISO_###.fasta
                               /workspace/output/predictions.tsv
                               /events.jsonl   harness event stream, verbatim
                               /stdout.txt
                               /meta.json
    runs/<arm>/rep<N>/predictions.tsv          all batches merged
    runs/<arm>/rep<N>/run_meta.json

Network handling differs per harness and is recorded, not assumed:
    gpt     codex --sandbox workspace-write   commands run without network
    claude  --disallowed-tools WebSearch WebFetch; the result event records
            web_search_requests and web_fetch_requests, which the manuscript cites
    gemini  --sandbox                         terminal restrictions
"""
import argparse
import csv
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
            ["exec", prompt, "--json", "--sandbox", "workspace-write", "--skip-git-repo-check"]
            + (["--model", model] if model else [])),
    },
}
PRED_FIELDS = ["isolate_id", "antibiotic", "prediction", "evidence"]
N_ANTIBIOTICS = 6


def find_bin(candidates: list[str]) -> str:
    for c in candidates:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit(f"None of these executables was found: {candidates}")


def select_genomes(pilot: int | None, isolates: str) -> list[Path]:
    src = ROOT / "sandbox" / "data" / "genomes"
    genomes = sorted(src.glob("ISO_*.fasta"))
    if not genomes:
        sys.exit(f"No genomes in {src}. Run scripts/03_fetch_genomes.py first.")
    if pilot:
        return genomes[:pilot]
    if isolates == "subset":
        sub = ROOT / "data" / "selection" / "reproducibility_subset.txt"
        if not sub.exists():
            sys.exit(f"{sub} not found; create it before using --isolates subset.")
        wanted = {l.strip() for l in sub.read_text().splitlines() if l.strip()}
        return [g for g in genomes if g.stem in wanted]
    return genomes


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


def run_batch(spec: dict, binary: str, prompt: str, model: str, genomes: list[Path],
              batch_dir: Path, timeout: int, env: dict) -> dict:
    ws = batch_dir / "workspace"
    (ws / "data" / "genomes").mkdir(parents=True, exist_ok=True)
    (ws / "output").mkdir(parents=True, exist_ok=True)
    for g in genomes:
        shutil.copy2(g, ws / "data" / "genomes" / g.name)
    shutil.copy2(ROOT / "sandbox" / "data" / "antibiotics.txt", ws / "data" / "antibiotics.txt")

    cmd = [binary] + spec["args"](prompt, model)
    meta = {
        "isolates": [g.stem for g in genomes],
        "command": [binary] + ["<task prompt>" if x == prompt else x for x in cmd[1:]],
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    t0 = time.time()
    with (batch_dir / "events.jsonl").open("w") as ev, (batch_dir / "stdout.txt").open("w") as so:
        p = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in p.stdout:
                so.write(line)
                so.flush()
                s = line.strip()
                if s.startswith("{"):
                    ev.write(s + "\n")
                    ev.flush()
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            meta["timed_out"] = True
    meta["exit_code"] = p.returncode
    meta["wall_clock_seconds"] = round(time.time() - t0, 1)
    meta["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    preds = ws / "output" / "predictions.tsv"
    meta["predictions_written"] = preds.exists()
    if preds.exists():
        meta["prediction_rows"] = sum(1 for _ in preds.open()) - 1
    (batch_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def merge_predictions(run: Path) -> int:
    """Concatenate the batches' predictions, keeping the first row per pair."""
    rows, seen = [], set()
    for batch in sorted(run.glob("batch_*")):
        p = batch / "workspace" / "output" / "predictions.tsv"
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                key = ((r.get("isolate_id") or "").strip(), (r.get("antibiotic") or "").strip())
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                rows.append({k: (r.get(k) or "").strip() for k in PRED_FIELDS})
    with (run / "predictions.tsv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PRED_FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--rep", type=int, required=True, help="replicate number; 0 means pilot")
    ap.add_argument("--model", default="", help="pin a model; empty uses the harness default")
    ap.add_argument("--pilot", type=int, help="use only the first N isolates (pilot, discarded)")
    ap.add_argument("--isolates", default="all", choices=["all", "subset"])
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=5400, help="seconds per batch")
    ap.add_argument("--max-batches", type=int, help="stop after this many batches this sitting")
    a = ap.parse_args()

    spec = ARMS[a.arm]
    run = ROOT / "runs" / a.arm / f"rep{a.rep}"
    run.mkdir(parents=True, exist_ok=True)
    genomes = select_genomes(a.pilot, a.isolates)
    batches = [genomes[i:i + a.batch_size] for i in range(0, len(genomes), a.batch_size)]
    prompt = (ROOT / "prompts" / "task_prompt.md").read_text(encoding="utf-8")
    binary = find_bin(spec["bin"])

    env = dict(os.environ)
    env["PATH"] = f"{HOME}/miniforge3/envs/amr/bin:{HOME}/miniforge3/bin:{HOME}/.local/bin:" + env.get("PATH", "")
    env.pop("OPENAI_API_KEY", None)      # force subscription auth, never API billing
    env.pop("ANTHROPIC_API_KEY", None)

    run_meta = {
        "arm": a.arm, "vendor": spec["vendor"], "replicate": a.rep,
        "pilot": bool(a.pilot), "isolate_set": a.isolates,
        "n_isolates": len(genomes), "batch_size": a.batch_size, "n_batches": len(batches),
        "binary": binary, "model_requested": a.model or "(harness default)",
        "network_note": spec["network_note"], "tool_versions": tool_versions(),
        "batches": [],
    }

    print(f"[{a.arm} rep{a.rep}] {len(genomes)} isolates in {len(batches)} batches of {a.batch_size}",
          file=sys.stderr)
    done_this_sitting = 0
    for i, chunk in enumerate(batches, 1):
        batch_dir = run / f"batch_{i:03d}"
        if (batch_dir / "workspace" / "output" / "predictions.tsv").exists():
            print(f"  batch {i:03d}: already done, skipping", file=sys.stderr)
            run_meta["batches"].append({"batch": i, "skipped": True})
            continue
        if a.max_batches and done_this_sitting >= a.max_batches:
            print(f"  stopping: reached --max-batches {a.max_batches}", file=sys.stderr)
            break
        batch_dir.mkdir(parents=True, exist_ok=True)
        print(f"  batch {i:03d}: {chunk[0].stem}..{chunk[-1].stem}", file=sys.stderr)
        m = run_batch(spec, binary, prompt, a.model, chunk, batch_dir, a.timeout, env)
        run_meta["batches"].append({"batch": i, **{k: m.get(k) for k in
                                                   ("exit_code", "wall_clock_seconds",
                                                    "predictions_written", "prediction_rows",
                                                    "timed_out") if k in m}})
        done_this_sitting += 1
        print(f"    exit={m['exit_code']} {m['wall_clock_seconds']}s rows={m.get('prediction_rows', 0)}",
              file=sys.stderr)

    n = merge_predictions(run)
    run_meta["merged_prediction_rows"] = n
    run_meta["expected_rows"] = len(genomes) * N_ANTIBIOTICS
    run_meta["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (run / "run_meta.json").write_text(json.dumps(run_meta, indent=2))

    print(f"\nmerged {n} of {len(genomes) * N_ANTIBIOTICS} expected rows -> {run / 'predictions.tsv'}")
    missing = [b["batch"] for b in run_meta["batches"] if b.get("predictions_written") is False]
    if missing:
        print(f"batches without predictions: {missing}", file=sys.stderr)


if __name__ == "__main__":
    main()
