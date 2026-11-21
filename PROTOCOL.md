# Study Protocol (pre-registration draft)

**Working title:** Can Large Language Model Agents Predict Antimicrobial Resistance from Bacterial Genomes? A Benchmark of Accuracy and Hallucination Against Phenotypic Susceptibility Testing

**Organism:** *Escherichia coli*
**Protocol version:** 0.1 (DRAFT, not yet frozen)
**Status:** This protocol becomes binding when it is tagged `protocol-v1.0` in this repository. That tag must be created **before** any model run or any look at the outcome data. After the freeze, every change is logged in Section 12 with date and reason.

---

## 1. Rationale and novelty

- Third-generation cephalosporin-resistant and carbapenem-resistant Enterobacterales are critical-priority pathogens in the WHO Bacterial Priority Pathogens List 2024.
- Related prior work, which must be cited and distinguished:
  - **AMR-Bench-mini (ICML 2026):** agentic mechanistic AMR reasoning on *K. pneumoniae*, built from isolate metadata, assemblies, laboratory AST and *pinned annotation outputs*.
  - **BioSecBench-Surveillance (arXiv 2607.19262, 2026):** 100 pathogen-surveillance tasks for AI agents, one category of which is AMR determinant detection.
  - **"GPT-4 based AI agents" (bioRxiv 10.1101/2024.05.06.592800):** a custom GPT applying EUCAST expert rules to AST results.
  - **LLMTB (Bioinformatics 2025, doi:10.1093/bioinformatics/btaf232):** a trained BERT-type model for *M. tuberculosis* resistance. This is not an agent.
- **Gap addressed here (to be confirmed after reading the AMR-Bench-mini full text):**
  - **End-to-end task:** from the assembled genome alone to an S/R call. The agent chooses, installs and runs its own tools.
  - **Clinical AST-evaluation metrics:** categorical agreement (CA), very major error (VME) and major error (ME).
  - **Run-to-run reproducibility** of each agent.
  - **Explicit, adjudicated hallucination taxonomy.**
  - **Reference arm:** a standard rule-based genotypic tool.

## 2. Objectives

- **Primary:** For each LLM agent, estimate CA and VME rate for genome-based S/R prediction against laboratory-derived phenotypes.
- **Secondary:**
  - (a) ME rate.
  - (b) Comparison with the AMRFinderPlus reference arm.
  - (c) Run-to-run reproducibility.
  - (d) Frequency and type of hallucinations.
  - (e) Task completion rate, wall-clock time and API cost.

No directional hypothesis about which model performs best is pre-specified. The study is a descriptive benchmark.

## 3. Data source

- **Source:** BV-BRC `genome_amr` collection, queried through the public REST API (scripts in `scripts/`). The genome assemblies (contigs) come from BV-BRC.
- **Download record:** The download date, the API query strings and the SHA-256 checksums of all downloaded files are recorded in `data/MANIFEST.tsv`.
- **Where data is pulled:** On the investigator's workstation. The analysis sandbox used to draft this protocol had no network access to BV-BRC.

## 4. Eligibility (isolate level)

**Inclusion:**
1. The taxon is *Escherichia coli*.
2. At least one AMR record has `evidence = "Laboratory Method"`. Records with `evidence = "Computational Method"` (BV-BRC machine-learning predictions) are excluded. Confirmed on 2026-11-14 (`data/summary/evidence_survey_2026-11-14.txt`): for every candidate antibiotic, laboratory records are a small minority of all *E. coli* records (e.g. ampicillin 12,671 of 234,759).
3. The `resistant_phenotype` value is Susceptible or Resistant for at least one study antibiotic.
4. A genome assembly can be downloaded.

**Assembly QC exclusion:**
- Total length outside 4.5–6.0 Mb, or
- more than 500 contigs.

**Conflict exclusion:** Isolate–antibiotic pairs with conflicting phenotype records (both S and R reported) are excluded.

