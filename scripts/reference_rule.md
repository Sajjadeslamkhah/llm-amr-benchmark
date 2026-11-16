# Reference arm (REF): AMRFinderPlus genotype-to-phenotype rule

Frozen with PROTOCOL.md. This rule is deliberately simple and transparent, because it is the reference arm, not an optimised predictor. Its limitations are listed at the end and reported in the manuscript.

## Versions

AMRFinderPlus software 4.2.7, database 2026-10-29.1 (installed 2026-11-14; see `runs/amrfinderplus/VERSIONS.txt`). The same build and database are used for this arm and inside every agent container.

## Command

```
amrfinder -n ISO_###.fasta --organism Escherichia --plus --threads 4 -o ISO_###.amrfinder.tsv
```

`--organism Escherichia` is required: it enables the point-mutation screen (`AMR_DNA-Escherichia.tsv`), which is where most fluoroquinolone resistance in *E. coli* is detected. Without it, ciprofloxacin determinants are largely missed.

## Vocabulary

The rule is written against the `Class` and `Subclass` values of the installed database, verified on 2026-11-14 with `scripts/inspect_amrfinder_db.py` (output: `data/summary/amrfinder_vocab.txt`, not committed; regenerate with `bash go.sh vocab`). Among 43 distinct classes in `fam.tsv` rows with `type = AMR`:

- `BETA-LACTAM` (459 rows) has 6 subclasses: `BETA-LACTAM` (211), `CARBAPENEM` (135), `CEPHALOSPORIN` (97), `METHICILLIN` (13), `CEPHALOTHIN` (2), `CEFTAROLINE/METHICILLIN` (1).
- `AMINOGLYCOSIDE` (291 rows) has 25 subclasses; gentamicin appears in 11 of them, usually combined with other agents (e.g. `GENTAMICIN/KANAMYCIN/TOBRAMYCIN`).
- `QUINOLONE` (12 rows) has one subclass, `QUINOLONE`. Quinolone also appears inside four combined classes, e.g. `AMINOGLYCOSIDE/QUINOLONE`.
- `TRIMETHOPRIM` (68 rows) and `SULFONAMIDE` (8 rows) each have a single subclass of the same name.

## Rule

Only rows with `Element type = AMR` are considered; `STRESS` and `VIRULENCE` rows are ignored. Point mutations (`Element subtype = POINT`) count the same as acquired genes. Matching is case-insensitive on whole, slash-separated tokens: `GENTAMICIN` matches the subclass `GENTAMICIN/TOBRAMYCIN` but not a substring of another word.

An isolate is called **R** for an antibiotic if at least one reported element satisfies its condition below; otherwise **S**.

| Antibiotic | Condition |
|---|---|
| ampicillin | `Class` contains the token `BETA-LACTAM` |
| cefotaxime | `Subclass` contains `CEPHALOSPORIN` or `CARBAPENEM` |
| meropenem | `Subclass` contains `CARBAPENEM` |
| ciprofloxacin | `Class` or `Subclass` contains `QUINOLONE` |
| gentamicin | `Subclass` contains `GENTAMICIN` |
| trimethoprim-sulfamethoxazole | at least one element with `TRIMETHOPRIM` **and** at least one with `SULFONAMIDE`, in `Class` or `Subclass` |

### Pre-specified decisions

These are choices, not facts, and are fixed before any run:

1. **Generic subclasses do not imply R for a specific agent.** The subclass `BETA-LACTAM` (211 rows, mostly narrow-spectrum penicillinases such as blaTEM-1) makes ampicillin R but not cefotaxime or meropenem. The subclass `AMINOGLYCOSIDE` (71 rows) does not make gentamicin R, because it does not state that gentamicin is affected. This is the conservative reading, and it will produce some very major errors; those are reported, not corrected after the fact.
2. **Any quinolone determinant makes ciprofloxacin R**, including a single *gyrA* mutation. Clinically, one mutation often leaves an isolate susceptible, so this rule is expected to over-call resistance. The simpler rule is kept because the reference arm must be reproducible without expert judgement.
3. **Trimethoprim-sulfamethoxazole requires both components**, since the combination retains activity when only one is compromised.

## Known limitations of this arm

- It uses presence of determinants only: no copy number, no promoter or expression context, no efflux up-regulation.
- Decisions 1 and 2 above trade accuracy for transparency in opposite directions, so this arm is a reproducible baseline, not a ceiling for what genotypic prediction can achieve.
- It is not a clinical tool and is not presented as one.

## Known failure, found on 2026-11-16 after the rule was applied

**Ampicillin: the rule is degenerate in *E. coli*.** `"BETA-LACTAM" in class` matches a
beta-lactamase of any kind, and nearly every *E. coli* genome carries one, so the rule calls
ampicillin resistant almost unconditionally. In this benchmark it called all 26 phenotypically
susceptible isolates resistant: major error 26/26 = 100%, with no very major errors because it
called nothing susceptible.

The rule was pre-registered and frozen before any scored run, so it stays as the primary
reference arm and this result is reported as it came out. Changing it now, after seeing the
numbers, would be a post-hoc revision and would cost more in credibility than the arm is worth.

What this does and does not show:

- It is a property of class-level mapping, not of AMRFinderPlus. AMRFinderPlus reports the
  determinants it finds; it does not claim to predict a phenotype, and it is not responsible
  for this rule.
- So no comparison in this study supports "the agents outperform AMRFinderPlus". The arm the
  agents are compared against is this rule applied to AMRFinderPlus output, and that is how
  every comparison must be worded.
- Ciprofloxacin shows a milder form of the same thing (major error 30.6%): any quinolone
  determinant is taken as resistance, although a single gyrA substitution need not reach a
  clinical breakpoint.
- A sensitivity analysis with a stricter mapping may be reported, labelled post-hoc and
  exploratory, never in place of the frozen rule.

