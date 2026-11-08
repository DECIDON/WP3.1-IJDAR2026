"""Étape 2 du pivot NER : format normalisé -> pivot PER/LOC (version du Sheet) + unités de tirage.

Correspondance des étiquettes = onglet « Matrice des entités » du Sheet des datasets (arbitrages du 2026-10-05) :
annotations de chaque projet prises telles quelles (frontières, catégories balisées, imbrications), seules les
classes PER et LOC gardées. Reprise de `experiences/dataset_per_loc/convert.py` (dépôt de rédaction de Mathieu),
sans la sortie BIO.

Sortie : <out>/<key>.jsonl, un document natif par ligne :
  {"doc_id", "page_id", "split", "lang", "text", "spans": [[début, fin, "PER"|"LOC"], ...],
   "units": [[début, fin], ...]}
`units` découpe le document en unités de tirage (cf. README.md, « Unités de tirage ») : le document entier
par défaut ; phrases (7romans), lignes (LitBank, newseye-fr) ou blocs Chandra (DECIDON) sinon. Une frontière
d'unité ne coupe jamais une entité : les morceaux qu'une entité enjambe sont fusionnés. GeoEDdA : l'unité est
l'article, qui regroupe plusieurs documents (paragraphes) ; elle est reconstituée par sample.py.
+ <out>/stats.csv (une ligne par jeu).

Usage (depuis experiments/ner/) :
  uv run python pivot.py --normalized /chemin/normalized --out /chemin/pivot [--only KEY ...]
"""
import argparse
import collections
import csv
import json
import os
import re

HIPE = {"pers": "PER", "loc": "LOC"}
NEWSEYE = {"PER": "PER", "LOC": "LOC"}
GEO = {f"{n}-{t}": ("PER" if t == "Person" else "LOC") for n in ("NP", "NC", "ENE") for t in ("Person", "Spatial")}
# (clé de sortie, clé normalisée, langue, ligne de la Matrice des entités, correspondance)
CORPUS = [
    ("7romans", "7-romans", "fr", "7romans", {"PER": "PER", "LOC": "LOC"}),
    ("basel", "basel-landrecords", "de", "The Basel Land Records Ground Truth", {"person": "PER", "place": "LOC"}),
    ("soduco-ref", "soduco-flat", "fr", "SoDUCo", {"PER": "PER", "LOC": "LOC"}),
    ("soduco-ocr", "soduco-flat-ocr", "fr", "SoDUCo", {"PER": "PER", "LOC": "LOC"}),
    ("ajmc-de", "hipe2022-ajmc-de", "de", "ajmc", HIPE),
    ("ajmc-en", "hipe2022-ajmc-en", "en", "ajmc", HIPE),
    ("ajmc-fr", "hipe2022-ajmc-fr", "fr", "ajmc", HIPE),
    ("hipe2020-de", "hipe2022-hipe2020-de", "de", "hipe2020", HIPE),
    ("hipe2020-en", "hipe2022-hipe2020-en", "en", "hipe2020 ; HIPE-2022|hipe2020-en", HIPE),
    ("hipe2020-fr", "hipe2022-hipe2020-fr", "fr", "hipe2020", HIPE),
    ("letemps-fr", "hipe2022-letemps-fr", "fr", "letemps", HIPE),
    ("newseye-fi", "hipe2022-newseye-fi", "fi", "newseye", NEWSEYE),
    ("newseye-fr", "hipe2022-newseye-fr", "fr", "newseye", NEWSEYE),
    ("newseye-sv", "hipe2022-newseye-sv", "sv", "newseye", NEWSEYE),
    ("geoedda", "geoedda", "fr", "GeoEDDA", GEO),
    ("litbank", "litbank", "en", "LitBank", {"PER": "PER", "LOC": "LOC", "GPE": "LOC", "FAC": "LOC"}),
    ("mpopp-dactylo", "mpopp-dactylo", "fr", "M-POPP", "mpopp"),
    ("mpopp-manuscrits", "mpopp-manuscrits", "fr", "M-POPP", "mpopp"),
    ("copious", "copious", "en", "COPIOUS", {"Person": "PER", "GeographicalLocation": "LOC"}),
    ("e-ner", "e-ner", "en", "E-NER", {"PERSON": "PER", "LOCATION": "LOC"}),
    ("oldbailey-1834-1913", "oldbailey-1834-1913", "en", "old bailey proceedings", {"PER": "PER", "LOC": "LOC"}),
    ("decidon-august", "decidon-august", "fr", "DECIDON CR JORF", {"PER": "PER", "SPK": "PER", "FCT": "PER", "LOC": "LOC"}),
    ("nem-fr", "nem-fr", "fr", "NEM.fr", {"PERS": "PER", "LOC": "LOC"}),
]

# M-POPP : parties de nom et d'adresse fusionnées quand elles se suivent ; ville et département = LOC seuls.
# Noms : séparateur toléré = blancs, « * » (bourrage dactylographique) et « - » de fin de ligne ; la virgule en plus
# entre prénoms (« Henriette, Constance, Delaumay ») et dans « Nom, Prénoms » (« Lemoigne, Onézime »), sauf si ce
# prénom ouvre une nouvelle personne (suivi de son nom).
MP_NAME = {"First name", "Family name"}
MP_ADDR = {"Street number", "Street type", "Street name"}
MP_GAP = re.compile(r"[\s*\-]*")
MP_GAPC = re.compile(r"[\s*,\-]*")
MP_JOIN = re.compile(r"[\s,]*")  # adresse : blancs et virgules


