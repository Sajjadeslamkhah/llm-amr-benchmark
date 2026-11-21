const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, PageOrientation, Footer, PageNumber,
} = require("docx");

const FONT = "Calibri";
const SZ = 22;        // 11 pt, in half-points
const LEAD = 300;     // ~1.25 line spacing, in twentieths of a point

// ---------- helpers ----------

// Inline markup: *italic*, **bold**, [n] citation (kept upright), ^sup^
function runs(text, opts = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\^[^^]+\^)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...opts }));
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...opts }));
    } else if (tok.startsWith("^")) {
      out.push(new TextRun({ text: tok.slice(1, -1), superScript: true, ...opts }));
    } else {
      out.push(new TextRun({ text: tok.slice(1, -1), italics: true, ...opts }));
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...opts }));
  return out.length ? out : [new TextRun({ text: "", ...opts })];
}

const P = (text, extra = {}) => new Paragraph({
  children: runs(text),
  spacing: { line: LEAD, after: 160 },
  alignment: AlignmentType.JUSTIFIED,
  ...extra,
});

const H1 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_1 });
const H2 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_2 });
const H3 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_3 });

const BULLET = (text, level = 0) => new Paragraph({
  children: runs(text),
  numbering: { reference: "bullets", level },
  spacing: { line: LEAD, after: 100 },
});

// Table: column widths in DXA summing to the table width; both table and cells set.
function table(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, w, header) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: header
      ? { type: ShadingType.CLEAR, fill: "EDEDED", color: "auto" }
      : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    children: [new Paragraph({
      children: runs(txt, { bold: !!header, size: 20 }),
      spacing: { line: 240, after: 0 },
    })],
  });
  return new Table({
    columnWidths: widths,
    width: { size: total, type: WidthType.DXA },
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false)) })),
    ],
  });
}

const SPACE = () => new Paragraph({ text: "", spacing: { after: 120 } });

// ---------- content ----------

const body = [];

body.push(new Paragraph({
  children: [new TextRun({
    text: "Can Large Language Model Agents Predict Antimicrobial Resistance from Bacterial "
        + "Genomes? A Benchmark of Accuracy and Unsupported Claims Against Phenotypic "
        + "Susceptibility Testing",
    bold: true, size: 30, font: FONT,
  })],
  spacing: { after: 120 }, alignment: AlignmentType.LEFT,
}));
body.push(new Paragraph({
  children: [new TextRun({
    text: "Introduction, hypotheses, aim and methods — draft of 21 November 2026",
    italics: true, size: 20, color: "595959", font: FONT,
  })],
  spacing: { after: 320 },
}));

// ===== 1. Introduction =====
body.push(H1("1. Introduction"));

body.push(P("Third-generation cephalosporin-resistant and carbapenem-resistant Enterobacterales both occupy the critical-priority tier of the WHO bacterial priority pathogens list 2024, the cephalosporin-resistant group listed separately for the first time [1]. Susceptibility testing remains the decision point for therapy, and whole-genome sequencing has long been proposed as a faster route to the same answer."));

body.push(P("That route works, but not yet well enough to replace phenotypic testing, and the literature is explicit about where it fails. In 9,001 *Escherichia coli* genomes with linked susceptibility results, AMRFinder failed the FDA major- and very-major-error thresholds for all seven antibiotics examined at strict identity and coverage; at default thresholds ampicillin sat at a very major error rate of 9.2% and ciprofloxacin at a major error rate of 18.2% [2]. On 1,095 *E. coli* from Canadian surveillance, Staramr reached 92.4% categorical concordance against broth microdilution, with the authors noting that prediction did not correlate well with CLSI breakpoints for some organism–antimicrobial combinations [3]. Across five pathogens, CARD and ResFinder differed in the direction of their errors — major error 42.7% against 25.1%, very major error 1.2% against 4.4% [4] — while ResFinder 4.0's own validation reached at least 95% genotype–phenotype concordance for 46 of 51 Gram-negative combinations [5]. The EUCAST subcommittee's 2025 update concludes that sequence-based prediction has advanced in separating wild-type from non-wild-type populations but that substantial obstacles remain before it can inform clinical decisions [6]."));

