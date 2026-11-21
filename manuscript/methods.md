# Methods

> Draft. Every number here is produced by a script in `scripts/` and none is typed by
> hand. Places where the study is not yet finished are marked **[pending]** rather than
> filled with a plausible value. The frozen protocol is `PROTOCOL.md`; every change made
> after the freeze is listed in its section 12 with the date and the reason, and the
> substantive ones are stated in this section too.

## Study design

This is a pre-registered descriptive benchmark. The protocol, the task prompt, the
isolate-selection code, the reference-arm rule and the analysis code were written and
committed before any scored model run, and the freeze is recorded in `FREEZE.md` with a
SHA-256 checksum of each frozen file. No directional hypothesis about which agent would
perform best was specified. The unit of analysis is the isolate–antibiotic pair.

A limitation of the pre-registration should be stated plainly: the freeze is a commit
in a repository the investigator controls, which is weaker evidence of timing than a
third-party timestamp. **[pending: deposit the frozen package with OSF or Zenodo and
cite the DOI here.]**

## Reference standard and data source

Phenotypes and genome assemblies were taken from BV-BRC through its public REST API
(`scripts/01_fetch_amr.py`, `scripts/03_fetch_genomes.py`). Download dates, the exact
query strings and a SHA-256 checksum of every downloaded file are recorded in
`data/MANIFEST.tsv`.

Only records with `evidence = "Laboratory Method"` were used. BV-BRC also distributes
machine-learning predictions as `evidence = "Computational Method"`, and these are the
large majority of its *E. coli* AMR records: for ampicillin, 12,671 of 234,759 records
are laboratory-derived (`data/summary/evidence_survey_2026-11-14.txt`). Including them
would have compared one prediction against another.

The recorded susceptible/resistant call was used as reported. These calls come from
different testing methods (disk diffusion, MIC, broth and agar dilution) and from
different standards (EUCAST, CLSI, or none stated) in versions that differ between
submitting studies. This heterogeneity is a property of the reference standard, not of
the agents, and it bounds the accuracy any genotype-based method can reach here. A
sensitivity analysis stratified by recorded standard is pre-specified. **[pending]**

## Eligibility and sample

Isolates were eligible if the taxon was *Escherichia coli*, at least one laboratory AMR
record existed, and the phenotype for at least one study antibiotic was susceptible or
resistant. Assemblies were excluded if the total length fell outside 4.5–6.0 Mb or the
assembly exceeded 500 contigs. Isolate–antibiotic pairs with both an S and an R record
were excluded as conflicting.

Six antibiotics were studied, one per class: ampicillin, cefotaxime, meropenem,
ciprofloxacin, gentamicin and trimethoprim/sulfamethoxazole. An antibiotic entered the
study only if at least 20 resistant and 20 susceptible eligible isolates existed; all
six met this on 2026-11-14.

120 isolates were drawn with a fixed seed (`SEED = 20261114`, `scripts/02_select_isolates.py`),
stratified so that each antibiotic reached at least 20 resistant and 20 susceptible
pairs where possible. Selection used phenotype labels only and never model output. Two
isolates then failed assembly QC, leaving **118** isolates that entered the blinded set.

Because selection writes phenotypes for all 120 while QC is applied afterwards, the
phenotype file was wider than the blinded set: 8 pairs belonged to the two excluded
isolates and were never shown to any agent. Scoring is restricted to pairs whose isolate
is in the blinding key, giving **553 pairs**, of which **552** carry a susceptible or
resistant phenotype (238 resistant, 314 susceptible). The correction and its effect are
recorded in `PROTOCOL.md` section 12 under 2026-11-21. Intermediate phenotypes are
excluded from the primary analysis.

## Blinding and leakage control

Public genomes and their phenotypes may be present in model training data. Each isolate
was renamed with a random code (`ISO_###`), FASTA headers were stripped and contigs
renamed, and the key was kept outside the agent workspace. Residual memorisation remains
possible and is a limitation.

