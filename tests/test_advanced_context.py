from advanced_context import (
    VenueContext, extract_api_football_fixture_context, build_referee_profile,
    referee_matchup_signal, ForumPost, analyze_forum_posts, supporter_sentiment_model_signal,
    analyze_supporter_pulse, supporter_pulse_model_signal,
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


def test_supporter_pulse_distinguishes_resignation_from_confidence():
    resigned=[ForumPost("No chance, season over", "hopeless and worried", 0, 5, 2, "Reddit r/test", author=f"u{i}") for i in range(10)]
    confident=[ForumPost("We will win", "confident, strong, good feeling", 0, 5, 2, "Reddit r/test", author=f"c{i}") for i in range(10)]
    r=analyze_supporter_pulse(resigned)
    c=analyze_supporter_pulse(confident)
    assert r.resignation > r.confidence
    assert c.confidence > c.resignation
    assert r.label in {"Uppgiven", "Orolig"}
    assert c.label == "Självsäker"

def test_supporter_pulse_tracks_consensus_and_tone_delta():
    posts=[ForumPost("We will win", "confident and strong", 0, 1, 0, "Forum", author=f"u{i}") for i in range(12)]
    p=analyze_supporter_pulse(posts, baseline_tone=-0.2)
    assert p.unique_authors == 12
    assert p.consensus > 0.9
    assert p.tone_delta is not None and p.tone_delta > 0

def test_supporter_pulse_cannot_move_model_without_history_validation():
    posts=[ForumPost("We will win", "confident strong positive", 0, 10, 5, "Forum", author=f"u{i}") for i in range(30)]
    p=analyze_supporter_pulse(posts)
    blocked=supporter_pulse_model_signal(p, independently_verified=True, historically_validated=False)
    assert blocked.effective_strength == 0