body.push(P("This body of work locates a specific difficulty. Detecting a determinant is largely solved; deciding what it implies for a given drug is not. The two drugs where the step fails hardest in *E. coli* show why. Every *E. coli* carries a chromosomal AmpC, catalogued as *blaEC*, expressed constitutively far below clinical significance; promoters from hyperproducing isolates are 70- to 120-fold stronger than from a low-level producer, and reverting a single −42 promoter mutation reduces expression 43-fold [7]. Gene presence therefore carries no information about ampicillin unless the regulatory context is read with it. For ciprofloxacin the problem is dose–response: substitutions in the quinolone resistance-determining regions of GyrA and ParC accumulate and the minimum inhibitory concentration rises in steps as they do [8], so isolates with one substitution or none show reduced susceptibility or low-level resistance rather than a clear phenotype, while those with two or more show high-level resistance [9]. A rule mapping presence to category must place a boundary somewhere in that gradient, and the published error rates show what the choice costs in both directions."));

body.push(P("Large language models have been applied to this clinical question, but from the other end of the pipeline. A GPT-4 agent customised with EUCAST expert rules and breakpoint tables classified resistance mechanisms across 862 phenotypic categories from 225 Gram-negative isolates, reaching 81.9% concordance against routine diagnostics where three human microbiologists reached 94.4% [10]. Fourteen models prescribing for 60 clinical cases accompanied by antibiograms produced correct prescriptions in at best 71.7% of responses [11], and against infectious-disease residents and specialists the models' weakest area was precisely the cases requiring an antibiogram to be read [12]. In every case the input is an already interpreted phenotype or a clinical vignette. None begins with a genome."));

body.push(P("Agentic systems that do begin with raw data have been benchmarked, though not on this task. BixBench poses some 300 open-answer questions over 50 bioinformatics scenarios and found leading models near 17% [13]. BioAgent Bench runs ten end-to-end tasks in which agents install packages and write staged outputs, benchmarking Claude Code, Codex CLI and OpenCode — the harness class examined here — and reports considerable run-to-run variability, but contains no antimicrobial resistance task [14]. BioSecBench-Surveillance gives agents a sandboxed tool suite and raw data across 100 deterministically graded pathogen-surveillance evaluations, one of seven categories being resistance characterisation, with the best configurations near 50% endpoint pass rate [15]. Closest to the present work, AMR-Bench-mini assembles a 924-task corpus for agentic mechanistic resistance reasoning in *Klebsiella pneumoniae* from isolate metadata, assemblies, laboratory susceptibility results and pinned annotation outputs, reporting 82–88% accuracy on a balanced pilot split and 50–64% on a hard split [16]. Separately, a trained transformer-based model predicts resistance in *Mycobacterium tuberculosis* from 12,185 CRyPTIC isolates [17], which is a predictive model rather than an agent."));

body.push(P("Two distinctions follow. AMR-Bench-mini supplies pinned annotation output, so choosing, installing and running a tool — and being wrong about which to run — lies outside its task. And none of these benchmarks scores output on the metrics a clinical laboratory uses: categorical agreement, very major error and major error are asymmetric in consequence in a way accuracy and pass rate cannot express, since calling a resistant organism susceptible reaches the patient and the reverse does not."));

body.push(P("Three phenomena this study observes are not new and are reported as instances. That nominally deterministic model output varies between runs is established generally [18], for coding-agent harnesses on bioinformatics tasks [14], and within antimicrobial decision support, where twelve scenarios submitted 100 times each showed reproducibility and clinical correctness moving independently [19]. That behaviour changes behind a fixed interface over months is likewise established [20]. And a human-adjudicated taxonomy of agent hallucinations already exists, with five categories and fourteen subcategories across five domains [21]."));

