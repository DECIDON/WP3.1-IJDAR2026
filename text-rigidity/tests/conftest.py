from collections import Counter

import pytest

from text_rigidity import nlp, phrastic

# Distribution UPOS factice, à la place du treebank PUD téléchargé depuis GitHub
# (mots de liaison et autres mots à peu près à parts égales : log2-odds de la référence ≈ 0,1)
FAKE_REFERENCE = Counter({"NOUN": 250, "VERB": 80, "AUX": 30, "DET": 120, "ADP": 120, "PRON": 40, "ADJ": 80,
                          "ADV": 50, "CCONJ": 25, "SCONJ": 15, "PROPN": 50, "NUM": 20, "PUNCT": 120})


@pytest.fixture
def fake_reference(monkeypatch):
    """Remplace la référence UD du français par FAKE_REFERENCE, pour tester sans réseau."""
    monkeypatch.setitem(nlp._POS_REF_CACHE, ("fr", "UD_French-PUD", "fr_pud-ud-test.conllu", "model"), FAKE_REFERENCE)
    monkeypatch.setattr(phrastic, "_REF_ODDS_CACHE", {})
    return FAKE_REFERENCE


@pytest.fixture(scope="session")
def nlp_fr():
    return nlp.get_nlp("fr")
