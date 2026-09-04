from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Iterable, Sequence
import re
import unicodedata

from core import MatchInput, market_probabilities
from data_sources import fetch_svenskaspel_current, fetch_the_odds_api, match_odds_to_coupon
from enrichment import fetch_team_finished_matches, summarize_team_form, form_signal_from_summaries
from competition_discovery import fetch_competitions, build_catalog, discover_coupon
from context_sources import fetch_api_football_injuries, fetch_api_football_lineups
from model_engine import parse_api_football_injuries, missing_value, build_match_signals
from pipeline import ProviderOutput, run_match_pipeline
from evidence import make_signal
from match_intelligence import IntelligenceClaim, resolve_claim
from source_consensus import DEFAULT_SOURCES, Observation
from api_cache import CachePolicy, CacheStats, cached_call, cache_stats, stats_delta


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm(value: str) -> str:
    s=unicodedata.normalize("NFKD", str(value or "")).encode("ascii","ignore").decode().lower()
    s=s.replace("&", " and ")
    s=re.sub(r"\b(fc|afc|cf|ac|sc|the)\b", " ", s)
    s=re.sub(r"[^a-z0-9]+", " ", s)
    aliases={
        "man utd":"manchester united", "man united":"manchester united",
        "man city":"manchester city", "spurs":"tottenham hotspur",
        "sheff utd":"sheffield united", "sheff wed":"sheffield wednesday",
        "qpr":"queens park rangers", "wolves":"wolverhampton wanderers",
        "west brom":"west bromwich albion", "nottm forest":"nottingham forest",
    }
    s=" ".join(s.split())
    return aliases.get(s,s)


def name_similarity(a: str, b: str) -> float:
    na,nb=_norm(a),_norm(b)
    if not na or not nb: return 0.0
    if na == nb: return 1.0
    seq=SequenceMatcher(None,na,nb).ratio()
    ta,tb=set(na.split()),set(nb.split())
    jac=len(ta&tb)/max(1,len(ta|tb))
    containment=min(1.0, len(ta&tb)/max(1,min(len(ta),len(tb))))
    return max(seq, 0.62*jac+0.38*containment)


@dataclass(frozen=True)
class FixtureMatch:
    fixture_id: int | None
    home_id: int | None
    away_id: int | None
    home_name: str
    away_name: str
    kickoff: str | None
    score: float
    confidence: str


def match_api_football_fixture(match: MatchInput, payload: dict[str,Any], *, high: float=0.88, review: float=0.78, min_margin: float=0.035) -> FixtureMatch:
    rows=[]
    for item in payload.get("response", []) if isinstance(payload,dict) else []:
        teams=item.get("teams") or {}; h=teams.get("home") or {}; a=teams.get("away") or {}
        hs=name_similarity(match.home, h.get("name") or "")
        aas=name_similarity(match.away, a.get("name") or "")
        # Orientation matters. Prevent a strong match caused by only one side.
        score=0.52*min(hs,aas)+0.48*((hs+aas)/2)
        rows.append((score,hs,aas,item))
    rows.sort(key=lambda x:x[0], reverse=True)
    if not rows:
        return FixtureMatch(None,None,None,"","",None,0.0,"Ingen")
    score,hs,aas,item=rows[0]
    margin=score-(rows[1][0] if len(rows)>1 else 0.0)
    conf="Hög" if score>=high and hs>=0.84 and aas>=0.84 and margin>=min_margin else "Granska" if score>=review else "Ingen"
    f=item.get("fixture") or {}; teams=item.get("teams") or {}; h=teams.get("home") or {}; a=teams.get("away") or {}
    return FixtureMatch(
        int(f.get("id")) if f.get("id") is not None else None,
        int(h.get("id")) if h.get("id") is not None else None,
        int(a.get("id")) if a.get("id") is not None else None,
        str(h.get("name") or ""), str(a.get("name") or ""), f.get("date"), float(score), conf,
    )


def parse_coupon_date(kickoff: str | None) -> str | None:
    if not kickoff: return None
    m=re.match(r"(\d{4}-\d{2}-\d{2})", kickoff)
    return m.group(1) if m else None


@dataclass
class OneClickConfig:
    odds_api_key: str = ""
    football_data_key: str = ""
    api_football_key: str = ""
    odds_sport_keys: tuple[str,...] = (
        "soccer_epl","soccer_efl_champ","soccer_england_league1","soccer_england_league2",
    )
    odds_regions: str = "uk,eu"
    max_competitions: int = 25
    form_matches: int = 12


@dataclass
class OneClickStage:
    name: str
    ok: bool
    message: str
    matched: int = 0
    attempted: int = 0


