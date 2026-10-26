import math

import pytest

from text_rigidity.phrastic import compute_name_density, compute_phrastic_balance, compute_verbless_rate

LIST = "Martin, épicier, rue de Seine, 12. Durand, boulanger, rue du Bac, 3. Lefèvre, tailleur, quai des Ormes, 8."
PROSE = ("Longtemps, je me suis couché de bonne heure. Parfois, à peine ma bougie éteinte, mes yeux se fermaient "
         "si vite que je n'avais pas le temps de me dire que je m'endormais.")


def test_balance_list_below_prose(fake_reference, nlp_fr):
    assert compute_phrastic_balance(LIST, "fr") < 0 < compute_phrastic_balance(PROSE, "fr")


def test_balance_reuses_parsed_doc(fake_reference, nlp_fr):
    assert compute_phrastic_balance(PROSE, "fr", doc=nlp_fr(PROSE)) == compute_phrastic_balance(PROSE, "fr")


def test_verbless_rate():
    assert compute_verbless_rate(LIST, "fr") == 1.0
    assert compute_verbless_rate(PROSE, "fr") == 0.0
    assert math.isnan(compute_verbless_rate("r. 12.", "fr"))


def test_name_density_and_exclude_spans():
    text = "Jean Dupont habite à Paris."
    full = compute_name_density(text, "fr")
    assert full > 50
    masked = compute_name_density(text, "fr", exclude_spans=[(0, len("Jean Dupont"))])
    assert masked < full


def test_unknown_language():
    with pytest.raises(ValueError):
        compute_name_density("texte", "xx")
