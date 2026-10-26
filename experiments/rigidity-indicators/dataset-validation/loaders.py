"""Chargement des datasets IJDAR 2026 dans un format commun.

Chaque document devient un dict {dataset, doc_id, lang, text, entities}, où entities est une liste de
(début, fin, étiquette d'origine) en offsets caractères dans text. Le texte garde les sauts de ligne
quand la source les fournit. Les fichiers bruts sont dans data/ (voir data/README.md).

Usage : python loaders.py  -> écrit data/pivot/<dataset>.jsonl et affiche un résumé.
"""
import csv
import glob
import json
import os
import random
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
PIVOT = os.path.join(DATA, "pivot")


def _doc(dataset, doc_id, lang, text, entities):
    return {"dataset": dataset, "doc_id": str(doc_id), "lang": lang, "text": text, "entities": entities}


def _detok(tokens, labels=None):
    """Recolle une liste de tokens sans information d'espacement ; renvoie le texte et les spans BIO/IO."""
    no_space_before = set(".,;:!?)]}%»”") | {"'s", "n't", "'re", "'ll", "'ve", "'m", "'d"}
    no_space_after = set("([{«“")
    out, offsets, prev = [], [], None
    pos = 0
    for tok in tokens:
        if prev is not None and tok not in no_space_before and prev not in no_space_after and not prev.endswith("'"):
            out.append(" ")
            pos += 1
        offsets.append((pos, pos + len(tok)))
        out.append(tok)
        pos += len(tok)
        prev = tok
    text = "".join(out)
    ents = _spans_from_tags(offsets, labels) if labels is not None else []
    return text, ents


def _spans_from_tags(offsets, labels):
    """Spans à partir d'étiquettes BIO ou IO (un I- qui change de type ouvre une nouvelle entité)."""
    ents, cur = [], None
    for (s, e), lab in zip(offsets, labels):
        if lab == "O" or not lab:
            if cur: ents.append(tuple(cur)); cur = None
            continue
        bio, _, typ = lab.partition("-")
        if not typ:
            bio, typ = "I", lab
        if bio == "B" or cur is None or cur[2] != typ:
            if cur: ents.append(tuple(cur))
            cur = [s, e, typ]
        else:
            cur[1] = e
    if cur: ents.append(tuple(cur))
    return ents


