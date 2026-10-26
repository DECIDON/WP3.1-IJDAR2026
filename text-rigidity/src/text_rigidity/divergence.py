"""Divergence KL entre la distribution UPOS d'un document et celle de la langue de référence.

Non retenue comme indicateur de rigidité (voir le rapport des expériences) ; conservée pour comparaison.
"""
from collections import Counter

import numpy as np
from scipy.stats import entropy

from .nlp import get_nlp, get_pos_reference_counts


def kl_divergence_counts(counts_doc: Counter, counts_ref: Counter, epsilon: float = 1e-5) -> float:
    """D_KL(P_doc || P_ref) en bits, avec lissage additif epsilon sur les deux distributions."""
    total_doc, total_ref = sum(counts_doc.values()), sum(counts_ref.values())
    if total_doc == 0:
        return 0.0
    tags = sorted(set(counts_doc) | set(counts_ref))
    p_doc = np.array([counts_doc.get(t, 0) / total_doc for t in tags]) + epsilon
    p_ref = np.array([counts_ref.get(t, 0) / total_ref for t in tags]) + epsilon
    return float(entropy(p_doc / p_doc.sum(), p_ref / p_ref.sum(), base=2))


def compute_pos_kl_divergence(
    text: str,
    lang: str = "fr",
    tagging: str = "model",
    exclude_pos: tuple = (),
    pos_ref: dict | None = None,
    doc=None,
) -> float:
    """Divergence KL entre la distribution UPOS du document et celle de la langue de référence.

    lang : langue du document (clé de SPACY_MODELS) ; elle fixe le modèle spaCy et le treebank.
    exclude_pos : étiquettes ignorées des deux côtés, ex. ("PUNCT", "SYM") pour ne pas recompter
        les signes déjà mesurés par l'indicateur de formatage typographique.
    pos_ref : distribution de référence fournie directement (effectifs ou probabilités).
    doc : document spaCy déjà analysé par get_nlp(lang), pour éviter de ré-analyser le texte.
    """
    if doc is None:
        doc = get_nlp(lang)(text)
    counts_doc = Counter(t.pos_ for t in doc if not t.is_space and t.pos_ not in exclude_pos)
    ref = pos_ref if pos_ref is not None else get_pos_reference_counts(lang, tagging)
    counts_ref = Counter({t: v for t, v in ref.items() if t not in exclude_pos})
    return kl_divergence_counts(counts_doc, counts_ref)
