from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable, Optional, Sequence
import math
import re
import requests

from evidence import EvidenceSignal, fan_sentiment_signal, referee_signal, weather_signal_from_history
from source_consensus import DEFAULT_SOURCES, Observation


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class VenueContext:
    name: str = ""
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class RefereeAssignment:
    name: str
    source: str
    updated_at: str


@dataclass(frozen=True)
class RefereeProfile:
    matches: int
    home_win_rate: float
    draw_rate: float
    away_win_rate: float
    cards_per_match: float | None = None
    penalties_per_match: float | None = None


@dataclass(frozen=True)
class ForumPost:
    title: str
    body: str
    created_utc: float
    score: int
    comments: int
    source: str
    url: str = ""
    author: str = ""


@dataclass(frozen=True)
class ForumRadar:
    posts: int
    weighted_sentiment: float
    injury_mentions: int
    lineup_mentions: int
    transfer_mentions: int
    alert_terms: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class SupporterPulse:
    posts: int
    unique_authors: int
    confidence: float
    resignation: float
    worry: float
    optimism: float
    anger: float
    consensus: float
    tone_delta: float | None
    source: str

    @property
    def sample_quality(self) -> float:
        volume = min(1.0, self.posts / 40.0)
        diversity = min(1.0, self.unique_authors / 20.0) if self.unique_authors else 0.0
        return max(0.0, min(1.0, 0.55 * volume + 0.45 * diversity))

    @property
    def label(self) -> str:
        if self.posts < 5:
            return "För lite underlag"
        if self.resignation >= 0.55:
            return "Uppgiven"
        if self.confidence >= 0.60 and self.optimism >= 0.45:
            return "Självsäker"
        if self.worry >= 0.55:
            return "Orolig"
        if self.anger >= 0.55:
            return "Arg/missnöjd"
        if self.optimism >= 0.45:
            return "Försiktigt optimistisk"
        return "Blandad ton"


NEGATIVE = {
    "injured", "injury", "out", "doubt", "doubtful", "suspended", "suspension",
    "poor", "awful", "terrible", "crisis", "fatigue", "tired", "missing", "absent",
    "skadad", "skada", "avstängd", "frånvaro", "tveksam", "kris",
}
POSITIVE = {
    "fit", "return", "returns", "available", "strong", "confident", "boost", "back",
    "frisk", "tillbaka", "tillgänglig", "stark", "formstark",
}
INJURY_TERMS = {"injury","injured","out","doubt","doubtful","suspended","suspension","skada","skadad","avstängd"}
LINEUP_TERMS = {"lineup","xi","starting","bench","formation","startelva","elva","bänk"}
TRANSFER_TERMS = {"signing","signed","transfer","loan","new signing","värvning","nyförvärv","lån"}


def extract_api_football_fixture_context(item: dict[str, Any]) -> tuple[VenueContext, RefereeAssignment | None]:
    fixture = item.get("fixture") or {}
    venue = fixture.get("venue") or {}
    vc = VenueContext(name=str(venue.get("name") or ""), city=str(venue.get("city") or ""))
    referee = str(fixture.get("referee") or "").strip()
    assignment = RefereeAssignment(referee, "API-Football", _now()) if referee else None
    return vc, assignment


def fetch_open_meteo_geocode(query: str, *, count: int = 5) -> list[dict[str, Any]]:
    if not str(query).strip():
        return []
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": str(query).strip(), "count": int(count), "language": "en", "format": "json"},
        timeout=12,
    )
    r.raise_for_status()
    return list((r.json() or {}).get("results") or [])


def resolve_venue_coordinates(venue: VenueContext) -> VenueContext:
    queries = [q for q in (f"{venue.name} {venue.city}".strip(), venue.city, venue.name) if q]
    for query in queries:
        rows = fetch_open_meteo_geocode(query, count=5)
        if not rows:
            continue
        # Geocoding is intentionally conservative: prefer exact city text if available.
        city_norm = re.sub(r"\W+", "", venue.city.lower())
        ranked = []
        for row in rows:
            name = str(row.get("name") or "")
            admin = " ".join(str(row.get(k) or "") for k in ("admin1","admin2","country"))
            hay = re.sub(r"\W+", "", (name+" "+admin).lower())
            bonus = 1.0 if city_norm and city_norm in hay else 0.0
            ranked.append((bonus, row))
        ranked.sort(key=lambda x:x[0], reverse=True)
        row = ranked[0][1]
        if row.get("latitude") is not None and row.get("longitude") is not None:
            return VenueContext(venue.name, venue.city, float(row["latitude"]), float(row["longitude"]))
    return venue


