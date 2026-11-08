"""E-NER (Au et al. 2022) : 52 dépôts SEC EDGAR annotés en 7 classes.

Source : dépôt GitHub, all.csv (version 7 classes ; edgar_all_4.csv = même données réduites à 4 classes,
non utilisée). Format CSV `token,tag`, `-DOCSTART-` entre documents, ligne vide (`,O`) entre phrases.
Étiquetage IOB1 (I- partout, B- seulement entre deux entités adjacentes de même type).
Doc = dépôt EDGAR (document).
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["IJDAR_RAW"], "e-ner", "all.csv")
OUT = os.environ["IJDAR_NORMALIZED"]
KEY = "e-ner"
LABELS = {"PERSON", "COURT", "BUSINESS", "GOVERNMENT", "LOCATION", "LEGISLATION/ACT", "MISCELLANEOUS"}
ALIAS = {"LOC": "LOCATION"}

docs, cur_doc = [], None
for row in csv.reader(open(RAW, encoding="utf-8")):
    if len(row) != 2:
        continue
    tok, tag = row
    if tok == "-DOCSTART-":
        cur_doc = []
        docs.append(cur_doc)
        continue
    cur_doc.append((tok, tag.strip()))

dropped = 0
with open(f"{OUT}/{KEY}.jsonl", "w") as fh:
    for i, toks in enumerate(docs):
        text, spans, cur, nl = "", [], None, False
        for tok, tag in toks:
            if tok == "":
                nl, cur = True, None
                continue
            if text:
                text += "\n" if nl else " "
            nl = False
            s = len(text)
            text += tok
            if tag == "O" or "-" not in tag:
                dropped += tag not in ("O", "")
                cur = None
                continue
            pre, lab = tag.split("-", 1)
            lab = ALIAS.get(lab, lab)
            if lab not in LABELS:
                dropped += 1
                cur = None
                continue
            if pre == "I" and cur is not None and cur[2] == lab:
                cur[1] = len(text)
            else:
                cur = [s, len(text), lab]
                spans.append(cur)
        fh.write(json.dumps({"doc_id": f"edgar-{i + 1:02d}", "page_id": None, "split": None, "text": text,
                             "spans": spans}, ensure_ascii=False) + "\n")
print(len(docs), "docs ; tokens à étiquette hors schéma ignorés :", dropped)

meta = {"key": KEY, "dataset": "E-NER", "sous_corpus": "SEC EDGAR filings", "sheets": ["Datasets NER anglais#9"],
        "unite_doc": "document (dépôt EDGAR)",
        "source": "https://github.com/terenceau2/E-NER-Dataset (all.csv ; dépôt redirigé vers terenceau1/E-NER-Dataset)",
        "version": "commit 4efb293 (2022-12-25)", "annotation": "gold",
        "remarques": ("Version 7 classes (all.csv). IOB1 décodé (I- continue, B- ouvre). 4 tokens étiquetés « P » "
                      "(coquille hors schéma) ignorés ; 1 « I-LOC » rattaché à LOCATION. Les identifiants des 52 "
                      "dépôts ne sont pas fournis : doc_id = rang dans all.csv. Pas de split publié."),
        "published": {"tokens": None, "mentions": 8820, "docs": 52}}
json.dump(meta, open(f"{OUT}/{KEY}.meta.json", "w"), ensure_ascii=False, indent=1)
