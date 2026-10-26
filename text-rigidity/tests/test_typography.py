import math

import pytest

from text_rigidity.typography import compute_typographic_formatting, count_typographic_marks, strip_markup


def test_directory_entry():
    counts, n_words = count_typographic_marks("Martin, épicier, r. de Seine, 12.")
    assert counts == {"punctuation": 5}
    assert n_words == 6
    assert compute_typographic_formatting("Martin, épicier, r. de Seine, 12.")["typo_total"] == pytest.approx(500 / 6)


def test_leaders_are_one_mark():
    counts, _ = count_typographic_marks("Martin ........ 12 — Durand . . . . 4")
    assert counts == {"rules": 2, "separators": 1}


def test_ellipsis_is_punctuation():
    counts, _ = count_typographic_marks("Il attendit...")
    assert counts == {"punctuation": 1}


def test_ignored_signs():
    # traits d'union et apostrophes internes, séparateurs numériques, césure de fin de ligne
    counts, n_words = count_typographic_marks("Saint-Honoré l'acte 1.500 3,5 épi-\ncier")
    assert counts == {}
    assert n_words == 10


def test_families():
    res = compute_typographic_formatting("(a) [b] | c § d")
    assert res["typo_brackets"] == pytest.approx(100.0)
    assert res["typo_separators"] == pytest.approx(25.0)
    assert res["typo_symbols"] == pytest.approx(25.0)
    assert res["typo_no_punctuation"] == res["typo_total"]


def test_strip_markup():
    assert strip_markup("# Titre\n**gras** et *ital*").split() == ["Titre", "gras", "et", "ital"]
    assert strip_markup("<p>a &amp; b</p>").split() == ["a", "&", "b"]
    assert count_typographic_marks("**gras**")[0] == {}
    assert count_typographic_marks("**gras**", remove_markup=False)[0] == {"symbols": 2}


def test_empty_text_is_nan():
    assert math.isnan(compute_typographic_formatting("")["typo_total"])