MPOPP_CORR = ("First name + Family name fusionnés -> PER ; Street number/type/name contigus -> LOC ; "
              "City, Department/Country -> LOC")


def mp_join(text, parts, i, cur):
    s, e, l = parts[i]
    if s < cur[1]:
        return False
    gap = text[cur[1]:s]
    if MP_GAP.fullmatch(gap):
        return True
    if not MP_GAPC.fullmatch(gap):
        return False
    if cur[2] == "First name":
        return True
    nxt = parts[i + 1] if i + 1 < len(parts) else None
    opens = nxt and nxt[2] == "Family name" and MP_GAP.fullmatch(text[e:nxt[0]])
    return l == "First name" and not opens


def mpopp(text, spans):
    out = [[s, e, "LOC"] for s, e, l in spans if l in ("City", "Department/Country")]
    names = sorted({(s, e, l) for s, e, l in spans if l in MP_NAME})
    cur = None
    for i, (s, e, l) in enumerate(names):
        if cur and mp_join(text, names, i, cur):
            cur[1], cur[2] = max(cur[1], e), l
        else:
            if cur:
                out.append([cur[0], cur[1], "PER"])
            cur = [s, e, l]
    if cur:
        out.append([cur[0], cur[1], "PER"])
    cur = None
    for s, e in sorted({(s, e) for s, e, l in spans if l in MP_ADDR}):
        if cur and s >= cur[1] and MP_JOIN.fullmatch(text[cur[1]:s]):
            cur[1] = max(cur[1], e)
        else:
            if cur:
                out.append(cur)
            cur = [s, e, "LOC"]
    if cur:
        out.append(cur)
    return out


def translate(d, mapping):
    if mapping == "mpopp":
        sp = mpopp(d["text"], d["spans"])
    else:
        sp = [[s, e, mapping[l.split(".")[0]]] for s, e, l in d["spans"] if l.split(".")[0] in mapping]
    text, out = d["text"], set()
    for s, e, l in sp:  # blancs de bord retirés (ex. SoDUCo : « \nquai de la Tournelle »)
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.add((s, e, l))
    return sorted(out, key=lambda x: (x[0], -x[1], x[2]))



# unité de tirage par jeu (défaut : le document natif) ; séparateur des morceaux dans le texte
UNIT = {"7romans": ("phrase", "\n"), "litbank": ("ligne", "\n"), "newseye-fr": ("ligne", "\n"),
        "decidon-august": ("bloc Chandra", re.compile(r"\n[ \t]*\n"))}


def units(text, spans, sep):
    """Morceaux [début, fin) du texte entre séparateurs, fusionnés quand une entité enjambe un séparateur ;
    morceaux vides (blancs seuls) retirés."""
    pieces, pos = [], 0
    for m in (re.finditer(re.escape(sep), text) if isinstance(sep, str) else sep.finditer(text)):
        pieces.append([pos, m.start()])
        pos = m.end()
    pieces.append([pos, len(text)])
    starts = sorted((s, e) for s, e, _ in spans)
    out, k, maxend = [], 0, -1
    for p in pieces:
        # entités commencées avant ce morceau : si l'une finit après la fin du morceau précédent, elle enjambe
        while k < len(starts) and starts[k][0] < p[0]:
            maxend = max(maxend, starts[k][1])
            k += 1
        if out and maxend > out[-1][1]:
            out[-1][1] = p[1]
        else:
            out.append(p)
    return [u for u in out if text[u[0]:u[1]].strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalized", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    stats_path = os.path.join(a.out, "stats.csv")
    old = {r["key"]: r for r in csv.DictReader(open(stats_path, encoding="utf-8"))} if os.path.exists(stats_path) else {}
    for key, src, lang, matrice, mapping in CORPUS:
        if a.only and key not in a.only:
            continue
        st = collections.Counter()
        with open(os.path.join(a.normalized, f"{src}.jsonl"), encoding="utf-8") as fi, \
                open(os.path.join(a.out, f"{key}.jsonl"), "w", encoding="utf-8") as fo:
            for line in fi:
                d = json.loads(line)
                sp = translate(d, mapping)
                if key in UNIT:
                    us = units(d["text"], sp, UNIT[key][1])
                    inside = sum(1 for s, e, _ in sp if any(u0 <= s and e <= u1 for u0, u1 in us))
                    assert inside == len(sp), (key, d["doc_id"], "entité hors unité")
                else:
                    us = [[0, len(d["text"])]]
                fo.write(json.dumps({"doc_id": d["doc_id"], "page_id": d.get("page_id"), "split": d.get("split"),
                                     "lang": lang, "text": d["text"], "spans": [list(x) for x in sp],
                                     "units": us}, ensure_ascii=False) + "\n")
                st["docs"] += 1
                st["units"] += len(us)
                for x in sp:
                    st[x[2]] += 1
        old[key] = {"key": key, "source": src, "langue": lang, "matrice": matrice, "docs": st["docs"],
                    "units": st["units"], "PER": st["PER"], "LOC": st["LOC"], "correspondance": corr(mapping)}
        print(old[key], flush=True)
    order = [c[0] for c in CORPUS]
    with open(stats_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "source", "langue", "matrice", "docs", "units", "PER", "LOC",
                                           "correspondance"])
        w.writeheader()
        w.writerows(sorted(old.values(), key=lambda r: order.index(r["key"])))


def corr(mapping):
    if not isinstance(mapping, dict):
        return MPOPP_CORR
    return " ; ".join(f"{' + '.join(k for k in mapping if mapping[k] == v)} -> {v}" for v in ("PER", "LOC"))


if __name__ == "__main__":
    main()
