#!/usr/bin/env bash
# Short entry points for the steps run on the investigator workstation.
#   bash go.sh vocab     AMRFinderPlus class/subclass vocabulary
#   bash go.sh fetch     download laboratory AMR records
#   bash go.sh select    select isolates and download genomes
#   bash go.sh harness   collect CLI help output for the three agents
#   bash go.sh test      run the unit tests
#   bash go.sh pilot [claude|gemini|gpt]   pilot run on 3 isolates (discarded)
#   bash go.sh run <arm> <rep> [max batches]  real run, resumable, in the background
#   bash go.sh pilotall  pilot all three arms overnight, in the background
#   bash go.sh events   summarise the pilot event streams
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
    rm -rf "runs/$arm/rep0"
    "$PY" scripts/05_run_agent.py --arm "$arm" --rep 0 --pilot 3 --batch-size 3 --timeout 2400
    ;;
  run)
    # bash go.sh run <claude|gemini|gpt> <replicate> [max batches this sitting]
    export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
    arm="${2:?arm required}"; rep="${3:?replicate required}"; maxb="${4:-}"
    extra=""; [ -n "$maxb" ] && extra="--max-batches $maxb"
    log="runs/run_${arm}_rep${rep}_$(date +%Y%m%d_%H%M).log"
    echo "Running $arm replicate $rep. Log: $log"
    echo "Leave the Mac plugged in, lid open. Safe to rerun: finished batches are skipped."
    caffeinate -dimsu "$PY" scripts/05_run_agent.py --arm "$arm" --rep "$rep" $extra > "$log" 2>&1 &
    echo "Started in the background (pid $!). You can close the Terminal window."
    ;;
  pilotall)
    export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
    mkdir -p runs
    log="runs/pilot_$(date +%Y%m%d_%H%M).log"
    echo "Pilot of all three arms. Log: $log"
    echo "Leave the Mac plugged in, lid open. Check the log in the morning."
    caffeinate -dimsu bash -c '
      for arm in claude gemini gpt; do
        echo "=================== $arm $(date)"
        '"$PY"' scripts/05_run_agent.py --arm "$arm" --rep 0 --pilot 3 --timeout 2400 --force || echo "ARM $arm FAILED"
      done
      echo "=================== done $(date)"
    ' > "$log" 2>&1 &
    echo "Started in the background (pid $!). You can close the Terminal window."
    ;;
  events)
    "$PY" scripts/inspect_events.py runs/claude/rep0 runs/gemini/rep0 > data/summary/events_pilot.txt 2>&1
    echo "--- gpt error ---" >> data/summary/events_pilot.txt
    head -40 runs/gpt/rep0/stdout.txt >> data/summary/events_pilot.txt 2>&1 || true
    wc -l data/summary/events_pilot.txt
    echo "Send me: data/summary/events_pilot.txt"
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