// ===== 2. Hypotheses =====
body.push(H1("2. Research question and hypotheses"));

body.push(P("The study was pre-registered as a descriptive benchmark. **No directional hypothesis was specified as to which agent would perform better**, and none is introduced here; the comparisons below were pre-specified as two-sided."));

body.push(P("**Primary question.** Given only an assembled *E. coli* genome and a list of six antibiotics, can an agentic command-line assistant choose and run its own tools and return a susceptible or resistant call that agrees with the laboratory phenotype at the rates a clinical laboratory would require?"));

body.push(P("**Pre-specified propositions, all non-directional:**"));
body.push(BULLET("**P1.** Each agent's categorical agreement, very major error rate and major error rate are estimated against the laboratory phenotype, and compared against the FDA criteria for antimicrobial susceptibility test devices [22] as reference lines rather than as pass/fail hypotheses."));
body.push(BULLET("**P2.** All pairwise comparisons among the arms are tested for equality of paired correctness by McNemar's exact test with Holm correction. The null is equality; no arm is nominated in advance."));
body.push(BULLET("**P3.** Within each agent, calls on a fixed isolate subset are expected to be identical across replicates; departure is quantified by Fleiss' κ rather than tested."));
body.push(BULLET("**P4.** Reported determinants, tool outputs, commands, breakpoints and accessions are checked against what the run actually produced. The null is that no such claim is unsupported."));

body.push(P("**Not hypotheses.** Run-to-run variation, change in a model behind a fixed interface, and the hallucination taxonomy are each precedented [14, 18–21]; they are measured and reported, not tested as novel propositions."));

// ===== 3. Aim =====
body.push(H1("3. Aim and objectives"));
body.push(P("**Aim.** To estimate, under pre-registration, how well agentic command-line assistants predict *E. coli* antimicrobial susceptibility phenotypes end to end from an assembled genome, on the metrics a clinical laboratory uses, and to characterise how they fail."));
body.push(P("**Primary objective.** For each agent, categorical agreement and very major error rate for genome-based S/R prediction against laboratory-derived phenotypes."));
body.push(P("**Secondary objectives:**"));
body.push(BULLET("Major error rate."));
body.push(BULLET("Comparison with a pre-specified rule applied to AMRFinderPlus output."));
body.push(BULLET("Run-to-run reproducibility."));
body.push(BULLET("Frequency and type of unsupported claims, by an adjudicated taxonomy."));
body.push(BULLET("Task completion, wall-clock time and tool usage."));

// ===== 4. Methods =====
body.push(H1("4. Methods"));

body.push(H2("4.1 Design"));
body.push(P("Pre-registered descriptive benchmark. The protocol, task prompt, isolate-selection code, reference-arm rule and analysis code were written and committed before any scored run; the freeze is recorded with a SHA-256 checksum of each frozen file. Every post-freeze change is logged with its date and reason. The unit of analysis is the isolate–antibiotic pair. The freeze is a commit in a repository the investigator controls, which is weaker evidence of timing than a third-party timestamp."));

body.push(H2("4.2 Reference standard and data source"));
body.push(P("Phenotypes and genome assemblies were taken from BV-BRC through its public REST API. Download dates, query strings and a SHA-256 checksum of every file are recorded in a manifest."));
body.push(P("Only records with evidence = “Laboratory Method” were used. BV-BRC also distributes machine-learning predictions as evidence = “Computational Method”, and these are the large majority of its *E. coli* records — for ampicillin, 12,671 of 234,759 records are laboratory-derived — so including them would compare one prediction against another."));
body.push(P("The recorded S/R call was used as reported, which makes the reference standard a clinical-breakpoint category. EUCAST has recommended since 2017, and reaffirmed in 2025, that epidemiological cut-off values rather than clinical breakpoints be the primary comparator for genotype–phenotype concordance [6, 23]. This study uses the secondary comparator deliberately: the question is whether an agent reproduces the call a laboratory would report, and that call is a clinical category. Consequently some disagreement counted here as error is disagreement with a breakpoint rather than with a wild-type boundary, and these figures are not comparable with studies scored against cut-off values."));
body.push(P("Calls derive from different testing methods (disk diffusion, MIC, broth and agar dilution) and standards (EUCAST, CLSI, or none stated) in versions differing between submitting studies. This heterogeneity bounds the agreement any genotype-based method can reach here."));

