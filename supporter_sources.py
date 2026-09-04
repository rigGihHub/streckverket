from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
import json
import re
import time

from advanced_context import ForumPost, SupporterPulse, analyze_supporter_pulse, fetch_reddit_subreddit_search


def _norm(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    aliases = {
        "spurs": "tottenham hotspur",
        "tottenham": "tottenham hotspur",
        "man utd": "manchester united",
        "man united": "manchester united",
        "man city": "manchester city",
    }
    return aliases.get(s, s)


@dataclass(frozen=True)
class SupporterSourceSpec:
    team: str
    platform: str
    locator: str
    display_name: str
    aliases: tuple[str, ...] = ()
    enabled: bool = True
    verified_at: str = ""
    source_url: str = ""
    notes: str = ""

    def __post_init__(self):
        if self.platform not in {"reddit"}:
            raise ValueError(f"Unsupported supporter platform: {self.platform}")
        if not self.team.strip() or not self.locator.strip():
            raise ValueError("Supporter source requires team and locator")

    @property
    def source_key(self) -> str:
        return f"{self.platform}:{self.locator.strip().lower()}"

    def matches_team(self, team_name: str) -> bool:
        target = _norm(team_name)
        names = {_norm(self.team), *(_norm(x) for x in self.aliases)}
        return target in names


@dataclass(frozen=True)
class PulseCollection:
    team: str
    opponent: str
    source: SupporterSourceSpec | None
    pulse: SupporterPulse
    posts: tuple[ForumPost, ...]
    status: str
    query_count: int
    filtered_out: int
    relevant_posts: int = 0
    relevance_rate: float = 0.0

    @property
    def available(self) -> bool:
        return self.source is not None and self.pulse.posts > 0


DEFAULT_SOURCES: tuple[SupporterSourceSpec, ...] = (
    SupporterSourceSpec(team="Tottenham Hotspur", platform="reddit", locator="coys", display_name="Reddit r/coys", aliases=("Tottenham", "Spurs", "Tottenham Hotspur FC"), verified_at="2026-09-04", source_url="https://www.reddit.com/r/coys/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Arsenal", platform="reddit", locator="Gunners", display_name="Reddit r/Gunners", aliases=("Arsenal FC",), verified_at="2026-09-04", source_url="https://www.reddit.com/r/Gunners/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Manchester United", platform="reddit", locator="reddevils", display_name="Reddit r/reddevils", aliases=("Man Utd", "Man United", "Manchester United FC"), verified_at="2026-09-04", source_url="https://www.reddit.com/r/reddevils/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Chelsea", platform="reddit", locator="chelseafc", display_name="Reddit r/chelseafc", aliases=("Chelsea FC",), verified_at="2026-09-04", source_url="https://www.reddit.com/r/chelseafc/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Manchester City", platform="reddit", locator="MCFC", display_name="Reddit r/MCFC", aliases=("Man City", "Manchester City FC"), verified_at="2026-09-04", source_url="https://www.reddit.com/r/MCFC/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Aston Villa", platform="reddit", locator="avfc", display_name="Reddit r/avfc", aliases=("Aston Villa FC", "Villa"), verified_at="2026-09-04", source_url="https://www.reddit.com/r/avfc/", notes="Explicit mapping; verified manually."),
    SupporterSourceSpec(team="Everton", platform="reddit", locator="Everton", display_name="Reddit r/Everton", aliases=("Everton FC",), verified_at="2026-09-04", source_url="https://www.reddit.com/r/Everton/", notes="Explicit mapping; verified manually."),
)


def load_supporter_sources(path: str | Path | None = None, *, extra_json: str = "") -> list[SupporterSourceSpec]:
    rows = [*DEFAULT_SOURCES]
    if path:
        p = Path(path)
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    rows.extend(SupporterSourceSpec(**_coerce_row(x)) for x in raw if isinstance(x, dict))
            except Exception:
                # A broken optional registry must not break coupon analysis.
                pass
    if extra_json.strip():
        try:
            raw = json.loads(extra_json)
            if isinstance(raw, list):
                rows.extend(SupporterSourceSpec(**_coerce_row(x)) for x in raw if isinstance(x, dict))
        except Exception:
            pass
    dedup: dict[str, SupporterSourceSpec] = {}
    for row in rows:
        if row.enabled:
            dedup[row.source_key] = row
    return list(dedup.values())


def _coerce_row(row: dict) -> dict:
    data = dict(row)
    aliases = data.get("aliases", ())
    if isinstance(aliases, list):
        data["aliases"] = tuple(str(x) for x in aliases)
    elif not isinstance(aliases, tuple):
        data["aliases"] = (str(aliases),) if aliases else ()
    return data


def save_supporter_sources(path: str | Path, sources: Iterable[SupporterSourceSpec]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for source in sources:
        row = asdict(source)
        row["aliases"] = list(source.aliases)
        payload.append(row)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def sources_for_team(team_name: str, sources: Sequence[SupporterSourceSpec]) -> list[SupporterSourceSpec]:
    return [s for s in sources if s.enabled and s.matches_team(team_name)]


def baseline_tone(history: Iterable[dict], *, team: str, source_name: str, limit: int = 12) -> float | None:
    rows = [
        r for r in history
        if _norm(str(r.get("team", ""))) == _norm(team)
        and str(r.get("source", "")) == str(source_name)
    ]
    if len(rows) < 3:
        return None
    rows = rows[-max(3, int(limit)):]
    tones = []
    for r in rows:
        raw = (
            float(r.get("confidence", 0) or 0)
            + float(r.get("optimism", 0) or 0)
            - float(r.get("resignation", 0) or 0)
            - float(r.get("worry", 0) or 0)
            - float(r.get("anger", 0) or 0)
        ) / 2.0
        tones.append(max(-1.0, min(1.0, raw)))
    return sum(tones) / len(tones) if tones else None


def _dedupe_posts(posts: Iterable[ForumPost]) -> list[ForumPost]:
    out = []
    seen = set()
    for post in posts:
        url_key = post.url.strip().lower() if post.url else ""
        title_key = re.sub(r"\s+", " ", post.title.strip().lower())
        key = ("url", url_key) if url_key else ("title", title_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(post)
    return out


def _filter_time_window(posts: Iterable[ForumPost], *, now_ts: float, max_age_hours: float, kickoff_ts: float | None) -> tuple[list[ForumPost], int]:
    oldest = now_ts - max(1.0, float(max_age_hours)) * 3600.0
    kept = []
    removed = 0
    upper = min(now_ts, kickoff_ts) if kickoff_ts is not None else now_ts
    for post in posts:
        created = float(post.created_utc or 0)
        if created <= 0 or created < oldest or created > upper:
            removed += 1
            continue
        kept.append(post)
    return kept, removed



_MATCH_TERMS = (
    "match", "game", "fixture", "lineup", "line-up", "starting xi", "start", "injury",
    "injured", "suspended", "suspension", "form", "manager", "coach", "tactic", "formation",
    "win", "draw", "lose", "loss", "beat", "chance", "confident", "worried", "nervous",
)
_NOISE_TERMS = (
    "merch", "merchandise", "shirt collection", "kit collection", "nostalgia", "throwback",
    "meme", "ticket", "tickets", "fantasy", "fpl", "transfer", "signed", "signing", "wallpaper",
)

def _tokens(value: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", _norm(value)) if len(x) >= 3}

def post_relevance_score(post: ForumPost, *, team: str, opponent: str) -> float:
    """Conservative lexical relevance score. It filters noise; it never verifies a factual claim."""
    text = f"{post.title} {post.body}".lower()
    score = 0.0
    opp_tokens = _tokens(opponent)
    team_tokens = _tokens(team)
    words = _tokens(text)
    if opp_tokens and words.intersection(opp_tokens):
        score += 0.55
    if team_tokens and words.intersection(team_tokens):
        score += 0.15
    hits = sum(1 for term in _MATCH_TERMS if term in text)
    score += min(0.45, hits * 0.15)
    noise = sum(1 for term in _NOISE_TERMS if term in text)
    score -= min(0.60, noise * 0.25)
    return max(0.0, min(1.0, score))

def filter_relevant_posts(posts: Iterable[ForumPost], *, team: str, opponent: str, threshold: float = 0.15) -> tuple[list[ForumPost], float]:
    rows = list(posts)
    if not rows:
        return [], 0.0
    relevant = [p for p in rows if post_relevance_score(p, team=team, opponent=opponent) >= threshold]
    return relevant, len(relevant) / len(rows)

def collect_team_pulse(
    *,
    team: str,
    opponent: str,
    sources: Sequence[SupporterSourceSpec],
    history: Iterable[dict] = (),
    now_ts: float | None = None,
    kickoff_ts: float | None = None,
    max_age_hours: float = 96,
    limit_per_query: int = 30,
) -> PulseCollection:
    matched = sources_for_team(team, sources)
    if not matched:
        empty = analyze_supporter_pulse([])
        return PulseCollection(team, opponent, None, empty, (), "Ingen verifierad supporterkälla registrerad", 0, 0, 0, 0.0)

    source = matched[0]
    if source.platform != "reddit":
        empty = analyze_supporter_pulse([])
        return PulseCollection(team, opponent, source, empty, (), "Källtypen saknar aktiv adapter", 0, 0, 0, 0.0)

    queries = []
    opponent_q = str(opponent or "").strip()
    if opponent_q:
        queries.append(opponent_q)
    queries.extend(["match", "team"])

    all_posts: list[ForumPost] = []
    errors = []
    for query in queries:
        try:
            all_posts.extend(fetch_reddit_subreddit_search(source.locator, query, limit=limit_per_query))
        except Exception as exc:
            errors.append(type(exc).__name__)

    deduped = _dedupe_posts(all_posts)
    current_ts = float(now_ts if now_ts is not None else time.time())
    filtered, removed = _filter_time_window(deduped, now_ts=current_ts, max_age_hours=max_age_hours, kickoff_ts=kickoff_ts)
    relevant, relevance_rate = filter_relevant_posts(filtered, team=team, opponent=opponent)
    baseline = baseline_tone(history, team=team, source_name=source.display_name)
    pulse = analyze_supporter_pulse(relevant, baseline_tone=baseline)
    if relevant:
        pulse = SupporterPulse(**{**pulse.__dict__, "source": source.display_name})
        status = f"{len(relevant)} relevanta av {len(filtered)} färska inlägg"
    elif filtered:
        status = "Färska inlägg hittades men inget passerade relevansfiltret"
    elif errors:
        status = "Supporterkällan kunde inte hämtas"
    else:
        status = "Källan svarade men gav inget färskt underlag"
    return PulseCollection(team, opponent, source, pulse, tuple(relevant), status, len(queries), removed + (len(filtered) - len(relevant)), len(relevant), relevance_rate)


def collection_rows(collections: Iterable[PulseCollection]) -> list[dict]:
    out = []
    for c in collections:
        out.append({
            "Lag": c.team,
            "Källa": c.source.display_name if c.source else "Saknas",
            "Status": c.status,
            "Inlägg": c.pulse.posts,
            "Skribenter": c.pulse.unique_authors,
            "Ton": c.pulse.label,
            "Underlag": f"{100*c.pulse.sample_quality:.0f}%",
            "Matchrelevans": f"{100*c.relevance_rate:.0f}%",
            "Konsensus": f"{100*c.pulse.consensus:.0f}%",
            "Tonförändring": "–" if c.pulse.tone_delta is None else f"{c.pulse.tone_delta:+.2f}",
        })
    return out
