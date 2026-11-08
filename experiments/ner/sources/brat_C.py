"""Famille Brat standoff (groupe C) : COPIOUS et HIMERA.

- copious : copious_published.zip (miroir HF DFKI-SLT/copious, archive Brat d'origine), dossiers
  train/dev/test, une page BHL par paire .txt/.ann. Doc = page ; page_id = identifiant de page BHL
  (champ numérique ≥ 7 chiffres du nom de fichier).
- himera : HIMERA_corpus.tar.gz (NaCTeM), .txt + .a1 (entités) + .a2 (événements, ignorés).
  Doc = document (article BMJ ou extrait de rapport MOH).

Entités discontinues (`T1\tLabel 10 15;20 30\t...`) : une seule mention, empan englobant
[min début, max fin). Entités imbriquées gardées telles quelles.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAWROOT = os.environ["IJDAR_RAW"]
OUT = os.environ["IJDAR_NORMALIZED"]


def read_brat(txt_path, ann_path, keep, crlf_to_lf=False):
    """crlf_to_lf : offsets calculés sur le texte aux fins de ligne normalisées (cas COPIOUS, .txt en CRLF)."""
    text = open(txt_path, encoding="utf-8", newline=None if crlf_to_lf else "").read()
    spans, n_disc, mism = [], 0, 0
    for line in open(ann_path, encoding="utf-8"):
        if not line.startswith("T"):
            continue
        tid, info, surface = (line.rstrip("\n").split("\t") + [""])[:3]
        lab, _, offs = info.partition(" ")
        if lab not in keep:
            continue
        frags = [tuple(map(int, f.split())) for f in offs.split(";")]
        if len(frags) > 1:
            n_disc += 1
        s, e = min(f[0] for f in frags), max(f[1] for f in frags)
        if " ".join(text[a:b] for a, b in frags) != surface:
            mism += 1
        spans.append([s, e, lab])
    return text, spans, n_disc, mism


def copious():
    key, root = "copious", f"{RAWROOT}/copious/copious_published"
    keep = {"Taxon", "GeographicalLocation", "Habitat", "TemporalExpression", "Person"}
    tot_disc = tot_mism = 0
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for split in ("train", "dev", "test"):
            for txt in sorted(glob.glob(f"{root}/{split}/*.txt")):
                stem = os.path.basename(txt)[:-4]
                text, spans, nd, mm = read_brat(txt, txt[:-4] + ".ann", keep, crlf_to_lf=True)
                tot_disc += nd
                tot_mism += mm
                # noms : <pageID> | <itemID>_English_<pageID>_<année> | <itemID>_English_<x>_<pageID>_<année>
                page = next((x for x in stem.rstrip(".").split("_") if x.isdigit() and len(x) >= 7), stem)
                fh.write(json.dumps({"doc_id": stem, "page_id": page, "split": split, "text": text,
                                     "spans": spans}, ensure_ascii=False) + "\n")
    print(key, "discontinues", tot_disc, "texte≠surface", tot_mism)
    meta = {"key": key, "dataset": "COPIOUS", "sous_corpus": "Biodiversity Heritage Library", "sheets": ["Datasets NER anglais#13"],
            "unite_doc": "page", "source": "https://huggingface.co/datasets/DFKI-SLT/copious/resolve/main/copious_published.zip",
            "version": "HF DFKI-SLT/copious commit 1cd4a9c (archive Brat 2019-01-04)", "annotation": "gold",
            "remarques": (f"Brat d'origine (pas les jsonl HF re-tokenisés) ; .txt en CRLF mais offsets calculés sur LF → CRLF normalisé en LF. Doc = page BHL, page_id = pageID BHL. "
                          f"{tot_disc} entités discontinues ramenées à leur empan englobant. Imbrications "
                          f"(Taxon avec/sans autorité) gardées. Relations Occur/SeenBy ignorées. "
                          f"Splits du dossier : 534/67/67 (la fiche dit 543/67/67). 50 surfaces .ann en mojibake (Â°, Ã¦) mais offsets justes."),
            "published": {"tokens": None, "mentions": 28801, "docs": 668}}
    json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)


def himera():
    key, root = "himera", f"{RAWROOT}/himera/HIMERA_corpus"
    keep = {"Anatomical", "Biological_Entity", "Condition", "Environmental", "Sign_or_Symptom", "Subject",
            "Therapeutic_or_Investigational"}
    tot_disc = tot_mism = 0
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for txt in sorted(glob.glob(f"{root}/**/*.txt", recursive=True)):
            if os.path.basename(txt).startswith("HIMERA_"):
                continue
            rel = os.path.relpath(txt, root)[:-4]
            text, spans, nd, mm = read_brat(txt, txt[:-4] + ".a1", keep)
            tot_disc += nd
            tot_mism += mm
            fh.write(json.dumps({"doc_id": rel, "page_id": None, "split": None, "text": text, "spans": spans},
                                ensure_ascii=False) + "\n")
    print(key, "discontinues", tot_disc, "texte≠surface", tot_mism)
    meta = {"key": key, "dataset": "HIMERA", "sous_corpus": "BMJ (1850s-1960s) + rapports MOH", "sheets": ["Datasets NER anglais#14"],
            "unite_doc": "document (article BMJ / extrait de rapport MOH)",
            "source": "http://www.nactem.ac.uk/himera/HIMERA_corpus.tar.gz", "version": "archive téléchargée le 2026-10-01",
            "annotation": "gold",
            "remarques": (f"Entités = .a1, 7 types ; Negation_Cue (57) exclu (indice de négation des événements, pas une "
                          f"entité) ; .a2 (déclencheurs et événements Affect/Causality) ignoré. {tot_disc} entités "
                          f"discontinues ramenées à leur empan englobant. Effectifs par classe différents de la fiche "
                          f"(issue du papier) : version distribuée ≠ version décrite."),
            "published": {"tokens": None, "mentions": 8480, "docs": 39}}
    json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    which = sys.argv[1:] or ["copious"]
    for w in which:
        globals()[w]()
