#!/usr/bin/env python3
"""Three-way composition control for the drift observation (post-hoc; PROTOCOL.md section 12).

    python scripts/kompozisyon_analiz.py
    python scripts/kompozisyon_analiz.py --truth ~/amr_gizli/reference_phenotypes.tsv

The question
------------
Replicate 1 saw each subset isolate in a batch of 10 mixed with the other 78 isolates.
Replicates 2 and 3 saw it in a batch of 10 subset-only isolates. So the pairs that moved
between replicate 1 and replicates 2/3 moved across a change of DATE and a change of BATCH
COMPOSITION at the same time, and the manuscript attributed the move to the date alone.

Replicate 4 holds composition at replicate 1's value and moves only the date:

    rep4 == rep2/3  ->  composition is not the explanation; the change is temporal
    rep4 == rep1    ->  composition is the explanation; the drift claim is withdrawn
    neither         ->  a third state; the arm is unstable in a way none of the three capture

What this script will not do
---------------------------
It reports counts, the isolates they come from, and the matched per-batch timing of
replicate 1 against replicate 4. It computes no p-value and declares no
significance: the moved set is a handful of pairs from a handful of isolates, the three
replicates are not independent of each other, and nothing at this size supports a test. The
verdict line names which way the counts point and how few they are.

It refuses to report when a replicate is short, because a missing batch would silently
shrink the common set and change every count below.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_tsv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def calls(path: Path) -> dict[tuple[str, str], str]:
    """Same normalisation as reproducibility.py: anything not S or R is NA."""
    out = {}
    for r in read_tsv(path):
        k = ((r.get("isolate_id") or "").strip(), (r.get("antibiotic") or "").strip())
        v = (r.get("prediction") or "").strip().upper()
        if k[0]:
            out[k] = v if v in ("S", "R") else "NA"
    return out


def batch_seconds(run: Path) -> list[float]:
    """Wall-clock seconds per batch from the runner's own meta.json files.

    Only replicate 1 and replicate 4 are comparable this way: they hold the same 118
    isolates in the same 12 batches of mixed composition, so a median over one is a
    median over the same unit as the other. Replicates 2 and 3 have 4 subset-only
    batches, which is what made the 449-versus-231/265 comparison unmatched.
    """
    out = []
    for m in sorted(run.glob("batch_[0-9][0-9][0-9]/meta.json")):
        try:
            v = json.loads(m.read_text()).get("wall_clock_seconds")
        except (ValueError, OSError):
            continue
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def median(xs: list[float]) -> float | str:
    if not xs:
        return ""
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def truth_map(path: Path) -> dict[tuple[str, str], str]:
    out = {}
    for r in read_tsv(path):
        iso = (r.get("isolate_id") or r.get("genome_id") or "").strip()
        abx = (r.get("antibiotic") or r.get("abx") or "").strip()
        ph = (r.get("phenotype") or r.get("resistant_phenotype") or "").strip().upper()
        if iso and abx and ph in ("S", "R"):
            out[(iso, abx)] = ph
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", default=None,
                    help="repeatable; default claude and gpt")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--subset", default="data/selection/reproducibility_subset.txt")
    ap.add_argument("--truth", default="",
                    help="optional reference phenotypes, kept outside the repository")
    ap.add_argument("--out", default="results/kompozisyon.tsv")
    a = ap.parse_args()
    arms = a.arm or ["claude", "gpt"]

    sub_file = ROOT / a.subset
    if not sub_file.exists():
        sys.exit(f"Alt kume dosyasi yok: {sub_file}")
    subset = {l.strip() for l in sub_file.read_text().splitlines() if l.strip()}

    truth = {}
    if a.truth:
        tp = Path(a.truth).expanduser()
        if not tp.exists():
            sys.exit(f"Referans dosyasi yok: {tp}")
        truth = truth_map(tp)

    rows, problems = [], []
    for arm in arms:
        per = {}
        for rep in ("1", "2", "3", "4"):
            f = ROOT / a.runs / arm / f"rep{rep}" / "predictions.tsv"
            if not f.exists():
                problems.append(f"{arm} rep{rep}: predictions.tsv yok")
                continue
            c = calls(f)
            per[rep] = {k: v for k, v in c.items() if k[0] in subset}
        if len(per) < 4:
            continue

        common = set.intersection(*(set(v) for v in per.values()))
        expected = len(subset) * 6
        if len(common) < expected:
            problems.append(
                f"{arm}: dort tekrarin tamaminda bulunan cift sayisi {len(common)}, "
                f"beklenen {expected}; eksik tekrar sayimlari degistirir")
            continue

        # Replicate 2 and 3 have to agree before "the date B call" means anything.
        rep23 = {k for k in common if per["2"][k] == per["3"][k]}
        moved = sorted(k for k in rep23 if per["1"][k] != per["2"][k])

        verdict = Counter()
        detail = []
        for k in moved:
            r1, r23, r4 = per["1"][k], per["2"][k], per["4"][k]
            if r4 == r23 and r4 != r1:
                side = "zaman"          # temporal
            elif r4 == r1 and r4 != r23:
                side = "bilesim"        # composition
            else:
                side = "ucuncu"         # neither
            verdict[side] += 1
            detail.append((k, r1, r23, r4, side, truth.get(k, "")))

        isolates_moved = {k[0] for k in moved}
        row = {
            "arm": arm,
            "pairs_in_all_four": len(common),
            "rep2_rep3_agree": len(rep23),
            "moved_rep1_vs_rep23": len(moved),
            "isolates_contributing_moved": len(isolates_moved),
            "rep4_sides_with_rep23_temporal": verdict["zaman"],
            "rep4_sides_with_rep1_composition": verdict["bilesim"],
            "rep4_third_state": verdict["ucuncu"],
            "agree_rep4_rep1": sum(1 for k in common if per["4"][k] == per["1"][k]),
            "agree_rep4_rep2": sum(1 for k in common if per["4"][k] == per["2"][k]),
            "agree_rep4_rep3": sum(1 for k in common if per["4"][k] == per["3"][k]),
            "na_rep1": sum(1 for k in common if per["1"][k] == "NA"),
            "na_rep4": sum(1 for k in common if per["4"][k] == "NA"),
        }
        # Matched timing: rep1 and rep4 share composition and batch count.
        s1 = batch_seconds(ROOT / a.runs / arm / "rep1")
        s4 = batch_seconds(ROOT / a.runs / arm / "rep4")
        row["median_seconds_per_batch_rep1"] = median(s1)
        row["median_seconds_per_batch_rep4"] = median(s4)
        row["batches_timed_rep1"] = len(s1)
        row["batches_timed_rep4"] = len(s4)

        if truth:
            row["moved_rep4_matches_lab"] = sum(
                1 for k in moved if truth.get(k) and per["4"][k] == truth[k])
            row["moved_with_lab_phenotype"] = sum(1 for k in moved if truth.get(k))
        rows.append(row)

        print(f"\n=== {arm}")
        print(f"  dort tekrarin tamaminda {len(common)} cift, "
              f"rep2 ve rep3 {len(rep23)} ciftte ayni")
        print(f"  rep1 ile rep2/3 arasinda degisen: {len(moved)} cift, "
              f"{len(isolates_moved)} ayri izolattan")
        if moved:
            print(f"  rep4 rep2/3 tarafinda (zaman): {verdict['zaman']}")
            print(f"  rep4 rep1 tarafinda (bilesim): {verdict['bilesim']}")
            print(f"  ucuncu bir durum: {verdict['ucuncu']}")
            w = max(len(f"{k[0]} {k[1]}") for k, *_ in detail)
            for k, r1, r23, r4, side, lab in detail:
                lab_s = f"  lab={lab}" if lab else ""
                print(f"    {k[0]} {k[1]:<{w - len(k[0])}}  "
                      f"rep1={r1} rep2/3={r23} rep4={r4}  -> {side}{lab_s}")
            if verdict["zaman"] > verdict["bilesim"]:
                print(f"  => sayilar zaman yonunde ({verdict['zaman']} / {len(moved)}). "
                      f"{len(moved)} cift ve {len(isolates_moved)} izolat bir testi "
                      f"desteklemez; bu bir yon, bir kanit degil.")
            elif verdict["bilesim"] > verdict["zaman"]:
                print(f"  => sayilar bilesim yonunde ({verdict['bilesim']} / {len(moved)}). "
                      f"Suruklenme iddiasi bu hâliyle geri cekilmeli.")
            else:
                print("  => sayilar iki yone esit dagildi; ikisi de ayrilamiyor.")
        else:
            print("  rep1 ile rep2/3 arasinda degisen cift yok; bu kol icin "
                  "ayristirilacak bir sey yok")
        if s1 and s4:
            print(f"  eslesmis sure (ayni bilesim, ayni parti sayisi): parti basina ortanca "
                  f"rep1={median(s1):.0f} s ({len(s1)} parti), "
                  f"rep4={median(s4):.0f} s ({len(s4)} parti)")
        else:
            print("  eslesmis sure hesaplanamadi: meta.json dosyalari eksik")

    for p in problems:
        print(f"EKSIK: {p}", file=sys.stderr)
    if not rows:
        sys.exit("Hicbir kol icin dort tekrar tam degil; tablo yazilmadi.")

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"\nyazildi: {out}")


if __name__ == "__main__":
    main()
