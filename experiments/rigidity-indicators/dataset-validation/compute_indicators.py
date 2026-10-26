"""Calcul des indicateurs de rigidité sur les datasets du projet (fenêtres tirées au hasard).

Les indicateurs viennent du package text_rigidity (racine du dépôt) ; les datasets viennent de loaders.py.

Usage : python compute_indicators.py [--sizes 100 300] [--max-windows 100] [--datasets nom1 nom2 ...]
Sortie : results/windows.csv (une ligne par fenêtre).
"""
import argparse
import os
import random
import re
import time

import pandas as pd
import text_rigidity as tr

import loaders

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
WORD_RE = re.compile(r"[^\W_]+")
LANGS = {"basel": "de", "litbank": "en", "e-ner": "en", "copious": "en", "old-bailey": "en"}


def dataset_lang(name, docs):
    return LANGS.get(name, docs[0]["lang"] if docs else "fr")


def sample_windows(docs, size, n_max, rng):
    """Fenêtres de size mots, sans chevauchement, tirées à tour de rôle dans les documents (au plus n_max)."""
    per_doc = []
    for d in docs:
        spans = [m.span() for m in WORD_RE.finditer(d["text"])]
        starts = list(range(0, len(spans) - size + 1, size))
        if not starts:
            continue
        rng.shuffle(starts)
        per_doc.append((d, spans, starts))
    rng.shuffle(per_doc)
    out = []
    while len(out) < n_max and any(st for _, _, st in per_doc):
        for d, spans, st in per_doc:
            if st and len(out) < n_max:
                s = st.pop()
                out.append((d, spans[s][0], spans[s + size - 1][1]))
    return out


def run(names, sizes, max_windows, seed=0):
    rows = []
    for name in names:
        t0 = time.time()
        docs = loaders.load_pivot(name)
        lang = dataset_lang(name, docs)
        nlp = tr.get_nlp(lang)
        reference = tr.FormularityReference([(d["doc_id"], d["text"]) for d in docs], lang=lang, seed=seed)
        for size in sizes:
            rng = random.Random(f"{seed}-{name}-{size}")
            wins = sample_windows(docs, size, max_windows, rng)
            texts = [d["text"][a:b] for d, a, b in wins]
            for (d, a, b), text, parsed in zip(wins, texts, nlp.pipe(texts, batch_size=32)):
                n_words = len(WORD_RE.findall(text))
                typo = tr.compute_typographic_formatting(text)
                # seuils 2 et 5 : sensibilité de la formularité au seuil d'occurrences (analysis.py)
                form = {k: tr.compute_formularity(text, reference, d["doc_id"], lang, parsed, min_count=k)
                        for k in (2, 3, 5)}
                rows.append({
                    "dataset": name, "lang": lang, "size": size, "doc_id": d["doc_id"], "start": a, "end": b,
                    "n_words": n_words,
                    "typo": typo["typo_total"], "typo_no_punct": typo["typo_no_punctuation"],
                    "balance": tr.compute_phrastic_balance(text, lang, parsed),
                    "verbless": tr.compute_verbless_rate(text, lang, parsed),
                    "name_density": tr.compute_name_density(text, lang, parsed),
                    "formularity": form[3]["formularity"], "formularity_k2": form[2]["formularity"],
                    "formularity_k5": form[5]["formularity"], "ref_tokens": form[3]["ref_tokens"],
                    "distinct2": tr.compute_lexical_diversity(text, 2, lang, parsed),
                    "kl": tr.compute_pos_kl_divergence(text, lang, doc=parsed),
                })
        print(f"{name:20s} {time.time() - t0:6.1f} s", flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[100, 300])
    ap.add_argument("--max-windows", type=int, default=100)
    ap.add_argument("--datasets", nargs="+", default=list(loaders.DATASETS))
    ap.add_argument("--out", default=os.path.join(RESULTS, "windows.csv"))
    args = ap.parse_args()
    df = run(args.datasets, args.sizes, args.max_windows)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{len(df)} windows -> {args.out}")
