"""Old Bailey Proceedings Online (TEI.2 XML, DHI 2021) -> normalized/oldbailey.jsonl.

Document = proces (div1 type="trialAccount") des sessionsPapers. Ordinary's Accounts exclus.
Classes : persName (5 sous-types) -> PER ; rs[type=alias] (imbrique dans persName) -> PER ;
placeName -> LOC ; rs[type=crimeDate] -> DATE ; rs[type=occupation] -> OCC.
Exclus (descriptions juridiques/evenementielles, pas des entites nommees) :
rs offenceDescription / verdictDescription / punishmentDescription (comptes dans meta.remarques).
page_id = page facsimile (xptr type=pageFacsimile) en vigueur au debut du proces.
Usage : python3 loaders/oldbailey.py RAW_DIR OUT_DIR [DEPUIS]   (bibliotheque standard seulement)
DEPUIS = AAAAMMJJ : ne garde que les sessions a partir de cette date -> key oldbailey-<AAAA>-1913.
  Ex. 18341101 : periode nov. 1834-1913, seule periode gold (balisage automatique PUIS verifie et complete a la
  main) ; avant, les noms autres qu'accuses/victimes sont la sortie GATE non corrigee (page Project du site).
"""
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

RAW = sys.argv[1] if len(sys.argv) > 1 else "../../datasets/raw/oldbailey"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../../datasets/normalized"
DEPUIS = sys.argv[3] if len(sys.argv) > 3 else None
KEY = f"oldbailey-{DEPUIS[:4]}-1913" if DEPUIS else "oldbailey"
WS = re.compile(r"\s+")
SKIP = {"interp", "join", "xptr"}  # elements vides (metadonnees) : on garde seulement leur tail
BLOCK = {"p", "div1", "div2", "note", "lb"}
excluded = Counter()
lab_count = Counter()


class Builder:
    def __init__(self):
        self.parts, self.n, self.spans = [], 0, []

    def add(self, s):
        if not s:
            return
        s = WS.sub(" ", s)
        if self.parts and (self.parts[-1].endswith((" ", "\n")) or not self.parts[-1]) and s.startswith(" "):
            s = s[1:]
        if not self.parts and s.startswith(" "):
            s = s[1:]
        if s:
            self.parts.append(s)
            self.n += len(s)

    def newline(self):
        if self.parts and not self.parts[-1].endswith("\n"):
            if self.parts[-1].endswith(" "):
                self.parts[-1] = self.parts[-1][:-1]
                self.n -= 1
            self.parts.append("\n")
            self.n += 1

    def text(self):
        return "".join(self.parts)


def label_of(el):
    tag, typ = el.tag, el.get("type")
    if tag == "persName":
        return "PER"
    if tag == "placeName":
        return "LOC"
    if tag == "rs":
        if typ == "alias":
            return "PER"
        if typ == "crimeDate":
            return "DATE"
        if typ == "occupation":
            return "OCC"
        excluded[typ] += 1
    return None


def walk(el, b, state):
    tag = el.tag
    if tag == "xptr" and el.get("type") == "pageFacsimile" and state["page"] is None:
        state["page"] = el.get("doc")
    if tag in SKIP:
        return
    if tag in BLOCK:
        b.newline()
    lab = label_of(el)
    start = b.n
    b.add(el.text)
    for ch in el:
        walk(ch, b, state)
        if ch.tail:
            b.add(ch.tail)
    if lab:
        b.spans.append([start, b.n, lab])
    if tag in BLOCK:
        b.newline()


def trim(text, spans):
    out = []
    for s, e, lab in spans:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.append([s, e, lab])
    return out


