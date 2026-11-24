===== batch_001/workspace/output/methods.md =====
# Methods: genotype-based S/R prediction for 10 *E. coli* isolates

## Tools and versions (all local, no internet access used)

| Tool | Version | Role |
|---|---|---|
| NCBI AMRFinderPlus (`amrfinder`) | 4.2.7 | detection of acquired AMR genes and *E. coli* chromosomal point mutations |
| AMRFinderPlus database | 2026-10-29.1 (`share/amrfinderplus/data/2026-10-29.1`) | reference proteins, HMMs, *Escherichia* mutation catalogue |
| BLAST+ (`blastn`/`tblastn`, called by AMRFinderPlus) | 2.17.0+ | sequence search |
| HMMER | 3.4 | installed with AMRFinderPlus; not used in nucleotide-only mode |
| Python | 3 (system `python3`) | rule-based translation of genotype into S/R |

I checked for other tools (ABRicate, RGI/CARD, ResFinder/PointFinder, staramr, Kleborate, prokka, prodigal, mlst, diamond). None of them is installed, so AMRFinderPlus is the only AMR caller used.

## AMRFinderPlus command

The same command was run on every assembly:

```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 2 --name ISO_### -o ISO_###.tsv
```

(ISO_001 and ISO_002 were run with `--threads 4`; thread count does not affect results.)

- `-n`: nucleotide input. This is a translated search (tblastn) plus blastn against the nucleotide mutation catalogue. No gene prediction was done.
- `-O Escherichia`: turns on the *E. coli* point-mutation screen (gyrA/parC/parE QRDR, ampC promoter, 16S rRNA, ftsI, etc.) and organism-specific suppression of intrinsic genes.
- `--plus`: also reports "plus"-scope genes (virulence, efflux, stress). These were not used for calls, except that the chromosomal `blaEC` was explicitly ignored.
- All other parameters were left at their defaults: curated per-family identity cut-offs, and 50% minimum coverage of the reference.

Raw per-isolate outputs, logs and the translation script (`call.py`) are kept in `../amr_work/`, outside the workspace.

## Which hits were used

- Only `Scope=core` AMR elements were used, plus the beta-lactamase genes. Plus-scope efflux genes such as `acrF`, `mdtM` and `emrD` were ignored.
- The chromosomal *E. coli* AmpC (`blaEC`) is intrinsic and expressed at low level, so it was ignored. Only ampC promoter or attenuator mutations would count, and none were found.
- Hits flagged `INTERNAL_STOP` were discarded.
- `PARTIAL` hits (other than `PARTIAL_CONTIG_END`) were used only if they covered at least 80% of the reference.
- `PARTIAL_CONTIG_END` hits (a gene split across contigs) were kept and are marked in the evidence column, e.g. `sul1[PARTIAL_CONTIG_ENDX]` in ISO_006.

## Genotype-to-phenotype rules

Each rule targets clinical breakpoint categories (EUCAST-style). A drug is predicted R if any of its listed conditions is met; otherwise it is S.

**Ampicillin: R** if there is any acquired beta-lactamase (AMRFinder Class `BETA-LACTAM`, other than `blaEC`), of any spectrum (TEM-1, OXA-1/-9, SHV, CTX-M, CMY, NDM, …), or an ampC/blaTEM promoter mutation.

**Cefotaxime: R** if any of the following is present:
- an ESBL, a plasmid AmpC or a carbapenemase. In practice this is an acquired beta-lactamase whose AMRFinder Subclass contains `CEPHALOSPORIN` or `CARBAPENEM`: CTX-M, SHV-12, CMY, NDM. One exception applies: the narrow-spectrum enzymes TEM-1/-2, SHV-1/-11/-28, OXA-1/-2/-9/-10 do not count. AMRFinder labels OXA-1 `CEPHALOSPORIN`, but on its own OXA-1 does not give cefotaxime resistance.
- a chromosomal ampC promoter hyper-expression mutation.

OXA-48-like enzymes alone would be called S, because they are weak cephalosporinases. None were found.

**Meropenem: R** if there is an acquired carbapenemase (Subclass contains `CARBAPENEM`, e.g. NDM). The PBP2/PBP3 changes `mrdA` and `ftsI` (e.g. `ftsI_N337NYRIN`, `mrdA_L573Q`) were not counted as conferring meropenem resistance on their own. No porin-loss rule was applied.

**Ciprofloxacin: R** if any of the following holds:
- 2 or more QRDR mutations in gyrA plus parC;
- 1 gyrA mutation plus a parE mutation or a PMQR gene;
- 1 QRDR mutation plus 1 PMQR gene;
- 2 or more PMQR genes.

PMQR genes are qnr*, qepA, oqxAB, `aac(6')-Ib-cr`, crpP. A single low-level determinant, such as gyrA S83L alone or one qnr gene alone, is called S because it is expected to sit below the R breakpoint. The evidence column states this.

**Gentamicin: R** if any of the following is present:
- `aac(3)` enzymes: aac(3)-I/-II/-III/-IV/-VI families, e.g. aac(3)-IIa/-IId/-IIe;
- `ant(2'')-Ia` or `aph(2'')`;
- a 16S rRNA methyltransferase: armA, rmtA–H, npmA;
- the 16S rRNA A1408G mutation.

