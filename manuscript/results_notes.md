# Results, as computed

Working notes for the Results section. Every number here comes from a file in
`results/`, named beside it. Nothing is typed from memory. The adjudication is not
done, so hallucination counts are candidates, not confirmed findings.

Scored set: 118 isolates, 552 isolate–antibiotic pairs with a susceptible or resistant
laboratory phenotype (238 R, 314 S). Source: `results/performance.tsv`.

## Accuracy against the laboratory phenotype

| Arm | Analysis | CA (95% CI) | VME (95% CI) | ME (95% CI) | No-calls |
|---|---|---|---|---|---|
| Claude | primary | 95.3% (93.2–96.8) | 6.7% (4.2–10.6) | 3.2% (1.7–5.8) | 0 |
| GPT | primary | 92.2% (89.7–94.2) | 5.5% (3.2–9.1) | 4.5% (2.7–7.3) | 16 |
| GPT | calls made only | 95.0% (92.8–96.5) | 5.5% (3.2–9.2) | 4.7% (2.8–7.7) | — |
| REF rule | primary | 86.6% (83.5–89.2) | 5.5% (3.2–9.1) | 19.4% (15.4–24.2) | 0 |

Claude's primary and no-call-excluded rows are identical: it called every pair it was
given and never abstained.

### Against the FDA AST criteria

Computed in `scripts/metrics.py` from the confidence limits, not from the point
estimates (FDA 2009, section X.A). No arm meets the criteria:

| Arm | CA > 89.9% | ME < 3% | VME limits | All |
|---|---|---|---|---|
| Claude | met | **not met** (3.18%) | **not met** | not met |
| GPT | met | **not met** (4.46%) | **not met** | not met |
| GPT, calls made | met | **not met** (4.67%) | **not met** | not met |
| REF rule | **not met** | **not met** | **not met** | not met |

Claude misses the major-error criterion by 0.18 percentage points. Every arm fails both
error criteria; only the rule-based arm also fails agreement.

### Per antibiotic, the two findings that stand out

From `results/performance.tsv`:

- **Meropenem** carries the worst very major error rates: Claude 35% (7 of 20
  reference-resistant pairs called susceptible), GPT 20%. The denominator is small
  because the sample was stratified to reach 20 resistant pairs per antibiotic, so this
  is not a population estimate; it is the clinically worst error on the clinically most
  important drug.
- **Ampicillin** is where the reference rule collapses: all 26 phenotypically
  susceptible isolates were called resistant (ME 26/26). Claude called all 26 correctly.

## Claude against GPT

From `results/mcnemar.tsv`:

| Comparison | Analysis | A only correct | B only correct | p | p (Holm) |
|---|---|---|---|---|---|
| Claude vs GPT | primary | 20 | 3 | 0.00049 | 0.00098 |
| Claude vs GPT | both arms called | 5 | 3 | 0.73 | 0.73 |
| Claude vs REF | primary | 58 | 10 | 2.4e-9 | 1.4e-8 |
| GPT vs REF | both arms called | 40 | 7 | 1.1e-6 | 4.3e-6 |

**The difference between the two agents is a difference in willingness to call, not in
accuracy.** On the pre-registered primary analysis, which scores a no-call as an error,
Claude is ahead by three points with p = 0.0005. On the 536 pairs both arms actually
called, the two are indistinguishable (p = 0.73). Both remain far ahead of the rule.

Both results are reported together. Reporting only the first would say Claude is more
accurate than GPT, which the second contradicts.

## Reproducibility

40-isolate subset, three replicates per arm, 168 scorable pairs.
Source: `results/reproducibility.tsv`.

| Arm | Identical in all three | Fleiss κ | 1v2 | 1v3 | 2v3 |
|---|---|---|---|---|---|
| Claude | 166/168 = 98.8% (95.8–99.7) | 0.983 | 1 | 1 | 2 |
| GPT | 160/168 = 95.2% (90.9–97.6) | 0.933 | 8 | 8 | 0 |

### GPT changed between 15 and 21 November

GPT's replicates 2 and 3 agree with each other exactly and both differ from replicate 1
on the same 8 pairs. That is not run-to-run noise. On those 8 pairs, replicate 1 agreed
with the laboratory 0 times and replicates 2 and 3 agreed 7 times each:

| Pair | Laboratory | rep1 | rep2 | rep3 |
|---|---|---|---|---|
| ISO_009 ciprofloxacin | S | R | S | S |
| ISO_035 ciprofloxacin | S | R | S | S |
| ISO_017 gentamicin | S | R | NA | NA |
| ISO_054 ampicillin | S | NA | S | S |
| ISO_056 ciprofloxacin | S | NA | S | S |
| ISO_057 trimethoprim/sulfamethoxazole | R | NA | R | R |
| ISO_103 ciprofloxacin | S | NA | S | S |
| ISO_106 ciprofloxacin | S | NA | S | S |

