from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
import json
import math


@dataclass(frozen=True)
class SourceObservation:
    source_key: str
    topic: str
    predicted_value: str
    actual_value: str
    published_at: Optional[str] = None
    resolved_at: Optional[str] = None
    confidence: float = 1.0
    independent: bool = True

    @property
    def correct(self) -> bool:
        return self.predicted_value.strip().lower() == self.actual_value.strip().lower()


@dataclass(frozen=True)
class SourcePerformance:
    source_key: str
    topic: str
    observations: int
    correct: int
    accuracy: float
    shrunk_accuracy: float
    timeliness_score: float
    independence_rate: float
    performance_score: float
    reliability_multiplier: float


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _timeliness(obs: SourceObservation, horizon_hours: float = 24.0) -> float:
    pub = _parse_dt(obs.published_at)
    res = _parse_dt(obs.resolved_at)
    if not pub or not res or pub >= res:
        return 0.5
    lead = (res - pub).total_seconds() / 3600
    return max(0.0, min(1.0, lead / horizon_hours))


def evaluate_source(
    observations: Iterable[SourceObservation],
    *,
    prior_accuracy: float = 0.72,
    prior_strength: float = 12.0,
) -> list[SourcePerformance]:
    groups = {}
    for o in observations:
        groups.setdefault((o.source_key, o.topic), []).append(o)

    out = []
    for (source_key, topic), items in groups.items():
        n = len(items)
        correct = sum(o.correct for o in items)
        raw_accuracy = correct / n if n else 0.0

        # Beta-like shrinkage against a conservative prior.
        shrunk = (correct + prior_accuracy * prior_strength) / (n + prior_strength)

        time_scores = [_timeliness(o) for o in items]
        timeliness = sum(time_scores) / len(time_scores) if time_scores else 0.5
        independence = sum(1.0 if o.independent else 0.0 for o in items) / n if n else 0.0

        # Accuracy dominates. Timeliness is useful only if source is actually right.
        score = (
            0.68 * shrunk
            + 0.18 * timeliness
            + 0.14 * independence
        )
        score = max(0.0, min(1.0, score))

        # Keep adaptation conservative: source history may nudge, not override, base reliability.
        multiplier = 0.78 + 0.44 * score   # 0.78..1.22
        multiplier = max(0.78, min(1.22, multiplier))

        out.append(SourcePerformance(
            source_key=source_key,
            topic=topic,
            observations=n,
            correct=correct,
            accuracy=round(raw_accuracy, 4),
            shrunk_accuracy=round(shrunk, 4),
            timeliness_score=round(timeliness, 4),
            independence_rate=round(independence, 4),
            performance_score=round(score, 4),
            reliability_multiplier=round(multiplier, 4),
        ))
    return out


def performance_lookup(perfs: Iterable[SourcePerformance]) -> dict[tuple[str, str], SourcePerformance]:
    return {(p.source_key, p.topic): p for p in perfs}


def adjusted_reliability(base_reliability: float, perf: Optional[SourcePerformance]) -> float:
    if perf is None:
        return max(0.0, min(1.0, base_reliability))
    return max(0.0, min(1.0, base_reliability * perf.reliability_multiplier))


def save_observations(path: str | Path, observations: Iterable[SourceObservation]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([asdict(x) for x in observations], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_observations(path: str | Path) -> list[SourceObservation]:
    p = Path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [SourceObservation(**x) for x in raw]
