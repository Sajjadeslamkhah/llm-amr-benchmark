#!/usr/bin/env bash
# Waits for the replicates to finish, then computes everything that does not need a
# person: reproducibility, the performance table, the hallucination screen, the blinded
# adjudication sheet, the uncertainty analysis and the run provenance.
#
# Safe to start while the replicates are still running. Nothing here consumes agent
# quota; it only reads files already on disk.
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/miniforge3/bin/python}"
export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
GIZLI="${GIZLI:-$HOME/amr_gizli}"
ARMS="${ARMS:-claude gpt}"
REF="$GIZLI/reference_phenotypes.tsv"
KEY="$GIZLI/blinding_key.tsv"

echo "=== baslangic $(date)"
[ -f "$REF" ] || { echo "Bulunamadi: $REF"; exit 1; }

# Wait for any agent still running. The replicates take hours; this loop costs nothing.
while :; do
  n=$(pgrep -f "05_run_agent.py --arm" 2>/dev/null | grep -v -w "$$" | wc -l | tr -d ' ')
  [ "${n:-0}" -eq 0 ] && break
  echo "--- ajan calisiyor ($n), bekleniyor ... $(date)"
  sleep 300
done
echo "=== ajan kalmadi, analizlere geciliyor $(date)"

mkdir -p results/audit

echo
echo "########## 1. tekrarlanabilirlik"
args=()
for kol in $ARMS; do args+=(--arm "$kol"); done
"$PY" scripts/reproducibility.py "${args[@]}" --ref "$REF" --key "$KEY" \
  --out results/reproducibility.tsv || echo "(tekrarlanabilirlik tamamlanamadi, yukariya bakin)"

echo
echo "########## 2. performans tablosu"
bash go.sh analiz || echo "(analiz tamamlanamadi)"

echo
echo "########## 3. uydurma denetimi"
bash go.sh uydurma || echo "(uydurma denetimi tamamlanamadi)"

echo
echo "########## 4. korleme degerlendirme sayfasi"
bash go.sh hakem || echo "(sayfa uretilemedi)"

echo
echo "########## 5. belirsizlik analizi (post-hoc)"
bash go.sh belirsizlik || echo "(belirsizlik analizi tamamlanamadi)"

echo
echo "########## 6. kosu kokeni"
bash go.sh koken || echo "(koken toplanamadi)"

echo
echo "########## 7. korleme sizintisi denetimi"
bash go.sh sizinti || true     # icerik bulursa 1 doner, bu bir hata degil

echo
echo "=== ozet $(date)"
for kol in $ARMS; do
  for rep in 1 2 3; do
    f="runs/$kol/rep$rep/predictions.tsv"
    [ -f "$f" ] && echo "  $kol rep$rep: $(( $(wc -l < "$f") - 1 )) satir"
  done
done
echo
ls -1 results/*.tsv results/audit/*.tsv 2>/dev/null
echo "=== bitti $(date)"
