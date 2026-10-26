import math

from text_rigidity.formularity import FormularityReference, compute_formularity, formula_tokens

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
