from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from budget_reallocation import reallocation_candidates
from core import SIGNS


@dataclass(frozen=True)
class SwapProposalSnapshot:
    """Exact budget reallocation shown when a coupon snapshot was captured.

    This is prospective provenance. Historical coupons without this object are
    deliberately left unknown; Streckverket must not reconstruct a proposal in
    hindsight because old snapshots did not preserve locks or the displayed
    recommendation.
    """

    rank: int
    donor_match_number: int
    donor_from: tuple[str, ...]
    donor_to: tuple[str, ...]
    recipient_match_number: int
    recipient_from: tuple[str, ...]
    recipient_to: tuple[str, ...]
    rows: int
    predicted_delta_coverage_pp: float
    predicted_relative_gain_pct: float


@dataclass(frozen=True)
class SwapBacktestResult:
    coupon_id: str
    captured_at: str
    proposal_rank: int
    donor_match_number: int
    recipient_match_number: int
    completed: bool
    original_hits: int | None
    swapped_hits: int | None
    hit_delta: int | None
    original_13: bool | None
    swapped_13: bool | None
    verdict: str
    predicted_delta_coverage_pp: float


def snapshot_reallocation_proposals(
    matches,
    system: dict,
    *,
    locks: Mapping[int, Sequence[str]] | None = None,
    limit: int = 5,
) -> tuple[SwapProposalSnapshot, ...]:
    if limit <= 0:
        return ()
    rows = reallocation_candidates(matches, system, locks=locks)[:limit]
    return tuple(
        SwapProposalSnapshot(
            rank=i,
            donor_match_number=int(row.donor_match_number),
            donor_from=tuple(row.donor_from),
            donor_to=tuple(row.donor_to),
            recipient_match_number=int(row.recipient_match_number),
            recipient_from=tuple(row.recipient_from),
            recipient_to=tuple(row.recipient_to),
            rows=int(row.rows),
            predicted_delta_coverage_pp=float(row.delta_coverage_pp),
            predicted_relative_gain_pct=float(row.relative_coverage_gain_pct),
        )
        for i, row in enumerate(rows, start=1)
    )


def _apply_by_match_number(coupon, proposal: SwapProposalSnapshot) -> tuple[tuple[str, ...], ...] | None:
    selections = [tuple(m.selected) for m in coupon.matches]
    index = {int(m.match_number): i for i, m in enumerate(coupon.matches)}
    di = index.get(int(proposal.donor_match_number))
    ri = index.get(int(proposal.recipient_match_number))
    if di is None or ri is None or di == ri:
        return None
    if tuple(selections[di]) != tuple(proposal.donor_from):
        return None
    if tuple(selections[ri]) != tuple(proposal.recipient_from):
        return None
    if not proposal.donor_to or not proposal.recipient_to:
        return None
    if any(s not in SIGNS for s in proposal.donor_to + proposal.recipient_to):
        return None
    # Exact-row invariant is rechecked at evaluation time so corrupt/imported
    # proposal metadata fails closed.
    if len(proposal.donor_from) * len(proposal.recipient_from) != len(proposal.donor_to) * len(proposal.recipient_to):
        return None
    selections[di] = tuple(proposal.donor_to)
    selections[ri] = tuple(proposal.recipient_to)
    return tuple(selections)


