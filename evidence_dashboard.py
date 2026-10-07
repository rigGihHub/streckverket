from __future__ import annotations

from typing import Sequence


REQUIRED_OBSERVATIONS = 30
REQUIRED_MATCHES = 20


def _key(row: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(row.get('Signaltyp') or 'Okänd signaltyp'),
        str(row.get('Liga') or 'Okänd liga'),
        str(row.get('Källa') or 'Okänd källa'),
    )


def _unknown_provenance(key: tuple[str, str, str]) -> bool:
    return any(value.startswith('Okänd ') for value in key)


def evidence_dashboard_rows(
    timing_rows: Sequence[dict[str, object]],
    directional_rows: Sequence[dict[str, object]],
    *,
    min_observations: int = REQUIRED_OBSERVATIONS,
    min_unique_matches: int = REQUIRED_MATCHES,
) -> list[dict[str, object]]:
    """Merge timing and directional evidence into one conservative review queue.

    Readiness is driven by data sufficiency and provenance, never by a high same-direction rate.
    The dashboard is therefore a prioritisation aid for analysis, not a signal-ranking engine.
    """
    direction_by_key = {_key(row): row for row in directional_rows}
    timing_by_key = {_key(row): row for row in timing_rows}
    all_keys = set(timing_by_key) | set(direction_by_key)

    out: list[dict[str, object]] = []
    for key in all_keys:
        timing = timing_by_key.get(key, {})
        direction = direction_by_key.get(key, {})
        observations = int(timing.get('Observationer') or 0)
        matches = int(timing.get('Unika matcher') or 0)
        directional_observations = int(direction.get('Riktningsobservationer') or 0)
        timing_ready = observations >= int(min_observations) and matches >= int(min_unique_matches)
        direction_ready = (
            directional_observations >= int(min_observations)
            and int(direction.get('Unika matcher') or 0) >= int(min_unique_matches)
        )
        provenance_gap = _unknown_provenance(key)

        missing_obs = max(0, int(min_observations) - observations)
        missing_matches = max(0, int(min_unique_matches) - matches)
        if provenance_gap:
            status = 'FIXA PROVENIENS'
            priority = 'DATAKVALITET'
            next_step = 'Komplettera liga/källa innan segmentet används för slutsatser.'
            rank = 1
        elif timing_ready and direction_ready:
            status = 'GRANSKA NU'
            priority = 'HÖG'
            next_step = 'Granska tidsmönster och riktningssamstämmighet. Ingen edge får påstås.'
            rank = 0
        elif timing_ready:
            status = 'GRANSKA TIDSMÖNSTER'
            priority = 'MEDEL'
            next_step = 'Tidsunderlaget räcker för granskning; samla mer användbar riktningsdata.'
            rank = 2
        else:
            status = 'SAMLA MER DATA'
            priority = 'VÄNTA'
            parts = []
            if missing_obs:
                parts.append(f'{missing_obs} fler observationer')
            if missing_matches:
                parts.append(f'{missing_matches} fler unika matcher')
            next_step = 'Behöver ' + ' och '.join(parts) + ' före granskning.' if parts else 'Samla mer verifierad historik.'
            rank = 3

        same_direction = direction.get('Andel samma riktning')
        out.append({
            'Prioritet': priority,
            'Status': status,
            'Signaltyp': key[0],
            'Liga': key[1],
            'Källa': key[2],
            'Observationer': observations,
            'Unika matcher': matches,
            'Säkert före': int(timing.get('Säkert före') or 0),
            'Osäker ordning': int(timing.get('Osäker ordning') or 0),
            'Riktningsobservationer': directional_observations,
            'Samma riktning %': same_direction,
            'Saknar observationer': missing_obs,
            'Saknar matcher': missing_matches,
            'Nästa steg': next_step,
            'Edge tillåten': False,
            '_rank': rank,
        })

    return sorted(
        out,
        key=lambda r: (
            int(r['_rank']),
            -int(r['Observationer']),
            str(r['Signaltyp']),
            str(r['Liga']),
            str(r['Källa']),
        ),
    )


def evidence_dashboard_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        'segments': len(rows),
        'review_now': sum(r.get('Status') == 'GRANSKA NU' for r in rows),
        'timing_review': sum(r.get('Status') == 'GRANSKA TIDSMÖNSTER' for r in rows),
        'provenance_gaps': sum(r.get('Status') == 'FIXA PROVENIENS' for r in rows),
        'collect_more': sum(r.get('Status') == 'SAMLA MER DATA' for r in rows),
        'edge_claim_allowed': False,
    }


def public_dashboard_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Strip internal sorting helpers before UI/export."""
    return [{k: v for k, v in row.items() if not k.startswith('_')} for row in rows]
