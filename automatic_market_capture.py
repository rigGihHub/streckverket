from __future__ import annotations

"""Conservative automatic pre-kickoff market capture (v3.62).

This module only persists bookmaker observations that are already present in the
live coupon. It does not fetch new prices, alter predictions, or call any late
observation a closing line. Repeated Streamlit reruns are safe because the
history store deduplicates unchanged observations within five minutes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from market_timeline import make_market_points
from snapshot_timing import classify_snapshot_timing


@dataclass(frozen=True)
class AutomaticCaptureResult:
    status: str
    saved_points: int = 0
    message: str = ""


def capture_eligible(matches: Sequence[object], *, data_mode: str, captured_at: str | None = None) -> tuple[bool, str]:
    if str(data_mode or "").strip().casefold() == "demo":
        return False, "Demodata sparas inte."
    if len(matches) != 13:
        return False, "Kupongen måste innehålla exakt 13 matcher."
    if not any(bool(getattr(m, "market_available", False)) for m in matches):
        return False, "Verifierad bookmakerbas saknas."
    observed_at = captured_at or datetime.now(timezone.utc).isoformat()
    for match in matches:
        kickoff = getattr(match, "kickoff", None)
        if kickoff and classify_snapshot_timing(observed_at, kickoff).bucket == "POST_KICKOFF":
            return False, "Minst en match har redan startat."
    return True, ""


def automatic_market_capture(store, matches: Sequence[object], *, data_mode: str, captured_at: str | None = None) -> AutomaticCaptureResult:
    stamp = captured_at or datetime.now(timezone.utc).isoformat()
    ok, reason = capture_eligible(matches, data_mode=data_mode, captured_at=stamp)
    if not ok:
        return AutomaticCaptureResult("SKIPPED", 0, reason)
    if store is None:
        return AutomaticCaptureResult("UNAVAILABLE", 0, "Historiklagring är inte tillgänglig.")
    try:
        saved = int(store.save_market_points(make_market_points(matches, captured_at=stamp)))
    except Exception as exc:
        return AutomaticCaptureResult("ERROR", 0, f"{type(exc).__name__}: {exc}")
    if saved:
        return AutomaticCaptureResult("SAVED", saved, "Aktuell bookmakerbild sparades automatiskt.")
    return AutomaticCaptureResult("UNCHANGED", 0, "Marknadsbilden är oförändrad sedan senaste mätningen.")
