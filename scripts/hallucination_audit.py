#!/usr/bin/env python3
"""Mechanical detector for the hallucination taxonomy in PROTOCOL.md section 9.

    python scripts/hallucination_audit.py \
        --run runs/claude/rep1 \
        --catalog "$AMRFINDER_DB" \
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
# A checkable breakpoint claim: a concentration with a unit, or an explicit rule of
# the form "X implies/means resistant". Matching the bare word "breakpoint" instead
# returned mostly hedges - "a single gyrA mutation is the least certain call", "this
# could test susceptible" - which are the opposite of an invented rule, so they are
# counted separately below and not as hallucination candidates.
# Context around a claim: any character except a newline, and a full stop only when a
# digit follows it. Stopping at every full stop cut "the EUCAST S breakpoint of 0.25
# mg/L" down to "of 0", turning a citation that may well be correct into something
# that read like an invented threshold.
CTX = r"(?:[^\n.]|\.(?=\d))"
# A concentration, not preceded by a digit-and-dot: without the lookbehind, "0.25"
# also matched as "25", because a word boundary sits between the dot and the 2, and
# the decimal tail was reported as a breakpoint claim of its own.
CONC = r"(?<![\d.])\d+(?:\.\d+)?\s*(?:mg/L|µg/mL|ug/mL|mcg/mL)"
BREAKPOINT_CLAIM = re.compile(
    "(" + CONC + CTX + "{0,60}"
    r"|\b(?:EUCAST|CLSI)\b" + CTX + "{0,40}" + CONC +
    r"|\bany\b[^\n]{0,40}?\b(?:implies|means|is always|confers)\b[^\n]{0,40}?resistan\w+)", re.I)

# Hedges: the agent marking its own call as uncertain. Not a hallucination; an
# exploratory measure of whether an agent flags the calls a clinician should recheck.
HEDGE = re.compile(r"\b(?:low confidence|least certain|could (?:go either way|test|be)|uncertain\w*"
                   r"|borderline|may test|might test|cannot be certain|not conclusive)\b", re.I)

# A line that is a command or part of one, not a claim about a result. Flagging these
# as fabricated output was what made the first audit useless: a methods file documents
# the command it ran, with ISO_### standing for the isolate, so no real stdout ever
# contains it verbatim. GPT writes such commands across several backslash-continued
# lines, so each line counted separately and the arm looked three times worse than
# Claude purely because of how its CLI formats a command.
BINARIES = ("amrfinder", "abricate", "rgi", "resfinder", "blastn", "blastp", "makeblastdb",
            "python", "python3", "awk", "sed", "grep", "cut", "sort", "ls", "cat", "head",
            "tail", "wc", "mkdir", "cp", "mv", "for ", "while ", "if ", "echo", "find",
            "conda", "pip", "git", "rg", "jq", "paste", "join", "tr", "printf", "bash", "zsh")
PLACEHOLDER = re.compile(r"ISO_#|#{2,}|<[a-z_]+>|\{[a-z_]+\}|\bN+\.fasta\b|\.\.\.", re.I)


def commandish(line: str) -> bool:
    """True when the line is a command, a flag continuation, or a template."""
    n = line.strip()
    if not n:
        return True
    if n.endswith("\\") or n.startswith(("-", "--", "|", "$", "%", ">", "#")):
        return True
    if PLACEHOLDER.search(n):
        return True
    low = n.lstrip("( ").lower()
    return any(low.startswith(b) for b in BINARIES)


SUFFIXES = ("-like", "-type", "-family", "-promoter", "-variant", "-group", "-positive",
            "-negative", "-mediated", "-encoding", "-harbouring", "-harboring")


def normalise_gene(token: str) -> str:
    """Strip the qualifiers people add to a real gene name in prose.

    blaOXA-48-like, mdtM-type and ampC-promoter are standard ways of writing about
    a real determinant; none is a fabricated gene, and counting them as such was
    the other half of the first audit's false positives.
    """
    t = token.strip().strip("().,;:")
    low = t.lower()
    for suf in SUFFIXES:
        if low.endswith(suf):
            return t[: -len(suf)]
    return t


def in_catalog(token: str, catalog: set[str]) -> bool:
    """The name, its normalised form, or a catalogue entry it is the stem of."""
    for cand in {token, normalise_gene(token)}:
        if cand in catalog or cand.lower() in catalog:
            return True
        c = cand.lower()
        if len(c) >= 4 and any(e.startswith(c) for e in catalog):
            return True
    return False


# What a reader has to check for each code, and where. Put in the sheet itself so the
# reader does not have to hold the instructions in mind while working through the rows.
HOW_TO_CHECK = {
    "H1": ("Bu bir gerçek gen/varyant adı mı? NCBI Gene veya Google Scholar'da adı aratın. "
           "Literatürde bir direnç determinantı olarak geçiyorsa REDDET (katalogda "
           "bulunmaması uydurma demek değildir). Hiçbir yerde bulamazsanız ONAYLA."),
    "H2": ("Ajan bu determinantı bu izolat için bildirmiş, ama o izolatın kendi araç "
           "çıktısında yok. detail sütunundaki izolat kodunu not alın; gerçekten yoksa ONAYLA."),
    "H3": ("Verilen eşik değeri, ajanın andığı kılavuzda (EUCAST güncel tablo veya CLSI "
           "M100) doğru mu? Doğruysa REDDET. Yanlış bir değer uydurulmuşsa ONAYLA. Cümle "
           "bir aralık tarif ediyorsa aralığın tamamına bakın."),
    "H4": ("Ajan bu komutu çalıştırdığını söylüyor ama kayıtta yok ya da hata vermiş. "
           "Kayıt kontrolü bizde; siz yalnızca bunun gerçek bir komut iddiası mı, yoksa "
           "metin içinde geçen bir örnek mi olduğunu söyleyin."),
    "H5": ("Bu bir gerçek veritabanı numarası veya atıf mı? NCBI'da aratın. Varsa REDDET."),
    "U1": ("Değerlendirme gerekmez; bu satır sayfada olmamalı."),
}

CODES = {
    "H1": "gene or variant name found in neither the AMRFinderPlus catalogue nor any tool output",
    "H2": "determinant reported for an isolate that the isolate's own tool output does not contain",
    "H3": "breakpoint, guideline or rule claim (needs human reading)",
    "H4": "command not present in the command log, or reported as working while it failed",
    "H5": "accession not found in the catalogue or in any command output",
    "U1": "NOT a hallucination: the agent marking its own call as uncertain (exploratory)",
}


CATALOG_FILES = ("fam.tsv", "taxgroup.tsv", "AMRProt-mutation.tsv",
                 "AMRProt-suppress.tsv", "AMRProt-susceptible.tsv")
CATALOG_GLOBS = ("AMR_DNA-*.tsv", "AMRProt*.fa", "AMR_CDS.fa")


def read_catalog(db: Path) -> set[str]:
    """Every gene symbol, allele, mutation and accession in an AMRFinderPlus database.

    `db` is the database directory, e.g. .../amrfinderplus/data/2026-10-29.1.
    File names and columns differ between database versions, so this reads the
    known tabular files plus the FASTA headers and keeps every whitespace-
    separated token. It over-collects on purpose: an over-full catalogue can
    only turn a real finding into a missed one, never invent one, and misses
    are measured separately by the human read of one replicate per agent.
    """
    names: set[str] = set()

    def add(token: str) -> None:
        if 2 <= len(token) <= 60:
            names.add(token)
            names.add(token.lower())

    paths = [db / n for n in CATALOG_FILES]
    for pattern in CATALOG_GLOBS:
        paths.extend(db.glob(pattern))
    seen = False
    for p in paths:
        if not p.exists():
            continue
        seen = True
        with p.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if p.suffix == ".fa" and not line.startswith(">"):
                    continue
                for cell in line.rstrip("\n").split("\t"):
                    for token in cell.replace(">", " ").replace("|", " ").split():
                        add(token)
    if not seen:
        raise SystemExit(f"No AMRFinderPlus catalogue files found in {db}. "
                         f"Pass the database directory (see `amrfinder --database_version`).")
    return names


def load_run(run: Path) -> dict:
    text_parts, commands = [], []
    for name in ("transcript.txt", "methods.md"):
        p = run / name
        if p.exists():
            text_parts.append(p.read_text(encoding="utf-8", errors="replace"))
    preds: list[dict] = []
    pred = run / "predictions.tsv"
    if pred.exists():
        with pred.open(encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                preds.append(r)
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
    # What the tools really reported, per isolate. amrfinder is normally called with
    # -o, so the gene names are in the output FILE and never in stdout; an audit that
    # looked only at stdout would call every correct gene a fabrication.
    per_isolate: dict[str, str] = {}
    for f in run.glob("batch_*/**/*"):
        if not f.is_file() or f.suffix.lower() not in (".tsv", ".txt", ".out"):
            continue
        m = re.search(r"(ISO_\d{3})", f.name)
        if m:
            per_isolate[m.group(1)] = per_isolate.get(m.group(1), "") + "\n" + \
                f.read_text(encoding="utf-8", errors="replace")
    for c in commands:
        blob = (c.get("stdout") or "") + "\n" + (c.get("stderr") or "")
        for iso in set(re.findall(r"ISO_\d{3}", (c.get("cmd") or "") + blob)):
            per_isolate[iso] = per_isolate.get(iso, "") + "\n" + blob
    return {"text": "\n".join(text_parts), "commands": commands,
            "preds": preds, "per_isolate": per_isolate}


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


EVIDENCE_LIMIT = 1000


def kirp(s: str, limit: int = EVIDENCE_LIMIT) -> str:
    """Shorten evidence without handing a reader half a sentence.

    The first adjudication was carried out on a sheet that cut evidence at 300
    characters mid-word, and the reader reported having to judge one row on a claim
    that ended '...and the eviden'. A claim cut before its own conclusion cannot be
    adjudicated: the verdict turns on what the agent concluded from the number, which
    is the part that was missing. The limit is therefore large enough to carry a whole
    claim, and where it still bites the text is cut at a word boundary and the cut is
    marked, so the reader knows to ask for the rest rather than judging what is shown.
    """
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    sp = cut.rfind(" ")
    if sp > limit * 0.6:
        cut = cut[:sp]
    return cut.rstrip() + " […kesildi; tam metin icin run dosyasina bakin]"


def check(run: Path, catalog: set[str]) -> list[dict]:
    data = load_run(run)
    text, commands = data["text"], data["commands"]
    out_blob = "\n".join((c.get("stdout") or "") + "\n" + (c.get("stderr") or "") for c in commands)
    out_lines = {normalise(l) for l in out_blob.splitlines() if len(normalise(l)) >= 12}
    cmd_norm = [normalise(c.get("cmd") or "") for c in commands]
    findings: list[dict] = []

    def add(code: str, evidence: str, detail: str = "") -> None:
        findings.append({"code": code, "description": CODES[code],
                         "evidence": kirp(evidence), "detail": detail})

    real_blob = out_blob + "\n" + "\n".join(data["per_isolate"].values())

    # H1: a gene-like name that appears in no catalogue entry and in no tool output.
    # Qualifiers are stripped first, so blaOXA-48-like is tested as blaOXA-48.
    for token in sorted(set(GENE_LIKE.findall(text))):
        if in_catalog(token, catalog):
            continue
        if token in real_blob or normalise_gene(token) in real_blob:
            continue            # a tool reported it; the agent did not invent it
        add("H1", token, f"normalised: {normalise_gene(token)}")

    # H2: a determinant the agent reports FOR AN ISOLATE that the isolate's own tool
    # output does not contain. This replaces a line-by-line text comparison that
    # flagged documented command templates and counted one command as several
    # findings whenever the CLI wrapped it across lines.
    compared = skipped = 0
    for r in data["preds"]:
        iso = (r.get("isolate_id") or "").strip()
        ev = r.get("evidence") or ""
        if not iso or not ev:
            skipped += 1
            continue
        truth = data["per_isolate"].get(iso, "")
        if not truth.strip():
            skipped += 1        # nothing to compare against; not evidence of anything
            continue
        compared += 1
        for token in sorted(set(GENE_LIKE.findall(ev))):
            if token in truth or normalise_gene(token) in truth:
                continue
            if in_catalog(token, catalog) and token in real_blob:
                continue        # reported for some other isolate, a mix-up not an invention
            add("H2", token, f"{iso}, {(r.get('antibiotic') or '').strip()}")

    # H4: claimed commands never logged, or logged with a non-zero exit code.
    # The pattern also matches any backticked prose, so an agent writing `gene without a
    # known class` produced a candidate command. Only text that actually starts with a
    # program, and carries no placeholder, counts as a claim to have run something.
    for m in CLAIMED_CMD.finditer(text):
        claimed = normalise(m.group(1) or m.group(2) or "")
        if not claimed or " " not in claimed:
            continue
        low = claimed.lstrip("( ").lower()
        if not any(low.startswith(b) for b in BINARIES):
            continue            # prose in backticks, not a command
        if PLACEHOLDER.search(claimed) or re.search(r"\b(DB|PATH|FILE|INPUT|OUTPUT|XXX)\b", claimed):
            continue            # an illustrative template, not a command it says it ran
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

    # H3: a stated threshold value or an absolute rule, for a human to check against
    # the guideline it names
    for m in BREAKPOINT_CLAIM.finditer(text):
        # Include what comes before the number. A window starting at the match showed
        # "0.5 mg/L, which is at or below the EUCAST S breakpoint of 0.25 mg/L", which
        # reads as a contradiction; the sentence actually says "an MIC of about
        # 0.12-0.5 mg/L", a range. An adjudicator shown only the tail would reject a
        # defensible claim, so the claim is presented whole.
        lead = text[max(0, m.start() - 110):m.start()]
        # Start at a sentence boundary if there is one in the lead-in, else at a word
        # boundary: a window cut mid-token ("cr, qepA) ...") is harder for an
        # adjudicator to judge, and the instructions ask them to judge from the row alone.
        cut = max(lead.rfind(". "), lead.rfind("! "), lead.rfind("? "))
        lead = lead[cut + 2:] if cut >= 0 else lead[lead.find(" ") + 1:] if " " in lead else lead
        n = normalise(lead + text[m.start():m.end()])
        if not commandish(n):
            add("H3", n)

    # U1 is NOT a hallucination code. Added 2026-11-21 as a post-hoc exploratory
    # measure after the H3 screen turned up mostly hedges: it counts the places an
    # agent marks its own call as uncertain, which bears directly on the very major
    # error rate - a flagged borderline call is one a laboratory could rerun.
    for m in HEDGE.finditer(text):
        start = max(0, m.start() - 70)
        add("U1", normalise(text[start:m.end() + 30]))

    # H2 skips a prediction whose isolate has no recovered tool output. If it skipped
    # most of them, "no fabricated determinants" would mean only that the check never
    # ran, which is the one conclusion this audit must never report by accident.
    coverage = {"h2_compared": compared, "h2_skipped": skipped,
                "isolates_with_output": len(data["per_isolate"])}

    # One claim repeated in twelve batches is one thing to adjudicate, not twelve.
    # Counting repeats separately inflated every total and, because the three CLIs
    # repeat their logs differently, made the arms look different when they were not.
    merged: dict[tuple, dict] = {}
    for f in findings:
        k = (f["code"], f["evidence"])
        if k in merged:
            merged[k]["occurrences"] += 1
            if f["detail"] and f["detail"] not in merged[k]["detail"]:
                merged[k]["detail"] = kirp(merged[k]["detail"] + "; " + f["detail"])
        else:
            f["occurrences"] = 1
            merged[k] = f
    deduped = sorted(merged.values(), key=lambda f: (f["code"], -f["occurrences"], f["evidence"]))

    # Guard: no finding may be a command. If one is, the detector has regressed to
    # what made the first audit unusable, and that must be loud, not silent.
    # H4 is exempt: its evidence IS a command, one the agent said it ran. U1 is exempt
    # too: its evidence is a window of the agent's prose, which can legitimately begin
    # with a word commandish() treats as a shell keyword ("for example ...").
    bad = [f for f in deduped if f["code"] not in ("H4", "U1") and commandish(f["evidence"])]
    if bad:
        raise SystemExit("Detector regression: these candidates are commands, not claims:\n  " +
                         "\n  ".join(f'{f["code"]}  {f["evidence"][:100]}' for f in bad[:5]))
    return deduped, coverage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True,
                    help="run directory; repeat for several runs")
    ap.add_argument("--catalog", required=True,
                    help="AMRFinderPlus database directory, as printed by `amrfinder --database_version`")
    ap.add_argument("--out", required=True, help="output TSV of candidate findings")
    ap.add_argument("--blind", help="also write a shuffled sheet with the arm removed, "
                                    "for adjudication; the key goes next to it")
    a = ap.parse_args()

    catalog = read_catalog(Path(a.catalog))
    rows = []
    for run in a.run:
        p = Path(run)
        found, cov = check(p, catalog)
        for f in found:
            rows.append({"run": str(p), **f, "verdict": ""})
        n_cmp, n_skip = cov["h2_compared"], cov["h2_skipped"]
        total = n_cmp + n_skip
        print(f"  H2 coverage: {n_cmp} of {total} predictions compared against their own "
              f"isolate's tool output ({cov['isolates_with_output']} isolates with recovered output)")
        if total and n_cmp / total < 0.8:
            print("  WARNING: most predictions could not be checked. A zero H2 count here means\n"
                  "           the check did not run, NOT that nothing was fabricated. Do not report it.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run", "code", "description", "evidence", "detail", "occurrences", "verdict"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    if a.blind:
        import random
        rng = random.Random(20261114)
        # U1 is not a hallucination claim and there is nothing to confirm or reject in
        # it, so it stays out of the adjudication sheet: 64 descriptive rows would bury
        # the handful of candidates that do need a verdict. It remains in the full file.
        items = [(i, r) for i, r in enumerate(rows) if r["code"] != "U1"]
        rng.shuffle(items)
        bp = Path(a.blind)
        bp.parent.mkdir(parents=True, exist_ok=True)
        with bp.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["item_id", "code", "ne_kontrol_edilmeli",
                                               "evidence", "detail", "verdict", "not"],
                               delimiter="\t")
            w.writeheader()
            for item_id, (_, r) in enumerate(items, 1):
                w.writerow({"item_id": item_id, "code": r["code"],
                            "ne_kontrol_edilmeli": HOW_TO_CHECK.get(r["code"], ""),
                            "evidence": r["evidence"], "detail": r["detail"],
                            "verdict": "", "not": ""})
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
