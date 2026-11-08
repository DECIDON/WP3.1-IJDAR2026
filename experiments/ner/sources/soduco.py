"""SoDUCo / French Trade Directories : benchmark plat (DAS 2022) et imbriqué (ICDAR 2023).

Doc = entrée d'annuaire ; page_id = <annuaire>-<page>. Annotations XML-like décodées par soduco_xml.
Lancer : uv run --with pandas --with pyarrow python loaders/soduco.py
"""
import collections
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from soduco_xml import parse_xml  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.environ["IJDAR_RAW"]
OUT = os.environ["IJDAR_NORMALIZED"]


def write(key, docs, meta):
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    meta = {"key": key, **meta}
    json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
    print(key, len(docs), sum(len(d["spans"]) for d in docs))


def ids(e):
    return f"{e['book']}-{e['page']}-{e['id']}", f"{e['book']}-{e['page']}"


# ---------------------------------------------------------------- plat (DAS 2022, Zenodo 6394464)
FTD = "https://doi.org/10.5281/zenodo.6394464 (french_trade_directories_19th_century_v1.0.0.zip)"
SHEETS_FLAT = ["Datasets NER français#19", "Datasets Structured Output#1"]

docs = []
for e in json.load(open(f"{RAW}/soduco-flat/10-all_entries_ocr_ner_human.json")):
    text, spans = parse_xml(e["ner_xml"])
    assert text == e["text_ocr"], e
    did, pid = ids(e)
    docs.append({"doc_id": did, "page_id": pid, "split": None, "text": text,
                 "spans": [s[:3] for s in spans]})
write("soduco-flat", docs, {
    "dataset": "SoDUCo — French Trade Directories (FTD), benchmark NER plat", "sous_corpus": "texte de référence (corrigé)",
    "sheets": SHEETS_FLAT, "unite_doc": "entrée d'annuaire",
    "source": FTD + " : labeled/10-all_entries_ocr_ner_human.json", "version": "v1.0.0 (2022-05)",
    "annotation": "gold",
    "remarques": ("8765 entrées / 78 pages / 18 annuaires ; tags XML plats (pas d'imbrication) ; "
                  "U+2029 -> \\n, entités XML décodées ; texte reconstitué = text_ocr à l'identique. "
                  "Pas de split publié dans le dépôt (le split DAS22 est calculé par le code du papier) -> split null. "
                  "Le libellé TITRE de la fiche = 'TITRE' dans la source."),
    "published": {"tokens": None, "mentions": 34242, "docs": 8765}})

docs = []
n_all = 0
for e in json.load(open(f"{RAW}/soduco-flat/31-all_entries_ner_align_pero.json")):
    n_all += 1
    if not e["has_valid_ner_xml"]:
        continue
    text, spans = parse_xml(e["ner_xml"])
    did, pid = ids(e)
    docs.append({"doc_id": did, "page_id": pid, "split": None, "text": text,
                 "spans": [s[:3] for s in spans]})
write("soduco-flat-ocr", docs, {
    "dataset": "SoDUCo — French Trade Directories (FTD), benchmark NER plat", "sous_corpus": "OCR PERO bruité (NER projeté)",
    "sheets": SHEETS_FLAT, "unite_doc": "entrée d'annuaire",
    "source": FTD + " : labeled/31-all_entries_ner_align_pero.json", "version": "v1.0.0 (2022-05)",
    "annotation": "gold projeté sur OCR (alignement automatique)",
    "remarques": (f"Version OCR PERO (meilleur moteur du papier DAS22) ; gold de référence projeté par alignement. "
                  f"Entrées à projection invalide (has_valid_ner_xml=false) exclues comme le demande le README : "
                  f"{len(docs)}/{n_all} gardées. Variantes Tesseract (32-) et Kraken (33-) non converties. "
                  "Le texte OCR n'est PAS identique au texte de référence (substitutions, coupures). "
                  "Quelques spans projetés vides (ex. <CARDINAL> </CARDINAL>) gardés tels quels si non vides."),
    "published": {"tokens": None, "mentions": None, "docs": None}})

