from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import requests


@dataclass
class WeatherSnapshot:
    temperature_c: Optional[float]
    precipitation_mm: Optional[float]
    wind_kmh: Optional[float]
    weather_code: Optional[int]
    source: str


def fetch_open_meteo_forecast(latitude: float, longitude: float, kickoff_iso: str) -> WeatherSnapshot:
    """Nyckelfri väderadapter. kickoff_iso används som timme YYYY-MM-DDTHH:MM."""
    date = kickoff_iso[:10]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&hourly=temperature_2m,precipitation,wind_speed_10m,weather_code"
        f"&start_date={date}&end_date={date}&timezone=auto"
    )
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    payload = r.json()
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Väderkällan saknade timdata")
    target = kickoff_iso[:13]
    idx = min(range(len(times)), key=lambda i: abs(int(times[i][11:13]) - int(target[11:13])))
    return WeatherSnapshot(
        temperature_c=_safe_idx(hourly.get("temperature_2m"), idx),
        precipitation_mm=_safe_idx(hourly.get("precipitation"), idx),
        wind_kmh=_safe_idx(hourly.get("wind_speed_10m"), idx),
        weather_code=_safe_idx(hourly.get("weather_code"), idx),
        source="Open-Meteo",
    )


def _safe_idx(values, idx):
    if not isinstance(values, list) or idx >= len(values):
        return None
    return values[idx]


def fetch_api_football_injuries(api_key: str, fixture_id: int) -> Dict[str, Any]:
    if not api_key:
        raise ValueError("API-Football-nyckel saknas")
    r = requests.get(
        "https://v3.football.api-sports.io/injuries",
        params={"fixture": fixture_id},
        headers={"x-apisports-key": api_key},
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


def fetch_live_football_officials(api_key: str, match_id: str) -> Dict[str, Any]:
    if not api_key:
        raise ValueError("Live Football API-nyckel saknas")
    r = requests.get(
        "https://live-football-api.com/api/v1/officials",
        params={"api_key": api_key, "match_id": match_id},
        timeout=12,
    )
    r.raise_for_status()
    return r.json()

@dataclass
class TeamMatch:
    home: str
    away: str
    home_goals: int
    away_goals: int
    utc_date: str


def fetch_football_data_team_matches(api_key: str, team_id: int, *, venue: str, limit: int = 10) -> list[TeamMatch]:
    """football-data.org v4. Finished matches only, optionally HOME/AWAY."""
    if not api_key:
        raise ValueError("football-data.org API-nyckel saknas")
    venue = venue.upper()
    if venue not in {"HOME", "AWAY"}:
        raise ValueError("venue måste vara HOME eller AWAY")
    r = requests.get(
        f"https://api.football-data.org/v4/teams/{int(team_id)}/matches",
        params={"status":"FINISHED", "venue":venue, "limit":int(limit)},
        headers={"X-Auth-Token": api_key}, timeout=12,
    )
    r.raise_for_status(); payload=r.json(); out=[]
    for m in payload.get("matches", []):
        ft=(m.get("score") or {}).get("fullTime") or {}
        hg,ag=ft.get("home"),ft.get("away")
        if hg is None or ag is None: continue
        out.append(TeamMatch((m.get("homeTeam") or {}).get("name", ""),(m.get("awayTeam") or {}).get("name", ""),int(hg),int(ag),m.get("utcDate", "")))
    return out


def fetch_api_football_fixture_candidates(api_key: str, *, date: str, team_id: int | None = None) -> Dict[str, Any]:
    """Hämta fixtures från API-Football för ett datum, valfritt filtrerat på lag-ID."""
    if not api_key:
        raise ValueError("API-Football-nyckel saknas")
    params={"date": date}
    if team_id is not None:
        params["team"] = int(team_id)
    r=requests.get(
        "https://v3.football.api-sports.io/fixtures",
        params=params,
        headers={"x-apisports-key": api_key},
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


def fetch_api_football_lineups(api_key: str, fixture_id: int) -> Dict[str, Any]:
    """Bekräftade/publicerade lineups för en specifik fixture när leverantören har dem."""
    if not api_key:
        raise ValueError("API-Football-nyckel saknas")
    r=requests.get(
        "https://v3.football.api-sports.io/fixtures/lineups",
        params={"fixture": int(fixture_id)},
        headers={"x-apisports-key": api_key},
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


def fetch_open_meteo_historical(latitude: float, longitude: float, start_date: str, end_date: str) -> Dict[str, Any]:
    """Historiskt timväder via Open-Meteo Archive API, för senare backtest av lag-väder-interaktion."""
    r=requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude":latitude,"longitude":longitude,"start_date":start_date,"end_date":end_date,
            "hourly":"temperature_2m,precipitation,wind_speed_10m,weather_code","timezone":"UTC",
        }, timeout=15,
    )
    r.raise_for_status(); return r.json()
