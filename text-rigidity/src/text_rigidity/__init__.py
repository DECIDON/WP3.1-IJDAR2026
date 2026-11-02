"""Indicateurs de rigidité textuelle, calculés sur le texte seul (sans annotation d'entités).

Indicateurs retenus :
- formatage typographique (axe liste ↔ phrase) : compute_typographic_formatting
- balance phrastique (axe liste ↔ phrase) : compute_phrastic_balance
- formulaicité : Self-BLEU (compute_self_bleu), mesure standard ; formularité (compute_formularity), complément
  lisible ; tous deux contre une FormularityReference
- densité de noms propres (covariable, pas une mesure de rigidité) : compute_name_density
- segments averbaux (contrôle de la balance) : compute_verbless_rate

Conservés pour comparaison, non retenus : divergence KL des POS, Distinct-N, ΔH, perplexité KenLM.
"""
from .divergence import compute_pos_kl_divergence, kl_divergence_counts
from .entropy import DELTA_H_TOKENS, compute_word_entropy, entropy_rate_lz, tokenize_words, unigram_entropy
from .formularity import (FormularityReference, compute_formularity, compute_self_bleu, formula_tokens, raw_tokens,
                          sample_reference_chunks)
from .lexical import compute_lexical_diversity
from .metrics import get_all_metrics
from .nlp import SPACY_MODELS, UD_REFERENCE_TREEBANKS, get_nlp, get_pos_reference_counts
from .perplexity import compute_ppl, download_ccnet_models
from .phrastic import compute_name_density, compute_phrastic_balance, compute_verbless_rate
from .typography import compute_typographic_formatting, count_typographic_marks, strip_markup

__version__ = "0.1.0"

__all__ = [
    "DELTA_H_TOKENS",
    "SPACY_MODELS",
    "UD_REFERENCE_TREEBANKS",
    "FormularityReference",
    "compute_formularity",
    "compute_lexical_diversity",
    "compute_name_density",
    "compute_phrastic_balance",
    "compute_pos_kl_divergence",
    "compute_ppl",
    "compute_self_bleu",
    "compute_typographic_formatting",
    "compute_verbless_rate",
    "compute_word_entropy",
    "count_typographic_marks",
    "download_ccnet_models",
    "entropy_rate_lz",
    "formula_tokens",
    "get_all_metrics",
    "get_nlp",
    "get_pos_reference_counts",
    "kl_divergence_counts",
    "raw_tokens",
    "sample_reference_chunks",
    "strip_markup",
    "tokenize_words",
    "unigram_entropy",
]
