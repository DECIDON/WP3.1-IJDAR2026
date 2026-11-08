"""Matcher NERC HIPE-conforme via **nervaluate** (MantisAI, v1.2.x — D. Batista & M. Upson,
successeur maintenu de davidsbatista/NER-Evaluation ; algo SemEval'13, = celui dont dérive le
HIPE-scorer CLEF). REMPLACE `lib/hipe_match` (matcher maison) — décision cross-forge 2026-06-10
après validation externe (cf. forge §HIPE-scorer) : sur les sorties chevauchantes (no-NMS) le
matcher maison était trop INDULGENT (pas de règle de « consommation » SemEval'13) → headline gonflé
(+0.146 sur 8è no-NMS) ; nervaluate gère nativement chevauchement/nesting, sans tokenisation (offsets).

Module **forge-agnostique** (à COPIER tel quel dans chaque forge, pas d'import croisé — collectif §6.F).
Dépendance : `nervaluate` (pip, léger).

Régimes SemEval'13 exposés (les 4) :
  - strict   : frontière exacte + type   (= ancien HIPE-strict ; HEADLINE / DIRECTEUR)
  - ent_type : type + chevauchement ≥1   (= ancien HIPE-fuzzy)
  - exact    : frontière exacte, type-agnostique
  - partial  : chevauchement, type-agnostique, crédit 0.5 aux partiels

Interface alignée sur l'ancien `hipe_match` pour minimiser la réécriture des appelants :
`count_page(gold, pred, regime) -> (cor_eff, act, pos)`, puis `prf`/`micro` génériques poolent.
`cor_eff` est un FLOAT (= correct, + 0.5·partial pour le régime `partial`). Le matching SemEval'13
étant INTRA-document, compter par page puis pooler == nervaluate sur l'ensemble (vérifié).
"""
from __future__ import annotations

from dataclasses import dataclass

from nervaluate import Evaluator

# (label, start, end) — offsets caractère relatifs au texte de PAGE (task.full_text).
Span = tuple[str, int, int]

# strict = DIRECTEUR (headline). ent_type = fuzzy. + exact + partial (demandés 2026-06-10).
MODES = ("strict", "ent_type", "exact", "partial")
HEADLINE_MODE = "strict"


def _to_ents(spans: list[Span]) -> list[dict]:
    return [{"label": l, "start": s, "end": e} for (l, s, e) in spans]


def count_page(gold: list[Span], pred: list[Span], regime: str) -> tuple[float, int, int]:
    """(COR_eff, ACT, POS) sur UNE page pour un régime SemEval'13, via nervaluate.

    COR_eff = correct (+ 0.5·partial pour `partial`). ACT = #pred système, POS = #gold.
    Pooler ces comptes sur les pages == nervaluate sur l'ensemble (matching intra-doc + pool).
    """
    # Court-circuit des cas VIDES (fréquent en per-label) : aucun match possible → COR=0, quel que
    # soit le régime. Évite aussi un bug nervaluate (`true[0][0]` IndexError quand un doc est `[[]]`).
    if not gold or not pred:
        return 0.0, len(pred), len(gold)
    tags = sorted({l for l, _, _ in gold} | {l for l, _, _ in pred})
    res = Evaluator([_to_ents(gold)], [_to_ents(pred)], tags=tags).evaluate()
    r = res["overall"][regime]
    cor = r.correct + (0.5 * r.partial if regime == "partial" else 0.0)
    return float(cor), int(r.actual), int(r.possible)


@dataclass
class PRF:
    precision: float
    recall: float
    f1: float
    cor: float
    act: int
    pos: int


def prf(cor: float, act: int, pos: int) -> PRF:
    p = cor / act if act else 0.0
    r = cor / pos if pos else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return PRF(p, r, f1, cor, act, pos)


def micro(per_unit: list[tuple[float, int, int]]) -> PRF:
    """Micro = COR/ACT/POS poolés sur toutes les pages (headline NERC HIPE)."""
    cor = sum(c for c, _, _ in per_unit)
    act = sum(a for _, a, _ in per_unit)
    pos = sum(p for _, _, p in per_unit)
    return prf(cor, act, pos)


def macro_f1(per_label: dict[str, PRF], labels: list[str]) -> float:
    """Macro = moyenne des F1 par label (sur `labels`)."""
    vals = [per_label[l].f1 for l in labels if l in per_label]
    return sum(vals) / len(vals) if vals else 0.0
