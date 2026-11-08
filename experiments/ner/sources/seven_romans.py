"""7-romans (ObTIC) : CoNLL IOB2 « token label », lu en lecture seule dans le clone de experiences/structuration.
doc = roman (un fichier .conll), page_id = null. Ligne vide = rupture de phrase -> "\n"."""
import glob
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.environ["IJDAR_RAW"], "7-romans")
OUT = os.environ["IJDAR_NORMALIZED"]
KEY = "7-romans"

commit = subprocess.run(["git", "-C", SRC, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
with open(f"{OUT}/{KEY}.jsonl", "w", encoding="utf-8") as fh:
    for f in sorted(glob.glob(f"{SRC}/ner/*.conll")):
        parts, spans, pos, cur = [], [], 0, None
        for line in open(f, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line.strip():
                if cur: spans.append(cur); cur = None
                if parts and parts[-1] == " ":
                    parts[-1] = "\n"
                continue
            tok, tag = line.rsplit(" ", 1)
            s = pos
            parts += [tok, " "]
            pos += len(tok) + 1
            e = s + len(tok)
            if tag == "O":
                if cur: spans.append(cur); cur = None
            else:
                pre, lab = tag.split("-", 1)
                if pre == "B" or cur is None or cur[2] != lab:
                    if cur: spans.append(cur)
                    cur = [s, e, lab]
                else:
                    cur[1] = e
        if cur: spans.append(cur)
        text = "".join(parts)
        doc = os.path.basename(f)[:-6]
        fh.write(json.dumps({"doc_id": doc, "page_id": None, "split": None, "text": text, "spans": spans},
                            ensure_ascii=False) + "\n")
meta = {"key": KEY, "dataset": "7-romans", "sous_corpus": None, "sheets": ["Datasets NER français#1"],
        "unite_doc": "roman", "source": "https://github.com/obtic-sorbonne/7-romans (dossier ner/, CoNLL)",
        "version": f"commit {commit}", "annotation": "gold",
        "remarques": "7 fichiers CoNLL IOB2 (un par roman) ; tokens joints par espace, ligne vide -> saut de ligne ; "
                     "pas de split publié (validation croisée par roman) ; page_id null (pas de pagination/chapitrage dans le CoNLL). "
                     "Clone dans datasets/raw/7-romans.",
        "published": {"tokens": 1322011, "mentions": 34478, "docs": 7}}
json.dump(meta, open(f"{OUT}/{KEY}.meta.json", "w"), ensure_ascii=False, indent=1)
