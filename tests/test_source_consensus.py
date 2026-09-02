from datetime import datetime, timezone

from source_consensus import SourceProfile, Observation, resolve_consensus, freshness_factor

NOW = datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)

def src(name, group, rel=.8, official=False):
    return SourceProfile(name, "test", group, rel, official)

def obs(value, source, time="2026-09-01T17:30:00+00:00"):
    return Observation("injury:player1", value, source, time, 1.0, True)

def test_duplicate_publishers_same_group_do_not_fake_corroboration():
    a = src("Site A", "wire_copy", .8)
    b = src("Site B", "wire_copy", .8)
    r = resolve_consensus([obs("OUT", a), obs("OUT", b)], now=NOW)
    assert r.independent_groups == 1
    assert not r.usable_for_model

def test_two_independent_sources_can_be_usable():
    a = src("API", "api", .9)
    b = src("Club", "club", .98, official=True)
    r = resolve_consensus([obs("OUT", a), obs("OUT", b)], now=NOW)
    assert r.independent_groups == 2
    assert r.value == "OUT"
    assert r.usable_for_model
    assert r.label in {"Medel", "Hög"}

def test_official_source_can_stand_on_its_own_when_fresh():
    club = src("Club", "club", .99, official=True)
    r = resolve_consensus([obs("OUT", club)], now=NOW)
    assert r.usable_for_model

def test_conflict_is_reported():
    a = src("API", "api", .9)
    b = src("Journalist", "journo", .85)
    r = resolve_consensus([obs("OUT", a), obs("AVAILABLE", b)], now=NOW)
    assert r.conflicts
    assert r.score < 0.72

def test_stale_data_decays():
    fresh = freshness_factor("2026-09-01T17:00:00+00:00", now=NOW, half_life_hours=12)
    old = freshness_factor("2026-08-30T18:00:00+00:00", now=NOW, half_life_hours=12)
    assert fresh > old
