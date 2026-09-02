from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Sequence

from core import MatchInput, SIGNS
from evidence import EvidenceSignal
from match_intelligence import IntelligenceClaim, MatchIntelligenceCard, build_match_card


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ProviderOutput:
    provider: str
    signals: list[EvidenceSignal] = field(default_factory=list)
    claims: list[IntelligenceClaim] = field(default_factory=list)
    message: str = ""
    quality: str = "Medel"
    metadata: dict = field(default_factory=dict)


@dataclass
class StageStatus:
    provider: str
    ok: bool
    fetched_at: str
    quality: str
    message: str
    error_type: str | None = None


@dataclass
class MatchPipelineResult:
    match: MatchInput
    enriched_match: MatchInput
    card: MatchIntelligenceCard
    stages: list[StageStatus]

    @property
    def failed_sources(self) -> list[str]:
        return [s.provider for s in self.stages if not s.ok]


Provider = Callable[[MatchInput], ProviderOutput]


def run_match_pipeline(match: MatchInput, providers: Sequence[Provider], *, max_total_shift: float = 0.14) -> MatchPipelineResult:
    """Kör varje källa isolerat. En källa får aldrig krascha resten av matchanalysen."""
    signals: list[EvidenceSignal] = []
    claims: list[IntelligenceClaim] = []
    stages: list[StageStatus] = []
    for provider in providers:
        name = getattr(provider, "provider_name", getattr(provider, "__name__", "okänd källa"))
        try:
            out = provider(match)
            signals.extend(out.signals)
            claims.extend(out.claims)
            stages.append(StageStatus(out.provider or name, True, _now(), out.quality, out.message or "OK"))
        except Exception as exc:
            stages.append(StageStatus(str(name), False, _now(), "Saknas", str(exc), type(exc).__name__))

    card = build_match_card(
        match_number=match.number, home=match.home, away=match.away,
        base_market=match.market, claims=claims, signals=signals,
        max_total_shift=max_total_shift,
    )
    enriched = MatchInput(
        match.number, match.home, match.away, match.odds, match.public, tuple(card.final_model),
        kickoff=match.kickoff, competition=match.competition,
    )
    return MatchPipelineResult(match, enriched, card, stages)


def run_coupon_pipeline(matches: Sequence[MatchInput], providers: Sequence[Provider], *, max_total_shift: float = 0.14) -> list[MatchPipelineResult]:
    return [run_match_pipeline(m, providers, max_total_shift=max_total_shift) for m in matches]


def recommendation(probabilities: Sequence[float]) -> str:
    return SIGNS[max(range(3), key=lambda i: probabilities[i])]


def recommendation_change(before: Sequence[float], after: Sequence[float], *, threshold_pp: float = 2.0) -> dict:
    b = tuple(before); a = tuple(after)
    old, new = recommendation(b), recommendation(a)
    deltas = tuple((x-y)*100 for x,y in zip(a,b))
    max_move = max(abs(x) for x in deltas)
    return {
        "changed_sign": old != new,
        "material": old != new or max_move >= threshold_pp,
        "before": old,
        "after": new,
        "delta_pp": deltas,
        "max_move_pp": max_move,
    }
