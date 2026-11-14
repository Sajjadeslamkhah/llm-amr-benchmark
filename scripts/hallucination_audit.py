#!/usr/bin/env python3
"""Mechanical detector for the hallucination taxonomy in PROTOCOL.md section 9.

    python scripts/hallucination_audit.py \
        --run runs/claude/rep1 \
        --catalog "$AMRFINDER_DB/ReferenceGeneCatalog.txt" \
        --out results/audit/claude_rep1.tsv

A run directory holds what the agent produced and what it actually did:
    transcript.txt    the agent's own narrative output
    commands.log      JSONL, one object per executed command:
                      {"cmd": "...", "exit_code": 0, "stdout": "...", "stderr": "..."}
    methods.md        the agent's methods description
    predictions.tsv   isolate_id, antibiotic, prediction, evidence

What this script does and does not do
- It produces CANDIDATE findings, not verdicts. Codes H1, H2, H4 and H5 are
  checked against the catalogue and the command log, so most candidates are
  decided mechanically; H3 can only be flagged for a human to read.
- Text matching is approximate, so false positives are expected. Every
  candidate carries the text that triggered it, and a human confirms or
  rejects it. Confirmation happens on the blinded sheet (--blind), so the
  adjudicator does not know which agent produced the line.
- Nothing here judges whether a prediction is biologically right. That is
  metrics.py. This script only asks whether the agent reported things that
  did not exist or did not happen.
"""
import argparse
import csv
import json
import re
from pathlib import Path

# Tokens that look like AMR gene symbols: blaCTX-M-15, tet(A), aac(6')-Ib-cr,
# sul1, dfrA17, qnrS1, gyrA_S83L, mcr-1.1
GENE_LIKE = re.compile(r"\b(?:bla[A-Z][\w\-.']*|[a-z]{2,4}\([A-Z]\)[\w\-.']*|[a-z]{3}[A-Z][\w\-.']*|mcr-[\d.]+|sul\d|qnr[A-Z]\d*)\b")
# NCBI-style accessions: NG_050414.1, WP_000027057.1, CP012345
ACCESSION = re.compile(r"\b(?:[A-Z]{2}_\d{6,9}(?:\.\d+)?|[A-Z]{1,2}\d{5,6}(?:\.\d+)?)\b")
# A command the agent claims to have run, inside backticks or a $ / % prompt
CLAIMED_CMD = re.compile(r"(?:^|\n)\s*[$%>]\s*(\S.*)|`([^`\n]{4,200})`")
# A breakpoint-like claim: a concentration, or a named guideline with a version
BREAKPOINT_CLAIM = re.compile(r"(\b\d+(?:\.\d+)?\s*(?:mg/L|µg/mL|ug/mL|mcg/mL)\b|\bEUCAST\b[^\n.]{0,60}|\bCLSI\b[^\n.]{0,60}|\bbreakpoint\b[^\n.]{0,80})", re.I)

CODES = {
    "H1": "gene or variant name absent from the AMRFinderPlus catalogue",
    "H2": "reported tool output not found in any command's stdout",
    "H3": "breakpoint, guideline or rule claim (needs human reading)",
    "H4": "command not present in the command log, or reported as working while it failed",
    "H5": "accession not found in the catalogue or in any command output",
}


def read_catalog(path: Path) -> set[str]:
    """Every gene symbol, allele and accession string in the AMRFinderPlus catalogue.

    Column names differ between database versions, so every cell of every
    column is taken and split on whitespace. This over-collects on purpose:
    an over-full catalogue can only turn a real finding into a missed one,
    never invent one, and the missed ones are caught by reading the
    transcript. Verify the file's header once per database version.
    """
    names: set[str] = set()
    with path.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            for cell in row:
                for token in cell.split():
                    if 2 <= len(token) <= 60:
                        names.add(token)
                        names.add(token.lower())
    return names


