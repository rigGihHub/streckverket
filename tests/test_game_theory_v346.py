from core import MatchInput
from game_theory import normalized_entropy, strategic_match, strategic_coupon_rows


def m(public=(0.70,0.18,0.12), model=(0.52,0.27,0.21)):
    return MatchInput(1,"A","B",(2.0,3.2,4.5),public,model)


def test_entropy_even_public_is_one():
    assert abs(normalized_entropy((1,1,1))-1.0) < 1e-9


def test_entropy_concentrated_is_low():
    assert normalized_entropy((0.98,0.01,0.01)) < 0.12


def test_contrarian_signal_requires_probability_support():
    x = strategic_match(m())
    assert x.best_value_sign == "2"
    assert x.model_probability >= .20
    assert x.role == "MOTSTRÖMS MED STÖD"


def test_rare_outcome_not_rewarded_only_for_rarity():
    x = strategic_match(m(public=(.55,.44,.01), model=(.54,.45,.01)))
    assert x.best_value_sign != "2"


def test_rows_are_descriptive_not_profit_claims():
    rows = strategic_coupon_rows([m()])
    assert "Spelteoriläge" in rows[0]
    assert "vinst" not in " ".join(map(str, rows[0].values())).lower()
