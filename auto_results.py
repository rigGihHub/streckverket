from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping, Sequence


def _norm(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|afc|cf|ac|sc|the)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    aliases = {
        "man utd": "manchester united", "man united": "manchester united",
        "man city": "manchester city", "spurs": "tottenham hotspur",
        "sheff utd": "sheffield united", "sheff wed": "sheffield wednesday",
        "qpr": "queens park rangers", "wolves": "wolverhampton wanderers",
        "west brom": "west bromwich albion", "nottm forest": "nottingham forest",
    }
    s = " ".join(s.split())
    return aliases.get(s, s)


def similarity(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def outcome_from_goals(home: Any, away: Any) -> str | None:
    if home is None or away is None:
        return None
    h, a = int(home), int(away)
    return "1" if h > a else "2" if a > h else "X"


@dataclass(frozen=True)
class ResultMatch:
    match_number: int
    result: str | None
    status: str
    provider_fixture_id: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    confidence: float = 0.0
    message: str = ""


def resolve_api_football_payload(matches: Sequence[Any], payload: Mapping[str, Any], *, min_score: float = 0.88, min_margin: float = 0.04) -> Dict[int, ResultMatch]:
    fixtures = list(payload.get("response", [])) if isinstance(payload, Mapping) else []
    out: Dict[int, ResultMatch] = {}
    for match in matches:
        candidates = []
        for item in fixtures:
            teams = item.get("teams") or {}
            hs = similarity(match.home, (teams.get("home") or {}).get("name") or "")
            aas = similarity(match.away, (teams.get("away") or {}).get("name") or "")
            score = 0.55 * min(hs, aas) + 0.45 * ((hs + aas) / 2)
            candidates.append((score, item))
        candidates.sort(key=lambda x: x[0], reverse=True)
        if not candidates:
            out[match.match_number] = ResultMatch(match.match_number, None, "saknas", message="Ingen match hittades hos resultatkällan.")
            continue
        score, item = candidates[0]
        margin = score - (candidates[1][0] if len(candidates) > 1 else 0.0)
        if score < min_score or margin < min_margin:
            out[match.match_number] = ResultMatch(match.match_number, None, "granska", confidence=score, message="Matchningen är inte tillräckligt säker för automatisk registrering.")
            continue
        fixture = item.get("fixture") or {}
        status = ((fixture.get("status") or {}).get("short") or "").upper()
        goals = item.get("goals") or {}
        finished = status in {"FT", "AET", "PEN"}
        if not finished:
            out[match.match_number] = ResultMatch(match.match_number, None, "ej_klar", int(fixture["id"]) if fixture.get("id") is not None else None, confidence=score, message="Matchen är hittad men inte slutrapporterad ännu.")
            continue
        h, a = goals.get("home"), goals.get("away")
        result = outcome_from_goals(h, a)
        out[match.match_number] = ResultMatch(
            match.match_number, result, "klar",
            int(fixture["id"]) if fixture.get("id") is not None else None,
            int(h) if h is not None else None, int(a) if a is not None else None,
            score, "Slutresultat hittat och matchat med hög säkerhet." if result else "Slutresultat saknar målsiffror.",
        )
    return out


def fetch_api_football_by_date(api_key: str, date: str, timeout: int = 15) -> dict[str, Any]:
    if not str(api_key).strip():
        raise ValueError("API-Football-nyckel saknas")
    import requests
    r = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": str(api_key).strip()},
        params={"date": date}, timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def kickoff_date(value: str | None) -> str | None:
    if not value:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    return m.group(1) if m else None


def fetch_coupon_results(coupon: Any, api_key: str, *, fetcher=fetch_api_football_by_date) -> tuple[Dict[int, str], list[ResultMatch]]:
    dates = sorted({d for m in coupon.matches if (d := kickoff_date(getattr(m, "kickoff", None)))})
    if not dates:
        return {}, [ResultMatch(m.match_number, None, "saknar_datum", message="Den sparade matchen saknar avsparkstid/datum.") for m in coupon.matches]
    all_resolved: Dict[int, ResultMatch] = {}
    for date in dates:
        subset = [m for m in coupon.matches if kickoff_date(getattr(m, "kickoff", None)) == date]
        payload = fetcher(api_key, date)
        all_resolved.update(resolve_api_football_payload(subset, payload))
    results = {n: r.result for n, r in all_resolved.items() if r.status == "klar" and r.result is not None}
    return results, [all_resolved.get(m.match_number, ResultMatch(m.match_number, None, "saknas")) for m in coupon.matches]
