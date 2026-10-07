"""Small, pure guards for specialist Streamlit views.

These checks deliberately fail closed: specialist tools should not run expensive or
stateful calculations on an incomplete/malformed coupon. They do not alter model logic.
"""
from __future__ import annotations

REQUIRED_MATCH_FIELDS = ("number", "home", "away", "model", "public", "market")


def specialist_coupon_issues(matches) -> tuple[str, ...]:
    issues: list[str] = []
    if matches is None:
        return ("Kupong saknas.",)
    try:
        count = len(matches)
    except TypeError:
        return ("Kupongen går inte att läsa som en matchlista.",)
    if count != 13:
        issues.append(f"Specialistverktyget kräver exakt 13 matcher; hittade {count}.")
    for idx, match in enumerate(matches, 1):
        missing = [name for name in REQUIRED_MATCH_FIELDS if not hasattr(match, name)]
        if missing:
            issues.append(f"Match {idx} saknar fält: {', '.join(missing)}.")
    return tuple(issues)


def specialist_coupon_ready(matches) -> bool:
    return not specialist_coupon_issues(matches)