Five of the eight are pairs replicate 1 declined and the later replicates called
correctly; two are wrong resistant calls that became correct susceptible calls. The
harness version was 0.169.0 on both dates and the prompt, isolates and batching were
identical.

The arm also got faster. Median wall-clock seconds per batch (`results/provenance.tsv`):
GPT 449 in replicate 1, 231 and 265 in replicates 2 and 3. Claude shows no such shift
(560, 547, 562). Accuracy alone could be chance at eight pairs; accuracy and speed moving
together over six days, with the harness version unchanged, is harder to read as anything
but a change behind the CLI.

Two consequences. The primary analysis rests on replicate 1 and therefore understates
the GPT arm as it behaved six days later. And the cause cannot be established, because
no model identifier is recorded for this arm — the logging gap described in the methods.
An agentic tool validated on one date may not be the same tool a week later, and without
a recorded model version a laboratory cannot tell.

Claude's two disagreements are both borderline ciprofloxacin pairs with a susceptible
laboratory result, scattered across the three pairings.

## Hallucination screen (candidates, adjudication pending)

Source: `results/audit/`. H2 coverage was 708 of 708 predictions per arm, so a zero is a
result and not an unrun check.

| Code | Claude | GPT |
|---|---|---|
| H1 gene or variant name found nowhere | 3 | 1 |
| H2 determinant absent from the isolate's own tool output | **0** | **0** |
| H3 stated breakpoint or absolute rule | 2 | 0 |
| H4 command claimed but not run, or failed and reported as working | **0** | **0** |

Neither agent reported a determinant its own tool output did not contain, and neither
claimed to have run a command it did not run. The four H1 candidates are `strA`, `strB`,
`crpP` and `oqxAB`, all real determinants under the literature's naming rather than the
catalogue's; the two H3 candidates cite the EUCAST ciprofloxacin susceptible breakpoint
of ≤0.25 mg/L, which is correct. Those readings are the investigator's preliminary view
and carry no weight until the two blinded readers return their verdicts.

Agents did not use the available tooling identically: Claude ran 124 shell commands
across its 12 batches, GPT 325, both with an exit code recorded for every command.

## Uncertainty, post-hoc and exploratory

Source: `results/uncertainty.tsv` and `results/uncertainty_flagged_pairs.tsv`.

Neither agent's expressed uncertainty identifies a single very major error: 0 of Claude's
16 and 0 of GPT's 13.

(An earlier run of this analysis counted 553 calls and 27 errors for Claude against
metrics.py's 552 and 26: it had kept the one intermediate phenotype that the protocol
excludes from the primary analysis, so every call on that pair scored as an error. Fixed
2026-11-21; the figures below are the corrected ones.)

The two express doubt in different ways, and neither way helps where it matters most.

**Claude flags calls it still makes.** Six of 553, of which five are correct and one is
wrong — ISO_103 ciprofloxacin, called resistant against a susceptible laboratory result.
That same pair is one of the only two on which its replicates disagree. So the flag
marked a call that was both wrong and unstable, while leaving all 16 very major errors
unmarked. Error rate among flagged calls 16.7% (3.0–56.4) against 4.8% (3.3–6.9) among
unflagged: the interval is far too wide at six calls to support a claim either way.

**GPT expresses doubt by declining.** It flagged none of the 537 calls it made; all six
of its flagged pairs are ones it then abstained on. All six have a susceptible laboratory
result, so calling susceptible would have been right on all six: the abstention cost six
correct answers and averted no very major error among them. Of its 16 abstentions
overall, 2 are laboratory-resistant.

**ISO_103 ciprofloxacin was flagged independently by both agents** — Claude called it
wrongly, GPT declined it. The difficulty sits in the isolate, a borderline single-gyrA
genotype, rather than in either agent.

## What is not yet done

- Blinded adjudication by two readers (`results/audit/adjudication_sheet.tsv`), Cohen's κ
  between them, and one replicate per arm read end to end to estimate what the screen
  misses.
- Pre-registration deposit with a third-party timestamp.
- Pre-specified sensitivity analyses: intermediate phenotypes as non-susceptible;
  phenotypes reinterpreted from MICs with EUCAST v16.1; stratification by testing
  standard.
- Answer-key-seeking scored by the two-reader procedure, as section 9 requires.
