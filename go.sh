#!/usr/bin/env bash
# Short entry points for the steps run on the investigator workstation.
#   bash go.sh vocab     AMRFinderPlus class/subclass vocabulary
#   bash go.sh fetch     download laboratory AMR records
#   bash go.sh select    select isolates and download genomes
#   bash go.sh test      run the unit tests
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
