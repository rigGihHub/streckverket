from dataclasses import dataclass

from decision_highlights import build_decision_highlights

@dataclass
class M:
    number: int
    home: str
    away: str
    model: tuple
    public: tuple


def test_highlights_identify_spike_guard_and_public_trap():
    matches = [
        M(1,'A','B',(0.68,0.19,0.13),(0.55,0.25,0.20)),
        M(2,'C','D',(0.38,0.34,0.28),(0.39,0.33,0.28)),
        M(3,'E','F',(0.42,0.30,0.28),(0.62,0.21,0.17)),
    ]
    out = build_decision_highlights(matches, [('1',),('1','X','2'),('X','2')])
    roles = {x.role for x in out}
    assert 'VIKTIGASTE SPIKEN' in roles
    assert 'VIKTIGASTE GARDERINGEN' in roles
    assert 'MATCHEN SOM KAN FÄLLA MÅNGA' in roles


def test_no_trap_claim_when_public_model_gap_is_small():
    matches = [
        M(1,'A','B',(0.52,0.28,0.20),(0.54,0.27,0.19)),
        M(2,'C','D',(0.40,0.34,0.26),(0.41,0.34,0.25)),
    ]
    out = build_decision_highlights(matches, [('1',),('1','X')])
    assert all(x.role != 'MATCHEN SOM KAN FÄLLA MÅNGA' for x in out)


def test_highlights_never_change_selections():
    matches = [M(1,'A','B',(0.7,0.2,0.1),(0.6,0.25,0.15))]
    selections = [('1',)]
    before = tuple(selections)
    build_decision_highlights(matches, selections)
    assert tuple(selections) == before
