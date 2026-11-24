===== batch_001/workspace/output/methods.md =====
# Genome-only resistance predictions

Inputs were all ten `data/genomes/ISO_*.fasta` assemblies, treated as Escherichia coli as specified, and the six exact antibiotic names in `data/antibiotics.txt`. No phenotype, isolate metadata, internet access, downloads, or external services were used. `assembly_qc.json` records sequence lengths, contig counts, ambiguous-base counts and SHA-256 input checksums, calculated with Python standard-library code. Original assemblies were preserved. For isolates lacking a completed original-assembly report, derived overlapping windows were searched as described below.

## Software and local database

- NCBI AMRFinderPlus **4.2.7**, checked with `amrfinder --version`.
- NCBI BLAST+ **2.17.0+**, build August 22, 2026; `blastn`, `blastp`, `blastx`, and `tblastn` versions checked before their analyses. Nucleotide-only AMRFinder logs show `tblastn` for original assemblies, `blastx` for windowed assemblies, and `blastn` for nucleotide mutation searches.
- HMMER **3.4** (August 2023), checked using `hmmsearch -h`; available but no protein/HMM search was requested in this nucleotide-only workflow.
- Python **3.9.6**, checked using `python3 --version`; standard library only for orchestration, assembly summaries, parsing and prediction generation.
- NCBI AMRFinderPlus database **2026-10-29.1**, explicitly verified using `amrfinder -d DB --database_version`, where DB was `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. The default database path did not resolve, so the installed database was supplied explicitly. No database was updated. The database's protein reference catalogue, hierarchy/curated cutoffs, Escherichia protein mutation catalogue and Escherichia DNA mutation references were used through AMRFinder.

Executable discovery found AMRFinderPlus and BLAST+ on PATH; ABRicate, RGI and ResFinder executables were not on PATH. All resistance searches used the single local database above.

## Search parameters and reproducibility

For each isolate, the command was:

```
amrfinder -d /Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1 \
  -n data/genomes/ISO_XXX.fasta -O Escherichia --threads 2 \
  --mutation_all output/amrfinder/ISO_XXX.mutations.tsv \
  -o output/amrfinder/ISO_XXX.tsv
```

Standard output/error were retained in `output/amrfinder/ISO_XXX.log`. Up to three independent isolates were run concurrently. No `--plus`, `--report_common`, protein annotation, or custom identity/coverage search options were supplied. AMRFinder defaults were used: curated identity threshold when present, otherwise 0.9; minimum reference coverage 0.5; genetic code 11. The organism option enables curated Escherichia resistance mutation detection. The mutation-all tables retain wild-type and unknown changes for audit; only resistance mutations in the primary report can drive R calls.

## Long-contig search adjustment

Original-assembly runs for ISO_002, ISO_003 and ISO_007 were unusually slow in translated searches. For ISO_002, ISO_003, ISO_007, ISO_008, ISO_009 and ISO_010, each original contig was divided into windows of at most 30,000 nt at a stride of 27,000 nt (3,000 nt overlap), without changing bases. Window headers append `__offset_START`, with zero-based original-contig offsets. Derived FASTA files are retained in `output/chunked_genomes/`; `python3 output/window_genomes.py` reproduces this transformation. The identical AMRFinder command and database were used with `-n output/chunked_genomes/ISO_XXX.fasta`, and reports/logs were written under `output/amrfinder_chunked/`. Up to three windowed searches ran concurrently. These windowed reports take precedence in prediction generation; repeated hits in overlaps are collapsed by element symbol. The overlap exceeds the length of the main acquired resistance genes and quinolone targets used for these predictions. Positions in windowed reports are relative to the window. Earlier unwindowed runs and any incomplete logs are not used when a windowed report exists.

`output/make_predictions.py` implements the genotype-to-phenotype rules and can be rerun from the workspace. Only primary-report AMR entries with at least 90% reference coverage and 90% identity, excluding PARTIAL methods, are eligible to drive calls. This additional filter avoids treating short fragments as functional determinants. Allele labels and amino acid changes are reported as assigned by AMRFinder. Unknown substitutions and ordinary intrinsic genes are not inferred to confer resistance.

## Translation to calls

These are qualitative genome-based predictions, without MIC estimation or a specified clinical breakpoint system:

- **Ampicillin:** R for an eligible acquired `bla` beta-lactamase, including TEM, OXA, CTX-M, acquired AmpC and carbapenemases.
- **Cefotaxime:** R for CTX-M or another explicitly annotated extended-spectrum beta-lactamase, acquired AmpC families CMY/DHA/FOX/ACT/MIR/ACC/MOX/LAT, or KPC/NDM/VIM/IMP. Narrow-spectrum TEM-1 and OXA-1 alone do not drive this call.
- **Meropenem:** R for KPC/NDM/VIM/IMP, OXA-48-like alleles (OXA-48/181/232/244), or a bla reference explicitly annotated as a carbapenem resistance enzyme. MrdA substitutions alone are not treated as meropenem resistance determinants. ESBL alone does not drive meropenem resistance.
- **Gentamicin:** R for an eligible entry whose curated Subclass includes GENTAMICIN, or an acquired 16S rRNA methyltransferase armA/rmtA–rmtH/npmA (including rmtC, whose database Subclass is the broader AMINOGLYCOSIDE). Streptomycin-only aadA and amikacin/kanamycin/tobramycin AAC(6')-Ib entries do not drive this call.
- **Ciprofloxacin:** curated gyrA resistance substitutions drive R; accompanying gyrB/parC/parE mutations, qnr, qepA, oqx and AAC(6')-Ib-cr determinants are included in evidence where present. A low-level plasmid mechanism or isolated parC/parE/gyrB determinant without a gyrA change is assigned NA because clinical resistance is uncertain. ParE I529L alone is not used to predict resistance.
- **Trimethoprim/sulfamethoxazole:** R if an eligible acquired dfr or sul determinant is present, using a conservative resistance rule for either component; all detected eligible dfr and sul genes are listed. A single component's determinant is less certain than determinants for both components.
- **S:** no eligible determinant relevant to that antibiotic was found. Evidence is exactly `no determinant found`. S is an absence-based prediction, not proof of phenotypic susceptibility.

Regulatory changes, expression, heteroresistance, novel alleles, porin defects, ESBL/AmpC plus permeability effects and unrepresented mechanisms may cause discordance. Chromosomal ampC promoter variation and non-curated regulatory/porin variants were not independently analyzed. Fragmented or incomplete assemblies can conceal determinants; the 90% coverage filter can miss disrupted or split genes. These limitations particularly affect absence-based S calls. No clinical susceptibility measurements or outcome claims are made.


===== batch_002/workspace/output/methods.md =====
# Genome-based resistance predictions

All ten supplied Escherichia coli assemblies were searched locally, without internet access, against the installed NCBI AMRFinderPlus database. No phenotype data or isolate metadata were used.

## Software and database

- AMRFinderPlus 4.2.7 (queried with `amrfinder --version`).
- NCBI AMRFinderPlus database 2026-10-29.1, database format 4.2.0 (confirmed with `amrfinder -d <database> --database_version`). Explicit database directory: `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. The default database path did not exist; the installed database was supplied explicitly. No update was attempted.
- NCBI BLAST+ 2.17.0+ (build Aug 22 2026); `blastn`, `blastx`, `tblastn`, and `blastp` versions were inspected. The nucleotide-only AMRFinder workflow uses translated nucleotide searches and nucleotide mutation searches; no independent BLAST analysis was added.
- HMMER 3.4 (Aug 2023), inspected with `hmmsearch -h`; no independent HMM search was performed.
- Python 3.9.6 standard library for job orchestration, TSV parsing, rule application, and output validation.

AMRFinderPlus and BLAST were available on PATH; ABRicate, RGI, ResFinder and PointFinder executables were not found on PATH. `--list_organisms` confirmed that `Escherichia` is supported.

## Search procedure

For every `data/genomes/ISO_###.fasta`:

```sh
amrfinder -n data/genomes/ISO_###.fasta \
  -d /Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1 \
  -O Escherichia --threads 2 \
  --mutation_all output/amrfinder/ISO_###.mutations.tsv \
  -o output/amrfinder/ISO_###.tsv
```

ISO_011 used four threads; other isolates used two threads, with at most two isolate searches running concurrently. Other options were defaults: curated identity thresholds where available, otherwise 90% identity; minimum reference coverage 50%; translation table 11; core report, without `--plus` or `--report_common`. No protein annotation was supplied. AMRFinder searches its bundled resistance protein/reference hierarchy and Escherichia protein/DNA mutation catalogs. Raw resistance reports and all-site mutation reports are retained in `output/amrfinder/`. Wild-type/unknown variants in the all-site reports are not treated as resistance determinants.

## Genotype-to-prediction rules

The accompanying `output/call_predictions.py` implements the exact rules and records the determinants driving each positive call. Calls use the main AMRFinder report, with an additional minimum 90% reference coverage for acquired genes, excluding interrupted/internal-stop matches. Contig-end partial matches are accepted at >=80% reference coverage and >=99% identity because missing sequence can reflect assembly fragmentation. This exception accepts ISO_017 aac(3)-IId (86.71% coverage, 100% identity, PARTIAL_CONTIG_ENDX) for gentamicin resistance; the assembly does not establish whether the missing end is intact. Curated resistance point mutations are retained. These are deterministic genomic predictions, not measured MICs or breakpoint-based susceptibility tests.

