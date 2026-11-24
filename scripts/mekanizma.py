#!/usr/bin/env python3
"""What was detectable in the assembly at all, against what the laboratory found.

    python scripts/mekanizma.py --ref ~/amr_gizli/reference_phenotypes.tsv \
        --key ~/amr_gizli/blinding_key.tsv \
        --pred claude=runs/claude/rep1/predictions.tsv \
        --pred gpt=runs/gpt/rep1/predictions.tsv \
        --pred ref=runs/amrfinderplus/predictions.tsv

Why this exists
---------------
The clinical audit named one question as the most likely thing a referee will ask and
the one the manuscript does not answer: of the pairs scored as very major errors, how
many carried any determinant an assembly-based method could in principle have found —
and specifically, how many of the 20 meropenem-resistant isolates carried a
carbapenemase at all?

It matters because the answer changes what the headline number means rather than
merely qualifying it. The commonest route to meropenem non-susceptibility in *E. coli*
without a carbapenemase is an ESBL or AmpC together with porin loss, which AMRFinderPlus
does not detect and which therefore no agent relying on it can recover. If a meaningful
share of the 20 are porin-mediated, part of the 35% very major error rate is the ceiling
imposed by the input rather than a failure of the reasoner, and the paper can say which
fraction of real resistance in this sample was predictable at all. The same applies to
every drug, which is why the third table covers all of them.

The second table settles a question about the frozen rule from the study's own data.
The rule calls trimethoprim-sulfamethoxazole resistant only when a trimethoprim element
and a sulfonamide element are both present, justified on the grounds that the
combination keeps working when one component is compromised. The EUCAST category is set
on the trimethoprim component, so an acquired *dfr* alone may well cross it. Whether it
does is answerable here: cross-tabulate the laboratory phenotype against dfr-only,
sul-only and both. If dfr-only isolates are phenotypically resistant, the rule carries a
second degeneracy, a very major error generator symmetrical to the ampicillin major
error generator already reported, and it is reported as one. The rule is frozen and is
not edited.

Nothing here is a reinterpretation of a phenotype or a prediction. The tables count what
AMRFinderPlus reported for each isolate, as it reported it.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Column reading and loading come from the scripts that already define them. The
# reference arm once called every isolate susceptible because it read "Element type"
# where AMRFinderPlus 4.x writes "Type"; re-deriving that logic here would reintroduce
# exactly that class of bug, in a table meant to explain the error rates.
_ref_arm = _load("amr_ref_arm", HERE / "04_reference_arm.py")
_metrics = _load("amr_metrics", HERE / "metrics.py")
alan, read_report, load_pred = _ref_arm.alan, _ref_arm.read_report, _metrics.load_pred

# Carbapenemase families, by the enzyme name in the element symbol. KPC, NDM, VIM and
# IMP hydrolyse carbapenems strongly; OXA-48-like is kept separate because its
# carbapenem hydrolysis is weak and OXA-48 producers are often meropenem-susceptible at
# the EUCAST breakpoint, so pooling the two would hide the distinction the table exists
# to show.
# Whether a determinant is a carbapenemase at all is taken from AMRFinderPlus's own
# subclass curation rather than from a family list written here, so the table does not
# depend on that list being complete. The family patterns only split the carbapenemases
# the catalogue already identified, and they must tolerate the bla prefix: a leading \b
# does not match in "blaNDM-5", because there is no word boundary between "bla" and
# "NDM". The first version of this file carried that bug, classified an NDM-positive
# isolate as carrying no carbapenemase, and so overstated the share of resistance that
# was undetectable — in the direction of the conclusion the table was written to test.
STRONG_CARBAPENEMASE = re.compile(r"(?:\b|bla)(?:KPC|NDM|VIM|IMP|SPM|GIM|SIM)\b", re.I)
OXA48_LIKE = re.compile(r"OXA-(?:48|162|181|204|232|244|245|247|163|405|484|519)", re.I)
ESBL_OR_AMPC = re.compile(
    r"(?:\b|bla)(?:CTX-M|SHV|TEM|CMY|DHA|ACC|ACT|FOX|MIR|MOX|PER|VEB|GES|BEL)\b", re.I)

# Which AMRFinderPlus subclass token would have to be present for a determinant to bear
# on a drug at all. This mirrors the frozen rule's mapping in scripts/reference_rule.md
# and is used only to ask whether anything relevant was visible, never to make a call.
DRUG_TOKENS = {
    "ampicillin": ("BETA-LACTAM",),
    "cefotaxime": ("CEPHALOSPORIN", "CARBAPENEM", "BETA-LACTAM"),
    "meropenem": ("CARBAPENEM",),
    "ciprofloxacin": ("QUINOLONE",),
    "gentamicin": ("AMINOGLYCOSIDE", "GENTAMICIN"),
    "trimethoprim/sulfamethoxazole": ("TRIMETHOPRIM", "SULFONAMIDE"),
}


def determinants(raw: Path) -> dict[str, list[dict]]:
    """Per isolate, the AMR rows AMRFinderPlus reported, with symbol, class, subclass."""
    out: dict[str, list[dict]] = {}
    for f in sorted(raw.glob("ISO_*.amrfinder.tsv")):
        iso = f.name.split(".")[0]
        rows = []
        for r in read_report(f):
            if alan(r, "Type", "Element type").upper() != "AMR":
                continue
            rows.append({
                "symbol": alan(r, "Element symbol", "Gene symbol", "Element name"),
                "cls": alan(r, "Class").upper(),
                "subclass": alan(r, "Subclass").upper(),
            })
        out[iso] = rows
    return out


def relevant(rows: list[dict], abx: str) -> list[str]:
    toks = DRUG_TOKENS[abx]
    hits = []
    for r in rows:
        blob = f"{r['cls']}/{r['subclass']}"
        if any(t in blob for t in toks):
            hits.append(r["symbol"])
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--pred", action="append", default=[], help="arm=path.tsv")
    ap.add_argument("--raw", default="runs/amrfinderplus/raw")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    raw = Path(a.raw)
    if not raw.is_dir():
        sys.exit(f"AMRFinderPlus raporlari yok: {raw}. Once: bash go.sh ref")
    det = determinants(raw)
    if not det:
        sys.exit(f"{raw} icinde ISO_*.amrfinder.tsv bulunamadi")

    key = pd.read_csv(a.key, sep="\t", dtype=str)
    ref = pd.read_csv(a.ref, sep="\t", dtype=str)
    ref = ref[ref["genome_id"].isin(set(key["genome_id"]))]
    ref = ref[ref["pheno"].isin(["S", "R"])].merge(key, on="genome_id", how="left")
    print(f"{len(det)} izolat raporu, {len(ref)} fenotipli cift\n")

    # ---- Table 1: meropenem phenotype against carbapenemase carriage
    mero = ref[ref["abx"] == "meropenem"].copy()

    def carb_class(iso: str) -> str:
        rows = det.get(iso, [])
        carb = [r["symbol"] for r in rows
                if "CARBAPENEM" in f"{r['cls']}/{r['subclass']}"]
        syms = " ".join(carb)
        strong = bool(STRONG_CARBAPENEMASE.search(syms))
        oxa = bool(OXA48_LIKE.search(syms))
        if carb:
            if strong and oxa:
                return "carbapenemase: strong + OXA-48-like"
            if strong:
                return "carbapenemase: strong (KPC/NDM/VIM/IMP)"
            if oxa:
                return "carbapenemase: OXA-48-like only"
            return "carbapenemase: other, in the catalogue's carbapenem subclass"
        others = " ".join(r["symbol"] for r in rows)
        ceph = any("CEPHALOSPORIN" in f"{r['cls']}/{r['subclass']}" for r in rows)
        if ceph or ESBL_OR_AMPC.search(others):
            return "no carbapenemase; ESBL or AmpC present"
        return "no carbapenemase and no ESBL or AmpC"

    mero["carbapenemase"] = mero["isolate_id"].map(carb_class)
    t1 = pd.crosstab(mero["carbapenemase"], mero["pheno"])
    print("=== Tablo 1  meropenem fenotipi x karbapenemaz tasiyiciligi")
    print(t1.to_string(), "\n")
    nR = int((mero["pheno"] == "R").sum())
    none_R = int(((mero["pheno"] == "R")
                  & mero["carbapenemase"].str.startswith("no carbapenemase")).sum())
    if nR:
        print(f"  meropenem-dirençli {nR} izolattan {none_R} tanesinde hic karbapenemaz yok"
              f" ({none_R / nR * 100:.0f}%); bu izolatlarda direnc assembly'den okunamayan"
              f" bir mekanizmaya (porin kaybi) isaret ediyor olabilir\n")

    # ---- Table 2: TMP-SMX phenotype against dfr and sul carriage
    ts = ref[ref["abx"] == "trimethoprim/sulfamethoxazole"].copy()

    def folate_class(iso: str) -> str:
        syms = [r["symbol"].lower() for r in det.get(iso, [])]
        dfr = any(s.startswith("dfr") for s in syms)
        sul = any(s.startswith("sul") for s in syms)
        return {(True, True): "dfr + sul", (True, False): "dfr only",
                (False, True): "sul only", (False, False): "neither"}[(dfr, sul)]

    ts["folate"] = ts["isolate_id"].map(folate_class)
    t2 = pd.crosstab(ts["folate"], ts["pheno"])
    print("=== Tablo 2  TMP-SMX fenotipi x dfr / sul tasiyiciligi")
    print(t2.to_string(), "\n")
    d_only = ts[ts["folate"] == "dfr only"]
    if len(d_only):
        r = int((d_only["pheno"] == "R").sum())
        print(f"  yalniz dfr tasiyan {len(d_only)} izolattan {r} tanesi dirençli."
              f" Donmus kural bunlari duyarli cagiriyor, cunku iki bileseni birlikte"
              f" ariyor; dirençli olanlar kuralin ikinci dejenerasyonudur\n")
    else:
        print("  yalniz dfr tasiyan izolat yok; kuralin bu kosulu bu veride test edilemiyor\n")

    # ---- Table 3: was anything relevant visible, for every very major error
    rows = []
    for spec in a.pred:
        name, path = spec.split("=", 1)
        m = ref.merge(load_pred(path, key), on=["genome_id", "abx"], how="left")
        m["prediction"] = m["prediction"].fillna("NA")
        vme = m[(m["pheno"] == "R") & (m["prediction"] == "S")]
        for _, r in vme.iterrows():
            hits = relevant(det.get(r["isolate_id"], []), r["abx"])
            rows.append({"arm": name, "isolate_id": r["isolate_id"], "abx": r["abx"],
                         "determinants_for_this_drug": "; ".join(hits) or "",
                         "anything_detectable": bool(hits)})
    if rows:
        v = pd.DataFrame(rows)
        print("=== Tablo 3  her cok buyuk hatada (VME) ilgili bir determinant var miydi")
        print(pd.crosstab(v["arm"], v["anything_detectable"]).to_string(), "\n")
        print("  ilaca gore:")
        print(pd.crosstab([v["abx"], v["anything_detectable"]], v["arm"]).to_string(), "\n")
        out = Path(a.out) / "vme_mekanizma.tsv"
        v.to_csv(out, sep="\t", index=False)
        print(f"  yazildi: {out}")
        print("  anything_detectable=False: AMRFinderPlus bu ilac icin hic determinant"
              " bildirmemis, yani ajan hangi akil yurutmeyi yaparsa yapsin direnci"
              " assembly'den cikaramazdi\n")

    o = Path(a.out)
    t1.to_csv(o / "meropenem_karbapenemaz.tsv", sep="\t")
    t2.to_csv(o / "tmpsmx_dfr_sul.tsv", sep="\t")
    print(f"yazildi: {o / 'meropenem_karbapenemaz.tsv'}, {o / 'tmpsmx_dfr_sul.tsv'}")


if __name__ == "__main__":
    main()
