from datetime import datetime, timezone
from source_registry import TeamSource, TeamRegistry, seed_from_football_data, registry_quality, normalize_domain
from club_intelligence import ClubClaim, assess_claims


def source(team, name, url, typ, origin=""):
    return TeamSource(team_key=team, name=name, url=url, source_type=typ, origin_group=origin)


def test_seed_official_site_from_football_data_payload():
    reg = seed_from_football_data({
        "id": 66,
        "name": "Manchester United FC",
        "area": {"name": "England"},
        "website": "https://www.manutd.com",
        "venue": "Old Trafford",
    })
    assert reg.external_team_ids["football_data"] == "66"
    assert len(reg.sources) == 1
    assert reg.sources[0].source_type == "official_club"
    assert reg.sources[0].domain == "manutd.com"


def test_same_publisher_subdomains_are_not_independent():
    a = source("t", "News A", "https://football.example.com/a", "national_media")
    b = source("t", "News B", "https://sport.example.com/b", "national_media")
    assert a.origin_group == b.origin_group == "example.com"


def test_registry_quality_rewards_source_diversity():
    reg = TeamRegistry(team_key="t", display_name="Team")
    reg.add_source(source("t", "Official", "https://team.example", "official_club"))
    reg.add_source(source("t", "Local", "https://localnews.example", "local_media"))
    reg.add_source(source("t", "Forum", "https://fans.example", "supporter_forum"))
    q = registry_quality(reg)
    assert q["score"] >= 70
    assert q["has_official"] and q["has_media"] and q["has_fan"]


def test_forum_claim_alone_is_not_model_usable():
    fan = source("t", "Forum", "https://fans.example", "supporter_forum")
    claims = [ClubClaim("t", "injury", "Player A", "out", fan, "2026-09-01T18:00:00Z")]
    a = assess_claims(claims, now=datetime(2026,9,1,20,tzinfo=timezone.utc))[0]
    assert not a.model_usable
    assert a.label == "Obekräftad"


def test_official_injury_can_be_model_usable():
    official = source("t", "Club", "https://club.example", "official_club")
    claims = [ClubClaim("t", "injury", "Player A", "out", official, "2026-09-01T19:30:00Z")]
    a = assess_claims(claims, now=datetime(2026,9,1,20,tzinfo=timezone.utc))[0]
    assert a.official_confirmation
    assert a.model_usable


def test_two_republishers_with_same_upstream_count_once():
    a = source("t", "Paper A", "https://a.example", "local_media")
    b = source("t", "Paper B", "https://b.example", "national_media")
    claims = [
        ClubClaim("t", "injury", "Player A", "out", a, "2026-09-01T19:30:00Z", upstream_origin="agency-x"),
        ClubClaim("t", "injury", "Player A", "out", b, "2026-09-01T19:35:00Z", upstream_origin="agency-x"),
    ]
    x = assess_claims(claims, now=datetime(2026,9,1,20,tzinfo=timezone.utc))[0]
    assert x.independent_origins == 1
    assert not x.model_usable


def test_conflict_blocks_model_use():
    club = source("t", "Club", "https://club.example", "official_club")
    media = source("t", "Local", "https://local.example", "local_media")
    claims = [
        ClubClaim("t", "lineup", "Player A", "starts", club, "2026-09-01T19:50:00Z"),
        ClubClaim("t", "lineup", "Player A", "bench", media, "2026-09-01T19:55:00Z"),
    ]
    a = assess_claims(claims, now=datetime(2026,9,1,20,tzinfo=timezone.utc))[0]
    assert a.conflict
    assert not a.model_usable
