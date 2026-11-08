"""LitBank (entités) : brat standoff (entities/brat/*.txt + *.ann), 100 extraits de ~2000 mots.
doc = extrait (un livre). Toutes les entités T* gardées, y compris imbriquées (6 classes ACE)."""
import glob
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.environ["IJDAR_RAW"], "litbank")
OUT = os.environ["IJDAR_NORMALIZED"]
KEY = "litbank"

commit = subprocess.run(["git", "-C", SRC, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
mismatch = 0
with open(f"{OUT}/{KEY}.jsonl", "w", encoding="utf-8") as fh:
    for ann in sorted(glob.glob(f"{SRC}/entities/brat/*.ann")):
        text = open(ann[:-4] + ".txt", encoding="utf-8").read()
        spans = []
        for line in open(ann, encoding="utf-8"):
            if not line.startswith("T"):
                continue
            tid, info, surf = line.rstrip("\n").split("\t")
            lab, rng = info.split(" ", 1)
            s, e = int(rng.split(" ")[0]), int(rng.split(" ")[-1])
            if text[s:e] != surf:
                mismatch += 1
            spans.append([s, e, lab])
        spans.sort()
        doc = os.path.basename(ann)[: -len("_brat.ann")]
        fh.write(json.dumps({"doc_id": doc, "page_id": None, "split": None, "text": text, "spans": spans},
                            ensure_ascii=False) + "\n")
print("surfaces != texte:", mismatch)
meta = {"key": KEY, "dataset": "LitBank", "sous_corpus": "entités", "sheets": ["Datasets NER anglais#1"],
        "unite_doc": "extrait (1 par livre)", "source": "https://github.com/dbamman/litbank (entities/brat)",
        "version": f"commit {commit}", "annotation": "gold",
        "remarques": "brat standoff, texte .txt déjà tokenisé (tokens séparés par espaces, une phrase par ligne) ; "
                     "toutes les couches d'imbrication gardées ; pas de split dans le dépôt (splits de CV publiés à part) ; page_id null.",
        "published": {"tokens": 210532, "mentions": 13912, "docs": 100}}
json.dump(meta, open(f"{OUT}/{KEY}.meta.json", "w"), ensure_ascii=False, indent=1)