`aac(6')-Ib` / `aac(6')-Ib-cr` (amikacin/tobramycin), `aadA` (streptomycin/spectinomycin) and `aph(3')`/`aph(3'')`/`aph(6)` do not count toward gentamicin resistance.

**Trimethoprim/sulfamethoxazole: R** if any acquired `dfrA`/`dfrB` gene is present. Sulfonamide genes (`sul1`–`sul3`) are listed as supporting evidence. A `sul` gene without a `dfr` gene is called S, because the combination generally stays active.

**NA** would have been used only for an antibiotic with no rule. It did not occur.

## Limitations

- Calls rest entirely on known determinants from AMRFinderPlus. The following are not detected:
  - novel mechanisms;
  - changes in expression level (efflux up-regulation, porin loss);
  - gene copy number.
- These effects can lead to false-S calls, for example carbapenem resistance from ESBL/AmpC plus porin loss, or borderline ciprofloxacin MICs.
- Breakpoint-borderline genotypes, such as a single gyrA mutation, are the least certain calls.


===== batch_002/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus 4.2.7** (`amrfinder`), database version **2026-10-29.1**
  (`.../envs/amr/share/amrfinderplus/data/2026-10-29.1`). This was the only dedicated AMR caller
  installed. abricate, RGI, ResFinder, staramr and mlst were not present.
- BLAST+ 2.17.0 and HMMER, used internally by AMRFinderPlus.
- Python 3 for the genotype-to-phenotype rules (`scripts/call.py`, kept in the workspace).

## Command (per isolate)
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` turns on species-specific point-mutation screening (gyrA/parC/parE, ampC promoter,
porins, etc.) and filters out intrinsic genes. `--plus` adds stress, virulence and efflux genes,
which were not used for the calls. Default identity and coverage thresholds were kept. Raw output is in
`output/amrfinder/`.

## Genotype-to-phenotype rules
Only `Scope = core`, `Type = AMR` elements were used. Partial or contig-edge hits (PARTIALX,
PARTIAL_CONTIG_ENDX, BLASTX) were accepted and labelled in the evidence column. An isolate was
called **R** if any of the listed determinants was found, otherwise **S**. No call was NA.

| Antibiotic | Determinants that give R |
|---|---|
| ampicillin | any acquired beta-lactamase (blaTEM, blaSHV, blaCTX-M, blaOXA incl. OXA-10/OXA-48, blaNDM, blaKPC, blaVIM, blaIMP, plasmid AmpC CMY/DHA) |
| cefotaxime | ESBL / plasmid AmpC / MBL / KPC (blaCTX-M, blaSHV-12, blaCMY, blaDHA, blaNDM, blaKPC, blaVIM, blaIMP). blaTEM-1, blaOXA-10 and blaOXA-48 alone were treated as not giving cefotaxime R. Chromosomal blaEC (intrinsic, `plus` scope) was ignored because no ampC promoter mutation was reported. |
| meropenem | carbapenemase (blaNDM, blaKPC, blaVIM, blaIMP, blaOXA-48-like). OXA-48 was called R, though it can give MICs near the breakpoint. |
| gentamicin | aac(3)-II/-IV/-VI family, ant(2'')-Ia, 16S rRNA methylases (armA, rmt*, npmA). aadA, aph(3'), aph(3'') and aph(6) were not counted. |
| ciprofloxacin | any QRDR mutation reported by AMRFinderPlus in gyrA or parC, or parE S458, or any PMQR gene (qnr, aac(6')-Ib-cr, qepA, oqxAB). parE I355T (ISO_020) was not counted. A single determinant (gyrA S83L alone, or qnrS1 alone) was called R but flagged as borderline. marR/acrR substitutions were not counted. |
| trimethoprim/sulfamethoxazole | any acquired dfrA gene, with or without sul1/2/3. A sul gene alone was not enough. |

## Caveats
- Calls are presence/absence only. Expression levels, copy number and porin/efflux contributions were not modelled.
- Borderline calls: ciprofloxacin for ISO_016 (gyrA S83L only) and ISO_018 (qnrS1 only);
  meropenem for ISO_012 (OXA-48 alone); cefotaxime for ISO_011 and ISO_012 (OXA-10 / OXA-48, called S).


===== batch_003/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus v4.2.7** (`/Users/applemacbookpro/miniforge3/envs/amr/bin/amrfinder`), database version **2026-10-29.1**.
- **BLAST+ 2.17.0+** (`blastn`/`tblastn`), used by AMRFinderPlus and for one manual check.
- No other AMR tools were installed (abricate, ResFinder, RGI, staramr, mlst were not present). Nothing was downloaded.

## Commands
For each `data/genomes/ISO_###.fasta`:

```
amrfinder -n ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```

- `-O Escherichia` turns on organism-specific point-mutation screening (gyrA, parC, parE, ampC promoter, etc.) and suppresses genes intrinsic to E. coli.
- `--plus` adds the extended gene set (efflux, stress, virulence). Those were not used for S/R calls.
- Default identity and coverage thresholds were used. Raw outputs are in `output/amrfinder/`.

Manual check: `tblastn` of TEM-1 (WP_000027057.1, from the AMRFinderPlus AMRProt.fa) against ISO_024. The non-exact blaTEM hit (99.65 % identity) is TEM-1 with a single I12M substitution in the signal peptide. That position is not an ESBL position (104/164/238/240), so I treated it as a narrow-spectrum penicillinase.

