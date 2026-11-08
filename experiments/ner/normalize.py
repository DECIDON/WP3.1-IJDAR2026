"""Étape 1 du pivot NER : données brutes -> format normalisé (un document natif par ligne, labels d'origine).

Les chargeurs de `sources/` sont ceux de la fiche statistique des datasets (dépôt de rédaction de Mathieu,
`experiences/fiche_stats/loaders/`), copiés tels quels ; seuls les chemins passent par deux variables
d'environnement, fixées ici. Format de sortie (`<key>.jsonl`) : {"doc_id", "page_id", "split", "text",
"spans": [[début, fin, label d'origine], ...]} + `<key>.meta.json` (provenance, choix faits).

Usage (depuis experiments/ner/) :
  uv run python normalize.py --raw /chemin/vers/raw --out /chemin/vers/normalized [--only soduco hipe ...]

`--raw` doit contenir les dossiers listés dans README.md (« Données brutes »).
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")

# chargeur -> arguments supplémentaires ; ordre = ordre d'exécution
LOADERS = {
    "hipe": [],
    "soduco": [],
    "mpopp": [],
    "seven_romans": [],
    "geoedda": [],
    "litbank": [],
    "e-ner": [],
    "brat_C": ["copious"],
    "basel": [],
    "decidon": [],
    "nem_fr": [],
    "oldbailey": None,  # arguments positionnels : RAW OUT DEPUIS (cf. sources/oldbailey.py)
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True, help="dossier des données brutes")
    ap.add_argument("--out", required=True, help="dossier de sortie (créé au besoin)")
    ap.add_argument("--only", nargs="*", choices=list(LOADERS), help="ne lancer que ces chargeurs")
    a = ap.parse_args()
    raw, out = os.path.abspath(a.raw), os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    env = {**os.environ, "IJDAR_RAW": raw, "IJDAR_NORMALIZED": out}
    for name, extra in LOADERS.items():
        if a.only and name not in a.only:
            continue
        args = [os.path.join(raw, "oldbailey"), out, "18341101"] if extra is None else extra
        t0 = time.time()
        print(f"== {name}", flush=True)
        subprocess.run([sys.executable, os.path.join(SRC, f"{name}.py"), *args], env=env, cwd=SRC, check=True)
        print(f"   {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
