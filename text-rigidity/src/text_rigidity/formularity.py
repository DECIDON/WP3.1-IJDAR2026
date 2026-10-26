"""Formularité : part d'une fenêtre prise dans des gabarits (n-grammes) qui reviennent ailleurs dans son
dataset. La référence est tirée des autres documents du dataset (laisser-un-document-dehors).
"""
import random
from collections import Counter

from .nlp import get_nlp, in_spans


def formula_tokens(doc) -> list[str]:
    """Séquence de tokens pour la formularité : noms propres -> <NAME>, nombres -> <NUM>, minuscules,
    signes conservés (ils font partie des gabarits), espaces et sauts de ligne retirés."""
    out = []
    for t in doc:
        if t.is_space:
            continue
        if t.pos_ == "PROPN":
            out.append("<NAME>")
        elif t.like_num or t.pos_ == "NUM":
            out.append("<NUM>")
        else:
            out.append(t.text.lower())
    return out


def _ngrams(tokens, n):
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def sample_reference_chunks(docs, chunk_tokens=500, pool_tokens=40_000, seed=0):
    """Extraits contigus de chunk_tokens mots, pris à tour de rôle dans les documents (pour qu'aucun document ne
    domine), jusqu'à pool_tokens mots. Renvoie une liste de (identifiant du document, texte de l'extrait)."""
    rng = random.Random(seed)
    per_doc = []
    for doc_id, text in docs:
        words = text.split()
        starts = list(range(0, max(1, len(words) - chunk_tokens + 1), chunk_tokens))
        rng.shuffle(starts)
        per_doc.append((doc_id, words, starts))
    rng.shuffle(per_doc)
    chunks, total = [], 0
    while total < pool_tokens and any(starts for _, _, starts in per_doc):
        for doc_id, words, starts in per_doc:
            if starts and total < pool_tokens:
                piece = words[starts.pop() :][:chunk_tokens]
                chunks.append((doc_id, " ".join(piece)))
                total += len(piece)
    return chunks


class FormularityReference:
    """Référence de formularité d'un dataset : extraits de taille fixe tirés de ses documents.

    docs : liste de (identifiant du document, texte). On tire des extraits contigus de chunk_tokens tokens,
    en faisant tourner les documents, jusqu'à pool_tokens tokens. Pour une fenêtre du document d, la
    référence est formée d'extraits d'autres documents (laisser-un-document-dehors), jusqu'à ref_tokens.
    """

    def __init__(self, docs, lang="fr", n=4, ref_tokens=20_000, chunk_tokens=500, pool_tokens=40_000, seed=0):
        self.n, self.ref_tokens = n, ref_tokens
        chunks = sample_reference_chunks(docs, chunk_tokens, pool_tokens, seed)
        nlp = get_nlp(lang)
        self.chunks = []
        for (doc_id, _), parsed in zip(chunks, nlp.pipe([c for _, c in chunks], batch_size=64)):
            toks = formula_tokens(parsed)
            self.chunks.append((doc_id, len(toks), Counter(_ngrams(toks, n))))
        self._cache = {}

    def chunks_for(self, doc_id):
        """Indices des extraits qui forment la référence de doc_id : hors doc_id, jusqu'à ref_tokens tokens."""
        out, size = [], 0
        for i, (d, ntok, _) in enumerate(self.chunks):
            if d == doc_id:
                continue
            if size >= self.ref_tokens:
                break
            out.append(i)
            size += ntok
        return out

    def counts_for(self, doc_id):
        """Effectifs des n-grammes dans la référence qui exclut doc_id, et taille effective (tokens)."""
        return self._stats(doc_id)[:2]

    def doc_freq_for(self, doc_id):
        """Nombre de documents distincts de la référence (hors doc_id) où apparaît chaque n-gramme."""
        return self._stats(doc_id)[2]

    def _stats(self, doc_id):
        if doc_id not in self._cache:
            total, size, docs = Counter(), 0, {}
            for i in self.chunks_for(doc_id):
                d, ntok, c = self.chunks[i]
                total.update(c)
                size += ntok
                for g in c:
                    docs.setdefault(g, set()).add(d)
            self._cache[doc_id] = (total, size, Counter({g: len(s) for g, s in docs.items()}))
        return self._cache[doc_id]


def compute_formularity(text: str, reference: FormularityReference, doc_id=None, lang: str = "fr", doc=None,
                        min_count: int = 3, min_docs: int = 1, exclude_spans=()) -> dict:
    """Formularité : part des tokens de la fenêtre couverts par un n-gramme (4-gramme par défaut) qui
    revient au moins min_count fois dans la référence de son dataset, hors document de la fenêtre, et qui
    contient au moins un mot (pas seulement des <NAME>, <NUM> et des signes).

    min_docs : critère de dispersion des lexical bundles (Biber et al.) ; le n-gramme doit en plus apparaître
    dans au moins min_docs documents distincts de la référence (1 = pas de critère, réglage historique).

    Renvoie {"formularity": part en %, "ref_tokens": taille effective de la référence}. La valeur n'est
    comparable d'un dataset à l'autre que si ref_tokens atteint la taille visée (20 000 par défaut).
    """
    if doc is None:
        doc = get_nlp(lang)(text)
    toks = formula_tokens([t for t in doc if not in_spans(t, exclude_spans)])
    counts, size = reference.counts_for(doc_id)
    spread = reference.doc_freq_for(doc_id) if min_docs > 1 else None
    n = reference.n
    if len(toks) < n:
        return {"formularity": float("nan"), "ref_tokens": size}
    covered = [False] * len(toks)
    for i, g in enumerate(_ngrams(toks, n)):
        # un gabarit doit contenir au moins un mot : une suite de <NAME>, <NUM> et de signes ne compte pas
        if (counts.get(g, 0) >= min_count and any(w[0].isalpha() for w in g)
                and (spread is None or spread.get(g, 0) >= min_docs)):
            for j in range(i, i + n):
                covered[j] = True
    return {"formularity": 100 * sum(covered) / len(toks), "ref_tokens": size}
