import math

import pytest

from text_rigidity.entropy import compute_word_entropy, entropy_rate_lz, tokenize_words, unigram_entropy


def test_tokenize_words():
    assert tokenize_words("L'Hôtel-Dieu, 12 rue X") == ["l", "hôtel", "dieu", "12", "rue", "x"]
    assert tokenize_words("rue 12", digits_to_zero=True) == ["rue", "00"]


@pytest.mark.parametrize("estimator", ["ml", "mm", "cs", "nsb"])
def test_unigram_entropy_estimators(estimator):
    tokens = ["a", "b", "c", "d"] * 50
    assert unigram_entropy(tokens, estimator) == pytest.approx(2.0, abs=0.05)


def test_unigram_entropy_plugin_exact():
    assert unigram_entropy(["a", "b"], "ml") == pytest.approx(1.0)
    with pytest.raises(ValueError):
        unigram_entropy(["a"], "inconnu")


def test_repetition_lowers_entropy_rate():
    repeated = ["le", "chat", "dort", "sur", "le", "tapis"] * 30
    assert entropy_rate_lz(repeated) < unigram_entropy(repeated)
    assert math.isnan(entropy_rate_lz(["seul"]))


def test_compute_word_entropy_windows():
    text = " ".join(["mot"] * 25)
    assert compute_word_entropy(text, n_tokens=10)["n_windows"] == 2
    res = compute_word_entropy(text, n_tokens=100)
    assert res["n_windows"] == 0 and math.isnan(res["delta_H"])
