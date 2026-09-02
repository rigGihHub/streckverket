from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

@dataclass
class PredictionSnapshot:
    coupon_id: str
    match_number: int
    home: str
    away: str
    model: list[float]
    market: list[float]
    public: list[float]
    source: str
    captured_at: str
    result: str | None = None


def make_snapshot(coupon_id, match, source: str, captured_at: str | None=None):
    return PredictionSnapshot(str(coupon_id),match.number,match.home,match.away,list(match.model),list(match.market),list(match.public),source,
                              captured_at or datetime.now(timezone.utc).isoformat())


def save_snapshots(path: str | Path, snapshots: Sequence[PredictionSnapshot]) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    if p.exists():
        try: rows=json.loads(p.read_text(encoding='utf-8'))
        except Exception: rows=[]
    rows.extend(asdict(s) for s in snapshots)
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


def load_snapshots(path: str | Path) -> List[Dict]:
    p=Path(path)
    if not p.exists(): return []
    return json.loads(p.read_text(encoding='utf-8'))
