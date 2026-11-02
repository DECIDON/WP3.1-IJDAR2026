import math

from text_rigidity.formularity import FormularityReference, compute_formularity, compute_self_bleu, formula_tokens

NAMES = ["Martin", "Durand", "Lefèvre", "Bernard", "Petit", "Moreau", "Laurent", "Simon", "Michel", "Garcia"]
TRADES = ["épicier", "boulanger", "tailleur", "cordonnier", "menuisier"]


def directory_page(k):
    return " ".join(
        f"{NAMES[(k + i) % len(NAMES)]}, {TRADES[(k * 3 + i) % len(TRADES)]}, demeurant rue de Seine, n° {k * 10 + i}."
        for i in range(12)
    )


DOCS = [(f"page-{k}", directory_page(k)) for k in range(8)]
PROSE = ("Longtemps, je me suis couché de bonne heure. Parfois, à peine ma bougie éteinte, mes yeux se fermaient "
         "si vite que je n'avais pas le temps de me dire que je m'endormais.")


def test_formula_tokens_abstract_names_and_numbers(nlp_fr):
    toks = formula_tokens(nlp_fr("Martin, épicier, rue de Seine, 12."))
    assert "<NUM>" in toks and "<NAME>" in toks and "martin" not in toks


def test_directory_is_formulaic():
    ref = FormularityReference(DOCS, lang="fr")
    page = compute_formularity(directory_page(99), ref, doc_id="page-99", lang="fr")
    prose = compute_formularity(PROSE, ref, doc_id="prose", lang="fr")
    assert page["formularity"] > 50
    assert prose["formularity"] == 0
    assert page["ref_tokens"] > 0


def test_leave_one_document_out():
    ref = FormularityReference(DOCS[:1], lang="fr")
    counts, size = ref.counts_for("page-0")
    assert size == 0 and not counts
    assert compute_formularity(DOCS[0][1], ref, doc_id="page-0", lang="fr")["formularity"] == 0


def test_short_window_is_nan():
    ref = FormularityReference(DOCS, lang="fr")
    assert math.isnan(compute_formularity("Martin", ref, lang="fr")["formularity"])


def test_dispersion_ignores_repetition_within_one_document():
    tic = "Le comité a décidé que la séance serait levée. "
    docs = DOCS + [("bavard", tic * 6)]
    ref = FormularityReference(docs, lang="fr")
    window = "Ce soir encore, " + tic
    assert compute_formularity(window, ref, doc_id="autre", lang="fr")["formularity"] > 0
    assert compute_formularity(window, ref, doc_id="autre", lang="fr", min_docs=2)["formularity"] == 0
    # les gabarits de l'annuaire reviennent dans plusieurs pages : ils passent le critère
    assert compute_formularity(directory_page(99), ref, doc_id="page-99", lang="fr", min_docs=3)["formularity"] > 50


def test_self_bleu_directory_above_prose():
    ref = FormularityReference(DOCS, lang="fr")
    page = compute_self_bleu(directory_page(99), ref, doc_id="page-99", lang="fr")
    prose = compute_self_bleu(PROSE, ref, doc_id="prose", lang="fr")
    assert page["self_bleu"] > 3 * prose["self_bleu"]
    assert 0 < prose["self_bleu"] < 100 and page["ref_tokens"] > 0


def test_self_bleu_leave_one_document_out_and_identity():
    ref = FormularityReference(DOCS[:2], lang="fr")
    # la page 0 est exclue de sa propre référence ; recopiée sous un autre identifiant, elle se retrouve en entier
    assert compute_self_bleu(DOCS[0][1], ref, doc_id="page-0", lang="fr")["self_bleu"] < 100
    assert compute_self_bleu(DOCS[0][1], ref, doc_id="autre", lang="fr")["self_bleu"] == 100


def test_self_bleu_is_order_sensitive():
    ref = FormularityReference(DOCS, lang="fr")
    words = directory_page(99).split()
    shuffled = " ".join(words[::7] + words[1::7] + words[2::7] + words[3::7] + words[4::7] + words[5::7] + words[6::7])
    assert (compute_self_bleu(shuffled, ref, doc_id="x", lang="fr")["self_bleu"]
            < compute_self_bleu(directory_page(99), ref, doc_id="x", lang="fr")["self_bleu"] / 2)


def test_self_bleu_short_window_is_nan():
    ref = FormularityReference(DOCS, lang="fr")
    assert math.isnan(compute_self_bleu("Martin", ref, lang="fr")["self_bleu"])
