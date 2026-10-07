from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class AnalysisTimingAdvice:
    headline: str
    message: str
    next_step: str
    tone: str
    hours_to_first_kickoff: float | None
    basis: str


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def analysis_timing_advice(matches: Iterable, *, now: datetime | None = None) -> AnalysisTimingAdvice:
    """Give a novice a conservative time-to-recheck message.

    The advice uses the earliest *known kickoff* as a timing proxy. It never
    claims that this is Svenska Spel's official betting deadline.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    kickoffs = [_parse_dt(getattr(m, "kickoff", None)) for m in matches]
    kickoffs = [dt for dt in kickoffs if dt is not None]
    basis = "Rådet bygger på tidigaste kända avspark, inte verifierat officiellt spelstopp."
    if not kickoffs:
        return AnalysisTimingAdvice(
            headline="TIDPUNKT OKÄND",
            message="Streckverket saknar en säker avsparkstid för kupongen och ska därför inte hitta på ett klockslag.",
            next_step="Gör en första analys nu och kontrollera kupongen igen senare innan du lämnar in.",
            tone="warning",
            hours_to_first_kickoff=None,
            basis=basis,
        )

    first = min(kickoffs)
    hours = (first - now).total_seconds() / 3600.0
    if hours <= 0:
        return AnalysisTimingAdvice(
            headline="MATCH HAR STARTAT",
            message="Minst en känd matchstart är passerad. Det här är inte längre en ren förmatchanalys.",
            next_step="Använd inte ett nytt pre-match-system som om hela kupongen fortfarande vore ospelad.",
            tone="error",
            hours_to_first_kickoff=hours,
            basis=basis,
        )
    if hours > 24:
        return AnalysisTimingAdvice(
            headline="TIDIG KOLL",
            message="Det är mer än ett dygn till tidigaste kända avspark. En analys nu är bra för överblick, men information kan ändras mycket.",
            next_step="Analysera nu om du vill planera systemet, men gör en ny kontroll närmare matchdagen.",
            tone="info",
            hours_to_first_kickoff=hours,
            basis=basis,
        )
    if hours > 6:
        return AnalysisTimingAdvice(
            headline="BRA LÄGE FÖR FÖRSTA ANALYS",
            message="Kupongen är nära nog för en användbar analys, men odds, skador och laginformation kan fortfarande ändras.",
            next_step="Analysera nu och gör en sista kontroll senare samma dag innan du spelar.",
            tone="info",
            hours_to_first_kickoff=hours,
            basis=basis,
        )
    if hours > 1:
        return AnalysisTimingAdvice(
            headline="SLUTLIG KONTROLL NÄRMAR SIG",
            message="Det är mindre än sex timmar till tidigaste kända avspark. Sena marknadsrörelser och laginfo kan nu vara mer relevanta.",
            next_step="Analysera nu. Om viktiga uppgifter fortfarande saknas, kontrollera en gång till närmare avspark.",
            tone="warning",
            hours_to_first_kickoff=hours,
            basis=basis,
        )
    return AnalysisTimingAdvice(
        headline="GÖR SLUTLIG KONTROLL NU",
        message="Det är mindre än en timme till tidigaste kända avspark.",
        next_step="Uppdatera analysen nu och undvik att vänta så länge att du riskerar att missa det riktiga spelstoppet.",
        tone="warning",
        hours_to_first_kickoff=hours,
        basis=basis,
    )
