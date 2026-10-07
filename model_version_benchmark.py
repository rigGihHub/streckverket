from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from verification_engine import benchmark_against_market

UNKNOWN_VERSION = "OKÄND VERSION"


@dataclass(frozen=True)
class VersionBenchmark:
    version: str
    coupons: int
    matches: int
    brier_gain: float | None
    logloss_gain: float | None
    recent_brier_gain: float | None
    verdict: str
    comparable: bool
    summary: str


def group_coupons_by_model_version(coupons: Sequence) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for coupon in coupons:
        version = str(getattr(coupon, "model_version", "") or "").strip() or UNKNOWN_VERSION
        grouped.setdefault(version, []).append(coupon)
    return grouped


def model_version_benchmarks(
    coupons: Sequence,
    *,
    min_sample: int = 100,
    min_coupons: int = 20,
) -> list[VersionBenchmark]:
    rows: list[VersionBenchmark] = []
    for version, version_coupons in group_coupons_by_model_version(coupons).items():
        report = benchmark_against_market(
            version_coupons,
            min_sample=min_sample,
            min_coupons=min_coupons,
        )
        known = version != UNKNOWN_VERSION
        comparable = bool(
            known
            and report.matches >= min_sample
            and report.coupons >= min_coupons
        )
        if not known:
            summary = (
                "Äldre snapshots saknar modellversion. De visas separat men får inte användas för att "
                "avgöra vilken modellgeneration som varit bäst."
            )
        elif not comparable:
            summary = (
                f"{version} har {report.matches} verifierade matcher från {report.coupons} separata kuponger. "
                f"Minst {min_sample} matcher och {min_coupons} kuponger krävs för versionsjämförelse."
            )
        else:
            summary = report.plain_summary
        rows.append(
            VersionBenchmark(
                version=version,
                coupons=report.coupons,
                matches=report.matches,
                brier_gain=report.brier_gain,
                logloss_gain=report.logloss_gain,
                recent_brier_gain=report.recent_brier_gain,
                verdict=report.verdict,
                comparable=comparable,
                summary=summary,
            )
        )
    rows.sort(key=lambda r: (r.version == UNKNOWN_VERSION, r.version), reverse=False)
    return rows


def public_version_rows(rows: Sequence[VersionBenchmark]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "Modellversion": r.version,
            "Kuponger": r.coupons,
            "Verifierade matcher": r.matches,
            "Status": r.verdict,
            "Jämförbar": "JA" if r.comparable else "NEJ",
            "Brier-fördel": None if r.brier_gain is None else round(r.brier_gain, 4),
            "Log loss-fördel": None if r.logloss_gain is None else round(r.logloss_gain, 4),
            "Senaste 30 %": None if r.recent_brier_gain is None else round(r.recent_brier_gain, 4),
            "Tolkning": r.summary,
        })
    return out
