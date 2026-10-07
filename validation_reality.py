from __future__ import annotations
from dataclasses import dataclass
from collections import Counter

from facit import is_validation_eligible, observation_quality_for_match
from snapshot_timing import classify_snapshot_timing

@dataclass(frozen=True)
class ValidationReality:
    eligible_matches: int
    eligible_coupons: int
    high_quality_matches: int
    near_kickoff_matches: int
    known_version_coupons: int
    unknown_version_coupons: int
    model_versions: tuple[tuple[str, int], ...]
    status: str
    biggest_gap: str
    edge_claim_allowed: bool = False


def assess_validation_reality(coupons, *, min_matches: int = 100, min_coupons: int = 20) -> ValidationReality:
    eligible_matches = 0
    eligible_coupon_ids = set()
    high_quality = 0
    near = 0
    versions = Counter()
    known_version_coupons = 0
    unknown_version_coupons = 0

    for coupon in coupons:
        coupon_has_eligible = False
        for match in coupon.matches:
            if not is_validation_eligible(match):
                continue
            coupon_has_eligible = True
            eligible_matches += 1
            if observation_quality_for_match(match, coupon.captured_at).score >= 60:
                high_quality += 1
            timing = classify_snapshot_timing(coupon.captured_at, getattr(match, "kickoff", None))
            if timing.eligible_pre_match and timing.hours_before_kickoff is not None and timing.hours_before_kickoff <= 3:
                near += 1
        if coupon_has_eligible:
            eligible_coupon_ids.add(coupon.coupon_id)
            version = str(getattr(coupon, "model_version", "") or "").strip()
            if version:
                versions[version] += 1
                known_version_coupons += 1
            else:
                unknown_version_coupons += 1

    coupon_count = len(eligible_coupon_ids)
    if eligible_matches < min_matches:
        status = "SAMLA MER HISTORIK"
        gap = f"Behöver minst {min_matches - eligible_matches} fler verifierade matcher för grundgranskning."
    elif coupon_count < min_coupons:
        status = "FÖR FÅ SEPARATA KUPONGER"
        gap = f"Behöver minst {min_coupons - coupon_count} fler separata kuponger. Matcher på samma kupong räknas inte som helt oberoende bevis."
    elif unknown_version_coupons > 0:
        status = "GRANSKNINGSBAR – VERSIONSPROVENIENS SAKNAS"
        gap = f"{unknown_version_coupons} historiska kuponger saknar modellversion. Jämför därför inte modellgenerationer som om de vore samma modell."
    elif high_quality < min_matches:
        status = "GRANSKNINGSBAR – KVALITETSHISTORIK TUNN"
        gap = f"Bara {high_quality} verifierade matcher har observationskvalitet minst 60/100."
    else:
        status = "GRANSKNINGSBAR – INTE BEVISAD EDGE"
        gap = "Fortsätt samla tidsstämplad historik och kontrollera robusthet över nya kuponger och modellversioner."

    return ValidationReality(
        eligible_matches=eligible_matches,
        eligible_coupons=coupon_count,
        high_quality_matches=high_quality,
        near_kickoff_matches=near,
        known_version_coupons=known_version_coupons,
        unknown_version_coupons=unknown_version_coupons,
        model_versions=tuple(sorted(versions.items())),
        status=status,
        biggest_gap=gap,
        edge_claim_allowed=False,
    )