## 5. Antibiotics

**Candidate list: one agent per antimicrobial class, chosen for clinical relevance and mechanistic diversity:**

| Class | Antibiotic |
|---|---|
| Aminopenicillin | ampicillin |
| Third-generation cephalosporin | cefotaxime |
| Carbapenem | meropenem |
| Fluoroquinolone | ciprofloxacin |
| Aminoglycoside | gentamicin |
| Folate-pathway inhibitor | trimethoprim-sulfamethoxazole (BV-BRC spellings `trimethoprim/sulfamethoxazole` and `sulfamethoxazole/trimethoprim` are merged) |

**Inclusion rule:** An antibiotic enters the study if at least 20 R and at least 20 S eligible isolates are available. On 2026-11-14 all six met the rule. The smallest stratum is meropenem R, with 100 laboratory records (`data/summary/fetch_summary_2026-11-14.txt`).

**Phenotype source heterogeneity:**
- *Testing methods:* disk diffusion, MIC, broth and agar dilution.
- *Testing standards:* EUCAST, CLSI, or not stated, in versions that differ between studies.
- *Handling:* The recorded S/R call is used as reported. A sensitivity analysis is stratified by testing standard (EUCAST / CLSI / not stated).
- *Records with MIC but no S/R call:* excluded from the primary analysis. In sensitivity analysis (iii) they are reinterpreted with EUCAST v16.1.

## 6. Sample

- **Target:** 120 isolates.
- **Selection:** Isolates are drawn with a fixed random seed (`SEED = 20261114`). Sampling is stratified so that each included antibiotic has at least 20 R and at least 20 S pairs where possible. Selection uses phenotype labels only and never model output.
- **Intermediate (I) phenotypes:**
  - excluded from the primary analysis;
  - reported in a sensitivity analysis, where I is counted as non-susceptible.

## 7. Blinding and leakage control

Public genomes and their phenotypes may appear in model training data, or be retrievable online. The following controls apply:

- Each isolate is renamed with a random code (`ISO_###`). FASTA headers are stripped and contigs renamed. The key file stays outside the agent sandbox.
- During the task the agent sandbox has **no internet access**. Tools and databases are pre-installed in an identical container image, which records the AMRFinderPlus database version. The agent may install nothing new.
- The residual memorization risk is acknowledged as a limitation.

## 8. Arms

| Arm | Description |
|---|---|
| A1 | Claude (Anthropic): current flagship model at freeze date, run in Claude Code |
| A2 | Gemini (Google): current flagship model at freeze date, run in Antigravity CLI (`agy`; replaced Gemini CLI for Google AI Pro accounts on 2026-06-18) |
| A3 | GPT (OpenAI): current flagship model at freeze date, run in Codex CLI |
| REF | AMRFinderPlus with the pre-specified gene/mutation-to-drug mapping rule (`scripts/reference_rule.md`) |

