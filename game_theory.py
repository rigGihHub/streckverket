from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Sequence
from core import MatchInput, SIGNS


@dataclass(frozen=True)
class StrategicMatch:
    number: int
    home: str
    away: str
    public_favorite: str
    public_favorite_share: float
    crowd_concentration: float
    best_value_sign: str
    model_probability: float
    public_share: float
    value_ratio: float
    role: str


def normalized_entropy(values: Sequence[float]) -> float:
    """0 = fully concentrated, 1 = evenly distributed across available outcomes."""
    vals = [max(0.0, float(x)) for x in values]
    total = sum(vals)
    if total <= 0 or len(vals) <= 1:
        return 0.0
    probs = [x / total for x in vals if x > 0]
    entropy = -sum(p * log(p) for p in probs)
    return entropy / log(len(vals))


def strategic_match(match: MatchInput) -> StrategicMatch:
    fav_i = max(range(3), key=lambda i: match.public[i])
    candidates = []
    for i, sign in enumerate(SIGNS):
        model = float(match.model[i])
        public = float(match.public[i])
        candidates.append((model / max(public, 0.01), model, -public, sign, public))
    ratio, model, _, sign, public = max(candidates)
    concentration = 1.0 - normalized_entropy(match.public)

    # Decision labels are descriptive. They are not claims of profitable equilibrium play.
    if sign != SIGNS[fav_i] and model >= 0.20 and ratio >= 1.25:
        role = "MOTSTRÖMS MED STÖD"
    elif match.public[fav_i] >= 0.65 and float(match.model[fav_i]) + 0.08 < float(match.public[fav_i]):
        role = "FOLKET TRÄNGS"
    elif ratio >= 1.15:
        role = "RELATIVT VÄRDE"
    else:
        role = "INGEN TYDLIG SPELTEORISIGNAL"

    return StrategicMatch(
        number=match.number,
        home=match.home,
        away=match.away,
        public_favorite=SIGNS[fav_i],
        public_favorite_share=float(match.public[fav_i]),
        crowd_concentration=concentration,
        best_value_sign=sign,
        model_probability=model,
        public_share=public,
        value_ratio=ratio,
        role=role,
    )


def strategic_coupon_rows(matches: Sequence[MatchInput]) -> list[dict]:
    rows = []
    for m in matches:
        x = strategic_match(m)
        rows.append({
            "Match": x.number,
            "Matchen": f"{x.home}–{x.away}",
            "Folkets favorit": f"{x.public_favorite} ({x.public_favorite_share:.0%})",
            "Trängsel": round(x.crowd_concentration * 100),
            "Intressant tecken": x.best_value_sign,
            "Modell": f"{x.model_probability:.0%}",
            "Streck": f"{x.public_share:.0%}",
            "Relativt värde": round(x.value_ratio, 2),
            "Spelteoriläge": x.role,
        })
    priority = {"MOTSTRÖMS MED STÖD": 0, "FOLKET TRÄNGS": 1, "RELATIVT VÄRDE": 2, "INGEN TYDLIG SPELTEORISIGNAL": 3}
    return sorted(rows, key=lambda r: (priority[r["Spelteoriläge"]], -float(r["Relativt värde"])))
