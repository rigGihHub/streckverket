from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from core import SIGNS, MatchInput, classify_match
from decision_page import summarize_decisions
from money_impact import spending_options, best_spending_option
from strategy_engine import best_cross, coupon_cleaners, coupon_type, countercheck


@dataclass(frozen=True)
class PlanItem:
    kind: str
    match_number: int | None
    title: str
    action: str
    why: str


@dataclass(frozen=True)
class PlayPlan:
    coupon_type: str
    coupon_explanation: str
    items: tuple[PlanItem, ...]
    budget_message: str
    countercheck: tuple[str, ...]


def _match(matches: Sequence[MatchInput], number: int) -> MatchInput:
    return next(m for m in matches if m.number == number)


def build_play_plan(matches: Sequence[MatchInput], budget: int, strategy: str = "MAX 13", locks=None) -> PlayPlan:
    """Build one beginner-friendly action plan from existing, auditable engines.

    No new football facts are invented here: every recommendation is derived from the
    model/public probabilities and the globally optimized system already in Streckverket.
    """
    summary = summarize_decisions(matches, int(budget), strategy, locks)
    system = summary["system"]
    ctype, ctext = coupon_type(matches)
    items: list[PlanItem] = []

    # The actual optimized system is the source of truth for actions.
    for m, sel in zip(matches, system["selections"]):
        klass = classify_match(m.model, m.public)
        if len(sel) == 1:
            sign = sel[0]
            i = SIGNS.index(sign)
            items.append(PlanItem(
                "SPIK", m.number, f"Spika match {m.number}",
                f"Spela bara {sign} i {m.home} – {m.away}.",
                f"Systemet prioriterar {sign}; modellen ger tecknet {m.model[i]*100:.0f} % och strecken är {m.public[i]*100:.0f} %.",
            ))
        elif klass == "Fällan":
            fav_i = max(range(3), key=lambda i: m.public[i])
            fav = SIGNS[fav_i]
            if fav not in sel or len(sel) > 1:
                items.append(PlanItem(
                    "FÄLLA", m.number, f"Var försiktig med favoriten i match {m.number}",
                    f"Systemet använder {''.join(sel)} i {m.home} – {m.away} i stället för att lita blint på {fav}.",
                    f"{fav} har {m.public[fav_i]*100:.0f} % av strecken men modellen bedömer chansen till {m.model[fav_i]*100:.0f} %.",
                ))

    bx = best_cross(matches)
    if bx:
        m = _match(matches, bx.number)
        sel = system["selections"][list(matches).index(m)]
        if "X" in sel:
            items.append(PlanItem(
                "X-VÄRDE", bx.number, f"Ta krysset på allvar i match {bx.number}",
                f"X finns med i systemet för {bx.home} – {bx.away}.",
                f"Modellen ger X {bx.model_probability*100:.0f} %, medan bara {bx.public_share*100:.0f} % av strecken ligger där.",
            ))

    cleaners = coupon_cleaners(matches, 5)
    for c in cleaners:
        m = _match(matches, c.number)
        idx = list(matches).index(m)
        if c.sign in system["selections"][idx]:
            items.append(PlanItem(
                "KUPONGRENSARE", c.number, f"Kupongrensare i match {c.number}",
                f"Behåll {c.sign} i {c.home} – {c.away}.",
                f"Tecknet är valt av {c.public_share*100:.0f} % men modellen ger det {c.model_probability*100:.0f} %. Om det sitter kan många andra system falla bort.",
            ))
            break

    # Deduplicate same kind+match, then prioritize a compact plan.
    seen = set(); compact=[]
    priority = {"SPIK": 0, "FÄLLA": 1, "X-VÄRDE": 2, "KUPONGRENSARE": 3}
    for item in sorted(items, key=lambda x: (priority.get(x.kind, 9), x.match_number or 99)):
        key=(item.kind,item.match_number)
        if key not in seen:
            compact.append(item); seen.add(key)

    options = spending_options(matches, int(budget), (10, 20, 50), strategy, locks)
    best = best_spending_option(options)
    if best is None:
        budget_message = "Behåll nuvarande budget. +10, +20 eller +50 kr ger ingen tydlig förbättring i den nuvarande radstrukturen."
    else:
        budget_message = (
            f"Om du vill öka budgeten är +{best.requested_extra} kr det effektivaste av +10/+20/+50-alternativen just nu. "
            f"Det använder cirka {best.actual_extra_cost:.0f} kr extra och höjer modellens beräknade 13-rättstäckning med "
            f"{best.coverage_gain_pp:.3f} procentenheter."
        )

    return PlayPlan(ctype, ctext, tuple(compact[:8]), budget_message, tuple(countercheck(matches, system)))
