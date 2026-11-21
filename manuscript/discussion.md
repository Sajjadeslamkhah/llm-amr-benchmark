# Discussion

> Draft. Claims about hallucination frequency are marked <mark>**[Pending adjudication]**</mark> and
> stand on candidates rather than confirmed findings until the two blinded readers return
> their verdicts. Every figure cited here is in `manuscript/results_notes.md` with the
> file it came from.

## What this study found

Two agentic command-line assistants, given only an assembled *E. coli* genome and a list
of six antibiotics, chose and ran their own tools and returned a susceptible or resistant
call for each pair. Both agreed with the laboratory phenotype more often than a
pre-registered rule applied to AMRFinderPlus output, and the margin is large and
significant. Neither was close to the agreement and error rates a laboratory would
require before using such a result.

The three findings that bear on whether this approach could be used are these.

**Neither agent fabricated what its tools reported.** On the pre-registered taxonomy, no
determinant was reported for an isolate whose own tool output did not contain it, and no
command was claimed that the execution log does not show, with the comparison possible
for every one of the 708 predictions per arm. <mark>**[Pending adjudication]**</mark> This is not what
the literature on language-model reliability would lead one to expect, and it matters for
how such a system would be supervised: the failure mode here is not invention but
interpretation. The determinants the agents listed were really there; what they concluded
from them was sometimes wrong.

**The agents do not know where they are wrong.** Claude marked six of 552 calls as
uncertain and covered none of its 16 very major errors; GPT marked none of the calls it
made, expressing doubt instead by declining 16 pairs, of which only two were resistant.
Self-reported confidence therefore cannot be used to triage which calls a laboratory
should verify, which is the obvious way one would try to make an imperfect predictor
usable. A system that is wrong 5% of the time and can say which 5% is a different
proposition from one that is wrong 5% of the time and cannot.

**Agreement was not the same tool a week later.** GPT's three replicates on the
reproducibility subset split 1 against 2-and-3: the later two agree with each other
exactly and both differ from the first on the same eight pairs, every one of them moving
toward the laboratory result, while median time per batch fell from 449 to about 250
seconds. The harness version, prompt, isolates and batching were identical. Claude shows
no such shift. Something behind the command-line tool changed between 15 and 21 November,
and because no model identifier is recorded for that arm we cannot say what.

## Measured against what a laboratory would require

No arm met the FDA criteria for an antimicrobial susceptibility test device. Both agents
cleared the agreement criterion; all three arms failed both error criteria. Claude missed
the major-error limit by 0.18 percentage points and the very major error limit by a wide
margin.

The very major error rate is the number that governs. A call of susceptible against a
resistant organism is the error that reaches the patient, and at 5-7% these methods are
three to four times above the limit set for a device measuring the same quantity. Within
that, meropenem is the worst case: 35% of reference-resistant meropenem pairs were called
susceptible by Claude and 20% by GPT. The denominator is 20 pairs, inflated deliberately
by stratified sampling, so this is not a population estimate — but carbapenem resistance
is where a missed call is least recoverable, and both agents were weakest exactly there.

These criteria were written for devices measuring a phenotype against a reference method,
and genotype-based prediction is a different task with a different error structure. They
are not a standard this study is held to. They are, however, the criteria a laboratory
would reach for, and the gap is not marginal.

## The comparison between the two agents is a comparison of caution

On the pre-registered primary analysis Claude agrees three points more often than GPT and
the difference is significant. On the 536 pairs both arms actually called, they are
indistinguishable. The entire difference is GPT's 16 abstentions, which the primary
analysis scores as errors.

Which analysis is the right one depends on the use. For a screening application where
every isolate must receive a call, an abstention is a failure and the primary analysis is
the relevant one. For a laboratory willing to run conventional testing on the pairs an
agent declines, abstention is the desirable behaviour and the second analysis is. The two
agents differ in a design choice, not in capability, and GPT's methods file states the
choice explicitly: an isolated determinant "is assigned NA because clinical resistance is
uncertain."

The practical lesson is about benchmark construction rather than about either agent. A
scoring rule that treats "I don't know" as a wrong answer will rank the agent that always
answers above the agent that sometimes declines, whatever their accuracy. Reporting one
number would have produced a finding that the other number contradicts.

Abstention was not free here. All six of the pairs GPT both flagged and declined have a
susceptible laboratory result, so answering susceptible would have been right on all six;
of its 16 abstentions in total, two were resistant. On this sample, declining cost more
correct answers than it averted serious errors.

## What the reference arm does and does not show

The reference arm is a rule we wrote and froze, applied to AMRFinderPlus output. It is not
AMRFinderPlus's own prediction: the tool reports the determinants it detects and makes no
phenotypic claim. **No comparison in this study supports a statement that the agents
outperform AMRFinderPlus.**

