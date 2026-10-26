"""Formularité des fenêtres NEM.fr avec une référence commune à tous les genres de NEM.fr.

Dans windows.csv, la référence de formularité d'une fenêtre est tirée des autres documents de SON sous-corpus ; un genre
de NEM.fr n'en fournit que 600 à 3 300 tokens, sous le seuil de comparabilité de 15 000 (analysis.MIN_REF_TOKENS) : la
valeur est mise à vide par common.load_windows. Ici, la référence est tirée de tout NEM.fr (68 documents, 12 genres),
toujours hors document de la fenêtre, avec les réglages de compute_indicators.py (FormularityReference par défaut,
seed 0, 4-grammes vus au moins 3 fois). La formularité d'un genre est alors mesurée par rapport à NEM.fr, pas par
rapport à lui-même : c'est la variante « NEMpool » des jeux d'indicateurs (pca_indicators.py).
Sortie : results/nem_formularity_pooled.csv (wid, formularity, ref_tokens).
Usage : uv run python nem_formularity.py
"""
import os

import pandas as pd
import text_rigidity as tr

from common import RESULTS, SIZE, WINDOWS, loaders

OUT = os.path.join(RESULTS, "nem_formularity_pooled.csv")


def main():
    w = pd.read_csv(WINDOWS, dtype={"doc_id": str})
    w = w[(w["size"] == SIZE) & w.dataset.str.startswith("nem-")]
    docs = {}
    for name in w.dataset.unique():
        docs.update({d["doc_id"]: d["text"] for d in loaders.load_pivot(name)})
    reference = tr.FormularityReference(list(docs.items()), lang="fr", seed=0)
    nlp = tr.get_nlp("fr")
    rows = []
    texts = [docs[r.doc_id][r.start:r.end] for r in w.itertuples()]
    for r, text, parsed in zip(w.itertuples(), texts, nlp.pipe(texts, batch_size=32)):
        f = tr.compute_formularity(text, reference, r.doc_id, "fr", parsed)
        rows.append({"wid": f"{r.dataset}:{r.doc_id}:{r.start}", "formularity": f["formularity"], "ref_tokens": f["ref_tokens"]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"{len(out)} fenêtres NEM.fr → {OUT} ; ref_tokens min {out.ref_tokens.min()}")


if __name__ == "__main__":
    main()
