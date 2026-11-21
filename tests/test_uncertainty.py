"""The uncertain-calls parser missed exactly the lines it exists to read: both
agents wrote the calls on the heading line itself, and the parser scanned only
what came after the heading."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("u", ROOT / "scripts" / "uncertainty.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def test_calls_named_on_the_heading_line_are_found():
    got = u.listed_uncertain("## Uncertain calls - ISO_052 ciprofloxacin and ISO_103 meropenem\nnext\n")
    assert ("ISO_052", "ciprofloxacin") in got
    assert ("ISO_103", "meropenem") in got


def test_a_bullet_list_carries_the_isolate_to_the_next_line():
    got = u.listed_uncertain("### Uncertain calls\n- ISO_007\n  - ciprofloxacin: borderline\n")
    assert ("ISO_007", "ciprofloxacin") in got


def test_a_different_heading_does_not_leak_in():
    got = u.listed_uncertain("### Uncertain calls\n- ISO_007 ciprofloxacin\n## Other\n- ISO_009 meropenem\n")
    assert ("ISO_009", "meropenem") not in got


def test_tmp_smx_synonyms_collapse_to_one_name():
    assert ("ISO_011", "trimethoprim/sulfamethoxazole") in \
        u.listed_uncertain("## Uncertain calls\n- ISO_011 TMP-SMX\n")


def test_wilson_interval_brackets_the_point_estimate():
    p, lo, hi = u.wilson(1, 6)
    assert lo < p < hi
