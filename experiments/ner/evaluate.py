"""Évaluation d'un run (zeroshot.py) contre le gold des sous-datasets : précision, rappel, F1 par jeu.

Correspondance via nervaluate (algorithme SemEval'13, celui du scoreur HIPE) : régime `strict` (mêmes bornes et
même type) et `fuzzy` (= `ent_type` : même type, chevauchement d'au moins un caractère). Chaque label est scoré
seul et les comptes sont sommés (micro = somme PER + LOC) : une prédiction d'un type ne « consomme » jamais une
mention gold de l'autre type. Prédictions triées avant scoring (nervaluate dépend de l'ordre des spans quand des
prédictions d'un même label se chevauchent). IC95 : bootstrap sur les UNITÉS (1 000 tirages, graine 42).

Old Bailey : seul le rappel est interprétable (annotation partielle, une personne prédite mais non annotée
compte comme fausse).

Sortie : <run>/recap.csv (tidy : jeu, langue, modèle, régime, portée, label, P, R, F1, cor, act, pos, IC95 du F1)
et un résumé à l'écran.

Usage : uv run python evaluate.py --sample /chemin/sample --run /chemin/runs/<nom>
"""
import argparse
import collections
import csv
import json
import os
import random

from nervaluate_match import count_page, prf

LABELS = ("PER", "LOC")
REGIMES = {"strict": "strict", "fuzzy": "ent_type"}
N_BOOT, SEED = 1000, 42


def counts(gold, pred):
    """{(régime, label): (cor, act, pos)} pour un segment."""
    out = {}
    for r, mode in REGIMES.items():
        for lab in LABELS:
            g = sorted((l, s, e) for s, e, l in gold if l == lab)
            p = sorted((l, s, e) for s, e, l, *_ in pred if l == lab)
            out[(r, lab)] = count_page(g, p, mode)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = json.load(open(os.path.join(a.run, "run.json")))
    rows = []
    for k, info in run["datasets"].items():
        gold = [json.loads(l) for l in open(os.path.join(a.sample, f"{k}.jsonl"), encoding="utf-8")]
        preds = [json.loads(l) for l in open(os.path.join(a.run, f"{k}.jsonl"), encoding="utf-8")]
        assert len(gold) == len(preds), f"{k} : {len(gold)} segments gold, {len(preds)} prédits"
        per_unit = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, 0]))
        for g, p in zip(gold, preds):  # même ordre (zeroshot.py écrit les segments dans l'ordre du sample)
            assert (g["unit_id"], g["doc_id"], g["start"]) == (p["unit_id"], p["doc_id"], p["start"]), k
            for key, (c, x, y) in counts(g["spans"], p["pred"]).items():
                acc = per_unit[p["unit_id"]][key]
                acc[0] += c; acc[1] += x; acc[2] += y
        units = list(per_unit)
        rng = random.Random(SEED)
        boots = [[rng.choice(units) for _ in units] for _ in range(N_BOOT)]
        for r in REGIMES:
            for scope, labs in [("micro", LABELS)] + [("per_label", (l,)) for l in LABELS]:
                def score(us):
                    c = x = y = 0
                    for u in us:
                        for lab in labs:
                            cc, xx, yy = per_unit[u][(r, lab)]
                            c += cc; x += xx; y += yy
                    return prf(c, x, y)
                m = score(units)
                f1s = sorted(score(b).f1 for b in boots)
                rows.append({"dataset": k, "lang": info["lang"], "model": info["model"], "regime": r, "scope": scope,
                             "label": "PER+LOC" if scope == "micro" else labs[0],
                             "precision": round(m.precision, 4), "recall": round(m.recall, 4), "f1": round(m.f1, 4),
                             "cor": m.cor, "act": m.act, "pos": m.pos,
                             "ci95_lo": round(f1s[int(0.025 * N_BOOT)], 4), "ci95_hi": round(f1s[int(0.975 * N_BOOT) - 1], 4)})
    with open(os.path.join(a.run, "recap.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{'jeu':20s} {'modèle':24s} {'P strict':>8s} {'R strict':>8s} {'F1 strict':>9s} {'F1 fuzzy':>8s}")
    for k in run["datasets"]:
        s = next(r for r in rows if r["dataset"] == k and r["regime"] == "strict" and r["scope"] == "micro")
        f = next(r for r in rows if r["dataset"] == k and r["regime"] == "fuzzy" and r["scope"] == "micro")
        print(f"{k:20s} {s['model'][-24:]:24s} {s['precision']:8.3f} {s['recall']:8.3f} {s['f1']:9.3f} {f['f1']:8.3f}")


if __name__ == "__main__":
    main()