## Genotype → phenotype rules
Only hits with Type = AMR were considered. Efflux genes (acrF, emrD, mdtM) and the chromosomal blaEC (class C AmpC, all alleles) were not counted as resistance unless an ampC promoter or attenuator mutation was reported. None was reported.

| Antibiotic | Called R if |
|---|---|
| ampicillin | any acquired β-lactamase: blaTEM/SHV/OXA-1-like penicillinase, ESBL (CTX-M etc.), plasmid AmpC, carbapenemase, or an ampC promoter mutation |
| cefotaxime | ESBL (CTX-M, ESBL-type TEM/SHV), plasmid AmpC (CMY/DHA etc.), carbapenemase (KPC, NDM, OXA-48-like…), or an ampC promoter mutation. TEM-1 alone → S |
| ciprofloxacin | ≥1 gyrA QRDR mutation (S83, D87), or a plasmid-mediated determinant (qnr, aac(6')-Ib-cr, qepA, oqxAB). A single gyrA S83L counts as R but is noted as low-level. parC/parE changes without a gyrA mutation (ISO_030: parC_S57T, parE_I355T) → S |
| gentamicin | aac(3)-I/II/III/IV/VI, ant(2'')-Ia, or 16S rRNA methyltransferase (armA, rmt*). Streptomycin- and kanamycin-only genes (aph(6)-Id, aph(3'')-Ib, aadA, aph(3')-Ia) → S |
| meropenem | carbapenemase gene |
| trimethoprim/sulfamethoxazole | an acquired dfrA/dfrB gene **and** a sul gene (sul1/2/3) both present. sul alone (ISO_022, partial sul2) → S |

If none of these determinants was found, the call is S and the evidence column says "no determinant found". No NA calls were needed.

## Caveats
- The ciprofloxacin call for ISO_026 rests on a single gyrA S83L. With current breakpoints it may fall at or near the S/I boundary.
- ISO_027's blaTEM is truncated at a contig end. It does not affect its calls, because CTX-M-55 is present.
- ISO_030's chromosomal blaEC is only 92.8 % identical to the reference, which may point to a divergent lineage. Its calls rest on KPC-2.


===== batch_004/workspace/output/methods.md =====
# Methods

## Input
10 *E. coli* assemblies (`data/genomes/ISO_031`–`ISO_040`, 81–261 contigs, 4.68–5.28 Mb; size and contig count checked with awk). Antibiotics: ampicillin, cefotaxime, ciprofloxacin, gentamicin, meropenem, trimethoprim/sulfamethoxazole.

## Tools
- **AMRFinderPlus 4.2.7** (`amrfinder`, conda env `amr`). Database version **2026-10-29.1**. Internally it uses BLAST+ 2.17.0 and HMMER.
- I ran no other AMR tools. ResFinder, ABRicate, RGI and KMA are not installed. Nothing was downloaded.

Command, run once per isolate:
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` turns on screening for species-specific point mutations: gyrA/parC/parE QRDR, the ampC/blaEC promoter, marR and others. `--plus` adds the extended gene set. Default identity and coverage thresholds were kept. Raw output is in `output/amrfinder/`.

## Genotype → phenotype rules
Rows with Type = AMR and Class EFFLUX were not used, because the intrinsic acrF/mdtM-type genes are present in all *E. coli*.

- **Ampicillin**: R if there is an acquired β-lactamase (blaTEM, blaSHV, blaCTX-M, blaOXA, a plasmid AmpC or any carbapenemase), or an ampC promoter/attenuator mutation. The chromosomal blaEC alone (any EC-n allele) with no promoter mutation → S.
- **Cefotaxime**: R if there is an ESBL (CTX-M, ESBL variants of TEM/SHV), a plasmid AmpC (CMY, DHA, …), an ampC promoter mutation or a carbapenemase. Narrow-spectrum TEM-1/SHV-1 → S.
- **Meropenem**: R only with a carbapenemase (KPC, NDM, VIM, IMP, OXA-48-like).
- **Ciprofloxacin**: R if there are ≥2 QRDR mutations (gyrA/parC), or 1 gyrA mutation plus a PMQR gene (qnr, aac(6')-Ib-cr, qepA). A single gyrA S83L on its own → S. That mutation typically gives an MIC of about 0.12–0.5 mg/L, which is at or below the EUCAST S breakpoint of 0.25 mg/L. marR S3N and parE I529L were treated as minor or non-causal.
- **Gentamicin**: R with aac(3)-II/IV/VI, ant(2'')-Ia, aac(6')-Ib variants that act on gentamicin, or a 16S rRNA methylase (armA, rmt). Genes that act only on streptomycin or kanamycin (aadA, aph(6)-Id, aph(3'')-Ib, aph(3')-Ia) do not count.
- **Trimethoprim/sulfamethoxazole**: R if any acquired dfrA/dfrB gene is present, with or without a sul gene. A sul gene without a dfr gene → S.
- If no relevant determinant was found → S with "no determinant found".

No isolate needed an NA call. AMRFinderPlus reported no partial or contig-edge hits in the relevant genes.

## Caveats
- The 2026-10-29.1 database screened the ampC promoter mutations and reported none. I did not try to predict ampC overexpression from other causes.
- The single gyrA S83L call for ISO_035 sits near the breakpoint. Under CLSI or older breakpoints it may test I or R.
- Porin loss and changes in expression cannot be assessed from these assemblies.


===== batch_005/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus 4.2.7** (`amrfinder`, conda env `amr`), database version **2026-10-29.1**
  (`.../envs/amr/share/amrfinderplus/data/2026-10-29.1`). Versions checked with `amrfinder -V`.
- BLAST+ 2.17.0 (used internally by AMRFinderPlus).
- Python 3 (standard library only) for genotype-to-phenotype translation (`scripts/call.py`).
- No other AMR tools (ResFinder/PointFinder, RGI, ABRicate, staramr) were installed. No internet access was used.

## Command (per isolate)
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` enables species-specific point-mutation screening (gyrA, parC, parE, ampC promoter, etc.)
and suppresses intrinsic-gene noise; `--plus` reports additional (efflux/stress) elements. Default
identity/coverage thresholds were used. Raw outputs are in `output/amrfinder/`.

## Genotype -> S/R rules
Only `Type == AMR` rows were used. Hits with method PARTIALX / PARTIAL_CONTIG_ENDX / INTERNAL_STOP were
excluded (none of these affected a call: catB3, aadA1, aadA2 only). Chromosomal blaEC (intrinsic ampC) was
ignored unless a promoter/attenuator mutation was reported (none were). Efflux genes (acrF, mdtM, emrD) and
regulatory mutations (marR, acrR, soxS) were not counted as sufficient for resistance.

| Antibiotic | R if any of |
|---|---|
| ampicillin | acquired beta-lactamase: blaTEM, blaSHV, blaCTX-M, blaOXA, blaCMY, blaDHA, blaACT, carbapenemases, etc. |
| cefotaxime | ESBL or AmpC: blaCTX-M, ESBL-type SHV, plasmid AmpC (blaCMY/DHA/ACT), carbapenemases, or ampC promoter mutation. blaTEM-1 and blaOXA-1 alone -> S |
| ciprofloxacin | >=2 QRDR mutations in gyrA, or gyrA mutation + parC/parE mutation, or gyrA mutation + PMQR gene (qnr, aac(6')-Ib-cr, qepA, oqxAB). A single change or marR/acrR/soxS alone -> S |
| gentamicin | aac(3)-I/II/III/IV/VI variants, ant(2'')-Ia, or 16S rRNA methylases (armA, rmt*, npmA). aac(6')-Ib(-cr) not counted |
| meropenem | carbapenemase (KPC, NDM, VIM, IMP, OXA-48-like, GES-5). Porin loss (e.g. ompF_W83Ter in ISO_042) not counted alone |
| trimethoprim/sulfamethoxazole | at least one dfr gene AND at least one sul gene (sul1/2/3); only one of the two -> S |

No call was NA. The `evidence` column lists the AMRFinderPlus element symbols that drove each call
(for ciprofloxacin, all QRDR mutations and PMQR genes found).


===== batch_006/workspace/output/methods.md =====
# Methods

## Input
10 *E. coli* genome assemblies (`data/genomes/ISO_051`–`ISO_060.fasta`, 52–184 contigs each) and 6 antibiotics from `data/antibiotics.txt`.

## Tools and databases
| Tool | Version | Use |
|---|---|---|
| NCBI AMRFinderPlus | 4.2.7 | detection of acquired AMR genes and chromosomal point mutations |
| AMRFinderPlus database | 2026-10-29.1 (`miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`) | reference genes, HMMs, point-mutation tables |
| BLAST+ | 2.17.0 (called internally by AMRFinderPlus) | |
| HMMER | 3.4 (called internally by AMRFinderPlus) | |
| Python | 3 (standard library only) | genotype-to-phenotype rules (`output/scripts/call.py`) |

No abricate, ResFinder/PointFinder, RGI/CARD or staramr was installed, so AMRFinderPlus was the only detection tool. Nothing was downloaded.

## Command
For each isolate:
```
amrfinder -n data/genomes/ISO_###.fasta --organism Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
The default identity and coverage thresholds were used. `--organism Escherichia` turns on screening for *E. coli* point mutations (gyrA, parC, parE, ampC promoter, folP, and others). Raw output and logs are in `output/amrfinder/`.

## Genotype → phenotype rules
Only rows with `Type == AMR` were used. STRESS and VIRULENCE rows were ignored.

- **Ampicillin**: R if any acquired β-lactamase is present (any `bla*` other than the intrinsic chromosomal `blaEC` alleles), e.g. TEM-1, OXA-1, CTX-M, CMY. Otherwise S. A chromosomal `blaEC` without a promoter or attenuator mutation is treated as non-resistant.
- **Cefotaxime**: R if an ESBL (CTX-M, or an ESBL-type SHV/TEM allele), a plasmid AmpC (CMY, DHA), an *ampC* promoter mutation, or a carbapenemase is present. TEM-1 and OXA-1 alone count as S.
- **Ciprofloxacin**: R if there are ≥2 QRDR mutations (gyrA/parC/parE), or a gyrA mutation plus a *qnr* gene. A single QRDR mutation or a single PMQR alone counts as S, because it usually gives only low-level reduced susceptibility below the EUCAST/CLSI R breakpoint. `aac(6')-Ib-cr` was not counted on its own. `marR_S3N` was ignored because it is a common polymorphism, not a resistance mutation.
- **Gentamicin**: R if an aac(3) family gene (aac(3)-II, -IV, -VI…), ant(2'')-Ia, or a 16S rRNA methyltransferase (armA, rmt) is present. Otherwise S. `aac(6')-Ib-cr` and streptomycin genes (aadA, aph(3'')-Ib, aph(6)-Id) do not confer gentamicin resistance.
- **Meropenem**: R only if a carbapenemase is present (KPC, NDM, VIM, IMP, OXA-48-like). None was found, so all calls are S. Porin loss combined with ESBL/AmpC was not modelled.
- **Trimethoprim/sulfamethoxazole**: R if any acquired `dfrA` gene is present, with or without `sul`. `sul1`/`sul2` alone, or `folP_P64S` alone, counts as S, because trimethoprim keeps the combination active.

No call was set to NA.

## Uncertain calls
- ISO_052 ciprofloxacin: only one mutation (gyrA S83L), called S. Its MIC may lie near the breakpoint.
- ISO_057 trimethoprim/sulfamethoxazole: dfrA1 with no sul gene, called R.
- ISO_053 and ISO_058 trimethoprim/sulfamethoxazole: sul genes with no dfrA, called S.


===== batch_007/workspace/output/methods.md =====
# Methods

## Tools and databases (all local, no network access)
- **AMRFinderPlus 4.2.7** (`amrfinder`, conda env `amr`), database version **2026-10-29.1**
  (`.../envs/amr/share/amrfinderplus/data/2026-10-29.1`). Versions were checked with `amrfinder --version` and `amrfinder -V`.
- AMRFinderPlus uses its bundled NCBI BLAST+ and HMMER binaries internally.
- Python 3 (standard library only) for the rule-based genotype-to-phenotype step (`output/scripts/call.py`).
- Other tools were looked for and are not installed: abricate, ResFinder/PointFinder, RGI, staramr, mlst.

## Command
For each assembly:
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` turns on the species-specific point-mutation screen (gyrA/parC/parE QRDR, ampC promoter, porins, etc.).
All other AMRFinderPlus thresholds were left at their defaults (curated per-gene identity cut-offs, 50% coverage minimum).
The raw reports are in `output/amrfinder/`. Only rows with `Type == AMR` were used. Partial hits (PARTIALX/PARTIAL_CONTIG_ENDX) were kept.

## Genotype → phenotype rules
- **Ampicillin**: R if any acquired beta-lactamase gene is found (blaTEM, blaOXA, blaCMY, blaKPC, etc., including blaTEM promoter variants). The intrinsic chromosomal *E. coli* ampC (blaEC, blaEC-#) is ignored unless an ampC promoter or attenuator mutation is reported. None was reported. Otherwise S.
- **Cefotaxime**: R if any of the following is present: an ESBL (CTX-M, SHV other than SHV-1/-11, TEM other than TEM-1, VEB, PER, GES), a plasmid AmpC (CMY, DHA, ACC, FOX, MOX, ACT, MIR, LAT), a carbapenemase, or an ampC promoter mutation. Narrow-spectrum TEM-1 and OXA-9 give S.
- **Ciprofloxacin**: R if a gyrA S83/D87 mutation occurs together with at least one other QRDR mutation (≥2 distinct gyrA/gyrB/parC/parE mutations in total), or a gyrA mutation occurs together with a plasmid-mediated quinolone-resistance gene (qnr, aac(6')-Ib-cr, qepA, oqxAB). A single determinant on its own (e.g., gyrA S83L alone) is predicted S: such strains usually have MICs near or below the EUCAST/CLSI R breakpoints, so this call has low confidence. With no determinant the call is S.
- **Gentamicin**: R if aac(3)-family genes, aac(6')-Ib' (the gentamicin-modifying variant), ant(2'')-Ia, or 16S rRNA methylases (armA, rmt*, npmA) are present. aph/aadA/aac(6')-Ib-cr give S.
- **Meropenem**: R only if a carbapenemase is present (KPC, NDM, VIM, IMP, OXA-48-like). Porin truncations (e.g., ompC) without a carbapenemase give S.
- **Trimethoprim/sulfamethoxazole**: R if any dfrA/dfrB gene is present. In practice a sul gene was present every time except ISO_070, where dfrA1 alone was called R with lower confidence. sul without dfr gives S, as does no determinant.
- NA was not needed. Every isolate/antibiotic pair got a call.

## Caveats
Predictions come from gene presence alone. Expression levels, copy number, and efflux or porin effects are not modelled. The cutoff for single-mutation ciprofloxacin calls and the call for dfr without sul are the least certain rules.


===== batch_008/workspace/output/methods.md =====
# Methods

## Tools and versions
- **AMRFinderPlus 4.2.7** (`amrfinder`), database version **2026-10-29.1**
  (`.../share/amrfinderplus/data/2026-10-29.1`), with its bundled BLAST+ **2.17.0+** (blastn/tblastn) and stxtyper.
- Python 3.13.13 for the genotype-to-phenotype rules (`output/scripts/call.py`).
- Other tools checked but not installed: abricate, RGI, ResFinder/PointFinder, ARIBA, staramr, mlst.
  Nothing was downloaded.

## Command (per isolate)
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 -o output/amrfinder/ISO_###.tsv
```
Defaults kept: identity/coverage thresholds from the curated database (`-i`/`-c` not set).
`-O Escherichia` turns on chromosomal point-mutation screening (gyrA, parC, parE, ampC promoter, porins, ftsI, etc.).
The raw reports are in `output/amrfinder/`.

## Genotype → phenotype rules
These rules use only rows of type `AMR`. Partial hits (PARTIAL/PARTIAL_CONTIG_END) were counted as present.
The chromosomal `blaEC` (intrinsic *E. coli* AmpC) was ignored.

| Antibiotic | R if |
|---|---|
| ampicillin | any acquired beta-lactamase (`bla*` other than blaEC: TEM, OXA-1, CTX-M, OXA-48, KPC, ...) or an ampC promoter mutation |
| cefotaxime | an ESBL, a plasmid AmpC, or a cefotaximase carbapenemase: CTX-M, non-TEM-1/2 TEM, non-SHV-1/11 SHV, CMY/DHA/ACC/FOX/MOX/ACT/MIR, PER/VEB/GES, KPC/NDM/VIM/IMP. Called S when only TEM-1, OXA-1 or OXA-48 is present (OXA-48 hydrolyses cefotaxime poorly) |
| ciprofloxacin | any gyrA QRDR mutation (all R calls here had gyrA S83L+D87N plus parC S80I, i.e. high-level), or a PMQR gene (qnr, aac(6')-Ib-cr, qepA) together with a parC/parE mutation |
| gentamicin | aac(3)-*, ant(2'')-Ia, or a 16S rRNA methylase (rmt*, armA, npmA). aac(6')-Ib(-cr) does not count |
| meropenem | an acquired carbapenemase (KPC, NDM, VIM, IMP, OXA-48-like, ...). A porin defect alone (ompF/ompC) was noted in the evidence but called S |
| trimethoprim/sulfamethoxazole | any acquired `dfr` gene (sul genes are listed as supporting evidence; sul without dfr is called S) |

If no rule fires, the call is S with "no determinant found"-type evidence. No NA calls were needed.

## Caveats
- OXA-48 → meropenem R is a conservative call. OXA-48 producers often have meropenem MICs near or below the clinical breakpoint.
- ISO_080 has an ompF frameshift with CTX-M-15 + OXA-1 and was called meropenem S. Ertapenem would be more affected than meropenem.
- Gene expression, copy number and MIC breakpoints were not modelled.


===== batch_009/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus v4.2.7** (`amrfinder`), database version **2026-10-29.1**
  (`.../envs/amr/share/amrfinderplus/data/2026-10-29.1`). This was the only dedicated AMR tool installed; abricate, RGI, ResFinder, staramr and mlst were not available.
- BLAST+ 2.17.0 was present but was not used on its own. A short Python 3 snippet was used to inspect the contig carrying the truncated blaCTX-M hit in ISO_081.
- Python 3 (standard library only) for the rule-based genotype→phenotype translation (`output/call_rules.py`).

## Gene and mutation detection
For each assembly:
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` turns on point-mutation screening for *E. coli* (gyrA, parC, parE, ampC promoter, porins, etc.). AMRFinderPlus default identity and coverage thresholds were used. Only rows with `Type == AMR` were used for calls. Hits that were partial because they ran into a contig end were treated as present. ISO_081 blaCTX-M: closest reference CTX-M-15, 100% identity, 92% coverage. The gene runs to the end of the 1,202-bp contig_44, so it was cut off by the assembly break and was not truncated in the genome.

## Genotype → S/R rules
| Antibiotic | Call R if | Otherwise S |
|---|---|---|
| ampicillin | any acquired β-lactamase (any `bla*` other than the intrinsic chromosomal `blaEC`), or an ampC promoter/blaEC mutation | intrinsic blaEC only |
| cefotaxime | ESBL (CTX-M, SHV/TEM ESBL variants, VEB, PER, GES), plasmid AmpC (CMY, DHA, ACC, FOX), carbapenemase, or chromosomal ampC promoter mutation | blaTEM-1 / narrow-spectrum only |
| meropenem | carbapenemase gene (KPC, NDM, VIM, IMP, OXA-48-like) | porin (ompC/ompF) changes alone are not counted as R |
| ciprofloxacin | ≥2 QRDR mutations in gyrA, or gyrA + parC, or gyrA/any target mutation + PMQR (qnr, qepA, aac(6')-Ib-cr, oqxAB), or ≥2 PMQR | a single gyrA mutation, a parE mutation alone, or a single PMQR gene is treated as low-level (MIC expected below the EUCAST/CLSI R breakpoint) → S |
| gentamicin | aac(3)-*, ant(2'')-Ia, 16S rRNA methyltransferase (armA, rmtA–F, npmA) | strA/strB [aph(3'')-Ib, aph(6)-Id], aadA, aph(3')-Ia do not affect gentamicin → S |
| trimethoprim/sulfamethoxazole | any `dfr` gene (sul genes usually co-occur) | sul gene alone, without dfr → S |

No call was set to NA. Efflux genes (acrF, mdtM, emrD), the acrR frameshift, and fosfomycin, colistin, cefiderocol and tetracycline determinants were recorded but did not change any call for the six antibiotics listed.

## Limitations
- The rules were not calibrated against phenotypes in this dataset.
- Expression-level effects (efflux overexpression, IS-driven promoters, copy number) are not modelled.
- Single-step fluoroquinolone mutants (ISO_089: gyrA S83L only) are borderline and may test R under some breakpoints.


===== batch_010/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus 4.2.7** (`amrfinder`), database version **2026-10-29.1** (local install; no update run, no network).
  - Dependencies in the same conda env: BLAST+ 2.17.0, HMMER 3.4.
- Python 3 (standard library only) for genotype-to-phenotype rules: `scripts/call.py`.
- No other AMR tools were installed (abricate, RGI, ResFinder/PointFinder, staramr, mlst were checked and were absent).

## Command
For each `data/genomes/ISO_###.fasta`:
```
amrfinder -n ISO_###.fasta -O Escherichia --plus --threads 4 -o output/amrfinder/ISO_###.tsv
```
`-O Escherichia` turns on species-specific point-mutation screening (gyrA/parC/parE QRDR, ampC promoter, etc.). Default identity/coverage thresholds were used. Only rows with `Type == AMR` were used. Partial hits (PARTIALX / PARTIAL_CONTIG_ENDX) were kept, but none of them affected a call for the six antibiotics: they were aph(6)-Id, aph(4)-Ia and aadA5.

## Genotype → S/R rules (`scripts/call.py`)
- **Ampicillin**: R if any acquired beta-lactamase (blaTEM, blaSHV, blaCTX-M, blaOXA, plasmid AmpC, carbapenemases, …) or an ampC promoter/attenuator mutation is present. The chromosomal blaEC (including the blaEC-5 allele) on its own is not counted, so those isolates are called S.
- **Cefotaxime**: R if an ESBL (CTX-M; TEM/SHV only when AMRFinder gives subclass CEPHALOSPORIN/CARBAPENEM), a plasmid AmpC (CMY, DHA, ACC, FOX, MOX, ACT), a carbapenemase or an ampC promoter mutation is present. Otherwise S. TEM-1 counts as narrow-spectrum.
- **Meropenem**: R if any gene with AMRFinder subclass CARBAPENEM is present (carbapenemase). Otherwise S.
- **Ciprofloxacin**: R if there are at least 2 QRDR mutations (gyrA/parC/parE), or at least 1 QRDR mutation plus a PMQR gene (qnr, aac(6')-Ib-cr, qepA), or at least 2 PMQR genes. A single gyrA mutation on its own (typical MIC 0.125–0.5 mg/L, around the S ≤0.25 breakpoint) is called S, and the evidence column flags it. oqxAB is not counted. marR_S3N is treated as a non-informative polymorphism.
- **Gentamicin**: R if aac(3) (e.g. aac(3)-II/-IV/-VI), ant(2'')-Ia or a 16S rRNA methylase (armA, rmt*, npmA) is present. aph/aadA/aac(6')-Ib genes do not confer gentamicin resistance and are ignored.
- **Trimethoprim/sulfamethoxazole**: R if any dfrA/dfrB gene is present (it was always found together with sul1/2/3 here). A sul gene without dfr is called S, because trimethoprim resistance is needed for clinical SXT resistance.
- No call was NA.

## Limitations
- Resistance from efflux overexpression, porin loss, or ampC hyperexpression that is not captured by the screened promoter mutations is not detected.
- Calls near the breakpoint (single gyrA mutation) carry the most uncertainty. Gene copy number and expression level are not modelled.


===== batch_011/workspace/output/methods.md =====
# Methods

## Tools and databases
- **AMRFinderPlus 4.2.7** (`/Users/applemacbookpro/miniforge3/envs/amr/bin/amrfinder`), database version **2026-10-29.1**. It uses BLAST+ 2.17.0 and HMMER 3.4 internally.
- No other AMR tools were installed (abricate, RGI, ResFinder/PointFinder and staramr were not found). No internet access was used.
- Python 3 with the standard library only (`output/scripts/call.py`) to turn genotypes into calls.

## Command
For each `data/genomes/ISO_###.fasta`:
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 --name ISO_### -o output/amrfinder/ISO_###.tsv
```
I used the default identity and coverage thresholds (curated per-reference cut-offs, otherwise 90% identity and 50% coverage). `-O Escherichia` turns on point-mutation screening (gyrA, parC, parE, ftsI, cirA and others). The raw outputs are in `output/amrfinder/`.

## Genotype-to-phenotype rules
Only rows with `Type == AMR` were used. Partial hits below 50% coverage were ignored.

| Antibiotic | Called R if any of |
|---|---|
| ampicillin | acquired bla genes: TEM, SHV, OXA-1, CTX-M, CMY, DHA, or a carbapenemase (NDM/KPC/VIM/IMP/OXA-48-like); or an ampC promoter mutation |
| cefotaxime | an ESBL (CTX-M, SHV-2/5/12), an acquired AmpC (CMY, DHA), a carbapenemase, or an ampC promoter mutation. TEM-1 and OXA-1 alone do not count |
| meropenem | a carbapenemase gene (NDM, KPC, VIM, IMP, OXA-48-like) |
| ciprofloxacin | a QRDR mutation in gyrA (S83, D87) or parC (S80, E84), or any qnr gene. parE mutations alone, and aac(6')-Ib-cr alone, are not enough |
| gentamicin | aac(3)-I/II/IV/VI, ant(2'')-Ia, or a 16S rRNA methyltransferase (rmt*, armA, npmA) |
| trimethoprim/sulfamethoxazole | any acquired dfrA/dfrB gene (all dfr-positive isolates here also carried sul1 and/or sul2) |

Otherwise the call is S and the evidence is "no determinant found".

These are not treated as resistance determinants for the six drugs:
- chromosomal blaEC (intrinsic ampC without a promoter mutation)
- efflux genes (acrF, emrD, mdtM)
- marR_S3N and acrR frameshifts
- ftsI insertions, cirA and mrdA mutations (on their own)

### Uncertain calls
- **ISO_103, ciprofloxacin.** This is called R on qnrS1 alone. qnrS1 gives low-level resistance that sits near the EUCAST/CLSI breakpoint.
- **ISO_108, ampicillin.** blaTEM sits at a contig end (86% coverage). This does not affect the call because blaCTX-M-55 and blaNDM-5 are also present.


===== batch_012/workspace/output/methods.md =====
# Methods

## Inputs
8 *E. coli* draft assemblies (`data/genomes/ISO_111`–`ISO_118.fasta`, 74–257 contigs each) and 6 antibiotics from `data/antibiotics.txt`. Only the genome sequences were used.

## Tools found and their versions
- **AMRFinderPlus 4.2.7**, database version **2026-10-29.1** (`.../envs/amr/share/amrfinderplus/data/2026-10-29.1`). It runs its own bundled BLAST+/HMMER (and stxtyper).
- **BLAST+ 2.17.0** (`blastn`), used for one manual check.
- Also present but not used: HMMER suite. abricate, RGI, ResFinder, staramr, prodigal, mlst and kraken2 are not installed.
- No internet access was used and nothing was downloaded or updated.

## Gene and mutation detection
For each isolate:
```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia --plus --threads 4 -o output/amrfinder/ISO_###.tsv
```
- `-O Escherichia` turns on species-specific point-mutation screening (gyrA, parC, parE, ompF, ftsI, ampC promoter and others).
- `--plus` reports additional genes, such as efflux pumps and virulence genes.
- All other settings were left at the defaults (curated per-gene identity and coverage cut-offs).
- Raw outputs are in `output/amrfinder/`.

**Manual check for ISO_115:** AMRFinderPlus reported blaTEM as `PARTIALX` (54% coverage, contig_61). I extracted the full-length blaTEM-1 gene (858 bp) from ISO_117 (contig_91:11336-12193). I then ran `blastn -evalue 1e-20` with it against the ISO_115 assembly. Two pieces matched:
- query positions 1–464 on contig_61, 100% identity
- query positions 457–858 on contig_102, 100% identity

Together they cover the whole gene, so this is an assembly break and not a truncated gene. I treated it as an intact blaTEM-1. The script is `output/work/call.py`.

## Rules for turning genotypes into S/R calls
Only hits with Type = AMR were used. The intrinsic or ubiquitous hits were ignored for these drugs: chromosomal blaEC (with no ampC promoter or attenuator mutation), acrF, emrD and mdtM.

| Antibiotic | Called R if any of these are present | Otherwise |
|---|---|---|
| ampicillin | an acquired beta-lactamase: blaTEM, blaSHV, blaOXA-1, blaCTX-M, plasmid AmpC (blaCMY, blaDHA) or a carbapenemase | S |
| cefotaxime | an ESBL (blaCTX-M), plasmid AmpC (blaCMY, blaDHA) or a carbapenemase (blaNDM, blaKPC, blaVIM, blaIMP, blaOXA-48-like). Narrow-spectrum blaTEM-1 and blaOXA-1 alone count as S | S |
| ciprofloxacin | any gyrA, parC or parE QRDR mutation, or a PMQR gene (qnr, aac(6')-Ib-cr, qepA, oqxAB). Every R isolate here had gyrA S83L + D87N + parC S80I | S. A marR mutation alone is not enough |
| gentamicin | aac(3)-type enzymes, ant(2'')-Ia, or 16S rRNA methylases (armA, rmt*, npmA). aph(3'')/aph(6)/aph(3')-Ia, aadA and aac(6')-Ib-cr do not affect gentamicin | S |
| meropenem | a carbapenemase gene | S. Porin loss (ompF) plus AmpC is noted in the evidence but called S, because it mainly affects ertapenem |
| trimethoprim/sulfamethoxazole | an acquired dfrA or dfrB gene (with or without sul1/2/3) | S. A sul gene alone does not give co-trimoxazole resistance |

Calls are categorical (S/R), with no intermediate category. No NA calls were needed.

## Caveats
- Predictions are based on presence or absence of determinants only.
- Gene expression, copy number, MIC breakpoints (EUCAST vs CLSI) and novel mechanisms are not modelled.
- ISO_116 has blaCMY-42, an ompF frameshift and mrdA_A543V. It could have raised carbapenem MICs, but it is predicted meropenem S.