def build_referee_profile(fixtures: Sequence[dict[str, Any]], referee_name: str) -> RefereeProfile:
    target = referee_name.strip().lower()
    selected=[]
    cards=[]; penalties=[]
    for item in fixtures:
        fixture=item.get("fixture") or {}
        if str(fixture.get("referee") or "").strip().lower() != target:
            continue
        goals=item.get("goals") or {}
        h,a=goals.get("home"),goals.get("away")
        if h is None or a is None:
            continue
        selected.append((int(h),int(a)))
        stat=item.get("referee_stats") or {}
        if stat.get("cards") is not None: cards.append(float(stat["cards"]))
        if stat.get("penalties") is not None: penalties.append(float(stat["penalties"]))
    n=len(selected)
    if not n:
        return RefereeProfile(0,0.0,0.0,0.0,None,None)
    hw=sum(h>a for h,a in selected)/n; dr=sum(h==a for h,a in selected)/n; aw=sum(h<a for h,a in selected)/n
    return RefereeProfile(n,hw,dr,aw,mean(cards) if cards else None,mean(penalties) if penalties else None)


def referee_matchup_signal(profile: RefereeProfile, *, league_home_win_rate: float, source: str = "historical referee sample") -> EvidenceSignal:
    if profile.matches <= 0:
        return referee_signal(home_style_edge=0.0, sample_size=0, source=source, explanation="Ingen historik")
    # Shrunk difference vs league base. This is deliberately tiny and should be backtested.
    raw = profile.home_win_rate - float(league_home_win_rate)
    shrink = profile.matches / (profile.matches + 30.0)
    edge = max(-1.0, min(1.0, (raw * shrink) / 0.12))
    return referee_signal(
        home_style_edge=edge,
        sample_size=profile.matches,
        source=source,
        explanation=f"Domarens hemmautfall jämfört med ligabas, shrinkad på {profile.matches} matcher.",
    )


def fetch_reddit_subreddit_search(subreddit: str, query: str, *, limit: int = 25, user_agent: str = "Stryktips13/1.3") -> list[ForumPost]:
    """Lågviktsradar. Reddit kan kräva OAuth; fel ska isoleras av pipelinen."""
    if not subreddit.strip() or not query.strip():
        return []
    url=f"https://www.reddit.com/r/{subreddit.strip()}/search.json"
    r=requests.get(url, params={"q":query,"restrict_sr":"on","sort":"new","t":"week","limit":int(limit),"raw_json":1}, headers={"User-Agent":user_agent}, timeout=12)
    r.raise_for_status()
    out=[]
    for child in (((r.json() or {}).get("data") or {}).get("children") or []):
        d=(child or {}).get("data") or {}
        out.append(ForumPost(
            title=str(d.get("title") or ""), body=str(d.get("selftext") or ""),
            created_utc=float(d.get("created_utc") or 0), score=int(d.get("score") or 0),
            comments=int(d.get("num_comments") or 0), source=f"Reddit r/{subreddit}",
            url="https://www.reddit.com"+str(d.get("permalink") or ""), author=str(d.get("author") or ""),
        ))
    return out



CONFIDENCE_TERMS = {
    "confident", "easy", "win", "winning", "sure", "certain", "comfortable", "dominate",
    "säker", "vinner", "vinst", "enkelt", "komfortabel", "dominerar", "självsäker",
}
RESIGNATION_TERMS = {
    "hopeless", "no chance", "finished", "done", "give up", "season over", "we're cooked",
    "ingen chans", "kört", "uppgiven", "säsongen är över", "ger upp", "hopplöst",
}
WORRY_TERMS = {
    "worried", "worry", "nervous", "concerned", "fear", "afraid", "problem", "weak",
    "orolig", "oro", "nervös", "bekymrad", "rädd", "problem", "svag",
}
ANGER_TERMS = {
    "furious", "angry", "disgrace", "embarrassing", "pathetic", "fraud", "sack",
    "rasande", "arg", "skandal", "pinsamt", "patetiskt", "sparka",
}
OPTIMISM_TERMS = {
    "hope", "positive", "good feeling", "believe", "excited", "promising", "strong",
    "hopp", "positiv", "bra känsla", "tror", "taggad", "lovande", "stark",
}

def _phrase_score(text: str, terms: set[str]) -> int:
    t = text.lower()
    return sum(1 for term in terms if term in t)

