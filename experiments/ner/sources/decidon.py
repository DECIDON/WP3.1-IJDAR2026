"""DECIDON AUGUST (débats) et TABLES (tables nominatives) : golds Label Studio distribués."""
import json
import os

LS = os.path.join(os.environ["IJDAR_RAW"], "decidon")  # copie du gold AUGUST (source : NER_label-studio)
GOLDS = {
    "decidon-august": dict(
        path=f"{LS}/project-16-at-2026-08-05-07-38-86641c79_AUGUST.json",
        dataset="DECIDON — AUGUST", sous_corpus="débats JORF", sheets=["Datasets NER français#8"],
        version="AUGUST md5 97301c30", published={"tokens": 158701, "mentions": 8538, "docs": 101}),
}
BLACKLIST = {"SIG", "OPN", "CLO"}
REMAP = {"PER-INT": "PER", "PER-EXT": "PER"}

out_dir = os.environ["IJDAR_NORMALIZED"]
for key, g in GOLDS.items():
    with open(f"{out_dir}/{key}.jsonl", "w") as fh:
        for t in json.load(open(g["path"])):
            text = t["data"]["text"]
            spans = []
            for r in t["annotations"][0]["result"]:
                v = r.get("value", {})
                if "labels" in v and v["labels"][0] not in BLACKLIST:
                    spans.append([v["start"], v["end"], REMAP.get(v["labels"][0], v["labels"][0])])
            pid = str(t["id"])
            fh.write(json.dumps({"doc_id": pid, "page_id": pid, "split": None, "text": text, "spans": spans},
                                ensure_ascii=False) + "\n")
    meta = {"key": key, "dataset": g["dataset"], "sous_corpus": g["sous_corpus"], "sheets": g["sheets"],
            "unite_doc": "page", "source": g["path"], "version": g["version"], "annotation": "gold",
            "remarques": "texte = text_md Chandra avec markup markdown ; SIG/OPN/CLO blacklistés exclus",
            "published": g["published"]}
    json.dump(meta, open(f"{out_dir}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