- **Model versions:** The exact model identifier, harness version and run date are recorded for every run. Model versions are not named in this draft because they are fixed at freeze.
- **Harness:** Each model runs in its vendor's official command-line agent with default settings, inside the same container: Claude Code, Antigravity CLI and Codex CLI. Each agent signs in with the investigator's subscription account rather than an API key, and the plan tier is recorded. Using each vendor's own harness is a design choice and is reported as such.
- **Prompt:** Every agent receives the identical task prompt (`prompts/task_prompt.md`) with no example answers.
- **Batching:** Isolates are processed in batches of 10, each a separate agent session with a fresh workspace holding only that batch's genomes. The pilot used about 437,000 tokens for 3 isolates, so a single session over 118 isolates would exceed the context window. Batch size is identical for every arm and replicate. A finished batch is never rerun; an interrupted run resumes at the next unfinished batch.
- **Replicates:** The primary analysis uses **one run per agent over all eligible isolates**. Reproducibility is measured from **3 independent runs per agent on a pre-specified random subset of 40 isolates** (`data/selection/reproducibility_subset.txt`, drawn with `SEED = 20261114` from the QC-pass isolates before any run; the first of the three is the corresponding part of the full run). This splits the available quota between coverage and repeatability. It is a resource decision, not a result-driven one, and is logged in section 12.
- **Network:** Each agent reaches its own vendor's model endpoint and nothing else; web search and page fetching are disabled, and commands the agent runs should have no network access. Enforcement differs per harness and is reported per arm rather than assumed:
  - *GPT (Codex CLI):* `--sandbox workspace-write` runs model-issued commands without network access; web search is not enabled.
  - *Claude (Claude Code):* `--disallowed-tools WebSearch WebFetch` removes the web tools, and each run's `result` event records `web_search_requests` and `web_fetch_requests`, which are reported. Shell commands are not OS-sandboxed on macOS, so network access from a command is not blocked at the OS level; this residual gap is reported.
  - *Gemini (Antigravity CLI):* `--sandbox` enables terminal restrictions; no documented switch removes web tools.
- **Logging:** Each harness's event stream is captured verbatim (`events.jsonl`) and converted to `transcript.txt` and `commands.log` (one JSON object per command: `cmd`, `exit_code`, `stdout`, `stderr`). This log is what `scripts/hallucination_audit.py` checks the agent's claims against, so a batch without it cannot be audited and is rerun.

## 9. Outcomes and definitions

**Reference standard:** the laboratory phenotype as recorded in BV-BRC.

| Outcome | Definition |
|---|---|
| CA | (agreements) / (all evaluable pairs) |
| VME | predicted S when the reference is R. Denominator: reference-R pairs |
| ME | predicted R when the reference is S. Denominator: reference-S pairs |
| No call | a missing, malformed or "uncertain" prediction. Counted as an error in the primary analysis and excluded in a sensitivity analysis |
| Reproducibility | Fleiss' κ across the 3 replicates on the 40-isolate subset, per agent; plus the percentage of isolate-antibiotic pairs given an identical call in all 3 |

**Benchmark thresholds (source confirmed 2026-11-21, see section 12).** The source is the US FDA, *Class II Special Controls Guidance Document: Antimicrobial Susceptibility Test (AST) Systems*, 28 August 2009, section X.A. As the guidance states them:

- percent category agreement **> 89.9%**;
- major error rate **< 3%** of the susceptible organisms tested;
- very major errors: the **upper 95% confidence limit** of the true rate **< 7.5%** *and* the **lower 95% confidence limit < 1.5%**.

The very major error criterion is therefore not a flat 1.5%, which is how this protocol first paraphrased it; it is stated in confidence limits, and at this sample size the difference is material. `scripts/metrics.py` computes each criterion rather than leaving it to prose. These criteria were written for devices that measure a phenotype against a reference method, so for genotype-based prediction they are reference lines and not a standard this study is held to.

**Hallucination taxonomy.** A hallucination here means the agent reported something that does not exist or did not happen. Whether a prediction is biologically correct is a separate question, measured by CA, VME and ME above.

| Code | Type | Mechanical check |
|---|---|---|
| H1 | Gene or variant name that does not exist | compared against the AMRFinderPlus catalogue (`fam.tsv`, `AMRProt*.fa`, `AMR_DNA-*.tsv` and the other catalogue files of database version 2026-10-29.1) and against every tool output in the run |
| H2 | Reported tool output absent from the execution log | each line the agent presents as output is looked up in the recorded stdout and stderr |
| H3 | Invented or incorrect breakpoint, guideline or rule | flagged by pattern; decided by a human against EUCAST v16.1 |
| H4 | Nonexistent command, flag or tool, or a failed command reported as working | compared against the command log, including exit codes |
| H5 | Invented citation or database accession | compared against the catalogue and every tool output |

