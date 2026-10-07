from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Sequence


SIGNS = ('1', 'X', '2')


def _center(values: Sequence[float]) -> tuple[float, float, float] | None:
    if len(values) != 3:
        return None
    xs = tuple(float(x) for x in values)
    mean = sum(xs) / 3.0
    return tuple(x - mean for x in xs)


def signal_direction(impact: Sequence[float]) -> dict[str, object] | None:
    """Describe direction only from the verified EvidenceSignal impact vector.

    Category names are deliberately ignored. Centering is valid because adding the same log-weight
    to 1/X/2 has no effect after probability normalization.
    """
    centered = _center(impact)
    if centered is None:
        return None
    magnitude = sqrt(sum(x * x for x in centered))
    if magnitude <= 1e-9:
        return None
    idx = max(range(3), key=lambda i: abs(centered[i]))
    direction = 'UPP' if centered[idx] > 0 else 'NED'
    return {
        'outcome': SIGNS[idx],
        'direction': direction,
        'label': f"{SIGNS[idx]} {'↑' if direction == 'UPP' else '↓'}",
        'vector': centered,
        'magnitude': magnitude,
    }


def classify_directional_response(signal_impact: Sequence[float], market_delta_pp: Sequence[float]) -> dict[str, object]:
    signal = signal_direction(signal_impact)
    market = _center(market_delta_pp)
    if signal is None or market is None:
        return {'status': 'RIKTNING OKÄND', 'alignment': None, 'expected': None}
    market_mag = sqrt(sum(x * x for x in market))
    if market_mag <= 1e-9:
        return {'status': 'INGEN MÄTBAR MARKNADSRÖRELSE', 'alignment': None, 'expected': signal['label']}
    sv = signal['vector']
    dot = sum(float(a) * float(b) for a, b in zip(sv, market))
    denom = float(signal['magnitude']) * market_mag
    alignment = dot / denom if denom > 0 else 0.0
    # Avoid turning tiny geometric differences into categorical claims.
    if alignment >= 0.20:
        status = 'SAMMA RIKTNING'
    elif alignment <= -0.20:
        status = 'MOTSATT RIKTNING'
    else:
        status = 'BLANDAD/OKLAR RIKTNING'
    return {'status': status, 'alignment': alignment, 'expected': signal['label']}


def signal_market_response_rows(timing_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Attach directional response only when timing is safely ordered and direction has provenance."""
    out: list[dict[str, object]] = []
    for row in timing_rows:
        if row.get('Tidsrelation') != 'SÄKERT FÖRE RÖRELSEINTERVALL':
            continue
        impact = row.get('Signal-impact 1/X/2') or ()
        delta = row.get('Marknadsdelta 1/X/2') or ()
        result = classify_directional_response(impact, delta)
        if result['status'] == 'RIKTNING OKÄND':
            # Keep auditable unknowns visible, but they are not usable directional evidence.
            usable = False
        else:
            usable = result['status'] != 'INGEN MÄTBAR MARKNADSRÖRELSE'
        enriched = dict(row)
        enriched.update({
            'Förväntad riktning': result.get('expected') or 'OKÄND',
            'Marknadsrespons': result['status'],
            'Riktningssamstämmighet': (round(float(result['alignment']), 3) if result.get('alignment') is not None else None),
            'Riktningsdata användbar': usable,
        })
        out.append(enriched)
    return out


def directional_evidence_rows(
    response_rows: Sequence[dict[str, object]], *, min_observations: int = 30, min_unique_matches: int = 20
) -> list[dict[str, object]]:
    """Aggregate only homogeneous category/league/source segments with known direction.

    This is descriptive evidence. Even a high same-direction rate cannot establish causality or edge.
    """
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in response_rows:
        if not bool(row.get('Riktningsdata användbar')):
            continue
        key = (
            str(row.get('Kategori') or 'Okänd signaltyp'),
            str(row.get('Liga') or 'Okänd liga'),
            str(row.get('Källa') or 'Okänd källa'),
        )
        groups[key].append(row)

    out: list[dict[str, object]] = []
    for (category, league, source), rows in groups.items():
        total = len(rows)
        unique_matches = len({(str(r.get('Kupong') or ''), int(r.get('Nr') or 0)) for r in rows})
        same = sum(r.get('Marknadsrespons') == 'SAMMA RIKTNING' for r in rows)
        opposite = sum(r.get('Marknadsrespons') == 'MOTSATT RIKTNING' for r in rows)
        mixed = sum(r.get('Marknadsrespons') == 'BLANDAD/OKLAR RIKTNING' for r in rows)
        reviewable = total >= int(min_observations) and unique_matches >= int(min_unique_matches)
        out.append({
            'Signaltyp': category,
            'Liga': league,
            'Källa': source,
            'Riktningsobservationer': total,
            'Unika matcher': unique_matches,
            'Samma riktning': same,
            'Motsatt riktning': opposite,
            'Blandad/oklar': mixed,
            'Andel samma riktning': round(100.0 * same / total, 1) if total else None,
            'Status': 'TILLRÄCKLIGT FÖR GRANSKNING' if reviewable else 'FÖR LITE DATA',
            'Edge tillåten': False,
            'Orsakspåstående tillåtet': False,
        })
    return sorted(out, key=lambda r: (-int(r['Riktningsobservationer']), str(r['Signaltyp']), str(r['Liga']), str(r['Källa'])))


def directional_evidence_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        'segments': len(rows),
        'reviewable_segments': sum(r.get('Status') == 'TILLRÄCKLIGT FÖR GRANSKNING' for r in rows),
        'edge_claim_allowed': False,
        'causal_claim_allowed': False,
    }
