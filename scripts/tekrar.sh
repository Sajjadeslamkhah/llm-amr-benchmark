#!/usr/bin/env bash
# Reproducibility replicates: the 40-isolate subset, replicates 2 and 3 for each arm.
#
# Replicate 1 is the corresponding part of the full run (PROTOCOL.md section 8), so only
# two more per arm are needed. They run one after another, never two at once: two agents
# sharing four cores slow each other down and make the wall-clock outcome incomparable.
#
# The model identity is recorded BEFORE each run. The full runs did not do this and the
# GPT arm's serving model is consequently unknown, which is also what cost the Gemini arm.
#
# The default model is used, not a pinned one, because replicate 1 ran on the default and
# the three replicates have to be comparable with each other. The harness version and
# whatever the CLI reports are captured per replicate instead.
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/miniforge3/bin/python}"
export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"

ARMS="${ARMS:-claude gpt}"
REPS="${REPS:-2 3}"
SUB="data/selection/reproducibility_subset.txt"
[ -f "$SUB" ] || { echo "Alt kume dosyasi yok: $SUB"; exit 1; }
echo "=== baslangic $(date), alt kume $(wc -l < "$SUB" | tr -d ' ') izolat"

bekle() {
  while :; do
    n=$(pgrep -f "05_run_agent.py --arm" 2>/dev/null | grep -v -w "$$" | wc -l | tr -d ' ')
    [ "${n:-0}" -eq 0 ] && return
    echo "--- baska bir ajan calisiyor ($n), bekleniyor ... $(date)"
    sleep 120
  done
}

for kol in $ARMS; do
  for rep in $REPS; do
    dir="runs/$kol/rep$rep"
    satir=0
    [ -f "$dir/predictions.tsv" ] && satir=$(( $(wc -l < "$dir/predictions.tsv") - 1 ))
    if [ "$satir" -ge 240 ]; then          # 40 izolat x 6 antibiyotik
      echo "=== $kol rep$rep zaten tamam ($satir/240)"
      continue
    fi
    bekle
    mkdir -p "$dir"
    {
      echo "# Recorded $(date -u +%Y-%m-%dT%H:%M:%SZ) before $kol rep$rep"
      case "$kol" in
        claude) claude --version 2>&1 | head -2 ;;
        gpt)    codex --version 2>&1 | head -2 ;;
      esac
      echo "# model: the harness default; see events.jsonl where the harness records it"
    } > "$dir/harness.txt" 2>&1
    for gecis in 1 2 3; do
      echo "=== $kol rep$rep gecis $gecis  $(date)"
      "$PY" scripts/05_run_agent.py --arm "$kol" --rep "$rep" --isolates subset
      satir=0
      [ -f "$dir/predictions.tsv" ] && satir=$(( $(wc -l < "$dir/predictions.tsv") - 1 ))
      echo "--- $kol rep$rep: $satir / 240 satir"
      [ "$satir" -ge 240 ] && break
      echo "--- eksik, 3 dakika sonra yeniden"
      sleep 180
    done
  done
done

echo
echo "=== ozet $(date)"
for kol in $ARMS; do
  for rep in 1 $REPS; do
    f="runs/$kol/rep$rep/predictions.tsv"
    [ -f "$f" ] && echo "  $kol rep$rep: $(( $(wc -l < "$f") - 1 )) satir"
  done
done
echo "=== bitti $(date)"
