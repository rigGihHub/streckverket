from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from market_timeline import MarketPoint
from signal_timeline import SignalPoint


@dataclass(frozen=True)
class MovementInterval:
    match_number: int
    home: str
    away: str
    interval_start: str
    interval_end: str
    threshold_pp: float
    strongest_outcome: str
    strongest_delta_pp: float
    delta_1x2_pp: tuple[float, float, float]


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def first_observed_movement_interval(
    series: Sequence[MarketPoint], *, threshold_pp: float = 1.0
) -> MovementInterval | None:
    """Return the first interval in which movement from the initial verified point crosses threshold.

    The actual move happened at an unknown time after interval_start and no later than interval_end.
    We deliberately preserve that uncertainty instead of assigning the move to interval_end.
    """
    verified = sorted(
        (p for p in series if p.market_available),
        key=lambda p: _parse_utc(p.captured_at),
    )
    if len(verified) < 2:
        return None
    base = verified[0]
    previous = base
    for point in verified[1:]:
        deltas = tuple((point.market[i] - base.market[i]) * 100.0 for i in range(3))
        magnitude = max(abs(float(d)) for d in deltas)
        if magnitude >= float(threshold_pp):
            idx = max(range(3), key=lambda i: abs(deltas[i]))
            return MovementInterval(
                match_number=point.match_number,
                home=point.home,
                away=point.away,
                interval_start=previous.captured_at,
                interval_end=point.captured_at,
                threshold_pp=float(threshold_pp),
                strongest_outcome=('1', 'X', '2')[idx],
                strongest_delta_pp=float(deltas[idx]),
                delta_1x2_pp=tuple(float(d) for d in deltas),
            )
        previous = point
    return None


def _eligible_fact(point: SignalPoint) -> bool:
    return (
        point.signal_type == 'verified_fact'
        and point.verification_status == 'VERIFIERAD MODELLSIGNAL'
        and bool(point.model_usable)
        and bool(point.verified_at)
    )


def fact_market_timing_rows(
    market_points: Sequence[MarketPoint],
    signal_points: Sequence[SignalPoint],
    *,
    coupon_key: str | None = None,
    threshold_pp: float = 1.0,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], list[MarketPoint]] = {}
    for point in market_points:
        if coupon_key is not None and point.coupon_key != coupon_key:
            continue
        if point.market_available:
            grouped.setdefault((point.coupon_key, point.match_number), []).append(point)

    intervals: dict[tuple[str, int], MovementInterval] = {}
    for key, series in grouped.items():
        interval = first_observed_movement_interval(series, threshold_pp=threshold_pp)
        if interval is not None:
            intervals[key] = interval

    out: list[dict[str, object]] = []
    for fact in signal_points:
        if coupon_key is not None and fact.coupon_key != coupon_key:
            continue
        if not _eligible_fact(fact):
            continue
        interval = intervals.get((fact.coupon_key, fact.match_number))
        if interval is None:
            continue
        verified_dt = _parse_utc(str(fact.verified_at))
        start_dt = _parse_utc(interval.interval_start)
        end_dt = _parse_utc(interval.interval_end)

        if verified_dt <= start_dt:
            relation = 'SÄKERT FÖRE RÖRELSEINTERVALL'
            min_hours = (start_dt - verified_dt).total_seconds() / 3600.0
            max_hours = (end_dt - verified_dt).total_seconds() / 3600.0
            timing_note = f'Faktumet var verifierat minst {min_hours:.1f} h före den tidigast möjliga tröskelpassagen.'
        elif verified_dt <= end_dt:
            relation = 'INOM OSÄKERT RÖRELSEINTERVALL'
            min_hours = None
            max_hours = None
            timing_note = 'Ordningen går inte att avgöra med de sparade marknadspunkterna.'
        else:
            relation = 'EFTER OBSERVERAD RÖRELSE'
            min_hours = -((verified_dt - end_dt).total_seconds() / 3600.0)
            max_hours = -((verified_dt - start_dt).total_seconds() / 3600.0)
            timing_note = 'Faktumet verifierades först efter att tröskelpassagen redan hade observerats.'

        out.append({
            'Kupong': fact.coupon_key,
            'Nr': fact.match_number,
            'Match': f'{fact.home} – {fact.away}',
            'Faktum': fact.subject,
            'Kategori': str(fact.payload.get('category') or ''),
            'Liga': str(fact.payload.get('competition') or 'Okänd liga'),
            'Källa': fact.source,
            'Verifierat': str(fact.verified_at),
            'Rörelseintervall start': interval.interval_start,
            'Rörelseintervall slut': interval.interval_end,
            'Marknadsrörelse': f'{interval.strongest_outcome} {interval.strongest_delta_pp:+.1f} p.e.',
            'Marknadsdelta 1/X/2': tuple(round(float(x), 3) for x in interval.delta_1x2_pp),
            'Signal-impact 1/X/2': tuple(float(x) for x in (fact.payload.get('impact_1x2') or ())),
            'Signalriktning proveniens': str(fact.payload.get('direction_basis') or ''),
            'Tidsrelation': relation,
            'Minsta försprång h': (round(min_hours, 1) if min_hours is not None and min_hours >= 0 else None),
            'Notering': timing_note,
        })
    return sorted(out, key=lambda r: (int(r['Nr']), str(r['Verifierat']), str(r['Faktum'])))


def timing_evidence_summary(rows: Sequence[dict[str, object]], *, min_observations: int = 30) -> dict[str, object]:
    total = len(rows)
    before = sum(1 for r in rows if r.get('Tidsrelation') == 'SÄKERT FÖRE RÖRELSEINTERVALL')
    ambiguous = sum(1 for r in rows if r.get('Tidsrelation') == 'INOM OSÄKERT RÖRELSEINTERVALL')
    after = sum(1 for r in rows if r.get('Tidsrelation') == 'EFTER OBSERVERAD RÖRELSE')
    usable_order = before + after
    if total < int(min_observations):
        status = 'FÖR LITE DATA'
    else:
        status = 'TILLRÄCKLIGT FÖR GRANSKNING'
    return {
        'observations': total,
        'definitely_before': before,
        'ambiguous': ambiguous,
        'after': after,
        'ordered_observations': usable_order,
        'before_rate_ordered': (before / usable_order if usable_order else None),
        'minimum_for_review': int(min_observations),
        'status': status,
        'edge_claim_allowed': False,
    }
