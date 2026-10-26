"""Perplexité d'un modèle de langue KenLM 5-grammes entraîné sur Wikipédia (CCNet, Wenzek et al. 2019).

Non retenue comme indicateur de rigidité ; conservée pour comparaison. Demande l'extra « perplexity »
(kenlm, sentencepiece) et les deux fichiers du modèle CCNet de la langue (voir download_ccnet_models).
"""
import os
import unicodedata
import urllib.request
from functools import lru_cache

CCNET_URL = "https://dl.fbaipublicfiles.com/cc_net/lm/{lang}.{ext}"


def download_ccnet_models(lang: str = "fr", dest: str = ".") -> tuple[str, str]:
    """Télécharge au besoin le tokenizer SentencePiece et le modèle KenLM CCNet de la langue.

    Renvoie (chemin du .sp.model, chemin du .arpa.bin). Le modèle KenLM français pèse environ 2,6 Go.
    """
    os.makedirs(dest, exist_ok=True)
    paths = []
    for ext in ("sp.model", "arpa.bin"):
        path = os.path.join(dest, f"{lang}.{ext}")
        if not os.path.exists(path):
            urllib.request.urlretrieve(CCNET_URL.format(lang=lang, ext=ext), path)
        paths.append(path)
    return paths[0], paths[1]


@lru_cache(maxsize=None)
def load_ccnet_model(sp_model: str, lm_model: str):
    """Charge (et garde en mémoire) le tokenizer SentencePiece et le modèle KenLM."""
    import kenlm
    import sentencepiece as spm

    sp = spm.SentencePieceProcessor()
    sp.load(sp_model)
    return sp, kenlm.Model(lm_model)


def compute_ppl(text: str, sp_model: str, lm_model: str) -> float:
    """Perplexité du texte (minuscules, NFKC, découpé par SentencePiece) ; 0.0 si le texte est vide."""
    if not text.strip():
        return 0.0
    sp, lm = load_ccnet_model(sp_model, lm_model)
    text_clean = unicodedata.normalize("NFKC", text.lower().strip())
    tokens = sp.encode_as_pieces(text_clean)
    if not tokens:
        return 0.0
    score = lm.score(" ".join(tokens), bos=True, eos=True)
    return round(10.0 ** (-score / (len(tokens) + 1)), 2)
