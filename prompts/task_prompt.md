# Task prompt (identical for every agent arm)

> Frozen together with PROTOCOL.md. Do not edit after the `protocol-v1.0` tag.

---

You are working in a Linux environment without internet access. The directory `/data/genomes/` contains genome assemblies (FASTA) of bacterial clinical isolates, one file per isolate, named `ISO_###.fasta`. All isolates are *Escherichia coli*.

The file `/data/antibiotics.txt` lists the antibiotics, one per line.

For **every isolate and every antibiotic**, predict whether the isolate is **Susceptible (S)** or **Resistant (R)**, using only the genome sequence. Pre-installed bioinformatics tools and databases are available. List them with `ls /opt/tools` and check each tool's version.

Write your predictions to `/output/predictions.tsv` with exactly these tab-separated columns and a header row:

```
isolate_id	antibiotic	prediction	evidence
```

- `prediction` must be `S`, `R`, or `NA` (only if you cannot make a call).
- `evidence` is a short free-text justification: the gene(s) or mutation(s) that drive the call, or "no determinant found".

Also write `/output/methods.md` describing exactly which tools, versions, databases and parameters you used, and how you translated genotypes into S/R calls.

Do not ask questions. Work until the files are complete.
