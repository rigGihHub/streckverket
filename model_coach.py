from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from factor_learning import factor_scorecard, proposed_weight_actions
from learning_diagnostics import diagnostic_segments, strongest_lessons, recommended_action

@dataclass(frozen=True)
class CoachFinding:
    priority: str
    area: str
    status: str
    evidence: str
    action: str


def build_model_coach(coupons: Sequence[object], *, min_segment: int = 30, min_factor: int = 30) -> dict:
    segments = diagnostic_segments(coupons, min_sample=min_segment)
    factors = factor_scorecard(coupons, min_sample=min_factor)
    lessons = strongest_lessons(segments)
    findings: list[CoachFinding] = []

    for row in segments:
        if row.segment == "Alla matcher" or row.verdict == "För lite data":
            continue
        priority = "Hög" if row.verdict == "Behöver granskas" else "Medel"
        findings.append(CoachFinding(
            priority, row.segment, row.verdict,
            f"{row.matches} matcher · skillnad mot marknaden {row.improvement:+.3f} i Brier (positivt är bättre).",
            row.explanation,
        ))

    for row in factors:
        if row["verdict"] == "För lite data":
            continue
        priority = "Hög" if row["verdict"] == "Behöver granskas" else "Medel"
        findings.append(CoachFinding(
            priority, row["name"], row["verdict"],
            f"{row['matches']} observationer · hjälpte i {100*row['help_rate']:.0f} % · genomsnittligt Brier-bidrag {row['mean_brier_gain']:+.4f}.",
            "Testa faktorn på ny separat data innan någon vikt ändras." if row["verdict"] != "Ingen tydlig skillnad" else "Behåll vikten tills vidare och samla mer facit.",
        ))

    findings.sort(key=lambda x: (x.priority != "Hög", x.status != "Behöver granskas", x.area))
    mature = [f for f in factors if f["verdict"] != "För lite data"]
    return {
        "segments": segments,
        "factors": factors,
        "findings": findings,
        "summary": lessons["summary"],
        "recommended_action": recommended_action(segments),
        "weight_actions": proposed_weight_actions(factors),
        "completed_matches": sum(1 for c in coupons for m in getattr(c, "matches", ()) if getattr(m, "result", None) in ("1","X","2")),
        "mature_factors": len(mature),
    }
