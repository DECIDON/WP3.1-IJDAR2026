"""Étape 3 : tirage équilibré des unités et répartition en folds, puis extraction des sous-datasets.

Deux sous-commandes :

  draw         tire, pour chaque jeu, des unités au hasard (graine 42) jusqu'à atteindre le budget commun de
               mentions PER + LOC (= total du plus petit jeu ; une unité qui ferait dépasser le budget de plus de
               5 % est sautée), puis les répartit en 6 folds équilibrés en mentions.
               Écrit splits/<key>.json (VERSIONNÉ : identifiants d'unités + offsets, aucune donnée textuelle) et
               réécrit le tableau « Unités de tirage » de README.md. Refuse d'écraser des splits existants
               sans --force : les sous-datasets sont figés.
  materialize  reconstruit les sous-datasets depuis le pivot et les splits figés : <out>/<key>.jsonl, un
               segment par ligne {"key", "unit_id", "fold", "doc_id", "start", "end", "lang", "text", "spans"},
               offsets des spans relatifs au segment. Ces fichiers ne sont PAS versionnés (licences).

Unité de tirage : cf. pivot.py (`units` de chaque document) ; GeoEDdA : l'article (tous ses paragraphes).
SoDUCo : les versions de référence et OCR reçoivent les mêmes entrées et les mêmes folds (tirage fait sur la
référence, parmi les entrées présentes dans les deux versions).

Usage (depuis experiments/ner/) :
  uv run python sample.py draw --pivot /chemin/pivot
  uv run python sample.py materialize --pivot /chemin/pivot --out /chemin/sample
"""
import argparse
import collections
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SPLITS = os.path.join(HERE, "splits")
README = os.path.join(HERE, "README.md")
TAGS = ("<!-- UNITES : début (généré par sample.py draw) -->", "<!-- UNITES : fin -->")
SEED, K = 42, 6
TOL = 0.05  # dépassement toléré du budget par la dernière unité tirée
PAIRED = {"soduco-ocr": "soduco-ref"}  # jeu -> jeu dont il reprend le tirage

# nom de l'unité de tirage (tableau du README) ; « (sous-unité) » = découpage plus fin que le document natif
UNIT_NAME = {
    "7romans": "phrase (sous-unité du roman)", "basel": "fiche de registre", "soduco-ref": "entrée d'annuaire",
    "soduco-ocr": "entrée d'annuaire", "ajmc-de": "page", "ajmc-en": "page", "ajmc-fr": "page",
    "hipe2020-de": "article", "hipe2020-en": "article", "hipe2020-fr": "article", "letemps-fr": "article",
    "newseye-fi": "page", "newseye-fr": "ligne (sous-unité de la page)", "newseye-sv": "page",
    "geoedda": "article de l'Encyclopédie", "litbank": "ligne (sous-unité de l'extrait)",
    "mpopp-dactylo": "zone d'acte", "mpopp-manuscrits": "zone d'acte", "copious": "page",
    "e-ner": "document (dépôt EDGAR)", "oldbailey-1834-1913": "procès",
    "decidon-august": "bloc Chandra (sous-unité de la page)", "nem-fr": "échantillon (genres confondus)",
}


def read_units(path, key):
    """unit_id -> {"segments": [(doc_id, début, fin)], "mentions": n} pour un jeu du pivot."""
    out = collections.OrderedDict()
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        us = d["units"]
        for i, (a, b) in enumerate(us):
            if key == "geoedda":
                uid = re.sub(r"-p[^-]*$", "", d["doc_id"])  # v<vol>-a<article>-p<paragraphe>[#n] -> article
            else:
                uid = d["doc_id"] if len(us) == 1 and (a, b) == (0, len(d["text"])) else f"{d['doc_id']}#{i}"
            u = out.setdefault(uid, {"segments": [], "mentions": 0})
            u["segments"].append((d["doc_id"], a, b))
            u["mentions"] += sum(1 for s, e, _ in d["spans"] if a <= s and e <= b)
    return out


def folds(drawn):
    """Répartition gloutonne en K folds équilibrés en mentions (plus grosses unités d'abord, ordre du tirage
    pour départager) ; renvoie unit_id -> fold."""
    load, out = [0] * K, {}
    for uid, n in sorted(drawn, key=lambda x: -x[1]):
        f = min(range(K), key=lambda j: (load[j], j))
        out[uid] = f
        load[f] += n
    return out


