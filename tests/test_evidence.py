from evidence import (
    adjust_probabilities, make_signal, data_quality,
    fan_sentiment_signal, weather_signal_from_history
)


def test_unverified_signal_does_not_move_model():
    base = (0.5, 0.3, 0.2)
    signal = make_signal("injury_suspension", "rykte", (-1,0,1), 1, "forum", is_verified=False)
    out, _ = adjust_probabilities(base, [signal])
    assert all(abs(a-b) < 1e-12 for a,b in zip(base,out))


def test_verified_injury_can_move_away_probability_up():
    base = (0.5,0.3,0.2)
    signal = make_signal("injury_suspension", "bekräftad frånvaro", (-0.5,0.1,0.5), 1, "official")
    out, _ = adjust_probabilities(base, [signal])
    assert out[0] < base[0]
    assert out[2] > base[2]
    assert abs(sum(out)-1) < 1e-12


def test_total_shift_is_capped():
    base=(0.34,0.33,0.33)
    signals=[make_signal("confirmed_lineup","x",(10,-10,-10),1,"official") for _ in range(4)]
    out,_=adjust_probabilities(base,signals,max_total_shift=0.10)
    moved=0.5*sum(abs(a-b) for a,b in zip(out,base))
    assert moved <= 0.1000001


def test_fan_sentiment_is_low_weight():
    s = fan_sentiment_signal(relative_sentiment_edge=1,post_count=1000,source="Reddit",explanation="test")
    assert s.weight <= 0.10
    assert s.effective_strength <= 0.10


def test_weather_small_sample_is_shrunk():
    small = weather_signal_from_history(
        home_points_per_game_condition=2.0, home_points_per_game_normal=1.2,
        away_points_per_game_condition=0.7, away_points_per_game_normal=1.4,
        sample_size=3, source="hist", explanation="x")
    large = weather_signal_from_history(
        home_points_per_game_condition=2.0, home_points_per_game_normal=1.2,
        away_points_per_game_condition=0.7, away_points_per_game_normal=1.4,
        sample_size=30, source="hist", explanation="x")
    assert small.effective_strength < large.effective_strength


def test_data_quality_counts_verified():
    sigs=[
        make_signal("team_strength","a",(0,0,0),1,"x"),
        make_signal("fan_sentiment","b",(0,0,0),1,"x",is_verified=False),
    ]
    q=data_quality(sigs)
    assert q["verified"] == 1
    assert q["total"] == 2
