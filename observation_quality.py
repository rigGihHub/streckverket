from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class ObservationQuality:
    score: int
    label: str
    evidence_coverage: int
    reasons: tuple[str, ...]
    missing: tuple[str, ...]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _bounded_points(value: float, maximum: int) -> int:
    return max(0, min(maximum, int(round(value))))


def assess_observation_quality(
    *,
    market_available: bool,
    captured_at: str | None,
    kickoff: str | None,
    market_source: str | None = None,
    market_bookmaker_count: int | None = None,
    market_last_update: str | None = None,
    market_match_confidence: float | None = None,
    public_last_update: str | None = None,
) -> ObservationQuality:
    """Score provenance/recency of a historical observation, never prediction quality.

    The score is deliberately conservative. Unknown metadata earns no points and is
    surfaced as missing evidence instead of being guessed from probabilities.
    """
    score = 0
    known_weight = 0
    reasons: list[str] = []
    missing: list[str] = []

    # 20: real bookmaker baseline is the non-negotiable foundation.
    known_weight += 20
    if market_available:
        score += 20
        reasons.append("Verifierad bookmakerbas finns")
    else:
        missing.append("verifierad bookmakerbas")

    # 15: explicit market provenance.
    known_weight += 15
    if market_source and str(market_source).strip():
        score += 15
        reasons.append(f"Marknadskälla: {str(market_source).strip()}")
    else:
        missing.append("marknadskälla")

    # 15: breadth. 1 source is useful, 3+ is much stronger.
    known_weight += 15
    if market_bookmaker_count is None:
        missing.append("antal bookmakers")
    else:
        count = max(0, int(market_bookmaker_count))
        if count >= 5:
            pts = 15
        elif count >= 3:
            pts = 13
        elif count == 2:
            pts = 10
        elif count == 1:
            pts = 6
        else:
            pts = 0
        score += pts
        reasons.append(f"{count} bookmaker{'s' if count != 1 else ''} i marknadsbasen")

    # 15: odds freshness at capture time.
    known_weight += 15
    captured = _parse_dt(captured_at)
    market_update = _parse_dt(market_last_update)
    if captured is None or market_update is None:
        missing.append("oddsens färskhet")
    else:
        age_minutes = max(0.0, (captured - market_update).total_seconds() / 60.0)
        if age_minutes <= 15:
            pts = 15
        elif age_minutes <= 60:
            pts = 13
        elif age_minutes <= 240:
            pts = 10
        elif age_minutes <= 720:
            pts = 6
        elif age_minutes <= 1440:
            pts = 3
        else:
            pts = 1
        score += pts
        reasons.append(f"Odds {int(round(age_minutes))} min gamla vid sparning")

    # 10: exact match confidence/provenance. 1.0 = exact/verified mapping.
    known_weight += 10
    if market_match_confidence is None:
        missing.append("matchningssäkerhet för odds")
    else:
        conf = max(0.0, min(1.0, float(market_match_confidence)))
        score += _bounded_points(conf * 10, 10)
        reasons.append(f"Oddsmatchning {int(round(conf * 100))} %")

    # 15: proximity to kickoff. Capturing after kickoff is not rewarded.
    known_weight += 15
    kickoff_dt = _parse_dt(kickoff)
    if captured is None or kickoff_dt is None:
        missing.append("tid till avspark")
    else:
        hours = (kickoff_dt - captured).total_seconds() / 3600.0
        if hours < 0:
            pts = 0
            reasons.append("Prognosen sparades efter avspark")
        elif hours <= 1:
            pts = 15
            reasons.append("Prognosen sparades inom 1 h före avspark")
        elif hours <= 3:
            pts = 13
            reasons.append("Prognosen sparades inom 3 h före avspark")
        elif hours <= 12:
            pts = 10
            reasons.append("Prognosen sparades inom 12 h före avspark")
        elif hours <= 24:
            pts = 7
            reasons.append("Prognosen sparades inom 24 h före avspark")
        elif hours <= 72:
            pts = 4
            reasons.append("Prognosen sparades inom 72 h före avspark")
        else:
            pts = 2
            reasons.append("Prognosen sparades mer än 72 h före avspark")
        score += pts

    # 10: public-streak freshness. Supported now, populated only when a source proves it.
    known_weight += 10
    public_update = _parse_dt(public_last_update)
    if captured is None or public_update is None:
        missing.append("streckens färskhet")
    else:
        age_minutes = max(0.0, (captured - public_update).total_seconds() / 60.0)
        if age_minutes <= 15:
            pts = 10
        elif age_minutes <= 60:
            pts = 9
        elif age_minutes <= 240:
            pts = 7
        elif age_minutes <= 720:
            pts = 4
        elif age_minutes <= 1440:
            pts = 2
        else:
            pts = 1
        score += pts
        reasons.append(f"Streck {int(round(age_minutes))} min gamla vid sparning")

    score = max(0, min(100, int(score)))
    evidence_coverage = int(round(100 * (known_weight - sum({
        "verifierad bookmakerbas": 20,
        "marknadskälla": 15,
        "antal bookmakers": 15,
        "oddsens färskhet": 15,
        "matchningssäkerhet för odds": 10,
        "tid till avspark": 15,
        "streckens färskhet": 10,
    }.get(item, 0) for item in missing)) / known_weight))

    if score >= 80:
        label = "HÖG"
    elif score >= 60:
        label = "MEDEL"
    elif score >= 40:
        label = "LÅG"
    else:
        label = "MYCKET LÅG"

    return ObservationQuality(score, label, evidence_coverage, tuple(reasons), tuple(missing))


def summarize_quality(items: Iterable[ObservationQuality]) -> dict[str, object]:
    rows = list(items)
    if not rows:
        return {"count": 0, "average_score": None, "high": 0, "medium": 0, "low": 0, "very_low": 0}
    return {
        "count": len(rows),
        "average_score": sum(x.score for x in rows) / len(rows),
        "high": sum(x.label == "HÖG" for x in rows),
        "medium": sum(x.label == "MEDEL" for x in rows),
        "low": sum(x.label == "LÅG" for x in rows),
        "very_low": sum(x.label == "MYCKET LÅG" for x in rows),
    }
