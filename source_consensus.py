from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class SourceProfile:
    name: str
    source_type: str
    independence_group: str
    base_reliability: float
    official: bool = False


@dataclass(frozen=True)
class Observation:
    claim_key: str
    value: str
    source: SourceProfile
    updated_at: Optional[str] = None
    confidence: float = 1.0
    direct: bool = True


@dataclass(frozen=True)
class ConsensusResult:
    claim_key: str
    value: Optional[str]
    score: float
    label: str
    independent_groups: int
    agreeing_sources: int
    conflicts: tuple[str, ...]
    usable_for_model: bool


DEFAULT_SOURCES: dict[str, SourceProfile] = {
    "svenska_spel": SourceProfile("Svenska Spel", "coupon", "svenska_spel", 0.95, True),
    "football_data": SourceProfile("football-data.org", "stats", "football_data", 0.82),
    "api_football": SourceProfile("API-Football", "team_news", "api_football", 0.84),
    "the_odds_api": SourceProfile("The Odds API", "odds_aggregator", "odds_market", 0.90),
    "open_meteo": SourceProfile("Open-Meteo", "weather", "weather_model", 0.88),
    "club_official": SourceProfile("Official club source", "club_news", "club_official", 0.98, True),
    "league_official": SourceProfile("Official league source", "competition_news", "league_official", 0.97, True),
    "supporter_forum": SourceProfile("Supporter forum", "sentiment", "fan_social", 0.35),
    "independent_journalist": SourceProfile("Independent journalist", "news", "journalist", 0.67),
}


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def freshness_factor(updated_at: Optional[str], *, now: Optional[datetime] = None, half_life_hours: float = 24.0) -> float:
    """Exponential freshness decay, intentionally forgiving for stable facts."""
    if not updated_at:
        return 0.70
    dt = _parse_time(updated_at)
    if not dt:
        return 0.60
    now = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
    if half_life_hours <= 0:
        return 1.0
    return 0.5 ** (age_hours / half_life_hours)


def observation_weight(obs: Observation, *, now: Optional[datetime] = None, half_life_hours: float = 24.0) -> float:
    direct_factor = 1.0 if obs.direct else 0.82
    return max(0.0, min(1.0,
        obs.source.base_reliability
        * max(0.0, min(1.0, obs.confidence))
        * freshness_factor(obs.updated_at, now=now, half_life_hours=half_life_hours)
        * direct_factor
    ))


def resolve_consensus(observations: Iterable[Observation], *, now: Optional[datetime] = None, half_life_hours: float = 24.0) -> ConsensusResult:
    obs = list(observations)
    if not obs:
        return ConsensusResult("", None, 0.0, "Saknas", 0, 0, (), False)
    claim_key = obs[0].claim_key
    if any(o.claim_key != claim_key for o in obs):
        raise ValueError("Alla observationer måste avse samma claim_key")

    # Prevent source cloning: within one independence group, only the strongest source counts per value.
    grouped: dict[tuple[str, str], float] = {}
    source_counts: dict[str, set[str]] = {}
    official_support: dict[str, bool] = {}
    for o in obs:
        w = observation_weight(o, now=now, half_life_hours=half_life_hours)
        key = (o.value, o.source.independence_group)
        grouped[key] = max(grouped.get(key, 0.0), w)
        source_counts.setdefault(o.value, set()).add(o.source.name)
        official_support[o.value] = official_support.get(o.value, False) or o.source.official

    value_scores: dict[str, float] = {}
    value_groups: dict[str, set[str]] = {}
    for (value, group), w in grouped.items():
        value_scores[value] = value_scores.get(value, 0.0) + w
        value_groups.setdefault(value, set()).add(group)

    best_value = max(value_scores, key=value_scores.get)
    best_score = value_scores[best_value]
    total = sum(value_scores.values())
    normalized = 0.0 if total <= 0 else best_score / total
    groups = len(value_groups.get(best_value, set()))
    agreeing_sources = len(source_counts.get(best_value, set()))
    conflicts = tuple(sorted(v for v in value_scores if v != best_value and value_scores[v] >= 0.20))

    # Confidence rewards independent corroboration and official confirmation; conflicts reduce it.
    corroboration = min(1.0, 0.55 + 0.18 * max(0, groups - 1))
    if official_support.get(best_value):
        corroboration = min(1.0, corroboration + 0.18)
    score = max(0.0, min(1.0, normalized * corroboration))
    if conflicts:
        score *= 0.82

    label = "Hög" if score >= 0.72 else "Medel" if score >= 0.48 else "Låg"
    usable = bool(score >= 0.55 and (groups >= 2 or official_support.get(best_value)))
    return ConsensusResult(
        claim_key=claim_key,
        value=best_value,
        score=score,
        label=label,
        independent_groups=groups,
        agreeing_sources=agreeing_sources,
        conflicts=conflicts,
        usable_for_model=usable,
    )


def provider_matrix() -> list[dict[str, str]]:
    return [
        {"Signal": "Kupong / streck", "Primär": "Svenska Spel", "Sekundär": "Snapshot/historik", "Regel": "Primärkällan styr; ändringar tidsstämplas"},
        {"Signal": "Odds", "Primär": "The Odds API / flera bookmakers", "Sekundär": "Svenska Spels odds", "Regel": "Median/robust aggregat; bookmaker-spridning visas"},
        {"Signal": "Matcher / tabell / form", "Primär": "football-data.org", "Sekundär": "API-Football", "Regel": "Konflikt flaggas; venue och motståndsstyrka bevaras"},
        {"Signal": "Skador / avstängningar", "Primär": "API-Football", "Sekundär": "Klubb/ligakälla", "Regel": "Forumrykte påverkar inte modellen utan verifiering"},
        {"Signal": "Startelva", "Primär": "Officiell klubb/liga", "Sekundär": "API-Football", "Regel": "Bekräftad lineup väger högre än predicted XI"},
        {"Signal": "Väder", "Primär": "Open-Meteo Best Match", "Sekundär": "ECMWF/Open-Meteo modellkontroll", "Regel": "Själva vädret är kontext; effekt kräver historiskt stöd"},
        {"Signal": "Supportersentiment", "Primär": "Flera forum/community-källor", "Sekundär": "Journalist/klubbverifiering", "Regel": "Early warning; mycket låg direkt modellvikt"},
        {"Signal": "Domare", "Primär": "Officiell tävling / matchdata", "Sekundär": "Statistikkälla", "Regel": "Matchup-effekt backtestas; kortsnitt ensamt räcker inte"},
    ]