def evaluate_swap_proposal(coupon, proposal: SwapProposalSnapshot) -> SwapBacktestResult:
    complete = len(coupon.matches) == 13 and all(getattr(m, "result", None) in SIGNS for m in coupon.matches)
    if not complete:
        return SwapBacktestResult(
            coupon_id=str(coupon.coupon_id), captured_at=str(coupon.captured_at), proposal_rank=int(proposal.rank),
            donor_match_number=int(proposal.donor_match_number), recipient_match_number=int(proposal.recipient_match_number),
            completed=False, original_hits=None, swapped_hits=None, hit_delta=None,
            original_13=None, swapped_13=None, verdict="VÄNTAR PÅ FACIT",
            predicted_delta_coverage_pp=float(proposal.predicted_delta_coverage_pp),
        )

    swapped = _apply_by_match_number(coupon, proposal)
    if swapped is None:
        return SwapBacktestResult(
            coupon_id=str(coupon.coupon_id), captured_at=str(coupon.captured_at), proposal_rank=int(proposal.rank),
            donor_match_number=int(proposal.donor_match_number), recipient_match_number=int(proposal.recipient_match_number),
            completed=True, original_hits=None, swapped_hits=None, hit_delta=None,
            original_13=None, swapped_13=None, verdict="OGILTIG PROVENIENS",
            predicted_delta_coverage_pp=float(proposal.predicted_delta_coverage_pp),
        )

    original_hits = sum(1 for m in coupon.matches if m.result in m.selected)
    swapped_hits = sum(1 for m, sel in zip(coupon.matches, swapped) if m.result in sel)
    delta = swapped_hits - original_hits
    if delta > 0:
        verdict = "BÄTTRE UTFALLSTÄCKNING"
    elif delta < 0:
        verdict = "SÄMRE UTFALLSTÄCKNING"
    else:
        verdict = "OFÖRÄNDRAD UTFALLSTÄCKNING"
    return SwapBacktestResult(
        coupon_id=str(coupon.coupon_id), captured_at=str(coupon.captured_at), proposal_rank=int(proposal.rank),
        donor_match_number=int(proposal.donor_match_number), recipient_match_number=int(proposal.recipient_match_number),
        completed=True, original_hits=original_hits, swapped_hits=swapped_hits, hit_delta=delta,
        original_13=(original_hits == 13), swapped_13=(swapped_hits == 13), verdict=verdict,
        predicted_delta_coverage_pp=float(proposal.predicted_delta_coverage_pp),
    )


def swap_backtest_results(coupons: Iterable, *, primary_only: bool = False) -> list[SwapBacktestResult]:
    out: list[SwapBacktestResult] = []
    for coupon in coupons:
        proposals = tuple(getattr(coupon, "swap_proposals", ()) or ())
        if primary_only:
            proposals = tuple(p for p in proposals if int(getattr(p, "rank", 0)) == 1)
        for proposal in proposals:
            out.append(evaluate_swap_proposal(coupon, proposal))
    return out


def swap_backtest_summary(coupons: Iterable) -> dict[str, int | str]:
    coupons = list(coupons)
    prospective = [c for c in coupons if tuple(getattr(c, "swap_proposals", ()) or ())]
    legacy_without = len(coupons) - len(prospective)
    primary = swap_backtest_results(prospective, primary_only=True)
    completed = [r for r in primary if r.completed and r.hit_delta is not None]
    pending = sum(1 for r in primary if not r.completed)
    better = sum(1 for r in completed if r.hit_delta > 0)
    worse = sum(1 for r in completed if r.hit_delta < 0)
    same = sum(1 for r in completed if r.hit_delta == 0)
    rescued_13 = sum(1 for r in completed if r.original_13 is False and r.swapped_13 is True)
    lost_13 = sum(1 for r in completed if r.original_13 is True and r.swapped_13 is False)

    if len(completed) < 20:
        status = "FÖR LITE PROSPEKTIV HISTORIK"
    elif better > worse and rescued_13 >= lost_13:
        status = "VÄRT FORTSATT GRANSKNING"
    elif worse > better or lost_13 > rescued_13:
        status = "SVAG HISTORISK SIGNAL"
    else:
        status = "INGEN TYDLIG SKILLNAD"

    return {
        "prospective_coupons": len(prospective),
        "legacy_without_proposal": legacy_without,
        "completed_primary": len(completed),
        "pending_primary": pending,
        "better": better,
        "same": same,
        "worse": worse,
        "rescued_13": rescued_13,
        "lost_13": lost_13,
        "status": status,
    }
