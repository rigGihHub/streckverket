from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from core import SIGNS


@dataclass(frozen=True)
class QuickAction:
    kind: str
    match_number: int | None
    title: str
    detail: str


@dataclass(frozen=True)
class CompressedDecision:
    rows: int
    cost: float
    spikes: int
    guards: int
    fulls: int
    readiness_status: str
    readiness_score: int
    actions: tuple[QuickAction, ...]


def _match_index(matches: Sequence[Any], number: int) -> int | None:
    for i, match in enumerate(matches):
        if int(match.number) == int(number):
            return i
    return None


def build_compressed_decision(matches, summary, readiness) -> CompressedDecision:
    """Compress the existing decision into a few actions without creating new picks.

    The optimized system is the source of truth. Summary sections may only be surfaced
    when they agree with the actual system selection for that match.
    """
    system = summary["system"]
    selections = list(system["selections"])
    spikes = [(m, tuple(sel)) for m, sel in zip(matches, selections) if len(sel) == 1]
    guards = [(m, tuple(sel)) for m, sel in zip(matches, selections) if len(sel) == 2]
    fulls = [(m, tuple(sel)) for m, sel in zip(matches, selections) if len(sel) == 3]
    actions: list[QuickAction] = []

    # Best actual system spike: strongest probability for the sign that is really spiked.
    if spikes:
        def spike_strength(item):
            m, sel = item
            idx = SIGNS.index(sel[0])
            return (float(m.model[idx]), -int(m.number))
        m, sel = max(spikes, key=spike_strength)
        idx = SIGNS.index(sel[0])
        actions.append(QuickAction(
            "SPIK", int(m.number), f"SPIKA {int(m.number)} · {sel[0]}",
            f"{m.home} – {m.away} · modell {m.model[idx]*100:.0f}% · streck {m.public[idx]*100:.0f}%",
        ))

    # Existing must-guard summary, but only if the optimized system actually guards it.
    for decision in summary.get("must_guard", ()): 
        idx = _match_index(matches, decision.number)
        if idx is not None and len(selections[idx]) > 1:
            m = matches[idx]
            sel = tuple(selections[idx])
            actions.append(QuickAction(
                "GARDERA", int(m.number), f"GARDERA {int(m.number)} · {''.join(sel)}",
                f"{m.home} – {m.away} · systemet använder {len(sel)} tecken",
            ))
            break

    # Existing trap/upset labels only. They never alter the system.
    for key, kind, label in (("traps", "FÄLLA", "SE UPP"), ("upsets", "SKRÄLL", "SKRÄLLCHANS")):
        for decision in summary.get(key, ()):
            idx = _match_index(matches, decision.number)
            if idx is None:
                continue
            m = matches[idx]
            sel = tuple(selections[idx])
            if kind == "FÄLLA":
                actions.append(QuickAction(
                    kind, int(m.number), f"{label} {int(m.number)}",
                    f"{m.home} – {m.away} · system {''.join(sel)} · folkfavorit {decision.public_favorite}",
                ))
            else:
                sign = decision.recommended
                if sign not in sel:
                    continue
                sign_idx = SIGNS.index(sign)
                actions.append(QuickAction(
                    kind, int(m.number), f"{label} {int(m.number)} · {sign}",
                    f"{m.home} – {m.away} · modell {m.model[sign_idx]*100:.0f}% · streck {m.public[sign_idx]*100:.0f}%",
                ))
            break

    return CompressedDecision(
        rows=int(system["rows"]), cost=float(system["cost"]),
        spikes=len(spikes), guards=len(guards), fulls=len(fulls),
        readiness_status=str(readiness.status), readiness_score=int(readiness.score),
        actions=tuple(actions[:4]),
    )
