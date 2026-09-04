from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from readiness_diagnostics import ReadinessDiagnostics, build_readiness_diagnostics


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _competition_name(match) -> str:
    value = str(getattr(match, "competition", "") or "").strip()
    return value or "Okänd tävling"


def build_quality_snapshot(*, coupon_fingerprint: str, matches: Sequence, cards: Sequence, stages: Sequence, data_mode: str, duration_seconds: float | None = None, match_provenance: Sequence = ()) -> dict:
    if str(data_mode).strip().lower() == "demo":
        raise ValueError("Demodata får inte sparas i datakvalitetshistoriken")
    if not matches or not cards or len(matches) != len(cards):
        raise ValueError("Matcher och analyskort måste finnas i samma antal")

    market_missing = sum(not bool(getattr(m, "market_available", True)) for m in matches)
    diag = build_readiness_diagnostics(cards, stages, market_missing_count=market_missing)

    competitions: dict[str, dict] = {}
    for match, card in zip(matches, cards):
        comp = _competition_name(match)
        row = competitions.setdefault(comp, {
            "matches": 0,
            "readiness_sum": 0,
            "layers_available": defaultdict(int),
            "verified_signal_sources": defaultdict(int),
        })
        row["matches"] += 1
        row["readiness_sum"] += int(getattr(card, "readiness_score", 0) or 0)
        missing = set(getattr(card, "missing", ()) or ())
        for layer in (x.key for x in diag.layers):
            if layer not in missing and not (layer == "market" and not bool(getattr(match, "market_available", True))):
                row["layers_available"][layer] += 1
        for signal in getattr(card, "used_signals", ()) or ():
            source = str(getattr(signal, "source", "") or "Okänd källa").strip()
            if source:
                row["verified_signal_sources"][source] += 1

    competition_rows = []
    for name, row in sorted(competitions.items()):
        total = row["matches"]
        competition_rows.append({
            "competition": name,
            "matches": total,
            "avg_readiness": round(row["readiness_sum"] / total, 1) if total else 0.0,
            "layer_coverage": {k: round(row["layers_available"].get(k, 0) / total, 4) if total else 0.0 for k in (x.key for x in diag.layers)},
            "verified_signal_sources": dict(row["verified_signal_sources"]),
        })

    return {
        "schema_version": 2,
        "captured_at": _now(),
        "coupon_fingerprint": str(coupon_fingerprint),
        "data_mode": str(data_mode),
        "duration_seconds": None if duration_seconds is None else round(float(duration_seconds), 3),
        "match_count": len(matches),
        "priority_key": diag.priority_key,
        "layers": [{
            "key": x.key, "available": x.available, "missing": x.missing, "total": x.total,
            "coverage_pct": x.coverage_pct,
        } for x in diag.layers],
        "sources": [{
            "name": x.name, "ok": x.ok, "matched": x.matched, "attempted": x.attempted,
            "coverage_pct": x.coverage_pct, "status": x.status,
        } for x in diag.sources],
        "competitions": competition_rows,
        "match_provenance": [{
            "match_number": int(getattr(x, "match_number", 0) or 0),
            "competition": str(getattr(x, "competition", "") or "Okänd tävling"),
            "source": str(getattr(x, "source", "") or "Okänd källa"),
            "matched_units": max(0, int(getattr(x, "matched_units", 0) or 0)),
            "attempted_units": max(0, int(getattr(x, "attempted_units", 0) or 0)),
            "status": str(getattr(x, "status", "") or ""),
            "reason_code": str(getattr(x, "reason_code", "") or ""),
        } for x in (match_provenance or ())],
    }


