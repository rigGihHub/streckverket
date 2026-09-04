"""Shared orchestration for Streckverket's one-click analysis.

Keeps the actual analysis execution and session payload construction outside
Streamlit so normal- and expert-UI use the same code path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any

from one_click import OneClickConfig, run_one_click
from production_hardening import Timer, coupon_fingerprint


DEFAULT_ODDS_SPORT_KEYS = (
    "soccer_epl",
    "soccer_efl_champ",
    "soccer_england_league1",
    "soccer_england_league2",
)


@dataclass(frozen=True)
class AnalysisExecution:
    result: Any
    duration_seconds: float | None
    coupon_fingerprint: str


def build_one_click_config(
    *,
    odds_api_key: str = "",
    football_data_key: str = "",
    api_football_key: str = "",
    odds_sport_keys: Iterable[str] = DEFAULT_ODDS_SPORT_KEYS,
    odds_regions: str = "uk,eu",
    max_competitions: int = 25,
) -> OneClickConfig:
    """Build a normalized one-click config from either secrets or expert UI."""
    cleaned_sports = tuple(str(x).strip() for x in odds_sport_keys if str(x).strip())
    return OneClickConfig(
        odds_api_key=str(odds_api_key).strip(),
        football_data_key=str(football_data_key).strip(),
        api_football_key=str(api_football_key).strip(),
        odds_sport_keys=cleaned_sports or DEFAULT_ODDS_SPORT_KEYS,
        odds_regions=str(odds_regions).strip() or "uk,eu",
        max_competitions=max(1, int(max_competitions)),
    )


def execute_one_click(config: OneClickConfig, *, coupon, fetch_coupon: bool) -> AnalysisExecution:
    """Run the analysis once and return the exact state payload UIs should save."""
    with Timer("one_click_analysis") as timer:
        result = run_one_click(config, coupon=coupon, fetch_coupon=bool(fetch_coupon))
    duration = timer.result.seconds if timer.result else None
    return AnalysisExecution(
        result=result,
        duration_seconds=duration,
        coupon_fingerprint=coupon_fingerprint(result.enriched),
    )
