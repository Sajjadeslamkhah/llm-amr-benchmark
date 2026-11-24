# Archive

The study's primary output, copied here by `scripts/arsiv.py` so that git tracks it.
Every file is listed in `MANIFEST.tsv` with its SHA-256 and byte count; that manifest is
what a reader verifies against.

Two things are deliberately absent. Anything whose name contains "key", because the
blinding key and the adjudication key resolve which arm produced which row and the
adjudication is not finished. And the reference phenotypes, which stay outside this tree
because the agents run inside it — replicate 4 was run after the freeze, so a scored run
that could read the answers is a live risk and not a historical one. The phenotypes are
published with the Zenodo deposit at submission.

Files above the per-file size limit are named in the script's output and go to Zenodo
rather than here. Genome FASTA copies under each batch workspace are left out as well:
they are copies of public BV-BRC assemblies and `data/MANIFEST.tsv` already identifies
each one by genome id and checksum.

This directory exists because `results/audit/` vanished twice during the work, both times
unnoticed, and the sheet one adjudicator had already worked from was lost with it.