Blinding was weaker in practice than the protocol assumed, and this is reported rather
than corrected after the fact. The agents were not confined to their workspace and could
read elsewhere on the disk, where the phenotype table and the code-to-genome key were
stored. `scripts/leak_check.py` scans every event log and classifies each run as B0 (the
file names never appear), B1 (a name appears in a directory listing or in the agent's own
prose, with no read command and no content in the log), B2 (a command read one of the
files) or B3 (content of either file appears in the log). On 2026-11-15 the files were
moved outside the project tree.

No scored run read either file. The Claude arm is class B1 throughout: its own report
states that it saw the key files in the parent directory and did not open them, and the
log confirms no read command and no content. The GPT arm is class B0. One Gemini batch in
an earlier, discarded pilot had read both files outright, mapping blinded codes to
genomes and then to phenotypes; that pilot's data is not used, and one scored Gemini batch
in which a single code-to-genome line appeared was deleted and repeated. Whether an agent
goes looking for the answer key when it can is reported as an outcome in its own right.

## Arms

| Arm | Agent | Harness |
|---|---|---|
| A1 | Claude | Claude Code 2.1.325 |
| A3 | GPT | Codex CLI 0.169.0 |
| REF | AMRFinderPlus 4.2.7, database 2026-10-29.1 | pre-specified mapping rule |

A third agent arm (A2, Gemini in Antigravity CLI) was run and then withdrawn before any
of its results were analysed. Antigravity CLI turned out to be a multi-model harness:
`agy models` lists three Flash-tier Gemini variants alongside Claude and GPT-OSS models.
The runs were issued without `--model`, so whichever model was default served them, and
that identity is recorded nowhere retrievable — not in the harness metadata, the
stream-json events, the CLI configuration or the CLI log — and cannot be recovered
afterwards. Reporting an arm whose model is unknown would not answer the question this
study asks, so it is excluded. Its data and logs remain in the repository and the decision
is recorded in `PROTOCOL.md` section 12 with its date.

This is worth stating as a methodological observation for anyone benchmarking agent
command-line tools: a vendor's own CLI may serve other vendors' models, may expose only a
reduced tier of its own, and need not record which model answered. Pinning `--model`
explicitly, and capturing it before the run, is a requirement rather than a refinement.

Run dates, wall-clock duration per batch, exit codes and the invoked binary are recorded
for every batch and collected by `scripts/run_provenance.py`. The model identifier is
recorded only where the harness writes it into its event stream: the Claude arm ran
`claude-opus-5-5`, and for the GPT and Gemini arms neither the harness metadata nor the
event stream contains a model identifier, so the serving model version for those two arms
is not known and cannot be recovered after the fact. This is a limitation of the logging,
reported as such; the harness version, the invoked binary and the run date are known for
all three. Model identity is captured before each run from this point on
(`bash go.sh surum`). **[pending: plan tier per arm.]**

Each agent ran in its vendor's own command-line harness with default settings. This is a
design choice: it measures the agent as a user would meet it, not the underlying model in
isolation, and harness differences are therefore part of what is compared. Each agent
signed in with the investigator's subscription account rather than an API key.

Every agent received the identical task prompt (`prompts/task_prompt.md`) with no example
answers. Isolates were processed in batches of 10, each a separate session with a fresh
workspace containing only that batch's genomes; a pilot consumed about 437,000 tokens for
3 isolates, so one session over 118 isolates would have exceeded the context window.
Batch size was identical for every arm.

Network access was restricted differently by each harness, and is reported per arm rather
than assumed. For GPT, `--sandbox workspace-write` runs model-issued commands without
network access. For Claude, `--disallowed-tools WebSearch WebFetch` removes the web tools
and each run records its web-search and web-fetch counts, both of which were zero across
all 12 batches, but shell commands are not
OS-sandboxed on macOS, so network access from a command is not blocked at that level; this
residual gap is reported. For Gemini, `--sandbox` enables terminal restrictions and no
documented switch removes web tools.

