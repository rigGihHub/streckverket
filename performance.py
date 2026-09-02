from __future__ import annotations
from dataclasses import dataclass
from math import log
from typing import Iterable, Sequence, Tuple
from core import normalize
from evidence import make_signal, EvidenceSignal

@dataclass(frozen=True)
class VenueForm:
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    opponent_strength: float = 0.5  # 0..1, 0.5 neutral

    @property
    def ppg(self) -> float:
        return (3*self.wins + self.draws) / max(1, self.matches)

    @property
    def goal_diff_per_game(self) -> float:
        return (self.goals_for - self.goals_against) / max(1, self.matches)


def shrink(value: float, sample: int, prior: float, prior_matches: int = 8) -> float:
    if sample < 0:
        raise ValueError('sample måste vara >= 0')
    return (value*sample + prior*prior_matches) / max(1, sample + prior_matches)


def venue_form_rating(form: VenueForm) -> float:
    """0..1-ish rating with conservative shrinkage. 0.5 is neutral."""
    ppg = shrink(form.ppg, form.matches, 1.35, 8)
    gd = shrink(form.goal_diff_per_game, form.matches, 0.0, 8)
    opp = min(1.0, max(0.0, form.opponent_strength))
    raw = 0.50 + 0.16*((ppg-1.35)/1.65) + 0.12*(max(-2,min(2,gd))/2) + 0.08*(opp-0.5)
    return min(0.9, max(0.1, raw))


def home_away_form_signal(home: VenueForm, away: VenueForm, source: str, updated_at: str | None = None) -> EvidenceSignal:
    h = venue_form_rating(home)
    a = venue_form_rating(away)
    edge = max(-1.0, min(1.0, (h-a)/0.35))
    sample = min(home.matches, away.matches)
    return make_signal(
        'home_away_form', 'Hemma-/bortaform',
        (0.34*edge, 0.05*abs(edge), -0.34*edge),
        reliability=0.9, source=source, updated_at=updated_at,
        sample_size=sample,
        explanation=(f'Hemma rating {h:.2f}, borta rating {a:.2f}; '
                     f'urval {home.matches}/{away.matches} matcher.'),
    )


def team_strength_signal(home_strength: float, away_strength: float, source: str, sample_size: int = 20) -> EvidenceSignal:
    """Strength inputs 0..1, ideally opposition-adjusted/xG/Elo based."""
    h = min(1,max(0,float(home_strength))); a=min(1,max(0,float(away_strength)))
    edge=max(-1,min(1,(h-a)/0.35))
    return make_signal('team_strength','Lagstyrka',(0.42*edge,0.03*abs(edge),-0.42*edge),0.92,source,
                       sample_size=sample_size,
                       explanation=f'Lagstyrka hemma {h:.2f}, borta {a:.2f}.')


def availability_signal(home_missing_value: float, away_missing_value: float, source: str, confirmed: bool=True) -> EvidenceSignal:
    """Missing value is a conservative 0..1 squad-impact estimate, not player count."""
    h=min(1,max(0,float(home_missing_value))); a=min(1,max(0,float(away_missing_value)))
    edge=max(-1,min(1,a-h))  # more away absences -> home edge
    return make_signal('injury_suspension','Verifierad spelarfrånvaro',(0.48*edge,0.06*abs(edge),-0.48*edge),
                       0.92 if confirmed else 0.0,source,is_verified=confirmed,
                       explanation=f'Frånvarovärde hemma {h:.2f}, borta {a:.2f}; baseras på betydelse, inte antal.')


def brier_score(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    if len(probabilities)!=len(outcomes) or not outcomes: raise ValueError('lika stora icke-tomma serier krävs')
    total=0.0
    for p,y in zip(probabilities,outcomes):
        p=normalize(p)
        total += sum((p[i]-(1.0 if i==y else 0.0))**2 for i in range(3))
    return total/len(outcomes)


def multiclass_log_loss(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    if len(probabilities)!=len(outcomes) or not outcomes: raise ValueError('lika stora icke-tomma serier krävs')
    return -sum(log(max(1e-12, normalize(p)[y])) for p,y in zip(probabilities,outcomes))/len(outcomes)
