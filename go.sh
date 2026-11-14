#!/usr/bin/env bash
# Short entry points for the steps run on the investigator workstation.
#   bash go.sh vocab     AMRFinderPlus class/subclass vocabulary
#   bash go.sh fetch     download laboratory AMR records
#   bash go.sh select    select isolates and download genomes
#   bash go.sh harness   collect CLI help output for the three agents
#   bash go.sh test      run the unit tests
#   bash go.sh pilot [claude|gemini|gpt]   pilot run on 3 isolates (discarded)
#   bash go.sh ref       run the AMRFinderPlus reference arm (after the freeze)
#   bash go.sh update    git pull
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-$HOME/miniforge3/bin/python}"
DB="${AMRFINDER_DB:-$HOME/miniforge3/envs/amr/share/amrfinderplus/data/2026-10-29.1}"

case "${1:-}" in
  vocab)
    mkdir -p data/summary
    "$PY" scripts/inspect_amrfinder_db.py "$DB" > data/summary/amrfinder_vocab.txt
    sed -n '/type=AMR rows/,$p' data/summary/amrfinder_vocab.txt
    ;;
  fetch)
    "$PY" scripts/01_fetch_amr.py
    ;;
  select)
    "$PY" scripts/02_select_isolates.py --evidence "Laboratory Method"
    "$PY" scripts/03_fetch_genomes.py
    ;;
  pilot)
    export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
    arm="${2:-claude}"
    "$PY" scripts/05_run_agent.py --arm "$arm" --rep 0 --pilot 3 --timeout 1800
    ;;
  ref)
    source "$HOME/miniforge3/etc/profile.d/conda.sh" && conda activate amr
    "$PY" scripts/04_reference_arm.py
    ;;
  harness)
    mkdir -p data/summary
    # npm-installed CLIs live in the base env, not in the amr env
    export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
    out=data/summary/harness_help.txt
    : > "$out"
    for c in "which claude codex agy" "codex --help" "codex exec --help" "codex login status"; do
      echo "########## $c" >> "$out"
      sh -c "$c" >> "$out" 2>&1 || echo "(command failed)" >> "$out"
      echo >> "$out"
    done
    for f in "$HOME/.claude/settings.json" "$HOME/.codex/config.toml" "$HOME/.antigravity/config.json" "$HOME/.agy/config.json"; do
      echo "########## exists? $f" >> "$out"
      [ -f "$f" ] && echo "yes" >> "$out" || echo "no" >> "$out"
    done
    wc -l "$out"
    echo "Send me: $out"
    ;;
  test)
    "$PY" -m pytest -q tests
    ;;
  update)
    git pull
    ;;
  *)
    sed -n '2,8p' "$0"
    exit 1
    ;;
esac
