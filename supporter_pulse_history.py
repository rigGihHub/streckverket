from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from advanced_context import SupporterPulse


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class SupporterPulseSnapshot:
    schema_version: int
    coupon_fingerprint: str
    match_number: int
    home: str
    away: str
    team: str
    side: str
    competition: str
    captured_at: str
    kickoff: str | None
    source: str
    posts: int
    unique_authors: int
    confidence: float
    resignation: float
    worry: float
    optimism: float
    anger: float
    consensus: float
    tone_delta: float | None
    sample_quality: float
    market_team_win_prob: float
    result: str | None = None

    @property
    def directional_tone(self) -> float:
        # Keep this as a descriptive signal, not a model probability.
        raw = (self.confidence + self.optimism) - (self.resignation + self.worry)
        return max(-1.0, min(1.0, raw / 2.0))


def make_pulse_snapshot(
    *,
    coupon_fingerprint: str,
    match,
    team: str,
    pulse: SupporterPulse,
    data_mode: str,
    captured_at: str | None = None,
) -> SupporterPulseSnapshot:
    if str(data_mode).strip().lower() == "demo":
        raise ValueError("Demodata får inte sparas i Supporter Pulse-historiken")
    side = "home" if str(team).strip().lower() == str(match.home).strip().lower() else "away" if str(team).strip().lower() == str(match.away).strip().lower() else ""
    if not side:
        raise ValueError("Supporter Pulse-teamet måste vara hemma- eller bortalaget i matchen")
    if pulse.posts <= 0:
        raise ValueError("Supporter Pulse saknar inlägg")
    if not bool(getattr(match, "market_available", True)):
        raise ValueError("Riktig bookmakerbas krävs för Supporter Pulse-historik")
    market = list(getattr(match, "market", ()) or ())
    if len(market) != 3:
        raise ValueError("Marknadsbas 1/X/2 krävs för historisk jämförelse")
    win_prob = float(market[0] if side == "home" else market[2])
    return SupporterPulseSnapshot(
        schema_version=1,
        coupon_fingerprint=str(coupon_fingerprint),
        match_number=int(match.number),
        home=str(match.home),
        away=str(match.away),
        team=str(team),
        side=side,
        competition=str(getattr(match, "competition", "") or "Okänd tävling"),
        captured_at=captured_at or _now(),
        kickoff=str(getattr(match, "kickoff", "") or "") or None,
        source=str(pulse.source or "Supporterforum"),
        posts=int(pulse.posts),
        unique_authors=int(pulse.unique_authors),
        confidence=float(pulse.confidence),
        resignation=float(pulse.resignation),
        worry=float(pulse.worry),
        optimism=float(pulse.optimism),
        anger=float(pulse.anger),
        consensus=float(pulse.consensus),
        tone_delta=None if pulse.tone_delta is None else float(pulse.tone_delta),
        sample_quality=float(pulse.sample_quality),
        market_team_win_prob=max(0.0, min(1.0, win_prob)),
        result=None,
    )


def load_pulse_history(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def append_pulse_snapshots(path: str | Path, snapshots: Sequence[SupporterPulseSnapshot]) -> None:
    if not snapshots:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = load_pulse_history(p)
    existing = {
        (str(r.get("coupon_fingerprint", "")), int(r.get("match_number", 0) or 0), str(r.get("team", "")).lower(), str(r.get("captured_at", "")), str(r.get("source", "")))
        for r in rows
    }
    for snapshot in snapshots:
        row = asdict(snapshot)
        key = (snapshot.coupon_fingerprint, snapshot.match_number, snapshot.team.lower(), snapshot.captured_at, snapshot.source)
        if key not in existing:
            rows.append(row)
            existing.add(key)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def attach_results(path: str | Path, results: Mapping[tuple[str, int], str]) -> int:
    """Attach 1/X/2 facit without inventing missing outcomes."""
    p = Path(path)
    rows = load_pulse_history(p)
    changed = 0
    for row in rows:
        key = (str(row.get("coupon_fingerprint", "")), int(row.get("match_number", 0) or 0))
        result = str(results.get(key, "") or "").upper()
        if result not in {"1", "X", "2"}:
            continue
        if row.get("result") != result:
            row["result"] = result
            changed += 1
    if changed:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)
    return changed


