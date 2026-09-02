from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Iterable, Sequence

import requests

from team_matching import TeamCandidate, TeamMatch, match_team


@dataclass(frozen=True)
class CompetitionRef:
    id: int | str
    code: str
    name: str
    country: str
    plan: str = ""


@dataclass(frozen=True)
class DiscoveryResult:
    query: str
    match: TeamMatch
    competition: CompetitionRef | None
    ambiguity: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def headers(api_key: str) -> dict:
    return {"X-Auth-Token": api_key, "User-Agent": "Stryktips13/1.1.0"}


def fetch_competitions(api_key: str, timeout: int = 12) -> list[CompetitionRef]:
    if not api_key.strip():
        return []
    r = requests.get("https://api.football-data.org/v4/competitions/", headers=headers(api_key), timeout=timeout)
    r.raise_for_status()
    out = []
    for c in r.json().get("competitions", []):
        area = c.get("area") or {}
        out.append(CompetitionRef(c.get("id"), c.get("code") or str(c.get("id")), c.get("name") or "", area.get("name") or "", c.get("plan") or ""))
    return [c for c in out if c.id is not None and c.name]


def fetch_competition_candidates(api_key: str, competition: CompetitionRef, timeout: int = 12) -> list[TeamCandidate]:
    url = f"https://api.football-data.org/v4/competitions/{competition.id}/teams"
    r = requests.get(url, headers=headers(api_key), timeout=timeout)
    r.raise_for_status()
    payload = r.json()
    out: list[TeamCandidate] = []
    for t in payload.get("teams", []):
        tid = t.get("id")
        if tid is None:
            continue
        country = ((t.get("area") or {}).get("name") or competition.country)
        for name in (t.get("name"), t.get("shortName"), t.get("tla")):
            if name:
                out.append(TeamCandidate(tid, str(name), competition.name, country))
    return out


def build_catalog(api_key: str, competitions: Sequence[CompetitionRef], *, max_competitions: int | None = None) -> tuple[list[TeamCandidate], dict[int | str, CompetitionRef], list[str]]:
    candidates: list[TeamCandidate] = []
    team_comp: dict[int | str, CompetitionRef] = {}
    errors: list[str] = []
    comps = list(competitions[:max_competitions] if max_competitions else competitions)
    for comp in comps:
        try:
            rows = fetch_competition_candidates(api_key, comp)
            candidates.extend(rows)
            for row in rows:
                team_comp.setdefault(row.team_id, comp)
        except Exception as exc:
            errors.append(f"{comp.name}: {type(exc).__name__}")
    return candidates, team_comp, errors


def discover_team(query: str, candidates: Sequence[TeamCandidate], team_competitions: dict[int | str, CompetitionRef]) -> DiscoveryResult:
    tm = match_team(query, candidates)
    comp = team_competitions.get(tm.candidate.team_id) if tm.candidate else None
    ambiguity = ""
    if tm.candidate:
        same_name = []
        for c in candidates:
            if c.team_id == tm.candidate.team_id:
                continue
            # only close candidates can create a country/competition ambiguity
            alt = match_team(query, [c], high_threshold=0.0, review_threshold=0.0, min_margin=0.0)
            if alt.score >= max(0.80, tm.score - 0.035):
                same_name.append(c)
        countries = {c.country for c in same_name if c.country}
        if countries and (tm.candidate.country not in countries or len(countries) > 1):
            ambiguity = "Liknande klubbar finns i flera länder/tävlingar – granska kontexten."
            if tm.confidence == "Hög":
                tm = TeamMatch(tm.query, tm.candidate, tm.score, "Granska", "Namnmatchningen är stark men klubbkontexten är tvetydig", tm.alternatives)
    return DiscoveryResult(query, tm, comp, ambiguity)


def discover_coupon(matches, candidates: Sequence[TeamCandidate], team_competitions: dict[int | str, CompetitionRef]):
    rows = []
    for m in matches:
        rows.append({
            "match_number": m.number,
            "home": discover_team(m.home, candidates, team_competitions),
            "away": discover_team(m.away, candidates, team_competitions),
        })
    return rows


class TeamMappingCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def remember(self, source_name: str, team_id: int | str, external_name: str, competition_id: int | str, competition_name: str, country: str) -> None:
        data = self.load()
        key = source_name.strip().lower()
        data[key] = {
            "source_name": source_name,
            "team_id": team_id,
            "external_name": external_name,
            "competition_id": competition_id,
            "competition_name": competition_name,
            "country": country,
            "approved_at": _now(),
        }
        self.save(data)

    def get(self, source_name: str) -> dict | None:
        return self.load().get(source_name.strip().lower())
