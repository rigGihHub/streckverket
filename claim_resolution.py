from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
import json
from source_performance import SourceObservation

@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    source_key: str
    topic: str
    subject: str
    predicted_value: str
    published_at: Optional[str] = None
    independent: bool = True
    resolved: bool = False
    actual_value: Optional[str] = None
    resolved_at: Optional[str] = None
    market_reaction_at: Optional[str] = None
    public_reaction_at: Optional[str] = None

@dataclass(frozen=True)
class ResolutionResult:
    claim_id: str
    correct: bool
    information_edge_market_minutes: Optional[int]
    information_edge_public_minutes: Optional[int]
    observation: SourceObservation

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value: return None
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _edge_minutes(published_at: Optional[str], reaction_at: Optional[str]) -> Optional[int]:
    pub, react = _parse_dt(published_at), _parse_dt(reaction_at)
    if not pub or not react: return None
    return int(round((react-pub).total_seconds()/60))

def resolve_claim(record: ClaimRecord, actual_value: str, resolved_at: str) -> ResolutionResult:
    observation = SourceObservation(
        source_key=record.source_key, topic=record.topic,
        predicted_value=record.predicted_value, actual_value=actual_value,
        published_at=record.published_at, resolved_at=resolved_at,
        independent=record.independent,
    )
    return ResolutionResult(
        claim_id=record.claim_id, correct=observation.correct,
        information_edge_market_minutes=_edge_minutes(record.published_at, record.market_reaction_at),
        information_edge_public_minutes=_edge_minutes(record.published_at, record.public_reaction_at),
        observation=observation,
    )

def information_edge_label(minutes: Optional[int]) -> str:
    if minutes is None: return 'Okänd'
    if minutes >= 180: return 'Mycket tidig'
    if minutes >= 60: return 'Tidig'
    if minutes >= 15: return 'Liten edge'
    if minutes >= 0: return 'Samtidigt'
    return 'Efter marknaden'

def summarize_information_edge(results: Iterable[ResolutionResult]) -> dict:
    items=list(results)
    market=[x.information_edge_market_minutes for x in items if x.correct and x.information_edge_market_minutes is not None]
    public=[x.information_edge_public_minutes for x in items if x.correct and x.information_edge_public_minutes is not None]
    correct=sum(x.correct for x in items)
    return {
        'resolved_claims':len(items),'correct_claims':correct,
        'correct_rate':correct/len(items) if items else 0.0,
        'avg_market_edge_minutes':round(sum(market)/len(market),1) if market else None,
        'avg_public_edge_minutes':round(sum(public)/len(public),1) if public else None,
        'market_edge_samples':len(market),'public_edge_samples':len(public),
    }

def save_claim_records(path: str|Path, records: Iterable[ClaimRecord]) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps([asdict(x) for x in records],ensure_ascii=False,indent=2),encoding='utf-8')

def load_claim_records(path: str|Path) -> list[ClaimRecord]:
    p=Path(path)
    if not p.exists(): return []
    return [ClaimRecord(**x) for x in json.loads(p.read_text(encoding='utf-8'))]
