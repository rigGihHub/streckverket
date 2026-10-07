from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from math import log
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from factor_learning import FactorSnapshot
from predictive_experiment import ShadowPrediction
from observation_quality import ObservationQuality, assess_observation_quality, summarize_quality

from core import SIGNS, normalize
from swap_backtest import SwapProposalSnapshot
from counterfactual_system_lab import CounterfactualSystemSnapshot


@dataclass(frozen=True)
class FacitMatch:
    match_number: int
    home: str
    away: str
    model: Tuple[float, float, float]
    market: Tuple[float, float, float]
    public: Tuple[float, float, float]
    selected: Tuple[str, ...]
    result: str | None = None
    factors: Tuple[FactorSnapshot, ...] = ()
    kickoff: str | None = None
    market_available: bool = True
    market_source: str = ""
    market_bookmaker_count: int | None = None
    market_last_update: str | None = None
    market_match_confidence: float | None = None
    market_dispersion: float | None = None
    market_outliers: Tuple[str, ...] = ()
    market_consensus_method: str = ""
    public_last_update: str | None = None
    shadow_predictions: Tuple[ShadowPrediction, ...] = ()


@dataclass(frozen=True)
class FacitCoupon:
    coupon_id: str
    captured_at: str
    source: str
    strategy: str
    budget: int
    rows: int
    model_coverage: float
    matches: Tuple[FacitMatch, ...]
    model_version: str = ""
    swap_proposals: Tuple[SwapProposalSnapshot, ...] = ()
    counterfactual_systems: Tuple[CounterfactualSystemSnapshot, ...] = ()
    market_timeline_key: str = ""


def _as_probs(values: Sequence[float]) -> Tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError("Tre sannolikheter krävs")
    out = normalize(values)
    return tuple(float(x) for x in out)  # type: ignore[return-value]


def make_coupon_snapshot(
    coupon_id: str,
    matches,
    selections: Sequence[Sequence[str]],
    *,
    source: str,
    strategy: str,
    budget: int,
    rows: int,
    model_coverage: float,
    captured_at: str | None = None,
    factor_snapshots: Mapping[int, Sequence[FactorSnapshot]] | None = None,
    model_version: str = "",
    swap_proposals: Sequence[SwapProposalSnapshot] = (),
    counterfactual_systems: Sequence[CounterfactualSystemSnapshot] = (),
    market_timeline_key: str = "",
    shadow_predictions: Mapping[int, Sequence[ShadowPrediction]] | None = None,
) -> FacitCoupon:
    if len(matches) != 13 or len(selections) != 13:
        raise ValueError("Ett Stryktipsfacit kräver exakt 13 matcher och 13 val")
    out: List[FacitMatch] = []
    for match, selected in zip(matches, selections):
        chosen = tuple(str(s).upper() for s in selected)
        if not chosen or any(s not in SIGNS for s in chosen):
            raise ValueError("Varje match måste ha minst ett giltigt tecken: 1, X eller 2")
        out.append(
            FacitMatch(
                match_number=int(match.number),
                home=str(match.home),
                away=str(match.away),
                model=_as_probs(match.model),
                market=_as_probs(match.market),
                public=_as_probs(match.public),
                selected=chosen,
                kickoff=getattr(match, "kickoff", None),
                market_available=bool(getattr(match, "market_available", True)),
                market_source=str(getattr(match, "market_source", "") or ""),
                market_bookmaker_count=getattr(match, "market_bookmaker_count", None),
                market_last_update=getattr(match, "market_last_update", None),
                market_match_confidence=getattr(match, "market_match_confidence", None),
                market_dispersion=getattr(match, "market_dispersion", None),
                market_outliers=tuple(getattr(match, "market_outliers", ()) or ()),
                market_consensus_method=str(getattr(match, "market_consensus_method", "") or ""),
                public_last_update=getattr(match, "public_last_update", None),
                factors=tuple((factor_snapshots or {}).get(int(match.number), ())),
                shadow_predictions=tuple((shadow_predictions or {}).get(int(match.number), ())),
            )
        )
    return FacitCoupon(
        coupon_id=str(coupon_id),
        captured_at=captured_at or datetime.now(timezone.utc).isoformat(),
        source=str(source),
        strategy=str(strategy),
        budget=int(budget),
        rows=int(rows),
        model_coverage=float(model_coverage),
        matches=tuple(out),
        model_version=str(model_version or ""),
        swap_proposals=tuple(swap_proposals), counterfactual_systems=tuple(counterfactual_systems),
        market_timeline_key=str(market_timeline_key or ""),
    )