- Ampicillin: acquired beta-lactamases, including narrow-spectrum TEM/OXA enzymes, ESBLs, acquired AmpC enzymes, and carbapenemases predict R. Native basal chromosomal ampC is not by itself counted.
- Cefotaxime: CTX-M ESBLs, identified ESBL TEM/SHV variants, acquired AmpC enzymes, and broad-spectrum carbapenemases (NDM/KPC/VIM/IMP) predict R. TEM-1, OXA-10 and OXA-48 alone do not predict cefotaxime resistance. Recognized ampC regulatory resistance variants also count.
- Meropenem: an acquired carbapenemase predicts R, including OXA-48 even though its MIC effect varies. Porin or target mutations alone do not establish meropenem resistance.
- Ciprofloxacin: recognized GyrA/ParC resistance substitutions or acquired quinolone/fluoroquinolone determinants (qnr, qepA, oqxAB, aac(6')-Ib-cr) predict R. Low-level determinants can yield MICs below clinical resistance breakpoints; this rule favors detecting genomic resistance potential. Isolated ParE or general efflux-regulator variants are not sufficient.
- Gentamicin: acquired determinants with GENTAMICIN in the curated subclass, or broad aminoglycoside resistance 16S methylases (armA/rmt/npmA), predict R. Streptomycin/kanamycin-specific aadA/aph genes do not count.
- Trimethoprim/sulfamethoxazole: a trimethoprim-resistant dfr determinant predicts R; accompanying sul genes are also reported. Sul alone is insufficient to establish resistance to the combination.

S means no qualifying resistance determinant was found for that antibiotic under these rules; evidence is `no determinant found`. It does not prove phenotypic susceptibility. Expression, novel determinants, promoter variation beyond the curated catalog, copy number, permeability, assembly gaps, and interactions between mechanisms may affect real susceptibility. NA is reserved for a failed/uninterpretable genome search. No external reference download or clinical breakpoint table was used. General regulator mutations (e.g. marR_S3N or acrR_T5N), isolated parE changes and ftsI variants were not sufficient alone for a call for these six drugs. A near-complete TEM-family match (ISO_017, 97.90% coverage, 100% identity to the TEM-1 reference) was accepted for ampicillin but not cefotaxime.

## Output validation

All ten searches completed successfully. The final TSV contains exactly 60 unique isolate–antibiotic pairs, the requested four columns, and only S/R calls with nonempty evidence. Calls comprise 24 R and 36 S; no NA calls were required.


===== batch_003/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility predictions

## Inputs and offline analysis
All ten supplied E. coli assemblies (ISO_021–ISO_030) were analyzed against all six exact antibiotic names in data/antibiotics.txt. No phenotype data, internet, downloads, or database updates were used. Python 3.9.6 (standard library) parsed FASTA files, summarized assembly sizes/ambiguity (assembly_qc.json), parsed reports, and wrote/validated predictions. Assemblies contain 4.63–5.50 Mb and 54–220 contigs; ISO_025 has 586 ambiguous bases. These are assembly-based predictions, not measured MICs.

## Software and database
PATH discovery found AMRFinderPlus and BLAST; abricate, rgi, minimap2, resfinder and pointfinder were not on PATH. AMRFinderPlus 4.2.7 was used with the installed NCBI AMRFinderPlus database 2026-10-29.1, explicitly located at:

`/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`

The default AMRFinder database path was invalid; no update was attempted. The explicit database version and supported Escherichia organism panel were checked before scanning. Versions were checked with amrfinder --version, blastn/blastp/blastx/tblastn -version (all BLAST 2.17.0+, build Aug 22 2026), hmmsearch -h (HMMER 3.4, Aug 2023), and python3 --version before analysis. Nucleotide-only AMRFinder ran translated BLAST (tblastn) and nucleotide mutation searches (blastn); no protein annotation or HMM scan was supplied/performed.

For each isolate the command was:

```
amrfinder -n data/genomes/ISO_###.fasta -O Escherichia \
  -d /Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1 \
  --threads 2 --mutation_all output/amrfinder/ISO_###.mutations.tsv \
  -o output/amrfinder/ISO_###.tsv
```

ISO_021 used --threads 4 instead of 2. Other parameters were defaults: curated family identity thresholds where available, otherwise 90% amino acid identity (`--ident_min -1`), minimum reference coverage 50% (`--coverage_min 0.5`), genetic code 11. No --plus or --report_common was used. Both acquired genes and curated Escherichia protein/DNA mutation calls were considered. The mutation_all reports also contain wild-type and unknown variants; these were not treated as resistance determinants. Raw reports and stderr logs are retained in output/amrfinder; run_amrfinder.py reproduces the remaining nine runs.

## Genotype-to-prediction rules
Drug-specific rules were applied to reported AMR hits, rather than treating every member of an antibiotic class as conferring resistance to every drug. Reported intact genes (at least 90% reference coverage, no reported internal stop) and curated relevant mutations were used. Partial hits below 90% coverage were not sufficient by themselves. S means no qualifying determinant for that drug was found; it does not establish phenotypic susceptibility. NA is reserved for unresolved drug-specific evidence that prevents a call.

- Ampicillin: R for acquired penicillin-hydrolyzing beta-lactamases, including TEM and CTX-M, or curated mutations whose AMRFinder subclass explicitly includes AMPICILLIN (e.g. marR_S3N).
- Cefotaxime: R for CTX-M ESBLs or another established extended-spectrum cephalosporinase/carbapenemase. TEM-1 alone does not qualify. ISO_024's family-level blaTEM hit was investigated separately as described below.
- Ciprofloxacin: R for curated quinolone/fluoroquinolone resistance mutations (including gyrA_S83L, gyrA_D87N, parC_S80I), or drug-relevant acquired quinolone determinants. Multiple QRDR mutations strengthen this call. A single gyrA mutation and regulatory mutations can cause only reduced susceptibility; calling these R is an explicit conservative genotype-based rule and may overcall resistance at some MIC breakpoints.
- Gentamicin: R for gentamicin-specific modifying enzymes (e.g. aac(3)-IId) or broad aminoglycoside resistance methylases. Streptomycin determinants aph(3'')-Ib, aph(6)-Id and aadA, and kanamycin-specific aph(3') genes do not qualify.
- Meropenem: R for a recognized carbapenemase. ESBL/TEM alone do not qualify. Porin loss combined with ESBL/AmpC can cause resistance but was not comprehensively modeled.
- Trimethoprim/sulfamethoxazole: R for qualifying dfr resistance genes; co-occurring sul genes provide additional support. Sul alone is not sufficient to infer resistance to the combination. ISO_022 has only a partial sul2 (63.10% coverage) and no dfr; this does not drive an R call.

Absence-based calls use evidence 'no determinant found'; this means no determinant meeting the above drug-specific rule, even when irrelevant determinants occur. Constitutive intrinsic efflux genes and unclassified variants were not used as evidence of acquired resistance. No clinical breakpoint standard or MIC model was applied. Expression, gene dosage, novel mechanisms, assembly gaps, and regulatory/porin mechanisms beyond the curated mutation panel remain limitations, particularly for negative calls and regulatory-only R calls.

## Supplemental TEM check
ISO_024 contains a full-length TEM-family hit, 99.65% identical to TEM-1 (WP_000027057.1). The matching reference protein was extracted directly from the same database AMRProt.fa and contig_29 from the assembly. BLASTX 2.17.0+ was run with defaults and:

```
blastx -query output/ISO_024_contig29.fna -subject output/TEM1_reference.faa \
  -outfmt '6 qseqid sseqid pident length qstart qend sstart send qseq sseq' \
  -out output/TEM1_alignment.tsv
```

The full-length primary alignment differs only at precursor residue 11 (I11M), in the signal peptide, with the mature TEM-1 sequence unchanged. It therefore supports ampicillin resistance but was not classified as an ESBL or used for cefotaxime resistance. Short secondary alignments were ignored. No novel TEM allele name was assigned.

## Final output and validation
make_predictions.py records the exact mapping implemented for this dataset. For the observed genes the cefotaxime-positive families were CTX-M and KPC; gentamicin positivity was aac(3)-IId; meropenem positivity was KPC-2. The internally stopped blaOXA in ISO_030 and the 86.01%-coverage partial blaTEM in ISO_027 were excluded. ISO_027 has an intact CTX-M-55 independently supporting its beta-lactam calls. The curated parC_S57T/parE_I355T calls in ISO_030 were counted under the quinolone rule; these accessory mutation-only signals are less definitive for clinical ciprofloxacin resistance than the combined gyrA/parC QRDR pattern in ISO_027. Similarly, ISO_026's ampicillin call depends on the curated marR_S3N association rather than an acquired beta-lactamase. These uncertainties are retained explicitly rather than interpreted as measured phenotypes.

Validation confirmed exactly 60 unique isolate–antibiotic pairs, the requested four-column header, exact input antibiotic strings, nonempty evidence, and allowed prediction labels. Final counts: 18 R, 42 S, 0 NA. No scan failed. All supporting files are local and the two requested deliverables are predictions.tsv and methods.md.


===== batch_004/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility predictions

## Inputs and scope
All 10 supplied E. coli assemblies (ISO_031 through ISO_040) were screened against a locally installed resistance database. Antibiotic names and order were read directly from `data/antibiotics.txt`. No internet access, database update, download, phenotype labels, or external isolate metadata were used. Input SHA-256 checksums are retained in `input_sha256.txt`. Basic FASTA counts are retained in `assembly_qc.json`; assemblies are 4.68–5.28 Mb, with 81–261 contigs and 0–92 ambiguous N bases. These checks do not establish completeness or exclude contamination.

## Software and database
Versions were checked before analysis using `amrfinder --version`, BLAST executables' `-version`, `hmmsearch -h`, and `python3 --version`.

- NCBI AMRFinderPlus 4.2.7, executable `/Users/applemacbookpro/miniforge3/envs/amr/bin/amrfinder`.
- NCBI AMRFinderPlus database **2026-10-29.1**, database format **4.2.0**, at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. Confirmed with `amrfinder -d <database> --database_version`. Organism support was verified using `--list_organisms`.
- NCBI BLAST+ 2.17.0+ (blastn, blastp, blastx, tblastn version checks; AMRFinder's nucleotide workflow actually ran tblastn and blastn).
- HMMER 3.4 (Aug 2023), available and version checked; no separate HMMER search was run because inputs were nucleotide assemblies, without protein annotations.
- Python 3.9.6 standard library for FASTA checks, report parsing, prediction generation, and output validation.

The default AMRFinder database path was invalid. The installed database was located locally and explicitly supplied; the initial default-path version query failed before any genome analysis. ABRicate, RGI, ResFinder, PointFinder, minimap2, and samtools were not on PATH. No installation was attempted.

## Search parameters and retained evidence
For each isolate, the exact command template was:

```sh
amrfinder -n data/genomes/ISO_XXX.fasta \
  -O Escherichia \
  -d /Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1 \
  --threads 4 \
  --mutation_all output/amrfinder/ISO_XXX.mutations.tsv \
  -o output/amrfinder/ISO_XXX.tsv \
  > output/amrfinder/ISO_XXX.log 2>&1
```

Search used default identity threshold `--ident_min -1` (curated threshold where available, otherwise 90%), minimum reference coverage `--coverage_min 0.5`, and translation table 11. Neither `--plus` nor `--report_common` was enabled. No annotations or gene-calling tool were required. Escherichia-specific protein and nucleotide mutation searches were enabled. The main report contains recognized resistance determinants; mutation_all additionally records wild-type and unknown states, which were not treated as resistance determinants. Coordinates, coverage, identity, reference accessions, and detection methods remain in the raw TSVs. No extra BLAST searches or custom reference databases were used.

## Translation to calls
Calls are deterministic genome-based estimates, not measured MICs or validated clinical susceptibility tests. No explicit EUCAST/CLSI breakpoint version or trained classifier was applied. `S` means the completed screen found no determinant judged sufficient for resistance to that particular drug. Absence of a database hit cannot exclude novel mechanisms, expression changes, porin defects, or assembly gaps. `NA` is used when detected evidence is insufficient to resolve a call.

Drug rules and the exact observed determinants are recorded below after completion of all screens. Database drug classes were interpreted by substrate specificity rather than transferring resistance to every member of a class. Intrinsic wild-type chromosomal functions and unrelated resistance determinants were not counted. The reproducible decision logic is retained in `make_predictions.py`.

| Antibiotic | Decision rule |
|---|---|
| ampicillin | R for an acquired beta-lactamase with an ampicillin resistance spectrum, including observed TEM-1, SHV-1, and KPC-3. MarR S3N alone yields NA. |
| cefotaxime | R for an ESBL, acquired AmpC, or broad-spectrum carbapenemase (observed KPC-3). TEM-1 or SHV-1 alone does not qualify. CirA disruption is a cefiderocol mechanism and is excluded. |
| ciprofloxacin | R for recognized quinolone resistance target substitutions, including observed gyrA S83L with or without D87N and parC S80I/E84V; associated qnrS1 is included in evidence. A lone gyrA S83L is a lower-confidence R estimate because the resulting MIC can be near susceptibility breakpoints. MarR S3N or plasmid quinolone determinants alone yield NA without a target substitution. ParE I529L alone was not used to drive a call. |
| gentamicin | R for a determinant whose curated subclass specifically includes GENTAMICIN (observed aac(3)-IId). Streptomycin-specific aadA/aph(6)-Id/aph(3\'\')-Ib and kanamycin-specific aph(3\')-Ia do not qualify. |
| meropenem | R for a carbapenemase (observed KPC-3). TEM-1 or SHV-1 alone does not qualify. No comprehensive porin/expression model was implemented. |
| trimethoprim/sulfamethoxazole | R when both a resistant dihydrofolate reductase (dfr) and sulfonamide resistance (sul) are detected. If only one component has a determinant, NA because the combination phenotype is uncertain. If neither is detected, S. |

MarR S3N is flagged by this database as a multidrug-associated variant, but its presence alone does not establish a clinical ampicillin or ciprofloxacin resistance phenotype; those affected calls are deliberately NA. This is a conservative interpretation rather than a claim that the database hit was absent. Similarly, single-component folate-pathway resistance was not automatically converted into a combination-drug R call. Other S rows use the requested evidence text "no determinant found", meaning no qualifying determinant for that drug under the stated rules, even when unrelated determinants were present.

No expression, MIC, plasmid copy number, or comprehensive porin-loss inference was made. Susceptibility calls rely on absence of recognized determinants and are less secure than positive calls supported by an intact characterized resistance gene. These estimates should not be interpreted as laboratory susceptibility results.

## Completed analysis and validation

All ten AMRFinder runs completed successfully. `predictions.tsv` has exactly the required four columns and 60 unique isolate–antibiotic pairs, covering ten isolates and six antibiotics. Counts: S=41, R=12, NA=7. Seven NA calls comprise ampicillin/ciprofloxacin in ISO_033 and ISO_036 (MarR S3N only), and trimethoprim/sulfamethoxazole in ISO_037 (dfrA14 only), ISO_038 (sul2 only), and ISO_040 (sul1 only).

Observed acquired beta-lactamases were TEM-1, SHV-1, and KPC-3; all had 100% reference coverage and identity. No qualifying cefotaxime or meropenem determinant other than KPC-3 was detected. Raw reports and successful-run logs are retained under `amrfinder/`. All reported hits exceeded 90% reference coverage and 90% identity; no fragmentary acquired gene was used to drive a resistance call.


===== batch_005/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility prediction

## Inputs and scope

All ten supplied E. coli assemblies (`data/genomes/ISO_041.fasta` through `ISO_050.fasta`) were analyzed without sequence modification. The six antibiotic names were read verbatim from `data/antibiotics.txt`. Only supplied sequences and preinstalled local reference data were used; no internet requests, downloads, database updates, phenotype labels, or isolate metadata were used.

## Software and database

Availability was checked on PATH and in the installed conda environment. AMRFinderPlus was available; abricate, ResFinder, PointFinder, RGI and minimap2 executables were not found on PATH. Versions were checked before analysis: AMRFinderPlus **4.2.7** (`amrfinder --version`); NCBI BLAST+ **2.17.0+** (`blastn`, `blastp`, `blastx`, and `tblastn -version`); HMMER **3.4**, August 2023 (`hmmsearch -h`). Python **3.9.6** (`python3 --version`) with standard-library modules was used for parsing, rule application and validation. HMMER was available but no protein/HMM search was requested: the analysis used nucleotide-input AMRFinder with translated searches.

The installed NCBI AMRFinderPlus database was **2026-10-29.1**, checked with `amrfinder --database_version` and `version.txt`. Its absolute directory was `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. This supplies curated AMR protein references, hierarchy and thresholds (`AMRProt.fa`, `fam.tsv`), protein mutation references (`AMRProt-mutation.tsv`) and Escherichia nucleotide mutation references (`AMR_DNA-Escherichia.fa` and `.tsv`). `amrfinder --list_organisms` confirmed **Escherichia** as a supported mutation-search group.

## Commands and parameters

For each isolate, the following was run successfully (replace `ISO_041` with its identifier):

```sh
amrfinder -n data/genomes/ISO_041.fasta -O Escherichia --threads 4 \
  --mutation_all output/amrfinder/ISO_041.mutations.tsv \
  -o output/amrfinder/ISO_041.tsv \
  > output/amrfinder/ISO_041.log 2>&1
```

No `--plus`, protein input, annotation input or reference update was used. Defaults were retained: curated identity threshold when available, otherwise 90% amino-acid identity (`--ident_min -1`); minimum reference coverage 50% (`--coverage_min 0.5`); bacterial translation table 11. AMRFinder invoked its own tblastn/blastn searches and report processing. Raw reports, all-site mutation reports (including wild-type and unknown variants) and execution logs are preserved in `output/amrfinder/`.

For phenotype rules, acquired-gene hits must additionally cover at least **90%** of the reference and must not have a partial-hit method. AMRFinder's curated identity filtering remains in force. POINT calls are taken from the main curated AMRFinder report; unknown variants from `--mutation_all` are not automatically resistance determinants. No partial hit was used to drive a call. `output/make_predictions.py` contains the exact executable translation rules; run from the workspace with `python3 output/make_predictions.py` after all searches complete.

## Genotype-to-prediction rules

The output is a binary genomic prediction, not a measured MIC or clinical susceptibility report. No breakpoint standard or dosing regimen was supplied; no MIC or S/I/R breakpoint conversion was attempted.

- **Ampicillin:** an acquired beta-lactamase (`bla` symbol) predicts R. This includes TEM-1, OXA-1, CTX-M enzymes, acquired AmpC and carbapenemases. Basal intrinsic E. coli ampC presence alone does not predict R.
- **Cefotaxime:** an extended-spectrum beta-lactamase (e.g. CTX-M), acquired cephalosporin-hydrolyzing class C enzyme (including CMY/DHA/FOX/ACC/ACT/MIR/LAT/MOX families), or carbapenemase predicts R. TEM-1 and OXA-1 alone are not used for this call, despite broad database class/subclass annotations.
- **Meropenem:** a carbapenemase predicts R (including KPC, NDM, VIM, IMP and OXA-48-like enzymes). CTX-M, TEM-1 or OXA-1 alone does not predict R. Porin disruption alone does not predict R.
- **Gentamicin:** a qualifying acquired gene whose curated AMRFinder subclass explicitly includes GENTAMICIN predicts R (including the observed AAC(3) enzymes). Streptomycin-only aadA and aph genes, and AAC(6')-Ib-cr, are not counted as gentamicin determinants merely because they belong to the aminoglycoside class.
- **Ciprofloxacin:** at least two curated gyrA target substitutions, or a gyrA substitution together with a parC substitution, predicts R. Associated parE substitutions and acquired quinolone determinants are included as supporting evidence. A lone target substitution or acquired low-level quinolone determinant without this combination is assigned NA because the binary resistance level is uncertain. General regulator variants such as marR_S3N, soxS_A12S and acrR changes alone do not drive R; expression and their quantitative effects were not established.
- **Trimethoprim/sulfamethoxazole:** a qualifying acquired dfr gene together with a sul gene predicts R. If only one component is supported, the combination is NA; neither detected predicts S.

Otherwise a successful screen with no applicable determinant produces **S**, with evidence `no determinant found`. This phrase means no determinant meeting the drug-specific rules, not an absence of all AMR genes in the isolate. Evidence for R lists the applicable genes/mutations; duplicate symbols are collapsed. No inference is made from isolate numbering or other isolates' results.

## Limitations

Resistance can arise through mechanisms not represented in the local database, gene expression, copy number, regulatory or structural variants, and combinations of ESBL/AmpC with permeability changes. These were not comprehensively modeled. Fragmented assemblies or ambiguous sequence may conceal determinants. Absence-based S calls are consequently less certain than strong determinant-based R calls. Wild-type mutation-site reports were inspected as supporting evidence, especially for quinolone-susceptible predictions. The sequence-only rules are not a validated clinical diagnostic model and do not establish phenotypic susceptibility.

## Completed-run validation

All ten AMRFinder runs completed successfully. The final TSV was checked for the exact four-column header, 60 data rows, one occurrence of every isolate–antibiotic pair, exact input antibiotic spellings, nonempty evidence and allowed prediction values. There are 28 R calls, 32 S calls and 0 NA calls. The S ciprofloxacin calls have wild-type GyrA positions 83/87 and ParC positions 80/84 in the all-site mutation reports. No curated carbapenemase was found.


===== batch_006/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility predictions

## Inputs and offline software

Analyzed all 10 `data/genomes/ISO_051.fasta` through `ISO_060.fasta` assemblies as Escherichia coli, and all six exact antibiotic names in `data/antibiotics.txt`. No phenotype data, external services, internet queries, downloads, or database updates were used. FASTA QC with Python 3.9.6 counted 4,875,446–5,270,692 bases and 52–184 contigs per isolate; only ISO_052 contained Ns (3). Per-assembly counts are in `assembly_qc.json`. Species identity was supplied by the task, not independently inferred.

Tools were located using `command -v` and the installed environment's binary directory. AMRFinderPlus was available; ABRicate, ResFinder, RGI, minimap2, samtools and Prodigal were not on PATH. Versions were checked before analysis: AMRFinderPlus `amrfinder --version`: **4.2.7**; NCBI BLAST+ `blastn -version`, `tblastn -version`, `blastp -version`: **2.17.0+** (build Aug 22 2026); `hmmscan -h`: **HMMER 3.4 (Aug 2023)**; `python3 --version`: **3.9.6**. The nucleotide-only AMRFinder workflow used translated BLAST and nucleotide BLAST; no protein annotation or separate HMM scan was performed.

`amrfinder --database_version` reported the local **NCBI AMRFinderPlus database 2026-10-29.1**, located at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. Its protein/CDS reference sequences, family hierarchy and curated thresholds, protein mutation catalog, and Escherichia nucleotide mutation references were used. `amrfinder --list_organisms` confirmed that `Escherichia` is supported. No other resistance database was used.

## Analysis command and parameters

For each isolate, ran:

```sh
amrfinder -n data/genomes/ISO_XXX.fasta -O Escherichia --threads 4 \
  --mutation_all output/amrfinder/ISO_XXX.mutations.tsv \
  -o output/amrfinder/ISO_XXX.tsv \
  > output/amrfinder/ISO_XXX.log 2>&1
```

Default database, genetic code 11, minimum identity -1 (curated threshold where supplied, otherwise 0.9), and reference coverage minimum 0.5 were retained. No `--plus` or `--report_common` option was used. The organism panel enables acquired determinant and curated resistance-mutation detection, including nucleotide mutations. Raw determinant reports, all-site mutation reports (including wild type and unknown substitutions), and logs are retained in `amrfinder/`.

For phenotype translation, only AMR-type report rows were considered, excluding STRESS entries. A further filter required >=90% reference coverage and excluded methods containing PARTIAL or INTERNAL_STOP. Unknown substitutions in the all-mutation reports were not interpreted as established resistance. The all-mutation reports were also inspected for coverage of GyrA positions 83/87 and ParC positions 80/84. These assembly-based searches cannot establish expression or MICs; S means no qualifying determinant for that drug under the rules below. It does not prove phenotypic susceptibility. Chromosomal regulatory changes outside the curated panel, porin loss, expression, heteroresistance and assembly omissions can cause discordance. No specific clinical breakpoint system was supplied; these are qualitative genotype predictions, not measured breakpoint classifications.

## Genotype-to-call rules

The executable implementation is `make_predictions.py` and uses the following deterministic rules:

- **Ampicillin:** R for an acquired `bla` beta-lactamase. TEM-1 is sufficient. An isolated regulatory mutation annotated with AMPICILLIN, without an acquired beta-lactamase, yields NA because its quantitative effect is uncertain.
- **Cefotaxime:** R for CTX-M, acquired AmpC families (CMY, DHA, FOX, MOX, ACC, ACT, MIR), KPC/NDM/VIM/IMP, a determinant named extended-spectrum, or a subclass explicitly including CEFOTAXIME. TEM-1 alone is insufficient.
- **Meropenem:** R for carbapenemase families KPC, NDM, VIM, IMP, OXA-48/181/232, a determinant name containing carbapenem, or a subclass explicitly including MEROPENEM. Other beta-lactamases alone are insufficient.
- **Gentamicin:** R for a GENTAMICIN subclass determinant or an acquired broad aminoglycoside methylase (`armA`, `rmt*`, `npmA`). Streptomycin-specific aadA and aph(3'')/aph(6) genes do not imply gentamicin resistance.
- **Ciprofloxacin:** R for at least two curated GyrA substitutions, or a curated GyrA substitution together with a curated ParC substitution. A lone target substitution, acquired quinolone determinant, or regulatory mutation annotated for quinolones without this target-mutation combination yields NA, because low-level quinolone effects do not uniquely determine a ciprofloxacin binary phenotype. All qualifying quinolone symbols are listed as evidence.
- **Trimethoprim/sulfamethoxazole:** R when determinants affecting both TRIMETHOPRIM and SULFONAMIDE are present (e.g. dfrA plus sul). Evidence affecting only one component yields NA because the combination phenotype is uncertain under this conservative rule.
- With no qualifying evidence, call S with evidence `no determinant found`. NA denotes unresolved drug-specific phenotype, not absence of a genome. Relevant genes/mutations justify R or NA; irrelevant resistance genes are not used to infer cross-resistance.

Calls are written in sorted isolate order and input antibiotic order. The script checks the Cartesian-product row count and uniqueness of isolate/antibiotic pairs; the final TSV is also checked for the exact four-column header, valid labels, nonempty evidence, and all 60 expected combinations.


===== batch_007/workspace/output/methods.md =====
# Genome-based susceptibility predictions

Inputs: all ten `data/genomes/ISO_*.fasta` assemblies (ISO_061–ISO_070), treated as Escherichia coli, and the six exact antibiotic names in `data/antibiotics.txt`. No phenotype data, internet access, or downloads were used.

## Software and reference data

Available executables were located using `command -v`. AMRFinderPlus was available; ResFinder, PointFinder, ABRicate, RGI, and StarAMR were not on PATH. Versions were checked before analysis using `amrfinder --version`, `amrfinder --database_version`, `blastn -version`, `blastp -version`, `tblastn -version`, `hmmscan -h`, and `python3 --version`.

- NCBI AMRFinderPlus 4.2.7.
- Bundled local AMRFinderPlus database 2026-10-29.1, at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. This supplies curated AMR protein references, gene-family classification and Escherichia protein/nucleotide mutation references.
- NCBI BLAST+ 2.17.0+ (reported build August 22, 2026); translated nucleotide searches use tblastn and nucleotide mutation searches use blastn. blastp was checked but a separate protein search was not run.
- HMMER 3.4 (August 2023) was available and checked; no separate HMM scan or predicted-protein input was used in this nucleotide-only workflow.
- Python 3.9.6 standard library for parsing, deterministic genotype-to-drug mapping, and output validation.

`amrfinder --list_organisms` confirmed the `Escherichia` option. For each isolate the command was:

```
amrfinder -n data/genomes/ISO_XXX.fasta -O Escherichia --threads 4 --mutation_all output/ISO_XXX.mutations.tsv -o output/ISO_XXX.amrfinder.tsv
```

No database update was requested. All other options were defaults: minimum identity uses curated family thresholds where available, otherwise 0.90; minimum reference coverage 0.50; translation table 11. No `--plus`, `--report_common`, or `--report_all_equal`. AMRFinder determines exact allele, family-level, partial, and resistance-associated point-mutation hits. The ordinary report contains resistance-associated mutations; the `--mutation_all` files also retain wild-type and unknown variants, which were not interpreted as resistance. Raw reports and logs are retained in `output/`.

## Translation into predictions

`output/make_predictions.py` implements the mapping. Only rows with Type AMR are considered. A recognized relevant determinant yields R; otherwise S with evidence `no determinant found`. This is a genome-based prediction, not a measured MIC or a claim of confirmed clinical susceptibility. No clinical breakpoint standard was applied because MICs were not estimated. NA is reserved for failed or uninterpretable analyses.

- **Ampicillin:** acquired beta-lactamases (including TEM, CMY, CTX-M, and carbapenemases) or curated resistance-associated ampC promoter mutations imply R. Routine wild-type chromosomal ampC is not counted.
- **Cefotaxime:** CTX-M ESBLs, CMY/DHA/FOX/MOX/ACC/ACT/MIR AmpC enzymes, KPC/NDM/VIM/IMP enzymes, explicitly annotated extended-spectrum TEM/SHV/OXA alleles, or curated ampC promoter resistance mutations imply R. TEM-1 alone does not imply cefotaxime resistance.
- **Ciprofloxacin:** curated quinolone resistance mutations (gyrA/parC/parE) and acquired quinolone determinants in the AMRFinder report imply R. Wild-type and unknown variants in the all-mutation output are excluded. A single low-effect determinant can be insufficient to cross a clinical breakpoint; this rule prioritizes sensitivity to genetic resistance.
- **Gentamicin:** the AMRFinder subclass must explicitly include GENTAMICIN, or an acquired 16S methylase armA/rmt/npmA must be present. Streptomycin-only aadA/aph(3'')/aph(6) and kanamycin-only aph(3') genes do not trigger R.
- **Meropenem:** recognized carbapenemase families NDM/KPC/VIM/IMP, OXA-48-like alleles (including OXA-181/232/244), GES-5, or an explicitly carbapenem-hydrolyzing enzyme imply R. ESBL/AmpC alone and an isolated porin mutation do not automatically imply meropenem resistance; permeability and expression effects cannot be reliably quantified from these hits.
- **Trimethoprim/sulfamethoxazole:** acquired dfr or sul genes imply R, with both listed where present. A determinant affecting one component is treated conservatively as resistance to the combination.

Limitations: assembly gaps, gene disruption, expression, uncharacterized mechanisms, efflux/porin regulation, and breakpoint-dependent low-level resistance can cause genotype/phenotype disagreement. Default partial-hit detection is retained; hit coverage and identity remain available in the raw reports. Susceptible calls mean absence of a determinant under these explicit drug-specific rules, rather than proof that all resistance mechanisms are absent.

## Run checks and specific interpretation notes

All ten searches completed successfully. Input FASTA symbols were validated and SHA-256 checksums, contig counts, and total sequence lengths recorded in `output/input_checksums.tsv`. The final TSV was checked for the exact header, 60 unique isolate–antibiotic pairs, complete Cartesian-product coverage, valid predictions, and nonempty evidence. All isolates had gyrA and parC entries in the all-mutation reports.

Drug-driving acquired genes were full-length matches (100% reference coverage); gyrA mutation alignments covered 99.66% of their reference. Some unrelated resistance genes had partial matches; they did not drive any of the six drug calls. ISO_063 has CMY-2 and ompC_W124Ter: its meropenem S call follows the rule above and carries uncertainty about permeability effects. ISO_069 has a single gyrA_S83L mutation: its ciprofloxacin R call follows the conservative genetic-resistance rule and has greater breakpoint uncertainty than multi-mutation calls. ISO_070 has dfrA1 without a reported sul gene: its combination-drug R call follows the one-component resistance rule. ISO_065 blaTEMp_C32T is supporting promoter evidence alongside intact TEM-1; it is not used to infer cefotaxime resistance.


===== batch_008/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility prediction

## Inputs and scope

Ten supplied Escherichia coli assemblies, ISO_071 through ISO_080, and the six exact antibiotic names in `data/antibiotics.txt` were analyzed. No internet access, downloads, phenotype labels, or external isolate information were used. Assembly lengths, contig counts and ambiguous-base counts are in `assembly_qc.tsv`; all assemblies contained approximately 5.0–5.5 Mb. Predictions are genomic inferences, not measured MICs or validated clinical susceptibility results. No breakpoint system or dosing regimen was supplied.

## Available software, database and commands

Shell discovery found AMRFinderPlus and NCBI BLAST+; ABRicate, RGI, ResFinder and PointFinder were not on PATH. Version checks preceded analysis:

- AMRFinderPlus `amrfinder --version`: **4.2.7**.
- `amrfinder --database_version`: installed NCBI AMRFinderPlus database **2026-10-29.1**, at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`.
- NCBI BLAST+ `blastn`, `blastp`, `blastx`, and `tblastn`, checked with `-version`: **2.17.0+** (build Aug 22 2026). AMRFinder's nucleotide workflow actually ran tblastn and blastn.
- HMMER `hmmsearch -h`: **3.4 (Aug 2023)**. Availability was checked; no separate HMMER search was performed because no protein annotation was supplied.
- Python `python3 --version`: **3.9.6**, standard library only, for assembly summaries, parsing, prediction generation and validation.

For each input, the exact search command was:

```sh
amrfinder -n data/genomes/ISO_071.fasta --organism Escherichia --threads 4 --mutation_all output/amrfinder/ISO_071.mutations.tsv -o output/amrfinder/ISO_071.tsv
```

The isolate ID was substituted for each assembly. The default installed database was used without updates. Other settings were defaults: curated identity threshold where available, otherwise 0.9 (`--ident_min -1`); minimum reference coverage 0.5; translation table 11; nucleotide input only. `--plus`, `--report_common` and `--report_all_equal` were not enabled. The organism option enables curated Escherichia protein mutations and nucleotide mutations, including the ampC promoter. Searches do not require a separate assembly annotation. The local database supplies AMR protein references and curated family rules, susceptible protein targets and mutation tables, and Escherichia nucleotide mutation references. Individual gene reference accessions, identity and coverage are preserved in the reports.

`output/amrfinder/` retains per-isolate reports, mutation-all reports and logs. Only the main resistance report drives calls: wild-type and UNKNOWN entries from mutation-all reports are not resistance evidence. A further minimum 90% reference coverage filter is applied to avoid treating short fragments as functional determinants; methods starting with INTERNAL_STOP or PARTIAL are excluded. No individual hit identity cutoff beyond AMRFinder's curated/default filtering is imposed. Near-full-length non-exact family matches are accepted at their reported family level; for example blaCTX-M is not relabeled as a particular allele based only on its closest reference.

## Genotype-to-call rules

`make_predictions.py` records the exact implementation and generates the requested table in sorted isolate order and input antibiotic order. Multiple qualifying determinants are deduplicated and listed in evidence.

- **Ampicillin:** R for an acquired bla beta-lactamase, a reported resistance-associated ampC promoter mutation, or a curated mutation explicitly annotated with AMPICILLIN activity. A normal chromosomal ampC gene alone is not used.
- **Cefotaxime:** R for CTX-M, acquired AmpC families (CMY, DHA, FOX, ACC, ACT, MIR, LAT, MOX), KPC/NDM/VIM/IMP/GES, a reported extended-spectrum beta-lactamase, or a resistance-associated ampC promoter mutation. Narrow-spectrum TEM-1 and OXA-1, and OXA-48 alone, do not establish cefotaxime resistance.
- **Meropenem:** R for a carbapenemase annotated with CARBAPENEM activity, or the listed KPC/NDM/VIM/IMP and OXA-48-like families. ESBL or AmpC alone is insufficient. A curated carbapenem-associated ompF/ompC disruption together with an ESBL/acquired AmpC is also called R, listing both mechanisms (observed in ISO_080: ompF_Y253EfsTer3 plus blaCTX-M-15). A porin change alone is insufficient. This interaction is a resistance-risk rule; the exact meropenem MIC remains uncertain. OXA-48 calls use a conservative carbapenemase-present rule even though meropenem MICs can vary.
- **Ciprofloxacin:** R when a curated quinolone resistance mutation in gyrA or gyrB is present; accompanying parC/parE mutations and plasmid quinolone determinants are listed. An isolated parC/parE mutation, qnr, aac(6')-Ib-cr or other low-level quinolone mechanism without a gyrA/gyrB resistance mutation yields NA because a clinical breakpoint phenotype is uncertain. The observed resistant isolates have multiple target mutations. Other mutations with unrelated drug annotations are ignored.
- **Gentamicin:** R for an AMRFinder hit whose substrate annotation explicitly includes GENTAMICIN, or armA/rmt/npmA methylases. Streptomycin-only aadA and aph(3'')/aph(6) determinants and aac(6')-Ib-cr alone do not establish gentamicin resistance.
- **Trimethoprim/sulfamethoxazole:** R when both a trimethoprim resistance determinant (e.g. dfrA) and a sulfonamide resistance determinant (e.g. sul1/sul2) are detected. If only one component is represented, NA is used with the gene and reason recorded, since the combination phenotype cannot confidently be assigned from that finding. If neither is found, S.

For all drugs, S is the operational prediction when no qualifying determinant is detected; its evidence is `no determinant found`. This means no determinant meeting the stated rules was found, not that resistance is impossible. NA is restricted to the explicit ambiguous mechanisms above or an analysis failure. All isolate analyses must complete successfully before the final file is generated.

## Limitations and reproducibility

Unrecognized alleles, assembly errors, gene expression, porin loss, efflux regulation, uncurated promoter variants and gene disruptions can alter phenotype. ESBL/AmpC plus porin loss can produce carbapenem resistance without a detected carbapenemase; the curated porin-disruption-plus-ESBL rule captures one such route but does not exhaustively screen all porin or regulatory mechanisms. Acquired-gene presence does not prove expression, and 90% coverage does not prove an intact ORF. Native chromosomal loci and common polymorphisms are not automatically treated as resistance. These limitations particularly affect determinant-negative S predictions.

Run `python3 output/make_predictions.py` from the workspace to regenerate the table from retained reports. Validation checks require exactly one row per input isolate/antibiotic pair, exactly the four requested columns, allowed prediction labels, and nonempty evidence.


===== batch_009/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility predictions

## Inputs and offline environment

All ten supplied `data/genomes/ISO_*.fasta` assemblies were analyzed as Escherichia coli. The six antibiotic labels were read verbatim from `data/antibiotics.txt`. No phenotype labels, external isolate information, internet access, or downloads were used. `assembly_qc.tsv` records contig counts, sequence lengths, N counts and input SHA-256 hashes. Assemblies contain 4.88–5.48 Mb; this is a basic input sanity check, not a completeness or contamination assessment.

## Software and database

Executable discovery used `command -v` and inspection of the installed AMR environment. AMRFinderPlus was available; ABRicate, ResFinder and minimap2 were not on PATH. Versions were checked before analysis:

- NCBI AMRFinderPlus **4.2.7**, installed in `/Users/applemacbookpro/miniforge3/envs/amr/bin`.
- Local NCBI AMRFinderPlus database **2026-10-29.1**, resolved by `amrfinder --database_version` to `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`. This includes curated resistance protein references, gene-family rules, Escherichia mutation references and mutation annotations.
- NCBI BLAST+ **2.17.0+** (build Aug 22 2026): `blastn`, `blastp`, `blastx` and `tblastn` versions checked. AMRFinder logs report using `tblastn` and `blastn` for this nucleotide-only workflow; checking the other executables does not imply they were run in the screen.
- HMMER **3.4** (Aug 2023), checked with `hmmsearch -h`; no independent HMM search or protein annotation was performed.
- Python **3.9.6**, standard library only, for assembly summaries, genotype interpretation and output validation.

## Search parameters and retained evidence

For each isolate, the command was:

```sh
amrfinder -n data/genomes/ISO_XXX.fasta --organism Escherichia --threads 4 \
  --mutation_all output/amrfinder/ISO_XXX.mutations.tsv \
  -o output/amrfinder/ISO_XXX.tsv
```

Standard error and standard output were retained in `output/amrfinder/ISO_XXX.log`. All searches must complete successfully before prediction export. Defaults were retained: curated identity thresholds where provided, otherwise 90% amino-acid identity (`--ident_min -1`), minimum reference coverage 50% (`--coverage_min 0.5`), and bacterial translation table 11. No `--plus`, protein input, GFF, database update, or nondefault search sensitivity was used. The primary TSV reports detected determinants; the separate mutation file includes wild-type and unknown variants as well as resistance variants. Unknown variants were not treated as resistance determinants. No additional sequence database was used.

## Translation into S/R calls

These are deterministic genotype predictions, not measured MICs or a validated clinical susceptibility assay. R means a relevant resistance mechanism was detected under the rules below; S means no qualifying determinant was detected. S does not prove phenotypic susceptibility. NA is reserved for an incomplete analysis or an unresolved mechanism that prevents a call; all searches completed, so only the latter applies here. The rules are drug-specific; generic antimicrobial class labels alone are insufficient.

- **Ampicillin:** R for acquired penicillin-hydrolyzing beta-lactamases, including TEM-1, CTX-M and CMY-2. Basal native E. coli ampC is not sufficient by itself.
- **Cefotaxime:** R for an extended-spectrum beta-lactamase (e.g. CTX-M) or acquired AmpC (e.g. CMY-2), or a relevant carbapenemase. TEM-1 alone is insufficient. ISO_081 has a CTX-M family hit with 92.44% coverage and 100% identity to its aligned reference (closest reference CTX-M-15); it is reported conservatively as blaCTX-M rather than assigned an exact allele.
- **Ciprofloxacin:** R for multiple established QRDR changes including GyrA S83L and D87N with ParC S80I (additional ParC/ParE mutations and acquired quinolone determinants are supporting evidence). A lone ancillary ParE substitution or an unknown mutation does not establish R. The observed resistant isolates have the multiple-target pattern. ISO_089 has GyrA S83L alone and is assigned NA for ciprofloxacin: this can cause reduced susceptibility but does not reliably resolve a binary S/R call without a breakpoint or MIC. Any lone acquired quinolone determinant without this target pattern would likewise be treated as unresolved.
- **Gentamicin:** R for gentamicin-active aminoglycoside-modifying enzymes (e.g. AAC(3) enzymes or appropriate ANT(2'') enzymes), or acquired 16S rRNA methylases such as RmtB1. AadA and APH(3'')/APH(6) streptomycin determinants and APH(3')-Ia kanamycin determinants do not establish gentamicin resistance.
- **Meropenem:** R for a carbapenemase, or an acquired ESBL/AmpC together with disruption of both major porins OmpC and OmpF. The latter is a mechanistic inference with lower confidence than a carbapenemase call; ESBL/AmpC alone, a single porin change, or cefiderocol-specific CirA disruption is insufficient. ISO_081 has blaCTX-M, ompC_Q171Ter and ompF_A251EfsTer3 and is assigned R by this combined-mechanism rule. Porin expression, efflux and enzyme activity were not measured.
- **Trimethoprim/sulfamethoxazole:** R when acquired resistant dihydrofolate reductase (`dfr`) and sulfonamide resistance (`sul`) determinants co-occur. The observed positive isolates carry both components. A single component alone would require cautious interpretation rather than automatic resistance to the combination.

For each drug, evidence lists the relevant genes or mutations. Negative calls use `no determinant found`. Resistance determinants for antibiotics outside the requested panel are retained in the raw reports but do not change these predictions. There is no direct inference of resistance from assembly size, isolate identity, or unrelated resistance genes.

## Limitations

Nucleotide-only screening can miss divergent, unrepresented or fragmented genes and mechanisms requiring expression or regulatory context. Partial gene hits may not encode an active enzyme. Porin loss plus beta-lactamase does not uniquely determine a meropenem MIC, and this combined-mechanism prediction is less certain. No clinical breakpoint standard, dosing regimen or MIC calibration was supplied, so no breakpoint-based conversion was performed. These limitations also apply to negative calls.

## Output validation

All ten AMRFinder searches completed successfully. `make_predictions.py` reproduces the interpretation and checks 60 unique isolate–antibiotic pairs, the exact requested antibiotic labels, four columns, permitted prediction values and nonempty evidence. An independent final check compared the output pairs with the Cartesian product of input assemblies and antibiotic labels. The output contains 44 S, 15 R and one NA (ISO_089/ciprofloxacin). Raw primary reports, all-mutation reports and execution logs are retained in `output/amrfinder/`.


===== batch_010/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility prediction

## Inputs and offline environment

Ten supplied E. coli assemblies, `data/genomes/ISO_091.fasta` through `ISO_100.fasta`, were analyzed. Antibiotic names and ordering come directly from `data/antibiotics.txt`. No phenotype, isolate metadata, internet access, downloads, or database updates were used.

Executable discovery used `command -v` and inspection of the installed AMR environment. AMRFinderPlus was available; ABRicate, ResFinder, PointFinder, RGI and DIAMOND were not on PATH. Versions were checked before analysis using `amrfinder --version`, `amrfinder --database_version`, `blastn -version`, `blastp -version`, `blastx -version`, `tblastn -version`, `hmmsearch -h`, and `python3 --version`.

- NCBI AMRFinderPlus: **4.2.7**.
- Installed NCBI AMRFinderPlus database: **2026-10-29.1**, at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1` (the resolved default database).
- NCBI BLAST+: **2.17.0+**, build Aug 22 2026 13:45:01. AMRFinder's nucleotide workflow invoked tblastn and blastn; blastp and blastx were inventoried but not separately run for analysis.
- HMMER: **3.4 (Aug 2023)**, inventoried; no separate HMMER analysis or protein annotation was performed.
- Python: **3.9.6**, standard library only, for parsing, decision rules and validation.

The database includes AMR protein/reference nucleotide sequences, curated gene family thresholds, Escherichia protein mutation definitions (`AMRProt-mutation.tsv`) and Escherichia DNA mutation references (`AMR_DNA-Escherichia.*`). `amrfinder --list_organisms` confirmed the supported `Escherichia` panel. No additional external database was used.

## Search parameters and reproducibility

For each isolate, the exact command pattern was:

```sh
amrfinder -n data/genomes/ISO_091.fasta -O Escherichia --threads 4 \
  --mutation_all output/amrfinder/ISO_091.mutations.tsv \
  -o output/amrfinder/ISO_091.tsv \
  > output/amrfinder/ISO_091.log 2>&1
```

The isolate ID was substituted for each of the ten assemblies. All searches completed with exit status zero. Inputs were nucleotide assemblies only. AMRFinder used its default curated identity thresholds (`--ident_min -1`, curated threshold where available, otherwise 0.9), default reference coverage minimum 0.5, and genetic code 11. `--plus`, `--report_common` and `--report_all_equal` were not enabled. Raw gene reports, all-mutation reports and execution logs are retained under `output/amrfinder/`.

For phenotype-driving hits, the parser additionally required at least **90% reference coverage and 90% identity** in the AMRFinder report. Duplicate copies were collapsed to unique symbols. This filter excludes short fragments; it does not exclude the near-full-length GyrA mutation alignments. All resistance-driving acquired genes in these assemblies have full reference coverage and 100% identity. The exact transformation is saved as `output/make_predictions.py`; reproduce with `python3 output/make_predictions.py` from the workspace root.

## Genotype-to-call rules

The calls are deterministic genome-based predictions, without an MIC model or a selected clinical breakpoint standard. An accepted drug-specific determinant gives R; otherwise S is an absence-of-supported-determinant inference. NA would be appropriate for an unprocessable assembly or failed search; none occurred.

| Antibiotic | Rule used |
| --- | --- |
| ampicillin | R for TEM or CTX-M beta-lactamases detected here: TEM-1, CTX-M-1, CTX-M-14, CTX-M-15, CTX-M-65. |
| cefotaxime | R for any of the detected CTX-M ESBLs. TEM-1 alone does not trigger this call. |
| ciprofloxacin | R for accepted GyrA S83/D87 or ParC S80/E84 resistance substitutions. The observed drivers were gyrA_S83L, gyrA_D87N and parC_S80I. A single gyrA_S83L is treated as R in this binary heuristic; its clinical category is less certain than that of combined GyrA/ParC mutations. |
| gentamicin | R for gentamicin-active AAC(3) enzymes; the observed driver was aac(3)-IVa. The script also recognizes aminoglycoside methylases armA/rmt and bifunctional AAC(6')-Ie/APH(2'') if present. Streptomycin-specific aph(3'')-Ib, aph(6)-Id and aadA, and aph(3')-Ia/aph(4)-Ia alone, do not trigger gentamicin R. |
| meropenem | R for recognized carbapenemase families KPC, NDM, VIM, IMP, or OXA-48/181/232. None was detected. CTX-M or TEM alone does not trigger meropenem R. |
| trimethoprim/sulfamethoxazole | R for an acquired dfr determinant; all dfr-positive isolates here also carry sul genes. sul1/sul2 without a detected dfr is treated as S for the combination, with the sul-only evidence explicitly stated. This is a lower-confidence combination-drug inference. |

The rules were applied to the actual detected allele names; this script is not a comprehensive phenotype classifier for other datasets. marR_S3N alone was not treated as sufficient for ampicillin or ciprofloxacin resistance because a regulatory variant does not reliably establish clinical resistance. parC_A56T was not used as a driver. oqxAB alone was not treated as decisive for ciprofloxacin; its carrier also had multiple target mutations. Fosfomycin, fosmidomycin, cefiderocol, colistin, macrolide, tetracycline and phenicol determinants do not drive the six requested drug calls.

S entries generally have evidence `no determinant found`, meaning no determinant accepted by the above drug-specific rules, not that the genome lacks all AMR genes. sul-only combination calls state the detected genes instead. No expression measurements, porin analysis, comprehensive regulatory variant interpretation or assembly completeness assessment was performed. Undetected or uncharacterized mechanisms and breakpoint-dependent effects can cause discrepancies with measured susceptibility, especially for single-target quinolone mutations, sul-only combination calls and ESBL plus permeability mechanisms.

## Output validation

`predictions.tsv` contains the exact four requested tab-separated columns, 60 data rows (10 isolates × 6 antibiotics), unique isolate–antibiotic pairs, and only S/R predictions. Input names and antibiotic strings are preserved exactly. Raw reports were inspected to verify the allele-specific mapping.


===== batch_011/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility prediction

## Inputs and scope

Analyzed all ten `data/genomes/ISO_*.fasta` assemblies as Escherichia coli, using the species supplied in the task. Antibiotic strings and ordering were read directly from `data/antibiotics.txt`. Every isolate has one prediction for each of the six antibiotics (60 rows). Only the supplied genome sequences and locally installed resistance references were used; no internet access, downloads, phenotype data, or database updates were used.

A Python FASTA check found 4,999,663–5,336,650 bases per assembly, 60–265 contigs, and zero N bases. These checks do not establish genome completeness or gene expression. Input SHA-256 checksums and assembly statistics are in `assembly_qc.tsv`.

## Software and database

Executable discovery used `command -v` and inspection of the installed AMR conda environment. AMRFinderPlus was available; ABRicate, RGI, ResFinder, PointFinder, minimap2, and samtools were not found on PATH.

Versions were checked before analysis using `amrfinder --version`, `amrfinder --database_version`, `blastn -version`, `blastp -version`, `blastx -version`, `tblastn -version`, `hmmsearch -h`, and `python --version`:

- NCBI AMRFinderPlus **4.2.7**, installed in `/Users/applemacbookpro/miniforge3/envs/amr/bin/`.
- Local NCBI AMRFinderPlus database **2026-10-29.1**, explicitly selected at `/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`.
- NCBI BLAST+ **2.17.0+** (reported package build August 22, 2026). The nucleotide-only AMRFinder analysis invoked tblastn and blastn, as recorded in its logs.
- HMMER **3.4** (August 2023) was available and version checked, but no protein/HMM search was requested in this nucleotide-only analysis.
- Python **3.13.13**, standard library only, for orchestration, FASTA statistics, report interpretation, checksums, and output validation.

The database supplies acquired-gene protein references (`AMRProt.fa`), taxon-specific mutation references and curated variants (`AMRProt-mutation.tsv`, `AMR_DNA-Escherichia.fa`, `AMR_DNA-Escherichia.tsv`), and gene-family hierarchy/thresholds (`fam.tsv`). Database metadata were inspected locally. The `Escherichia` taxon was confirmed using `amrfinder --list_organisms`. Checksums of the principal reference files are retained in `database_checksums.tsv`.

## Search commands and parameters

For each isolate, the exact command pattern was:

```sh
amrfinder -n data/genomes/ISO_XXX.fasta \
  -O Escherichia \
  -d /Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1 \
  --threads 2 --name ISO_XXX \
  --mutation_all output/amrfinder/ISO_XXX.mutations.tsv \
  -o output/amrfinder/ISO_XXX.tsv
```

Up to three isolates ran concurrently. Nucleotide-only translated searches detected acquired genes and protein resistance mutations; taxon-specific nucleotide searches checked supported DNA mutations. Defaults were retained: genetic code 11, minimum reference coverage 0.5, identity setting -1 (curated thresholds where supplied, otherwise 0.9). No `--plus`, `--report_common`, custom BLAST arguments, annotation, or external gene prediction was used. All ten commands exited with code 0. Logs, primary reports, and all-mutation reports are in `amrfinder/`.

For phenotype mapping, acquired genes had to have Type AMR, Subtype AMR, at least 90% reference coverage, and neither PARTIAL nor INTERNAL_STOP in the method. AMRFinder's curated identity requirements still applied. Thus the partial TEM hit in ISO_108 was excluded; its full-length CTX-M-55 and NDM-5 independently support its beta-lactam calls. Reported curated POINT hits were considered separately. WILDTYPE and UNKNOWN entries in the all-mutation reports were not treated as resistance determinants. Common quinolone target positions were reviewed in those reports to distinguish absence of reported mutations from the detected variants.

## Genotype-to-call rules

These are conservative, deterministic genome-based predictions, not measured MICs or formal breakpoint classifications. No breakpoint standard or dose regimen was supplied. `R` denotes a strong drug-relevant resistance genotype; `S` denotes no qualifying resistance determinant found under these searches and rules; `NA` denotes a detected relevant determinant whose isolated effect does not establish S/R. A strong R genotype takes precedence over uncertain modifiers. The executable implementation is `call_predictions.py`.

| Antibiotic | R rule and interpretation |
| --- | --- |
| ampicillin | Qualifying acquired beta-lactamase. Observed drivers: TEM-1, OXA-1, CTX-M-15/55, CMY-2, NDM-5. A lone regulatory mutation such as MarR S3N receives NA. |
| cefotaxime | CTX-M ESBL, plasmid AmpC, or broad-spectrum carbapenemase. Observed: CTX-M-15/55, CMY-2, NDM-5. TEM-1 and OXA-1 alone do not establish cefotaxime resistance. Isolated ampC regulatory or FtsI point changes would receive NA. |
| ciprofloxacin | A GyrA position 83/87 resistance substitution plus either a second such GyrA substitution or a ParC position 80/84 resistance substitution. Observed resistant combinations include GyrA S83L + D87N + ParC S80I, and GyrA S83L + ParC S80R. Isolated qnr, AAC(6')-Ib-cr, efflux-regulatory, or single target mutations receive NA because MIC shifts may not cross a clinical resistance breakpoint. Other reported quinolone mutations are modifiers, not independent high-confidence R calls. |
| gentamicin | Acquired determinant whose AMRFinder subclass explicitly includes GENTAMICIN, or a broad aminoglycoside resistance 16S rRNA methylase (rmt/armA). Observed: AAC(3)-IId, AAC(3)-IVa, RmtB1. AadA, APH(3'')-Ib, APH(6)-Id, and AAC(6')-Ib-cr do not independently establish gentamicin resistance. |
| meropenem | Acquired carbapenemase. Observed: NDM-5. ESBL or AmpC alone is insufficient. An isolated MrdA resistance mutation would receive NA; in ISO_108, NDM-5 already supports R. |
| trimethoprim/sulfamethoxazole | Both a qualifying dfr gene and a sul gene, supporting resistance to both components. Observed dfrA1/12/14/17 and sul1/2. A determinant affecting only one component would receive NA. |

The code additionally recognizes CMY/DHA/FOX/MOX/ACC AmpC families and NDM/KPC/VIM/IMP/OXA-48-like carbapenemases; only the observed families above affect this dataset. The rules are scoped to these inputs rather than a comprehensive clinical prediction model for every possible allele.

The four NA entries are ISO_103 ciprofloxacin (QnrS1 alone), ISO_105 ampicillin and ciprofloxacin (MarR S3N alone), and ISO_106 ciprofloxacin (ParE D475E alone). These are explicitly uncertain calls, rather than automatically equating every database resistance association with clinical resistance.

S calls use the evidence text `no determinant found`. Absence of a detected determinant does not prove phenotypic susceptibility: expression, porin loss, regulatory mechanisms, novel alleles, assembly defects, and unmodeled combinations can alter phenotype. In particular, ESBL/AmpC plus permeability changes can affect carbapenem susceptibility. No systematic porin-loss or promoter-expression model was applied.

## Output and validation

`predictions.tsv` contains exactly the requested four columns with tabs and a header. Validation checks all 60 unique isolate/antibiotic pairs, exact antibiotic strings, allowed prediction values, nonempty evidence, and successful AMRFinder completion. Final counts: 27 R, 29 S, 4 NA. Run `python output/call_predictions.py` from the workspace to regenerate predictions from the retained reports.


===== batch_012/workspace/output/methods.md =====
# Genome-based antimicrobial susceptibility predictions

## Inputs and local resources

Analyzed all eight supplied Escherichia coli assemblies, ISO_111 through ISO_118, and all six exact antibiotic names in data/antibiotics.txt (48 isolate–antibiotic pairs). No phenotype data, internet access, downloads, database updates, or remote services were used.

Tool discovery inspected PATH and the installed amr environment bin/share directories. The available resistance caller was NCBI AMRFinderPlus. Versions were checked before screening with `amrfinder --version`, `amrfinder --database_version`, `blastn -version`, and `blastx -version`. AMRFinderPlus was 4.2.7; BLAST+ was 2.17.0+ (build Aug 22 2026). `tblastn -version` also confirmed 2.17.0+. Bundled report/mutation components were subsequently checked with `amr_report -version` and `dna_mutation -version`, both 4.2.7 (their double-dash version options were unsupported). Python 3.9.6, checked with `python3 --version`, was used for FASTA QC, report inspection, TSV generation and validation. No separate annotation or gene-prediction tool was used.

The local NCBI AMRFinderPlus database was version **2026-10-29.1**, resolved by AMRFinder to:

`/Users/applemacbookpro/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1`

Resources used by the nucleotide-mode workflow include AMR protein references and family hierarchy/curated thresholds, susceptible/suppression references, protein mutation definitions, and Escherichia nucleotide mutation references/definitions. Local `fam.tsv`, `AMRProt-mutation.tsv`, and `AMR_DNA-Escherichia.tsv` were inspected to understand annotations. No other resistance database was used. `amrfinder --list_organisms` confirmed the supported `Escherichia` option.

## Screening procedure

For each isolate ID, ran the following command, saving stdout/stderr to output/amrfinder/ID.log:

```sh
amrfinder -n data/genomes/ID.fasta -O Escherichia --threads 4 \
  --mutation_all output/amrfinder/ID.mutations.tsv \
  -o output/amrfinder/ID.tsv
```

All eight commands completed successfully. This runs translated nucleotide resistance-gene searches and organism-specific protein/DNA mutation searches (logs report tblastn and blastn). No HMM/protein-input annotation workflow was invoked. Defaults were retained: genetic code 11; minimum reference coverage 0.5; minimum identity -1, meaning curated thresholds where available and 0.9 otherwise. No `--plus`, `--report_common`, or threshold overrides were supplied. The regular reports contain curated resistance hits; the mutation_all tables additionally contain wild-type and unknown variants, which were not automatically treated as resistance.

FASTA QC counted contigs, sequence bases and non-ACGT bases (output/assembly_qc.json). Assemblies ranged from 4,676,468 to 5,469,751 bases and 74 to 257 contigs; none contained ambiguous bases. This establishes basic input plausibility, not assembly completeness. Reports and logs are retained in output/amrfinder/; output/make_predictions.py records the exact final mapping.

## Translation to predictions

These are qualitative, rule-based genotype predictions, not measured MICs. There was no supplied breakpoint standard, dose or phenotype calibration. S means no sufficient genomic mechanism for resistance to that particular drug was identified under these rules; it is not proof of phenotypic susceptibility. R requires an appropriate substrate-specific determinant or coherent combination. NA is used for a detected but inconclusive mechanism that prevents a defensible binary call.

- **Ampicillin:** intact CTX-M-15/27, TEM-1, CMY-42, OXA-1 or NDM-5 supports R. ISO_115 has only a partial TEM-family hit (154/286 aa, 53.85% coverage, 100% identity; PARTIALX) and marR_S3N. Its TEM hit is internal to a 1,197-base contig (positions 636–1097), rather than a clearly complete functional gene. Ampicillin is NA for this isolate because functionality and the regulator mutation's breakpoint effect are uncertain.
- **Cefotaxime:** CTX-M-15/27, CMY-42 or NDM-5 supports R. TEM-1 and OXA-1 alone were not treated as cefotaxime resistance. FtsI insertion I336IKYRI was retained as supporting context rather than a sole cefotaxime rule.
- **Ciprofloxacin:** the combination gyrA_S83L + gyrA_D87N with parC_S80I supports R in ISO_111, ISO_116 and ISO_118. Additional parC/parE changes and aac(6')-Ib-cr5 are supporting evidence, not sole high-level resistance rules. ISO_115 has marR_S3N without this target-mutation combination; efflux regulator changes can have context-dependent effects, so this call is NA rather than assuming that a generic QUINOLONE annotation establishes clinical ciprofloxacin resistance.
- **Gentamicin:** aac(3)-IIe or rmtB1 supports R. aph(6)-Id, aph(3'')-Ib and aadA genes target streptomycin; aph(3')-Ia targets kanamycin. They do not independently justify gentamicin R. aac(6')-Ib-cr5 was likewise not used as a gentamicin determinant.
- **Meropenem:** NDM-5 supports R. ISO_116 is also predicted R from the combination of a curated OmpF frameshift/early termination (ompF_Y253EfsTer3), carbapenem-associated mrdA_A543V, and CMY-42/CTX-M-15 beta-lactamases. This non-carbapenemase inference has greater phenotype uncertainty than the NDM call: porin, target, enzyme expression and breakpoint effects are not measured. ESBL/AmpC alone was not sufficient for meropenem R.
- **Trimethoprim/sulfamethoxazole:** acquired dfrA plus sul genes supports R: dfrA5+sul2 in ISO_115, dfrA17+sul1/sul2 in ISO_116, and dfrA12/dfrA17+sul1 in ISO_118. Sul2 alone in ISO_117 was not sufficient to infer combination resistance and was assigned S with explicit evidence that no trimethoprim determinant was found. This combination rule can miss resistance caused by an unrecognized trimethoprim mechanism.

Calls with no drug-relevant determinant use S and evidence `no determinant found`. Genes or mutations for unrequested drugs (e.g. fosfomycin, nitrofurantoin, tetracyclines, macrolides and cefiderocol) were not transferred to unrelated antibiotics. Intrinsic basal beta-lactamase/efflux activity and unknown variants were not assumed to confer resistance. Fragmented assemblies, missing genes, expression changes, uncurated mechanisms and incomplete knowledge of mutation effects remain limitations.

## Output validation

output/predictions.tsv has exactly the four requested tab-separated columns, 48 unique isolate–antibiotic rows, the exact supplied antibiotic names, and only S/R/NA predictions. Counts: 29 S, 17 R, 2 NA. All eight raw reports have successful completion logs. The generation script checks row count, pair uniqueness and allowed prediction labels.