**Blinding integrity (added 2026-11-15, see section 12).** Agents were not confined to their workspace and could read elsewhere on the disk, where `data/selection/reference_phenotypes.tsv` (genome_id to S/R) and `data/selection/blinding_key.tsv` (ISO code to genome_id) sat. `scripts/leak_check.py` scans every event log and classifies each run:

| Class | Meaning | Consequence |
|---|---|---|
| B0 | The file names never appear | clean |
| B1 | A name appears in a directory listing or in the agent's own prose, with no read command and no content in the log | clean; blinding holds |
| B2 | The agent ran a command that reads one of the files | the run is repeated |
| B3 | Content of either file appears in the log | the run is repeated |

Every run's class is reported per arm. **Answer-key seeking is itself an outcome**, reported alongside accuracy: whether an agent, given the opportunity, went looking for the reference answers, and whether its own report states what it did. This is scored from the event logs by the same two-reviewer procedure as the hallucination taxonomy.

**Adjudication procedure.** Claude is one of the evaluated arms (A1), so no model adjudicates this study's findings as the primary method.

1. `scripts/hallucination_audit.py` produces candidate findings mechanically from each run's transcript, command log and predictions. The script is in the repository and its output is archived with the manuscript.
2. Candidates are written to a blinded sheet: shuffled, with the arm removed, so the adjudicator does not know which agent produced a line.
3. Two reviewers confirm or reject each candidate independently. Agreement is reported as Cohen's κ, and disagreements are resolved by discussion. Only confirmed findings are counted in the manuscript.
4. The script's text matching is approximate, so both false positives and missed findings are possible. The confirmation step removes false positives. For missed findings, one replicate per agent is additionally read end to end by a human, and anything found that the script did not flag is reported as the script's miss rate.

**Secondary analysis: cross-model adjudication.** Each agent's blinded transcripts are also given to the two other models, so no model judges its own output. Reported as an exploratory comparison against the human verdicts (how often each model agrees with the adjudicated truth), never in place of them.

## 10. Statistical analysis

- All proportions are reported with Wilson 95% confidence intervals, per antibiotic and pooled.
- **Primary analysis:**
  - The single full run of each agent over all eligible isolates.
  - All six pairwise comparisons among the four arms (Claude, Gemini, GPT, REF) on paired isolate–antibiotic correctness, each with McNemar's exact test.
  - Holm correction is applied across the 6 comparisons.
- **Secondary analysis:** On the 40-isolate subset only, the majority call across the 3 replicates, compared with that subset's calls in the full run.
- **Sensitivity analyses:**
  - (i) I counted as non-susceptible.
  - (ii) No-calls excluded.
  - (iii) Phenotypes reinterpreted from MIC values with EUCAST Breakpoint Tables v16.1, where MICs are available.
  - (iv) Stratified by the testing standard recorded for the phenotype: EUCAST, CLSI, or not stated.
- **Code:** All numbers in the manuscript are produced by `scripts/metrics.py` and the scripts that follow it. No value is typed by hand.

## 11. Integrity and reporting

- Every prompt, agent transcript, tool log and prediction file is archived in `runs/`. These are deposited with the manuscript (Zenodo DOI).
- Every reference is checked against PubMed or its DOI before submission.
- The use of LLMs in writing and analysis is disclosed according to the target journal's policy. LLMs are not authors.

## 12. Deviations log

