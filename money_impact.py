from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from budget_workshop import optimize_for_budget


@dataclass(frozen=True)
class SelectionChange:
    match_number: int
    home: str
    away: str
    before: tuple[str, ...]
    after: tuple[str, ...]

    @property
    def added(self) -> tuple[str, ...]:
        return tuple(s for s in self.after if s not in self.before)

    @property
    def removed(self) -> tuple[str, ...]:
        return tuple(s for s in self.before if s not in self.after)


@dataclass(frozen=True)
class SpendingOption:
    requested_extra: int
    budget_after: int
    rows_before: int
    rows_after: int
    cost_before: float
    cost_after: float
    actual_extra_cost: float
    coverage_before: float
    coverage_after: float
    coverage_gain_pp: float
    gain_per_kr: float
    changes: tuple[SelectionChange, ...]

    @property
    def useful(self) -> bool:
        return self.actual_extra_cost > 0 and self.coverage_gain_pp > 1e-12


def _changes(matches, before, after) -> tuple[SelectionChange, ...]:
    out = []
    for match, old, new in zip(matches, before, after):
        old_t, new_t = tuple(old), tuple(new)
        if old_t != new_t:
            out.append(SelectionChange(match.number, match.home, match.away, old_t, new_t))
    return tuple(out)


def spending_options(
    matches,
    base_budget: int,
    increments: Iterable[int] = (10, 20, 50),
    strategy: str = "MAX 13",
    locks=None,
    row_price: float = 1.0,
) -> list[SpendingOption]:
    """Compare the globally optimal system at base budget with higher budgets.

    The optimizer is allowed to rebuild the system. That matters because a better use of
    extra money may be to move guards between matches, not simply append one sign.
    """
    base_budget = int(base_budget)
    base = optimize_for_budget(matches, base_budget, strategy, locks, row_price)
    options: list[SpendingOption] = []

    for inc in sorted(set(int(x) for x in increments if int(x) > 0)):
        target_budget = base_budget + inc
        nxt = optimize_for_budget(matches, target_budget, strategy, locks, row_price)
        actual_extra = float(nxt["cost"] - base["cost"])
        gain_pp = float((nxt["coverage"] - base["coverage"]) * 100)
        options.append(
            SpendingOption(
                requested_extra=inc,
                budget_after=target_budget,
                rows_before=int(base["rows"]),
                rows_after=int(nxt["rows"]),
                cost_before=float(base["cost"]),
                cost_after=float(nxt["cost"]),
                actual_extra_cost=actual_extra,
                coverage_before=float(base["coverage"]),
                coverage_after=float(nxt["coverage"]),
                coverage_gain_pp=gain_pp,
                gain_per_kr=(gain_pp / actual_extra) if actual_extra > 0 else 0.0,
                changes=_changes(matches, base["selections"], nxt["selections"]),
            )
        )
    return options


def best_spending_option(options: Iterable[SpendingOption]) -> SpendingOption | None:
    useful = [o for o in options if o.useful]
    if not useful:
        return None
    return max(useful, key=lambda o: (o.gain_per_kr, o.coverage_gain_pp, -o.actual_extra_cost))


def plain_change(change: SelectionChange) -> str:
    before = "".join(change.before)
    after = "".join(change.after)
    if change.added and not change.removed:
        added = "/".join(change.added)
        return f"Match {change.match_number}: lägg till {added} ({before} → {after})"
    if change.removed and not change.added:
        removed = "/".join(change.removed)
        return f"Match {change.match_number}: ta bort {removed} ({before} → {after})"
    return f"Match {change.match_number}: ändra {before} → {after}"


def explain_option(option: SpendingOption) -> str:
    if option.actual_extra_cost <= 0:
        return (
            f"En budgetökning på {option.requested_extra} kr räcker inte till ett bättre system "
            "med nuvarande radstruktur. Pengarna behöver alltså inte användas bara för att budgeten finns."
        )
    if option.coverage_gain_pp <= 1e-12:
        return (
            f"Det går att använda cirka {option.actual_extra_cost:.0f} kr extra, men modellen hittar "
            "ingen mätbar förbättring av 13-rättstäckningen."
        )
    if not option.changes:
        return (
            f"Cirka {option.actual_extra_cost:.0f} kr extra höjer modellens beräknade 13-rättstäckning "
            f"med {option.coverage_gain_pp:.3f} procentenheter."
        )
    first = plain_change(option.changes[0])
    extra_changes = len(option.changes) - 1
    suffix = f" och {extra_changes} ytterligare systemändring{'ar' if extra_changes != 1 else ''}" if extra_changes else ""
    return (
        f"För cirka {option.actual_extra_cost:.0f} kr extra får du +{option.coverage_gain_pp:.3f} "
        f"procentenheter beräknad 13-rättstäckning. Viktigaste ändringen: {first}{suffix}."
    )
