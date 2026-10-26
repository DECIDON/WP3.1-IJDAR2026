"""Diversité lexicale Distinct-N.

Non retenue comme indicateur de rigidité (voir le rapport des expériences) ; conservée pour comparaison.
"""
from .nlp import get_nlp


def compute_lexical_diversity(text: str, n: int = 2, lang: str = "fr", doc=None) -> float:
    """Calcule le score Distinct-N sur les mots réels (sans ponctuation)."""
    if doc is None:
        doc = get_nlp(lang)(text)
    words = [token.text.lower() for token in doc if not token.is_punct and not token.is_space]

    if len(words) < n:
        return 0.0

    ngrams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
    return len(set(ngrams)) / len(ngrams)
