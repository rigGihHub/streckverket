from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from core import SIGNS
from facit import FacitCoupon, FacitMatch


@dataclass(frozen=True)
class DiagnosticRow:
    segment: str
    matches: int
    model_brier: float
    market_brier: float
    improvement: float
    model_pick_accuracy: float
    market_pick_accuracy: float
    verdict: str
    explanation: str


def _idx(result: str) -> int:
    return SIGNS.index(result)


def _pick(probs: Sequence[float]) -> int:
    return max(range(3), key=lambda i: float(probs[i]))


def _brier(probs: Sequence[float], result: str) -> float:
    y = _idx(result)
    return sum((float(probs[i]) - (1.0 if i == y else 0.0)) ** 2 for i in range(3))


def _completed(coupons: Iterable[FacitCoupon]) -> List[FacitMatch]:
    return [m for c in coupons for m in c.matches if m.result in SIGNS]


def _segment_row(name: str, matches: Sequence[FacitMatch], min_sample: int) -> DiagnosticRow | None:
    if not matches:
        return None
    n = len(matches)
    model_brier = sum(_brier(m.model, m.result) for m in matches) / n  # type: ignore[arg-type]
    market_brier = sum(_brier(m.market, m.result) for m in matches) / n  # type: ignore[arg-type]
    improvement = market_brier - model_brier
    model_acc = sum(_pick(m.model) == _idx(m.result) for m in matches) / n  # type: ignore[arg-type]
    market_acc = sum(_pick(m.market) == _idx(m.result) for m in matches) / n  # type: ignore[arg-type]

    if n < min_sample:
        verdict = "För lite data"
        explanation = f"Bara {n} matcher. Vi visar riktningen men ändrar inte modellen utifrån detta ännu."
    elif improvement >= 0.03:
        verdict = "Ser lovande ut"
        explanation = "Streckverkets sannolikheter har varit tydligt bättre än marknadsbasen i den här typen av matcher."
    elif improvement <= -0.03:
        verdict = "Behöver granskas"
        explanation = "Marknadsbasen har varit tydligt bättre här. Streckverkets extra justeringar kan vara för starka eller peka åt fel håll."
    else:
        verdict = "Ingen tydlig skillnad"
        explanation = "Streckverket och marknadsbasen ligger nära varandra. Mer historik behövs innan vi drar slutsatser."

    return DiagnosticRow(
        segment=name,
        matches=n,
        model_brier=model_brier,
        market_brier=market_brier,
        improvement=improvement,
        model_pick_accuracy=model_acc,
        market_pick_accuracy=market_acc,
        verdict=verdict,
        explanation=explanation,
    )


def diagnostic_segments(coupons: Sequence[FacitCoupon], min_sample: int = 30) -> List[DiagnosticRow]:
    """Evaluate situations where Streckverket changes or challenges the market/public.

    Positive ``improvement`` means lower (better) Brier score than the market.
    Segments overlap intentionally: each answers a different practical question.
    """
    if min_sample < 5:
        raise ValueError("min_sample måste vara minst 5")
    matches = _completed(coupons)
    if not matches:
        return []

    def delta(m: FacitMatch) -> float:
        return max(abs(float(a) - float(b)) for a, b in zip(m.model, m.market))

    def public_favorite(m: FacitMatch) -> int:
        return _pick(m.public)

    segments: List[Tuple[str, List[FacitMatch]]] = [
        ("Alla matcher", matches),
        ("Streckverket ändrar marknaden tydligt", [m for m in matches if delta(m) >= 0.05]),
        ("Streckverket ligger nära marknaden", [m for m in matches if delta(m) < 0.03]),
        (
            "Vi går emot folkets favorit",
            [m for m in matches if _pick(m.model) != public_favorite(m)],
        ),
        (
            "Överstreckad favorit",
            [m for m in matches if float(m.public[public_favorite(m)]) - float(m.model[public_favorite(m)]) >= 0.10],
        ),
        (
            "Modellen är ganska säker (60 %+)",
            [m for m in matches if max(float(x) for x in m.model) >= 0.60],
        ),
        (
            "Modellen är osäker (ingen över 45 %)",
            [m for m in matches if max(float(x) for x in m.model) <= 0.45],
        ),
    ]

    rows: List[DiagnosticRow] = []
    for name, subset in segments:
        row = _segment_row(name, subset, min_sample)
        if row is not None:
            rows.append(row)
    return rows


def strongest_lessons(rows: Sequence[DiagnosticRow]) -> dict:
    eligible = [r for r in rows if r.segment != "Alla matcher" and r.verdict != "För lite data"]
    if not eligible:
        return {
            "best": None,
            "worst": None,
            "summary": "Det finns ännu för lite historik för att säga vilka typer av Streckverket-beslut som fungerar bäst eller sämst.",
        }
    best = max(eligible, key=lambda r: r.improvement)
    worst = min(eligible, key=lambda r: r.improvement)
    if best.improvement <= 0.01 and worst.improvement >= -0.01:
        summary = "Inget analyserat läge skiljer sig tydligt från marknadsbasen ännu. Fortsätt samla facit."
    else:
        summary = (
            f"Starkast hittills: {best.segment.lower()}. "
            f"Svagast hittills: {worst.segment.lower()}. Detta är en historisk signal, inte en garanti för nästa kupong."
        )
    return {"best": best, "worst": worst, "summary": summary}


def recommended_action(rows: Sequence[DiagnosticRow]) -> str:
    """Conservative model-development action; never auto-changes weights."""
    eligible = [r for r in rows if r.segment != "Alla matcher" and r.verdict != "För lite data"]
    bad = sorted((r for r in eligible if r.improvement <= -0.03), key=lambda r: r.improvement)
    good = sorted((r for r in eligible if r.improvement >= 0.03), key=lambda r: r.improvement, reverse=True)
    if bad:
        return (
            f"Granska först '{bad[0].segment}'. Marknaden har varit bättre i det läget. "
            "Streckverket ska inte automatiskt ändra några vikter; orsaken måste först analyseras på fler matcher."
        )
    if good:
        return (
            f"'{good[0].segment}' ser lovande ut. Behåll signalen under observation, men höj inte vikten automatiskt förrän resultatet håller över ett större och nytt datamaterial."
        )
    return "Ingen modelländring rekommenderas ännu. Fortsätt samla facit och jämför på nytt när underlaget har vuxit."
