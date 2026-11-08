"""Régime 1 : NER zero-shot PER / LOC sur les sous-datasets tirés (sample.py materialize).

Deux familles de modèles, chacune « telle quelle », sans aucun exemple de nos datasets :

  spacy   pipelines `*_core_news_lg` / `en_core_web_lg` (même architecture CNN pour toutes les langues), choisis
          par la langue du jeu ; `--spacy-en en_core_web_trf` remplace le modèle anglais (variante transformer,
          en bonus : il n'existe pas d'équivalent pour les autres langues). Correspondance des étiquettes de
          chaque pipeline vers PER / LOC : SPACY_MAP ; les autres étiquettes (ORG, MISC, DATE…) sont ignorées.
  gliner  `knowledgator/gliner-relex-multi-v1.0` (mDeBERTa-v3, multilingue), usage NER seul, types demandés
          « person » et « location » (en anglais pour toutes les langues), seuil 0,5, décodage plat.
          Texte découpé en morceaux de lignes < MAX_TOKENS sous-tokens (une ligne trop longue est coupée sur
          les espaces) ; doublons inter-morceaux : score max.

Sortie : <out>/<key>.jsonl, un segment par ligne {"unit_id", "doc_id", "start", "end", "fold",
"pred": [[début, fin, "PER"|"LOC", score], ...]} (offsets relatifs au segment ; score = 1 pour spaCy)
+ <out>/run.json (modèles, versions, paramètres, durées, étiquettes brutes rencontrées).
Le dossier de sortie ne doit pas exister (jamais d'écrasement).

Usage (depuis experiments/ner/, après `uv sync --group spacy --group gliner`) :
  uv run python zeroshot.py spacy  --sample /chemin/sample --out /chemin/runs/<nom> [--keys ...] [--threads 12]
  uv run python zeroshot.py gliner --sample /chemin/sample --out /chemin/runs/<nom> [--keys ...] [--threads 12]
"""
import argparse
import collections
import datetime
import json
import os
import platform
import sys
import time

SPACY_MODELS = {"fr": "fr_core_news_lg", "de": "de_core_news_lg", "en": "en_core_web_lg",
                "fi": "fi_core_news_lg", "sv": "sv_core_news_lg"}
# étiquettes des pipelines spaCy -> PER / LOC (WikiNER fr/de : PER LOC ; OntoNotes en : PERSON GPE LOC FAC ;
# fi : PERSON GPE LOC ; sv : PRS LOC). Toute étiquette absente d'ici est ignorée et comptée dans run.json.
SPACY_MAP = {"PER": "PER", "PERSON": "PER", "PRS": "PER", "LOC": "LOC", "GPE": "LOC", "FAC": "LOC"}
GLINER_MODEL = "knowledgator/gliner-relex-multi-v1.0"
GLINER_LABELS = {"person": "PER", "location": "LOC"}
THRESHOLD = 0.5
MAX_TOKENS = 384


