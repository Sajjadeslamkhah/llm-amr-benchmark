# Reference arm (REF): AMRFinderPlus genotype-to-phenotype rule

Frozen with PROTOCOL.md. This rule is intentionally simple and transparent, because it is the reference arm, not an optimised predictor.

## Command

```
amrfinder -n ISO_###.fasta --organism Escherichia --plus -o ISO_###.amrfinder.tsv
```

The AMRFinderPlus software version and database version are recorded in `runs/amrfinderplus/VERSIONS.txt`: software 4.2.7, database 2026-10-29.1 (installed 2026-11-14). The same build and database are used for the reference arm and inside every agent container.

## Rule

An isolate is called **R** for an antibiotic if AMRFinderPlus reports at least one element meeting both conditions:

- `Element type` is `AMR`, including point mutations reported with `--organism`;
- `Class`/`Subclass` maps to that antibiotic according to the table below.

Otherwise the call is **S**.

| Antibiotic | Determinants that trigger R (AMRFinderPlus Class/Subclass) |
|---|---|
| ampicillin | any BETA-LACTAM element (any subclass) |
| cefotaxime, ceftriaxone, ceftazidime | BETA-LACTAM with subclass CEPHALOSPORIN or CARBAPENEM |
| meropenem | BETA-LACTAM with subclass CARBAPENEM |
| ciprofloxacin | any QUINOLONE element |
| gentamicin | AMINOGLYCOSIDE with subclass containing GENTAMICIN |
| trimethoprim/sulfamethoxazole | ≥1 TRIMETHOPRIM element **and** ≥1 SULFONAMIDE element |

**Before the freeze:** check the Class/Subclass strings in this table against the vocabulary of the installed AMRFinderPlus database version (`ReferenceGeneCatalog.txt`), and correct any mismatch here.
