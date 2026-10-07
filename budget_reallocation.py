from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import prod
from typing import Mapping, Sequence

from core import MatchInput, SIGNS


@dataclass(frozen=True)
class BudgetReallocation:
    donor_match_number: int
    donor_home: str
    donor_away: str
    donor_from: tuple[str, ...]
    donor_to: tuple[str, ...]
    removed_signs: tuple[str, ...]
    recipient_match_number: int
    recipient_home: str
    recipient_away: str
    recipient_from: tuple[str, ...]
    recipient_to: tuple[str, ...]
    added_signs: tuple[str, ...]
    rows: int
    cost: float
    base_coverage: float
    new_coverage: float
    delta_coverage_pp: float
    relative_coverage_gain_pct: float
    donor_coverage_change_pp: float
    recipient_coverage_change_pp: float


def _selection_coverage(match: MatchInput, selection: Sequence[str]) -> float:
    return sum(float(match.model[SIGNS.index(sign)]) for sign in selection)


def _system_coverage(matches: Sequence[MatchInput], selections: Sequence[Sequence[str]]) -> float:
    return prod(_selection_coverage(match, selection) for match, selection in zip(matches, selections))


def _ordered_subset(selection: Sequence[str], size: int) -> list[tuple[str, ...]]:
    selected = set(selection)
    return [tuple(sign for sign in SIGNS if sign in combo) for combo in combinations([s for s in SIGNS if s in selected], size)]


def _ordered_superset(selection: Sequence[str], size: int) -> list[tuple[str, ...]]:
    current = set(selection)
    return [
        tuple(sign for sign in SIGNS if sign in combo)
        for combo in combinations(SIGNS, size)
        if current.issubset(set(combo))
    ]


def reallocation_candidates(
    matches: Sequence[MatchInput],
    system: dict,
    *,
    locks: Mapping[int, Sequence[str]] | None = None,
    row_price: float | None = None,
) -> list[BudgetReallocation]:
    """Find exact-row reallocations that improve model coverage.

    One match gives up guard coverage while another receives guard coverage. The
    total row multiplier must remain exactly unchanged. User-locked matches are
    never modified. This is a diagnostic over the already-produced system; it
    does not estimate payout, ROI or expected profit.
    """
    selections = [tuple(sel) for sel in system.get("selections", ())]
    if not matches or len(matches) != len(selections):
        return []
    if any(len(sel) not in (1, 2, 3) or not sel for sel in selections):
        return []

    locks = locks or {}
    base_rows = int(system.get("rows") or prod(len(sel) for sel in selections))
    if base_rows < 1:
        return []
    price = float(row_price if row_price is not None else system.get("row_price", 1.0))
    base_coverage = _system_coverage(matches, selections)
    if base_coverage <= 0:
        return []

    out: list[BudgetReallocation] = []
    for donor_idx, (donor_match, donor_sel) in enumerate(zip(matches, selections)):
        if donor_match.number in locks or len(donor_sel) <= 1:
            continue
        donor_cov = _selection_coverage(donor_match, donor_sel)
        if donor_cov <= 0:
            continue

        for recipient_idx, (recipient_match, recipient_sel) in enumerate(zip(matches, selections)):
            if recipient_idx == donor_idx or recipient_match.number in locks or len(recipient_sel) >= 3:
                continue
            recipient_cov = _selection_coverage(recipient_match, recipient_sel)
            if recipient_cov <= 0:
                continue

            for donor_size in range(1, len(donor_sel)):
                for recipient_size in range(len(recipient_sel) + 1, 4):
                    # Exact same total row multiplier: no hidden budget increase/decrease.
                    if donor_size * recipient_size != len(donor_sel) * len(recipient_sel):
                        continue
                    for donor_to in _ordered_subset(donor_sel, donor_size):
                        donor_new_cov = _selection_coverage(donor_match, donor_to)
                        if donor_new_cov <= 0:
                            continue
                        for recipient_to in _ordered_superset(recipient_sel, recipient_size):
                            recipient_new_cov = _selection_coverage(recipient_match, recipient_to)
                            new_coverage = base_coverage * (donor_new_cov / donor_cov) * (recipient_new_cov / recipient_cov)
                            delta_pp = (new_coverage - base_coverage) * 100.0
                            if delta_pp <= 1e-12:
                                continue
                            removed = tuple(sign for sign in donor_sel if sign not in donor_to)
                            added = tuple(sign for sign in recipient_to if sign not in recipient_sel)
                            relative = ((new_coverage / base_coverage) - 1.0) * 100.0
                            out.append(BudgetReallocation(
                                donor_match_number=int(donor_match.number),
                                donor_home=str(donor_match.home), donor_away=str(donor_match.away),
                                donor_from=donor_sel, donor_to=donor_to, removed_signs=removed,
                                recipient_match_number=int(recipient_match.number),
                                recipient_home=str(recipient_match.home), recipient_away=str(recipient_match.away),
                                recipient_from=recipient_sel, recipient_to=recipient_to, added_signs=added,
                                rows=base_rows, cost=base_rows * price,
                                base_coverage=base_coverage, new_coverage=new_coverage,
                                delta_coverage_pp=delta_pp, relative_coverage_gain_pct=relative,
                                donor_coverage_change_pp=(donor_new_cov - donor_cov) * 100.0,
                                recipient_coverage_change_pp=(recipient_new_cov - recipient_cov) * 100.0,
                            ))

    return sorted(
        out,
        key=lambda x: (-x.delta_coverage_pp, -x.relative_coverage_gain_pct, x.donor_match_number, x.recipient_match_number, x.removed_signs, x.added_signs),
    )


def best_reallocation(matches: Sequence[MatchInput], system: dict, *, locks=None) -> BudgetReallocation | None:
    rows = reallocation_candidates(matches, system, locks=locks)
    return rows[0] if rows else None