def read_sample(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


# ------------------------------------------------------------------------------------------------ spaCy
def run_spacy(segments, lang, models, raw_labels):
    import spacy
    name = models[lang]
    nlp = spacy.load(name, exclude=["parser", "lemmatizer", "attribute_ruler", "senter", "morphologizer",
                                    "tagger", "trainable_lemmatizer"])
    nlp.max_length = max(nlp.max_length, max(len(s["text"]) for s in segments) + 1)
    out = []
    for seg, doc in zip(segments, nlp.pipe((s["text"] for s in segments), batch_size=16)):
        pred = []
        for ent in doc.ents:
            raw_labels[f"{name}:{ent.label_}"] += 1
            lab = SPACY_MAP.get(ent.label_)
            if lab:
                pred.append([ent.start_char, ent.end_char, lab, 1.0])
        out.append(pred)
    return out, name


# ------------------------------------------------------------------------------------------------ GLiNER
def ner_only_if_relex(model):
    """Copié de la forge DECIDON GLiNER-relex (lib/predict.py, `_ner_only_if_relex`) : un checkpoint relex
    forme toutes les paires d'empans retenus (coût inutile en NER seul) et `predict_entities` renvoie
    (entités, relations). On ne garde que le 1er empan cible en inférence et on force return_relations=False ;
    les scores d'entité (calculés avant) sont inchangés."""
    core = model.model
    if not any(hasattr(core, n) for n in ("relations_rep_layer", "pair_rep_layer", "triples_score_layer")):
        return
    if getattr(core.config, "span_mode", None) == "token_level":
        _rep = core.represent_spans

        def _rep_top1(*a, **k):
            scores, rep, mask, idx = _rep(*a, **k)
            if not core.training:
                rep, mask, idx = rep[:, :1], mask[:, :1], idx[:, :1]
            return scores, rep, mask, idx

        core.represent_spans = _rep_top1
    else:
        _sel = core.select_span_target_embedding

        def _sel_top1(*a, **k):
            if not core.training:
                k["top_k"] = 1
            return _sel(*a, **k)

        core.select_span_target_embedding = _sel_top1
    _orig = model.predict_entities

    def _predict(*a, **k):
        return _orig(*a, return_relations=False, **k)

    model.predict_entities = _predict


def chunks(text, count, max_tokens):
    """Morceaux (début, fin) de `text`, chacun < max_tokens sous-tokens, sur frontières de ligne ; une ligne trop
    longue est coupée sur les espaces."""
    pieces, pos = [], 0  # (début, fin, n_tokens) de lignes ou de bouts de ligne
    for line in text.split("\n"):
        n = count(line)
        if n < max_tokens:
            pieces.append((pos, pos + len(line), n))
        else:
            words, start, cur = line.split(" "), pos, 0
            p = pos
            for w in words:
                nw = count(w) + 1
                if cur and cur + nw >= max_tokens:
                    pieces.append((start, p - 1, cur))
                    start, cur = p, 0
                cur += nw
                p += len(w) + 1
            pieces.append((start, pos + len(line), cur))
        pos += len(line) + 1
    out, cur_s, cur_e, cur_n = [], None, None, 0
    for s, e, n in pieces:
        if cur_s is not None and cur_n + n + 1 >= max_tokens:
            out.append((cur_s, cur_e))
            cur_s, cur_n = None, 0
        if cur_s is None:
            cur_s = s
        cur_e, cur_n = e, cur_n + n + 1
    if cur_s is not None:
        out.append((cur_s, cur_e))
    return [(s, e) for s, e in out if text[s:e].strip()]


def load_gliner(threads):
    import torch
    from gliner import GLiNER
    torch.set_num_threads(threads)
    model = GLiNER.from_pretrained(GLINER_MODEL)
    ner_only_if_relex(model)
    model.eval()
    dp = model.data_processor
    tok = getattr(dp, "transformer_tokenizer", None) or getattr(dp, "tokenizer")
    return model, lambda s: len(tok.encode(s, add_special_tokens=False))


def run_gliner(segments, model, count):
    import torch
    out = []
    with torch.no_grad():
        for seg in segments:
            text, best = seg["text"], {}
            for a, b in chunks(text, count, MAX_TOKENS):
                for ent in model.predict_entities(text[a:b], list(GLINER_LABELS), flat_ner=True,
                                                  threshold=THRESHOLD):
                    key = (a + ent["start"], a + ent["end"], GLINER_LABELS[ent["label"]])
                    best[key] = max(best.get(key, 0.0), float(ent["score"]))
            out.append([[s, e, l, sc] for (s, e, l), sc in sorted(best.items())])
    return out


# ------------------------------------------------------------------------------------------------ main
def versions(names):
    import importlib.metadata as md
    v = {}
    for n in names:
        try:
            v[n] = md.version(n)
        except md.PackageNotFoundError:
            pass
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("backend", choices=["spacy", "gliner"])
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keys", nargs="*")
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--spacy-en", default=SPACY_MODELS["en"], help="modèle spaCy anglais (ex. en_core_web_trf)")
    a = ap.parse_args()
    if os.path.exists(a.out):
        raise SystemExit(f"{a.out} existe déjà : jamais d'écrasement, choisir un nouveau dossier")
    os.makedirs(a.out)
    keys = a.keys or sorted(f[:-6] for f in os.listdir(a.sample) if f.endswith(".jsonl"))
    models = {**SPACY_MODELS, "en": a.spacy_en}
    run = {"backend": a.backend, "command": " ".join(sys.argv), "date": datetime.datetime.now().isoformat(),
           "host": platform.node(), "threads": a.threads, "datasets": {}}
    raw_labels = collections.Counter()
    if a.backend == "gliner":
        model, count = load_gliner(a.threads)
        run.update(model=GLINER_MODEL, labels=GLINER_LABELS, threshold=THRESHOLD, max_tokens=MAX_TOKENS,
                   flat_ner=True, versions=versions(["gliner", "transformers", "torch"]))
    else:
        import torch  # noqa: F401  (spacy-curated-transformers pour en_core_web_trf)
        torch.set_num_threads(a.threads)
        run.update(models=models, label_map=SPACY_MAP, versions=versions(["spacy", "torch"] + [
            m.replace("_", "-") for m in models.values()]))
    for k in keys:
        segs = read_sample(os.path.join(a.sample, f"{k}.jsonl"))
        lang = segs[0]["lang"]
        if a.backend == "spacy" and a.spacy_en != SPACY_MODELS["en"] and lang != "en":
            continue  # variante anglaise seule
        t0 = time.time()
        if a.backend == "spacy":
            preds, name = run_spacy(segs, lang, models, raw_labels)
        else:
            preds, name = run_gliner(segs, model, count), GLINER_MODEL
        dt = time.time() - t0
        with open(os.path.join(a.out, f"{k}.jsonl"), "w", encoding="utf-8") as fo:
            for s, p in zip(segs, preds):
                fo.write(json.dumps({"unit_id": s["unit_id"], "doc_id": s["doc_id"], "start": s["start"],
                                     "end": s["end"], "fold": s["fold"], "pred": p}, ensure_ascii=False) + "\n")
        n_chars = sum(len(s["text"]) for s in segs)
        run["datasets"][k] = {"model": name, "lang": lang, "segments": len(segs), "chars": n_chars,
                              "pred": sum(len(p) for p in preds), "seconds": round(dt, 1)}
        run["raw_labels"] = dict(raw_labels)
        json.dump(run, open(os.path.join(a.out, "run.json"), "w"), ensure_ascii=False, indent=1)
        print(f"{k:20s} {name:38s} segments {len(segs):4d}  préd. {sum(len(p) for p in preds):5d}  {dt:7.1f} s",
              flush=True)


if __name__ == "__main__":
    main()