def draw(a):
    keys = sorted(f[:-6] for f in os.listdir(a.pivot) if f.endswith(".jsonl"))
    keys = [k for k in keys if k not in PAIRED] + [k for k in PAIRED if k in keys]  # référence d'abord
    units = {k: read_units(os.path.join(a.pivot, f"{k}.jsonl"), k) for k in keys}
    totals = {k: sum(u["mentions"] for u in v.values()) for k, v in units.items()}
    budget = min(totals.values())
    os.makedirs(SPLITS, exist_ok=True)
    rows = []
    for k in keys:
        path = os.path.join(SPLITS, f"{k}.json")
        if os.path.exists(path) and not a.force:
            raise SystemExit(f"{path} existe : les splits sont figés (--force pour les refaire)")
        ref = PAIRED.get(k)
        if ref:  # même tirage et mêmes folds que le jeu de référence
            prev = json.load(open(os.path.join(SPLITS, f"{ref}.json")))
            assign = {u["unit_id"]: u["fold"] for u in prev["units"]}
            ids = list(assign)
        else:
            pool = sorted(units[k])
            if k in PAIRED.values():  # n'importe quelle entrée de la référence n'existe pas forcément en OCR
                other = [o for o, r in PAIRED.items() if r == k][0]
                pool = [uid for uid in pool if uid in units[other]]
            random.Random(SEED).shuffle(pool)
            ids, n = [], 0
            for uid in pool:
                if n >= budget:
                    break
                m = units[k][uid]["mentions"]
                if n + m > budget * (1 + TOL):  # ferait trop dépasser le budget : unité sautée
                    continue
                ids.append(uid)
                n += m
            assign = folds([(uid, units[k][uid]["mentions"]) for uid in ids])
        rec = [{"unit_id": uid, "fold": assign[uid], "mentions": units[k][uid]["mentions"],
                "segments": [list(s) for s in units[k][uid]["segments"]]} for uid in ids]
        per_fold = [sum(r["mentions"] for r in rec if r["fold"] == f) for f in range(K)]
        meta = {"key": k, "seed": SEED, "k": K, "budget": budget, "paired_with": ref,
                "unit": UNIT_NAME[k], "n_units_total": len(units[k]), "n_mentions_total": totals[k],
                "n_units": len(rec), "n_mentions": sum(per_fold), "mentions_per_fold": per_fold}
        json.dump({**meta, "units": rec}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        rows.append(meta)
        print(f"{k:20s} unités {len(rec):4d}/{len(units[k]):6d}  mentions {sum(per_fold):4d}  folds {per_fold}")
    write_readme(rows, budget)


def write_readme(rows, budget):
    num = lambda v: f"{v:,}".replace(",", " ")
    lines = [f"Budget commun : **{budget} mentions PER + LOC** par jeu (= total du plus petit jeu), graine {SEED}, "
             f"{K} folds.", "",
             "| jeu | unité de tirage | unités (corpus) | mentions / unité | unités tirées | mentions tirées | "
             "mentions par fold |", "|---|---|---:|---:|---:|---:|---|"]
    for r in rows:
        mpu = r["n_mentions_total"] / r["n_units_total"]
        lines.append(f"| {r['key']} | {r['unit']} | {num(r['n_units_total'])} | {mpu:.1f} | {num(r['n_units'])} | "
                     f"{r['n_mentions']} | {min(r['mentions_per_fold'])}–{max(r['mentions_per_fold'])} |")
    txt = open(README, encoding="utf-8").read()
    i, j = txt.index(TAGS[0]) + len(TAGS[0]), txt.index(TAGS[1])
    open(README, "w", encoding="utf-8").write(txt[:i] + "\n" + "\n".join(lines) + "\n" + txt[j:])


def materialize(a):
    os.makedirs(a.out, exist_ok=True)
    for f in sorted(os.listdir(SPLITS)):
        sp = json.load(open(os.path.join(SPLITS, f), encoding="utf-8"))
        k = sp["key"]
        need = {}
        for u in sp["units"]:
            for doc_id, s, e in u["segments"]:
                need.setdefault(doc_id, []).append((u["unit_id"], u["fold"], s, e))
        n_seg = n_ment = 0
        with open(os.path.join(a.out, f"{k}.jsonl"), "w", encoding="utf-8") as fo:
            for line in open(os.path.join(a.pivot, f"{k}.jsonl"), encoding="utf-8"):
                d = json.loads(line)
                for uid, fold, s, e in need.pop(d["doc_id"], []):
                    spans = [[x - s, y - s, l] for x, y, l in d["spans"] if s <= x and y <= e]
                    fo.write(json.dumps({"key": k, "unit_id": uid, "fold": fold, "doc_id": d["doc_id"], "start": s,
                                         "end": e, "lang": d["lang"], "text": d["text"][s:e], "spans": spans},
                                        ensure_ascii=False) + "\n")
                    n_seg += 1
                    n_ment += len(spans)
        assert not need, f"{k} : documents introuvables dans le pivot : {list(need)[:3]}"
        assert n_ment == sp["n_mentions"], (k, n_ment, sp["n_mentions"])
        print(f"{k:20s} segments {n_seg:5d}  mentions {n_ment}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--pivot", required=True)
    d.add_argument("--force", action="store_true")
    m = sub.add_parser("materialize")
    m.add_argument("--pivot", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args()
    draw(a) if a.cmd == "draw" else materialize(a)


if __name__ == "__main__":
    main()