def with_results(coupon: FacitCoupon, results: Mapping[int, str]) -> FacitCoupon:
    updated: List[FacitMatch] = []
    for match in coupon.matches:
        result = results.get(match.match_number, match.result)
        if result is not None:
            result = str(result).upper()
            if result not in SIGNS:
                raise ValueError(f"Ogiltigt resultat för match {match.match_number}: {result}")
        updated.append(FacitMatch(
            match_number=match.match_number, home=match.home, away=match.away,
            model=match.model, market=match.market, public=match.public,
            selected=match.selected, kickoff=match.kickoff, market_available=match.market_available,
            market_source=match.market_source, market_bookmaker_count=match.market_bookmaker_count,
            market_last_update=match.market_last_update, market_match_confidence=match.market_match_confidence,
            market_dispersion=match.market_dispersion, market_outliers=match.market_outliers, market_consensus_method=match.market_consensus_method,
            public_last_update=match.public_last_update, result=result, factors=match.factors,
            shadow_predictions=match.shadow_predictions,
        ))
    return FacitCoupon(
        coupon_id=coupon.coupon_id, captured_at=coupon.captured_at, source=coupon.source,
        strategy=coupon.strategy, budget=coupon.budget, rows=coupon.rows,
        model_coverage=coupon.model_coverage, matches=tuple(updated), model_version=coupon.model_version,
        swap_proposals=coupon.swap_proposals, counterfactual_systems=coupon.counterfactual_systems,
        market_timeline_key=coupon.market_timeline_key,
    )


def _outcome_index(result: str) -> int:
    try:
        return SIGNS.index(result)
    except ValueError as exc:
        raise ValueError(f"Ogiltigt utfall: {result}") from exc


def _brier_one(probs: Sequence[float], result: str) -> float:
    p = _as_probs(probs)
    y = _outcome_index(result)
    return sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(3))


def _logloss_one(probs: Sequence[float], result: str) -> float:
    p = _as_probs(probs)
    return -log(max(1e-12, p[_outcome_index(result)]))


def _pick(probs: Sequence[float]) -> str:
    return SIGNS[max(range(3), key=lambda i: float(probs[i]))]


def observation_quality_for_match(match: FacitMatch, captured_at: str | None) -> ObservationQuality:
    return assess_observation_quality(
        market_available=bool(getattr(match, "market_available", False)),
        captured_at=captured_at, kickoff=getattr(match, "kickoff", None),
        market_source=getattr(match, "market_source", ""),
        market_bookmaker_count=getattr(match, "market_bookmaker_count", None),
        market_last_update=getattr(match, "market_last_update", None),
        market_match_confidence=getattr(match, "market_match_confidence", None),
        public_last_update=getattr(match, "public_last_update", None),
    )


def observation_quality_summary(coupons: Iterable[FacitCoupon]) -> Dict[str, object]:
    qualities = [observation_quality_for_match(m, c.captured_at) for c in coupons for m in c.matches]
    return summarize_quality(qualities)


def is_validation_eligible(match: FacitMatch) -> bool:
    """True only when the result is known and a real bookmaker baseline was captured.

    Historical model-vs-market learning must never treat fallback/synthetic market
    probabilities as genuine bookmaker evidence.
    """
    return match.result in SIGNS and bool(getattr(match, "market_available", False))


