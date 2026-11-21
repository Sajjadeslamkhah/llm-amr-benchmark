#!/usr/bin/env bash
# Short entry points for the steps run on the investigator workstation.
#   bash go.sh vocab     AMRFinderPlus class/subclass vocabulary
#   bash go.sh fetch     download laboratory AMR records
#   bash go.sh select    select isolates and download genomes
#   bash go.sh harness   collect CLI help output for the three agents
#   bash go.sh test      run the unit tests
#   bash go.sh pilot [claude|gemini|gpt]   pilot run on 3 isolates (discarded)
#   bash go.sh subset   draw the 40-isolate reproducibility subset (once)
#   bash go.sh freeze   tag protocol-v1.0 after the tests pass
#   bash go.sh durum   calisan var mi, kac grup bitti, son log
#   bash go.sh run <arm> <rep> [max batches]  real run, resumable, in the background
#   bash go.sh pilotall  pilot all three arms overnight, in the background
#   bash go.sh events   summarise the pilot event streams
#   bash go.sh bitir    tekrar koslari bitince tum analizleri sirayla calistir
#   bash go.sh tekrar   tekrarlanabilirlik: 40 izolatlik alt kumede rep2 ve rep3
#   bash go.sh gece     gozetimsiz: GPT bitince Gemini, tekrar denemeli, sonra sizinti denetimi
#   bash go.sh duyarlilik  on belirlenmis duyarlilik analizleri (ara fenotip, test standardi)
#   bash go.sh analiz  tamamlanmis kollar icin tum sayilari hesapla (results/)
#   bash go.sh uydurma  uydurma (hallusinasyon) denetimi: aday bulgulari cikar
#   bash go.sh belirsizlik  ajanin kendi belirsizlik isareti hatalarini yakaliyor mu (post-hoc)
#   bash go.sh kontrol  referans ciftleri korleme anahtarina baglaniyor mu
#   bash go.sh surum    KOSUDAN ONCE: harness surumu ve model kimligini kaydet
#   bash go.sh koken    her kolun model kimligi, harness surumu, tarih, sure, web sayaclari
#   bash go.sh paket    okuyucuya gonderilecek zip (sayfa + talimat; anahtar HARIC)
#   bash go.sh hakem    korleme degerlendirme sayfasi (iki bagimsiz okuyucu icin)
#   bash go.sh sizinti  ajanlar referans fenotipleri/korleme anahtarini gordu mu
#   bash go.sh ref       run the AMRFinderPlus reference arm (after the freeze)
#   bash go.sh update    git pull
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-$HOME/miniforge3/bin/python}"
# Gemini (A2) 2026-11-21'de calismadan cikarildi: Antigravity CLI cok modelli ve hangi
# modelin hizmet verdigi hicbir yerde kayitli degil (PROTOCOL.md, 12. bolum). Verisi
# repoda duruyor ama hicbir analize girmiyor.
ARMS="${ARMS:-claude gpt}"
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
  subset)
    "$PY" scripts/make_subset.py
    ;;
  freeze)
    "$PY" -m pytest -q tests || { echo "Tests failed; not freezing."; exit 1; }
    git tag -f -a protocol-v1.0 -m "Protocol frozen before any scored agent run" 2>/dev/null || true
    # Etiketi uzak depoya gönderme burada DENENMEZ: kimlik bilgisi yoksa komut şifre sorup takılıyor.
    # Donma kaydı FREEZE.md commit'idir; etiketi göndermek isterseniz: git push origin protocol-v1.0
    echo "Frozen. Marker: FREEZE.md (commit). Local tag: protocol-v1.0"
    echo "Every later change goes in PROTOCOL.md section 12."
    ;;
  durum)
    set +e                      # bu blokta hicbir eksik dosya komutu yarida kesmesin
    if pgrep -f "05_run_agent.py" >/dev/null 2>&1; then
      echo "CALISIYOR:"; pgrep -af "05_run_agent.py" | sed 's/^/   /'
    else
      echo "DURMUS (calisan ajan yok)"
    fi
    for d in runs/claude/rep* runs/gemini/rep* runs/gpt/rep*; do
      [ -d "$d" ] || continue
      biten=$(ls -d "$d"/batch_*/workspace/output/predictions.tsv 2>/dev/null | wc -l | tr -d " ")
      satir=$([ -f "$d/predictions.tsv" ] && echo $(($(wc -l < "$d/predictions.tsv") - 1)) || echo 0)
      echo "  $d : $biten grup bitti, $satir tahmin satiri"
    done
    son=$(ls -t runs/run_*.log 2>/dev/null | head -1)
    if [ -n "$son" ]; then echo; echo "son log: $son"; tail -5 "$son"; fi
    exit 0
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
  bitir)
    # Tekrar koslari bitene kadar bekler, sonra insan gerektirmeyen her seyi hesaplar.
    mkdir -p runs
    log="runs/bitir_$(date +%Y%m%d_%H%M).log"
    echo "Zincir basladi. Log: $log"
    echo "Tekrar koslari bitince analizler kendiliginden calisacak."
    PY="$PY" ARMS="$ARMS" GIZLI="${GIZLI:-$HOME/amr_gizli}" \
      caffeinate -dimsu bash scripts/bitir.sh > "$log" 2>&1 &
    echo "Arka planda calisiyor (pid $!)."
    ;;
  tekrar)
    # Tekrarlanabilirlik koslari: 40 izolatlik alt kume, her kol icin rep2 ve rep3.
    # Model kimligini kosudan ONCE kaydeder (tam kosularda bu yapilmadi).
    mkdir -p runs
    log="runs/tekrar_$(date +%Y%m%d_%H%M).log"
    echo "Tekrar koslari basladi. Log: $log"
    echo "Mac prize takili, kapagi acik kalsin. Terminali kapatabilirsiniz."
    PY="$PY" ARMS="$ARMS" caffeinate -dimsu bash scripts/tekrar.sh > "$log" 2>&1 &
    echo "Arka planda calisiyor (pid $!)."
    ;;
  gece)
    export PATH="$HOME/miniforge3/bin:$HOME/.local/bin:$PATH"
    mkdir -p runs
    log="runs/gece_$(date +%Y%m%d_%H%M).log"
    echo "Gozetimsiz calisma basladi. Log: $log"
    echo "Mac prize takili, kapagi acik kalsin. Terminali kapatabilirsiniz."
    PY="$PY" caffeinate -dimsu bash scripts/gece.sh > "$log" 2>&1 &
    echo "Arka planda calisiyor (pid $!)."
    ;;
  duyarlilik)
    GIZLI="${GIZLI:-$HOME/amr_gizli}"
    [ -f "$GIZLI/reference_phenotypes.tsv" ] || { echo "Bulunamadi: $GIZLI"; exit 1; }
    args=()
    for kol in $ARMS; do
      f="runs/$kol/rep1/predictions.tsv"
      [ -f "$f" ] && args+=(--pred "$kol=$f")
    done
    [ -f runs/amrfinderplus/predictions.tsv ] && args+=(--pred "ref=runs/amrfinderplus/predictions.tsv")
    "$PY" scripts/sensitivity.py --ref "$GIZLI/reference_phenotypes.tsv" \
      --key "$GIZLI/blinding_key.tsv" "${args[@]}" --out results/sensitivity
    ;;
  analiz)
    # Referans fenotipler ve korleme anahtari proje agacinin disinda (~/amr_gizli),
    # cunku ajanlar calisma klasorunun disini okuyabiliyordu (2026-11-15 sapmasi).
    GIZLI="${GIZLI:-$HOME/amr_gizli}"
    REF="$GIZLI/reference_phenotypes.tsv"
    KEY="$GIZLI/blinding_key.tsv"
    if [ ! -f "$REF" ] || [ ! -f "$KEY" ]; then
      echo "Bulunamadi: $REF veya $KEY"
      echo "Dosyalar baska bir yerdeyse: GIZLI=/yol/klasor bash go.sh analiz"
      exit 1
    fi
    args=()
    for kol in $ARMS; do
      f="runs/$kol/rep1/predictions.tsv"
      if [ -f "$f" ]; then
        n=$(( $(wc -l < "$f") - 1 ))
        if [ "$n" -ge 708 ]; then
          args+=(--pred "$kol=$f")
          echo "dahil: $kol ($n satir)"
        else
          echo "atlandi: $kol (sadece $n/708 satir, tamamlanmamis)"
        fi
      else
        echo "atlandi: $kol (tahmin dosyasi yok)"
      fi
    done
    if [ -f runs/amrfinderplus/predictions.tsv ]; then
      args+=(--pred "ref=runs/amrfinderplus/predictions.tsv")
      echo "dahil: ref (AMRFinderPlus)"
    else
      echo "UYARI: referans kolu yok, once: bash go.sh ref"
    fi
    if [ "${#args[@]}" -eq 0 ]; then echo "Hicbir kol hazir degil."; exit 1; fi
    echo
    "$PY" scripts/metrics.py --ref "$REF" --key "$KEY" "${args[@]}" --out results/
    ;;
  uydurma)
    # Olay akislarini denetimin bekledigi bicime cevirir, sonra mekanik uydurma
    # denetimini calistirir. Veritabani yolu: AMRFINDER_DB=... ile verilebilir.
    DB="${AMRFINDER_DB:-}"
    if [ -z "$DB" ]; then
      for c in "$HOME/miniforge3/envs/amr/share/amrfinderplus/data/latest" \
               "$HOME/miniforge3/envs/amr/share/amrfinderplus/data"/* ; do
        [ -f "$c/fam.tsv" ] && DB="$c" && break
      done
    fi
    if [ -z "$DB" ] || [ ! -f "$DB/fam.tsv" ]; then
      echo "AMRFinderPlus veritabani bulunamadi (fam.tsv aradim)."
      echo "Yolu bulmak icin:  find \$HOME -name fam.tsv 2>/dev/null | head"
      echo "Sonra:             AMRFINDER_DB=/bulunan/yol bash go.sh uydurma"
      exit 1
    fi
    echo "veritabani: $DB"
    mkdir -p results/audit
    for kol in $ARMS; do
      f="runs/$kol/rep1/predictions.tsv"
      [ -f "$f" ] || continue
      n=$(( $(wc -l < "$f") - 1 ))
      [ "$n" -ge 708 ] || { echo "atlandi: $kol ($n/708)"; continue; }
      echo
      echo "=== $kol"
      "$PY" scripts/events_to_audit.py --run "runs/$kol/rep1" || exit 1
      "$PY" scripts/hallucination_audit.py --run "runs/$kol/rep1" --catalog "$DB" \
        --out "results/audit/${kol}_rep1.tsv" || exit 1
    done
    echo
    echo "Aday bulgular: results/audit/"
    wc -l results/audit/*.tsv 2>/dev/null
    ;;
  belirsizlik)
    GIZLI="${GIZLI:-$HOME/amr_gizli}"
    [ -f "$GIZLI/reference_phenotypes.tsv" ] || { echo "Bulunamadi: $GIZLI/reference_phenotypes.tsv"; exit 1; }
    args=()
    for kol in $ARMS; do
      f="runs/$kol/rep1/predictions.tsv"
      [ -f "$f" ] || continue
      n=$(( $(wc -l < "$f") - 1 ))
      [ "$n" -ge 708 ] && args+=(--run "$kol=runs/$kol/rep1") || echo "atlandi: $kol ($n/708)"
    done
    [ "${#args[@]}" -gt 0 ] || { echo "Hicbir kol hazir degil."; exit 1; }
    "$PY" scripts/uncertainty.py --ref "$GIZLI/reference_phenotypes.tsv" \
      --key "$GIZLI/blinding_key.tsv" "${args[@]}" --out results/uncertainty.tsv
    ;;
  kontrol)
    # Her kolda hata yazilan ama aslinda hicbir kolun tahmin uretmedigi ciftler var mi:
    # metrics 560 cift goruyor, belirsizlik analizi 553. Fark bir baglama sorunuysa
    # o cesitler her kola hata olarak yaziliyor, ki bu ajan hatasi degil.
    GIZLI="${GIZLI:-$HOME/amr_gizli}"
    "$PY" - "$GIZLI" <<'PYIN'
import csv, sys
from pathlib import Path
g = Path(sys.argv[1])
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))
ref = rd(g / "reference_phenotypes.tsv")
key = rd(g / "blinding_key.tsv")
gid2iso = {r["genome_id"]: r["isolate_id"] for r in key}
missing = [r for r in ref if r["genome_id"] not in gid2iso]
print(f"referans cift sayisi : {len(ref)}")
print(f"korleme anahtarinda  : {len(ref) - len(missing)}")
print(f"anahtarda OLMAYAN    : {len(missing)}")
if missing:
    print("  genome_id'ler:", sorted({r["genome_id"] for r in missing}))
    print("  antibiyotikler:", sorted({r["abx"] for r in missing}))
for arm in ("claude", "gpt", "amrfinderplus"):
    f = Path("runs") / arm / ("rep1/predictions.tsv" if arm != "amrfinderplus" else "predictions.tsv")
    if not f.exists():
        continue
    have = {(r["isolate_id"], r["antibiotic"]) for r in rd(f) if (r.get("prediction") or "").strip() in ("S", "R")}
    want = {(gid2iso[r["genome_id"]], r["abx"]) for r in ref if r["genome_id"] in gid2iso}
    print(f"{arm:14s}: {len(want - have)} baglanabilir ciftte cagri yok")
PYIN
    ;;
  surum)
    # Model kimligi ve harness surumunu KOSUDAN ONCE kaydet. rep1'de bu yapilmadi:
    # Claude kendi olay akisina model adini yaziyor, Codex ve Antigravity yazmiyor,
    # ve kosu bittikten sonra hangi surumun hizmet verdigi geriye donuk bilinemiyor.
    out="results/harness_$(date +%Y%m%d_%H%M).txt"
    mkdir -p results
    {
      echo "# Harness and model identity, recorded $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo "# Written before a run. A blank model line means the CLI does not report it."
      for b in claude codex agy; do
        echo
        echo "## $b"
        command -v "$b" || { echo "(not installed)"; continue; }
        "$b" --version 2>&1 | head -3
        echo "-- model as the CLI reports it:"
        case "$b" in
          agy)   "$b" models 2>&1 | head -20 ;;
          codex) "$b" --config 2>&1 | grep -i -m3 model || \
                 grep -i -m3 "^model" "$HOME/.codex/config.toml" 2>/dev/null || \
                 echo "(no configured model found; Codex does not log the serving model)" ;;
          claude) echo "(recorded per run in the event stream)" ;;
        esac
      done
    } > "$out" 2>&1
    echo "$out"
    cat "$out"
    ;;
  koken)
    "$PY" scripts/run_provenance.py --out results/provenance.tsv
    ;;
  paket)
    # Okuyucuya gonderilecek tek dosya. Anahtar DISARIDA kalir ve bu kontrol edilir:
    # anahtarin kazara paylasilmasi korlemeyi tamamen bozar ve geri alinamaz.
    sheet="results/audit/adjudication_sheet.tsv"
    [ -f "$sheet" ] || { echo "Once: bash go.sh hakem"; exit 1; }
    out="results/degerlendirme_paketi.zip"
    rm -f "$out"
    tmp=$(mktemp -d)
    cp "$sheet" "$tmp/adjudication_sheet.tsv"
    cp docs/DEGERLENDIRME_TR.md "$tmp/TALIMAT.md"
    # PDF de koy: okuyucu Markdown dosyasi acmak zorunda kalmasin
    if "$PY" scripts/md_to_pdf.py docs/DEGERLENDIRME_TR.md "$tmp/TALIMAT.pdf" >/dev/null 2>&1; then
      :
    else
      echo "UYARI: PDF uretilemedi, pakete yalnizca Markdown konuyor."
      "$PY" scripts/md_to_pdf.py docs/DEGERLENDIRME_TR.md "$tmp/TALIMAT.pdf" 2>&1 | tail -4
    fi
    ( cd "$tmp" && zip -q "$OLDPWD/$out" adjudication_sheet.tsv TALIMAT.md \
        $( [ -f TALIMAT.pdf ] && echo TALIMAT.pdf ) )
    rm -rf "$tmp"
    if unzip -l "$out" | grep -qi "key"; then
      echo "DUR: pakette anahtar dosyasi var. Gondermeyin."
      rm -f "$out"
      exit 1
    fi
    echo "Gonderilecek dosya: $out"
    unzip -l "$out"
    echo
    echo "Satir sayisi (baslik haric): $(( $(wc -l < "$sheet") - 1 ))"
    echo "Anahtar dosyasi pakette DEGIL, yerinde duruyor: results/audit/adjudication_sheet.key.tsv"
    ;;
  hakem)
    # Korleme degerlendirme sayfasi: tum kollarin adaylari TEK dosyada, karisik
    # sirada, kol adi cikarilmis. Okuyucu hangi ajani degerlendirdigini bilmez.
    DB="${AMRFINDER_DB:-}"
    if [ -z "$DB" ]; then
      for c in "$HOME/miniforge3/envs/amr/share/amrfinderplus/data/latest" \
               "$HOME/miniforge3/envs/amr/share/amrfinderplus/data"/* ; do
        [ -f "$c/fam.tsv" ] && DB="$c" && break
      done
    fi
    [ -f "$DB/fam.tsv" ] || { echo "AMRFinderPlus veritabani bulunamadi"; exit 1; }
    args=()
    for kol in $ARMS; do
      f="runs/$kol/rep1/predictions.tsv"
      [ -f "$f" ] || continue
      n=$(( $(wc -l < "$f") - 1 ))
      [ "$n" -ge 708 ] && args+=(--run "runs/$kol/rep1") || echo "atlandi: $kol ($n/708)"
    done
    [ "${#args[@]}" -gt 0 ] || { echo "Hicbir kol hazir degil."; exit 1; }
    mkdir -p results/audit
    "$PY" scripts/hallucination_audit.py "${args[@]}" --catalog "$DB" \
      --out results/audit/all_arms.tsv \
      --blind results/audit/adjudication_sheet.tsv
    echo
    echo "Okuyuculara verilecek dosya : results/audit/adjudication_sheet.tsv"
    echo "Kol adlarini cozen anahtar   : results/audit/adjudication_sheet.key.tsv"
    echo "Anahtari okuyuculara VERMEYIN; degerlendirme bitene kadar acilmaz."
    ;;
  sizinti)
    "$PY" scripts/leak_check.py
    ;;
  ref)
    # Arka planda, uyku engelli: ~118 izolat x ~1 dk. Kesilse de kaldigi yerden devam eder
    # (bitmis izolatin amrfinder raporu diskte durur ve atlanir).
    mkdir -p runs
    log="runs/ref_$(date +%Y%m%d_%H%M).log"
    echo "Referans kolu basladi. Log: $log"
    echo "Terminali kapatabilirsiniz. Mac prize takili, kapagi acik kalsin."
    caffeinate -dimsu bash -c '
      source "$HOME/miniforge3/etc/profile.d/conda.sh" && conda activate amr
      '"$PY"' scripts/04_reference_arm.py
    ' > "$log" 2>&1 &
    echo "Arka planda calisiyor (pid $!)."
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