# ---------------------------------------------------------------- imbriqué (ICDAR 2023, Zenodo 8167628 + splits HF nlpso)
key = lambda s: re.sub(r"\s+", "", s).replace("``", '"').replace("''", '"')
hf_split = collections.defaultdict(list)
for sp in ["train", "dev", "test"]:
    for toks in pd.read_parquet(f"{RAW}/soduco-nested/m1/{sp}.parquet").tokens:
        hf_split[key("".join(toks))].append(sp)
n_hf = sum(len(v) for v in hf_split.values())

DUP = re.compile(r"(<SPAT>.*?</SPAT>)\1")
nested, niv1 = [], []
n_dup_fixed = n_excl = 0
for e in json.load(open(f"{RAW}/soduco-nested/dataset_SODUCO_nested_ner.json")):
    if not e["has_valid_ner_xml_pero"]:
        n_excl += 1
        continue
    x = e["nested_ner_xml_ref"]
    text, spans = parse_xml(x)
    if text != e["text_ocr_ref"]:
        x = DUP.sub(r"\1", x)
        text, spans = parse_xml(x)
        assert text == e["text_ocr_ref"], e
        n_dup_fixed += 1
    sp = hf_split[key(text)].pop(0)
    did, pid = ids(e)
    nested.append({"doc_id": did, "page_id": pid, "split": sp, "text": text, "spans": [s[:3] for s in spans]})
    niv1.append({"doc_id": did, "page_id": pid, "split": sp, "text": text,
                 "spans": [s[:3] for s in spans if s[3] == 0]})
assert not any(hf_split.values()), "entrées HF non appariées"
assert len(nested) == n_hf == 8445

NEST_SRC = ("https://doi.org/10.5281/zenodo.8167628 (dataset_SODUCO_nested_ner.json, champ nested_ner_xml_ref) "
            "+ splits de https://huggingface.co/datasets/nlpso/m1_fine_tuning_ref_cmbert_iob2")
NEST_REM = (f"Source = JSON Zenodo (texte de référence + XML imbriqué, avec annuaire/page) plutôt que les datasets HF "
            f"pré-tokenisés ; splits train/dev/test repris des datasets HF nlpso (appariement 8445/8445 sur le texte sans espaces). "
            f"Comme dans le papier, seules les entrées à projection PERO valide sont gardées "
            f"({n_excl} exclues sur 8765). {n_dup_fixed} entrées avaient un bloc <SPAT> dupliqué dans le XML "
            f"(texte != text_ocr_ref) : doublon retiré. ")
SHEETS_NEST = ["Datasets NER français#20", "Datasets Structured Output#2"]
write("soduco-nested", nested, {
    "dataset": "SoDUCo — French Trade Directories, benchmark NER imbriqué (ICDAR 2023)", "sous_corpus": "niv. 1 + niv. 2",
    "sheets": SHEETS_NEST, "unite_doc": "entrée d'annuaire", "source": NEST_SRC, "version": "Zenodo 8167628 (2023-04-25)",
    "annotation": "gold",
    "remarques": NEST_REM + ("Spans des deux niveaux avec leur label réel : niv. 1 PER ACT DESC SPAT TITRE, "
                             "niv. 2 LOC CARDINAL FT ACT TITRE-H TITRE-P (ACT existe aux deux niveaux) -> 10 classes. "
                             "Dérogation voulue au CONTRAT (label = 1er niveau) ; la version conforme est soduco-nested-niv1. "
                             "Écart au chiffre publié (32 956 mentions) : il exclut les conteneurs SPAT et DESC "
                             "(41 978 - 8 655 SPAT - 371 DESC = 32 952, à 4 près). Comptes par label identiques aux tags "
                             "IOB2 des datasets HF à 5 TITRE-P près."),
    "published": {"tokens": None, "mentions": 32956, "docs": 8445}})
write("soduco-nested-niv1", niv1, {
    "dataset": "SoDUCo — French Trade Directories, benchmark NER imbriqué (ICDAR 2023)", "sous_corpus": "niv. 1 seul",
    "sheets": SHEETS_NEST, "unite_doc": "entrée d'annuaire", "source": NEST_SRC, "version": "Zenodo 8167628 (2023-04-25)",
    "annotation": "gold",
    "remarques": NEST_REM + "Spans de niveau 1 seulement (PER ACT DESC SPAT TITRE) ; les niv. 2 sont dans soduco-nested.",
    "published": {"tokens": None, "mentions": None, "docs": 8445}})