# --- HIPE-2022 (hipe2020, letemps, newseye, ajmc) -------------------------------------------------
def load_hipe(collection, lang):
    files = sorted(glob.glob(os.path.join(DATA, "hipe2022", "data", "v2.1", collection, lang, "*.tsv")))
    files = [f for f in files if re.search(r"-(train|dev|dev2|test)-%s\.tsv$" % lang, f)]
    docs = []
    for f in files:
        out, offsets, labels, doc_id = [], [], [], None
        pos = 0

        def flush():
            if doc_id and out:
                docs.append(_doc(f"{collection}-{lang}", doc_id, lang, "".join(out).rstrip(), _spans_from_tags(offsets, labels)))

        col = None
        for line in open(f, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("TOKEN\t"):
                col = line.split("\t").index("NE-COARSE-LIT")
                continue
            if line.startswith("# hipe2022:document_id"):
                flush()
                out, offsets, labels, pos = [], [], [], 0
                doc_id = line.split("=", 1)[1].strip()
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            tok, misc = parts[0], parts[-1]
            offsets.append((pos, pos + len(tok)))
            labels.append(parts[col])
            out.append(tok)
            pos += len(tok)
            sep = "\n" if "EndOfLine" in misc else ("" if "NoSpaceAfter" in misc else " ")
            out.append(sep)
            pos += len(sep)
        flush()
    # le test « non masqué » et les dev2 peuvent recouvrir d'autres fichiers : on dédoublonne par identifiant
    seen, uniq = set(), []
    for d in docs:
        if d["doc_id"] not in seen:
            seen.add(d["doc_id"]); uniq.append(d)
    return uniq


# --- SoDUCo : une page d'annuaire = un document ----------------------------------------------------
_XML_TAG = re.compile(r"</?([A-Z_-]+)>")  # TITRE-H, TITRE-P : avec tiret


def _parse_inline_xml(xml):
    """Texte et spans de premier niveau d'une entrée SoDUCo (balises imbriquées,   = saut de ligne)."""
    xml = xml.replace(" ", "\n")
    out, stack, ents, pos, i = [], [], [], 0, 0
    for m in _XML_TAG.finditer(xml):
        chunk = unicodedata.normalize("NFC", xml[i:m.start()].replace("&apos;", "'").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
        out.append(chunk); pos += len(chunk); i = m.end()
        if m.group(0).startswith("</"):
            if stack:
                typ, start = stack.pop()
                if not stack:  # entités de premier niveau seulement
                    ents.append((start, pos, typ))
        else:
            stack.append((m.group(1), pos))
    tail = xml[i:].replace("&apos;", "'").replace("&amp;", "&")
    out.append(tail)
    return "".join(out), ents


def load_soduco(variant="ref"):
    data = json.load(open(os.path.join(DATA, "soduco", "dataset_SODUCO_nested_ner.json"), encoding="utf-8"))
    pages = defaultdict(list)
    for e in data:
        if variant == "pero" and str(e.get("has_valid_ner_xml_pero")) != "True":
            continue
        pages[(e["book"], int(e["page"]))].append(e)
    docs = []
    for (book, page), entries in sorted(pages.items()):
        entries.sort(key=lambda e: int(e["id"]))
        text, ents = "", []
        for e in entries:
            t, es = _parse_inline_xml(e[f"nested_ner_xml_{variant}"])
            if text:
                text += "\n"
            ents += [(s + len(text), x + len(text), typ) for s, x, typ in es]
            text += t
        docs.append(_doc(f"soduco-{variant}", f"{book}_p{page}", "fr", text, ents))
    return docs


# --- M-POPP : une page = un document ; préfixes emoji = étiquettes (encodage 1) --------------------
_MPOPP_PER = {"💬", "🗨"}
_MPOPP_LOC = {"🌇", "🗺", "🔟", "🛣", "🔠", "🌍"}


def _mpopp_is_tag(c):
    return not (c.isalnum() or c.isspace()) and unicodedata.category(c) == "So"


def load_mpopp(subset):
    path = os.path.join(DATA, "m-popp", "m-popp_datasets", subset, "labels", f"labels-{subset}-encoding-1.json")
    gt = json.load(open(path, encoding="utf-8"))["ground_truth"]
    docs = []
    for split in ("train", "valid", "test"):
        for page, v in gt[split].items():
            text_out, ents, cur, pos = [], [], None, 0
            for piece in re.split(r"(\s+)", v["text"]):
                if not piece:
                    continue
                if piece.isspace():
                    text_out.append(piece); pos += len(piece)
                    continue
                k = 0
                while k < len(piece) and _mpopp_is_tag(piece[k]):
                    k += 1
                prefix, word = piece[:k], piece[k:]
                # le premier symbole de l'encodage 1 est le champ, la suite le contexte (rôle, adresse…)
                field = next((c for c in prefix if c not in "ⓟⓜⓑⓘⓝⓢⓅⓂⒷⒾⓃⓈ"), None)
                cls = "PER" if field in _MPOPP_PER else "LOC" if field in _MPOPP_LOC else ("OTHER" if field else None)
                ctx = prefix[prefix.index(field) + 1:] if field else ""
                core = word.rstrip(".,;:*-")
                if cls and core:
                    gap = "".join(text_out)[cur[1]:] if cur else ""
                    if cur and cur[2] == cls and cur[3] == ctx and not gap.strip(" ,.;:-'"):
                        cur[1] = pos + len(core)
                    else:
                        if cur: ents.append(tuple(cur[:3]))
                        cur = [pos, pos + len(core), cls, ctx]
                elif word.strip(".,;:*-'\"()"):
                    if cur: ents.append(tuple(cur[:3])); cur = None
                text_out.append(word); pos += len(word)
            if cur: ents.append(tuple(cur[:3]))
            docs.append(_doc(f"m-popp-{subset}", page, "fr", "".join(text_out), [e for e in ents if e[2] != "OTHER"]))
    return docs


# --- 7romans : un roman = un document (phrases recollées, sans information d'espacement) ------------
def load_7romans():
    import pandas as pd
    names = ["B-LOC", "B-MISC", "B-ORG", "B-PER", "I-LOC", "I-MISC", "I-ORG", "I-PER", "O"]
    df = pd.read_parquet(os.path.join(DATA, "7romans", "train-00000-of-00001.parquet"))
    docs = []
    for novel, g in df.groupby("novel", sort=False):
        toks, labs = [], []
        for t, l in zip(g["tokens"], g["labels"]):
            toks += list(t); labs += [names[i] for i in l]
        text, ents = _detok(toks, labs)
        docs.append(_doc("7romans", novel, "fr", text, ents))
    return docs


# --- GeoEDdA : les paragraphes d'un même volume, dans l'ordre des articles --------------------------
def load_geoedda():
    paras = []
    for split in ("train", "val", "test"):
        for line in open(os.path.join(DATA, "geoedda", f"{split}.jsonl"), encoding="utf-8"):
            paras.append(json.loads(line))
    by_vol = defaultdict(list)
    for p in paras:
        m = p["meta"]
        by_vol[m["volume"]].append(p)
    docs = []
    for vol, ps in sorted(by_vol.items()):
        ps.sort(key=lambda p: (p["meta"]["article"], p["meta"]["paragraph"]))
        text, ents = "", []
        for p in ps:
            if text:
                text += "\n\n"
            ents += [(s["start"] + len(text), s["end"] + len(text), s["label"]) for s in p.get("spans", [])]
            text += p["text"]
        docs.append(_doc("geoedda", f"vol{vol}", "fr", text, ents))
    return docs


# --- formats brat (LitBank, COPIOUS, NEM.fr) --------------------------------------------------------
def _read_ann(path):
    ents = []
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if not parts[0].startswith("T") or len(parts) < 3:
            continue
        if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():  # variante NEM.fr : T1 \t LAB \t s \t e
            lab, spans = parts[1], [(int(parts[2]), int(parts[3]))]
        else:
            lab, _, rest = parts[1].partition(" ")
            spans = [tuple(map(int, frag.split())) for frag in rest.split(";")]
        ents.append((spans[0][0], spans[-1][1], lab))
    return ents


def load_brat(dataset, pattern, lang, doc_id=lambda p: os.path.basename(p)[:-4]):
    docs = []
    for txt in sorted(glob.glob(pattern)):
        ann = txt[:-4] + ".ann"
        text = open(txt, encoding="utf-8").read()
        ents = [e for e in (_read_ann(ann) if os.path.exists(ann) else []) if 0 <= e[0] < e[1] <= len(text)]
        docs.append(_doc(dataset, doc_id(txt), lang, text, ents))
    return docs


def load_litbank():
    return load_brat("litbank", os.path.join(DATA, "litbank", "entities", "brat", "*.txt"), "en")


def load_copious():
    return load_brat("copious", os.path.join(DATA, "copious", "copious_published", "*", "*.txt"), "en")


def load_nem(genre):
    files = os.path.join(DATA, "nem-fr", "texts", "*.txt")
    docs = []
    for txt in sorted(glob.glob(files)):
        name = os.path.basename(txt)[:-4]
        g = re.match(r"[a-z]+", name).group(0)
        if g != genre:
            continue
        ann = os.path.join(DATA, "nem-fr", "named_entities_annotations", name + ".ann")
        docs.append(_doc(f"nem-{genre}", name, "fr", open(txt, encoding="utf-8").read(), _read_ann(ann) if os.path.exists(ann) else []))
    return docs


NEM_GENRES = ["prose", "poetry", "multi", "information", "encyclopedia", "spoken", "politique", "juridique",
              "biomedical", "tweets", "defense", "mail"]


# --- E-NER : CSV token,étiquette (IO), documents séparés par -DOCSTART- -------------------------------
def load_ener():
    docs, toks, labs, n = [], [], [], 0
    with open(os.path.join(DATA, "e-ner", "all.csv"), encoding="utf-8", newline="") as f:
        rows = csv.reader(f)
        next(rows)
        for row in rows:
            if not row:
                continue
            tok, lab = (",".join(row[:-1]), row[-1]) if len(row) > 2 else (row[0], row[1] if len(row) > 1 else "O")
            if tok == "-DOCSTART-":
                if toks:
                    text, ents = _detok(toks, labs); docs.append(_doc("e-ner", n, "en", text, ents)); n += 1
                toks, labs = [], []
                continue
            if tok:
                toks.append(tok); labs.append(lab)
    if toks:
        text, ents = _detok(toks, labs); docs.append(_doc("e-ner", n, "en", text, ents))
    return docs


# --- TEI (Basel, Old Bailey) -------------------------------------------------------------------------
def _tei_text(elem, keep, block_tags, out=None, ents=None):
    """Parcourt un élément TEI : texte (espaces normalisés), sauts de ligne sur <lb/> et blocs, spans des balises keep."""
    if out is None:
        out, ents = [], []
    tag = elem.tag.split("}")[-1]
    if tag in ("interp", "join", "note", "teiHeader"):
        if elem.tail:
            out.append(re.sub(r"\s+", " ", elem.tail))
        return out, ents
    if tag == "lb":
        out.append("\n")
    start = len("".join(out))
    if elem.text:
        out.append(re.sub(r"\s+", " ", elem.text))
    for child in elem:
        _tei_text(child, keep, block_tags, out, ents)
    if tag in keep:
        s, e = start, len("".join(out))
        txt = "".join(out)
        while s < e and txt[s].isspace(): s += 1
        while e > s and txt[e - 1].isspace(): e -= 1
        if e > s:
            ents.append((s, e, elem.get("type") or tag))
    if tag in block_tags:
        out.append("\n")
    if elem.tail:
        out.append(re.sub(r"\s+", " ", elem.tail))
    return out, ents


def _clean_layout(text, ents):
    """Espaces multiples réduits à un, espaces en bord de ligne et lignes vides supprimés ; offsets recalculés."""
    out, pos_map = [], {}
    for i, c in enumerate(text):
        pos_map[i] = len(out)
        if c == "\n":
            while out and out[-1] == " ":
                out.pop()
            if out and out[-1] != "\n":
                out.append("\n")
        elif c.isspace():
            if out and out[-1] not in " \n":
                out.append(" ")
        else:
            out.append(c)
    pos_map[len(text)] = len(out)
    while out and out[-1] in " \n":
        out.pop()
    new_text = "".join(out)
    new_ents = []
    for s, e, lab in ents:
        a, b = min(pos_map[s], len(new_text)), min(pos_map[e], len(new_text))
        while a < b and new_text[a].isspace(): a += 1
        while b > a and new_text[b - 1].isspace(): b -= 1
        if b > a:
            new_ents.append((a, b, lab))
    return new_text, new_ents


BASEL_SKIPPED = []


def load_basel():
    by_group = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(DATA, "basel", "tei_simple", "tei_simple", "*.xml"))):
        try:
            # les fichiers déclarent encoding='UTF8', que expat refuse : on décode nous-mêmes
            raw = re.sub(r"^<\?xml[^>]*\?>", "", open(f, encoding="utf-8").read())
            body = ET.fromstring(raw).find(".//{http://www.tei-c.org/ns/1.0}body")
        except ET.ParseError:
            BASEL_SKIPPED.append(os.path.basename(f))
            continue
        if body is None:
            continue
        out, ents = _tei_text(body, {"persName", "placeName"}, {"ab", "p"})
        text, ents = _clean_layout("".join(out), ents)
        group = "_".join(os.path.basename(f).split("_")[:3])
        by_group[group].append((text, ents))
    docs = []
    for g, recs in sorted(by_group.items()):
        text, ents = "", []
        for t, es in recs:
            if text:
                text += "\n\n"
            ents += [(s + len(text), e + len(text), l) for s, e, l in es]
            text += t
        docs.append(_doc("basel", g, "de", text, ents))
    return docs