The rule's failure for ampicillin makes the point concrete. Because a beta-lactam
determinant of any kind implied resistance, and nearly every *E. coli* carries one, the
rule called all 26 phenotypically susceptible isolates resistant. Claude called all 26
correctly. What separates them is not detection — both saw the same genes — but knowing
that a chromosomal *blaEC* at basal expression does not confer clinical ampicillin
resistance while an acquired *blaTEM-1* does. That distinction is exactly what a
class-level mapping cannot encode and what the agents supplied.

We report the rule as it ran rather than repairing it after seeing the result. A rule
rewritten once the numbers are known is not a pre-registered comparator, and the failure
is informative in itself: naive determinant-to-phenotype mapping breaks down precisely
where carriage is near-universal.

## Two findings about measurement rather than about models

**A vendor's own agent CLI need not run that vendor's model, and need not record which
model answered.** A third arm was run and withdrawn. Antigravity CLI, used for the Gemini
arm, turns out to list three Flash-tier Gemini variants alongside Claude Sonnet, Claude
Opus and GPT-OSS models; the runs carried no explicit model flag, and the identity of the
model that served them appears in no local record we could find. The arm was therefore
unusable and is reported as withdrawn with its data retained. The same omission, in
milder form, affects the GPT arm, whose drift we can measure but not explain. Anyone
benchmarking agentic tools should pin the model explicitly and capture its identifier
before the run; we did not, and it cost an arm and an explanation.

**A mechanical hallucination screen can manufacture differences between vendors.** Our
first implementation produced 114 candidates that were almost entirely artifacts. One
class matters beyond this study: because one harness wraps a shell command across
backslash-continued lines, a single documented command counted as several findings, and
that alone made that arm appear three times worse than the other on the most serious
category. A screen whose candidate counts depend on log formatting cannot support a
comparison between arms. The taxonomy was unchanged; the implementation was rewritten
before any of its output was used, and ten regression tests now pin each artifact.

## Limitations

- **Reference standard.** The phenotypes come from different testing methods and
  standards in versions that differ between submitting studies, and the recorded call is
  used as reported. This bounds the agreement any genotype-based method can reach. The
  stratified analysis shows the strata are not interchangeable: resistance in the
  CLSI-labelled records is less often explained by a detectable determinant, and every
  arm — including the standard-blind rule — does worse there.
- **Memorisation.** The genomes are public and may appear in training data. Blinding
  removed identifiers but cannot remove sequence. Reading the agents' own reasoning,
  which proceeds from the determinants they detected, argues against recall driving the
  result, but does not exclude it.
- **Blinding was weaker than the protocol assumed.** The agents were not confined to
  their workspace. No scored run read the phenotype table or the code-to-genome key, and
  Claude's own report states that it saw those files and did not open them — but the
  control was procedural, not enforced, until the files were moved on 15 November.
- **One run per arm for the primary analysis**, with reproducibility measured on a
  40-isolate subset. Given the GPT drift, a single run fixes a model at a date rather
  than characterising it.
- **Sample.** 118 isolates and 552 pairs, stratified to reach 20 resistant pairs per
  antibiotic. Per-antibiotic error rates rest on small denominators and the resistant
  prevalence is not that of any clinical population.
- **Two agents, one harness each, one organism.** Harness and model are not separable in
  this design: what is measured is the agent as a user meets it.
- **Pre-registration without a third-party timestamp.** The freeze is a commit in a
  repository we control. <mark>**[Pending: deposit with a DOI.]**</mark>

## What would have to change

For genome-based prediction by agent to be usable in a clinical workflow, the very major
error rate would have to fall by roughly a factor of four, and that is the smaller
problem. The larger one is that a laboratory needs to know which calls to distrust, and
neither agent's self-reported uncertainty identified a single very major error. Until an
agent can mark its own unreliable calls, the only safe deployment is one in which every
call is confirmed conventionally, which removes the reason to use it.

Two requirements follow for anyone who evaluates these systems. Pin and record the model,
because the tool changes under a fixed version string. And report the scoring rule's
treatment of abstention explicitly, because it decides the ranking.

## Conclusion

Agentic assistants reading bacterial genomes produced susceptibility calls that agreed
with laboratory results more often than a frozen determinant-mapping rule, and did so
without fabricating what their tools reported. <mark>**[Pending adjudication]**</mark> They remain well
outside the error limits that would permit clinical use, they are weakest on carbapenems
where a missed call matters most, and they cannot identify their own unreliable calls. The
difference between the two agents was a difference in willingness to answer rather than in
accuracy. One of the three arms could not be reported at all because the harness did not
record which model answered, and one of the two remaining arms changed measurably within
six days. The reliability question for this class of tool is at least as much about
knowing what was measured as about how well it performed.
