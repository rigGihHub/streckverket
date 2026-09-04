from advanced_context import ForumPost
import supporter_sources as ss


def post(title, ts, url, author="u"):
    return ForumPost(title, "", ts, 1, 0, "Reddit r/coys", url=url, author=author)


def test_explicit_alias_mapping_never_guesses_unknown_team():
    sources = list(ss.DEFAULT_SOURCES)
    assert ss.sources_for_team("Spurs", sources)[0].locator == "coys"
    assert ss.sources_for_team("Tottenham", sources)[0].locator == "coys"
    assert ss.sources_for_team("Random United", sources) == []


def test_collection_deduplicates_and_blocks_post_kickoff(monkeypatch):
    now = 1_800_000_000.0
    kickoff = now - 600
    rows = [
        post("We will win", now - 3600, "https://x/1", "a"),
        post("We will win duplicate", now - 3500, "https://x/1", "a"),
        post("No chance", now - 1200, "https://x/2", "b"),
        post("Leak after kickoff", now - 300, "https://x/3", "c"),
    ]
    monkeypatch.setattr(ss, "fetch_reddit_subreddit_search", lambda *a, **k: rows)
    c = ss.collect_team_pulse(team="Tottenham", opponent="Arsenal", sources=list(ss.DEFAULT_SOURCES), now_ts=now, kickoff_ts=kickoff)
    assert c.pulse.posts == 2
    assert c.pulse.unique_authors == 2
    assert c.filtered_out >= 1


def test_baseline_requires_multiple_historical_snapshots():
    row = {"team":"Tottenham Hotspur","source":"Reddit r/coys","confidence":.5,"optimism":.5,"resignation":0,"worry":0,"anger":0}
    assert ss.baseline_tone([row, row], team="Spurs", source_name="Reddit r/coys") is None
    assert ss.baseline_tone([row, row, row], team="Spurs", source_name="Reddit r/coys") == 0.5


def test_collection_returns_source_missing_instead_of_guessing():
    c = ss.collect_team_pulse(team="Unknown FC", opponent="Other FC", sources=list(ss.DEFAULT_SOURCES), now_ts=1_800_000_000)
    assert not c.available
    assert c.source is None
    assert "Ingen verifierad" in c.status


def test_relevance_filter_prefers_match_context_and_rejects_noise():
    ts = 1_800_000_000.0
    rows = [
        post("Arsenal match: worried about the starting lineup", ts, "https://x/a", "a"),
        post("New retro kit collection and tickets", ts, "https://x/b", "b"),
        post("Confident we win this game", ts, "https://x/c", "c"),
    ]
    relevant, rate = ss.filter_relevant_posts(rows, team="Tottenham", opponent="Arsenal")
    assert [p.url for p in relevant] == ["https://x/a", "https://x/c"]
    assert 0.60 < rate < 0.70


def test_source_registry_expanded_only_with_explicit_mappings():
    sources = list(ss.DEFAULT_SOURCES)
    assert ss.sources_for_team("Arsenal", sources)[0].locator == "Gunners"
    assert ss.sources_for_team("Man Utd", sources)[0].locator == "reddevils"
    assert ss.sources_for_team("Chelsea FC", sources)[0].locator == "chelseafc"
    assert ss.sources_for_team("Unknown Town", sources) == []
