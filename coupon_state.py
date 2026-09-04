"""Centralized coupon/session-state transitions for Streckverket.

The Streamlit UI has several ways to replace or enrich a coupon. This module
keeps those transitions consistent and makes dependent analysis state stale in
one place instead of relying on every UI branch to remember cleanup.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, MutableMapping

from production_hardening import coupon_fingerprint


ANALYSIS_STATE_KEYS = (
    "one_click_result",
    "one_click_coupon_fingerprint",
    "one_click_duration_seconds",
)

COUPON_DEPENDENT_STATE_KEYS = ANALYSIS_STATE_KEYS + (
    "manual_coupon",
)


@dataclass(frozen=True)
class CouponStateChange:
    changed: bool
    previous_fingerprint: str | None
    current_fingerprint: str
    invalidated_keys: tuple[str, ...]


def _fingerprint_or_none(coupon: Iterable[Any] | None) -> str | None:
    if coupon is None:
        return None
    coupon_list = list(coupon)
    if not coupon_list:
        return None
    return coupon_fingerprint(coupon_list)


def set_coupon_state(
    state: MutableMapping[str, Any],
    coupon: Iterable[Any],
    *,
    data_mode: str,
    source_message: str,
    stale_notice: str | None = "Kupongen har ändrats sedan senaste analysen. Den gamla analysen har därför tagits bort.",
) -> CouponStateChange:
    """Replace the active coupon and invalidate state that belongs to another coupon.

    Re-applying an identical coupon updates source metadata but deliberately
    keeps valid analysis/manual state. This matters for Streamlit reruns and CSV
    uploads where the same input may be parsed repeatedly.
    """
    new_coupon = list(coupon)
    if len(new_coupon) != 13:
        raise ValueError(f"En Stryktipskupong måste innehålla exakt 13 matcher, fick {len(new_coupon)}.")

    previous_coupon = state.get("coupon")
    previous_fp = _fingerprint_or_none(previous_coupon)
    current_fp = coupon_fingerprint(new_coupon)
    changed = previous_fp != current_fp

    invalidated: list[str] = []
    if changed:
        for key in COUPON_DEPENDENT_STATE_KEYS:
            if key in state:
                state.pop(key, None)
                invalidated.append(key)
        if stale_notice and previous_fp is not None and "one_click_result" in invalidated:
            state["analysis_stale_notice"] = stale_notice

    state["coupon"] = new_coupon
    state["data_mode"] = str(data_mode)
    state["source_message"] = str(source_message)

    return CouponStateChange(
        changed=changed,
        previous_fingerprint=previous_fp,
        current_fingerprint=current_fp,
        invalidated_keys=tuple(invalidated),
    )


def ensure_coupon_state(
    state: MutableMapping[str, Any],
    default_coupon: Iterable[Any],
    *,
    data_mode: str = "Demo",
    source_message: str = "Demodata används. Inga siffror ska tolkas som aktuell kupong.",
) -> None:
    """Initialize coupon state without creating a false stale-analysis notice."""
    if "coupon" not in state:
        set_coupon_state(
            state,
            default_coupon,
            data_mode=data_mode,
            source_message=source_message,
            stale_notice=None,
        )


def commit_analysis_state(
    state: MutableMapping[str, Any],
    *,
    enriched_coupon: Iterable[Any],
    result: Any,
    coupon_fingerprint_value: str,
    duration_seconds: float | None,
    data_mode: str = "Multi-source",
    source_message: str = "Analys genomförd med de datakällor som var tillgängliga och verifierbara.",
) -> CouponStateChange:
    """Atomically commit an analysis and the coupon it belongs to.

    Coupon replacement must happen before saving the analysis payload, because
    changing the coupon intentionally invalidates old analysis state.
    """
    transition = set_coupon_state(
        state,
        enriched_coupon,
        data_mode=data_mode,
        source_message=source_message,
        stale_notice=None,
    )
    state["one_click_result"] = result
    state["one_click_coupon_fingerprint"] = str(coupon_fingerprint_value)
    state["one_click_duration_seconds"] = duration_seconds
    return transition