def main():
    files = sorted(f for f in glob.glob(f"{RAW}/sessionsPapers/*.xml")
                   if not DEPUIS or os.path.basename(f)[:8] >= DEPUIS)
    n_docs = 0
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{KEY}.jsonl", "w", encoding="utf-8") as fh:
        for f in files:
            root = ET.parse(f).getroot()
            cur_page = None
            # parcours en ordre document pour suivre la page courante
            for div0 in root.iter("div0"):
                for div1 in div0:
                    if div1.tag != "div1":
                        if div1.tag == "xptr" and div1.get("type") == "pageFacsimile":
                            cur_page = div1.get("doc")
                        continue
                    if div1.get("type") != "trialAccount":
                        # mettre a jour la page courante a partir des xptr de la section sautee
                        for x in div1.iter("xptr"):
                            if x.get("type") == "pageFacsimile":
                                cur_page = x.get("doc")
                        continue
                    b = Builder()
                    state = {"page": None}
                    # page de debut : xptr en tete du proces s'il precede tout texte, sinon page courante
                    first_text_seen = False
                    start_page = cur_page
                    for x in div1.iter():
                        if x.tag == "xptr" and x.get("type") == "pageFacsimile":
                            if not first_text_seen:
                                start_page = x.get("doc")
                            cur_page = x.get("doc")
                        elif x.tag not in SKIP and x.text and x.text.strip():
                            first_text_seen = True
                    walk(div1, b, state)
                    text = b.text()
                    # nettoyage final : retirer \n de tete (offsets inchanges si on ne touche qu'a la fin)
                    spans = trim(text, b.spans)
                    for _, _, lab in spans:
                        lab_count[lab] += 1
                    fh.write(json.dumps({"doc_id": div1.get("id"), "page_id": start_page, "split": None,
                                         "text": text, "spans": spans}, ensure_ascii=False) + "\n")
                    n_docs += 1
    meta = {
        "key": "oldbailey", "dataset": "Old Bailey Proceedings Online", "sous_corpus": "Proceedings (sessionsPapers) 1674-1913",
        "sheets": ["Datasets NER anglais#(sans N°) Old Bailey Proceedings Online"],
        "unite_doc": "procès (div1 trialAccount)",
        "source": "https://www.dhi.ac.uk/san/data/oldbailey/oldbailey.zip (DHI Data Service, via https://www.dhi.ac.uk/data/oldbailey)",
        "version": "DHI data release 19 Jan 2021 (fichiers XML datés 2015-2017 ; = OBO_XML 7.2, figshare 10.15131/shef.data.4775434.v2)",
        "annotation": "silver",
        "remarques": (
            "Balisage semi-automatique (1674-1834 : manuel sauf les noms de personnes, balisés par GATE (80-90 % trouvés, compléments manuels pour accusés et victimes seulement) ; 1834-1913 : passe automatique puis vérification manuelle), non exhaustif "
            "(nom balisé seulement si prénom+patronyme). doc = div1 trialAccount des 2163 sessionsPapers ; "
            "frontMatter/supplementaryMaterial/punishmentSummary/advertisements et Ordinary's Accounts exclus. "
            "Classes : persName (witness/defendant/victim/juror/judiciaryName) + rs alias (imbriqué) -> PER ; "
            "placeName -> LOC ; rs crimeDate -> DATE ; rs occupation -> OCC. Exclus car descriptions juridiques "
            "et non entités nommées : " + ", ".join(f"rs {k} {v}" for k, v in excluded.most_common()) + ". "
            "page_id = page facsimilé où commence le procès (un procès peut couvrir plusieurs pages : stats par "
            "page = procès rattachés à leur page de début). Texte : blancs normalisés, \\n entre paragraphes. "
            "Contrôle : 197 744 procès vs 197 752 annoncés (-8, <0,01 %). Ordinary's Accounts (475 fichiers) non "
            "calculés. Même contenu que OBO_XML_7-2.zip (figshare 10.15131/shef.data.4775434.v2)."),
        "published": {"tokens": None, "mentions": None, "docs": 197752},
    }
    if DEPUIS:
        meta.update(key=KEY, sous_corpus=f"Proceedings (sessionsPapers) {DEPUIS[:4]}-1913, {len(files)} sessions",
                    annotation="gold",
                    remarques=f"Sous-ensemble à partir de la session {DEPUIS} : balisage automatique puis vérifié et "
                              "complété à la main (« Remaining markup, including checking of the results of the "
                              "automated markup, was carried out by a team of eight data developers », page Project). "
                              + meta["remarques"].split(" doc = ", 1)[1].replace("2163 sessionsPapers", f"{len(files)} sessionsPapers"),
                    published={"tokens": None, "mentions": None, "docs": None})
    json.dump(meta, open(f"{OUT}/{KEY}.meta.json", "w"), ensure_ascii=False, indent=1)
    print(n_docs, lab_count.most_common(), excluded.most_common())


if __name__ == "__main__":
    main()
