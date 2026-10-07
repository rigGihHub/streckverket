from __future__ import annotations

"""Explicit registry and lifecycle for prospective prediction experiments.

The registry is deliberately static and auditable. It never mutates production
weights. Lifecycle state is derived only from the pre-registered experiment,
its prospective shadow observations and the fixed v3.79 governance rules.
"""

from dataclasses import dataclass
from typing import Iterable

MARKET_PULL_EXPERIMENT_ID = "market_pull_25_v1"

STATUS_WAITING_GATE = "VÄNTAR PÅ BESLUTSGRIND"
STATUS_ACTIVE = "AKTIVT SHADOW-EXPERIMENT"
STATUS_REVIEW_READY = "MOGEN FÖR FÖRSTA GRANSKNING"
STATUS_PAUSED = "PAUSAD FÖR MANUELL GRANSKNING"
STATUS_REJECTED = "FÖRKASTAT"
STATUS_UNKNOWN = "OKÄNT EXPERIMENT"


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    label: str
    candidate_rule: str
    created_version: str
    candidate_family: str
    pre_registered_parameters: tuple[tuple[str, float], ...]
    affects_production: bool = False
    automatic_promotion: bool = False


_REGISTRY: dict[str, ExperimentDefinition] = {
    MARKET_PULL_EXPERIMENT_ID: ExperimentDefinition(
        experiment_id=MARKET_PULL_EXPERIMENT_ID,
        label="25 % närmare bookmakerankaret",
        candidate_rule="candidate = 75% frozen production model + 25% frozen verified bookmaker anchor",
        created_version="3.78.0",
        candidate_family="market-anchor-shrinkage",
        pre_registered_parameters=(("market_weight", 0.25),),
    ),
}


def get_experiment(experiment_id: str) -> ExperimentDefinition | None:
    return _REGISTRY.get(str(experiment_id or "").strip())


def registered_experiments() -> tuple[ExperimentDefinition, ...]:
    return tuple(_REGISTRY[k] for k in sorted(_REGISTRY))


def _has_any_shadow(coupons: Iterable, experiment_id: str) -> bool:
    for coupon in coupons:
        for match in tuple(getattr(coupon, "matches", ()) or ()):
            if any(getattr(p, "experiment_id", "") == experiment_id
                   for p in tuple(getattr(match, "shadow_predictions", ()) or ())):
                return True
    return False


def experiment_lifecycle(coupons: Iterable, *, experiment_id: str = MARKET_PULL_EXPERIMENT_ID) -> dict:
    """Return deterministic lifecycle state; never changes production automatically."""
    history = list(coupons)
    definition = get_experiment(experiment_id)
    if definition is None:
        return {
            "experiment_id": experiment_id,
            "registered": False,
            "status": STATUS_UNKNOWN,
            "accepts_new_snapshots": False,
            "terminal": True,
            "reason": "Experiment-ID saknas i det explicita registret. Streckverket gissar inte kandidatens regel.",
        }

    from shadow_governance import shadow_governance
    from market_anchor_decision import market_anchor_decision

    governance = shadow_governance(history, experiment_id=experiment_id)
    decision = governance["decision"]
    has_shadow = _has_any_shadow(history, experiment_id)

    if decision == "FÖRKASTA KANDIDATEN":
        status = STATUS_REJECTED
        accepts = False
        terminal = True
        reason = "Governance-grinden har förkastat kandidaten. Nya snapshots för experimentet stoppas."
    elif decision == "GODKÄND FÖR SEPARAT PRODUKTIONSKANDIDAT-GRANSKNING":
        status = STATUS_PAUSED
        accepts = False
        terminal = False
        reason = "Shadow-fasen har klarat promotion-grinden och pausas för separat manuell granskning. Ingen automatisk promotion."
    elif governance["review_ready"]:
        status = STATUS_REVIEW_READY
        accepts = True
        terminal = False
        reason = "Experimentet har tillräckligt underlag för första governance-bedömning men fortsätter i shadow tills en terminal eller manuell review-status nås."
    elif has_shadow:
        status = STATUS_ACTIVE
        accepts = True
        terminal = False
        reason = "Prospektiva shadow-observationer finns och experimentet fortsätter samla data."
    else:
        gate = market_anchor_decision(history)
        candidate = gate.get("candidate_experiment")
        if candidate == "TESTA MINDRE MODELLJUSTERINGAR MOT MARKNADSANKARET":
            status = STATUS_ACTIVE
            accepts = True
            terminal = False
            reason = "v3.77-grinden tillåter det förhandsregistrerade experimentet. Nästa pre-match-snapshot får frysa kandidaten."
        else:
            status = STATUS_WAITING_GATE
            accepts = False
            terminal = False
            reason = "Experimentet är registrerat men får inte starta innan v3.77-grinden öppnar för just denna kandidatfamilj."

    return {
        "experiment_id": experiment_id,
        "registered": True,
        "label": definition.label,
        "created_version": definition.created_version,
        "candidate_family": definition.candidate_family,
        "candidate_rule": definition.candidate_rule,
        "pre_registered_parameters": dict(definition.pre_registered_parameters),
        "status": status,
        "accepts_new_snapshots": accepts,
        "terminal": terminal,
        "reason": reason,
        "governance_decision": decision,
        "completed_matches": governance["completed_matches"],
        "completed_coupons": governance["completed_coupons"],
        "affects_production": False,
        "automatic_promotion": False,
    }


def experiment_registry_rows(coupons: Iterable) -> list[dict]:
    history = list(coupons)
    rows = []
    for exp in registered_experiments():
        life = experiment_lifecycle(history, experiment_id=exp.experiment_id)
        rows.append({
            "Experiment": exp.experiment_id,
            "Kandidat": exp.label,
            "Status": life["status"],
            "Matcher": life["completed_matches"],
            "Kuponger": life["completed_coupons"],
            "Nya snapshots": "JA" if life["accepts_new_snapshots"] else "NEJ",
            "Produktionspåverkan": "NEJ",
        })
    return rows