body.push(H2("4.3 Eligibility and sample"));
body.push(P("Eligible isolates were *E. coli* with at least one laboratory AMR record and a susceptible or resistant phenotype for at least one study antibiotic. Assemblies were excluded if total length fell outside 4.5–6.0 Mb or contigs exceeded 500. Isolate–antibiotic pairs with both an S and an R record were excluded as conflicting."));
body.push(P("Six antibiotics, one per class: ampicillin, cefotaxime, meropenem, ciprofloxacin, gentamicin and trimethoprim/sulfamethoxazole. An antibiotic entered the study only if at least 20 resistant and 20 susceptible eligible isolates existed; all six met this."));
body.push(P("120 isolates were drawn with a fixed seed, stratified so each antibiotic reached at least 20 resistant and 20 susceptible pairs where possible. Selection used phenotype labels only and never model output. Two isolates then failed assembly QC, leaving **118** isolates in the blinded set. Because selection writes phenotypes for all 120 while QC follows, 8 pairs belonged to the two excluded isolates and were never shown to any agent; scoring is restricted to pairs whose isolate is in the blinding key, giving **553 pairs**, of which **552** carry an S or R phenotype (238 R, 314 S). Intermediate phenotypes are excluded from the primary analysis."));

body.push(H2("4.4 Blinding and leakage control"));
body.push(P("Each isolate was renamed with a random code, FASTA headers stripped and contigs renamed, and the key kept outside the agent workspace. Residual memorisation remains possible: the genomes are public and blinding cannot remove sequence."));
body.push(P("Blinding was weaker in practice than the protocol assumed. The agents were not confined to their workspace and could read elsewhere on the disk, where the phenotype table and the code-to-genome key were stored. A script classifies every run as B0 (the file names never appear), B1 (a name appears in a directory listing or the agent's own prose, with no read command and no content in the log), B2 (a command read one of the files) or B3 (content appears in the log). The files were subsequently moved outside the project tree. No scored run read either file."));

body.push(H2("4.5 Arms"));
body.push(table(
  ["Arm", "Agent", "Harness", "Plan"],
  [
    ["A1", "Claude (claude-opus-5-5)", "Claude Code 2.1.325", "Max"],
    ["A3", "GPT (model identifier not recorded)", "Codex CLI 0.169.0", "Pro"],
    ["REF", "AMRFinderPlus 4.2.7, database 2026-10-29.1", "pre-specified mapping rule", "—"],
  ],
  [900, 3100, 3000, 1000],
));
body.push(SPACE());
body.push(P("A third agent arm was run and withdrawn before any of its results were analysed, because its harness proved to be multi-model, the runs carried no explicit model flag, and the identity of the serving model appears in no retrievable record. The same omission in milder form affects A3. Model identity is now captured before each run."));
body.push(P("Each agent ran in its vendor's own command-line harness with default settings, which measures the agent as a user meets it; harness and model are therefore not separable in this design. Every agent received an identical task prompt with no example answers. Isolates were processed in batches of 10, each a separate session with a fresh workspace containing only that batch's genomes, because a pilot consumed about 437,000 tokens for 3 isolates. Batch size was identical for every arm."));
body.push(P("Network restriction differs by harness and is reported per arm rather than assumed. For A3, --sandbox workspace-write runs model-issued commands without network access. For A1, --disallowed-tools WebSearch WebFetch removes the web tools and each run records its web-search and web-fetch counts, both zero across all 12 batches; shell commands are not OS-sandboxed on macOS, so network access from a command is not blocked at that level."));
body.push(H3("Reference arm"));
body.push(P("AMRFinderPlus was run on each assembly and a pre-specified rule mapped detected elements of type AMR to an S/R call per antibiotic. The rule was verified against the database and frozen before any run. It is degenerate for ampicillin: a beta-lactam determinant of any kind implies resistance, and nearly every *E. coli* carries one. It is reported as it ran rather than repaired after the fact. This is a property of class-level mapping, not of AMRFinderPlus, which reports determinants and makes no phenotypic claim [24]; accordingly, no comparison in this study supports a statement that the agents outperform AMRFinderPlus."));

