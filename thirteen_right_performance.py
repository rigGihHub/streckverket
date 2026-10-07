from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from core import SIGNS


@dataclass(frozen=True)
class Coupon13Diagnostic:
    coupon_id: str
    strategy: str
    budget: int
    rows: int
    system_hits: int
    thirteen_correct: bool
    model_pick_hits: int
    market_pick_hits: int
    market_completed: int
    missed_spikes: int
    missed_halves: int
    allocation_misses: int
    model_coverage: float


def _pick(probs: Sequence[float]) -> str:
    return SIGNS[max(range(3), key=lambda i: float(probs[i]))]


def _complete(coupon) -> bool:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    return len(matches) == 13 and all(getattr(m, "result", None) in SIGNS for m in matches)


def coupon_diagnostic(coupon) -> Coupon13Diagnostic | None:
    """Describe a fully resolved coupon without changing or reconstructing it."""
    if not _complete(coupon):
        return None

    system_hits = 0
    model_hits = 0
    market_hits = 0
    market_completed = 0
    missed_spikes = 0
    missed_halves = 0
    allocation_misses = 0

    for match in coupon.matches:
        result = str(match.result)
        selected = tuple(getattr(match, "selected", ()) or ())
        covered = result in selected
        system_hits += int(covered)
        model_pick = _pick(match.model)
        model_hits += int(model_pick == result)

        if bool(getattr(match, "market_available", False)):
            market_completed += 1
            market_hits += int(_pick(match.market) == result)

        if not covered:
            if len(selected) == 1:
                missed_spikes += 1
            elif len(selected) == 2:
                missed_halves += 1
            # If the model's own top outcome was the result but the built system
            # excluded it, the miss belongs to system construction/allocation,
            # not to the model's top-pick prediction.
            if model_pick == result:
                allocation_misses += 1

    return Coupon13Diagnostic(
        coupon_id=str(getattr(coupon, "coupon_id", "")),
        strategy=str(getattr(coupon, "strategy", "")),
        budget=int(getattr(coupon, "budget", 0) or 0),
        rows=int(getattr(coupon, "rows", 0) or 0),
        system_hits=system_hits,
        thirteen_correct=(system_hits == 13),
        model_pick_hits=model_hits,
        market_pick_hits=market_hits,
        market_completed=market_completed,
        missed_spikes=missed_spikes,
        missed_halves=missed_halves,
        allocation_misses=allocation_misses,
        model_coverage=float(getattr(coupon, "model_coverage", 0.0) or 0.0),
    )


def coupon_rows(coupons: Iterable) -> list[dict]:
    out: list[dict] = []
    for coupon in coupons:
        d = coupon_diagnostic(coupon)
        if d is None:
            continue
        out.append({
            "Kupong": d.coupon_id,
            "Strategi": d.strategy or "–",
            "Budget": d.budget,
            "Rader": d.rows,
            "Systemträffar": d.system_hits,
            "13 täckt": "JA" if d.thirteen_correct else "NEJ",
            "Spikmissar": d.missed_spikes,
            "Halvmissar": d.missed_halves,
            "Systemval missade trots rätt modellförstaval": d.allocation_misses,
            "Modellens förstaval rätt": d.model_pick_hits,
            "Marknadens förstaval rätt": d.market_pick_hits if d.market_completed else None,
            "Modellens frysta systemtäckning": d.model_coverage,
        })
    return out


def miss_rows(coupons: Iterable) -> list[dict]:
    rows: list[dict] = []
    for coupon in coupons:
        if not _complete(coupon):
            continue
        for match in coupon.matches:
            result = str(match.result)
            selected = tuple(getattr(match, "selected", ()) or ())
            if result in selected:
                continue
            model_pick = _pick(match.model)
            model_rank = sorted(SIGNS, key=lambda s: float(match.model[SIGNS.index(s)]), reverse=True).index(result) + 1
            rows.append({
                "Kupong": str(getattr(coupon, "coupon_id", "")),
                "Match": int(match.match_number),
                "Möte": f"{match.home} – {match.away}",
                "Val": "/".join(selected),
                "Utfall": result,
                "Typ": "SPIKMISS" if len(selected) == 1 else "HALVGARDERINGSMISS" if len(selected) == 2 else "SYSTEMMISS",
                "Modellförstaval": model_pick,
                "Rätt utfalls modellrank": model_rank,
                "Modellen hade rätt förstaval": "JA" if model_pick == result else "NEJ",
                "Marknadens förstaval": _pick(match.market) if bool(getattr(match, "market_available", False)) else "–",
            })
    return rows