@dataclass(frozen=True)
class MatchSourceProvenance:
    match_number: int
    competition: str
    source: str
    matched_units: int
    attempted_units: int
    status: str = ""
    reason_code: str = ""


@dataclass
class OneClickResult:
    coupon: list[MatchInput]
    enriched: list[MatchInput]
    cards: list[Any]
    stages: list[OneClickStage] = field(default_factory=list)
    fixture_matches: dict[int,FixtureMatch] = field(default_factory=dict)
    discovery: list[dict] = field(default_factory=list)
    api_stats: CacheStats = field(default_factory=lambda: CacheStats(0, 0, 0))
    match_provenance: list[MatchSourceProvenance] = field(default_factory=list)

    @property
    def ready_count(self) -> int:
        return sum(1 for c in self.cards if c.readiness_score >= 50)


def fetch_api_football_fixtures_by_date(api_key: str, date: str, timeout: int=15) -> dict[str,Any]:
    if not api_key.strip(): raise ValueError("API-Football-nyckel saknas")
    import requests
    r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":api_key}, params={"date":date}, timeout=timeout)
    r.raise_for_status(); return r.json()


def _form_provider(home_summary: dict, away_summary: dict):
    sig=form_signal_from_summaries(home_summary, away_summary, "football-data.org")
    def provider(match: MatchInput):
        return ProviderOutput(provider="football-data.org", signals=[sig], message="Venue-form hämtad", quality="Medel")
    provider.provider_name="football-data.org"
    return provider


def _absence_provider(payload: dict, fm: FixtureMatch):
    absences=parse_api_football_injuries(payload)
    hm=missing_value(absences,fm.home_id); am=missing_value(absences,fm.away_id)
    signals=build_match_signals(home_missing=hm,away_missing=am,source_absence="API-Football",absence_verified=True)
    observations=[]
    for a in absences:
        observations.append(Observation("availability", f"{a.team_id}:{a.player}:{a.status}", DEFAULT_SOURCES["api_football"], _now(), confidence=0.78, direct=True))
    claim=resolve_claim("availability","injury_suspension",observations) if observations else IntelligenceClaim("availability","injury_suspension",(),None)
    def provider(match: MatchInput):
        return ProviderOutput(provider="API-Football", signals=signals, claims=[claim], message=f"{len(absences)} frånvaroposter", quality="Medel")
    provider.provider_name="API-Football"
    return provider


def _lineup_provider(payload: dict):
    response=payload.get("response",[]) if isinstance(payload,dict) else []
    # A confirmed lineup is an intelligence/readiness claim here. We do not invent player-value impacts yet.
    obs=[]
    if response:
        obs.append(Observation("confirmed_lineup","confirmed",DEFAULT_SOURCES["api_football"],_now(),confidence=0.90,direct=True))
    claim=resolve_claim("confirmed_lineup","confirmed_lineup",obs) if obs else IntelligenceClaim("confirmed_lineup","confirmed_lineup",(),None)
    def provider(match: MatchInput):
        return ProviderOutput(provider="API-Football lineups", claims=[claim], message="Bekräftad lineup hittad" if response else "Lineup ännu ej tillgänglig", quality="Hög" if response else "Saknas")
    provider.provider_name="API-Football lineups"
    return provider


