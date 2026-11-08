#!/usr/bin/env bash
# Régime 1 (zero-shot) sur machine partagée : CPU seul, 12 threads (50 % d'un poste à 24), nice, mémoire plafonnée.
# Les trois runs s'enchaînent (spaCy lg, spaCy trf anglais, GLiNER), chacun suivi de son évaluation.
#   bash run_zeroshot.sh <SAMPLE> <RUNS> <PREFIXE>      ex. bash run_zeroshot.sh ../data/sample ../runs mathieu_1er_jet
# Lancer dans `screen` ; sortie : <RUNS>/<PREFIXE>_zeroshot_{spacy_lg,spacy_trf_en,gliner_relex_multi}/
set -euo pipefail
SAMPLE=$(realpath "$1"); RUNS=$(realpath "$2"); P=$3
THREADS=${THREADS:-12}
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS TOKENIZERS_PARALLELISM=false
cd "$(dirname "$0")"
run() {  # <nom> <arguments de zeroshot.py>
  local out="$RUNS/${P}_zeroshot_$1"; shift
  echo "== $(date '+%F %T') $out"
  nice -n 10 uv run python zeroshot.py "$@" --sample "$SAMPLE" --out "$out" --threads "$THREADS"
  uv run python evaluate.py --sample "$SAMPLE" --run "$out"
}
run spacy_lg spacy
run spacy_trf_en spacy --spacy-en en_core_web_trf
run gliner_relex_multi gliner
echo "== $(date '+%F %T') fini"
