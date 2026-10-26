import math
from collections import Counter

import pytest

from text_rigidity import get_all_metrics, get_pos_reference_counts
from text_rigidity.divergence import compute_pos_kl_divergence, kl_divergence_counts


def test_kl_divergence_counts():
    c = Counter({"NOUN": 3, "VERB": 1})
    assert kl_divergence_counts(c, c) == pytest.approx(0.0, abs=1e-9)
    assert kl_divergence_counts(Counter({"NOUN": 4}), c) > 0
    assert kl_divergence_counts(Counter(), c) == 0.0


def test_kl_with_explicit_reference(nlp_fr):
    doc = nlp_fr("Le chat dort sur le tapis.")
    own = Counter(t.pos_ for t in doc)
    assert compute_pos_kl_divergence(doc.text, "fr", pos_ref=own, doc=doc) == pytest.approx(0.0, abs=1e-9)
    assert compute_pos_kl_divergence(doc.text, "fr", pos_ref={"PROPN": 1}, doc=doc) > 1


def test_get_all_metrics(fake_reference):
    m = get_all_metrics("Martin, épicier, rue de Seine, 12.\nDurand, boulanger, rue du Bac, 3.", lang="fr")
    assert set(m) == {"typo", "balance", "verbless", "lex", "names", "zlib", "w_line", "kl", "ppl"}
    assert m["w_line"] == 6.0
    assert math.isnan(m["ppl"])  # pas de modèle KenLM fourni


@pytest.mark.network
def test_pud_reference_download():
    counts = get_pos_reference_counts("fr", "gold")
    assert counts["NOUN"] > 1000
