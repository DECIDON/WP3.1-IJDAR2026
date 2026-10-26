"""Formatage typographique : densité des signes qui mettent le texte en page (axe liste ↔ phrase).

Faute de moyens d'impression (corps, graisses, alignements), les documents anciens structurent souvent
l'information avec des caractères : points de conduite, tirets et cadratins entre les champs,
parenthèses et crochets, pipes, accolades, signes de renvoi. Indépendant de la langue, sans spaCy.
"""
import html
import re
import unicodedata
from collections import Counter

# Familles de marques typographiques. Un caractère absent de ces listes est classé d'après sa
# catégorie Unicode (Ps/Pe/Pi/Pf : brackets, Pd/Pc : separators, Po : punctuation, S* : symbols).
TYPO_FAMILIES = {
    "punctuation": ".,;:!?…¿¡",
    "brackets": "()[]{}⟨⟩〈〉«»‹›\"“”„‟‘’'",
    "separators": "-‐‑‒–—―|¦‖/\\·•‣∙⁃_~",
    "symbols": "§¶†‡*°№&%#@+=<>$£¢¤℔⁂",
}
TYPO_ORDER = ["punctuation", "brackets", "separators", "symbols", "rules"]
_CHAR_FAMILY = {c: fam for fam, chars in TYPO_FAMILIES.items() for c in chars}
# Caractères dont la répétition forme un filet ou des points de conduite : ......  -----  * * *
_LEADER_CHARS = set(".·•_-‐‑‒–—―=*~")
_INTRAWORD = set("-‐‑'’")  # trait d'union, apostrophe

_WORD_RE = re.compile(r"[^\W_]+")
# Suite d'un même signe, éventuellement espacé : "....", ". . . .", "* * *", "--"
_RUN_RE = re.compile(r"([^\w\s]|_)(?:[ \t]?\1)*")
_EOL_RE = re.compile(r"[ \t]*\n")

_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_MD_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M)
_MD_STRONG = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", re.S)
_MD_EM = re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])")
_MD_TABLE_RULE = re.compile(r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+(?:[ \t]*:?-{3,}:?[ \t]*)?$", re.M)
_MD_TABLE_ROW = re.compile(r"^[ \t]*\|(.*)\|[ \t]*$", re.M)


def strip_markup(text: str) -> str:
    """Retire le balisage ajouté par la chaîne de numérisation (HTML, Markdown).

    Titres, gras et tableaux Markdown encodent une mise en forme qui, sur l'imprimé, passait par
    le corps ou la graisse des caractères, pas par des signes : on ne doit pas les compter.
    """
    text = _HTML_TAG.sub(" ", text)
    text = html.unescape(text)
    text = _MD_TABLE_RULE.sub("", text)
    text = _MD_TABLE_ROW.sub(lambda m: m.group(1).replace("|", "\t"), text)
    text = _MD_HEADING.sub("", text)
    text = _MD_STRONG.sub(r"\2", text)
    return _MD_EM.sub(r"\1", text)


def _typo_family(c: str) -> str | None:
    fam = _CHAR_FAMILY.get(c)
    if fam:
        return fam
    cat = unicodedata.category(c)
    if cat in ("Ps", "Pe", "Pi", "Pf"):
        return "brackets"
    if cat in ("Pd", "Pc"):
        return "separators"
    if cat == "Po":
        return "punctuation"
    if cat.startswith("S"):
        return "symbols"
    return None


def count_typographic_marks(text: str, remove_markup: bool = True) -> tuple[Counter, int]:
    """Compte les marques typographiques par famille et les mots du texte.

    Une marque est un geste typographique : une suite d'un même signe ("--", "...", "!!") compte
    pour une marque, une suite de 3 signes de filet ou plus (hors "...") est un filet (famille "rules").
    Ne sont pas comptés : traits d'union et apostrophes internes aux mots, césures de fin de
    ligne, séparateurs décimaux ou de milliers entre deux chiffres.
    """
    text = unicodedata.normalize("NFC", text)
    if remove_markup:
        text = strip_markup(text)
    counts = Counter()
    for m in _RUN_RE.finditer(text):
        c = m.group(1)
        n = m.group(0).count(c)
        if n == 1:
            prev = text[m.start() - 1] if m.start() > 0 else " "
            nxt = text[m.end()] if m.end() < len(text) else " "
            if c in _INTRAWORD and prev.isalpha() and nxt.isalpha():
                continue
            if c in ".," and prev.isdigit() and nxt.isdigit():
                continue
            if c in "-‐" and prev.isalpha() and _EOL_RE.match(text, m.end()):
                continue
        if n >= 3 and c in _LEADER_CHARS and not (c == "." and n == 3):
            fam = "rules"
        else:
            fam = _typo_family(c)
        if fam:
            counts[fam] += 1
    return counts, len(_WORD_RE.findall(text))


def compute_typographic_formatting(text: str, remove_markup: bool = True) -> dict:
    """Densité de formatage typographique, en marques pour 100 mots, totale et par famille.

    typo_no_punctuation exclut la ponctuation de phrase (. , ; : ! ? …) pour isoler les signes
    utilisés comme moyens de mise en page : brackets, separators, symbols, rules (filets).
    """
    counts, n_words = count_typographic_marks(text, remove_markup=remove_markup)
    per = 100.0 / n_words if n_words else float("nan")
    res = {f"typo_{fam}": counts[fam] * per for fam in TYPO_ORDER}
    res["typo_total"] = sum(counts.values()) * per
    res["typo_no_punctuation"] = res["typo_total"] - res["typo_punctuation"]
    return res
