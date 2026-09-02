from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class RefreshPlan:
    hours_to_deadline: float
    intervals_minutes: dict[str, int]
    urgency: str


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def build_refresh_plan(deadline: datetime, now: datetime | None = None) -> RefreshPlan:
    """Dynamisk refresh-policy. Tätare bara för källor som faktiskt kan ändras nära spelstopp."""
    now = _aware(now or datetime.now(timezone.utc))
    deadline = _aware(deadline)
    hours = max(0.0, (deadline - now).total_seconds() / 3600)

    if hours > 24:
        intervals = {"streck":180, "odds":180, "injuries":360, "lineups":360, "weather":360, "form":720, "standings":720}
        urgency = "Låg"
    elif hours > 6:
        intervals = {"streck":60, "odds":60, "injuries":120, "lineups":120, "weather":180, "form":360, "standings":360}
        urgency = "Normal"
    elif hours > 1:
        intervals = {"streck":20, "odds":20, "injuries":30, "lineups":20, "weather":60, "form":240, "standings":240}
        urgency = "Hög"
    elif hours > (20/60):
        intervals = {"streck":10, "odds":10, "injuries":15, "lineups":5, "weather":30, "form":240, "standings":240}
        urgency = "Mycket hög"
    else:
        intervals = {"streck":5, "odds":5, "injuries":10, "lineups":2, "weather":20, "form":240, "standings":240}
        urgency = "Sista kontroll"
    return RefreshPlan(hours, intervals, urgency)


def is_due(last_updated: datetime | None, interval_minutes: int, now: datetime | None = None) -> bool:
    if last_updated is None:
        return True
    now = _aware(now or datetime.now(timezone.utc))
    last_updated = _aware(last_updated)
    return (now-last_updated).total_seconds() >= interval_minutes*60
