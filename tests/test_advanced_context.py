from advanced_context import (
    VenueContext, extract_api_football_fixture_context, build_referee_profile,
    referee_matchup_signal, ForumPost, analyze_forum_posts, supporter_sentiment_model_signal,
)


def test_extract_fixture_context():
    venue, ref = extract_api_football_fixture_context({"fixture":{"venue":{"name":"Emirates Stadium","city":"London"},"referee":"A. Ref"}})
    assert venue.name == "Emirates Stadium"
    assert venue.city == "London"
    assert ref and ref.name == "A. Ref"


def test_referee_profile_and_signal_shrunk():
    rows=[]
    for i in range(10):
        rows.append({"fixture":{"referee":"A. Ref"},"goals":{"home":2 if i<6 else 0,"away":0 if i<6 else (0 if i<8 else 1)}})
    p=build_referee_profile(rows,"A. Ref")
    assert p.matches == 10
    sig=referee_matchup_signal(p,league_home_win_rate=.45)
    assert sig.sample_size == 10
    assert sig.effective_strength > 0


def test_forum_radar_not_verified_by_itself():
    posts=[ForumPost("Star striker injured and out", "terrible news", 0, 10, 5, "Reddit r/test") for _ in range(5)]
    r=analyze_forum_posts(posts)
    assert r.injury_mentions == 5
    assert r.weighted_sentiment < 0
    sig=supporter_sentiment_model_signal(r,independently_verified=False)
    assert sig.effective_strength == 0
