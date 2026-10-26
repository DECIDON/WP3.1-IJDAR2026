"""Indicateurs fondés sur les catégories grammaticales : balance phrastique (axe liste ↔ phrase),
segments averbaux (contrôle de la balance) et densité de noms propres (covariable).

Tous acceptent exclude_spans, la liste des spans (début, fin) en caractères à ignorer : c'est ce qui
permet de retirer l'entité cible à l'échelle locale, après l'étiquetage du texte entier.
"""
import math
from collections import Counter

from .nlp import get_nlp, get_pos_reference_counts, in_spans

# Mots de liaison : ce qui fait tenir une phrase (verbes, déterminants, prépositions, pronoms, conjonctions)
GLUE_POS = {"VERB", "AUX", "DET", "ADP", "PRON", "SCONJ", "CCONJ"}
# Exclus de la balance : noms propres (mesurés à part par la densité de noms propres) et signes
# (mesurés par le formatage typographique), pour que les trois indicateurs restent distincts
BALANCE_EXCLUDED_POS = {"PROPN", "PUNCT", "SYM", "X", "SPACE"}
SEGMENT_BOUNDARIES = {".", ";", ":", "!", "?", "…", "|"}
_REF_ODDS_CACHE: dict = {}


def _glue_log_odds(counts: Counter) -> float:
    words = sum(v for t, v in counts.items() if t not in BALANCE_EXCLUDED_POS)
    glue = sum(counts.get(t, 0) for t in GLUE_POS)
    return math.log2((glue + 0.5) / (words - glue + 0.5))


def compute_phrastic_balance(text: str, lang: str = "fr", doc=None, exclude_spans=()) -> float:
    """Balance phrastique : log2-odds des mots de liaison parmi les mots (hors noms propres et signes),
    moins la même quantité pour la référence PUD de la langue.

    Négative : moins de liaison que la prose de référence (listes, champs) ; positive : plus (récit).
    exclude_spans : spans (début, fin) en caractères à ignorer, par exemple l'entité cible à l'échelle locale.
    """
    if doc is None:
        doc = get_nlp(lang)(text)
    counts = Counter(t.pos_ for t in doc if not t.is_space and not in_spans(t, exclude_spans))
    if lang not in _REF_ODDS_CACHE:
        _REF_ODDS_CACHE[lang] = _glue_log_odds(get_pos_reference_counts(lang, "model"))
    return _glue_log_odds(counts) - _REF_ODDS_CACHE[lang]


def compute_verbless_rate(text: str, lang: str = "fr", doc=None, min_words: int = 3, exclude_spans=()) -> float:
    """Part des segments sans verbe conjugué (trait UD VerbForm=Fin).

    Un segment va d'un signe de fin (. ; : ! ? … |) ou d'un saut de paragraphe au suivant ; les sauts
    de ligne simples ne coupent pas, car ils suivent la mise en colonne et non la syntaxe. Les segments
    de moins de min_words mots (abréviations comme « r. », « J.-B. ») sont ignorés. NaN sans segment.
    """
    if doc is None:
        doc = get_nlp(lang)(text)
    segments, current = [], []
    for tok in doc:
        if "\n\n" in tok.text or (tok.is_punct and tok.text in SEGMENT_BOUNDARIES):
            if current:
                segments.append(current)
            current = []
        elif not tok.is_space and not in_spans(tok, exclude_spans):
            current.append(tok)
    if current:
        segments.append(current)
    segments = [s for s in segments if sum(1 for t in s if t.is_alpha) >= min_words]
    if not segments:
        return float("nan")
    verbless = sum(1 for s in segments if not any("Fin" in t.morph.get("VerbForm") for t in s))
    return verbless / len(segments)


def compute_name_density(text: str, lang: str = "fr", doc=None, exclude_spans=()) -> float:
    """Densité de noms propres : part des mots étiquetés PROPN, en %. Indicateur textuel de la densité
    d'entités, qui n'utilise pas le gold (les étiquettes viennent de spaCy)."""
    if doc is None:
        doc = get_nlp(lang)(text)
    words = [t for t in doc if not (t.is_space or t.is_punct) and not in_spans(t, exclude_spans)]
    if not words:
        return float("nan")
    return 100 * sum(1 for t in words if t.pos_ == "PROPN") / len(words)