body.push(H2("4.6 Outcomes"));
body.push(P("Categorical agreement (agreements over evaluable pairs); very major error (predicted S against reference R, over reference-R pairs); major error (predicted R against reference S, over reference-S pairs). A missing, malformed or explicitly uncertain prediction is a no-call, counted as an error in the primary analysis and excluded in a pre-specified sensitivity analysis."));
body.push(P("Results are displayed against the FDA criteria [22]: category agreement above 89.9%; major error below 3% of susceptible organisms tested; and for very major errors, an upper 95% confidence limit below 7.5% together with a lower limit below 1.5%. The very major error criterion is stated in confidence limits rather than as a flat value, and at this sample size the difference matters, so each criterion is computed rather than asserted. These criteria were written for devices measuring a phenotype against a reference method and are reference lines here, not a standard this study is held to."));
body.push(P("Reproducibility is Fleiss' κ across three replicates on a pre-specified random 40-isolate subset drawn with the same seed before any run, plus the proportion of pairs called identically in all three. The first replicate is the corresponding part of the full run; two further runs per arm were made, giving 168 scorable pairs per arm. Replicates ran consecutively, never concurrently."));
body.push(H3("Unsupported-claim taxonomy"));
body.push(table(
  ["Code", "Claim tested"],
  [
    ["H1", "A gene or variant name that does not exist"],
    ["H2", "A reported determinant absent from the isolate's own tool output"],
    ["H3", "An invented or incorrect breakpoint, guideline or rule"],
    ["H4", "A command claimed but absent from the log, or failed and reported as working"],
    ["H5", "An invented citation or accession"],
  ],
  [900, 7100],
));
body.push(SPACE());
body.push(P("A mechanical screen produces candidates from each run's transcript, methods file, command log and predictions; it is deliberately broad, so most candidates are expected to be rejected. The proportion of predictions for which the H2 comparison was possible is reported, so a zero cannot be mistaken for an unrun check."));

body.push(H2("4.7 Adjudication"));
body.push(P("Claude is one of the evaluated arms, so no model adjudicates the findings as the primary method. Candidates are shuffled into a single blinded sheet with the arm removed. Two reviewers confirm or reject each independently, with written instructions stating what does not count as an unsupported claim. Agreement is reported as Cohen's κ, disagreements resolved by discussion and the resolution recorded, and only then is the key opened. Only confirmed findings are counted. One replicate per agent is additionally read end to end to estimate what the screen misses."));

body.push(H2("4.8 Statistical analysis"));
body.push(P("Proportions with Wilson 95% confidence intervals, per antibiotic and pooled. The primary analysis uses one full run per agent. All pairwise comparisons among arms are made on paired isolate–antibiotic correctness with McNemar's exact test and Holm correction."));
body.push(P("Two analyses were added beside the pre-registered ones, neither replacing them, and both labelled post-hoc wherever they appear. First, McNemar restricted to pairs on which both arms made a call: the primary comparison scores a no-call as an error and the arms differ in how often they decline, so without this restriction an arm that abstains more often appears less accurate when it may simply be more cautious. Second, an exploratory analysis of whether an agent's own expressed uncertainty identifies the calls it got wrong, asked only of calls the agent made, since under the primary scoring an abstention is an error by definition and the measure would otherwise be circular."));
body.push(P("Pre-specified sensitivity analyses: intermediate phenotypes as non-susceptible; no-calls excluded; phenotypes reinterpreted from MIC values with current EUCAST breakpoint tables where MICs are available; stratification by recorded testing standard. The recorded standard is case-normalised before stratification, since the repository writes it four ways."));
body.push(P("All numbers are produced by the analysis scripts; none is typed by hand."));

