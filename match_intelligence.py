from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from core import normalize
from evidence import EvidenceSignal, adjust_probabilities
from source_consensus import Observation, ConsensusResult, resolve_consensus

CRITICAL_CATEGORIES = {
    "market": 0.24,
    "team_strength": 0.15,
    "home_away_form": 0.12,
    "injury_suspension": 0.14,
    "confirmed_lineup": 0.14,
    "rest_schedule": 0.06,
    "weather": 0.04,
    "referee": 0.04,
    "fan_sentiment": 0.02,
    "other": 0.05,
}

@dataclass(frozen=True)
class IntelligenceClaim:
    key: str
    category: str
    observations: tuple[Observation, ...] = ()
    consensus: ConsensusResult | None = None

    @property
    def usable(self) -> bool:
        return bool(self.consensus and self.consensus.usable_for_model)

    @property
    def conflict(self) -> bool:
        return bool(self.consensus and self.consensus.conflicts)

@dataclass
class MatchIntelligenceCard:
    match_number: int
    home: str
    away: str
    base_market: tuple[float,float,float]
    final_model: tuple[float,float,float]
    claims: list[IntelligenceClaim] = field(default_factory=list)
    used_signals: list[EvidenceSignal] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)
    readiness_score: int = 0
    readiness_label: str = "Låg"
    conflicts: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def resolve_claim(key: str, category: str, observations: Iterable[Observation]) -> IntelligenceClaim:
    obs = tuple(observations)
    consensus = resolve_consensus(obs) if obs else None
    return IntelligenceClaim(key=key, category=category, observations=obs, consensus=consensus)


def _category_ready(category: str, claims: Sequence[IntelligenceClaim], signals: Sequence[EvidenceSignal]) -> float:
    # market is represented by the base probabilities and always available for a valid card
    if category == "market":
        return 1.0
    cat_claims = [c for c in claims if c.category == category]
    if cat_claims:
        scores = [c.consensus.score for c in cat_claims if c.consensus]
        usable = [c for c in cat_claims if c.usable]
        if usable:
            return min(1.0, max([c.consensus.score for c in usable if c.consensus] or [0.0]))
        if scores:
            return 0.25 * max(scores)
    cat_signals = [s for s in signals if s.category == category and s.is_verified]
    if cat_signals:
        return min(1.0, max(s.effective_strength for s in cat_signals))
    return 0.0


def readiness(claims: Sequence[IntelligenceClaim], signals: Sequence[EvidenceSignal]) -> tuple[int,str,list[str],list[str]]:
    weighted = 0.0
    missing=[]
    conflicts=[]
    for category, weight in CRITICAL_CATEGORIES.items():
        val = _category_ready(category, claims, signals)
        weighted += weight * val
        if weight >= 0.06 and val < 0.20:
            missing.append(category)
    for c in claims:
        if c.conflict:
            conflicts.append(c.key)
            weighted -= 0.025
    score=max(0,min(100,round(100*weighted)))
    label="Hög" if score >= 75 else "Medel" if score >= 50 else "Låg"
    return score,label,conflicts,missing


def build_match_card(
    *,
    match_number: int,
    home: str,
    away: str,
    base_market: Sequence[float],
    claims: Sequence[IntelligenceClaim] = (),
    signals: Sequence[EvidenceSignal] = (),
    max_total_shift: float = 0.14,
) -> MatchIntelligenceCard:
    base=normalize(base_market)
    # Only verified evidence signals may alter the probability model. Claims are used to decide
    # whether upstream facts are trusted before a caller creates such a signal.
    used=[s for s in signals if s.is_verified and s.effective_strength > 0]
    final,audit=adjust_probabilities(base, used, max_total_shift=max_total_shift)
    score,label,conflicts,missing=readiness(claims,used)
    return MatchIntelligenceCard(
        match_number=match_number, home=home, away=away,
        base_market=tuple(base), final_model=tuple(final),
        claims=list(claims), used_signals=used, audit=audit,
        readiness_score=score, readiness_label=label,
        conflicts=conflicts, missing=missing,
    )


def card_summary(card: MatchIntelligenceCard) -> dict[str, object]:
    delta=tuple(f-b for b,f in zip(card.base_market,card.final_model))
    return {
        "Nr": card.match_number,
        "Match": f"{card.home} – {card.away}",
        "Readiness": f"{card.readiness_score}/100 · {card.readiness_label}",
        "Källkonflikter": len(card.conflicts),
        "Saknas": ", ".join(card.missing) if card.missing else "–",
        "Δ1": delta[0], "ΔX": delta[1], "Δ2": delta[2],
        "Signaler i modell": len(card.used_signals),
    }
