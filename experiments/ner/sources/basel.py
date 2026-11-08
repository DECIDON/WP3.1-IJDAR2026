"""The Basel Land Records Ground Truth (Prada Ziegler, Hitz, Fuchs 2025, Zenodo 16919653).

829 extraits (fiches de registre) en allemand pré-moderne, TEI.
  - basel-landrecords        : TEI imbriqué. Entités = <rs type=person|place|organization> à tous les
                               niveaux d'imbrication + valeurs <date> et <measure type=currency> (money).
                               Les éléments descriptifs (<seg> apposition/attribut, <name>, <roleName>)
                               ne sont pas des entités → ignorés.
  - basel-landrecords-simple : TEI simple (plat) : persName / placeName / orgName / date / measure.
Texte = contenu de <ab>, blancs (indentation XML) normalisés en une espace.
"""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["IJDAR_RAW"], "basel")
OUT = os.environ["IJDAR_NORMALIZED"]
NS = "{http://www.tei-c.org/ns/1.0}"


def label_nested(el):
    tag = el.tag.replace(NS, "")
    if tag == "rs":
        return el.get("type")
    if tag == "date":
        return "date"
    if tag == "measure":
        return "money"
    return None


def label_simple(el):
    tag = el.tag.replace(NS, "")
    return {"persName": "person", "placeName": "place", "orgName": "organization",
            "date": "date", "measure": "money"}.get(tag)


def convert(path, labeler):
    # en-tête « encoding='UTF8' » inconnu d'expat → on décode nous-mêmes et on retire la déclaration
    src = open(path, encoding="utf-8").read()
    root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", src.lstrip()))
    ab = root.find(f".//{NS}body/{NS}ab")
    buf, spans = [], []
    length = [0]

    def add(s):
        if not s:
            return
        s = re.sub(r"\s+", " ", s)
        if (not buf or buf[-1].endswith(" ")) and s.startswith(" "):
            s = s[1:]
        if s:
            buf.append(s)
            length[0] += len(s)

    def walk(el, top=False):
        start = length[0]
        add(el.text)
        for ch in el:
            walk(ch)
            add(ch.tail)
        lab = None if top else labeler(el)
        if lab:
            spans.append([start, length[0], lab])

    walk(ab, top=True)
    text = "".join(buf)
    out = []
    for s, e, lab in spans:
        while s < e and text[s] == " ":
            s += 1
        while e > s and text[e - 1] == " ":
            e -= 1
        if e > s:
            out.append([s, e, lab])
    stripped = text.rstrip(" ")
    return stripped, sorted(out), root


for key, sub, labeler, rem in [
    ("basel-landrecords", "tei_nested", label_nested,
     "TEI imbriqué : une span par <rs> (person / place / organization, GPE-ORG inclus dans organization, "
     "GPE et location et facility dans place) à tous les niveaux + valeurs date et money (<measure "
     "type=currency>). Appositions, attributs, têtes <name>/<roleName> ignorés (éléments descriptifs, pas des "
     "entités). Les « >30 000 annotations » publiées comptent aussi ces éléments descriptifs : non "
     "comparables aux mentions."),
    ("basel-landrecords-simple", "tei_simple", label_simple,
     "TEI simple (plat, noms propres seuls) : persName→person, placeName→place, orgName→organization, "
     "date, measure→money. Variante plate de basel-landrecords."),
]:
    n = 0
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for f in sorted(glob.glob(f"{RAW}/{sub}/*.tei.xml")):
            text, spans, root = convert(f, labeler)
            did = os.path.basename(f)[: -len(".tei.xml")]
            fh.write(json.dumps({"doc_id": did, "page_id": None, "split": None, "text": text, "spans": spans},
                                ensure_ascii=False) + "\n")
            n += 1
    print(key, n)
    meta = {"key": key, "dataset": "The Basel Land Records Ground Truth", "sous_corpus": sub,
            "sheets": ["Datasets NER anglais#Registres (Basel Land Records)",
                       "Synthèse des datasets#The Basel Land Records Ground Truth"],
            "unite_doc": "extrait de source (fiche de registre)",
            "source": f"https://zenodo.org/records/16919653 ({sub}.zip)", "version": "v0.1 (2025-08-21)",
            "annotation": "gold",
            "remarques": rem + " Doc = fichier TEI (un extrait), pas de page ni de split publiés. Texte "
                               "= contenu de <ab> (déjà tokenisé par espaces), blancs normalisés.",
            "published": {"tokens": 50000, "mentions": None, "docs": 829}}
    json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