### Reference arm

AMRFinderPlus was run on each assembly, and a pre-specified rule mapped the detected
elements to an S/R call per antibiotic (`scripts/reference_rule.md`). Only rows of element
type AMR were used. The rule and its vocabulary were verified against the database on
2026-11-14 and frozen before any run.

The rule is degenerate for ampicillin in *E. coli*: a beta-lactam determinant of any kind
implies resistance, and nearly every *E. coli* genome carries one, so the rule called all
26 phenotypically susceptible isolates resistant (major error 26/26). Ciprofloxacin shows
a milder form of the same thing. The rule was pre-registered and is reported as it ran; it
was not revised after the results were seen. Two consequences follow. First, this is a
property of class-level mapping and not of AMRFinderPlus, which reports determinants and
does not claim to predict a phenotype. Second, and therefore, no comparison in this study
supports a claim that the agents outperform AMRFinderPlus: the arm they are compared
against is this rule applied to AMRFinderPlus output, and every comparison is worded that
way. A stricter mapping may be reported as a clearly labelled post-hoc sensitivity
analysis. **[pending]**

## Outcomes

Against the laboratory phenotype: categorical agreement (CA, agreements over evaluable
pairs); very major error (VME, predicted S when the reference is R, over reference-R
pairs); major error (ME, predicted R when the reference is S, over reference-S pairs). A
missing, malformed or explicitly uncertain prediction is a no-call, counted as an error in
the primary analysis and excluded in a pre-specified sensitivity analysis.

Results are displayed against the criteria in the US FDA *Class II Special Controls
Guidance Document: Antimicrobial Susceptibility Test (AST) Systems* (28 August 2009,
section X.A): percent category agreement above 89.9%; a major error rate below 3% of the
susceptible organisms tested; and, for very major errors, an upper 95% confidence limit of
the true rate below 7.5% together with a lower limit below 1.5%. The very major error
criterion is stated in confidence limits rather than as a flat 1.5%, and at this sample
size the difference matters, so each criterion is computed by `scripts/metrics.py` rather
than asserted.

These criteria were written for devices that measure a phenotype against a reference
method. Genotype-based prediction is a different task with a different error structure, so
they serve here as reference lines and not as a standard this study is held to. They are
nonetheless the criteria a laboratory would apply before using such a result clinically,
which is why they are reported.

Reproducibility is Fleiss' κ across three replicates on a pre-specified random subset of
40 isolates, drawn with the same seed before any run, plus the proportion of pairs given
an identical call in all three. The first replicate is the corresponding part of the full
run and two further runs were made per arm (`scripts/tekrar.sh`), giving 168 scorable
pairs per arm. Replicates ran one after another rather than concurrently, since two agents
sharing four cores would make the wall-clock outcome incomparable, and the harness
identity was recorded before each run.

### Hallucination taxonomy

A hallucination here means the agent reported something that does not exist or did not
happen; whether a prediction is biologically correct is measured separately by CA, VME and
ME. The pre-registered codes are H1 (a gene or variant name that does not exist), H2
(reported tool output absent from the execution log), H3 (an invented or incorrect
breakpoint, guideline or rule), H4 (a nonexistent command or tool, or a failed command
reported as working) and H5 (an invented citation or accession).

`scripts/hallucination_audit.py` produces candidates mechanically from each run's
transcript, methods file, command log and predictions, and `scripts/events_to_audit.py`
normalises each harness's event stream into a common format beforehand. The screen is
deliberately broad, so most candidates are expected to be rejected on reading.