def run_one_click(config: OneClickConfig, *, coupon: Sequence[MatchInput] | None=None, fetch_coupon: bool=True) -> OneClickResult:
    stages=[]
    match_provenance=[]
    stats_before = cache_stats()

    # TTLs are intentionally conservative. Stable metadata can live longer;
    # odds/fixtures/lineups are short-lived so the cache cannot create false freshness.
    odds_policy = CachePolicy("odds", 120)
    competitions_policy = CachePolicy("competitions", 24*3600)
    catalog_policy = CachePolicy("team_catalog", 12*3600)
    form_policy = CachePolicy("venue_form", 4*3600)
    fixtures_policy = CachePolicy("fixtures", 120)
    injuries_policy = CachePolicy("injuries", 300)
    lineups_policy = CachePolicy("lineups", 90)
    if fetch_coupon:
        fetched,status=fetch_svenskaspel_current()
        if not status.ok or not fetched:
            raise RuntimeError(status.message)
        current=list(fetched); stages.append(OneClickStage("Svenska Spel",True,status.message,13,13))
    else:
        if not coupon or len(coupon)!=13: raise ValueError("Exakt 13 matcher krävs när kupongen inte hämtas automatiskt")
        current=list(coupon); stages.append(OneClickStage("Kupong",True,"Befintlig kupong används",13,13))

    _coupon_source = "Svenska Spel" if fetch_coupon else "Kupong"
    for m in current:
        match_provenance.append(MatchSourceProvenance(
            m.number, str(getattr(m, "competition", "") or "Okänd tävling"),
            _coupon_source, 1, 1, "Kupongmatch tillgänglig", "matched"
        ))

    # Odds: independent of other sources. If unavailable, Svenska Spels odds remain as base.
    if config.odds_api_key.strip():
        events,status=cached_call(odds_policy, (config.odds_api_key, config.odds_sport_keys, config.odds_regions), lambda: fetch_the_odds_api(config.odds_api_key,config.odds_sport_keys,config.odds_regions))
        matched=match_odds_to_coupon(current,events) if status.ok else {}
        if status.ok:
            updated=[]
            for m in current:
                e=matched.get(m.number)
                if e:
                    odds=tuple(e["odds"]); updated.append(MatchInput(m.number,m.home,m.away,odds,m.public,market_probabilities(odds),kickoff=m.kickoff,competition=m.competition))
                else: updated.append(m)
            current=updated
        stages.append(OneClickStage("The Odds API",status.ok,status.message,len(matched),13))
    else:
        stages.append(OneClickStage("The Odds API",False,"API-nyckel saknas – Svenska Spels odds används",0,13))

    for m in current:
        match_provenance.append(MatchSourceProvenance(
            m.number, str(getattr(m, "competition", "") or "Okänd tävling"),
            "The Odds API", 1 if (config.odds_api_key.strip() and m.number in (matched if 'matched' in locals() else {})) else 0, 1,
            "Matchad" if (config.odds_api_key.strip() and m.number in (matched if 'matched' in locals() else {})) else ("API-nyckel saknas" if not config.odds_api_key.strip() else ("API-fel" if not status.ok else "Ingen säker matchning")),
            "matched" if (config.odds_api_key.strip() and m.number in (matched if 'matched' in locals() else {})) else ("api_key_missing" if not config.odds_api_key.strip() else ("api_error" if not status.ok else "no_secure_match"))
        ))

    discovery=[]; form_by_match={}
    _football_data_error = ""
    if config.football_data_key.strip():
        try:
            comps=cached_call(competitions_policy, config.football_data_key, lambda: fetch_competitions(config.football_data_key))
            comps=sorted(comps,key=lambda c:(0 if c.country=="England" else 1,c.country,c.name))[:config.max_competitions]
            candidates,team_comp,errors=cached_call(catalog_policy, (config.football_data_key, tuple((c.id,c.name,c.country) for c in comps)), lambda: build_catalog(config.football_data_key,comps))
            discovery=discover_coupon(current,candidates,team_comp)
            matched_teams=0
            for row in discovery:
                h=row["home"]; a=row["away"]
                if h.match.confidence=="Hög" and a.match.confidence=="Hög" and h.match.candidate and a.match.candidate:
                    matched_teams += 2
                    hm,_=cached_call(form_policy, (config.football_data_key,h.match.candidate.team_id,"HOME",config.form_matches), lambda: fetch_team_finished_matches(config.football_data_key,h.match.candidate.team_id,"HOME",config.form_matches))
                    am,_=cached_call(form_policy, (config.football_data_key,a.match.candidate.team_id,"AWAY",config.form_matches), lambda: fetch_team_finished_matches(config.football_data_key,a.match.candidate.team_id,"AWAY",config.form_matches))
                    form_by_match[row["match_number"]]=(summarize_team_form(hm,h.match.candidate.team_id), summarize_team_form(am,a.match.candidate.team_id))
            stages.append(OneClickStage("football-data.org",True,f"Lagmatchning/form klar; {len(errors)} tävlingsfel isolerades",matched_teams,26))
        except Exception as exc:
            _football_data_error = f"{type(exc).__name__}: {exc}"
            stages.append(OneClickStage("football-data.org",False,_football_data_error,0,26))
    else:
        stages.append(OneClickStage("football-data.org",False,"API-nyckel saknas",0,26))

    _discovery_by_match = {int(row.get("match_number")): row for row in discovery if row.get("match_number") is not None}
    for m in current:
        row = _discovery_by_match.get(m.number)
        matched_teams = 0
        if row:
            for side in ("home", "away"):
                side_row = row.get(side)
                mt = getattr(side_row, "match", None)
                if mt and getattr(mt, "confidence", "") == "Hög" and getattr(mt, "candidate", None):
                    matched_teams += 1
        if matched_teams == 2:
            fd_status, fd_reason = "Båda lag matchade", "matched"
        elif not config.football_data_key.strip():
            fd_status, fd_reason = "API-nyckel saknas", "api_key_missing"
        elif _football_data_error:
            fd_status, fd_reason = f"API-fel: {_football_data_error}", "api_error"
        elif not row:
            fd_status, fd_reason = "Ingen lagkatalog/matchningsrad för matchen", "no_candidates"
        else:
            confidences=[]
            for side in ("home", "away"):
                side_row=row.get(side)
                mt=getattr(side_row, "match", None)
                confidences.append(str(getattr(mt, "confidence", "Ingen") or "Ingen"))
            if "Granska" in confidences:
                fd_status, fd_reason = f"{matched_teams}/2 lag säkert matchade; minst ett lag är tvetydigt", "ambiguous_team_match"
            else:
                fd_status, fd_reason = f"{matched_teams}/2 lag säkert matchade; för låg matchsannolikhet", "low_confidence_team_match"
        match_provenance.append(MatchSourceProvenance(
            m.number, str(getattr(m, "competition", "") or "Okänd tävling"),
            "football-data.org", matched_teams, 2, fd_status, fd_reason
        ))

    fixture_matches={}; injury_payloads={}; lineup_payloads={}
    _api_football_error = ""
    if config.api_football_key.strip():
        try:
            dates=sorted({d for d in (parse_coupon_date(m.kickoff) for m in current) if d})
            date_payloads={d:cached_call(fixtures_policy, (config.api_football_key,d), lambda d=d: fetch_api_football_fixtures_by_date(config.api_football_key,d)) for d in dates}
            high_count=0
            for m in current:
                d=parse_coupon_date(m.kickoff)
                if not d: continue
                fm=match_api_football_fixture(m,date_payloads.get(d,{})); fixture_matches[m.number]=fm
                if fm.confidence=="Hög" and fm.fixture_id:
                    high_count += 1
                    try: injury_payloads[m.number]=cached_call(injuries_policy, (config.api_football_key,fm.fixture_id), lambda fm=fm: fetch_api_football_injuries(config.api_football_key,fm.fixture_id))
                    except Exception: injury_payloads[m.number]={"response":[]}
                    try: lineup_payloads[m.number]=cached_call(lineups_policy, (config.api_football_key,fm.fixture_id), lambda fm=fm: fetch_api_football_lineups(config.api_football_key,fm.fixture_id))
                    except Exception: lineup_payloads[m.number]={"response":[]}
            stages.append(OneClickStage("API-Football",True,"Fixture-matchning + frånvaro/lineup försökt för säkra träffar",high_count,13))
        except Exception as exc:
            _api_football_error = f"{type(exc).__name__}: {exc}"
            stages.append(OneClickStage("API-Football",False,_api_football_error,0,13))
    else:
        stages.append(OneClickStage("API-Football",False,"API-nyckel saknas",0,13))

    for m in current:
        fm = fixture_matches.get(m.number)
        matched_fixture = 1 if (fm and fm.confidence == "Hög" and fm.fixture_id) else 0
        if not config.api_football_key.strip():
            status, reason_code = "API-nyckel saknas", "api_key_missing"
        elif not parse_coupon_date(m.kickoff):
            status, reason_code = "Matchdatum saknas", "missing_match_date"
        elif _api_football_error:
            status, reason_code = f"API-fel: {_api_football_error}", "api_error"
        elif matched_fixture:
            status, reason_code = "Fixture säkert matchad", "matched"
        elif fm and fm.confidence == "Granska":
            status, reason_code = "Fixture-matchning är tvetydig och kräver granskning", "ambiguous_fixture_match"
        else:
            status, reason_code = "Ingen säker fixture-matchning", "no_secure_match"
        match_provenance.append(MatchSourceProvenance(
            m.number, str(getattr(m, "competition", "") or "Okänd tävling"),
            "API-Football fixture", matched_fixture, 1, status, reason_code
        ))

    cards=[]; enriched=[]
    for m in current:
        providers=[]
        if m.number in form_by_match:
            providers.append(_form_provider(*form_by_match[m.number]))
        fm=fixture_matches.get(m.number)
        if fm and fm.confidence=="Hög":
            if m.number in injury_payloads: providers.append(_absence_provider(injury_payloads[m.number],fm))
            if m.number in lineup_payloads: providers.append(_lineup_provider(lineup_payloads[m.number]))
        result=run_match_pipeline(m,providers,max_total_shift=0.14)
        cards.append(result.card); enriched.append(result.enriched_match)

    return OneClickResult(current,enriched,cards,stages,fixture_matches,discovery,stats_delta(stats_before, cache_stats()),match_provenance)
