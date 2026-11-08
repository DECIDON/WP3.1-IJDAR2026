"""NEM.fr (Named-Entities Multigenre French Corpus, extension de FENEC) : brat standoff, 12 genres.

Source : github.com/ayusekyo111/NEM.fr (clone dans raw/nem-fr). Doc = échantillon (fichier .txt,
~1 000 tokens ; discours et mails gardent leur découpage naturel). Une key pour le corpus entier
(`nem-fr`) et une par genre (`nem-fr-<genre>`), genre = préfixe du nom de fichier.

- Le pseudo-label `true` (33 spans, tweets seulement) double à l'identique une entité déjà étiquetée
  (marqueur de hashtag) : ignoré.
- Tweets : les offsets des .ann ne correspondent plus au .txt publié (texte anonymisé après annotation,
  `@XXX`) → chaque mention est ré-ancrée sur sa surface (recherche tolérante aux espaces, dans l'ordre
  des offsets d'origine). Les autres genres ont des offsets justes (la surface .ann est tokenisée).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["IJDAR_RAW"], "nem-fr")
OUT = os.environ["IJDAR_NORMALIZED"]
GENRE = {"prose": "prose", "poetry": "poetry", "multi": "multisources", "information": "information",
         "encyclopedia": "encyclopedia", "spoken": "spoken", "politique": "political", "juridique": "legal",
         "biomedical": "biomedical", "tweets": "tweets", "defense": "defense", "mail": "mail"}
LABELS = {"PERS", "LOC", "ORG", "TIME", "PROD", "EVENT"}


def read(stem):
    text = open(f"{RAW}/texts/{stem}.txt", encoding="utf-8", newline="").read()
    ents = []
    for line in open(f"{RAW}/named_entities_annotations/{stem}.ann", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if p[0].startswith("T") and p[1] in LABELS:
            ents.append((int(p[2]), int(p[3]), p[1], p[4]))
    return text, ents


def realign(text, ents):
    """Ré-ancre chaque surface : 1re occurrence à partir du début de la mention précédente."""
    spans, lost, moved, cur = [], 0, 0, 0
    for s, e, lab, form in sorted(ents):
        if re.sub(r"\s", "", text[s:e]) == re.sub(r"\s", "", form):
            spans.append([s, e, lab])
            continue
        pat = r"\s*".join(map(re.escape, re.sub(r"[\s#]", "", form)))
        m = re.compile(pat, re.I).search(text, cur) or re.compile(pat, re.I).search(text)
        if m:
            spans.append([m.start(), m.end(), lab])
            cur, moved = m.start(), moved + 1
        else:
            lost += 1
    return spans, lost, moved


def main():
    stems = sorted(f[:-4] for f in os.listdir(f"{RAW}/named_entities_annotations") if f.endswith(".ann"))
    by_genre, lost_tot, moved = {}, 0, 0
    for stem in stems:
        genre = GENRE[re.match(r"[a-z]+", stem).group()]
        text, ents = read(stem)
        spans, lost, mv = realign(text, ents)
        lost_tot, moved = lost_tot + lost, moved + mv
        by_genre.setdefault(genre, []).append({"doc_id": stem, "page_id": None, "split": None, "text": text,
                                               "spans": spans})
    common = {"dataset": "NEM.fr", "unite_doc": "échantillon (~1 000 tokens ; discours et mails entiers)",
              "source": "https://github.com/ayusekyo111/NEM.fr", "version": "commit df04538 (2026-02-09)",
              "annotation": "gold",
              "remarques": (f"brat ; labels PERS/LOC/ORG/TIME/PROD/EVENT, imbrication gardée ; pseudo-label `true` "
                            f"(33, marqueur de hashtag doublant une entité) ignoré ; tweets : offsets .ann décalés "
                            f"par l'anonymisation → ré-ancrés sur la surface ({lost_tot} mention(s) non retrouvée(s)). "
                            f"Pas de split. Dépôt sans licence globale : licence par source (data_statements.csv).")}
    for key, docs, sous in [("nem-fr", [d for g in by_genre.values() for d in g], "12 genres")] + [
            (f"nem-fr-{g}", docs, g) for g, docs in sorted(by_genre.items())]:
        with open(f"{OUT}/{key}.jsonl", "w") as fh:
            for d in docs:
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        meta = {"key": key, "sous_corpus": sous, "sheets": ["Synthèse des datasets#NEM.fr"] if key == "nem-fr" else [],
                **common, "published": {"tokens": 51480 if key == "nem-fr" else None, "mentions": None,
                                        "docs": None}}
        json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
    print({g: len(d) for g, d in by_genre.items()}, "non retrouvées", lost_tot, "ré-ancrées", moved)


if __name__ == "__main__":
    main()
