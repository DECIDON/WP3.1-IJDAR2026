"""Famille HIPE (format TSV HIPE) : HIPE-2022 v2.1 (sous-corpus x langue) et CLEF-HIPE-2020 v1.4 (fr).

Couches retenues (CONTRAT) : NE-COARSE-LIT + NE-NESTED, label = 1er niveau (avant le premier « . »).
Composants (comp.*) exclus. Fichiers *masked* et ajmc-entity-ocr-correction-*.tsv exclus.
Texte : tokens joints par une espace, "" si NoSpaceAfter, "\n" si EndOfLine (prioritaire).
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
H22 = os.path.join(os.environ["IJDAR_RAW"], "hipe2022/data/v2.1")
C20 = os.path.join(os.environ["IJDAR_RAW"], "clef-hipe2020-fr/data/v1.4/fr")
OUT = os.environ["IJDAR_NORMALIZED"]

H22_SRC = "https://github.com/hipe-eval/HIPE-2022-data (data/v2.1)"
H22_VER = "v2.1, commit {commit}"

DATASETS = {
    "hipe2022-hipe2020-fr": dict(dir=f"{H22}/hipe2020/fr", sous="hipe2020 (fr)", sheets=["Datasets NER français#3"],
                                 unite="article", page=False, pub={"tokens": 245026, "mentions": 10255, "docs": 244}),
    "hipe2022-letemps-fr": dict(dir=f"{H22}/letemps/fr", sous="letemps (fr)", sheets=["Datasets NER français#4"],
                                unite="article", page=False, pub={"tokens": 466600, "mentions": 11045, "docs": 516}),
    "hipe2022-newseye-fr": dict(dir=f"{H22}/newseye/fr", sous="newseye (fr)", sheets=["Datasets NER français#5"],
                                unite="page", page=True, pub={"tokens": 378111, "mentions": 15003, "docs": 140}),
    "hipe2022-ajmc-fr": dict(dir=f"{H22}/ajmc/fr", sous="ajmc (fr)", sheets=["Datasets NER français#17"],
                             unite="page", page=True, pub={"tokens": 35487, "mentions": 2372, "docs": 104}),
    "hipe2022-hipe2020-en": dict(dir=f"{H22}/hipe2020/en", sous="hipe2020 (en)", sheets=["Datasets NER anglais#7"],
                                 unite="article", page=False, pub=None),
    "hipe2022-ajmc-en": dict(dir=f"{H22}/ajmc/en", sous="ajmc (en)", sheets=["Datasets NER anglais#12"],
                             unite="page", page=True, pub={"tokens": 43490, "mentions": 2587, "docs": 87}),
    # autres langues des sous-corpus multilingues (sous-lignes de la fiche Synthèse)
    "hipe2022-hipe2020-de": dict(dir=f"{H22}/hipe2020/de", sous="hipe2020 (de)", sheets=["Synthèse des datasets#hipe2020"],
                                 unite="article", page=False, pub=None),
    "hipe2022-newseye-fi": dict(dir=f"{H22}/newseye/fi", sous="newseye (fi)", sheets=["Synthèse des datasets#newseye"],
                                unite="page", page=True, pub=None),
    "hipe2022-newseye-sv": dict(dir=f"{H22}/newseye/sv", sous="newseye (sv)", sheets=["Synthèse des datasets#newseye"],
                                unite="page", page=True, pub=None),
    "hipe2022-ajmc-de": dict(dir=f"{H22}/ajmc/de", sous="ajmc (de)", sheets=["Synthèse des datasets#ajmc"],
                             unite="page", page=True, pub=None),
}
LAYERS = ["NE-COARSE-LIT", "NE-NESTED"]
EXTRA = {
    "hipe2022-hipe2020-fr": "mentions 10902 vs 10255 publiées (+6,3 %) : le chiffre publié = NE-COARSE-LIT seul ; +647 spans NE-NESTED (surtout loc.adm.town, org.ent).",
    "hipe2022-letemps-fr": "mentions 11138 vs 11045 (+0,8 %) = +93 spans NE-NESTED.",
    "hipe2022-newseye-fr": "mentions 15758 vs 15003 (+5,0 %) : +755 spans NE-NESTED (ORG, LOC). 4 splits publiés : train, dev, dev2, test (35 docs chacun). Tokens retokenisés -2,9 % (fragments OCR '###...').",
    "hipe2022-ajmc-fr": "mentions 2381 vs 2372 = +9 NE-NESTED. Pas de métadonnée de page autre que l'id de document (= page).",
    "hipe2022-ajmc-en": "mentions 2591 vs 2587 = +4 NE-NESTED. La page sophoclesplaysa05campgoog_0146 figure 2 fois (identique) dans le train source : gardée telle quelle (87 docs, 86 page_id distincts). Métadonnée ajmc:page = n° de page imprimé, non utilisé (page_id = doc_id).",
    "hipe2022-topres19th-en": "455 docs (train 309, dev 34, test 112) vs 343 publiés = train+dev seulement ; mentions 4606 (train+dev 3419 vs 3364 publiées, -1,6 %). Pas de couche NE-NESTED dans ce sous-corpus (coarse seul).",
    "hipe2022-hipe2020-en": "dev + test seulement (pas de train en anglais) ; pas de couche NE-NESTED renseignée (colonne '_'). Pas de chiffre publié dans la fiche.",
    "clef-hipe2020-fr": "mentions 10901 vs 10923 publiées (-0,2 %). Même texte que hipe2022-hipe2020-fr (1 span de moins : 'Londres' étiqueté B-comp en coarse dans v1.4 l. 132222 du train, exclu car comp.*). Fichiers test-masked* exclus.",
}


def split_of(fname):
    m = re.search(r"-(train|dev2|dev|test)-", os.path.basename(fname))
    return m.group(1)


def iob_spans(tags, offs):
    """tags : liste de tags IOB ; offs : (start,end) char de chaque token. -> [(s,e,label)]"""
    spans, cur = [], None
    for tag, (s, e) in zip(tags, offs):
        if tag in ("O", "_", ""):
            if cur:
                spans.append(cur)
            cur = None
            continue
        pre, lab = tag.split("-", 1)
        lab = lab.split(".")[0]
        if pre == "B" or cur is None or cur[2] != lab:
            if cur:
                spans.append(cur)
            cur = [s, e, lab]
        else:
            cur[1] = e
    if cur:
        spans.append(cur)
    return [tuple(x) for x in spans if x[2] != "comp"]


def parse_file(path):
    docs, cols, cur = [], None, None

    def flush():
        if cur and cur["toks"]:
            docs.append(cur)

    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("TOKEN\t"):
            cols = line.split("\t")
            continue
        if not line.strip():
            continue
        if line.startswith("#") and "\t" not in line:
            if cur is None or cur["toks"]:
                flush()
                cur = {"meta": {}, "toks": []}
            m = re.match(r"#\s*([^=]+?)\s*=\s*(.*)$", line)
            if m:
                cur["meta"][m.group(1)] = m.group(2).strip()
            continue
        f = line.split("\t")
        f += [""] * (len(cols) - len(f))
        cur["toks"].append(dict(zip(cols, f)))
    flush()
    return docs


def build(doc):
    text, offs = "", []
    for t in doc["toks"]:
        s = len(text)
        text += t["TOKEN"]
        offs.append((s, len(text)))
        misc = t.get("MISC", "")
        text += "\n" if "EndOfLine" in misc else ("" if "NoSpaceAfter" in misc else " ")
    spans = []
    for layer in LAYERS:
        spans += iob_spans([t.get(layer, "_") for t in doc["toks"]], offs)
    return text.rstrip(), [list(x) for x in spans]


def main():
    commit = os.popen(f"git -C {os.environ['IJDAR_RAW']}/hipe2022 log -1 --format=%h").read().strip()
    ccommit = ""
    for key, g in DATASETS.items():
        files = sorted(f for f in glob.glob(f"{g['dir']}/*.tsv") if "mask" not in f.lower())
        n = 0
        with open(f"{OUT}/{key}.jsonl", "w", encoding="utf-8") as fh:
            for f in files:
                for d in parse_file(f):
                    m = d["meta"]
                    did = m.get("hipe2022:document_id") or m.get("document_id")
                    text, spans = build(d)
                    rec = {"doc_id": did, "page_id": did if g["page"] else None, "split": split_of(f),
                           "text": text, "spans": spans}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
        clef = g.get("clef")
        rem = ("couches NE-COARSE-LIT + NE-NESTED, label 1er niveau (nested fin type loc.adm.town -> loc) ; "
               "fichiers *masked* exclus ; texte reconstruit avec NoSpaceAfter/EndOfLine. ")
        if g["page"]:
            rem += "doc = page (page_id = doc_id). "
        else:
            rem += "doc = article ; aucune métadonnée de page physique dans les TSV -> page_id null. "
        rem += EXTRA.get(key, "")
        meta = {"key": key, "dataset": "CLEF-HIPE-2020 (impresso)" if clef else "HIPE-2022",
                "sous_corpus": g["sous"], "sheets": g["sheets"], "unite_doc": g["unite"],
                "source": "https://github.com/impresso/CLEF-HIPE-2020 (data/v1.4/fr)" if clef else H22_SRC,
                "version": f"v1.4, commit {ccommit}" if clef else H22_VER.format(commit=commit),
                "annotation": "gold", "remarques": rem, "published": g["pub"], "files": [os.path.basename(f) for f in files]}
        json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
        print(key, n, "docs", [os.path.basename(f) for f in files])


if __name__ == "__main__":
    main()