// ===== References =====
body.push(H1("References"));
const refs = [
  "World Health Organization. WHO bacterial priority pathogens list, 2024. Geneva: WHO; 2024.",
  "Lipworth S, Crook D, Walker AS, Peto T, Stoesser N. Exploring uncatalogued genetic variation in antimicrobial resistance gene families in *Escherichia coli*: an observational analysis. *Lancet Microbe*. 2024;5(11):100913.",
  "Wilke MAP, Mataseje LF, Lerminiaux N, et al. Genomic prediction of antimicrobial resistance in priority healthcare pathogens using Staramr. *Microbiol Spectr*. 2026;14(11):e0165226.",
  "Mahfouz N, Ferreira I, Beisken S, von Haeseler A, Posch AE. Large-scale assessment of antimicrobial resistance marker databases for genetic phenotype prediction: a systematic review. *J Antimicrob Chemother*. 2020;75(11):3099–3108.",
  "Bortolaia V, Kaas RS, Ruppe E, et al. ResFinder 4.0 for predictions of phenotypes from genotypes. *J Antimicrob Chemother*. 2020;75(12):3491–3500.",
  "Samuelsen Ø, López-Causapé C, Aarestrup FM, et al. The role of whole genome sequencing in antimicrobial susceptibility prediction of bacteria: 2025 update from the EUCAST Subcommittee. *Clin Microbiol Infect*. 2026;32(7S):S1–S34.",
  "Caroff N, Espaze E, Gautreau D, Richet H, Reynaud A. Analysis of the effects of −42 and −32 *ampC* promoter mutations in clinical isolates of *Escherichia coli* hyperproducing *ampC*. *J Antimicrob Chemother*. 2000;45(6):783–788.",
  "Qiang YZ, Qin T, Fu W, Cheng WP, Li YS, Yi G. Use of a rapid mismatch PCR method to detect *gyrA* and *parC* mutations in ciprofloxacin-resistant clinical isolates of *Escherichia coli*. *J Antimicrob Chemother*. 2002;49(3):549–552.",
  "Yang J, Luo Y, Cui S, Wang W, Han L. Diverse phenotypic and genotypic characterization among clinical *Klebsiella pneumoniae* and *Escherichia coli* isolates carrying plasmid-mediated quinolone resistance determinants. *Microb Drug Resist*. 2011;17(3):363–367.",
  "Giske CG, Bressan M, Fiechter F, Hinic V, Mancini S, Nolte O, Egli A. GPT-4-based AI agents — the new expert system for detection of antimicrobial resistance mechanisms? *J Clin Microbiol*. 2024;62(11):e0068924.",
  "De Vito A, Geremia N, Marino A, et al. Comparing large language models for antibiotic prescribing in different clinical scenarios: which performs better? *Clin Microbiol Infect*. 2025;31(8):1336–1342.",
  "De Vito A, Colpani A, Bitas C, et al. Assessing ChatGPT's theoretical knowledge and prescriptive accuracy in bacterial infections: a comparative study with infectious diseases residents and specialists. *Infection*. 2025;53(3):873–881.",
  "Mitchener L, Laurent JM, Andonian A, et al. BixBench: a comprehensive benchmark for LLM-based agents in computational biology. arXiv:2503.00096. 2025.",
  "Fa D, Čuljak M, Pandža B, Čupić M. BioAgent Bench: an AI agent evaluation suite for bioinformatics. arXiv:2601.21800. 2026.",
  "Bhasin H, Flyangolts K, Wang D, et al. BioSecBench-Surveillance: a verifiable benchmark for AI agents in pathogen genomic surveillance. arXiv:2607.19262. 2026.",
  "Nergiz AI, Cinar EN. AMR-Bench-mini: a diagnostic benchmark for agentic mechanistic AMR reasoning under evidence insufficiency. Poster, 3rd Workshop on Multi-modal Foundation Models and Large Language Models for Life Sciences, ICML 2026.",
  "Testagrose C, Pandey S, Serajian M, Marini S, Prosperi M, Boucher C. Leveraging large language models to predict antibiotic resistance in *Mycobacterium tuberculosis*. *Bioinformatics*. 2025;41(Suppl 1):i40–i48.",
  "Atil B, Aykent S, Chittams A, et al. Non-determinism of “deterministic” LLM settings. arXiv:2408.04667. 2025.",
  "De Vito A, Geremia N, Russo A, Colpani A, Vaira LA, Madeddu G. Reproducibility of AI-generated antibiotic recommendations in standardised clinical scenarios: a proof-of-concept experimental study. *Int J Antimicrob Agents*. 2026;67(10):107881.",
  "Chen L, Zaharia M, Zou J. How is ChatGPT's behavior changing over time? arXiv:2307.09009. 2023.",
  "Liu X, Yang X, Li Z, Li P, He R. AgentHallu: benchmarking automated hallucination attribution of LLM-based agents. arXiv:2601.06818. 2026.",
  "US Food and Drug Administration. Class II special controls guidance document: antimicrobial susceptibility test (AST) systems. 28 August 2009.",
  "Ellington MJ, Ekelund O, Aarestrup FM, et al. The role of whole genome sequencing in antimicrobial susceptibility testing of bacteria: report from the EUCAST Subcommittee. *Clin Microbiol Infect*. 2017;23(1):2–22.",
  "Feldgarden M, Brover V, Gonzalez-Escalona N, et al. AMRFinderPlus and the Reference Gene Catalog facilitate examination of the genomic links among antimicrobial resistance, stress response, and virulence. *Sci Rep*. 2021;11(1):12728.",
];
refs.forEach((r, i) => body.push(new Paragraph({
  children: runs(`${i + 1}. ${r}`),
  spacing: { line: 260, after: 90 },
  indent: { left: 360, hanging: 360 },
})));

