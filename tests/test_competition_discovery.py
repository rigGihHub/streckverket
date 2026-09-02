from pathlib import Path

from competition_discovery import CompetitionRef, TeamMappingCache, discover_team
from team_matching import TeamCandidate


def test_discovery_attaches_competition():
    comp = CompetitionRef(2021, "PL", "Premier League", "England")
    candidates = [TeamCandidate(66, "Manchester United FC", "Premier League", "England")]
    result = discover_team("Man Utd", candidates, {66: comp})
    assert result.match.candidate.team_id == 66
    assert result.competition.code == "PL"


def test_ambiguous_cross_country_forces_review():
    eng = CompetitionRef(1, "ENG", "Example England", "England")
    usa = CompetitionRef(2, "USA", "Example USA", "USA")
    candidates = [
        TeamCandidate(1, "United City", eng.name, eng.country),
        TeamCandidate(2, "United City FC", usa.name, usa.country),
    ]
    result = discover_team("United City", candidates, {1: eng, 2: usa})
    assert result.match.confidence == "Granska"


def test_cache_roundtrip(tmp_path):
    cache = TeamMappingCache(tmp_path / "teams.json")
    cache.remember("Man Utd", 66, "Manchester United FC", 2021, "Premier League", "England")
    row = cache.get("man utd")
    assert row["team_id"] == 66
    assert row["competition_name"] == "Premier League"
