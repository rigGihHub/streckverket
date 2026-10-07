from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Sequence

from core import MatchInput, SIGNS


@dataclass(frozen=True)
class GuardUpgrade:
    match_number: int
    home: str
    away: str
    from_selection: tuple[str, ...]
    to_selection: tuple[str, ...]
    added_sign: str
    added_sign_probability: float
    added_sign_public_share: float
    base_rows: int
    new_rows: int
    extra_rows: int
    extra_cost: float
    base_coverage: float
    new_coverage: float
    delta_coverage_pp: float
    coverage_pp_per_100_extra_rows: float


def _selection_coverage(match: MatchInput, selection: Sequence[str]) -> float:
    return sum(float(match.model[SIGNS.index(sign)]) for sign in selection)


def _system_coverage(matches: Sequence[MatchInput], selections: Sequence[Sequence[str]]) -> float:
    return prod(_selection_coverage(match, selection) for match, selection in zip(matches, selections))


def guard_upgrade_candidates(
    matches: Sequence[MatchInput],
    system: dict,
    *,
    row_price: float | None = None,
) -> list[GuardUpgrade]:
    """Rank local one-sign guard upgrades by model coverage gained per extra row.

    This is deliberately a local diagnostic. It does not estimate payout, expected profit,
    or tell the user to increase stake. Full-coupon coverage inherits the optimizer's
    independence assumption for match outcomes.
    """
    selections = [tuple(sel) for sel in system.get("selections", ())]
    if len(matches) != len(selections) or not matches:
        return []

    base_rows = int(system.get("rows") or prod(len(sel) for sel in selections))
    if base_rows < 1:
        return []
    price = float(row_price if row_price is not None else system.get("row_price", 1.0))
    base_coverage = float(system.get("coverage") or _system_coverage(matches, selections))
    candidates: list[GuardUpgrade] = []

    for idx, (match, current) in enumerate(zip(matches, selections)):
        if len(current) >= 3 or len(current) < 1:
            continue
        current_cov = _selection_coverage(match, current)
        if current_cov <= 0:
            continue

        omitted = [sign for sign in SIGNS if sign not in current]
        for added_sign in omitted:
            new_selection = tuple(sign for sign in SIGNS if sign in set(current) | {added_sign})
            new_rows_exact = base_rows * len(new_selection) / len(current)
            new_rows = int(round(new_rows_exact))
            extra_rows = new_rows - base_rows
            if extra_rows <= 0:
                continue

            sign_idx = SIGNS.index(added_sign)
            added_p = float(match.model[sign_idx])
            new_match_cov = current_cov + added_p
            new_coverage = base_coverage * (new_match_cov / current_cov)
            delta_pp = (new_coverage - base_coverage) * 100.0
            efficiency = delta_pp / extra_rows * 100.0

            candidates.append(GuardUpgrade(
                match_number=int(match.number),
                home=str(match.home), away=str(match.away),
                from_selection=current, to_selection=new_selection,
                added_sign=added_sign,
                added_sign_probability=added_p,
                added_sign_public_share=float(match.public[sign_idx]),
                base_rows=base_rows, new_rows=new_rows, extra_rows=extra_rows,
                extra_cost=extra_rows * price,
                base_coverage=base_coverage, new_coverage=new_coverage,
                delta_coverage_pp=delta_pp,
                coverage_pp_per_100_extra_rows=efficiency,
            ))

    return sorted(
        candidates,
        key=lambda x: (-x.coverage_pp_per_100_extra_rows, -x.delta_coverage_pp, x.extra_rows, x.match_number, x.added_sign),
    )


def best_guard_upgrade(matches: Sequence[MatchInput], system: dict) -> GuardUpgrade | None:
    candidates = guard_upgrade_candidates(matches, system)
    return candidates[0] if candidates else None
