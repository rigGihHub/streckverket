from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, List, Sequence, Tuple

from core import MatchInput, market_probabilities
from data_sources import (
    SourceStatus,
    fetch_svenskaspel_current,
    fetch_the_odds_api,
    match_odds_to_coupon,
    parse_coupon_csv,
)
from demo_data import get_demo_matches


@dataclass(frozen=True)
class OddsMergeResult:
    coupon: List[MatchInput]
    status: SourceStatus
    matched_count: int

    @property
    def message(self) -> str:
        return f"{self.status.message} Matchade {self.matched_count}/13 kupongmatcher utan fuzzy-gissning."


def load_current_coupon() -> Tuple[List[MatchInput] | None, SourceStatus]:
    """Single application entry-point for the current Svenska Spel coupon."""
    return fetch_svenskaspel_current()


def load_csv_coupon(dataframe: Any) -> List[MatchInput]:
    """Parse a user supplied coupon dataframe and enforce source-level validation."""
    return parse_coupon_csv(dataframe)


def load_demo_coupon() -> List[MatchInput]:
    """Return demo data through the same loader boundary as production sources."""
    return list(get_demo_matches())


def merge_external_odds(
    coupon: Sequence[MatchInput],
    api_key: str,
    sport_keys: Sequence[str],
    regions: str = "uk,eu",
) -> OddsMergeResult:
    """Fetch and conservatively merge bookmaker odds without losing coupon metadata.

    Team matching remains exact/normalized only; unmatched games are left untouched.
    A matched game is explicitly marked as having real market data.
    """
    events, status = fetch_the_odds_api(api_key, sport_keys, regions)
    if not status.ok:
        return OddsMergeResult(list(coupon), status, 0)

    matched = match_odds_to_coupon(coupon, events)
    updated: List[MatchInput] = []
    for match in coupon:
        event = matched.get(match.number)
        if not event:
            updated.append(match)
            continue
        new_odds = tuple(float(x) for x in event["odds"])
        updated.append(
            replace(
                match,
                odds=new_odds,
                model=market_probabilities(new_odds),
                market_available=True,
            )
        )
    return OddsMergeResult(updated, status, len(matched))
