# Task prompt (identical for every agent arm)

> Frozen together with PROTOCOL.md. Do not edit after the `protocol-v1.0` tag.
> Paths are relative to the agent's working directory, which the runner sets
> to the run's `workspace/`.

---

You are working in a Linux/macOS shell. The directory `data/genomes/` contains genome assemblies (FASTA) of bacterial clinical isolates, one file per isolate, named `ISO_###.fasta`. All isolates are *Escherichia coli*.

The file `data/antibiotics.txt` lists the antibiotics, one per line.

For **every isolate and every antibiotic**, predict whether the isolate is **Susceptible (S)** or **Resistant (R)**, using only the genome sequence. Bioinformatics tools and databases are already installed; find out what is available and check each tool's version before you use it. You have no internet access, so do not try to download anything.

Write your predictions to `output/predictions.tsv` with exactly these tab-separated columns and a header row:

```
isolate_id	antibiotic	prediction	evidence
```

- `isolate_id` is the file name without `.fasta`, e.g. `ISO_001`.
- `antibiotic` is the exact string from `data/antibiotics.txt`.
- `prediction` must be `S`, `R`, or `NA` (only if you cannot make a call).
- `evidence` is a short free-text justification: the gene(s) or mutation(s) that drive the call, or "no determinant found".

Also write `output/methods.md` describing exactly which tools, versions, databases and parameters you used, and how you translated genotypes into S/R calls.

Do not ask questions. Work until both files are complete.
