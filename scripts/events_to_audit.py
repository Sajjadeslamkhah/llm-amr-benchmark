#!/usr/bin/env python3
"""Normalise each vendor's event stream into what hallucination_audit.py reads.

    python scripts/events_to_audit.py --run runs/claude/rep1

Each agent CLI writes a different JSONL shape, so this walks every object and
pulls out (command, output, exit code) triples and the agent's own narrative.
It writes, in the run directory:

    commands.log      one JSON object per executed command
    transcript.txt    the agent's narrative text, batch by batch
    methods.md        the methods files the agent wrote, concatenated

It REFUSES to write an empty commands.log. A silent zero would make the
hallucination audit report "no fabricated tool output" for an arm whose commands
were never read at all, which is worse than no audit. On zero it prints the keys
it did see, so the extractor can be fixed against the real shape.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

# Keys that have held a shell command, an output, and an exit code, per vendor.
CMD_KEYS = ("CommandLine", "command", "cmd", "Command", "shell_command")
OUT_KEYS = ("output", "aggregated_output", "stdout", "Output", "result", "content")
EXIT_KEYS = ("exit_code", "exitCode", "returncode", "ExitCode", "status_code")
# Tool names that run a shell command. Anything else (file read, search) is not
# a command for the H4 check, so it is counted separately rather than guessed at.
SHELL_TOOLS = {"bash", "run_command", "shell", "command_execution", "local_shell",
               "run_terminal_command", "execute_command"}


def walk(obj, path=(), parents=()):
    """Every dict in the object, with the key path and the ancestor dicts that reached it.

    The ancestors matter: a command sits under "input" or "parameters", while the tool's
    name and its output sit on the dict above it.
    """
    if isinstance(obj, dict):
        yield path, obj, parents
        for k, v in obj.items():
            yield from walk(v, path + (k,), parents + (obj,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),), parents)


def first(d: dict, keys) -> str | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
    return None


def tool_name(d: dict, parents) -> str:
    """The tool's name, from the command's dict or, failing that, the dicts above it."""
    for cand in (d,) + tuple(reversed(parents)):
        for k in ("tool_name", "name", "tool"):
            v = cand.get(k)
            if isinstance(v, str) and v.strip() and v.strip().lower() not in ("input", "parameters"):
                return v.strip().lower()
        t = cand.get("type")
        if isinstance(t, str) and t.strip().lower() in SHELL_TOOLS:
            return t.strip().lower()
    return ""


def extract(p: Path) -> tuple[list[dict], list[str], Counter]:
    cmds: list[dict] = []
    narrative: list[str] = []
    seen: Counter = Counter()
    results: dict[str, str] = {}   # tool_use_id -> output, for CLIs that send it separately
    errors: dict[str, bool] = {}   # tool_use_id -> is_error, same reason
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        for path, d, parents in walk(ev):
            # a tool result that arrives in its own event, keyed back to the call
            tid = d.get("tool_use_id") or d.get("toolUseId")
            if isinstance(tid, str) and tid:
                c = d.get("content")
                if isinstance(c, str) and c.strip():
                    results[tid] = c
                elif isinstance(c, list):
                    txt = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    if txt.strip():
                        results[tid] = txt
                if isinstance(d.get("is_error"), bool):
                    errors[tid] = d["is_error"]
            cmd = first(d, CMD_KEYS)
            if cmd:
                name = tool_name(d, parents)
                seen[name or "?"] += 1
                # the output sits on the command's dict, or on one of the dicts above it
                out = first(d, OUT_KEYS) or ""
                code = first(d, EXIT_KEYS)
                for up in reversed(parents):
                    if not out:
                        out = first(up, OUT_KEYS) or ""
                    if code is None:
                        code = first(up, EXIT_KEYS)
                if code is None:
                    # Claude Code marks failure with is_error instead of an exit code.
                    # Mapped to 1/0 so H4 is measurable for every arm, not just the
                    # ones whose CLI happens to report a numeric status.
                    for cand in (d,) + tuple(reversed(parents)):
                        e = cand.get("is_error")
                        if isinstance(e, bool):
                            code = "1" if e else "0"
                            break
                # the id of the call, so a separately sent result can be matched to it
                call_id = None
                for cand in (d,) + tuple(reversed(parents)):
                    v = cand.get("id")
                    if isinstance(v, str) and v:
                        call_id = v
                        break
                cmds.append({"cmd": cmd, "exit_code": int(code) if code and str(code).lstrip("-").isdigit() else None,
                             "stdout": out, "stderr": "", "tool": name, "source": p.name,
                             "call_id": call_id, "key_path": ".".join(path)})
            # the agent's own prose: a text block, not a tool result
            t = d.get("text")
            if isinstance(t, str) and t.strip() and "tool_use_id" not in d:
                narrative.append(t)
            r = d.get("response")
            if isinstance(r, str) and r.strip():
                narrative.append(r)
    for c in cmds:                      # fill in what came in a later event
        cid = c.get("call_id")
        if not c["stdout"] and cid in results:
            c["stdout"] = results[cid]
        if c["exit_code"] is None and cid in errors:
            c["exit_code"] = 1 if errors[cid] else 0
    return cmds, narrative, seen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="a run directory, e.g. runs/claude/rep1")
    ap.add_argument("--allow-empty", action="store_true",
                    help="write the files even with no commands found (do not use for a real audit)")
    ap.add_argument("--debug-paths", action="store_true",
                    help="show which key paths the commands came from, to find double counting")
    a = ap.parse_args()
    run = Path(a.run)
    logs = sorted(run.glob("batch_*/events.jsonl"))
    if not logs:
        raise SystemExit(f"No batch_*/events.jsonl under {run}")

    all_cmds: list[dict] = []
    all_text: list[str] = []
    seen: Counter = Counter()
    for p in logs:
        c, t, s = extract(p)
        for row in c:
            row["batch"] = p.parent.name
        all_cmds += c
        all_text.append(f"===== {p.parent.name} =====\n" + "\n".join(t))
        seen += s

    shell = [c for c in all_cmds if c["tool"] in SHELL_TOOLS]
    print(f"{run}: {len(logs)} event logs")
    print(f"  commands found : {len(all_cmds)}  (of which shell tools: {len(shell)})")
    print(f"  narrative chars: {sum(len(t) for t in all_text)}")
    print("  tool names seen: " + (", ".join(f"{k}={v}" for k, v in seen.most_common(8)) or "(none)"))
    withcode = sum(1 for c in all_cmds if c["exit_code"] is not None)
    print(f"  with exit code : {withcode} of {len(all_cmds)}")
    if a.debug_paths:
        paths = Counter((c["key_path"], c["tool"] or "(no name)") for c in all_cmds)
        print("  key paths:")
        for (kp, t), n in paths.most_common(12):
            print(f"    {n:5d}  tool={t:18s} {kp}")
    for c in all_cmds[:3]:
        print(f"    sample: [{c['tool']}] exit={c['exit_code']} {c['cmd'][:90]}")

    if not all_cmds and not a.allow_empty:
        raise SystemExit(
            "\nNo commands extracted. Not writing commands.log: an empty one would make the\n"
            "audit report 'no fabricated tool output' for an arm whose commands were never read.\n"
            "Send the tool names above and one event line so the extractor can be fixed:\n"
            f"  head -c 2000 {logs[0]}")

    (run / "commands.log").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in all_cmds))
    (run / "transcript.txt").write_text("\n\n".join(all_text))
    methods = [f"===== {m.parent.parent.name} =====\n{m.read_text(errors='replace')}"
               for m in sorted(run.glob("batch_*/output/methods.md"))]
    if methods:
        (run / "methods.md").write_text("\n\n".join(methods))
    print(f"  wrote commands.log, transcript.txt" + (f", methods.md ({len(methods)} files)" if methods else
          "  [no methods.md found under batch_*/output/]"))


if __name__ == "__main__":
    main()
