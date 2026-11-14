# llm-amr-benchmark

**Can Large Language Model Agents Predict Antimicrobial Resistance from Bacterial Genomes? A Benchmark of Accuracy and Hallucination Against Phenotypic Susceptibility Testing**

This benchmark compares three autonomous LLM agents, **Claude** (Anthropic), **Gemini** (Google) and **GPT** (OpenAI), against a rule-based **AMRFinderPlus** reference arm. Each predicts susceptible/resistant calls for *Escherichia coli* from genome assemblies, and the calls are scored against laboratory phenotypes from BV-BRC.

The study is pre-registered: see [`PROTOCOL.md`](PROTOCOL.md). The protocol is binding from the `protocol-v1.0` tag onward.

## Status

| Step | State |
|---|---|
| Protocol draft | ✅ v0.1 |
| Protocol freeze (`protocol-v1.0` tag) | ⏳ |
| Data download | ⏳ |
| Agent runs | ⏳ |
| Analysis | ⏳ |
| Manuscript | ⏳ |

**No results exist yet.** Every number in the future manuscript will be produced by `scripts/metrics.py` from the files in `runs/`.

## Layout

```
PROTOCOL.md              pre-registered study protocol
prompts/task_prompt.md   identical task given to every agent
scripts/
  01_fetch_amr.py        BV-BRC phenotype download (needs internet)
  02_select_isolates.py  eligibility + antibiotic rule + seeded sampling
  03_fetch_genomes.py    assembly download, QC, anonymisation
  reference_rule.md      AMRFinderPlus reference-arm rule
  metrics.py             CA / VME / ME, Wilson CIs, McNemar, Fleiss kappa
tests/                   unit tests for metrics.py (synthetic toy data)
data/                    downloaded data (raw files not committed)
sandbox/                 the only files the agents see
runs/                    agent transcripts, logs, predictions
results/                 script-generated tables and figures
```

## Workflow

```bash
pip install -r requirements.txt
python scripts/01_fetch_amr.py                        # then fix the evidence string in PROTOCOL.md §4
python scripts/02_select_isolates.py --evidence "<exact string>"
python scripts/03_fetch_genomes.py
git tag protocol-v1.0 && git push --tags             # freeze BEFORE any agent run
```

## Integrity rules

1. No number is typed by hand. All numbers come from scripts.
2. The reference phenotypes and the blinding key never enter the agent sandbox.
3. Every agent transcript is archived unedited.
4. Every reference is checked against PubMed or its DOI.
