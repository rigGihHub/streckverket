from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from market_timeline import MarketPoint

SIGNS = ("1", "X", "2")


@dataclass(frozen=True)
class MovementAssessment:
    match_number: int
    home: str
    away: str
    points: int
    strongest_outcome: str
    strongest_delta_pp: float
    magnitude_pp: float
    classification: str
    direction_text: str
    first_capture: str
    last_capture: str


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def classify_magnitude(max_abs_delta_pp: float) -> str:
    """Descriptive buckets only; these are not betting-signal thresholds."""
    value = abs(float(max_abs_delta_pp))
    if value < 1.0:
        return "STABIL"
    if value < 3.0:
        return "MÅTTLIG RÖRELSE"
    return "KRAFTIG RÖRELSE"


def assess_match_movement(series: Sequence[MarketPoint]) -> MovementAssessment | None:
    verified = [p for p in series if p.market_available]
    if len(verified) < 2:
        return None
    verified.sort(key=lambda p: _parse_utc(p.captured_at))
    first, last = verified[0], verified[-1]
    deltas = tuple((last.market[i] - first.market[i]) * 100.0 for i in range(3))
    idx = max(range(3), key=lambda i: abs(deltas[i]))
    strongest = float(deltas[idx])
    magnitude = max(abs(float(d)) for d in deltas)
    sign = SIGNS[idx]
    if strongest > 0:
        direction = f"Marknaden har flyttat mot {sign} ({strongest:+.1f} p.e.)"
    elif strongest < 0:
        direction = f"Marknaden har flyttat från {sign} ({strongest:+.1f} p.e.)"
    else:
        direction = "Ingen tydlig nettoförflyttning"
    return MovementAssessment(
        match_number=last.match_number,
        home=last.home,
        away=last.away,
        points=len(verified),
        strongest_outcome=sign,
        strongest_delta_pp=strongest,
        magnitude_pp=magnitude,
        classification=classify_magnitude(magnitude),
        direction_text=direction,
        first_capture=first.captured_at,
        last_capture=last.captured_at,
    )


def movement_assessments(points: Sequence[MarketPoint], *, coupon_key: str | None = None) -> list[MovementAssessment]:
    grouped: dict[tuple[str, int], list[MarketPoint]] = {}
    for p in points:
        if coupon_key is not None and p.coupon_key != coupon_key:
            continue
        grouped.setdefault((p.coupon_key, p.match_number), []).append(p)
    out: list[MovementAssessment] = []
    for series in grouped.values():
        assessment = assess_match_movement(series)
        if assessment is not None:
            out.append(assessment)
    return sorted(out, key=lambda x: x.match_number)


def movement_rows(points: Sequence[MarketPoint], *, coupon_key: str | None = None) -> list[dict[str, object]]:
    return [
        {
            "Nr": a.match_number,
            "Match": f"{a.home} – {a.away}",
            "Klass": a.classification,
            "Största rörelse": f"{a.strongest_outcome} {a.strongest_delta_pp:+.1f} p.e.",
            "Mätpunkter": a.points,
            "Tolkning": a.direction_text,
        }
        for a in movement_assessments(points, coupon_key=coupon_key)
    ]


def _same_match(row: dict, assessment: MovementAssessment) -> bool:
    return (
        int(row.get("match_number", 0) or 0) == assessment.match_number
        and str(row.get("home", "")).strip().casefold() == assessment.home.strip().casefold()
        and str(row.get("away", "")).strip().casefold() == assessment.away.strip().casefold()
    )


def supporter_timing_rows(
    points: Sequence[MarketPoint],
    supporter_history: Iterable[dict],
    *,
    coupon_key: str | None = None,
) -> list[dict[str, object]]:
    """Compare supporter capture timestamps with the first *observed* market move.

    This does not claim causality or predictive value. A move is considered observed only
    between two saved verified market points, so the exact time of the underlying market
    change remains unknown within that interval.
    """
    grouped: dict[tuple[str, int], list[MarketPoint]] = {}
    for p in points:
        if coupon_key is not None and p.coupon_key != coupon_key:
            continue
        if p.market_available:
            grouped.setdefault((p.coupon_key, p.match_number), []).append(p)

    assessments = {a.match_number: a for a in movement_assessments(points, coupon_key=coupon_key)}
    out: list[dict[str, object]] = []
    history = list(supporter_history)
    for (_, match_number), series in grouped.items():
        assessment = assessments.get(match_number)
        if assessment is None:
            continue
        series.sort(key=lambda p: _parse_utc(p.captured_at))
        # First interval where any outcome differs by >= 1 percentage point from the first point.
        base = series[0]
        observed_move_at: str | None = None
        for point in series[1:]:
            if max(abs((point.market[i] - base.market[i]) * 100.0) for i in range(3)) >= 1.0:
                observed_move_at = point.captured_at
                break
        if observed_move_at is None:
            continue
        move_dt = _parse_utc(observed_move_at)
        matching = [r for r in history if _same_match(r, assessment)]
        if not matching:
            continue
        for row in matching:
            captured = str(row.get("captured_at", "") or "")
            if not captured:
                continue
            pulse_dt = _parse_utc(captured)
            hours = (move_dt - pulse_dt).total_seconds() / 3600.0
            if hours > 0:
                relation = "FÖRE OBSERVERAD RÖRELSE"
            elif hours < 0:
                relation = "EFTER OBSERVERAD RÖRELSE"
            else:
                relation = "SAMMA TIDPUNKT"
            out.append({
                "Nr": match_number,
                "Match": f"{assessment.home} – {assessment.away}",
                "Lag": str(row.get("team", "") or ""),
                "Supporter Pulse": captured,
                "Första observerade rörelse": observed_move_at,
                "Tidsrelation": relation,
                "Skillnad timmar": round(hours, 1),
                "Varning": "Tidsrelation, inte bevis på orsak eller edge",
            })
    return sorted(out, key=lambda r: (int(r["Nr"]), str(r["Supporter Pulse"])))
