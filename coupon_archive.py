from __future__ import annotations

"""Read-only helpers for Streckverket's coupon archive.

The archive deliberately derives all labels from saved FacitCoupon snapshots.
It never reconstructs or invents information that was not captured before kickoff.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

from core import SIGNS
from facit import FacitCoupon, FacitMatch, evaluate_coupon


@dataclass(frozen=True)
class ArchiveRow:
    coupon_id: str
    captured_at: str
    captured_label: str
    source: str
    strategy: str
    budget: int
    rows: int
    coverage: float
    completed: int
    system_hits: int
    status: str
    result_label: str


def _date_label(value: str) -> str:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(value)


def coupon_status(coupon: FacitCoupon) -> str:
    ev = evaluate_coupon(coupon)
    completed = int(ev["completed"])
    if completed == 0:
        return "Väntar på facit"
    if completed < 13:
        return "Pågående facit"
    if bool(ev["thirteen_correct"]):
        return "Systemet täckte 13"
    return "Facit klart"


def result_label(coupon: FacitCoupon) -> str:
    ev = evaluate_coupon(coupon)
    completed = int(ev["completed"])
    hits = int(ev["system_hits"])
    if completed == 0:
        return "–"
    if completed < 13:
        return f"{hits}/{completed} täckta hittills"
    if bool(ev["thirteen_correct"]):
        return "13/13 täckta"
    return f"{hits}/13 täckta"


def archive_rows(coupons: Sequence[FacitCoupon]) -> List[ArchiveRow]:
    rows: List[ArchiveRow] = []
    for coupon in sorted(coupons, key=lambda c: (c.captured_at, c.coupon_id), reverse=True):
        ev = evaluate_coupon(coupon)
        rows.append(
            ArchiveRow(
                coupon_id=coupon.coupon_id,
                captured_at=coupon.captured_at,
                captured_label=_date_label(coupon.captured_at),
                source=coupon.source,
                strategy=coupon.strategy,
                budget=int(coupon.budget),
                rows=int(coupon.rows),
                coverage=float(coupon.model_coverage),
                completed=int(ev["completed"]),
                system_hits=int(ev["system_hits"]),
                status=coupon_status(coupon),
                result_label=result_label(coupon),
            )
        )
    return rows


def filter_coupons(
    coupons: Sequence[FacitCoupon],
    *,
    status: str | None = None,
    strategy: str | None = None,
    query: str = "",
) -> List[FacitCoupon]:
    wanted_status = (status or "Alla").strip()
    wanted_strategy = (strategy or "Alla").strip()
    needle = query.strip().casefold()
    out: List[FacitCoupon] = []
    for coupon in coupons:
        if wanted_status != "Alla" and coupon_status(coupon) != wanted_status:
            continue
        if wanted_strategy != "Alla" and coupon.strategy != wanted_strategy:
            continue
        if needle:
            haystack = " ".join(
                [coupon.coupon_id, coupon.source, coupon.strategy]
                + [f"{m.home} {m.away}" for m in coupon.matches]
            ).casefold()
            if needle not in haystack:
                continue
        out.append(coupon)
    return sorted(out, key=lambda c: (c.captured_at, c.coupon_id), reverse=True)


def match_archive_rows(coupon: FacitCoupon) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for match in sorted(coupon.matches, key=lambda m: m.match_number):
        model_pick = SIGNS[max(range(3), key=lambda i: float(match.model[i]))]
        market_pick = SIGNS[max(range(3), key=lambda i: float(match.market[i]))]
        public_pick = SIGNS[max(range(3), key=lambda i: float(match.public[i]))]
        out.append(
            {
                "Match": match.match_number,
                "Möte": f"{match.home} – {match.away}",
                "System": "".join(match.selected),
                "Resultat": match.result or "–",
                "Täckt": "Ja" if match.result in match.selected else ("–" if match.result is None else "Nej"),
                "Modellens förstaval": model_pick,
                "Marknadens förstaval": market_pick,
                "Folkets förstaval": public_pick,
                "Modell 1/X/2": " / ".join(f"{100*p:.0f}%" for p in match.model),
                "Marknad 1/X/2": " / ".join(f"{100*p:.0f}%" for p in match.market),
                "Streck 1/X/2": " / ".join(f"{100*p:.0f}%" for p in match.public),
                "Verifierade faktorer": sum(1 for f in match.factors if f.verified and f.effective_strength > 0),
            }
        )
    return out


def factor_archive_rows(coupon: FacitCoupon) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for match in coupon.matches:
        for factor in match.factors:
            rows.append(
                {
                    "Match": match.match_number,
                    "Möte": f"{match.home} – {match.away}",
                    "Faktor": factor.name,
                    "Kategori": factor.category,
                    "Källa": factor.source,
                    "Verifierad": "Ja" if factor.verified else "Nej",
                    "Styrka": float(factor.effective_strength),
                    "Effekt 1": float(factor.delta[0]),
                    "Effekt X": float(factor.delta[1]),
                    "Effekt 2": float(factor.delta[2]),
                }
            )
    return rows


def archive_summary(coupons: Sequence[FacitCoupon]) -> Dict[str, object]:
    rows = archive_rows(coupons)
    complete = sum(r.completed == 13 for r in rows)
    thirteen = sum(r.status == "Systemet täckte 13" for r in rows)
    waiting = sum(r.completed == 0 for r in rows)
    return {
        "coupons": len(rows),
        "complete": complete,
        "thirteen": thirteen,
        "waiting": waiting,
        "latest": rows[0].captured_label if rows else None,
    }
