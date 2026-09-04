from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from core import normalize
from evidence import EvidenceSignal, adjust_probabilities

SIGNS = ("1", "X", "2")
CATEGORY_NAMES = {
    "market_move": "Förändring i oddsen",
    "confirmed_lineup": "Bekräftad startelva",
    "injury_suspension": "Skador och avstängningar",
    "team_strength": "Lagens grundstyrka",
    "home_away_form": "Hemma- och bortaform",
    "rest_schedule": "Vila och spelschema",
    "manager_change": "Tränarbyte",
    "referee": "Domare",
    "weather": "Väder",
    "travel": "Resa",
    "fan_sentiment": "Supporterinformation",
    "motivation": "Motivation",
}

@dataclass(frozen=True)
class FactorContribution:
    category: str
    name: str
    source: str
    verified: bool
    strength: float
    delta: tuple[float, float, float]
    explanation: str


def explain_probability_change(base: Sequence[float], signals: Iterable[EvidenceSignal], *, max_total_shift: float = 0.14):
    """Förklarar modellflytten steg för steg.

    Bidragen är sekventiella och summerar därför exakt till modellens slutliga
    förändring. Ordningen följer signalordningen. Ogranskade signaler får 0 effekt.
    """
    base = normalize(base)
    current = base
    rows: list[FactorContribution] = []
    accepted: list[EvidenceSignal] = []
    for signal in signals:
        before = current
        accepted.append(signal)
        current, _ = adjust_probabilities(base, accepted, max_total_shift=max_total_shift)
        delta = tuple(a-b for a,b in zip(current, before))
        rows.append(FactorContribution(
            signal.category,
            CATEGORY_NAMES.get(signal.category, signal.category.replace("_", " ").capitalize()),
            signal.source or "Källa saknas",
            bool(signal.is_verified),
            float(signal.effective_strength),
            delta,
            signal.explanation or signal.label,
        ))
    return current, rows


def biggest_reason(rows: Sequence[FactorContribution], sign_index: int) -> FactorContribution | None:
    if not rows:
        return None
    return max(rows, key=lambda r: abs(r.delta[sign_index]))


def plain_delta(delta: float, sign: str) -> str:
    pp = delta * 100
    if abs(pp) < 0.05:
        return f"ändrar inte chansen för {sign} mätbart"
    direction = "ökar" if pp > 0 else "minskar"
    return f"{direction} vår uppskattning för {sign} med {abs(pp):.1f} procentenheter"


def plain_summary(base: Sequence[float], final: Sequence[float], rows: Sequence[FactorContribution], home: str, away: str) -> str:
    base = normalize(base); final = normalize(final)
    idx = max(range(3), key=lambda i: abs(final[i]-base[i]))
    sign = SIGNS[idx]
    meaning = home + " vinner" if sign == "1" else ("oavgjort" if sign == "X" else away + " vinner")
    total = (final[idx]-base[idx])*100
    reason = biggest_reason(rows, idx)
    if abs(total) < 0.05:
        return "Den verifierade informationen ändrar inte marknadens grundbedömning på ett mätbart sätt."
    verb = "högre" if total > 0 else "lägre"
    text = f"Efter den verifierade informationen bedömer Streckverket chansen för {meaning} {abs(total):.1f} procentenheter {verb} än marknadens utgångspunkt."
    if reason and abs(reason.delta[idx]) >= 0.0005:
        text += f" Den största enskilda förklaringen i beräkningen är {reason.name.lower()}."
    return text