def load_old_bailey(n_sessions=40, seed=0):
    """Procès (trialAccount) d'un échantillon de sessions 1834-1913, réparties régulièrement dans le temps."""
    files = sorted(f for f in glob.glob(os.path.join(DATA, "old-bailey", "sessionsPapers", "*.xml"))
                   if "1834" <= os.path.basename(f)[:4] <= "1913")
    step = len(files) / n_sessions
    files = [files[int(k * step)] for k in range(n_sessions)]
    docs = []
    for f in files:
        root = ET.parse(f).getroot()
        for div in root.iter("div1"):
            if div.get("type") != "trialAccount":
                continue
            out, ents = _tei_text(div, {"persName", "placeName"}, {"p"})
            text, ents = _clean_layout("".join(out), ents)
            if text:
                docs.append(_doc("old-bailey", div.get("id"), "en", text, ents))
    return docs


# --- registre des datasets ----------------------------------------------------------------------------
DATASETS = {
    "hipe2020-fr": lambda: load_hipe("hipe2020", "fr"),
    "hipe2020-en": lambda: load_hipe("hipe2020", "en"),
    "hipe2020-de": lambda: load_hipe("hipe2020", "de"),
    "letemps-fr": lambda: load_hipe("letemps", "fr"),
    "newseye-fr": lambda: load_hipe("newseye", "fr"),
    "newseye-fi": lambda: load_hipe("newseye", "fi"),
    "newseye-sv": lambda: load_hipe("newseye", "sv"),
    "ajmc-fr": lambda: load_hipe("ajmc", "fr"),
    "ajmc-en": lambda: load_hipe("ajmc", "en"),
    "ajmc-de": lambda: load_hipe("ajmc", "de"),
    "soduco-ref": lambda: load_soduco("ref"),
    "soduco-pero": lambda: load_soduco("pero"),
    "m-popp-printed": lambda: load_mpopp("printed"),
    "m-popp-handwritten": lambda: load_mpopp("handwritten"),
    "7romans": load_7romans,
    "geoedda": load_geoedda,
    "litbank": load_litbank,
    "e-ner": load_ener,
    "copious": load_copious,
    "basel": load_basel,
    "old-bailey": load_old_bailey,
    **{f"nem-{g}": (lambda g=g: load_nem(g)) for g in NEM_GENRES},
}


def load_pivot(name):
    """Charge un dataset depuis le cache data/pivot/ (le crée au besoin)."""
    path = os.path.join(PIVOT, f"{name}.jsonl")
    if not os.path.exists(path):
        os.makedirs(PIVOT, exist_ok=True)
        docs = DATASETS[name]()
        with open(path, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return [json.loads(l) for l in open(path, encoding="utf-8")]


if __name__ == "__main__":
    for name in DATASETS:
        docs = load_pivot(name)
        words = sum(len(re.findall(r"[^\W_]+", d["text"])) for d in docs)
        n_ent = sum(len(d["entities"]) for d in docs)
        bad = sum(1 for d in docs for s, e, _ in d["entities"] if not (0 <= s < e <= len(d["text"])))
        labels = defaultdict(int)
        for d in docs:
            for _, _, l in d["entities"]:
                labels[l] += 1
        top = ", ".join(f"{k}:{v}" for k, v in sorted(labels.items(), key=lambda x: -x[1])[:5])
        print(f"{name:20s} docs={len(docs):5d} words={words:8d} entities={n_ent:6d} out_of_bounds={bad} | {top}")
