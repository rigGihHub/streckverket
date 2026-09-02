from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Iterable, Optional, Sequence

CLUB_STOPWORDS = {
    "fc", "afc", "cf", "sc", "ac", "calcio", "football", "club",
    "the", "fk", "if", "bk", "sk", "united", "city", "town",
}

ALIASES = {
    "man utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "spurs": "tottenham hotspur",
    "tottenham": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "brighton": "brighton hove albion",
    "west brom": "west bromwich albion",
    "sheff utd": "sheffield united",
    "sheffield utd": "sheffield united",
    "sheff wed": "sheffield wednesday",
    "qpr": "queens park rangers",
    "psg": "paris saint germain",
    "inter": "internazionale",
    "inter milan": "internazionale",
    "ath madrid": "atletico madrid",
    "atleti": "atletico madrid",
    "bayern": "bayern munich",
    "bayern munchen": "bayern munich",
    "gladbach": "borussia monchengladbach",
    "koln": "cologne",
}

@dataclass(frozen=True)
class TeamCandidate:
    team_id: int | str
    name: str
    competition: str = ""
    country: str = ""

@dataclass(frozen=True)
class TeamMatch:
    query: str
    candidate: Optional[TeamCandidate]
    score: float
    confidence: str
    reason: str
    alternatives: tuple[tuple[str, float], ...] = ()


def _ascii(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c))


def normalize_team_name(name: str) -> str:
    s = _ascii(name).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    if s in ALIASES:
        s = ALIASES[s]
    tokens = s.split()
    # Behåll 'united/city' i korta namn; ta endast bort generiska suffix/prefix.
    removable = {"fc", "afc", "cf", "sc", "ac", "football", "club", "fk"}
    tokens = [t for t in tokens if t not in removable]
    s = " ".join(tokens)
    return ALIASES.get(s, s)


def _token_score(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def similarity(query: str, candidate: str) -> float:
    a, b = normalize_team_name(query), normalize_team_name(candidate)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    tok = _token_score(a, b)
    containment = 1.0 if (a in b or b in a) and min(len(a), len(b)) >= 5 else 0.0
    return min(1.0, 0.58 * seq + 0.32 * tok + 0.10 * containment)


def match_team(
    query: str,
    candidates: Sequence[TeamCandidate],
    *,
    competition_hint: str = "",
    high_threshold: float = 0.90,
    review_threshold: float = 0.78,
    min_margin: float = 0.055,
) -> TeamMatch:
    ranked = []
    hint = (competition_hint or "").lower().strip()
    for c in candidates:
        score = similarity(query, c.name)
        if hint and c.competition and hint in c.competition.lower():
            score = min(1.0, score + 0.035)
        ranked.append((score, c))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return TeamMatch(query, None, 0.0, "Ingen", "Inga kandidater tillgängliga")
    best_score, best = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = best_score - second
    alternatives = tuple((c.name, round(s, 3)) for s, c in ranked[1:4])
    if best_score >= high_threshold and margin >= min_margin:
        return TeamMatch(query, best, best_score, "Hög", "Tydlig namnmatchning", alternatives)
    if best_score >= review_threshold:
        return TeamMatch(query, best, best_score, "Granska", "Rimlig men inte tillräckligt entydig matchning", alternatives)
    return TeamMatch(query, None, best_score, "Ingen", "För låg säkerhet för automatisk koppling", alternatives)


def match_coupon_teams(matches, candidates: Sequence[TeamCandidate], competition_hint: str = ""):
    out = []
    for m in matches:
        out.append({
            "match_number": m.number,
            "home": match_team(m.home, candidates, competition_hint=competition_hint),
            "away": match_team(m.away, candidates, competition_hint=competition_hint),
        })
    return out