The mechanical implementation was rewritten on 2026-11-21, before any of its output was
used, because its first candidates were dominated by artifacts; the taxonomy itself is
unchanged. Three classes of artifact were removed, each now covered by a regression test:
a command template documented in the agent's methods file was read as fabricated output,
and because one harness wraps a command across continuation lines, one command counted as
several findings, which alone made that arm appear three times worse on the most serious
category; real determinants written under literature names or with qualifiers
(`blaOXA-48-like`, `strA`, `mdtM-type`) were reported as nonexistent genes; and a context
window that stopped at every full stop split a decimal breakpoint into two apparent claims.
H2 now asks whether a determinant reported for an isolate appears in that isolate's own
tool output, including the files AMRFinderPlus writes with `-o`, which never reach stdout;
the proportion of predictions for which this comparison was possible is reported, so a
zero cannot be read as a clean result when it means the check did not run. No count from
the first implementation is used anywhere.

### Adjudication

Claude is one of the evaluated arms, so no model adjudicates this study's findings as the
primary method. Candidates are shuffled into a single blinded sheet with the arm removed.
Two reviewers confirm or reject each one independently, with written instructions
(`docs/ADJUDICATION.md`) that state what does not count as a hallucination. Agreement is
reported as Cohen's κ, disagreements are resolved by discussion and the resolution
recorded, and only then is the key opened. Only confirmed findings are counted. To
estimate what the screen misses, one replicate per agent is additionally read end to end
by a human. A reading by the other models is reported, if at all, as an exploratory
comparison against the human verdicts. **[pending: adjudication not yet performed.]**

## Statistical analysis

Proportions are reported with Wilson 95% confidence intervals, per antibiotic and pooled.
The primary analysis uses one full run per agent. All pairwise comparisons among the arms
are made on paired isolate–antibiotic correctness with McNemar's exact test, with Holm
correction across the comparisons.

Two analyses were added beside the pre-registered ones on 2026-11-21, neither replacing
them. First, McNemar restricted to the pairs on which both arms made a call. The primary
comparison scores a no-call as an error, and the arms differ in how often they decline, so
without this restriction an arm that abstains more often appears less accurate when it may
simply be more cautious. Second, a no-call is treated as an uncertainty signal in an
exploratory analysis of whether an agent's own expressed doubt identifies the calls it got
wrong (`scripts/uncertainty.py`); that analysis asks the question only of the calls an
agent made, since under the primary scoring an abstention is an error by definition and
would otherwise make the measure circular. Both additions are labelled post-hoc wherever
they appear.

Pre-specified sensitivity analyses (`scripts/sensitivity.py`): intermediate phenotypes
counted as non-susceptible; no-calls excluded; phenotypes reinterpreted from MIC values
with EUCAST Breakpoint Tables v16.1 where MICs are available; and stratification by the
recorded testing standard. The first, second and fourth were carried out. Only one
intermediate phenotype exists among the scored pairs, so the first cannot be informative
and is reported for completeness. The fourth is reported with two checks printed beside
it, because the strata differ in resistant share and the standard-blind reference arm's
error rate also varies across them, so a difference between strata cannot be attributed
to the standard. **[pending: the third, which requires each of the six breakpoints to be
read off the current EUCAST table rather than entered from memory; 347 of 553 pairs carry
a usable MIC.]**

The recorded testing standard is normalised before stratification: BV-BRC writes it as
CLSI and clsi, EUCAST and eucast, and both names together in either order, which left one
stratum split four ways.

All numbers are produced by `scripts/metrics.py` and the scripts downstream of it.

## Deviations from the protocol

All deviations are logged in `PROTOCOL.md` section 12 with date and reason. The ones that
affect interpretation are stated where they arise above, and the material ones are: the
Gemini harness was changed from Gemini CLI to Antigravity CLI before any scored run,
because the former was retired for the account tier used; the Gemini arm was interrupted
by a weekly subscription quota and completed a week later, so it is not contemporaneous
with the other two arms; over that week the Antigravity CLI updated from 1.5.8 to 1.5.14,
so that arm spans two harness versions, and which batches ran on each is reported; two
batches were run concurrently on two occasions, so wall-clock time is not comparable for
those batches and they are excluded from the timing outcome; the blinding gap and the
reference-rule failure described above; and the scoring correction that removed the 8 pairs
never shown to any agent.
