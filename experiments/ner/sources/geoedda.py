"""GEODE — GeoEDdA-NER (paragraphes, spans imbriqués) et GeoEDdA-TopoRel (entrées, placeNames).

Lancer : python3 loaders/geoedda.py (bibliothèque standard seulement).
"""
import collections
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW, OUT = os.environ["IJDAR_RAW"], os.environ["IJDAR_NORMALIZED"]
SPLITS = {"train": "train", "val": "dev", "test": "test"}


def write(key, docs, meta):
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    json.dump({"key": key, **meta}, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
    print(key, len(docs), sum(len(d["spans"]) for d in docs))


# ------------------------------------------------------------------ GeoEDdA-NER
docs, entries, seen = [], set(), collections.Counter()
for f, sp in SPLITS.items():
    for line in open(f"{RAW}/geoedda/{f}.jsonl"):
        d = json.loads(line)
        m = d["meta"]
        ent = f"v{m['volume']}-a{m['article']}"
        entries.add(ent)
        did = f"{ent}-p{m['paragraph']}"
        seen[did] += 1
        if seen[did] > 1:
            did += f"#{seen[did]}"
        docs.append({"doc_id": did, "page_id": None, "split": sp, "text": d["text"],
                     "spans": [[s["start"], s["end"], s["label"]] for s in d.get("spans", [])]})
n_dup = sum(1 for v in seen.values() if v > 1)
write("geoedda", docs, {
    "dataset": "GeoEDdA-NER", "sous_corpus": "Encyclopédie de Diderot & d'Alembert (ARTFL)",
    "sheets": ["Datasets NER français#14"], "unite_doc": "paragraphe d'article",
    "source": "https://huggingface.co/datasets/GEODE/GeoEDdA-NER (train/val/test.jsonl)",
    "version": "HF commit e09cf103", "annotation": "gold (pré-annotation par modèles puis correction)",
    "remarques": (f"Doc = paragraphe (unité native du jeu : 2200 paragraphes tirés de {len(entries)} articles distincts "
                  "(volume, article) ; page_id null, la source ne donne pas la page). Les 12 classes de la source sont gardées "
                  "telles quelles, y compris les non-entités Relation, Head, Domain-mark et Latlong ; spans imbriqués "
                  "(ENE-* englobant NP-*/NC-*) tous gardés. Splits HF train/val/test (val -> dev). "
                  f"{n_dup} identifiants (volume, article, paragraph) portés par des paragraphes DIFFÉRENTS de splits différents "
                  "(numérotation de paragraphe incohérente dans meta) : gardés, suffixés '#n'. "
                  "Le nb d'articles distincts peut donc être légèrement surestimé ; il vaut 2001 comme publié. "
                  "Écart tokens : 161 238 tokens spaCy dans la source (= chiffre publié) vs ~172 600 avec la "
                  "tokenisation de stats.py (+7 % : élisions 'd'', abréviations 'Géog.' scindées en mot + ponctuation)."),
    "published": {"tokens": 161238, "mentions": 25079, "docs": 2200}})
