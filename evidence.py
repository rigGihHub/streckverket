from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from core import SIGNS, normalize


@dataclass(frozen=True)
class EvidenceSignal:
    """En verifierbar informationssignal för en match.

    impact är en riktad förändring i log-vikt för 1/X/2, inte procentenheter.
    reliability 0..1 anger käll-/datakvalitet. weight är signaltypens maxvikt.
    """
    category: str
    label: str
    impact: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    reliability: float = 0.0
    weight: float = 0.0
    source: str = ""
    updated_at: Optional[str] = None
    sample_size: Optional[int] = None
    explanation: str = ""
    is_verified: bool = False

    @property
    def effective_strength(self) -> float:
        if not self.is_verified:
            return 0.0
        r = min(1.0, max(0.0, self.reliability))
        w = min(1.0, max(0.0, self.weight))
        return r * w


DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
    "market_move": 0.80,
    "confirmed_lineup": 0.75,
    "injury_suspension": 0.65,
    "team_strength": 0.60,
    "home_away_form": 0.50,
    "rest_schedule": 0.35,
    "manager_change": 0.30,
    "referee": 0.20,
    "weather": 0.18,
    "travel": 0.15,
    "fan_sentiment": 0.10,
    "motivation": 0.10,
}


def capped_sample_reliability(sample_size: Optional[int], full_at: int = 20) -> float:
    if not sample_size or sample_size <= 0:
        return 0.0
    return min(1.0, sample_size / float(full_at))


def make_signal(
    category: str,
    label: str,
    impact: Sequence[float],
    reliability: float,
    source: str,
    *,
    updated_at: Optional[str] = None,
    sample_size: Optional[int] = None,
    explanation: str = "",
    is_verified: bool = True,
    weight: Optional[float] = None,
) -> EvidenceSignal:
    if len(impact) != 3:
        raise ValueError("impact måste innehålla 1/X/2")
    category_weight = DEFAULT_CATEGORY_WEIGHTS.get(category, 0.10) if weight is None else weight
    if sample_size is not None:
        reliability = reliability * capped_sample_reliability(sample_size)
    return EvidenceSignal(
        category=category,
        label=label,
        impact=tuple(float(x) for x in impact),
        reliability=float(reliability),
        weight=float(category_weight),
        source=source,
        updated_at=updated_at,
        sample_size=sample_size,
        explanation=explanation,
        is_verified=is_verified,
    )


def adjust_probabilities(
    base: Sequence[float],
    signals: Iterable[EvidenceSignal],
    *,
    max_total_shift: float = 0.22,
) -> Tuple[Tuple[float, float, float], List[Dict[str, object]]]:
    """Justerar marknadsbasen med spårbara, reliability-viktade log-signaler.

    max_total_shift begränsar avståndet mot marknadsbasen för att undvika falsk precision.
    """
    base = normalize(base)
    logs = [log(max(1e-9, p)) for p in base]
    contributions: List[Dict[str, object]] = []

    for signal in signals:
        strength = signal.effective_strength
        scaled = tuple(v * strength for v in signal.impact)
        if strength > 0:
            logs = [x + d for x, d in zip(logs, scaled)]
        contributions.append({
            "category": signal.category,
            "label": signal.label,
            "strength": strength,
            "scaled_impact": scaled,
            "source": signal.source,
            "updated_at": signal.updated_at,
            "explanation": signal.explanation,
            "verified": signal.is_verified,
        })

    raw = normalize([exp(x) for x in logs])
    # L1-avståndets halva motsvarar flyttad sannolikhetsmassa.
    moved = 0.5 * sum(abs(a-b) for a,b in zip(raw, base))
    if moved > max_total_shift and moved > 0:
        alpha = max_total_shift / moved
        raw = normalize([b + alpha*(r-b) for b,r in zip(base, raw)])
    return raw, contributions


def data_quality(signals: Iterable[EvidenceSignal]) -> Dict[str, object]:
    sigs = list(signals)
    verified = [s for s in sigs if s.is_verified]
    if not sigs:
        return {"score": 0, "label": "Saknas", "verified": 0, "total": 0}
    score = 100 * sum(s.effective_strength for s in verified) / max(1.0, sum(max(0.05, s.weight) for s in sigs))
    score = max(0, min(100, round(score)))
    label = "Hög" if score >= 70 else "Medel" if score >= 40 else "Låg"
    return {"score": score, "label": label, "verified": len(verified), "total": len(sigs)}


def weather_signal_from_history(
    *,
    home_points_per_game_condition: float,
    home_points_per_game_normal: float,
    away_points_per_game_condition: float,
    away_points_per_game_normal: float,
    sample_size: int,
    source: str,
    explanation: str,
) -> EvidenceSignal:
    """Konservativ vädersignal baserad på faktisk historik, inte väderetiketter i sig."""
    home_delta = home_points_per_game_condition - home_points_per_game_normal
    away_delta = away_points_per_game_condition - away_points_per_game_normal
    edge = max(-1.0, min(1.0, (home_delta - away_delta) / 1.5))
    # liten påverkan: väder får aldrig dominera modellen
    impact = (0.30*edge, 0.06*abs(edge), -0.30*edge)
    return make_signal(
        "weather", "Historik i liknande väder", impact, 0.85, source,
        sample_size=sample_size, explanation=explanation,
    )


def referee_signal(
    *,
    home_style_edge: float,
    sample_size: int,
    source: str,
    explanation: str,
) -> EvidenceSignal:
    """Domarsignal måste bygga på en definierad matchup-effekt, inte bara kortsnitt."""
    edge = max(-1.0, min(1.0, home_style_edge))
    return make_signal(
        "referee", "Domarprofil mot lagens spelstil",
        (0.22*edge, 0.04*abs(edge), -0.22*edge),
        0.80, source, sample_size=sample_size, explanation=explanation,
    )


def fan_sentiment_signal(
    *,
    relative_sentiment_edge: float,
    post_count: int,
    source: str,
    explanation: str,
) -> EvidenceSignal:
    """Supportersentiment är avsiktligt mycket svagt och kräver volym."""
    edge = max(-1.0, min(1.0, relative_sentiment_edge))
    return make_signal(
        "fan_sentiment", "Supportersentiment",
        (0.16*edge, 0.02*abs(edge), -0.16*edge),
        0.55, source, sample_size=post_count, explanation=explanation,
        weight=DEFAULT_CATEGORY_WEIGHTS["fan_sentiment"],
    )
