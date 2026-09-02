from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pipeline import MatchPipelineResult, recommendation_change


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def serialize_run(coupon_id: str, results: Sequence[MatchPipelineResult], *, source: str = "pipeline") -> dict:
    return {
        "coupon_id": str(coupon_id),
        "captured_at": _now(),
        "source": source,
        "matches": [{
            "number": r.match.number,
            "home": r.match.home,
            "away": r.match.away,
            "market": list(r.card.base_market),
            "model": list(r.card.final_model),
            "public": list(r.match.public),
            "readiness": r.card.readiness_score,
            "readiness_label": r.card.readiness_label,
            "missing": list(r.card.missing),
            "conflicts": list(r.card.conflicts),
            "failed_sources": r.failed_sources,
            "stages": [asdict(s) for s in r.stages],
        } for r in results],
    }


def append_run(path: str | Path, run: dict) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    rows=[]
    if p.exists():
        try: rows=json.loads(p.read_text(encoding="utf-8"))
        except Exception: rows=[]
    if not isinstance(rows, list): rows=[]
    rows.append(run)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load_runs(path: str | Path) -> list[dict]:
    p=Path(path)
    if not p.exists(): return []
    try:
        rows=json.loads(p.read_text(encoding="utf-8"))
        return rows if isinstance(rows,list) else []
    except Exception:
        return []


def compare_latest(runs: Sequence[dict]) -> list[dict]:
    if len(runs) < 2: return []
    a,b=runs[-2],runs[-1]
    old={int(x["number"]):x for x in a.get("matches",[])}
    out=[]
    for x in b.get("matches",[]):
        nr=int(x["number"])
        if nr not in old: continue
        change=recommendation_change(old[nr]["model"], x["model"])
        if change["material"]:
            out.append({"number":nr,"home":x.get("home",""),"away":x.get("away",""),**change})
    return out