body.push(SPACE());
body.push(new Paragraph({
  children: runs("Three citation details remain unresolved and are flagged in the project's reference file: the AMR-Bench-mini full text could not be retrieved, so four statements this draft makes about it rest on its listing abstract; bioRxiv and PubMed disagree on the first author's spelling for reference 10; and reference 1 should cite the WHO report itself with its own date and ISBN rather than the accompanying news release.", { italics: true, size: 20, color: "595959" }),
  spacing: { line: 260, after: 120 },
}));

// ---------- document ----------

const doc = new Document({
  creator: "Sajjad Eslamkhah",
  title: "LLM agents and antimicrobial resistance prediction — introduction, hypotheses, aim and methods",
  styles: {
    default: {
      document: { run: { font: FONT, size: SZ }, paragraph: { spacing: { line: LEAD } } },
      title: { run: { font: FONT, size: 30, bold: true }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true } },
      heading1: { run: { font: FONT, size: 26, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 360, after: 140 }, keepNext: true } },
      heading2: { run: { font: FONT, size: 23, bold: true, color: "2E5496" }, paragraph: { spacing: { before: 260, after: 110 }, keepNext: true } },
      heading3: { run: { font: FONT, size: 22, bold: true, italics: true }, paragraph: { spacing: { before: 200, after: 90 }, keepNext: true } },
    },
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 240 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 240 } } } },
      ],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838, orientation: PageOrientation.PORTRAIT },
        margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "7F7F7F", font: FONT })],
        })],
      }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("LLM-AMR_Introduction_Methods.docx", b);
  console.log("yazildi:", b.length, "bayt");
});