def validation_observation_counts(coupons: Iterable[FacitCoupon]) -> Dict[str, int]:
    completed = 0
    eligible = 0
    missing_market = 0
    for coupon in coupons:
        for match in coupon.matches:
            if match.result not in SIGNS:
                continue
            completed += 1
            if is_validation_eligible(match):
                eligible += 1
            else:
                missing_market += 1
    return {
        "completed": completed,
        "eligible": eligible,
        "excluded_missing_market": missing_market,
    }


def evaluate_coupon(coupon: FacitCoupon) -> Dict[str, object]:
    completed = [m for m in coupon.matches if m.result in SIGNS]
    if not completed:
        return {
            "completed": 0,
            "total": len(coupon.matches),
            "system_hits": 0,
            "thirteen_correct": False,
            "model_pick_hits": 0,
            "market_pick_hits": 0,
            "market_completed": 0,
            "public_pick_hits": 0,
            "model_brier": None,
            "market_brier": None,
            "model_log_loss": None,
            "market_log_loss": None,
            "plain_summary": "Inga resultat är registrerade ännu.",
        }

    system_hits = sum(1 for m in completed if m.result in m.selected)
    model_hits = sum(1 for m in completed if _pick(m.model) == m.result)
    validation = [m for m in completed if is_validation_eligible(m)]
    market_hits = sum(1 for m in validation if _pick(m.market) == m.result)
    public_hits = sum(1 for m in completed if _pick(m.public) == m.result)
    model_brier = (sum(_brier_one(m.model, m.result) for m in validation) / len(validation)) if validation else None
    market_brier = (sum(_brier_one(m.market, m.result) for m in validation) / len(validation)) if validation else None
    model_ll = (sum(_logloss_one(m.model, m.result) for m in validation) / len(validation)) if validation else None
    market_ll = (sum(_logloss_one(m.market, m.result) for m in validation) / len(validation)) if validation else None

    if len(completed) < len(coupon.matches):
        plain = f"{len(completed)} av {len(coupon.matches)} matcher har fått ett slutresultat. Facitet är därför inte komplett ännu."
    elif system_hits == 13:
        plain = "Systemet täckte utfallet i alla 13 matcher. Det betyder att 13 rätt fanns bland systemets rader."
    else:
        plain = f"Systemet täckte {system_hits} av 13 matchutfall. {13-system_hits} matcher föll utanför de tecken vi hade valt."

    return {
        "completed": len(completed),
        "total": len(coupon.matches),
        "system_hits": system_hits,
        "thirteen_correct": len(completed) == 13 and system_hits == 13,
        "model_pick_hits": model_hits,
        "market_pick_hits": market_hits,
        "market_completed": len(validation),
        "public_pick_hits": public_hits,
        "model_brier": model_brier,
        "market_brier": market_brier,
        "model_log_loss": model_ll,
        "market_log_loss": market_ll,
        "plain_summary": plain,
    }


def calibration_rows(coupons: Iterable[FacitCoupon], bin_size: float = 0.10) -> List[Dict[str, float | int | str]]:
    if not 0 < bin_size <= 0.5:
        raise ValueError("bin_size måste vara > 0 och <= 0,5")
    buckets: Dict[int, List[int]] = {}
    sums: Dict[int, float] = {}
    for coupon in coupons:
        for m in coupon.matches:
            if not is_validation_eligible(m):
                continue
            for sign, prob in zip(SIGNS, m.model):
                idx = min(int(float(prob) / bin_size), int(1.0 / bin_size) - 1)
                buckets.setdefault(idx, []).append(1 if sign == m.result else 0)
                sums[idx] = sums.get(idx, 0.0) + float(prob)
    rows: List[Dict[str, float | int | str]] = []
    for idx in sorted(buckets):
        ys = buckets[idx]
        n = len(ys)
        lo = idx * bin_size
        hi = min(1.0, (idx + 1) * bin_size)
        rows.append({
            "intervall": f"{int(round(lo*100))}–{int(round(hi*100))} %",
            "antal": n,
            "modell_snitt": sums[idx] / n,
            "utfall_snitt": sum(ys) / n,
            "kalibreringsfel": abs((sums[idx] / n) - (sum(ys) / n)),
        })
    return rows