def performance_summary(coupons: Iterable, *, min_review_coupons: int = 20) -> dict:
    coupons = list(coupons)
    diagnostics = [d for c in coupons if (d := coupon_diagnostic(c)) is not None]
    complete = len(diagnostics)
    thirteen = sum(int(d.thirteen_correct) for d in diagnostics)
    system_misses = sum(13 - d.system_hits for d in diagnostics)
    missed_spikes = sum(d.missed_spikes for d in diagnostics)
    missed_halves = sum(d.missed_halves for d in diagnostics)
    allocation_misses = sum(d.allocation_misses for d in diagnostics)
    model_hits = sum(d.model_pick_hits for d in diagnostics)
    market_hits = sum(d.market_pick_hits for d in diagnostics)
    market_completed = sum(d.market_completed for d in diagnostics)
    completed_matches = complete * 13
    expected_13 = sum(max(0.0, min(1.0, d.model_coverage)) for d in diagnostics)

    if complete == 0:
        priority = "SAMLA FACIT"
        lesson = "Inga kompletta prospektivt sparade kuponger finns ännu. Streckverket ska inte gissa vilken del som hindrar 13 rätt."
    elif complete < min_review_coupons:
        priority = "SAMLA MER PROSPEKTIV HISTORIK"
        lesson = (
            f"Bara {complete} kompletta kuponger finns. Missmönstren visas, men underlaget är för litet för att ändra modell eller systemmotor automatiskt."
        )
    else:
        allocation_share = allocation_misses / system_misses if system_misses else 0.0
        spike_share = missed_spikes / system_misses if system_misses else 0.0
        model_acc = model_hits / completed_matches if completed_matches else 0.0
        market_acc = market_hits / market_completed if market_completed else None
        if allocation_share >= 0.20:
            priority = "GRANSKA SYSTEM-/BUDGETALLOKERING"
            lesson = "En betydande del av systemmissarna inträffade trots att modellens eget förstaval var rätt. Prioritera systemkonstruktionen före nya modellvikter."
        elif spike_share >= 0.50:
            priority = "GRANSKA SPIKDISCIPLIN"
            lesson = "Minst hälften av systemmissarna kommer från spikar. Undersök vilka sannolikhetsnivåer och signalmönster som gör spikarna för aggressiva."
        elif market_acc is not None and model_acc + 0.02 < market_acc:
            priority = "GRANSKA PROGNOSJUSTERINGAR"
            lesson = "Modellens förstaval har hittills träffat sämre än den verifierade marknadsbasen. Extra modelljusteringar bör granskas före mer komplex systemoptimering."
        else:
            priority = "FORTSÄTT PROSPEKTIV VALIDERING"
            lesson = "Ingen enskild felkälla dominerar tillräckligt för en automatisk ändring. Fortsätt samla kuponger och testa nästa hypotes prospektivt."

    return {
        "stored_coupons": len(coupons),
        "complete_coupons": complete,
        "thirteen_correct": thirteen,
        "actual_13_rate": (thirteen / complete) if complete else None,
        "mean_system_hits": (sum(d.system_hits for d in diagnostics) / complete) if complete else None,
        "mean_model_coverage": (sum(d.model_coverage for d in diagnostics) / complete) if complete else None,
        "expected_13_count_from_frozen_model": expected_13,
        "system_misses": system_misses,
        "missed_spikes": missed_spikes,
        "missed_halves": missed_halves,
        "allocation_misses": allocation_misses,
        "model_pick_accuracy": (model_hits / completed_matches) if completed_matches else None,
        "market_pick_accuracy": (market_hits / market_completed) if market_completed else None,
        "review_ready": complete >= min_review_coupons,
        "min_review_coupons": min_review_coupons,
        "priority": priority,
        "lesson": lesson,
        "automatic_model_change": False,
        "edge_claim_allowed": False,
    }
