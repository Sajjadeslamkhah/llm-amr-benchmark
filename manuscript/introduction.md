# Introduction

> Draft. Citations were verified against the sources on 2026-11-21; the two that could not
> be confirmed are marked in `manuscript/references.md` and in the text below.

Third-generation cephalosporin-resistant and carbapenem-resistant Enterobacterales both
sit in the critical-priority tier of the WHO bacterial priority pathogens list 2024, the
cephalosporin-resistant group as an entry of its own for the first time.<sup>WHO2024</sup>
Susceptibility testing remains the decision point for treatment, and whole-genome
sequencing has long been proposed as a faster route to the same answer.

That route works, but not yet well enough to replace phenotypic testing, and the
literature is unusually explicit about where it fails. In 9,001 *Escherichia coli* genomes
with linked susceptibility results, AMRFinder failed the FDA major- and very-major-error
thresholds for all seven antibiotics examined when run at strict identity and coverage;
relaxing to default thresholds improved sensitivity at the cost of specificity, leaving
ampicillin at a very major error rate of 9.2% and ciprofloxacin at a major error rate of
18.2%.<sup>Lipworth2024</sup> On 1,095 *E. coli* from Canadian surveillance, Staramr
reached 92.4% categorical concordance against broth microdilution while the authors noted
that prediction did not correlate well with CLSI breakpoints for some
organism-antimicrobial combinations.<sup>Wilke2026</sup> Across five pathogens, CARD and
ResFinder differed sharply in the direction of their errors — major error 42.7% against
25.1%, very major error 1.2% against 4.4%<sup>Mahfouz2020</sup> — while ResFinder 4.0's own
validation reached at least 95% genotype-phenotype concordance for 46 of 51 Gram-negative
combinations.<sup>Bortolaia2020</sup> The EUCAST subcommittee's 2025 update concludes that
sequence-based prediction has advanced in separating wild-type from non-wild-type
populations but that substantial obstacles remain before it can serve clinical
decisions.<sup>EUCAST2026</sup>

What this body of work locates is a specific difficulty. Detecting a resistance
determinant is largely solved; deciding what it implies for a given drug is not, and the
two drugs where it fails hardest in *E. coli* illustrate why. Every *E. coli* carries a
chromosomal AmpC, now catalogued as *blaEC*, expressed constitutively at a level far below
clinical significance; promoters from hyperproducing isolates are 70- to 120-fold stronger
than from a low-level producer, and reverting a single −42 promoter mutation reduces
expression 43-fold.<sup>Caroff2000</sup> Gene presence therefore carries no information
about ampicillin unless the regulatory context is read with it. For ciprofloxacin the
problem is dose-response rather than regulation: substitutions in the quinolone
resistance-determining regions of GyrA and ParC accumulate, and the minimum inhibitory
concentration rises in steps as they do,<sup>Qiang2002</sup> so isolates carrying a single
substitution or none show reduced susceptibility or low-level resistance rather than a
clear phenotype, while isolates with two or more show high-level
resistance.<sup>Yang2011</sup> A rule that maps determinant presence to a category must
place a boundary somewhere in that gradient, and the published error rates show what the
choice costs in both directions.

Large language models have been applied to this clinical question, but from the other end
of the pipeline. A GPT-4 agent customised with EUCAST expert rules and breakpoint tables
classified resistance mechanisms across 862 phenotypic categories from 225 Gram-negative
isolates, reaching 81.9% concordance against routine diagnostics where three human
microbiologists reached 94.4%.<sup>Giske2024</sup> Fourteen models prescribing antibiotics
for 60 clinical cases accompanied by antibiograms produced correct prescriptions in at best
71.7% of responses,<sup>DeVito2025a</sup> and in a comparison against infectious-disease
residents and specialists the models' weakest area was precisely the cases requiring an
antibiogram to be read.<sup>DeVito2025b</sup> In every case the input is an already
interpreted phenotype or a clinical vignette. None begins with a genome.

Agentic systems that do begin with raw data have been benchmarked, though not on this
task. BixBench poses around 300 open-answer questions over 50 real bioinformatics scenarios
and found leading models near 17%.<sup>Mitchener2025</sup> BioAgent Bench runs ten
end-to-end tasks in which agents install packages and write staged outputs, benchmarking
Claude Code, Codex CLI and OpenCode — the same harness class examined here — and reports
considerable run-to-run variability; its bacterial tasks cover comparative genomics,
variant calling and metagenomics, but it contains no antimicrobial resistance
task.<sup>Fa2026</sup> BioSecBench-Surveillance gives agents a sandboxed tool suite and
raw or near-raw data across 100 deterministically graded pathogen-surveillance evaluations,
one of its seven categories being resistance characterisation, with the best configurations
near 50% endpoint pass rate.<sup>Bhasin2026</sup> Closest to the present work,
AMR-Bench-mini assembles a 924-task corpus for agentic mechanistic resistance reasoning in
*Klebsiella pneumoniae* from isolate metadata, assemblies, laboratory susceptibility
results and pinned annotation outputs, reporting 82–88% accuracy on a balanced pilot split
and 50–64% on a hard split.<sup>Nergiz2026</sup> Separately, a trained transformer-based
model predicts resistance in *Mycobacterium tuberculosis* from 12,185 CRyPTIC
isolates,<sup>Testagrose2025</sup> which is a predictive model rather than an agent.

Two distinctions follow from that list. AMR-Bench-mini supplies its agents with pinned
annotation output, so the step of choosing, installing and running a tool — and of being
wrong about which tool to run — is outside its task. And none of these benchmarks scores
output on the metrics a clinical laboratory uses: categorical agreement, very major error
and major error are asymmetric in consequence in a way that accuracy and pass rate cannot
express, since calling a resistant organism susceptible reaches the patient and the reverse
does not.

This study therefore asks a question none of them asks. Given only an assembled *E. coli*
genome and a list of six antibiotics, one per class and including both of the hard cases
above, can an agentic command-line assistant choose and run its own tools and return a
susceptible or resistant call that agrees with the laboratory result at the rates a
laboratory would require? Two agents were run in their vendors' own command-line harnesses
against laboratory phenotypes from BV-BRC, alongside a pre-registered rule applied to
AMRFinderPlus output as a reference arm, with the protocol, selection code, reference rule
and analysis code frozen before any scored run.

Three things this study measures are not new, and are reported as instances rather than as
discoveries. That nominally deterministic language-model output varies between runs has
been quantified generally,<sup>Atil2025</sup> for coding-agent harnesses on bioinformatics
tasks,<sup>Fa2026</sup> and within antimicrobial decision support, where twelve scenarios
submitted 100 times each to two systems showed that reproducibility and clinical
correctness do not move together.<sup>DeVito2026</sup> That the behaviour of a model behind
a fixed interface changes over months is likewise established.<sup>Chen2023</sup> And a
human-adjudicated taxonomy of agent hallucinations already exists, with five categories and
fourteen subcategories derived across five domains.<sup>Liu2026</sup> What is reported here
is how these phenomena appear in per-drug susceptibility calls specifically: whether
run-to-run variation propagates into the very major and major error rates, which is where
it would matter clinically, and whether the determinants an agent reports are ones its own
tools actually produced.
