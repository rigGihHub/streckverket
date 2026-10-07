from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FirstTimeStrategy:
    label: str
    engine_strategy: str
    explanation: str


STRATEGIES = (
    FirstTimeStrategy(
        label="Streckverkets rekommendation",
        engine_strategy="VÄRDE",
        explanation="Balanserar sannolikhet med hur kupongen är streckad. Detta är standardvalet.",
    ),
    FirstTimeStrategy(
        label="Försiktigare",
        engine_strategy="MAX 13",
        explanation="Prioriterar de mest sannolika resultaten enligt modellen och går mer sällan emot favoriter.",
    ),
)


def strategy_labels() -> tuple[str, ...]:
    return tuple(s.label for s in STRATEGIES)


def resolve_strategy(label: str) -> FirstTimeStrategy:
    for strategy in STRATEGIES:
        if strategy.label == label:
            return strategy
    return STRATEGIES[0]


def beginner_reason_lines(summary: dict, matches: Sequence, readiness_status: str) -> tuple[str, ...]:
    """Compress existing decision objects into at most three plain-language reasons.

    This creates no new predictive signal; it only describes the already-built system.
    """
    lines: list[str] = []
    spikes = list(summary.get("spikes") or [])
    guards = list(summary.get("must_guard") or [])
    traps = list(summary.get("traps") or [])

    if spikes:
        d = spikes[0]
        lines.append(f"Match {d.number} är den tydligaste kandidaten att spika.")
    if guards:
        d = guards[0]
        lines.append(f"Match {d.number} är en av matcherna där en gardering gör mest nytta.")
    if traps:
        d = traps[0]
        lines.append(f"Match {d.number} är en favorit att vara extra försiktig med.")

    if not lines:
        lines.append("Kupongen saknar just nu en enskild match som sticker ut tydligt.")

    if str(readiness_status or "").upper() not in {"SPELKlar".upper(), "SPEKLAR"}:
        lines.append("Underlaget är ännu inte fullt spelklart, så kontrollera statusen innan du lämnar in.")

    return tuple(lines[:3])
