#!/usr/bin/env python3
"""Does an agent's own uncertainty flag pick out the calls it got wrong?

    python scripts/uncertainty.py \
        --ref ~/amr_gizli/reference_phenotypes.tsv \
        --key ~/amr_gizli/blinding_key.tsv \
        --run claude=runs/claude/rep1 \
        --run gpt=runs/gpt/rep1 \
        --out results/uncertainty.tsv

Post-hoc and exploratory, added 2026-11-21. It is not part of the pre-registered
analysis and no confirmatory claim rests on it. It exists because the H3 screen
turned up mostly hedges rather than invented rules: both agents marked some of
their own calls as uncertain, and whether those are the wrong ones is a question
with a clinical answer. A flagged call is one a laboratory could rerun, so an
agent whose flags cover most of its very major errors would be usable in a way
that its raw error rate alone does not show.

Two independent signals, reported separately and together:

  evidence  the call's own evidence field hedges (per call, unambiguous)
  listed    the call appears under a heading about uncertain calls in the
            agent's narrative

The script refuses to report a result when neither signal fires, because "the
flags do not predict errors" and "the flags were never found" would otherwise
look the same.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

HEDGE = re.compile(r"\b(?:low confidence|least certain|less certain|could go either way"
                   r"|could test|may test|might test|uncertain\w*|borderline|equivocal"
                   r"|cannot be certain|not conclusive|unclear|ambiguous|provisional)\b", re.I)
HEADING = re.compile(r"^#{1,6}\s*.*uncertain.*$", re.I | re.M)
ISO = re.compile(r"ISO_\d{3}")
ABX = ("ampicillin", "cefotaxime", "meropenem", "ciprofloxacin", "gentamicin",
       "trimethoprim/sulfamethoxazole", "trimethoprim-sulfamethoxazole", "tmp-smx",
       "co-trimoxazole", "sxt")
CANON = {"trimethoprim-sulfamethoxazole": "trimethoprim/sulfamethoxazole",
         "tmp-smx": "trimethoprim/sulfamethoxazole",
         "co-trimoxazole": "trimethoprim/sulfamethoxazole",
         "sxt": "trimethoprim/sulfamethoxazole"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def read_tsv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def narrative(run: Path) -> str:
    parts = []
    for name in ("methods.md", "transcript.txt"):
        f = run / name
        if f.exists():
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def listed_uncertain(text: str) -> set[tuple[str, str]]:
    """Calls named under a heading about uncertain calls.

    The block runs to the next heading. Within it, every isolate code is paired with
    every antibiotic named on the same line, so a line listing two drugs for one
    isolate yields two calls.
    """
    out: set[tuple[str, str]] = set()
    marks = [m for m in HEADING.finditer(text)]
    ends = [m.start() for m in re.finditer(r"^#{1,6}\s", text, re.M)]
    for m in marks:
        nxt = min((e for e in ends if e > m.end()), default=len(text))
        # from m.start(), not m.end(): both agents wrote the calls on the heading line
        # itself ("## Uncertain calls - ISO_052 ciprofloxacin"), so scanning only after
        # the heading skipped exactly the lines this measure is about
        current: list[str] = []
        for line in text[m.start():nxt].splitlines():
            isos = ISO.findall(line)
            low = line.lower()
            drugs = {CANON.get(a, a) for a in ABX if a in low}
            if isos:
                current = isos
            if not current:
                continue
            for i in (isos or current):
                for d in drugs:
                    out.add((i, d))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--run", action="append", required=True, help="arm=run_directory")
    ap.add_argument("--out", default="results/uncertainty.tsv")
    a = ap.parse_args()

    ref = {(r["genome_id"], r["abx"]): r["pheno"] for r in read_tsv(Path(a.ref))}
    iso_of = {r["genome_id"]: r["isolate_id"] for r in read_tsv(Path(a.key))}
    truth = {(iso_of[g], abx): ph for (g, abx), ph in ref.items() if g in iso_of}

    rows = []
    for spec in a.run:
        arm, rundir = spec.split("=", 1)
        run = Path(rundir)
        preds = read_tsv(run / "predictions.tsv")
        text = narrative(run)
        listed = listed_uncertain(text)

        by_evidence, calls = set(), {}
        for r in preds:
            k = ((r.get("isolate_id") or "").strip(), (r.get("antibiotic") or "").strip())
            calls[k] = (r.get("prediction") or "").strip().upper()
            if HEDGE.search(r.get("evidence") or ""):
                by_evidence.add(k)

        # Abstention. A pair is abstained when the agent wrote NA for it OR wrote no
        # row for it at all: Claude's 8 no-calls and 14 of GPT's 24 are missing rows,
        # not NA values, so reading only the rows present missed most of them.
        made = {k for k, p in calls.items() if p in ("S", "R") and k in truth}
        abstained = {k for k in truth if k not in made}

        # Whether a flag predicts an error is asked ONLY of calls the agent made.
        # Counting an abstention as an error made the question circular: under the
        # pre-registered scoring a no-call is an error by definition, so a flag set
        # that includes abstentions is wrong 100% of the time whatever it tracks.
        wrong = {k for k in made if calls[k] != truth[k]}
        vme_made = {k for k in wrong if truth[k] == "R"}
        for label, flagged in (("evidence", by_evidence), ("listed", listed),
                               ("either", by_evidence | listed)):
            fl = {k for k in made if k in flagged}
            un = made - fl
            fw = len(fl & wrong)
            uw = len(un & wrong)
            p_f, lo_f, hi_f = wilson(fw, len(fl))
            p_u, lo_u, hi_u = wilson(uw, len(un))
            rows.append({
                "arm": arm, "signal": label, "calls_made": len(made),
                "flagged": len(fl), "unflagged": len(un),
                "errors_total": len(wrong), "errors_flagged": fw,
                "error_rate_flagged": round(p_f, 4), "erf_lo": round(lo_f, 4), "erf_hi": round(hi_f, 4),
                "error_rate_unflagged": round(p_u, 4), "eru_lo": round(lo_u, 4), "eru_hi": round(hi_u, 4),
                "vme_total": len(vme_made), "vme_flagged": len(fl & vme_made),
                "abstained": len(abstained), "abstained_ref_R": sum(1 for k in abstained if truth[k] == "R"),
            })

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    for r in rows:
        if r["signal"] != "either":
            continue
        print(f"{r['arm']}: made {r['calls_made']} calls, abstained on {r['abstained']} "
              f"({r['abstained_ref_R']} of those are resistant in the laboratory data)")
        print(f"  flagged {r['flagged']} of the calls it made, {r['unflagged']} not")
        print(f"  error rate   flagged {r['error_rate_flagged']:.3f} "
              f"[{r['erf_lo']:.3f}-{r['erf_hi']:.3f}]   "
              f"unflagged {r['error_rate_unflagged']:.3f} "
              f"[{r['eru_lo']:.3f}-{r['eru_hi']:.3f}]")
        print(f"  of {r['vme_total']} very major errors among the calls it made, "
              f"{r['vme_flagged']} were flagged")

    if all(r["flagged"] == 0 for r in rows):
        raise SystemExit(
            "\nNo uncertainty flag was found for any call in any arm. That is a parsing\n"
            "failure, not a result: reporting it would read as 'the agents never flagged\n"
            "anything', which the logs contradict. Check how the agents wrote their\n"
            "uncertain calls and widen the patterns before using this output.")
    print(f"\n{out}")
    print("Post-hoc and exploratory. Not part of the pre-registered analysis.")


if __name__ == "__main__":
    main()
