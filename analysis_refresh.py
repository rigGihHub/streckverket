"""Novice-safe refresh helpers for Streckverket.

The normal UI needs one obvious way to rerun the analysis without accidentally
switching to another coupon. These helpers keep coupon identity checks outside
Streamlit and make the behavior testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


def _norm_team(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def coupon_fixture_signature(coupon: Sequence[Any]) -> tuple[tuple[int, str, str], ...]:
    return tuple(
        (int(getattr(m, "number", i + 1)), _norm_team(getattr(m, "home", "")), _norm_team(getattr(m, "away", "")))
        for i, m in enumerate(coupon)
    )


def same_coupon_fixtures(left: Sequence[Any], right: Sequence[Any]) -> bool:
    """True only when all 13 numbered fixtures are the same.

    We deliberately do not compare odds/public/model values: those are exactly
    the fields a refresh is allowed to update.
    """
    return len(left) == 13 and len(right) == 13 and coupon_fixture_signature(left) == coupon_fixture_signature(right)


@dataclass(frozen=True)
class RefreshCouponChoice:
    coupon: list[Any]
    used_fresh_coupon: bool
    message: str


def choose_refresh_coupon(open_coupon: Sequence[Any], fetched_coupon: Sequence[Any] | None) -> RefreshCouponChoice:
    """Use freshly fetched coupon data only when fixture identity is safe.

    A demo coupon is not treated specially here. The caller can explicitly
    replace demo with a fetched real coupon before analysis if that is the
    intended user action. For an already opened real/CSV coupon, fixture safety
    takes precedence over freshness.
    """
    current = list(open_coupon)
    fetched = list(fetched_coupon or [])
    if same_coupon_fixtures(current, fetched):
        return RefreshCouponChoice(fetched, True, "Kupongens grunddata uppdaterades eftersom samma 13 matcher verifierades.")
    return RefreshCouponChoice(current, False, "Den öppna kupongen behölls; Streckverket byter aldrig matchuppsättning under en omanalys.")
