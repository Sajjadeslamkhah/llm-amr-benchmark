# Protocol freeze — v1.0

Frozen on 2026-11-15 (Europe/Istanbul), before any scored agent run.

Everything below was fixed before a single prediction was compared with a phenotype.
From this point on, every change to the protocol is recorded in PROTOCOL.md section 12
with its date and reason.

## What had already happened

- Data downloaded, isolates selected, genomes fetched (118 of 120 passed assembly QC).
- The reproducibility subset of 40 isolates was drawn with SEED 20261114, from the blinded
  isolate codes only, before any run.
- Pilot runs of 3 isolates per agent confirmed each harness starts, works and writes a
  predictions file (Claude 874 s, Gemini 1164 s, GPT 804 s). Pilot output is discarded and
  is not part of any analysis.

## What had NOT happened

- No agent prediction has been compared with a reference phenotype.
- No accuracy, error rate or hallucination count has been computed or looked at.

## SHA-256 of the frozen files

    3be83e26d05040452bc2d10113325ee92639f9cadaff9ea7a65f44b30b420220  PROTOCOL.md
    2713ffb1051dfc34ef0d35970b224137f89ddea4679a90e952cc972e40c79135  prompts/task_prompt.md
    eb8641892a8282b4d1c89d711f4af7afe4cab750f21d55734cff35d62e10a50f  scripts/reference_rule.md
    e89cdbe48e196b2a52e6dcb8665df8fec1fcdf1727f885de7816633e1f768901  scripts/01_fetch_amr.py
    cc340e9d434a910ac9be1c30df4e117cbbbf02c4a4136d76c37a253b87a224ef  scripts/02_select_isolates.py
    c2055388b3cc9a13a404caf9d829cbdda515198900e8eab62362d933e340deeb  scripts/03_fetch_genomes.py
    aedf41ea7ac6bea0d8c059e1674df6fc8c39d033fc7533fe1a9bb3e6a356cb0d  scripts/04_reference_arm.py
    51c3178f3fdad2463a3ca0ead40c6e29602789b0aab321eb7bcd769380b90e2f  scripts/05_run_agent.py
    61a2eeec4bfbdd7e0c6f048c7e9db05a35c1d1dfccb1f470bbacc14b97b85795  scripts/make_subset.py
    7249cc2695df0dd729c10bc58f416178b6381943cf095ab4a0668641841cf4d0  scripts/metrics.py
    7ce474165ea8453d9c2b7b8b91d3b761de7f3beba2d16d48c9117dcf23f072a5  scripts/hallucination_audit.py
    (missing)  data/selection/reproducibility_subset.txt

Verify with:

    shasum -a 256 PROTOCOL.md prompts/task_prompt.md scripts/reference_rule.md ...


---

## Addendum — 2026-11-15, same day, before any scored run

`data/selection/reproducibility_subset.txt` was recorded as `(missing)` above: it had been drawn on
the investigator's workstation and was not yet in the repository when FREEZE.md was written. The file
is now committed. It was reproduced byte for byte from `scripts/make_subset.py`
(`SEED = 20261114`, 40 of the 118 blinded isolate codes) and the first eight entries match what the
workstation printed when the subset was drawn: ISO_004, ISO_009, ISO_016, ISO_017, ISO_020, ISO_024,
ISO_025, ISO_028.

    baa795af815c37989b33033a840d5aa80b57e1fa252a3b3d3722a8efa71419c0  data/selection/reproducibility_subset.txt

Anyone can regenerate it and check the hash:

    python scripts/make_subset.py

Still true at the time of this addendum: no agent prediction has been compared with a reference
phenotype, and no accuracy, error rate or hallucination count has been computed.
