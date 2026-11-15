#!/usr/bin/env bash
# Gözetimsiz çalışma sırası:
#   1) çalışan bir ajan varsa bitmesini bekle (iki ajan aynı anda 4 çekirdeği bölüşmesin
#      ve duvar saati süreleri karşılaştırılabilir kalsın)
#   2) eksik kolları sırayla tamamla, ağ hatasında yeniden dene
#   3) körleme bütünlüğü denetimini çalıştır
#
# Ayrı bir DOSYA olarak çalışır: `bash -c '...'` içine gömülürse betiğin kendi komut
# satırında "05_run_agent.py" geçer ve aşağıdaki bekleme döngüsü kendini çalışan ajan
# sanıp sonsuza kadar bekler. (2026-11-15'te tam olarak bu oldu.)
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/miniforge3/bin/python}"
export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"

BEKLENEN=708          # 118 izolat x 6 antibiyotik
GECIS=5               # bir kol için en fazla kaç deneme

satir() {             # $1 = kol adı -> birleştirilmiş tahmin satırı sayısı
  local f="runs/$1/rep1/predictions.tsv"
  [ -f "$f" ] && echo $(( $(wc -l < "$f") - 1 )) || echo 0
}

bekle() {
  while :; do
    # kendi pid'imizi saymıyoruz; bu dosyanın argv'si sadece "bash scripts/gece.sh"
    n=$(pgrep -f "05_run_agent.py --arm" 2>/dev/null | grep -v -w "$$" | wc -l | tr -d ' ')
    [ "${n:-0}" -eq 0 ] && return
    echo "--- başka bir ajan çalışıyor ($n süreç), bekleniyor ... $(date)"
    sleep 120
  done
}

kolu_tamamla() {      # $1 = kol adı
  local kol="$1"
  if [ "$(satir "$kol")" -ge "$BEKLENEN" ]; then
    echo "=== $kol zaten tamam ($(satir "$kol")/$BEKLENEN)"
    return
  fi
  for g in $(seq 1 "$GECIS"); do
    echo "=== $kol geçiş $g  $(date)"
    "$PY" scripts/05_run_agent.py --arm "$kol" --rep 1
    echo "--- $kol toplam $(satir "$kol") / $BEKLENEN satır"
    if [ "$(satir "$kol")" -ge "$BEKLENEN" ]; then
      echo "=== $kol tamam"
      return
    fi
    echo "--- eksik kaldı, 3 dakika sonra yeniden denenecek"
    sleep 180
  done
  echo "=== $kol $GECIS geçişte tamamlanamadı, elle bakılmalı"
}

echo "=== başlangıç $(date)"
bekle
for kol in gpt gemini claude; do
  kolu_tamamla "$kol"
done

echo "=== körleme denetimi $(date)"
"$PY" scripts/leak_check.py

echo
echo "=== özet $(date)"
for kol in claude gemini gpt; do
  echo "  $kol : $(satir "$kol") / $BEKLENEN satır"
done
echo "=== bitti $(date)"