def _directional(row: dict) -> float:
    raw = (float(row.get("confidence", 0) or 0) + float(row.get("optimism", 0) or 0)) - (float(row.get("resignation", 0) or 0) + float(row.get("worry", 0) or 0))
    return max(-1.0, min(1.0, raw / 2.0))


def _team_won(row: dict) -> int | None:
    result = str(row.get("result", "") or "").upper()
    side = str(row.get("side", "") or "").lower()
    if result not in {"1", "X", "2"} or side not in {"home", "away"}:
        return None
    return int((side == "home" and result == "1") or (side == "away" and result == "2"))


def signal_history_rows(history: Iterable[dict], *, min_observations: int = 30) -> list[dict]:
    """Evaluate whether pulse categories precede outcomes beyond bookmaker expectation.

    This deliberately uses market surprise (actual win - market win probability), not raw
    win rate. Otherwise favourite teams with optimistic forums would create a false edge.
    """
    groups = {
        "Hög självsäkerhet": lambda r: float(r.get("confidence", 0) or 0) >= 0.45,
        "Hög uppgivenhet": lambda r: float(r.get("resignation", 0) or 0) >= 0.45,
        "Hög oro": lambda r: float(r.get("worry", 0) or 0) >= 0.45,
        "Hög optimism": lambda r: float(r.get("optimism", 0) or 0) >= 0.45,
        "Stark positiv ton": lambda r: _directional(r) >= 0.30,
        "Stark negativ ton": lambda r: _directional(r) <= -0.30,
    }
    out=[]
    rows=list(history)
    for label, predicate in groups.items():
        selected=[]
        for row in rows:
            won=_team_won(row)
            if won is None or not predicate(row):
                continue
            market=float(row.get("market_team_win_prob", 0) or 0)
            if not 0 <= market <= 1:
                continue
            selected.append((won, market))
        n=len(selected)
        wins=sum(x[0] for x in selected)
        expected=sum(x[1] for x in selected)
        surprise=(wins-expected)/n if n else None
        if n < min_observations:
            verdict=f"För lite data ({n}/{min_observations})"
        elif surprise is not None and surprise >= 0.06:
            verdict="Lovande positiv avvikelse – kräver fortsatt validering"
        elif surprise is not None and surprise <= -0.06:
            verdict="Negativ avvikelse mot marknaden – kräver fortsatt validering"
        else:
            verdict="Ingen tydlig marginalnytta mot marknaden"
        out.append({
            "Signal": label,
            "Matcher": n,
            "Faktiska vinster": f"{wins}/{n}" if n else "–",
            "Marknaden väntade": f"{expected:.1f}" if n else "–",
            "Marknadsjusterad avvikelse": f"{surprise*100:+.1f} p.e." if surprise is not None else "–",
            "Bedömning": verdict,
        })
    return out


def competition_pulse_rows(history: Iterable[dict], *, min_observations: int = 20) -> list[dict]:
    stats=defaultdict(lambda: {"n":0,"surprise":0.0,"tone":0.0,"quality":0.0})
    for row in history:
        won=_team_won(row)
        if won is None:
            continue
        market=float(row.get("market_team_win_prob", 0) or 0)
        comp=str(row.get("competition", "") or "Okänd tävling")
        s=stats[comp]
        s["n"] += 1
        s["surprise"] += won-market
        s["tone"] += _directional(row)
        s["quality"] += float(row.get("sample_quality", 0) or 0)
    out=[]
    for comp,s in sorted(stats.items()):
        n=s["n"]
        out.append({
            "Liga/tävling": comp,
            "Observationer": n,
            "Snitt ton": f"{s['tone']/n:+.2f}" if n else "–",
            "Snitt underlagskvalitet": f"{100*s['quality']/n:.0f}%" if n else "–",
            "Marknadsjusterat utfall": f"{100*s['surprise']/n:+.1f} p.e." if n else "–",
            "Underlag": "Tillräckligt för försiktig trend" if n >= min_observations else f"För lite data ({n}/{min_observations})",
        })
    return out
