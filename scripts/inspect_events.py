#!/usr/bin/env python3
"""Summarise a run's event stream so the parser can be written against it.

    python scripts/inspect_events.py runs/claude/rep0 runs/gemini/rep0

For each run, prints the event types seen, how often, and one truncated
example of each, so the shapes are visible without dumping megabytes.
"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

CUT = 220


def shorten(obj, depth: int = 0):
    if isinstance(obj, str):
        return obj if len(obj) <= CUT else obj[:CUT] + f"...<{len(obj)} chars>"
    if isinstance(obj, list):
        if depth >= 3:
            return f"<list of {len(obj)}>"
        return [shorten(x, depth + 1) for x in obj[:3]] + ([f"...<{len(obj)} items>"] if len(obj) > 3 else [])
    if isinstance(obj, dict):
        if depth >= 4:
            return f"<dict keys={list(obj)[:8]}>"
        return {k: shorten(v, depth + 1) for k, v in list(obj.items())[:15]}
    return obj


def kind(ev: dict) -> str:
    """A label fine-grained enough to show each distinct event shape."""
    for key in ("type", "event", "kind", "msg_type"):
        if key in ev and isinstance(ev[key], str):
            label = ev[key]
            inner = ev.get(label) or ev.get("message") or ev.get("msg") or ev.get("payload")
            if isinstance(inner, dict):
                # Gemini: step_update.step_type / .state; Claude: message.content[].type
                for k2 in ("step_type", "subtype", "type", "role", "event"):
                    if isinstance(inner.get(k2), str):
                        label = f"{label}/{inner[k2]}"
                        break
                content = inner.get("content")
                if isinstance(content, list) and content and isinstance(content[0], dict):
                    blocks = sorted({b.get("type") for b in content if isinstance(b, dict) and b.get("type")})
                    if blocks:
                        label += "[" + ",".join(blocks) + "]"
            return label
    return "(no type key) keys=" + ",".join(sorted(ev)[:6])


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: inspect_events.py <run dir> [<run dir> ...]")
    for d in sys.argv[1:]:
        run = Path(d)
        print(f"\n{'=' * 70}\n{run}")
        meta = run / "meta.json"
        if meta.exists():
            m = json.loads(meta.read_text())
            print("meta:", {k: m.get(k) for k in
                            ("arm", "exit_code", "wall_clock_seconds", "prediction_rows",
                             "model_requested", "n_isolates")})
        ev_path = run / "events.jsonl"
        if not ev_path.exists():
            print("no events.jsonl")
            continue
        counts, examples = Counter(), OrderedDict()
        bad = 0
        for line in ev_path.open(encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if not isinstance(ev, dict):
                continue
            k = kind(ev)
            counts[k] += 1
            examples.setdefault(k, ev)
        print(f"{sum(counts.values())} events, {len(counts)} types, {bad} unparsed lines")
        for k, n in counts.most_common():
            print(f"\n--- {k}  (n={n})")
            print(json.dumps(shorten(examples[k]), indent=2, ensure_ascii=False)[:1600])


if __name__ == "__main__":
    main()