def load_quality_history(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def append_quality_snapshot(path: str | Path, snapshot: dict) -> None:
    if str(snapshot.get("data_mode", "")).strip().lower() == "demo":
        raise ValueError("Demodata får inte sparas i datakvalitetshistoriken")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = load_quality_history(p)
    rows.append(snapshot)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def source_history_rows(history: Iterable[dict], *, min_snapshots: int = 3) -> list[dict]:
    stats = defaultdict(lambda: {"snapshots": 0, "matched": 0, "attempted": 0, "errors": 0})
    for snap in history:
        if str(snap.get("data_mode", "")).strip().lower() == "demo":
            continue
        seen = set()
        for src in snap.get("sources", []) or []:
            name = str(src.get("name", "Okänd källa"))
            s = stats[name]
            if name not in seen:
                s["snapshots"] += 1
                seen.add(name)
            s["matched"] += max(0, int(src.get("matched", 0) or 0))
            s["attempted"] += max(0, int(src.get("attempted", 0) or 0))
            if not bool(src.get("ok", False)):
                s["errors"] += 1
    out = []
    for name, s in sorted(stats.items()):
        pct = round(100 * s["matched"] / s["attempted"]) if s["attempted"] else None
        enough = s["snapshots"] >= min_snapshots
        out.append({
            "Källa": name,
            "Kuponger": s["snapshots"],
            "Matchat": f"{s['matched']}/{s['attempted']}" if s["attempted"] else "–",
            "Historisk täckning": f"{pct}%" if pct is not None else "–",
            "Körningar med fel": s["errors"],
            "Bedömning": _source_assessment(pct, s["errors"], s["snapshots"], enough, min_snapshots),
        })
    return out


def _source_assessment(pct: int | None, errors: int, snapshots: int, enough: bool, min_snapshots: int) -> str:
    if not enough:
        return f"För lite data ({snapshots}/{min_snapshots} kuponger)"
    if errors >= max(2, snapshots // 2):
        return "Instabil källa"
    if pct is None:
        return "Ingen mätbar matchningsgrad"
    if pct >= 80:
        return "Stark historisk täckning"
    if pct >= 50:
        return "Varierande historisk täckning"
    return "Svag historisk täckning"


def competition_history_rows(history: Iterable[dict], *, min_matches: int = 10) -> list[dict]:
    stats = defaultdict(lambda: {"matches": 0, "readiness_weighted": 0.0, "layers": defaultdict(float), "signals": defaultdict(int), "snapshots": 0})
    for snap in history:
        if str(snap.get("data_mode", "")).strip().lower() == "demo":
            continue
        for comp in snap.get("competitions", []) or []:
            name = str(comp.get("competition", "Okänd tävling"))
            n = max(0, int(comp.get("matches", 0) or 0))
            s = stats[name]
            s["matches"] += n
            s["snapshots"] += 1
            s["readiness_weighted"] += float(comp.get("avg_readiness", 0) or 0) * n
            for key, frac in (comp.get("layer_coverage", {}) or {}).items():
                s["layers"][key] += float(frac or 0) * n
            for source, count in (comp.get("verified_signal_sources", {}) or {}).items():
                s["signals"][source] += int(count or 0)
    out = []
    for name, s in sorted(stats.items()):
        n = s["matches"]
        weak_layer = "–"
        if n and s["layers"]:
            key, value = min(s["layers"].items(), key=lambda kv: kv[1] / n)
            weak_layer = f"{key}: {round(100*value/n)}%"
        top_source = "–"
        if s["signals"]:
            src, count = max(s["signals"].items(), key=lambda kv: kv[1])
            top_source = f"{src} ({count})"
        out.append({
            "Liga/tävling": name,
            "Matcher": n,
            "Kuponger": s["snapshots"],
            "Snitt-readiness": f"{s['readiness_weighted']/n:.0f}/100" if n else "–",
            "Svagaste informationslager": weak_layer,
            "Vanligaste verifierade signalkälla": top_source,
            "Underlag": "Tillräckligt för försiktig trend" if n >= min_matches else f"För lite data ({n}/{min_matches} matcher)",
        })
    return out


def competition_source_history_rows(history: Iterable[dict], *, min_attempted_units: int = 10) -> list[dict]:
    """Aggregate exact source matching by competition from match-level provenance.

    Older snapshots without match_provenance are intentionally ignored instead of
    backfilling guessed per-league values from coupon-level stage totals.
    """
    stats = defaultdict(lambda: {"matched": 0, "attempted": 0, "matches": set(), "snapshots": set()})
    for snap_index, snap in enumerate(history):
        if str(snap.get("data_mode", "")).strip().lower() == "demo":
            continue
        fingerprint = str(snap.get("coupon_fingerprint", "") or f"snapshot:{snap_index}")
        for row in snap.get("match_provenance", []) or []:
            comp = str(row.get("competition", "") or "Okänd tävling")
            source = str(row.get("source", "") or "Okänd källa")
            attempted = max(0, int(row.get("attempted_units", 0) or 0))
            matched = max(0, min(attempted, int(row.get("matched_units", 0) or 0)))
            if attempted <= 0:
                continue
            s = stats[(comp, source)]
            s["matched"] += matched
            s["attempted"] += attempted
            s["matches"].add((fingerprint, int(row.get("match_number", 0) or 0)))
            s["snapshots"].add(fingerprint)
    out = []
    for (comp, source), s in sorted(stats.items()):
        attempted = s["attempted"]
        pct = round(100 * s["matched"] / attempted) if attempted else None
        enough = attempted >= min_attempted_units
        if not enough:
            assessment = f"För lite data ({attempted}/{min_attempted_units} försök)"
        elif pct >= 80:
            assessment = "Stark matchning"
        elif pct >= 50:
            assessment = "Varierande matchning"
        else:
            assessment = "Svag matchning"
        out.append({
            "Liga/tävling": comp,
            "Källa": source,
            "Matcher": len(s["matches"]),
            "Kuponger": len(s["snapshots"]),
            "Matchat": f"{s['matched']}/{attempted}",
            "Täckning": f"{pct}%" if pct is not None else "–",
            "Bedömning": assessment,
        })
    return out


_FAILURE_LABELS = {
    "api_key_missing": "API-nyckel saknas",
    "api_error": "API-fel",
    "missing_match_date": "Matchdatum saknas",
    "no_candidates": "Ingen kandidatdata",
    "ambiguous_team_match": "Tvetydig lagnamnsmatchning",
    "low_confidence_team_match": "För låg säkerhet i lagnamnsmatchning",
    "ambiguous_fixture_match": "Tvetydig fixture-matchning",
    "no_secure_match": "Ingen säker matchning",
}

def failure_reason_history_rows(history: Iterable[dict], *, min_failures: int = 3) -> list[dict]:
    """Aggregate explicit match-level failure causes.

    Only v3.18+ snapshots with reason_code contribute. Matched rows are ignored and
    older free-text statuses are never guessed into categories.
    """
    stats = defaultdict(lambda: {"failures": 0, "matches": set(), "snapshots": set()})
    for snap_index, snap in enumerate(history):
        if str(snap.get("data_mode", "")).strip().lower() == "demo":
            continue
        fingerprint = str(snap.get("coupon_fingerprint", "") or f"snapshot:{snap_index}")
        for row in snap.get("match_provenance", []) or []:
            code = str(row.get("reason_code", "") or "").strip()
            if not code or code == "matched":
                continue
            source = str(row.get("source", "") or "Okänd källa")
            comp = str(row.get("competition", "") or "Okänd tävling")
            key = (source, comp, code)
            s = stats[key]
            s["failures"] += 1
            s["matches"].add((fingerprint, int(row.get("match_number", 0) or 0)))
            s["snapshots"].add(fingerprint)
    out=[]
    for (source, comp, code), s in sorted(stats.items(), key=lambda kv: (-kv[1]["failures"], kv[0])):
        n=s["failures"]
        out.append({
            "Källa": source,
            "Liga/tävling": comp,
            "Felorsak": _FAILURE_LABELS.get(code, code),
            "Misslyckanden": n,
            "Matcher": len(s["matches"]),
            "Kuponger": len(s["snapshots"]),
            "Underlag": "Återkommande problem" if n >= min_failures else f"För lite data ({n}/{min_failures} missar)",
        })
    return out