def aggregate_performance(coupons: Sequence[FacitCoupon]) -> Dict[str, object]:
    completed_matches = [m for c in coupons for m in c.matches if m.result in SIGNS]
    validation_matches = [m for m in completed_matches if is_validation_eligible(m)]
    complete_coupons = [c for c in coupons if all(m.result in SIGNS for m in c.matches)]
    thirteen = sum(bool(evaluate_coupon(c)["thirteen_correct"]) for c in complete_coupons)
    excluded_missing_market = len(completed_matches) - len(validation_matches)
    if not validation_matches:
        return {
            "matches": 0,
            "completed_matches": len(completed_matches),
            "excluded_missing_market": excluded_missing_market,
            "coupons": len(coupons),
            "complete_coupons": 0,
            "model_pick_accuracy": None,
            "market_pick_accuracy": None,
            "public_pick_accuracy": None,
            "model_brier": None,
            "market_brier": None,
            "model_log_loss": None,
            "market_log_loss": None,
            "system_13_count": thirteen,
            "lesson": "Det behövs färdiga matcher med verifierad bookmakerbas innan Streckverket kan jämföra modellen mot marknaden.",
        }
    n = len(validation_matches)
    model_hits = sum(_pick(m.model) == m.result for m in validation_matches)
    market_hits = sum(_pick(m.market) == m.result for m in validation_matches)
    public_hits = sum(_pick(m.public) == m.result for m in validation_matches)
    mb = sum(_brier_one(m.model, m.result) for m in validation_matches) / n
    kb = sum(_brier_one(m.market, m.result) for m in validation_matches) / n
    mll = sum(_logloss_one(m.model, m.result) for m in validation_matches) / n
    kll = sum(_logloss_one(m.market, m.result) for m in validation_matches) / n

    if n < 100:
        lesson = "Underlaget är fortfarande litet. Streckverket visar resultaten men ska inte ändra modellen aggressivt ännu."
    elif mb + 0.01 < kb and mll < kll:
        lesson = "Modellen har hittills bedömt sannolikheter bättre än marknadsbasen. Fortsätt samla data innan vikter ändras stort."
    elif mb > kb + 0.01 and mll > kll:
        lesson = "Marknadsbasen har hittills varit bättre kalibrerad än Streckverkets justeringar. Modellens extra signaler bör granskas."
    else:
        lesson = "Modellen och marknadsbasen ligger nära varandra. Mer historik behövs för att avgöra om justeringarna ger verklig förbättring."

    return {
        "matches": n,
        "completed_matches": len(completed_matches),
        "excluded_missing_market": excluded_missing_market,
        "coupons": len(coupons),
        "complete_coupons": len(complete_coupons),
        "model_pick_accuracy": model_hits / n,
        "market_pick_accuracy": market_hits / n,
        "public_pick_accuracy": public_hits / n,
        "model_brier": mb,
        "market_brier": kb,
        "model_log_loss": mll,
        "market_log_loss": kll,
        "system_13_count": thirteen,
        "lesson": lesson,
    }


def dumps_facit(coupons: Sequence[FacitCoupon]) -> str:
    return json.dumps([asdict(c) for c in coupons], ensure_ascii=False, indent=2)


