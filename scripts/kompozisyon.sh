#!/usr/bin/env bash
# Composition control for the GPT drift observation (post-hoc; PROTOCOL.md section 12).
#
# Why this run exists
# -------------------
# The manuscript reported that 8 isolate-antibiotic pairs moved between GPT's replicate 1
# and its replicates 2 and 3, and attributed the move to a change behind a fixed harness
# version string. The methods said the prompt, isolates and batching were identical. The
# batching was NOT identical:
#
#   replicate 1   is the corresponding slice of the full run, so each of the 40 subset
#                 isolates sat in a batch of 10 mixed with the other 78 isolates
#   replicates 2,3  ran --isolates subset, so each sat in a batch of 10 subset-only isolates
#
# Batch SIZE was the same; batch MEMBERSHIP was not. For a system whose output depends on
# session context that is a first-order alternative explanation for the move, and it also
# predicts a direction, since replicate 1's companions differ systematically.
#
# This run holds composition at replicate 1's value and moves only the date. select_genomes()
# is sorted(glob) and therefore deterministic, so --isolates all reproduces replicate 1's
# batch membership exactly.
#
#   agrees with reps 2,3  ->  composition is not the explanation; the change is temporal
#   agrees with rep 1     ->  composition is the explanation; the drift claim is withdrawn
#
# The Claude arm runs as the control: it was stable across its three replicates, so if
# composition drove the GPT move, Claude should be unaffected here too.
#
# What this run is NOT
# --------------------
# It is not a reproducibility replicate and it enters no pre-registered analysis. It lives
# in rep4 only because the frozen runner builds its path from --rep; scripts/kompozisyon_analiz.py
# is the only analysis that reads it. reproducibility.py keeps --reps 1,2,3.
#
# Failed attempts are preserved here, unlike scripts/tekrar.sh, which let the runner
# overwrite events.jsonl and stdout.txt of an attempt that produced nothing. A batch with no
# predictions is archived as batch_###_attemptNN before the next pass, so the retry count and
# every attempt's command log survive for the audit.
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/miniforge3/bin/python}"
export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"

ARMS="${ARMS:-claude gpt}"
REP="${REP:-4}"
HEDEF=708                      # 118 izolat x 6 antibiyotik

echo "=== kompozisyon kontrolu, baslangic $(date)"
echo "=== kollar: $ARMS, rep$REP, tum izolatlar (rep1 ile ayni parti bilesimi)"

bekle() {
  while :; do
    n=$(pgrep -f "05_run_agent.py --arm" 2>/dev/null | grep -v -w "$$" | wc -l | tr -d ' ')
    [ "${n:-0}" -eq 0 ] && return
    echo "--- baska bir ajan calisiyor ($n), bekleniyor ... $(date)"
    sleep 120
  done
}

# Ciktisi olmayan parti dizinlerini arsivle, silme. Yeniden deneme sayisini basar.
arsivle() {
  local dir="$1" pass="$2" n=0
  for b in "$dir"/batch_[0-9][0-9][0-9]; do
    [ -d "$b" ] || continue
    if [ ! -f "$b/workspace/output/predictions.tsv" ]; then
      mv "$b" "${b}_attempt$(printf '%02d' "$pass")"
      n=$((n + 1))
    fi
  done
  [ "$n" -gt 0 ] && echo "--- gecis $pass: ciktisi olmayan $n parti arsivlendi"
  return 0
}

for kol in $ARMS; do
  dir="runs/$kol/rep$REP"
  satir=0
  [ -f "$dir/predictions.tsv" ] && satir=$(( $(wc -l < "$dir/predictions.tsv") - 1 ))
  if [ "$satir" -ge "$HEDEF" ]; then
    echo "=== $kol rep$REP zaten tamam ($satir/$HEDEF)"
    continue
  fi
  bekle
  mkdir -p "$dir"
  {
    echo "# Recorded $(date -u +%Y-%m-%dT%H:%M:%SZ) before $kol rep$REP (composition control)"
    case "$kol" in
      claude) claude --version 2>&1 | head -2 ;;
      gpt)    codex --version 2>&1 | head -2 ;;
    esac
    echo "# model: the harness default, as in replicates 1-3; the event stream records what was served"
  } > "$dir/harness.txt" 2>&1

  for gecis in 1 2 3; do
    [ "$gecis" -gt 1 ] && arsivle "$dir" $((gecis - 1))
    echo "=== $kol rep$REP gecis $gecis  $(date)"
    "$PY" scripts/05_run_agent.py --arm "$kol" --rep "$REP" --isolates all
    satir=0
    [ -f "$dir/predictions.tsv" ] && satir=$(( $(wc -l < "$dir/predictions.tsv") - 1 ))
    echo "--- $kol rep$REP: $satir / $HEDEF satir"
    [ "$satir" -ge "$HEDEF" ] && break
    echo "--- eksik, 5 dakika sonra yeniden"
    sleep 300
  done
  echo "--- $kol yeniden denenen parti sayisi: $(ls -d "$dir"/batch_*_attempt* 2>/dev/null | wc -l | tr -d ' ')"
done

echo
echo "=== ozet $(date)"
for kol in $ARMS; do
  f="runs/$kol/rep$REP/predictions.tsv"
  [ -f "$f" ] && echo "  $kol rep$REP: $(( $(wc -l < "$f") - 1 )) / $HEDEF satir, yeniden deneme $(ls -d runs/$kol/rep$REP/batch_*_attempt* 2>/dev/null | wc -l | tr -d ' ')"
done
echo
echo "=== uc yonlu karsilastirma"
"$PY" scripts/kompozisyon_analiz.py || echo "analiz basarisiz; elle calistir: python scripts/kompozisyon_analiz.py"
echo "=== bitti $(date)"
