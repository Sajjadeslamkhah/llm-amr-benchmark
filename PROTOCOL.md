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
2. At least one AMR record has `evidence` indicating a laboratory-derived phenotype. Computationally predicted phenotypes are excluded. The exact `evidence` string is confirmed on the first download and written here before the freeze.
3. The `resistant_phenotype` value is Susceptible or Resistant for at least one study antibiotic.
4. A genome assembly can be downloaded.

**Assembly QC exclusion:**
- Total length outside 4.5–6.0 Mb, or
- more than 500 contigs.

**Conflict exclusion:** Isolate–antibiotic pairs with conflicting phenotype records (both S and R reported) are excluded.

## 5. Antibiotics

**Candidate list, chosen for clinical relevance:**
- ampicillin
- cefotaxime
- ceftriaxone
- ceftazidime
- meropenem
- ciprofloxacin
- gentamicin
- trimethoprim-sulfamethoxazole

**Pre-specified inclusion rule:**
- An antibiotic enters the study if at least 20 R and at least 20 S eligible isolates are available.
- At most 6 antibiotics are kept. When more than 6 qualify, priority follows the order of the candidate list.
- The final list is fixed from counts alone, before any model run.

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
- **Harness:** Each model runs in its vendor's official command-line agent with default settings, inside the same container. Using each vendor's own harness is a design choice and is reported as such.
- **Prompt:** Every agent receives the identical task prompt (`prompts/task_prompt.md`) with no example answers.
- **Replicates:** 3 independent runs per agent, each from a fresh container.

## 9. Outcomes and definitions

**Reference standard:** the laboratory phenotype as recorded in BV-BRC.

| Outcome | Definition |
|---|---|
| CA | (agreements) / (all evaluable pairs) |
| VME | predicted S when the reference is R. Denominator: reference-R pairs |
| ME | predicted R when the reference is S. Denominator: reference-S pairs |
| No call | a missing, malformed or "uncertain" prediction. Counted as an error in the primary analysis and excluded in a sensitivity analysis |
| Reproducibility | Fleiss' κ across the 3 replicates, per agent |

**Benchmark thresholds:** Results are displayed against the commonly used AST-evaluation thresholds: CA ≥ 90%, VME ≤ 1.5%, ME ≤ 3%. The exact source for these thresholds is to be confirmed and cited before the freeze. They serve as reference lines, not as pass/fail hypotheses.

**Hallucination taxonomy**, adjudicated independently by two reviewers with disagreements resolved by discussion:

| Code | Type |
|---|---|
| H1 | Gene or variant name that does not exist in the AMRFinderPlus/CARD databases |
| H2 | Reported tool output that is absent from the execution log (fabricated execution) |
| H3 | Invented or incorrect breakpoint, guideline or rule |
| H4 | Nonexistent command, flag or tool |
| H5 | Invented citation or database accession |

## 10. Statistical analysis

- All proportions are reported with Wilson 95% confidence intervals, per antibiotic and pooled.
- **Primary analysis:**
  - Replicate 1 of each agent.
  - All six pairwise comparisons among the four arms (Claude, Gemini, GPT, REF) on paired isolate–antibiotic correctness, each with McNemar's exact test.
  - Holm correction is applied across the 6 comparisons.
- **Secondary analysis:** Majority vote across the 3 replicates.
- **Sensitivity analyses:**
  - (i) I counted as non-susceptible.
  - (ii) No-calls excluded.
  - (iii) Phenotypes reinterpreted from MIC values with EUCAST Breakpoint Tables v16.1, where MICs are available.
- **Code:** All numbers in the manuscript are produced by `scripts/metrics.py` and the scripts that follow it. No value is typed by hand.

## 11. Integrity and reporting

- Every prompt, agent transcript, tool log and prediction file is archived in `runs/`. These are deposited with the manuscript (Zenodo DOI).
- Every reference is checked against PubMed or its DOI before submission.
- The use of LLMs in writing and analysis is disclosed according to the target journal's policy. LLMs are not authors.

## 12. Deviations log

| Date | Section | Change | Reason |
|---|---|---|---|
| — | — | — | — |
