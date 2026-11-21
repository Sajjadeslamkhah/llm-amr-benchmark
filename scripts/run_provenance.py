#!/usr/bin/env python3
"""Collect what each run actually was, for the methods table.

    python scripts/run_provenance.py --out results/provenance.tsv

The manuscript has to state the model identifier, harness version, plan tier and
date for every arm, and the Gemini arm ran a week after the others, so a single
name per vendor would be wrong. Everything here is read from each batch's
meta.json and from the harness event stream; nothing is inferred from the vendor
name, and a field that is absent is reported as absent rather than guessed.

Also reports, per arm: the number of batches, wall-clock seconds per batch, and
the web-search and web-fetch counts a harness recorded, which is the evidence for
the network claims in the methods section.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

MODEL_KEYS = ("model", "model_id", "modelId", "model_name", "slug")
VERSION_KEYS = ("version", "harness_version", "cli_version", "agy_version")
TIER_KEYS = ("plan", "tier", "plan_tier", "subscription")
# The harness writes these; the first key list was guessed and matched none of them.
DATE_KEYS = ("started_utc", "started", "start", "started_at", "date", "timestamp")
DUR_KEYS = ("wall_clock_seconds", "duration_seconds", "seconds", "duration_s", "elapsed")


def dig(obj, keys: tuple[str, ...]) -> set[str]:
    """Every value under any of these keys, anywhere in the object."""
    found: set[str] = set()
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and isinstance(v, str) and v.strip():
                    found.add(v.strip())
                stack.append(v)
        elif isinstance(o, list):
            stack.extend(o)
    return found


def numbers(obj, keys: tuple[str, ...]) -> list[float]:
    """Every numeric value under any of these keys. dig() only returns strings, and
    the harness writes wall_clock_seconds as a number, so durations were all missed."""
    out: list[float] = []
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(float(v))
                stack.append(v)
        elif isinstance(o, list):
            stack.extend(o)
    return out


def from_events(p: Path) -> dict:
    """Model name and the web-tool counters, which only the result event carries."""
    out: dict[str, set[str] | int] = {"model": set(), "web_search": 0, "web_fetch": 0}
    for line in p.read_text(errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        out["model"] |= dig(ev, MODEL_KEYS)
        for k, field in (("web_search", "web_search_requests"), ("web_fetch", "web_fetch_requests")):
            for v in dig(ev, (field,)):
                try:
                    out[k] = max(int(out[k]), int(v))
                except (TypeError, ValueError):
                    pass
            # the counter is usually a number, which dig() skips
            stack = [ev]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    v = o.get(field)
                    if isinstance(v, int):
                        out[k] = max(int(out[k]), v)
                    stack.extend(o.values())
                elif isinstance(o, list):
                    stack.extend(o)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--out", default="results/provenance.tsv")
    a = ap.parse_args()

    root = Path(a.runs)
    rows = []
    for rep in sorted(root.glob("*/rep*")):
        if not rep.is_dir():
            continue
        arm = rep.parent.name
        models: set[str] = set()
        versions: set[str] = set()
        tiers: set[str] = set()
        dates: set[str] = set()
        durations: list[float] = []
        web = defaultdict(int)
        binaries: set[str] = set()
        failed: list[str] = []
        batches = sorted(rep.glob("batch_*"))
        for b in batches:
            meta = b / "meta.json"
            if meta.exists():
                try:
                    m = json.loads(meta.read_text(errors="replace"))
                except json.JSONDecodeError:
                    m = {}
                models |= dig(m, MODEL_KEYS)
                versions |= dig(m, VERSION_KEYS)
                tiers |= dig(m, TIER_KEYS)
                for v in dig(m, DATE_KEYS):
                    dates.add(v[:10])
                durations += numbers(m, DUR_KEYS)
                for v in dig(m, ("command",)):
                    if "/" in v and not v.startswith("-"):
                        binaries.add(Path(v).name)
                cmd = m.get("command")
                if isinstance(cmd, list) and cmd:
                    binaries.add(Path(str(cmd[0])).name)
                code = m.get("exit_code")
                if isinstance(code, int) and code != 0:
                    failed.append(f"{b.name}:{code}")
            ev = b / "events.jsonl"
            if ev.exists():
                e = from_events(ev)
                models |= e["model"]
                web["search"] += int(e["web_search"])
                web["fetch"] += int(e["web_fetch"])
        rows.append({
            "arm": arm, "replicate": rep.name, "batches": len(batches),
            "binary": "; ".join(sorted(binaries)) or "(not recorded)",
            "nonzero_exit_batches": "; ".join(failed) or "none",
            "model_ids": "; ".join(sorted(models)) or "(not recorded)",
            "harness_version": "; ".join(sorted(versions)) or "(not recorded)",
            "plan_tier": "; ".join(sorted(tiers)) or "(not recorded)",
            "run_dates": "; ".join(sorted(dates)) or "(not recorded)",
            "median_batch_seconds": round(sorted(durations)[len(durations) // 2], 1) if durations else "",
            "web_search_requests": web["search"], "web_fetch_requests": web["fetch"],
        })

    if not rows:
        raise SystemExit(f"No run directories under {root}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[k]) for k in rows[0]) + "\n")

    for r in rows:
        if not r["batches"]:
            continue
        print(f"{r['arm']} {r['replicate']}: {r['batches']} batches, {r['run_dates']}")
        print(f"  model   : {r['model_ids']}")
        print(f"  harness : {r['binary']} {r['harness_version']}   plan: {r['plan_tier']}")
        print(f"  batch s : median {r['median_batch_seconds']}   failed: {r['nonzero_exit_batches']}")
        print(f"  web tools: {r['web_search_requests']} searches, {r['web_fetch_requests']} fetches")
    print(f"\n{out}")
    if any(r["model_ids"] == "(not recorded)" for r in rows if r["batches"]):
        print("\nAt least one arm has no model identifier in its logs. The methods table needs\n"
              "one per arm and the Gemini arm ran a week after the others, so a single name per\n"
              "vendor would be wrong. Record it from the harness before the replicates.")


if __name__ == "__main__":
    main()
