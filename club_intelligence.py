from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional
import hashlib
import re

from source_registry import TeamSource
from source_performance import SourcePerformance, adjusted_reliability


HIGH_RISK_TOPICS = {"injury", "suspension", "lineup", "transfer", "manager"}
MODEL_RELEVANT_TOPICS = {"injury", "suspension", "lineup", "manager", "travel", "rest"}


def canonical_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9åäöæøéüß ]+", " ", text)
    return " ".join(text.split())


def claim_fingerprint(team_key: str, topic: str, subject: str, value: str) -> str:
    raw = "|".join([
        team_key.strip().lower(),
        topic.strip().lower(),
        canonical_text(subject),
        canonical_text(value),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ClubClaim:
    team_key: str
    topic: str
    subject: str
    value: str
    source: TeamSource
    published_at: Optional[str] = None
    direct: bool = True
    confidence: float = 1.0
    upstream_origin: str = ""

    @property
    def fingerprint(self) -> str:
        return claim_fingerprint(self.team_key, self.topic, self.subject, self.value)

    @property
    def evidence_group(self) -> str:
        # If a publisher explicitly cites another origin, count the origin rather than the republisher.
        return (self.upstream_origin or self.source.origin_group or "unknown").strip().lower()


@dataclass(frozen=True)
class ClaimAssessment:
    fingerprint: str
    topic: str
    subject: str
    value: str
    confidence: float
    label: str
    independent_origins: int
    sources: int
    official_confirmation: bool
    conflict: bool
    model_usable: bool
    reason: str


def _freshness(published_at: Optional[str], now: datetime, half_life_hours: float) -> float:
    if not published_at:
        return 0.70
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 3600)
        return 0.5 ** (age / half_life_hours)
    except Exception:
        return 0.60


def assess_claims(
    claims: Iterable[ClubClaim],
    *,
    now: Optional[datetime] = None,
    half_life_hours: float = 18.0,
    performance: Optional[dict[tuple[str, str], SourcePerformance]] = None,
) -> list[ClaimAssessment]:
    now = now or datetime.now(timezone.utc)
    claims = list(claims)
    groups: dict[tuple[str, str, str], list[ClubClaim]] = {}
    for c in claims:
        # Same topic/subject can have competing values, which is what we need to detect.
        groups.setdefault((c.team_key, c.topic, canonical_text(c.subject)), []).append(c)

    out = []
    for (_, topic, subject_key), bucket in groups.items():
        values: dict[str, list[ClubClaim]] = {}
        for c in bucket:
            values.setdefault(canonical_text(c.value), []).append(c)

        scored = {}
        meta = {}
        for value_key, value_claims in values.items():
            per_origin = {}
            official = False
            for c in value_claims:
                perf = (performance or {}).get((c.source.name, c.topic))
                base_rel = adjusted_reliability(c.source.reliability, perf)
                w = base_rel * max(0.0, min(1.0, c.confidence))
                w *= _freshness(c.published_at, now, half_life_hours)
                w *= 1.0 if c.direct else 0.82
                per_origin[c.evidence_group] = max(per_origin.get(c.evidence_group, 0.0), w)
                official = official or c.source.source_type in {"official_club", "official_league"}
            scored[value_key] = sum(per_origin.values())
            meta[value_key] = {
                "origins": len(per_origin),
                "sources": len({c.source.name for c in value_claims}),
                "official": official,
                "claims": value_claims,
            }

        best_key = max(scored, key=scored.get)
        total = sum(scored.values()) or 1.0
        normalized = scored[best_key] / total
        info = meta[best_key]
        conflict = len([v for v, score in scored.items() if v != best_key and score >= 0.22]) > 0

        corroboration = min(1.0, 0.50 + 0.18 * max(0, info["origins"] - 1))
        if info["official"]:
            corroboration = min(1.0, corroboration + 0.25)
        confidence = normalized * corroboration
        if conflict:
            confidence *= 0.72

        topic_requires_strong_support = topic in HIGH_RISK_TOPICS
        if topic_requires_strong_support:
            model_usable = confidence >= 0.62 and (info["official"] or info["origins"] >= 2) and not conflict
        else:
            model_usable = confidence >= 0.55 and not conflict

        if confidence >= 0.78:
            label = "Verifierad"
        elif confidence >= 0.55:
            label = "Stödd"
        else:
            label = "Obekräftad"

        example = info["claims"][0]
        if conflict:
            reason = "Motstridiga uppgifter finns; signalen spärras från modellen."
        elif info["official"]:
            reason = "Officiell källa stöder uppgiften."
        elif info["origins"] >= 2:
            reason = f"{info['origins']} oberoende ursprung stöder uppgiften."
        else:
            reason = "Endast ett oberoende ursprung; används främst som bevakningssignal."

        out.append(ClaimAssessment(
            fingerprint=example.fingerprint,
            topic=topic,
            subject=example.subject,
            value=example.value,
            confidence=round(confidence, 4),
            label=label,
            independent_origins=info["origins"],
            sources=info["sources"],
            official_confirmation=info["official"],
            conflict=conflict,
            model_usable=model_usable and topic in MODEL_RELEVANT_TOPICS,
            reason=reason,
        ))
    return out


def intelligence_summary(assessments: Iterable[ClaimAssessment]) -> dict:
    items = list(assessments)
    return {
        "claims": len(items),
        "verified": sum(x.label == "Verifierad" for x in items),
        "supported": sum(x.label == "Stödd" for x in items),
        "unconfirmed": sum(x.label == "Obekräftad" for x in items),
        "conflicts": sum(x.conflict for x in items),
        "model_usable": sum(x.model_usable for x in items),
    }
