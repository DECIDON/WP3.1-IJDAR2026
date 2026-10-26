"""Calcul groupé des indicateurs d'une fenêtre de texte."""
import zlib

from .divergence import compute_pos_kl_divergence
from .lexical import compute_lexical_diversity
from .nlp import get_nlp
from .perplexity import compute_ppl
from .phrastic import compute_name_density, compute_phrastic_balance, compute_verbless_rate
from .typography import compute_typographic_formatting


def get_all_metrics(text: str, lang: str = "fr", ppl_models: dict | None = None) -> dict:
    """Indicateurs d'une fenêtre de texte.

    Retenus : typo et balance (axe liste ↔ phrase), names (densité de noms propres, covariable).
    verbless (segments averbaux) sert de contrôle de la balance. La formularité, autre indicateur retenu,
    demande une référence tirée du dataset : voir compute_formularity. Conservés pour comparaison avec
    les analyses précédentes, mais non retenus : lex (Distinct-2), zlib, w_line, kl, ppl.

    ppl_models : {langue: (chemin .sp.model, chemin .arpa.bin)} ; ppl vaut NaN pour une langue absente.
    """
    # Surface
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    words = text.split()
    total_words = len(words) if words else 1
    text_bytes = text.encode("utf-8")
    r_zlib = len(zlib.compress(text_bytes)) / len(text_bytes) if text_bytes else 0.0
    w_line = total_words / len(lines) if lines else 0.0
    typo = compute_typographic_formatting(text)["typo_total"]

    # Une seule analyse spaCy, dans la langue du document
    doc = get_nlp(lang)(text)
    balance = compute_phrastic_balance(text, lang=lang, doc=doc)
    verbless = compute_verbless_rate(text, lang=lang, doc=doc)
    names = compute_name_density(text, lang=lang, doc=doc)
    lex_div = compute_lexical_diversity(text, n=2, lang=lang, doc=doc)
    kl_pos = compute_pos_kl_divergence(text, lang=lang, doc=doc)

    # Perplexité globale (KenLM CCNet), seulement si le modèle de la langue est fourni
    ppl = compute_ppl(text, *ppl_models[lang]) if ppl_models and lang in ppl_models else float("nan")

    return {
        "typo": typo,
        "balance": balance,
        "verbless": verbless,
        "lex": lex_div,
        "names": names,
        "zlib": r_zlib,
        "w_line": w_line,
        "kl": kl_pos,
        "ppl": ppl,
    }
