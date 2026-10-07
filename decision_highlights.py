from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

SIGNS = ("1", "X", "2")


@dataclass(frozen=True)
class DecisionHighlight:
    role: str
    match_number: int
    match_name: str
    selection: str
    explanation: str


def _pct(x: float) -> int:
    return int(round(max(0.0, min(1.0, float(x))) * 100))


def build_decision_highlights(matches: Iterable[object], selections: Sequence[Sequence[str]]) -> tuple[DecisionHighlight, ...]:
    matches = list(matches)
    if len(matches) != len(selections):
        raise ValueError("Antalet matcher och systemval måste vara lika.")

    highlights: list[DecisionHighlight] = []

    # 1) Viktigaste spiken: högst modellstöd bland de tecken som systemet faktiskt spikar.
    spike_candidates = []
    for m, sel in zip(matches, selections):
        chosen = tuple(str(s) for s in sel if str(s) in SIGNS)
        if len(chosen) != 1:
            continue
        idx = SIGNS.index(chosen[0])
        model = tuple(float(v) for v in getattr(m, "model", (0, 0, 0)))
        public = tuple(float(v) for v in getattr(m, "public", (0, 0, 0)))
        if len(model) != 3 or len(public) != 3:
            continue
        spike_candidates.append((model[idx], model[idx] - public[idx], m, chosen[0]))
    if spike_candidates:
        model_p, diff, m, sign = max(spike_candidates, key=lambda x: (x[0], x[1], -int(getattr(x[2], "number", 99))))
        extra = ""
        if diff >= 0.05:
            extra = f" Strecket är {_pct(getattr(m, 'public')[SIGNS.index(sign)])} %, alltså lägre än modellens nivå."
        highlights.append(DecisionHighlight(
            role="VIKTIGASTE SPIKEN",
            match_number=int(getattr(m, "number")),
            match_name=f"{getattr(m, 'home')} – {getattr(m, 'away')}",
            selection=sign,
            explanation=f"Det här är den spik i systemet som har starkast modellstöd ({_pct(model_p)} % för {sign}).{extra}",
        ))

    # 2) Viktigaste garderingen: den garderade match där modellens topputfall är minst dominant.
    guard_candidates = []
    for m, sel in zip(matches, selections):
        chosen = tuple(str(s) for s in sel if str(s) in SIGNS)
        if len(chosen) <= 1:
            continue
        model = tuple(float(v) for v in getattr(m, "model", (0, 0, 0)))
        if len(model) != 3:
            continue
        uncertainty = 1.0 - max(model)
        spread = max(model) - min(model)
        guard_candidates.append((uncertainty, -spread, len(chosen), m, chosen))
    if guard_candidates:
        _, _, _, m, chosen = max(guard_candidates, key=lambda x: (x[0], x[1], x[2], -int(getattr(x[3], "number", 99))))
        model = tuple(float(v) for v in getattr(m, "model"))
        highlights.append(DecisionHighlight(
            role="VIKTIGASTE GARDERINGEN",
            match_number=int(getattr(m, "number")),
            match_name=f"{getattr(m, 'home')} – {getattr(m, 'away')}",
            selection="/".join(chosen),
            explanation=f"Ingen sida dominerar modellen tydligt här; högsta modellchansen är {_pct(max(model))} %. Systemet lägger därför extra skydd i just den här matchen.",
        ))

    # 3) Fälla många: största positiva gapet mellan folkets favorit och modellens sannolikhet.
    trap_candidates = []
    for m in matches:
        model = tuple(float(v) for v in getattr(m, "model", (0, 0, 0)))
        public = tuple(float(v) for v in getattr(m, "public", (0, 0, 0)))
        if len(model) != 3 or len(public) != 3:
            continue
        fav_idx = max(range(3), key=lambda i: public[i])
        gap = public[fav_idx] - model[fav_idx]
        trap_candidates.append((gap, public[fav_idx], m, SIGNS[fav_idx], model[fav_idx]))
    if trap_candidates:
        gap, pub_p, m, sign, model_p = max(trap_candidates, key=lambda x: (x[0], x[1], -int(getattr(x[2], "number", 99))))
        if gap >= 0.05:
            highlights.append(DecisionHighlight(
                role="MATCHEN SOM KAN FÄLLA MÅNGA",
                match_number=int(getattr(m, "number")),
                match_name=f"{getattr(m, 'home')} – {getattr(m, 'away')}",
                selection=sign,
                explanation=f"Folkets favorit {sign} är streckad till {_pct(pub_p)} %, medan modellen ligger på {_pct(model_p)} %. Det gör favoriten mer sårbar än strecken antyder.",
            ))

    # Avoid duplicate match/role clutter. A match can still legitimately appear twice only if it is both key spike and public trap,
    # but novice view benefits from distinct decisions where possible.
    deduped: list[DecisionHighlight] = []
    used: set[int] = set()
    for item in highlights:
        if item.match_number in used:
            continue
        deduped.append(item)
        used.add(item.match_number)
    return tuple(deduped[:3])
