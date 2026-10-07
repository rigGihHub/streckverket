"""Plain-language comparison between two Streckverket analyses.

Presentation-only. It compares already-produced inputs/results and never changes
probabilities, strategy, or system construction. Reasons are phrased as observed
co-changes, not proven causal claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

SIGNS = ("1", "X", "2")


@dataclass(frozen=True)
class AnalysisSnapshot:
    odds: tuple[tuple[float, float, float], ...]
    public: tuple[tuple[float, float, float], ...]
    model: tuple[tuple[float, float, float], ...]
    selections: tuple[tuple[str, ...], ...]
    readiness_headline: str
    missing_lineups: tuple[int, ...]
    missing_injuries: tuple[int, ...]


@dataclass(frozen=True)
class AnalysisChangeReport:
    headline: str
    summary: str
    details: tuple[str, ...]
    system_changed: bool
    changed_matches: tuple[int, ...]
    reasons: tuple[str, ...] = ()


def _triple(obj: Any, attr: str) -> tuple[float, float, float]:
    vals = tuple(float(x) for x in getattr(obj, attr, (0.0, 0.0, 0.0)))
    return vals[:3] if len(vals) >= 3 else (0.0, 0.0, 0.0)


def _missing(cards: Sequence[Any] | None, category: str) -> tuple[int, ...]:
    missing: list[int] = []
    for card in cards or ():
        if category in set(getattr(card, "missing", ()) or ()):
            missing.append(int(getattr(card, "match_number", 0)))
    return tuple(n for n in missing if n > 0)


def make_analysis_snapshot(
    matches: Sequence[Any],
    selections: Sequence[Sequence[str]],
    readiness_headline: str,
    cards: Sequence[Any] | None = None,
) -> AnalysisSnapshot:
    return AnalysisSnapshot(
        odds=tuple(_triple(m, "odds") for m in matches),
        public=tuple(_triple(m, "public") for m in matches),
        model=tuple(_triple(m, "model") for m in matches),
        selections=tuple(tuple(s) for s in selections),
        readiness_headline=str(readiness_headline or ""),
        missing_lineups=_missing(cards, "confirmed_lineup"),
        missing_injuries=_missing(cards, "injury_suspension"),
    )


def _selection_text(selection: Sequence[str]) -> str:
    signs = tuple(selection)
    if len(signs) == 1:
        return f"spik {signs[0]}"
    return "/".join(signs)


def _changed(old: Sequence[float], new: Sequence[float], tolerance: float) -> bool:
    return any(abs(a - b) > tolerance for a, b in zip(old, new))


def _system_change_reason(
    match_number: int,
    before: AnalysisSnapshot,
    after: AnalysisSnapshot,
    *,
    odds_tolerance: float,
    probability_tolerance: float,
) -> str:
    """Explain observed co-changes without pretending to prove causality."""
    i = match_number - 1
    factors: list[str] = []
    if i < len(before.odds) and i < len(after.odds) and _changed(before.odds[i], after.odds[i], odds_tolerance):
        factors.append("marknadsoddsen ändrades")
    if i < len(before.public) and i < len(after.public) and _changed(before.public[i], after.public[i], probability_tolerance):
        factors.append("streckfördelningen ändrades")
    if i < len(before.model) and i < len(after.model) and _changed(before.model[i], after.model[i], probability_tolerance):
        factors.append("modellens sannolikheter ändrades")
    if match_number in set(before.missing_lineups) - set(after.missing_lineups):
        factors.append("nytt verifierat startelvsunderlag tillkom")
    if match_number in set(before.missing_injuries) - set(after.missing_injuries):
        factors.append("nytt verifierat skade-/avstängningsunderlag tillkom")

    transition = f"{_selection_text(before.selections[i])} → {_selection_text(after.selections[i])}"
    if factors:
        observed = ", ".join(factors)
        return f"Match {match_number}: {transition}. Samtidigt {observed}. Det är observerade förändringar, inte bevisad enskild orsak."

    any_coupon_input_change = any(
        _changed(a, b, probability_tolerance)
        for old_group, new_group in ((before.public, after.public), (before.model, after.model))
        for a, b in zip(old_group, new_group)
    ) or any(_changed(a, b, odds_tolerance) for a, b in zip(before.odds, after.odds))
    if any_coupon_input_change:
        return (
            f"Match {match_number}: {transition}. Ingen tydlig lokal dataändring hittades i matchen; "
            "systemet optimeras över hela kupongen, så budgeten kan ha flyttats när andra matcher ändrades."
        )
    return (
        f"Match {match_number}: {transition}. Inga synliga odds-, streck- eller modellförändringar hittades; "
        "ändringen kan därför inte förklaras säkert av förändringsrapporten."
    )


def compare_analysis_snapshots(
    before: AnalysisSnapshot,
    after: AnalysisSnapshot,
    *,
    odds_tolerance: float = 0.005,
    probability_tolerance: float = 0.005,
) -> AnalysisChangeReport:
    odds_changed: list[int] = []
    public_changed: list[int] = []
    model_changed: list[int] = []
    for i, (old, new) in enumerate(zip(before.odds, after.odds), start=1):
        if _changed(old, new, odds_tolerance):
            odds_changed.append(i)
    for i, (old, new) in enumerate(zip(before.public, after.public), start=1):
        if _changed(old, new, probability_tolerance):
            public_changed.append(i)
    for i, (old, new) in enumerate(zip(before.model, after.model), start=1):
        if _changed(old, new, probability_tolerance):
            model_changed.append(i)

    changed_system: list[int] = []
    details: list[str] = []
    for i, (old, new) in enumerate(zip(before.selections, after.selections), start=1):
        if tuple(old) != tuple(new):
            changed_system.append(i)
            details.append(f"Match {i}: {_selection_text(old)} → {_selection_text(new)}")

    newly_confirmed = sorted(set(before.missing_lineups) - set(after.missing_lineups))
    newly_injury_info = sorted(set(before.missing_injuries) - set(after.missing_injuries))
    readiness_changed = before.readiness_headline != after.readiness_headline

    parts: list[str] = []
    if odds_changed:
        parts.append(f"odds ändrades i {len(odds_changed)} matcher")
    if public_changed:
        parts.append(f"streckfördelningen ändrades i {len(public_changed)} matcher")
    if model_changed:
        parts.append(f"modellsannolikheter ändrades i {len(model_changed)} matcher")
    if newly_confirmed:
        parts.append(f"startelvsunderlaget förbättrades i {len(newly_confirmed)} matcher")
    if newly_injury_info:
        parts.append(f"skade-/avstängningsunderlaget förbättrades i {len(newly_injury_info)} matcher")
    if readiness_changed:
        parts.append(f"status ändrades från {before.readiness_headline} till {after.readiness_headline}")

    if changed_system:
        headline = f"SYSTEMET ÄNDRADES I {len(changed_system)} MATCHER"
        parts.append(f"systemtecknen ändrades i {len(changed_system)} matcher")
    else:
        headline = "SYSTEMET ÄR OFÖRÄNDRAT"
        parts.append("systemtecknen är oförändrade")

    if not (odds_changed or public_changed or model_changed or newly_confirmed or newly_injury_info or readiness_changed or changed_system):
        summary = "Den nya analysen gav inga synliga förändringar i odds, streck, modell, status, lagunderlag eller systemtecken."
    else:
        summary = "; ".join(parts).capitalize() + "."

    if odds_changed:
        details.append("Odds ändrades: match " + ", ".join(str(n) for n in odds_changed) + ".")
    if public_changed:
        details.append("Streckfördelningen ändrades: match " + ", ".join(str(n) for n in public_changed) + ".")
    if model_changed:
        details.append("Modellens sannolikheter ändrades: match " + ", ".join(str(n) for n in model_changed) + ".")
    if newly_confirmed:
        details.append("Nytt startelvsunderlag: match " + ", ".join(str(n) for n in newly_confirmed) + ".")
    if newly_injury_info:
        details.append("Nytt skade-/avstängningsunderlag: match " + ", ".join(str(n) for n in newly_injury_info) + ".")
    if readiness_changed:
        details.append(f"Spelklarhetsstatus: {before.readiness_headline} → {after.readiness_headline}.")

    reasons = tuple(
        _system_change_reason(
            n, before, after,
            odds_tolerance=odds_tolerance,
            probability_tolerance=probability_tolerance,
        )
        for n in changed_system
    )

    return AnalysisChangeReport(
        headline=headline,
        summary=summary,
        details=tuple(details),
        system_changed=bool(changed_system),
        changed_matches=tuple(changed_system),
        reasons=reasons,
    )