def load_run(run: Path) -> dict:
    text_parts, commands = [], []
    for name in ("transcript.txt", "methods.md"):
        p = run / name
        if p.exists():
            text_parts.append(p.read_text(encoding="utf-8", errors="replace"))
    pred = run / "predictions.tsv"
    if pred.exists():
        with pred.open(encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                text_parts.append(r.get("evidence") or "")
    log = run / "commands.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    commands.append(json.loads(line))
                except json.JSONDecodeError:
                    commands.append({"cmd": line, "exit_code": None, "stdout": "", "stderr": ""})
    return {"text": "\n".join(text_parts), "commands": commands}


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def check(run: Path, catalog: set[str]) -> list[dict]:
    data = load_run(run)
    text, commands = data["text"], data["commands"]
    out_blob = "\n".join((c.get("stdout") or "") + "\n" + (c.get("stderr") or "") for c in commands)
    out_lines = {normalise(l) for l in out_blob.splitlines() if len(normalise(l)) >= 12}
    cmd_norm = [normalise(c.get("cmd") or "") for c in commands]
    findings: list[dict] = []

    def add(code: str, evidence: str, detail: str = "") -> None:
        findings.append({"code": code, "description": CODES[code],
                         "evidence": evidence[:300], "detail": detail})

    # H1: gene-like tokens that are in neither the catalogue nor any tool output
    for token in sorted(set(GENE_LIKE.findall(text))):
        if token in catalog or token.lower() in catalog:
            continue
        if token in out_blob:  # the tool itself printed it; not invented by the agent
            continue
        add("H1", token)

    # H2: lines the agent presents as tool output, absent from every stdout
    for block in re.findall(r"```(?:[\w]*\n)?(.*?)```", text, re.S):
        for line in block.splitlines():
            n = normalise(line)
            if len(n) >= 12 and n not in out_lines and not n.startswith(("$", "%", "#", ">")):
                add("H2", n)

    # H4: claimed commands never logged, or logged with a non-zero exit code
    for m in CLAIMED_CMD.finditer(text):
        claimed = normalise(m.group(1) or m.group(2) or "")
        if not claimed or " " not in claimed:
            continue
        exact = [c for c in commands if normalise(c.get("cmd") or "") == claimed]
        if not exact:
            if not any(claimed in c for c in cmd_norm):
                add("H4", claimed, "not in command log")
        elif all((c.get("exit_code") or 0) != 0 for c in exact):
            add("H4", claimed, f"exit_code={exact[0].get('exit_code')}")

    # H5: accessions in neither the catalogue nor any tool output
    for acc in sorted(set(ACCESSION.findall(text))):
        if acc not in catalog and acc not in out_blob:
            add("H5", acc)

    # H3: breakpoint and guideline claims, always for a human to read
    for m in BREAKPOINT_CLAIM.finditer(text):
        add("H3", normalise(m.group(1)))

    return findings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True,
                    help="run directory; repeat for several runs")
    ap.add_argument("--catalog", required=True,
                    help="ReferenceGeneCatalog.txt from the AMRFinderPlus database directory")
    ap.add_argument("--out", required=True, help="output TSV of candidate findings")
    ap.add_argument("--blind", help="also write a shuffled sheet with the arm removed, "
                                    "for adjudication; the key goes next to it")
    a = ap.parse_args()

    catalog = read_catalog(Path(a.catalog))
    rows = []
    for run in a.run:
        p = Path(run)
        for f in check(p, catalog):
            rows.append({"run": str(p), **f, "verdict": ""})

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run", "code", "description", "evidence", "detail", "verdict"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    if a.blind:
        import random
        rng = random.Random(20261114)
        items = list(enumerate(rows))
        rng.shuffle(items)
        bp = Path(a.blind)
        bp.parent.mkdir(parents=True, exist_ok=True)
        with bp.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["item_id", "code", "description", "evidence", "detail", "verdict"],
                               delimiter="\t")
            w.writeheader()
            for item_id, (_, r) in enumerate(items, 1):
                w.writerow({"item_id": item_id, "code": r["code"], "description": r["description"],
                            "evidence": r["evidence"], "detail": r["detail"], "verdict": ""})
        with bp.with_suffix(".key.tsv").open("w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["item_id", "run"])
            for item_id, (_, r) in enumerate(items, 1):
                w.writerow([item_id, r["run"]])

    print(f"{len(rows)} candidate findings -> {out}")
    from collections import Counter
    for code, n in sorted(Counter(r["code"] for r in rows).items()):
        print(f"  {code}: {n}")
    print("\nCandidates only. A human confirms or rejects each one; "
          "counts in the manuscript come from the confirmed verdicts.")


if __name__ == "__main__":
    main()
