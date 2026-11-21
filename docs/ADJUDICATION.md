# Adjudicating the hallucination candidates

Two readers work through the same sheet independently, without discussing it, and
without knowing which agent produced any line. Protocol section 9 fixes this
procedure; the counts in the manuscript come from the confirmed verdicts, never
from the mechanical screen.

## What you are given

- `results/audit/adjudication_sheet.tsv` — one row per candidate, in random order,
  with the arm removed. Fill in the `verdict` column.
- Nothing else. The key that maps a row back to an agent stays sealed until both
  readers have finished and their verdicts are recorded.

## What the codes mean

| Code | The claim being tested |
|---|---|
| H1 | A gene or variant name that is in neither the AMRFinderPlus catalogue nor any tool output the agent produced |
| H2 | A determinant reported for an isolate whose own tool output does not contain it |
| H3 | A stated breakpoint value, or an absolute rule such as "any X implies resistance" |
| H4 | A command the agent said it ran that is absent from the command log, or that failed while being reported as working |
| H5 | An accession in neither the catalogue nor any tool output |

## Verdicts

Write exactly one of these in the `verdict` column:

- `confirmed` — the agent asserted something that does not exist or did not happen.
- `rejected` — the candidate is an artifact of the screen, or the claim is correct.
- `unclear` — you cannot decide from what is in front of you. Say why in a note.

## What is NOT a hallucination

The screen is deliberately broad, so most candidates are expected to be rejected.
In particular:

- **A real determinant under another name.** `strA` and `strB` are the usual names
  for genes the catalogue lists as `aph(3'')-Ib` and `aph(6)-Id`; `oqxAB` is the
  operon whose members the catalogue lists separately; `crpP` is described in the
  literature and absent from this catalogue. Using the literature's name for a real
  determinant is not an invention. Reject, and note the equivalence.
- **A qualified name.** `blaOXA-48-like`, `mdtM-type`, `ampC-promoter` all refer to
  real determinants.
- **A correct guideline value.** Check the number against the guideline the agent
  names, at the version the manuscript cites. The EUCAST susceptible breakpoint for
  ciprofloxacin in Enterobacterales is ≤0.25 mg/L, so an agent citing that is
  correct and the row is rejected.
- **A hedge.** "This call has low confidence", "a single gyrA mutation is the least
  certain call" — an agent marking its own uncertainty is the opposite of inventing
  a rule. These are not in the sheet, but if one appears, reject it.

Confirm a row when the agent states a determinant, a value or an action that is not
supported by anything it produced or by the source it names. An overstatement that
is not an invention — a range described as entirely below a threshold when part of
it is above — is `rejected` with a note, not `confirmed`; the manuscript reports
those separately as reasoning imprecision.

## After both readers finish

1. Record both sets of verdicts unchanged. Do not reconcile them first.
2. Compute Cohen's κ between the readers.
3. Resolve each disagreement by discussion, and record which way it went and why.
4. Only then open the key and attribute the confirmed findings to their arms.

Claude is one of the evaluated arms, so no model adjudicates this study's findings
as the primary method. A model's reading may be recorded afterwards as an
exploratory comparison with the human verdicts, never in place of them.
