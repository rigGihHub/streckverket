from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections import Counter
from typing import Sequence

from observation_quality import ObservationQuality, assess_observation_quality


@dataclass(frozen=True)
class CaptureQualityGate:
    status: str
    can_save: bool
    average_score: int
    verified_market_matches: int
    started_matches: int
    evidence_coverage: int
    message: str
    actions: tuple[str, ...]
    match_scores: tuple[int, ...]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _quality_for_match(match, captured_at: str) -> ObservationQuality:
    return assess_observation_quality(
        market_available=bool(getattr(match, "market_available", False)),
        captured_at=captured_at,
        kickoff=getattr(match, "kickoff", None),
        market_source=getattr(match, "market_source", ""),
        market_bookmaker_count=getattr(match, "market_bookmaker_count", None),
        market_last_update=getattr(match, "market_last_update", None),
        market_match_confidence=getattr(match, "market_match_confidence", None),
        public_last_update=getattr(match, "public_last_update", None),
    )


def assess_capture_quality(matches: Sequence[object], *, captured_at: str | None = None) -> CaptureQualityGate:
    """Assess whether a live coupon snapshot is suitable for facit/model history.

    This gate measures observation provenance and timing. It never uses which team
    the model prefers, the system selections, or eventual match outcomes.
    """
    now = _parse_dt(captured_at) or datetime.now(timezone.utc)
    timestamp = now.isoformat()
    qualities = [_quality_for_match(match, timestamp) for match in matches]

    if not qualities:
        return CaptureQualityGate(
            status="VÄNTA", can_save=False, average_score=0, verified_market_matches=0,
            started_matches=0, evidence_coverage=0,
            message="Ingen kupong finns att spara.", actions=("Hämta en riktig kupong först.",), match_scores=(),
        )

    verified = sum(bool(getattr(match, "market_available", False)) for match in matches)
    started = 0
    for match in matches:
        kickoff = _parse_dt(getattr(match, "kickoff", None))
        if kickoff is not None and kickoff <= now:
            started += 1

    avg_score = int(round(sum(q.score for q in qualities) / len(qualities)))
    avg_coverage = int(round(sum(q.evidence_coverage for q in qualities) / len(qualities)))

    missing_counts = Counter(item for q in qualities for item in q.missing)
    actions: list[str] = []

    if verified < len(matches):
        actions.append(f"Hämta verifierade bookmakerodds för {len(matches) - verified} match(er).")
    if missing_counts["oddsens färskhet"]:
        actions.append("Uppdatera odds nära sparögonblicket så att oddsens färskhet kan styrkas.")
    if missing_counts["antal bookmakers"]:
        actions.append("Använd en marknadskälla som anger hur många bookmakers som ingår.")
    if missing_counts["matchningssäkerhet för odds"]:
        actions.append("Säkerställ att bookmakeroddsen är kopplade till rätt fixture.")
    if missing_counts["streckens färskhet"]:
        actions.append("Spara tidsstämpel för Svenska Spels streck när källan kan styrka den.")
    if missing_counts["tid till avspark"]:
        actions.append("Komplettera avsparkstid där den saknas.")

    # Hard historical-integrity rules: a pre-match snapshot cannot be captured
    # after any known kickoff, and model-vs-market history requires real market
    # evidence for the whole 13-match coupon. Data-quality failures belong in the
    # separate data-quality history, not in the facit benchmark.
    if started:
        return CaptureQualityGate(
            status="SPARA INTE", can_save=False, average_score=avg_score,
            verified_market_matches=verified, started_matches=started,
            evidence_coverage=avg_coverage,
            message=f"{started} match(er) har redan startat. Den här kupongen är inte längre en ren pre-match-observation.",
            actions=("Vänta till nästa kupong för en ny pre-match-snapshot.",),
            match_scores=tuple(q.score for q in qualities),
        )

    if len(matches) != 13:
        return CaptureQualityGate(
            status="SPARA INTE", can_save=False, average_score=avg_score,
            verified_market_matches=verified, started_matches=0,
            evidence_coverage=avg_coverage,
            message=f"Kupongen innehåller {len(matches)} matcher. Facithistoriken kräver exakt 13.",
            actions=("Hämta om den verifierade Stryktipskupongen.",),
            match_scores=tuple(q.score for q in qualities),
        )

    if verified != 13:
        return CaptureQualityGate(
            status="VÄNTA", can_save=False, average_score=avg_score,
            verified_market_matches=verified, started_matches=0,
            evidence_coverage=avg_coverage,
            message=f"Verifierad bookmakerbas finns för {verified}/13 matcher. Facithistoriken väntar för att inte blanda in fallback-data.",
            actions=tuple(actions[:4]) or ("Uppdatera bookmakerdata och försök igen.",),
            match_scores=tuple(q.score for q in qualities),
        )

    if avg_score >= 80:
        status = "BRA"
        message = "Bra observationsunderlag. Den här snapshoten är lämplig att spara i facithistoriken."
    elif avg_score >= 60:
        status = "GODKÄND"
        message = "Godkänt observationsunderlag. Snapshoten kan sparas, men metadata kan förbättras."
    else:
        status = "SVAG"
        message = "Alla 13 bookmakerbaser är verifierade, men observationsmetadata är svag. Snapshoten får sparas och märks med låg kvalitet."

    return CaptureQualityGate(
        status=status, can_save=True, average_score=avg_score,
        verified_market_matches=verified, started_matches=0,
        evidence_coverage=avg_coverage, message=message,
        actions=tuple(actions[:4]), match_scores=tuple(q.score for q in qualities),
    )