def loads_facit(text: str) -> List[FacitCoupon]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError("Facitfilen måste innehålla en lista")
    coupons: List[FacitCoupon] = []
    for item in raw:
        matches = []
        for m in item.get("matches", []):
            factors = tuple(
                FactorSnapshot(
                    category=str(f.get("category", "other")),
                    name=str(f.get("name", f.get("category", "Okänd faktor"))),
                    source=str(f.get("source", "Källa saknas")),
                    verified=bool(f.get("verified", False)),
                    effective_strength=float(f.get("effective_strength", 0.0)),
                    counterfactual=_as_probs(f.get("counterfactual", m.get("market", (1/3,1/3,1/3)))),
                    delta=tuple(float(x) for x in f.get("delta", (0.0,0.0,0.0))),
                )
                for f in (m.get("factors") or [])
            )
            shadow_predictions = tuple(
                ShadowPrediction(
                    experiment_id=str(p.get("experiment_id", "")),
                    label=str(p.get("label", "")),
                    probabilities=_as_probs(p.get("probabilities", (1/3,1/3,1/3))),
                    source_model_version=str(p.get("source_model_version", "")),
                    candidate_rule=str(p.get("candidate_rule", "")),
                )
                for p in (m.get("shadow_predictions") or [])
            )
            matches.append(FacitMatch(
                match_number=int(m["match_number"]), home=str(m["home"]), away=str(m["away"]),
                model=_as_probs(m["model"]), market=_as_probs(m["market"]), public=_as_probs(m["public"]),
                selected=tuple(str(x) for x in m["selected"]), kickoff=m.get("kickoff"),
                market_available=bool(m.get("market_available", False)),
                market_source=str(m.get("market_source", "") or ""),
                market_bookmaker_count=(int(m["market_bookmaker_count"]) if m.get("market_bookmaker_count") is not None else None),
                market_last_update=m.get("market_last_update"),
                market_match_confidence=(float(m["market_match_confidence"]) if m.get("market_match_confidence") is not None else None),
                market_dispersion=(float(m["market_dispersion"]) if m.get("market_dispersion") is not None else None),
                market_outliers=tuple(str(x) for x in (m.get("market_outliers") or ())),
                market_consensus_method=str(m.get("market_consensus_method", "") or ""),
                public_last_update=m.get("public_last_update"), result=m.get("result"), factors=factors,
                shadow_predictions=shadow_predictions,
            ))
        swap_proposals = tuple(
            SwapProposalSnapshot(
                rank=int(p.get("rank", i + 1)),
                donor_match_number=int(p["donor_match_number"]),
                donor_from=tuple(str(x) for x in p["donor_from"]),
                donor_to=tuple(str(x) for x in p["donor_to"]),
                recipient_match_number=int(p["recipient_match_number"]),
                recipient_from=tuple(str(x) for x in p["recipient_from"]),
                recipient_to=tuple(str(x) for x in p["recipient_to"]),
                rows=int(p.get("rows", item.get("rows", 0))),
                predicted_delta_coverage_pp=float(p.get("predicted_delta_coverage_pp", 0.0)),
                predicted_relative_gain_pct=float(p.get("predicted_relative_gain_pct", 0.0)),
            )
            for i, p in enumerate(item.get("swap_proposals", ()) or ())
        )
        counterfactual_systems = tuple(
            CounterfactualSystemSnapshot(
                label=str(v.get("label", "OKÄNT SYSTEM")), origin=str(v.get("origin", "unknown")),
                selections=tuple(tuple(str(s) for s in sel) for sel in v.get("selections", ())),
                rows=int(v.get("rows", 0)), model_coverage=float(v.get("model_coverage", 0.0)),
                aliases=tuple(str(x) for x in (v.get("aliases", ()) or ())),
            ) for v in (item.get("counterfactual_systems", ()) or ())
        )
        coupons.append(FacitCoupon(
            coupon_id=str(item["coupon_id"]), captured_at=str(item["captured_at"]),
            source=str(item["source"]), strategy=str(item["strategy"]), budget=int(item["budget"]),
            rows=int(item["rows"]), model_coverage=float(item["model_coverage"]), matches=tuple(matches),
            model_version=str(item.get("model_version", "") or ""), swap_proposals=swap_proposals,
            counterfactual_systems=counterfactual_systems,
            market_timeline_key=str(item.get("market_timeline_key", "") or ""),
        ))
    return coupons