def analyze_supporter_pulse(posts: Iterable[ForumPost], *, baseline_tone: float | None = None) -> SupporterPulse:
    rows = list(posts)
    if not rows:
        return SupporterPulse(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, "Forum")
    source = rows[0].source
    authors = {p.author.strip().lower() for p in rows if p.author.strip() and p.author.strip().lower() not in {"[deleted]", "deleted"}}
    totals = {"confidence": 0.0, "resignation": 0.0, "worry": 0.0, "optimism": 0.0, "anger": 0.0}
    per_post_signs=[]
    total_weight=0.0
    for p in rows:
        text=f"{p.title} {p.body}".lower()
        weight=min(3.0, 1.0 + math.log1p(max(0,p.score)+max(0,p.comments))/4.0)
        total_weight += weight
        local={
            "confidence": _phrase_score(text, CONFIDENCE_TERMS),
            "resignation": _phrase_score(text, RESIGNATION_TERMS),
            "worry": _phrase_score(text, WORRY_TERMS),
            "optimism": _phrase_score(text, OPTIMISM_TERMS),
            "anger": _phrase_score(text, ANGER_TERMS),
        }
        for k,v in local.items(): totals[k] += weight * min(2, v)
        pos = local["confidence"] + local["optimism"]
        neg = local["resignation"] + local["worry"] + local["anger"]
        per_post_signs.append(1 if pos > neg else (-1 if neg > pos else 0))
    denom=max(1.0,total_weight)
    norm=lambda x: max(0.0,min(1.0,x/denom))
    confidence=norm(totals["confidence"]); resignation=norm(totals["resignation"]); worry=norm(totals["worry"]); optimism=norm(totals["optimism"]); anger=norm(totals["anger"])
    non_neutral=[x for x in per_post_signs if x]
    consensus=0.0
    if non_neutral:
        consensus=abs(sum(non_neutral))/len(non_neutral)
    current_tone=max(-1.0,min(1.0,(confidence+optimism-resignation-worry-anger)/2.0))
    tone_delta=None if baseline_tone is None else max(-2.0,min(2.0,current_tone-float(baseline_tone)))
    return SupporterPulse(len(rows), len(authors), confidence, resignation, worry, optimism, anger, consensus, tone_delta, source)

def supporter_pulse_model_signal(pulse: SupporterPulse, *, independently_verified: bool, historically_validated: bool) -> EvidenceSignal:
    """Supporter Pulse får modellpåverkan först efter både oberoende verifiering och historisk validering."""
    directional=(pulse.confidence+pulse.optimism)-(pulse.resignation+pulse.worry)
    edge=max(-1.0,min(1.0,directional/2.0))
    sig=fan_sentiment_signal(
        relative_sentiment_edge=edge,
        post_count=pulse.posts,
        source=pulse.source,
        explanation=f"Supporter Pulse: {pulse.label}. Konsensus {pulse.consensus:.0%}. Signal är spärrad utan historiskt bevisad marginalnytta.",
    )
    verified=bool(independently_verified and historically_validated and pulse.sample_quality >= 0.45 and pulse.consensus >= 0.35)
    if verified:
        return sig
    return EvidenceSignal(**{**sig.__dict__, "is_verified": False})

def analyze_forum_posts(posts: Iterable[ForumPost]) -> ForumRadar:
    rows=list(posts)
    if not rows:
        return ForumRadar(0,0.0,0,0,0,(),"Forum")
    pos=neg=0.0; inj=line=trans=0; alerts=set(); source=rows[0].source
    for p in rows:
        text=(p.title+" "+p.body).lower()
        tokens=set(re.findall(r"[a-zåäö]+", text))
        weight=min(3.0, 1.0 + math.log1p(max(0,p.score)+max(0,p.comments))/4.0)
        pos += weight*len(tokens & POSITIVE); neg += weight*len(tokens & NEGATIVE)
        if tokens & INJURY_TERMS: inj += 1; alerts.add("frånvaro")
        if tokens & LINEUP_TERMS: line += 1; alerts.add("startelva")
        if tokens & TRANSFER_TERMS or "new signing" in text: trans += 1; alerts.add("nyförvärv")
    sentiment=(pos-neg)/max(1.0,pos+neg)
    return ForumRadar(len(rows),max(-1.0,min(1.0,sentiment)),inj,line,trans,tuple(sorted(alerts)),source)


def forum_radar_observations(radar: ForumRadar, *, team_key: str) -> list[Observation]:
    """Radar claims are direct=False: they must not by themselves become trusted facts."""
    if radar.posts <= 0:
        return []
    source = DEFAULT_SOURCES.get("supporter_forum")
    if source is None:
        # Import lazily to avoid hard coupling to a specific registry version.
        from source_consensus import SourceProfile
        source = SourceProfile("supporter_forum", "Supporterforum", "community", 0.30, "forum-community")
    obs=[]
    for term in radar.alert_terms:
        obs.append(Observation(f"forum:{team_key}:{term}", term, source, _now(), confidence=min(0.55,0.20+radar.posts/100), direct=False))
    return obs


def supporter_sentiment_model_signal(radar: ForumRadar, *, independently_verified: bool) -> EvidenceSignal:
    """Sentiment changes probabilities only after independent verification flag is true."""
    sig=fan_sentiment_signal(
        relative_sentiment_edge=radar.weighted_sentiment,
        post_count=radar.posts,
        source=radar.source,
        explanation="Supportersentiment är en lågviktsindikator och kräver oberoende verifiering.",
    )
    if independently_verified:
        return sig
    return EvidenceSignal(**{**sig.__dict__, "is_verified": False})
