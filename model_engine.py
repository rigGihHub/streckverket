from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import requests

from core import normalize
from evidence import EvidenceSignal, adjust_probabilities, make_signal
from performance import availability_signal, team_strength_signal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class StandingStrength:
    team_id: int | str
    team_name: str
    played: int
    points: int
    goals_for: int
    goals_against: int
    position: int | None
    strength: float
    source: str = "football-data.org"


@dataclass(frozen=True)
class Absence:
    player: str
    team_id: int | str | None
    status: str
    reason: str
    importance: float
    replacement_quality: float
    verified: bool

    @property
    def impact(self) -> float:
        if not self.verified:
            return 0.0
        imp=max(0.0,min(1.0,float(self.importance)))
        repl=max(0.0,min(1.0,float(self.replacement_quality)))
        return imp * (1.0 - repl)


def football_data_headers(api_key: str) -> dict:
    return {"X-Auth-Token": api_key, "User-Agent": "Stryktips13/1.1.0"}


def fetch_competition_standings(api_key: str, competition_id: int | str, timeout: int = 12) -> tuple[dict[int | str, StandingStrength], str]:
    if not api_key.strip():
        raise ValueError("football-data.org API-nyckel saknas")
    url=f"https://api.football-data.org/v4/competitions/{competition_id}/standings"
    r=requests.get(url, headers=football_data_headers(api_key), timeout=timeout)
    r.raise_for_status()
    payload=r.json()
    tables=payload.get("standings", [])
    total=next((x for x in tables if x.get("type") == "TOTAL"), tables[0] if tables else None)
    if not total:
        return {}, _now()
    rows=total.get("table", [])
    if not rows:
        return {}, _now()
    # Strength is intentionally simple and conservative: shrink points/game and goal difference
    # toward neutral, then map to 0..1. This is not presented as Elo/xG.
    out={}
    for row in rows:
        team=row.get("team") or {}
        tid=team.get("id")
        if tid is None:
            continue
        played=max(0,int(row.get("playedGames") or 0))
        points=int(row.get("points") or 0)
        gf=int(row.get("goalsFor") or 0)
        ga=int(row.get("goalsAgainst") or 0)
        ppg=points/max(1,played)
        gd=(gf-ga)/max(1,played)
        # Bayesian-ish shrinkage against 8 neutral matches.
        ppg_s=(ppg*played + 1.35*8)/max(1,played+8)
        gd_s=(gd*played + 0.0*8)/max(1,played+8)
        strength=0.50 + 0.24*((ppg_s-1.35)/1.65) + 0.16*(max(-2.0,min(2.0,gd_s))/2.0)
        strength=max(0.08,min(0.92,strength))
        out[tid]=StandingStrength(
            tid, team.get("name") or str(tid), played, points, gf, ga,
            int(row.get("position")) if row.get("position") is not None else None,
            strength,
        )
    return out, _now()


def parse_api_football_injuries(payload: Mapping[str, Any], *, importance_by_player: Mapping[str, float] | None = None, replacement_quality_by_player: Mapping[str, float] | None = None) -> list[Absence]:
    importance_by_player=importance_by_player or {}
    replacement_quality_by_player=replacement_quality_by_player or {}
    out=[]
    for item in payload.get("response", []) if isinstance(payload, Mapping) else []:
        player=item.get("player") or {}
        team=item.get("team") or {}
        name=str(player.get("name") or "Okänd spelare")
        reason=str(player.get("reason") or item.get("reason") or "")
        typ=str(player.get("type") or item.get("type") or "")
        status=(typ + (": " + reason if reason else "")).strip(": ")
        # API presence is treated as source verification, but player importance remains conservative/default low.
        imp=float(importance_by_player.get(name, 0.35))
        repl=float(replacement_quality_by_player.get(name, 0.65))
        out.append(Absence(name, team.get("id"), status, reason, imp, repl, True))
    return out


def missing_value(absences: Iterable[Absence], team_id: int | str | None = None) -> float:
    vals=[]
    for a in absences:
        if team_id is not None and a.team_id != team_id:
            continue
        vals.append(a.impact)
    # Multiple absences combine sub-additively, avoiding silly >100% squad damage.
    remaining=1.0
    for v in sorted(vals, reverse=True):
        remaining *= (1.0 - min(0.45,v))
    return max(0.0,min(1.0,1.0-remaining))


def build_match_signals(
    *,
    home_strength: float | None = None,
    away_strength: float | None = None,
    home_missing: float | None = None,
    away_missing: float | None = None,
    form_signal: EvidenceSignal | None = None,
    source_strength: str = "football-data.org",
    source_absence: str = "API-Football",
    absence_verified: bool = True,
) -> list[EvidenceSignal]:
    signals=[]
    if home_strength is not None and away_strength is not None:
        signals.append(team_strength_signal(home_strength, away_strength, source_strength, sample_size=20))
    if home_missing is not None and away_missing is not None:
        signals.append(availability_signal(home_missing, away_missing, source_absence, confirmed=absence_verified))
    if form_signal is not None:
        signals.append(form_signal)
    return signals


def enriched_probabilities(base_market: Sequence[float], signals: Iterable[EvidenceSignal], max_total_shift: float = 0.14):
    """Conservative v0.8 cap: external context may move at most 14 percentage points total probability mass."""
    adjusted, audit=adjust_probabilities(base_market, signals, max_total_shift=max_total_shift)
    base=normalize(base_market)
    for row in audit:
        row["base"] = tuple(base)
        row["final"] = tuple(adjusted)
    return adjusted, audit


def probability_delta(base: Sequence[float], final: Sequence[float]) -> tuple[float,float,float]:
    b=normalize(base); f=normalize(final)
    return tuple(fi-bi for bi,fi in zip(b,f))
