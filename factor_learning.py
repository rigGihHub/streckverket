from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from core import SIGNS, normalize
from evidence import adjust_probabilities
from explainable_model import CATEGORY_NAMES


@dataclass(frozen=True)
class FactorSnapshot:
    """Det som behövs för att i efterhand mäta en faktors marginalbidrag.

    counterfactual är modellens sannolikheter om just den signalen hade utelämnats,
    medan final_model är den faktiskt sparade modellen. På så sätt kan vi efter facit
    jämföra samma match med och utan faktorn utan att hitta på information i efterhand.
    """

    category: str
    name: str
    source: str
    verified: bool
    effective_strength: float
    counterfactual: Tuple[float, float, float]
    delta: Tuple[float, float, float]


def snapshots_from_card(card) -> Tuple[FactorSnapshot, ...]:
    signals = list(getattr(card, "used_signals", []) or [])
    final_model = tuple(normalize(getattr(card, "final_model")))
    rows: List[FactorSnapshot] = []
    for idx, signal in enumerate(signals):
        others = [s for j, s in enumerate(signals) if j != idx]
        without, _ = adjust_probabilities(card.base_market, others, max_total_shift=0.14)
        delta = tuple(float(f - w) for f, w in zip(final_model, without))
        rows.append(
            FactorSnapshot(
                category=str(signal.category),
                name=CATEGORY_NAMES.get(signal.category, signal.category.replace("_", " ").capitalize()),
                source=str(signal.source or "Källa saknas"),
                verified=bool(signal.is_verified),
                effective_strength=float(signal.effective_strength),
                counterfactual=tuple(float(x) for x in without),
                delta=delta,
            )
        )
    return tuple(rows)


def factor_map_from_cards(cards: Sequence[object]) -> Dict[int, Tuple[FactorSnapshot, ...]]:
    out: Dict[int, Tuple[FactorSnapshot, ...]] = {}
    for card in cards:
        number = int(getattr(card, "match_number"))
        out[number] = snapshots_from_card(card)
    return out


def _brier(probs: Sequence[float], result: str) -> float:
    p = normalize(probs)
    idx = SIGNS.index(result)
    return sum((p[i] - (1.0 if i == idx else 0.0)) ** 2 for i in range(3))


def factor_observations(coupons: Iterable[object]) -> List[dict]:
    """Returnerar ett observationsrad per sparad faktor och färdig match.

    Positiv brier_gain betyder att den slutliga modellen blev bättre än samma modell
    utan just den faktorn. Det är ett historiskt diagnostikmått, inte ett bevis på kausalitet.
    """
    rows: List[dict] = []
    for coupon in coupons:
        for match in getattr(coupon, "matches", ()):
            if getattr(match, "result", None) not in SIGNS:
                continue
            final = tuple(getattr(match, "model"))
            for factor in getattr(match, "factors", ()) or ():
                if not getattr(factor, "verified", False):
                    continue
                without = tuple(getattr(factor, "counterfactual"))
                gain = _brier(without, match.result) - _brier(final, match.result)
                shift = 0.5 * sum(abs(float(x)) for x in getattr(factor, "delta"))
                rows.append({
                    "coupon_id": getattr(coupon, "coupon_id", ""),
                    "match_number": int(match.match_number),
                    "category": factor.category,
                    "name": factor.name,
                    "source": factor.source,
                    "effective_strength": float(factor.effective_strength),
                    "shift": float(shift),
                    "brier_gain": float(gain),
                    "helped": gain > 0,
                })
    return rows


def factor_scorecard(coupons: Iterable[object], *, min_sample: int = 30) -> List[dict]:
    grouped: Dict[str, List[dict]] = {}
    for row in factor_observations(coupons):
        grouped.setdefault(str(row["category"]), []).append(row)

    out: List[dict] = []
    for category, rows in grouped.items():
        n = len(rows)
        mean_gain = sum(float(r["brier_gain"]) for r in rows) / n
        helped = sum(bool(r["helped"]) for r in rows) / n
        mean_shift = sum(float(r["shift"]) for r in rows) / n
        sources = len({str(r["source"]) for r in rows if r.get("source")})
        if n < min_sample:
            verdict = "För lite data"
        elif mean_gain >= 0.005 and helped >= 0.55:
            verdict = "Ser lovande ut"
        elif mean_gain <= -0.005 and helped <= 0.45:
            verdict = "Behöver granskas"
        else:
            verdict = "Ingen tydlig skillnad"
        out.append({
            "category": category,
            "name": CATEGORY_NAMES.get(category, category.replace("_", " ").capitalize()),
            "matches": n,
            "mean_brier_gain": mean_gain,
            "help_rate": helped,
            "mean_shift": mean_shift,
            "sources": sources,
            "verdict": verdict,
        })
    return sorted(out, key=lambda r: (r["verdict"] == "För lite data", -abs(float(r["mean_brier_gain"])), -int(r["matches"])))


def factor_lesson(scorecard: Sequence[dict]) -> str:
    mature = [r for r in scorecard if r["verdict"] != "För lite data"]
    if not mature:
        total = sum(int(r["matches"]) for r in scorecard)
        return (
            f"Det finns {total} faktorobservationer, men ännu för få per faktor för att dra stabila slutsatser. "
            "Streckverket sparar facit men ändrar inga modellvikter automatiskt."
        )
    best = max(mature, key=lambda r: float(r["mean_brier_gain"]))
    worst = min(mature, key=lambda r: float(r["mean_brier_gain"]))
    if float(best["mean_brier_gain"]) <= 0 and float(worst["mean_brier_gain"]) <= 0:
        return "Ingen mogen faktor har hittills förbättrat sannolikheterna tydligt. De extra justeringarna bör granskas försiktigt."
    if float(worst["mean_brier_gain"]) >= 0:
        return f"{best['name']} ser hittills starkast ut. Ingen mogen faktor visar en tydligt negativ effekt, men mer ny data behövs."
    return f"{best['name']} ser hittills mest lovande ut, medan {worst['name'].lower()} bör granskas extra. Ingen vikt ändras automatiskt."


def proposed_weight_actions(scorecard: Sequence[dict], *, min_sample: int = 100) -> List[dict]:
    """Endast granskningsförslag – aldrig automatiska viktändringar."""
    actions: List[dict] = []
    for row in scorecard:
        n = int(row["matches"])
        if n < min_sample:
            continue
        gain = float(row["mean_brier_gain"])
        if gain >= 0.008 and float(row["help_rate"]) >= 0.56:
            action = "Överväg en liten höjning efter test på ny, separat data"
        elif gain <= -0.008 and float(row["help_rate"]) <= 0.44:
            action = "Överväg en liten sänkning efter test på ny, separat data"
        else:
            action = "Behåll vikten tills vidare"
        actions.append({**row, "action": action})
    return actions
