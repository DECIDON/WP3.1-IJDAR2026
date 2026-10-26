"""Prévisibilité co-textuelle ΔH = H1 - ĥ (Bentz et al. 2017), indicateur d'échelle corpus.

Non retenue : l'estimateur est fortement biaisé aux tailles disponibles (un texte dont on a mélangé
les mots garde 2,4 à 2,7 bits sur 20 000 mots au lieu de 0). Conservée pour comparaison.
"""
import math
import re
from collections import Counter, defaultdict

import numpy as np
from scipy.special import digamma, gammaln, polygamma

# Découpage en mots comme Bentz et al. (2017, annexe A) pour l'Europarl : séparation sur \W+,
# la ponctuation (apostrophes et traits d'union compris) sépare les mots et n'est pas comptée.
_WORD_RE = re.compile(r"[^\W_]+")

# Taille d'échantillon (mots contigus) à partir de laquelle ΔH sépare les corpus structurés de la
# prose dans nos tests ; Bentz et al. observent une stabilisation complète vers 50 000 mots.
DELTA_H_TOKENS = 20_000


def tokenize_words(text: str, lowercase: bool = True, digits_to_zero: bool = False) -> list[str]:
    """Découpe un texte en mots (suites alphanumériques), ponctuation exclue."""
    if lowercase:
        text = text.lower()
    tokens = _WORD_RE.findall(text)
    if digits_to_zero:
        # Option inspirée de la normalisation CCNet : un numéro de rue ou une date devient un patron
        tokens = [re.sub(r"\d", "0", t) for t in tokens]
    return tokens


def _nsb_entropy_nats(counts: np.ndarray, alphabet_size: float) -> float:
    """Estimateur NSB (Nemenman, Shafee & Bialek 2002) : moyenne a posteriori de l'entropie sous un
    mélange de priors de Dirichlet rendant l'entropie a priori quasi uniforme. Intégration numérique
    sur log(beta), effectifs regroupés par valeur pour rester rapide sur de grands vocabulaires."""
    n_vals, mult = np.unique(counts, return_counts=True)
    n, v, k = counts.sum(), len(counts), alphabet_size
    log_b = np.linspace(np.log(1e-7), np.log(1e4), 2000)
    b = np.exp(log_b)
    nb = n_vals[None, :] + b[:, None]
    log_evidence = gammaln(k * b) - gammaln(n + k * b) + ((gammaln(nb) - gammaln(b)[:, None]) * mult).sum(axis=1)
    log_w = log_evidence + np.log(k * polygamma(1, k * b + 1) - polygamma(1, b + 1)) + log_b
    w = np.exp(log_w - log_w.max())
    h_b = (
        digamma(n + k * b + 1)
        - ((nb * digamma(nb + 1)) * mult).sum(axis=1) / (n + k * b)
        - (k - v) * b / (n + k * b) * digamma(b + 1)
    )
    return float((w * h_b).sum() / w.sum())


def unigram_entropy(tokens: list[str], estimator: str = "cs", alphabet_size: float = 1e6) -> float:
    """Entropie unigramme H1 de la distribution des mots, en bits/mot.

    Estimateurs (Bentz et al. 2017, annexe B) : "ml" (plug-in), "mm" (Miller-Madow),
    "cs" (Chao-Shen, conçu pour les échantillons où beaucoup de types ne sont vus qu'une fois),
    "nsb" (Nemenman-Shafee-Bialek, retenu par Bentz et al. ; alphabet_size = taille supposée du
    vocabulaire, à laquelle l'estimation est peu sensible dès qu'elle dépasse largement le nombre de types).
    """
    n = len(tokens)
    if n == 0:
        return float("nan")
    counts = np.array(list(Counter(tokens).values()), dtype=float)
    p = counts / n
    if estimator == "nsb":
        return _nsb_entropy_nats(counts, alphabet_size) / math.log(2)
    if estimator == "ml":
        h = -np.sum(p * np.log(p))
    elif estimator == "mm":
        h = -np.sum(p * np.log(p)) + (len(counts) - 1) / (2 * n)
    elif estimator == "cs":
        f1 = np.sum(counts == 1)
        if f1 == n:  # uniquement des hapax : couverture nulle, correction usuelle
            f1 = n - 1
        pa = (1 - f1 / n) * p
        la = 1 - (1 - pa) ** n
        h = -np.sum(pa * np.log(pa) / la)
    else:
        raise ValueError(f"Unknown estimator: {estimator!r}")
    return float(h / math.log(2))


def entropy_rate_lz(tokens: list[str]) -> float:
    """Taux d'entropie ĥ des mots (bits/mot), estimateur à fenêtre croissante de Gao et al. (2008).

    Formulation de Bentz et al. (2017, éq. 8-9) : ĥ = (1/N) Σ_i log2(i) / L_i, où L_i - 1 est la
    longueur de la plus longue suite de mots commençant en i et déjà présente en entier dans
    t_1..t_{i-1}. Mêmes conventions que l'implémentation de référence (paquet R Hrate).
    """
    n = len(tokens)
    if n < 2:
        return float("nan")
    previous = defaultdict(list)  # mot -> positions antérieures
    total = 0.0
    for i, tok in enumerate(tokens):
        longest = 0
        for j in previous[tok]:
            k = 1
            while i + k < n and j + k < i and tokens[j + k] == tokens[i + k]:
                k += 1
            longest = max(longest, k)
        total += math.log2(i + 1) / (longest + 1)
        previous[tok].append(i)
    return total / n


def compute_word_entropy(
    text: str,
    n_tokens: int | None = None,
    estimator: str = "cs",
    lowercase: bool = True,
    digits_to_zero: bool = False,
) -> dict:
    """Entropie des mots selon Bentz et al. (2017) : H1, ĥ et leur différence ΔH = H1 - ĥ.

    ΔH mesure l'incertitude sur un mot levée par le co-texte qui le précède : plus un texte
    réemploie des suites de mots (formules, patrons d'entrées), plus ΔH est élevé.

    Les estimateurs dépendent fortement de la longueur du texte : n_tokens découpe le texte en
    fenêtres consécutives de n_tokens mots exactement (le reste est ignoré) et renvoie la moyenne
    sur les fenêtres ; un texte plus court que n_tokens donne NaN. ΔH n'est discriminant qu'à
    partir de ~20 000 mots contigus (DELTA_H_TOKENS) : c'est un indicateur d'échelle corpus.
    """
    tokens = tokenize_words(text, lowercase=lowercase, digits_to_zero=digits_to_zero)
    if n_tokens is None:
        windows = [tokens]
    else:
        windows = [tokens[s : s + n_tokens] for s in range(0, len(tokens) - n_tokens + 1, n_tokens)]
    if not windows or not windows[0]:
        return {"H1": float("nan"), "h_rate": float("nan"), "delta_H": float("nan"), "n_windows": 0}
    h1 = np.array([unigram_entropy(w, estimator) for w in windows])
    hr = np.array([entropy_rate_lz(w) for w in windows])
    return {
        "H1": float(h1.mean()),
        "h_rate": float(hr.mean()),
        "delta_H": float((h1 - hr).mean()),
        "n_windows": len(windows),
    }
