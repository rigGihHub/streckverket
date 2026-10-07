from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExpertDecisionSummary:
    data_status: str
    evidence_status: str
    next_action: str
    review_now: int = 0
    timing_review: int = 0
    provenance_gaps: int = 0
    collect_more: int = 0
    edge_claim_allowed: bool = False


def evidence_snapshot(store: Any) -> dict[str, int | bool]:
    """Build the same conservative evidence snapshot used by Evidence Dashboard.

    The function deliberately works from stored market/signal history. It does not
    infer missing league/source provenance and it never promotes a segment to edge.
    """
    empty = {
        "review_now": 0,
        "timing_review": 0,
        "provenance_gaps": 0,
        "collect_more": 0,
        "edge_claim_allowed": False,
    }
    if store is None:
        return empty

    from fact_market_timing import fact_market_timing_rows
    from repeated_signal_evidence import repeated_signal_evidence_rows
    from signal_market_response import signal_market_response_rows, directional_evidence_rows
    from evidence_dashboard import evidence_dashboard_rows, evidence_dashboard_summary

    market_points = store.load_market_points(None)
    signal_points = store.load_signal_points(None)
    timing = fact_market_timing_rows(market_points, signal_points, threshold_pp=1.0)
    repeated = repeated_signal_evidence_rows(timing, min_observations=30, min_unique_matches=20)
    direction_response = signal_market_response_rows(timing)
    directional = directional_evidence_rows(direction_response, min_observations=30, min_unique_matches=20)
    rows = evidence_dashboard_rows(repeated, directional)
    summary = evidence_dashboard_summary(rows)
    return {
        "review_now": int(summary.get("review_now", 0)),
        "timing_review": int(summary.get("timing_review", 0)),
        "provenance_gaps": int(summary.get("provenance_gaps", 0)),
        "collect_more": int(summary.get("collect_more", 0)),
        "edge_claim_allowed": False,
    }


def build_expert_decision_summary(
    *,
    data_mode: str,
    total_matches: int,
    market_verified: int,
    analysis_available: bool,
    readiness_priority_text: str | None,
    evidence: dict[str, int | bool] | None = None,
) -> ExpertDecisionSummary:
    """Create a short expert action summary without inventing a new readiness score."""
    evidence = evidence or {}
    review_now = int(evidence.get("review_now", 0) or 0)
    timing_review = int(evidence.get("timing_review", 0) or 0)
    provenance_gaps = int(evidence.get("provenance_gaps", 0) or 0)
    collect_more = int(evidence.get("collect_more", 0) or 0)

    if str(data_mode).lower() == "demo":
        data_status = "DEMO – INTE SPELKLAR"
        next_action = "Hämta en riktig kupong innan expertanalysen används för beslut."
    elif total_matches != 13:
        data_status = "VÄNTA – KUPONGEN ÄR INTE KOMPLETT"
        next_action = f"Säkra exakt 13 matcher. Nuvarande kupong innehåller {total_matches}."
    elif market_verified < total_matches:
        missing = max(0, total_matches - market_verified)
        data_status = "VÄNTA – MARKNADSANKARE SAKNAS"
        next_action = f"Säkra verifierad bookmakerbas för {missing} av {total_matches} matcher innan övrig evidens prioriteras."
    elif not analysis_available:
        data_status = "UNDERLAG FINNS – ANALYS SAKNAS"
        next_action = "Kör Analysera kupongen så att datatäckning och verifierade informationslager kan granskas."
    else:
        data_status = "MARKNADSBAS VERIFIERAD"
        next_action = readiness_priority_text or "Ingen tydlig datalucka dominerar. Granska bara segment med tillräcklig historik."

    if review_now > 0:
        evidence_status = f"{review_now} segment värda manuell granskning"
        if data_status == "MARKNADSBAS VERIFIERAD" and (not readiness_priority_text or readiness_priority_text.startswith("Ingen tydlig")):
            next_action = f"Granska de {review_now} segment som har tillräckligt underlag. Leta efter robusthet – inte en hög procentsiffra."
    elif timing_review > 0:
        evidence_status = f"{timing_review} segment har tillräcklig tidsdata"
        if data_status == "MARKNADSBAS VERIFIERAD" and (not readiness_priority_text or readiness_priority_text.startswith("Ingen tydlig")):
            next_action = "Granska tidsmönstren och fortsätt samla riktningsdata innan några slutsatser dras."
    elif provenance_gaps > 0:
        evidence_status = f"{provenance_gaps} segment har proveniensproblem"
        if data_status == "MARKNADSBAS VERIFIERAD" and (not readiness_priority_text or readiness_priority_text.startswith("Ingen tydlig")):
            next_action = "Fixa okänd liga/källa i historiken innan segmenten används för slutsatser."
    elif collect_more > 0:
        evidence_status = "Historiken är fortfarande för tunn"
        if data_status == "MARKNADSBAS VERIFIERAD" and (not readiness_priority_text or readiness_priority_text.startswith("Ingen tydlig")):
            next_action = "Samla fler verifierade observationer och unika matcher. Ändra inte modellvikter ännu."
    else:
        evidence_status = "Ingen granskningsbar signalevidens ännu"

    return ExpertDecisionSummary(
        data_status=data_status,
        evidence_status=evidence_status,
        next_action=next_action,
        review_now=review_now,
        timing_review=timing_review,
        provenance_gaps=provenance_gaps,
        collect_more=collect_more,
        edge_claim_allowed=False,
    )
