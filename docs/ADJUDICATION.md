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

The screen is deliberately broad, so most candidates are expected to be rejected. The
categories below say what to check. **Verify each row yourself**; this list names the
kinds of false positive the screen produces, not the verdict for any particular row.

- **A real determinant under another name.** Most resistance genes carry two or three
  names in the literature and the AMRFinderPlus catalogue uses one of them. Absence from
  this catalogue is not evidence of invention. Search the name in NCBI Gene or Google
  Scholar; if it is a described resistance determinant, reject it and note the name you
  found it under.
- **An operon or family name** where the catalogue lists the members separately. Check
  the same way.
- **A qualified name**, ending in `-like`, `-type`, `-family` or `-promoter`. Strip the
  qualifier and search the stem.
- **A correct guideline value.** Check the number yourself against the guideline the
  agent names, at the version the manuscript cites. If the sentence describes a range,
  judge the whole range.
- **A hedge.** An agent marking its own call as uncertain is the opposite of inventing a
  rule.

Confirm a row when the agent states a determinant, a value or an action that is not
supported by anything it produced or by the source it names. An overstatement that is not
an invention — a range described as entirely below a threshold when part of it is above —
is `rejected` with a note, not `confirmed`.

## After both readers finish

1. Record both sets of verdicts unchanged. Do not reconcile them first.
2. Compute Cohen's κ between the readers.
3. Resolve each disagreement by discussion, and record which way it went and why.
4. Only then open the key and attribute the confirmed findings to their arms.

Claude is one of the evaluated arms, so no model adjudicates this study's findings
as the primary method. A model's reading may be recorded afterwards as an
exploratory comparison with the human verdicts, never in place of them.
