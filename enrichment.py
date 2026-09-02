from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
import requests

from evidence import make_signal
from performance import VenueForm, home_away_form_signal
from team_matching import TeamCandidate


@dataclass
class EnrichmentStatus:
    ok: bool
    source: str
    message: str
    updated_at: str


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def football_data_headers(api_key: str):
    return {"X-Auth-Token": api_key, "User-Agent": "Stryktips13/0.8.0"}


def fetch_football_data_teams(api_key: str, competition: str) -> tuple[list[TeamCandidate], EnrichmentStatus]:
    if not api_key.strip():
        return [], EnrichmentStatus(False, "football-data.org", "API-nyckel saknas", _now())
    url = f"https://api.football-data.org/v4/competitions/{competition}/teams"
    try:
        r = requests.get(url, headers=football_data_headers(api_key), timeout=12)
        r.raise_for_status()
        payload = r.json()
        teams = []
        comp_name = (payload.get("competition") or {}).get("name") or competition
        for t in payload.get("teams", []):
            if t.get("id") is not None and t.get("name"):
                teams.append(TeamCandidate(t["id"], t["name"], comp_name, ((t.get("area") or {}).get("name") or "")))
                short = t.get("shortName")
                if short and short != t["name"]:
                    teams.append(TeamCandidate(t["id"], short, comp_name, ((t.get("area") or {}).get("name") or "")))
        return teams, EnrichmentStatus(True, "football-data.org", f"Hämtade {len(teams)} namnposter för {comp_name}", _now())
    except Exception as exc:
        return [], EnrichmentStatus(False, "football-data.org", f"Kunde inte hämta lag: {type(exc).__name__}", _now())


def fetch_team_finished_matches(api_key: str, team_id: int | str, venue: str, limit: int = 12) -> tuple[list[dict], EnrichmentStatus]:
    venue = venue.upper()
    if venue not in {"HOME", "AWAY"}:
        raise ValueError("venue måste vara HOME eller AWAY")
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    params = {"status": "FINISHED", "venue": venue, "limit": int(limit)}
    try:
        r = requests.get(url, headers=football_data_headers(api_key), params=params, timeout=12)
        r.raise_for_status()
        return r.json().get("matches", []), EnrichmentStatus(True, "football-data.org", f"{len(r.json().get('matches', []))} {venue.lower()}matcher", _now())
    except Exception as exc:
        return [], EnrichmentStatus(False, "football-data.org", f"Matchhämtning misslyckades: {type(exc).__name__}", _now())


def summarize_team_form(matches: Sequence[dict], team_id: int | str) -> dict:
    points = goals_for = goals_against = played = 0
    weights = []
    weighted_points = weighted_gd = weight_sum = 0.0
    # Nyare matcher antas ligga sist eller först beroende på API; sortera på datum stigande och ge senaste störst vikt.
    ordered = sorted(matches, key=lambda m: m.get("utcDate") or "")
    for idx, m in enumerate(ordered):
        home = (m.get("homeTeam") or {}).get("id")
        away = (m.get("awayTeam") or {}).get("id")
        score = ((m.get("score") or {}).get("fullTime") or {})
        hg, ag = score.get("home"), score.get("away")
        if hg is None or ag is None or team_id not in {home, away}:
            continue
        is_home = team_id == home
        gf, ga = (hg, ag) if is_home else (ag, hg)
        p = 3 if gf > ga else 1 if gf == ga else 0
        # Mild recency weighting, max ~1.55x senaste mot äldsta vid 12 matcher.
        w = 1.0 + 0.05 * idx
        played += 1; points += p; goals_for += gf; goals_against += ga
        weighted_points += w * p; weighted_gd += w * (gf-ga); weight_sum += w
    if played == 0:
        return {"played":0,"ppg":1.35,"gd_pg":0.0,"weighted_ppg":1.35,"weighted_gd_pg":0.0}
    return {
        "played": played,
        "ppg": points/played,
        "gd_pg": (goals_for-goals_against)/played,
        "weighted_ppg": weighted_points/weight_sum,
        "weighted_gd_pg": weighted_gd/weight_sum,
    }


def form_signal_from_summaries(home: dict, away: dict, source: str = "football-data.org"):
    # Bygg VenueForm-kompatibla summeringar. Vi använder PPG/GD via syntetiska W/D/L endast
    # för att återanvända den konservativa shrinkage-logiken; påverkan förblir liten.
    def approx_form(d: dict) -> VenueForm:
        n=max(0,int(d.get("played",0)))
        ppg=float(d.get("weighted_ppg",1.35))
        gd=float(d.get("weighted_gd_pg",0.0))
        # Approximerade poängfördelningar räcker här eftersom venue_form_rating primärt använder PPG/GD.
        pts=max(0.0,min(3.0,ppg))*n
        wins=int(pts//3)
        rem=pts-3*wins
        draws=min(max(0,n-wins), int(round(rem)))
        losses=max(0,n-wins-draws)
        gf=max(0, int(round(max(0.0,gd)*n)))
        ga=max(0, int(round(max(0.0,-gd)*n)))
        return VenueForm(n,wins,draws,losses,gf,ga,0.5)
    sig=home_away_form_signal(approx_form(home), approx_form(away), source)
    return make_signal(
        "home_away_form",
        "Venue-form + målskillnad",
        sig.impact,
        reliability=0.88,
        source=source,
        sample_size=min(int(home.get("played",0)), int(away.get("played",0))),
        explanation=f"Hemma: {home.get('played',0)} matcher, viktad PPG {home.get('weighted_ppg',1.35):.2f}, GD/match {home.get('weighted_gd_pg',0):+.2f}. Borta: {away.get('played',0)} matcher, viktad PPG {away.get('weighted_ppg',1.35):.2f}, GD/match {away.get('weighted_gd_pg',0):+.2f}.",
    )
