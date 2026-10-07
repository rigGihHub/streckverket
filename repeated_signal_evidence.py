from __future__ import annotations

from collections import defaultdict
from typing import Sequence


def _segment_key(row: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(row.get('Kategori') or 'Okänd signaltyp'),
        str(row.get('Liga') or 'Okänd liga'),
        str(row.get('Källa') or 'Okänd källa'),
    )


def repeated_signal_evidence_rows(
    timing_rows: Sequence[dict[str, object]],
    *,
    min_observations: int = 30,
    min_unique_matches: int = 20,
) -> list[dict[str, object]]:
    """Aggregate fact→market timing only inside homogeneous signal/league/source segments.

    Multiple facts from the same coupon+match may be useful audit records, but cannot alone create
    repeated evidence. A segment therefore needs both enough observations and enough unique matches.
    Ambiguous timing is retained and never silently counted as 'before'.
    """
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in timing_rows:
        groups[_segment_key(row)].append(row)

    out: list[dict[str, object]] = []
    for (category, league, source), rows in groups.items():
        total = len(rows)
        unique_matches = len({(str(r.get('Kupong') or ''), int(r.get('Nr') or 0)) for r in rows})
        before = sum(r.get('Tidsrelation') == 'SÄKERT FÖRE RÖRELSEINTERVALL' for r in rows)
        ambiguous = sum(r.get('Tidsrelation') == 'INOM OSÄKERT RÖRELSEINTERVALL' for r in rows)
        after = sum(r.get('Tidsrelation') == 'EFTER OBSERVERAD RÖRELSE' for r in rows)
        ordered = before + after
        reviewable = total >= int(min_observations) and unique_matches >= int(min_unique_matches)
        status = 'TILLRÄCKLIGT FÖR GRANSKNING' if reviewable else 'FÖR LITE DATA'
        out.append({
            'Signaltyp': category,
            'Liga': league,
            'Källa': source,
            'Observationer': total,
            'Unika matcher': unique_matches,
            'Säkert före': before,
            'Osäker ordning': ambiguous,
            'Efter': after,
            'Andel före (avgörbar ordning)': (round(100.0 * before / ordered, 1) if ordered else None),
            'Status': status,
            'Min observationer': int(min_observations),
            'Min unika matcher': int(min_unique_matches),
            'Edge tillåten': False,
        })
    return sorted(out, key=lambda r: (-int(r['Observationer']), str(r['Signaltyp']), str(r['Liga']), str(r['Källa'])))


def repeated_signal_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    reviewable = [r for r in rows if r.get('Status') == 'TILLRÄCKLIGT FÖR GRANSKNING']
    return {
        'segments': len(rows),
        'reviewable_segments': len(reviewable),
        'insufficient_segments': len(rows) - len(reviewable),
        'edge_claim_allowed': False,
    }