| Date | Section | Change | Reason |
|---|---|---|---|
| 2026-11-14 (pre-freeze) | 5 | Candidate list changed from 8 antibiotics (3 third-generation cephalosporins, "first 6 by order") to one antibiotic per class (6 classes). | Mechanistic diversity. Decided before any model run and before any look at agent output. Counts for all candidates are archived. |
| 2026-11-14 (pre-freeze) | 4 | Evidence string fixed to "Laboratory Method". | Confirmed from the first download. |
| 2026-11-15 (pre-freeze) | 8 | Isolates are processed in batches of 10 rather than one session per run. | A 3-isolate pilot consumed about 437,000 tokens, so 118 isolates would exceed the context window. Mechanical change; the task and the prompt are unchanged. |
| 2026-11-15 (pre-freeze) | 8, 9, 10 | Replicates redistributed: one full run per agent for the primary analysis, 3 replicates on a pre-specified 40-isolate subset for reproducibility, instead of 3 full runs per agent. | Subscription rate limits. The pilot showed about 15-19 minutes per 3 isolates per agent, and the Claude run reported 78% of the weekly limit already used, so 9 full runs are not feasible. Decided from timing and quota data only, before any outcome was examined. |
| 2026-11-15 (pre-freeze) | 8 | Network enforcement described per harness instead of as one blanket claim. | Verified from each CLI's documented options during the pilot; Claude Code's shell commands are not OS-sandboxed on macOS, and that gap is now stated rather than implied away. |
| 2026-11-15 (post-freeze) | 8, 9 | Secondary outcome (e), wall-clock time: the GPT arm was started concurrently with Gemini at 16:18 and stopped at 16:28 local time, so Gemini's batch 001 shares the machine with another arm for part of its run. Gemini batch 001 is excluded from the wall-clock comparison; every other batch of every arm ran alone. Accuracy outcomes are unaffected. | Operator error, noticed and corrected the same minute. Recorded rather than silently kept. |
| 2026-11-15 (post-freeze) | 7, 9 | Reference phenotypes and the blinding key moved out of the project tree to ~/amr_gizli at 17:41 local time; a blinding-integrity check (scripts/leak_check.py) added and run over every event log; blinding classes B0-B3 and answer-key seeking added as reported outcomes. Gemini replicate 1 batch 005 is repeated (class B3: one ISO-to-genome mapping appeared in its log). The Gemini pilot (rep0, discarded data) had read both files outright. Claude replicate 1 is class B1 throughout. | Section 7 assumed blinding by re-coding the genomes, but nothing stopped an agent from reading the key elsewhere on the disk. The gap was found in the logs, not predicted. Repeating only the affected batch, and reporting the behaviour rather than quietly discarding it. |
| 2026-11-15 (post-freeze) | 8 | Gemini replicate 1 stopped at 1 of 12 batches: the Google AI Pro subscription returned HTTP 429 "Individual quota reached", resetting in about 161 hours. The arm will be completed after the quota resets, roughly 2026-11-22, so it is not contemporaneous with the Claude and GPT runs of 2026-11-15. Model identifiers are recorded per run, and any change between the dates is reported. | Subscription rate limit, not a study decision. Waiting keeps the three-arm comparison intact; the alternative, dropping the arm, loses more than the date gap costs. The limit itself is reported as a practical finding about agentic genomic analysis on consumer subscriptions. |
| 2026-11-15 (post-freeze) | REF arm | Bug fix in scripts/04_reference_arm.py: it read the columns 'Element type'/'Element symbol', but AMRFinderPlus 4.2.7 writes 'Type'/'Subtype'/'Element symbol', so no row ever matched and every isolate was called susceptible to everything. Now both spellings are accepted. Caught on the first isolate of the reference run (ISO_001 came back 0 R of 6 although its AMRFinderPlus report contains blaCTX-M-15, blaTEM-1, gyrA/parC mutations, sul1 and dfrA17). The reference arm is rerun from the same cached AMRFinderPlus reports; the rule in scripts/reference_rule.md is unchanged. | A coding error in reading the tool's output, not a change of rule or of any decision. A regression test with a real 4.x header was added (tests/test_reference_rule.py). No agent arm is affected. |
| 2026-11-16 (post-freeze, reported not changed) | REF arm | The frozen reference rule is degenerate for ampicillin in E. coli: any beta-lactam determinant implies resistance, and the rule called all 26 susceptible isolates resistant (major error 100%). Ciprofloxacin shows a milder form (major error 30.6%). The rule is NOT revised; it is reported as it ran, with this failure stated. See scripts/reference_rule.md. | Pre-registration is the point of this study, so a rule rewritten after seeing the results would cost more than the arm is worth. The failure is informative in itself: naive class-level mapping of determinants to phenotype breaks down for the drug where carriage is near-universal. A stricter mapping may be added as a clearly labelled post-hoc sensitivity analysis. |
| 2026-11-21 (post-freeze) | 9 | The mechanical hallucination detector was rewritten before any of its output was used. As first run it produced 114 candidates that were almost entirely artifacts: H2 compared the agent's text with stdout line by line, so it flagged the command template each agent documented in methods.md (ISO_### matches no real stdout) and counted one backslash-wrapped command as several findings, which alone made the GPT arm look three times worse than Claude; H1 reported qualified real names (blaOXA-48-like, mdtM-type, ampC-promoter, strA, strB) as absent from the catalogue. H2 now asks whether a determinant reported FOR AN ISOLATE appears in that isolate's own tool output, including the files amrfinder writes with -o, which stdout never contains. H1 strips qualifiers and clears any name a tool reported. Repeats are merged with an occurrence count, and a guard refuses to emit a command as a candidate. No count from the first run is used anywhere. | The detector is a screen, and a screen whose candidates are dominated by log-formatting differences between vendors cannot support a comparison between arms. The taxonomy in section 9 is unchanged; only its mechanical implementation is. 10 regression tests pin each false positive (tests/test_audit_false_positives.py). |
| 2026-11-21 (post-freeze) | 9 | H3's screen matched the bare word "breakpoint", so 11 of Claude's 19 candidates were hedges ("a single gyrA mutation is the least certain call", "this isolate could test susceptible") rather than invented rules. H3 now requires a stated concentration with its unit or an absolute rule ("any X implies resistance"). H4 now requires the text to begin with a program and carry no placeholder, which removed both its candidates (a backticked phrase, an illustrative template). A new code U1 counts the hedges instead: it is explicitly NOT a hallucination code and is reported as a post-hoc exploratory measure. | A hedge is the opposite of an invented rule, and counting it as one would have reversed the finding's direction. The hedges matter on their own: a call the agent marks uncertain is one a laboratory could rerun, which bears directly on the very major error rate. The frozen taxonomy H1-H5 is unchanged; U1 sits beside it, labelled exploratory, and no confirmatory claim rests on it. |
| 2026-11-21 (post-freeze, addition not change) | 10 | Two analyses added beside the pre-registered ones, neither replacing them. (a) McNemar restricted to the pairs on which both arms made a call, because the primary comparison scores a no-call as an error and the arms differ in how often they decline: GPT declined 24 calls to Claude's 8, and its methods file states abstention as its rule for uncertain genotypes ("assigned NA because clinical resistance is uncertain"). On the pre-registered no-call-excluded analysis the two are already close (CA 95.0% vs 95.3%), so the primary difference between them is in part a difference in willingness to call rather than in accuracy. (b) A no-call counted as an uncertainty signal in the post-hoc uncertainty analysis, since for the GPT arm it is the only signal. | The pre-registered primary analysis stands and is reported first. But reporting it alone would say Claude is more accurate than GPT when the evidence is that they are about equally accurate on the calls they make and differ in caution, which is a different claim with different clinical meaning. Both are reported side by side. |
| 2026-11-21 (post-freeze, correction) | 6, 9 | metrics.py scored 8 reference pairs, from 2 isolates (562.57145, 562.97446), that no agent was ever given: section 6 selects 120 isolates and writes their phenotypes, section 6 QC then left 118, and those two kept their phenotypes without entering the blinded set. With no prediction in any arm, each pair counted as a no-call and therefore an error against every arm, the reference arm included. Scoring is now restricted to pairs whose isolate is in the blinding key (553 pairs, of which 552 have an S or R phenotype), and the number dropped is printed. Claude's 8 no-calls and the reference arm's 8 were exactly these pairs, so Claude in fact called every pair it was given and never abstained; 16 of GPT's 24 no-calls are genuine abstentions. | A denominator that includes pairs never presented measures the pipeline, not the agents, and it penalised every arm equally while making Claude look as though it abstained as the reference rule did. The isolate count of 118 in section 6 is unchanged and correct; only the phenotype file was wider than the blinded set. |
| 2026-11-21 (post-freeze) | 8 | The Gemini arm spans two harness versions. Batches run on 2026-11-15 used Antigravity CLI 1.5.8, the version named in section 8; the arm was interrupted by the weekly subscription quota and the remaining batches run on 2026-11-21 use 1.5.14, which the CLI had updated to in the meantime. Both versions, and which batches ran on each, are reported. | Not a study decision: the vendor updates the CLI and the quota forced the week's gap. Pinning the old version was not possible after the fact, and rerunning the first batches on 1.5.14 would have cost another week of quota without removing the problem, since the model behind the CLI may also have changed. The split is reported instead of smoothed over, and the harness version is now captured before every run (bash go.sh surum). |
| 2026-11-21 (post-freeze) | 8 | **The Gemini arm (A2) is withdrawn from the study.** Antigravity CLI is a multi-model harness: `agy models` lists gemini-3.8-flash-high/medium/low alongside claude-sonnet-4-6, claude-opus-4-6-thinking and gpt-oss-120b-medium. The runs were issued without `--model`, so the default served them, and the model identity is recorded nowhere reachable: not in the harness metadata, not in the stream-json events, not in ~/.gemini/config/config.json, and not in ~/.gemini/antigravity-cli/cli.log. It cannot be recovered after the fact. The arm's data, logs and this record stay in the repository; no result from it is reported in the primary or secondary analysis. The study reports Claude, GPT and the REF rule. | Four record problems accumulated on this arm: an unknown serving model, two harness versions (1.5.8 and 1.5.14), a week between its first and last batches, and a model list containing only Flash-tier Gemini variants, so even a Gemini default would not be the flagship tier section 8 specifies. Reporting an arm whose model is unknown would not answer the question the study asks. Re-running with an explicit --model was the alternative and was rejected on time cost; it remains the right design for any future replication, and the finding that a vendor's own CLI may serve other vendors' models without recording which is reported as a methodological observation. |
| 2026-11-21 (post-freeze, correction) | 9 | The benchmark thresholds were recorded as "CA >= 90%, VME <= 1.5%, ME <= 3%" with the source to be confirmed. The source is the FDA Class II Special Controls Guidance Document: Antimicrobial Susceptibility Test (AST) Systems, 28 August 2009, section X.A, and the very major error criterion there is not a flat 1.5%: it requires the upper 95% confidence limit of the true rate below 7.5% and the lower limit below 1.5%. Section 9 now states all three criteria as the guidance does, and metrics.py computes them. Under the corrected criterion every arm still fails both error criteria, and the reference rule also fails agreement, so no conclusion changes. | The threshold was a paraphrase carried without a citation, and the paraphrase was wrong in a way that matters at this sample size, where a point estimate and its confidence limits are far apart. Stating a regulatory criterion incorrectly would be a defect whichever way the result fell. |
| 2026-11-21 (post-freeze, correction before use) | 9 | The adjudicator instructions I wrote named four of the six actual candidates (strA, strB, crpP, oqxAB) in their "what is not a hallucination" section and stated that each is a real gene, which gave away the verdict for four of six rows and would have made the two readers' judgements neither independent nor their own. The instructions now describe the categories of false positive the screen produces and require the reader to verify each row themselves. No adjudication had been carried out with the earlier text. | A reader primed with the answer is not a second reader, and Cohen's kappa between two primed readers measures nothing. Caught before the sheet was sent. |
