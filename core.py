from __future__ import annotations
from dataclasses import dataclass
from math import prod, log, exp
from typing import Dict, Iterable, List, Sequence, Tuple

SIGNS = ("1", "X", "2")
SUBSETS = [
    ("1",), ("X",), ("2",),
    ("1","X"), ("1","2"), ("X","2"),
    ("1","X","2"),
]

def normalize(values: Sequence[float]) -> Tuple[float, float, float]:
    total = float(sum(values))
    if total <= 0:
        raise ValueError("Summan måste vara > 0")
    out = tuple(float(v) / total for v in values)
    return out  # type: ignore

def market_probabilities(odds: Sequence[float]) -> Tuple[float, float, float]:
    """Tar bort bookmaker-marginal proportionellt från decimala 1X2-odds."""
    if len(odds) != 3 or any(float(o) <= 1 for o in odds):
        raise ValueError("Tre giltiga decimalodds > 1 krävs")
    implied = [1.0 / float(o) for o in odds]
    return normalize(implied)

def value_index(model: Sequence[float], public: Sequence[float]) -> Tuple[float, float, float]:
    vals = []
    for p, s in zip(model, public):
        vals.append(float("inf") if s <= 0 else float(p) / float(s))
    return tuple(vals)  # type: ignore

def overround(odds: Sequence[float]) -> float:
    return sum(1 / float(o) for o in odds) - 1.0

def entropy(probs: Sequence[float]) -> float:
    return -sum(p * log(p) for p in probs if p > 0)

def uncertainty_score(probs: Sequence[float]) -> float:
    # normaliserad entropi 0..1
    return entropy(probs) / log(3)

def classify_match(model: Sequence[float], public: Sequence[float]) -> str:
    m = dict(zip(SIGNS, model))
    s = dict(zip(SIGNS, public))
    best = max(SIGNS, key=m.get)
    best_p = m[best]
    best_gap = s[best] - best_p

    # tydlig felstreckning på lågstreckat utfall
    for sign in SIGNS:
        if s[sign] <= 0.18 and m[sign] >= 0.24 and m[sign] - s[sign] >= 0.08:
            return "Skrälläge"

    if best_p >= 0.70 and best_gap <= 0.08:
        return "Stark spik"
    if best_p >= 0.56 and (best_p - s[best]) >= 0.07:
        return "Värdespik"
    if s[best] - best_p >= 0.13 and s[best] >= 0.58:
        return "Fällan"
    if best_p >= 0.58 and best_gap >= 0.08:
        return "Riskspik"

    ordered = sorted(model, reverse=True)
    if ordered[0] + ordered[1] >= 0.78 and ordered[2] <= 0.22:
        return "Halvgardering"
    return "Helgardering"

def spike_score(model: Sequence[float], public: Sequence[float], market: Sequence[float]) -> Tuple[str, int]:
    m = dict(zip(SIGNS, model))
    s = dict(zip(SIGNS, public))
    mk = dict(zip(SIGNS, market))
    sign = max(SIGNS, key=m.get)
    p = m[sign]
    value = min(1.5, p / max(s[sign], 0.01))
    market_support = 1 - min(1, abs(p - mk[sign]) / 0.20)
    certainty = 1 - uncertainty_score(model)
    # sannolikhet dominerar; värde får inte slå ut säkra favoriter.
    raw = 100 * (0.58*p + 0.16*(value/1.5) + 0.16*market_support + 0.10*certainty)
    return sign, max(0, min(100, round(raw)))

def _objective_probs(model: Sequence[float], public: Sequence[float], strategy: str) -> Tuple[float,float,float]:
    if strategy == "MAX 13":
        return tuple(model)  # type: ignore
    if strategy == "VÄRDE":
        # Modellens p är fortfarande basen, men understreckning får måttlig vikt.
        weights = []
        for p, s in zip(model, public):
            ratio = min(3.0, p / max(s, 0.01))
            weights.append(p * (ratio ** 0.32))
        return normalize(weights)
    raise ValueError("Okänd strategi")

@dataclass
class MatchInput:
    number: int
    home: str
    away: str
    odds: Tuple[float,float,float]
    public: Tuple[float,float,float]
    model: Tuple[float,float,float]
    kickoff: str | None = None
    competition: str = ""

    @property
    def market(self):
        return market_probabilities(self.odds)

def optimize_system(
    matches: Sequence[MatchInput],
    max_rows: int,
    strategy: str = "MAX 13",
    locks: Dict[int, Tuple[str,...]] | None = None,
):
    """
    Global DP över systemets radmultiplikator.
    För MAX 13 maximeras produkten av täckt modellsannolikhet.
    Antagande: matchutfallen behandlas som oberoende.
    """
    locks = locks or {}
    if max_rows < 1:
        raise ValueError("Budget/rader måste vara minst 1")

    # state rows -> (log objective coverage, selections)
    states = {1: (0.0, [])}

    for match in matches:
        candidate_sets = [locks[match.number]] if match.number in locks else SUBSETS
        obj_probs = dict(zip(SIGNS, _objective_probs(match.model, match.public, strategy)))
        new_states = {}

        for rows, (score, selections) in states.items():
            for subset in candidate_sets:
                mult = len(subset)
                nr = rows * mult
                if nr > max_rows:
                    continue
                covered_obj = sum(obj_probs[s] for s in subset)
                if covered_obj <= 0:
                    continue
                ns = score + log(covered_obj)
                old = new_states.get(nr)
                if old is None or ns > old[0]:
                    new_states[nr] = (ns, selections + [tuple(subset)])

        # Dominansrensning: behåll state om inget billigare/equal state har högre score.
        best_so_far = -1e99
        pruned = {}
        for rows in sorted(new_states):
            sc, sels = new_states[rows]
            if sc > best_so_far + 1e-12:
                pruned[rows] = (sc, sels)
                best_so_far = sc
        states = pruned

    if not states:
        raise ValueError("Inget system ryms inom budgeten med valda låsningar")

    # välj högst objectivescore; vid lika score billigare system
    best_rows, (best_score, selections) = max(states.items(), key=lambda kv: (kv[1][0], -kv[0]))

    true_coverage = 1.0
    per_match_coverage = []
    public_row_mass = 1.0
    for match, subset in zip(matches, selections):
        md = dict(zip(SIGNS, match.model))
        pd = dict(zip(SIGNS, match.public))
        c = sum(md[s] for s in subset)
        pc = sum(pd[s] for s in subset)
        per_match_coverage.append(c)
        true_coverage *= c
        public_row_mass *= pc

    random_coverage = best_rows / (3 ** len(matches))
    return {
        "rows": best_rows,
        "selections": selections,
        "coverage": true_coverage,
        "random_coverage": random_coverage,
        "objective_score": exp(best_score),
        "per_match_coverage": per_match_coverage,
        "public_mass": public_row_mass,
    }

def best_upgrades(matches, current_rows, strategy="MAX 13", locks=None):
    current = optimize_system(matches, current_rows, strategy, locks)
    target = optimize_system(matches, current_rows * 2, strategy, locks)
    changed = []
    for m, a, b in zip(matches, current["selections"], target["selections"]):
        if a != b:
            changed.append((m.number, a, b))
    rel = (target["coverage"] / current["coverage"] - 1) if current["coverage"] > 0 else 0
    return current, target, changed, rel
