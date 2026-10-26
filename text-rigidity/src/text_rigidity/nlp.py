"""Étiquetage spaCy par langue et distributions UPOS de référence (treebanks Universal Dependencies)."""
import importlib
import urllib.request
from collections import Counter

import spacy

# Modèles spaCy par langue (codes ISO 639-1)
SPACY_MODELS = {
    "fr": "fr_core_news_sm",
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fi": "fi_core_news_sm",
    "sv": "sv_core_news_sm",
    "it": "it_core_news_sm",
    "es": "es_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "el": "el_core_news_sm",
}

# Treebanks UD de référence. Par défaut les treebanks PUD (Parallel UD) : les mêmes 1000 phrases
# de presse et de Wikipédia dans chaque langue, si bien que les distributions de référence ne
# diffèrent que par la langue et pas par le genre des textes. Pas de PUD pour le grec et le
# néerlandais : on se rabat sur un treebank généraliste.
UD_REFERENCE_TREEBANKS = {
    "fr": ("UD_French-PUD", "fr_pud-ud-test.conllu"),
    "en": ("UD_English-PUD", "en_pud-ud-test.conllu"),
    "de": ("UD_German-PUD", "de_pud-ud-test.conllu"),
    "fi": ("UD_Finnish-PUD", "fi_pud-ud-test.conllu"),
    "sv": ("UD_Swedish-PUD", "sv_pud-ud-test.conllu"),
    "it": ("UD_Italian-PUD", "it_pud-ud-test.conllu"),
    "es": ("UD_Spanish-PUD", "es_pud-ud-test.conllu"),
    "pt": ("UD_Portuguese-PUD", "pt_pud-ud-test.conllu"),
    "el": ("UD_Greek-GDT", "el_gdt-ud-test.conllu"),
    "nl": ("UD_Dutch-Alpino", "nl_alpino-ud-test.conllu"),
}
UD_RAW_URL = "https://raw.githubusercontent.com/UniversalDependencies/{repo}/master/{file}"
USER_AGENT = "text-rigidity/0.1"

_NLP_CACHE: dict = {}
_POS_REF_CACHE: dict = {}


def get_nlp(lang: str = "fr"):
    """Modèle spaCy de la langue (téléchargé au besoin), sans parser, NER ni lemmatiseur."""
    if lang not in _NLP_CACHE:
        if lang not in SPACY_MODELS:
            raise ValueError(f"Unsupported language: {lang!r} (see SPACY_MODELS)")
        name = SPACY_MODELS[lang]
        try:
            nlp_lang = spacy.load(name, disable=["parser", "ner", "lemmatizer"])
        except OSError:
            spacy.cli.download(name)
            importlib.invalidate_caches()
            nlp_lang = spacy.load(name, disable=["parser", "ner", "lemmatizer"])
        nlp_lang.max_length = 2_000_000
        _NLP_CACHE[lang] = nlp_lang
    return _NLP_CACHE[lang]


def in_spans(tok, spans) -> bool:
    """Vrai si le token commence dans l'un des spans (début, fin) en caractères."""
    return any(s <= tok.idx < e for s, e in spans)


def _read_conllu(repo: str, file: str) -> list[str]:
    url = UD_RAW_URL.format(repo=repo, file=file)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8").splitlines()


def get_pos_reference_counts(lang: str = "fr", tagging: str = "model", treebank: tuple | None = None) -> Counter:
    """Effectifs UPOS du treebank de référence de la langue.

    tagging="model" : le texte brut du treebank (lignes "# text =") est ré-étiqueté par le même
        modèle spaCy que les documents ; P_doc et P_ref sortent alors du même instrument et la KL
        ne mesure pas les écarts de conventions entre spaCy et le treebank (ex. « du » = 1 token
        DET pour spaCy, 2 mots ADP + DET dans UD).
    tagging="gold" : étiquettes UPOS manuelles du treebank.
    treebank : (dépôt, fichier) pour remplacer le treebank par défaut de la langue.
    """
    repo, file = treebank or UD_REFERENCE_TREEBANKS[lang]
    key = (lang, repo, file, tagging)
    if key not in _POS_REF_CACHE:
        lines = _read_conllu(repo, file)
        if tagging == "gold":
            counts = Counter(
                parts[3]
                for parts in (line.split("\t") for line in lines if line and not line.startswith("#"))
                if len(parts) >= 4 and parts[0].isdigit() and parts[3] != "_"
            )
        elif tagging == "model":
            sentences = [line[len("# text = ") :] for line in lines if line.startswith("# text = ")]
            counts = Counter(
                tok.pos_ for doc in get_nlp(lang).pipe(sentences, batch_size=256) for tok in doc if not tok.is_space
            )
        else:
            raise ValueError(f"tagging must be 'model' or 'gold', not {tagging!r}")
        if not counts:
            raise RuntimeError(f"Empty reference distribution for {repo}/{file}")
        _POS_REF_CACHE[key] = counts
    return _POS_REF_CACHE[key]
