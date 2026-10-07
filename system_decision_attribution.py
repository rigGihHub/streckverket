from __future__ import annotations

"""Attribute prospective P(13) decision weakness without double-counting labs.

v3.83, v3.85 and v3.86 are deliberately overlapping diagnostics.  Their
headline P(13) effects must therefore not be added together.  This module uses
v3.83 as broad context, v3.85 to isolate guard relocation and v3.86 as the
strict same-row whole-structure benchmark.  Spike diagnostics are kept on a
separate evidence axis because calibration gaps/Brier scores are not directly
commensurable with P(13) headroom.
"""

from typing import Iterable

from system_p13_audit import system_p13_summary
from guard_allocation_lab import guard_allocation_summary
from counterfactual_13_optimizer_audit import optimizer_audit_summary
from spike_failure_lab import spike_failure_summary


def _pos(value) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except Exception:
        return 0.0


def decision_attribution_summary(coupons: Iterable) -> dict:
    coupons = list(coupons)
    broad = system_p13_summary(coupons)
    guard = guard_allocation_summary(coupons)
    structure = optimizer_audit_summary(coupons)
    spike = spike_failure_summary(coupons)

    direct_ready = bool(guard["review_ready"] and structure["review_ready"])
    spike_ready = bool(spike["review_ready"])

    guard_issue = guard["status"] == "GRANSKA GARDERINGSALLOKERING"
    structure_issue = structure["status"] == "GRANSKA COUNTERFACTUAL MAX-13-STRUKTUR"
    broad_issue = broad["status"] == "GRANSKA SYSTEM-/BUDGETALLOKERING"

    spike_status = str(spike["status"])
    spike_system_issue = spike_status == "GRANSKA SYSTEMETS SPIKVAL"
    spike_probability_issue = spike_status in {
        "GRANSKA SPIKÖVERKONFIDENS",
        "GRANSKA MODELLJUSTERINGAR PÅ SPIKAR",
    }

    guard_delta = _pos(guard.get("mean_p13_delta_pp"))
    structure_delta = _pos(structure.get("mean_p13_delta_pp"))
    guard_share = (min(1.0, guard_delta / structure_delta) if structure_delta > 1e-12 else None)
    residual_structure_delta = max(0.0, structure_delta - guard_delta)

    if not direct_ready and not spike_ready:
        priority = "SAMLA MER PROSPEKTIV HISTORIK"
        attribution = "UNDERLAGET ÄR INTE MOGNAT"
        rationale = (
            "Beslutsområdena har ännu inte tillräckligt prospektivt underlag för jämförbar attribution. "
            "Streckverket ska inte rangordna problem på små sample."
        )
    elif direct_ready and structure_issue:
        if guard_issue and guard_share is not None and guard_share >= 0.60:
            priority = "TESTA GARDERINGSALLOKERING FÖRST"
            attribution = "GARDERINGSALLOKERING DOMINERAR DET DIREKTA P(13)-HEADROOMET"
            rationale = (
                "Samma-rad-auditen visar strukturellt P(13)-headroom och huvuddelen av det genomsnittliga direkta headroomet "
                "kan reproduceras av den striktare garderingflytt-analysen. Ett avgränsat garderingsexperiment är därför mer informativt än att ändra hela strategin."
            )
        elif spike_system_issue and spike_ready:
            priority = "TESTA SPIKVAL OCH SYSTEMSTRUKTUR SEPARAT"
            attribution = "BLANDAD SYSTEMSIGNAL: SPIKVAL + ÖVRIG STRUKTUR"
            rationale = (
                "Samma-rad-systemen visar återkommande P(13)-headroom samtidigt som spiklabbet pekar på systemets val av spiktecken. "
                "Signalerna bör testas i separata prospektiva strategiexperiment för att undvika att effekterna blandas ihop."
            )
        else:
            priority = "TESTA SYSTEMSTRUKTUR FÖRST"
            attribution = "ÖVRIG SYSTEMSTRUKTUR HAR TYDLIGAST DIREKT P(13)-SIGNAL"
            rationale = (
                "Counterfactual-auditen visar återkommande headroom med exakt samma radantal, men garderingflyttar förklarar inte huvuddelen av signalen. "
                "Nästa experiment bör därför rikta sig mot den bredare spik/halv/hel-strukturen."
            )
    elif direct_ready and guard_issue:
        priority = "TESTA GARDERINGSALLOKERING FÖRST"
        attribution = "GARDERINGSALLOKERING ÄR DEN TYDLIGASTE DIREKTA SYSTEMSIGNALEN"
        rationale = (
            "Garderingflyttar visar återkommande P(13)-nytta under exakt samma radantal medan den bredare strukturgrinden inte visar motsvarande återkommande signal."
        )
    elif spike_ready and spike_system_issue:
        priority = "TESTA SPIKVAL FÖRST"
        attribution = "SPIKVALET ÄR DEN TYDLIGASTE SYSTEMSIGNALEN"
        rationale = (
            "Spiklabbet pekar på systemets val av spiktecken, medan samma-rad-auditerna inte visar ett tydligt återkommande allokerings- eller strukturproblem."
        )
    elif spike_ready and spike_probability_issue:
        priority = "TESTA SANNOLIKHET/KALIBRERING FÖRE STRATEGI"
        attribution = "SPIKPROBLEMET SER FRÄMST PREDIKTIVT UT"
        rationale = (
            "Spikdiagnostiken pekar på överkonfidens eller sämre sannolikheter än marknadsankaret. Detta är inte direkt P(13)-headroom och ska därför inte blandas ihop med systemallokering."
        )
    elif direct_ready and broad_issue:
        priority = "BEHÅLL SYSTEMHYPOTESEN ÖPPEN – ISOLERING SAKNAS"
        attribution = "BRED P(13)-SIGNAL UTAN TYDLIG KÄLLA"
        rationale = (
            "Den breda budgetauditen ser headroom, men de striktare samma-rad-labben isolerar ännu inte garderingar eller struktur som återkommande huvudorsak. "
            "Bygg inte en strategiregel från den breda signalen ensam."
        )
    else:
        priority = "INGET NYTT STRATEGIEXPERIMENT ÄNNU"
        attribution = "INGEN TYDLIG ÅTERKOMMANDE BESLUTSBRIST"
        rationale = (
            "De mogna diagnostikgrindarna pekar inte ut spikdisciplin, garderingallokering eller systemstruktur som ett tillräckligt tydligt återkommande huvudproblem."
        )

    return {
        "stored_coupons": len(coupons),
        "direct_system_review_ready": direct_ready,
        "spike_review_ready": spike_ready,
        "broad_status": broad["status"],
        "guard_status": guard["status"],
        "structure_status": structure["status"],
        "spike_status": spike["status"],
        "broad_mean_p13_delta_pp": broad.get("mean_p13_delta_pp"),
        "guard_mean_p13_delta_pp": guard.get("mean_p13_delta_pp"),
        "structure_mean_p13_delta_pp": structure.get("mean_p13_delta_pp"),
        "guard_share_of_structure_headroom": guard_share,
        "residual_structure_headroom_pp": residual_structure_delta,
        "priority": priority,
        "attribution": attribution,
        "rationale": rationale,
        "p13_effects_are_additive": False,
        "spike_metrics_commensurable_with_p13": False,
        "uses_results_for_selection": False,
        "automatic_strategy_change": False,
        "automatic_model_change": False,
        "edge_claim_allowed": False,
    }
