from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json
import math
import re
import requests

from core import MatchInput, normalize


@dataclass
class SourceStatus:
    name: str
    ok: bool
    updated_at: Optional[str]
    quality: str
    message: str


class DataSourceError(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_json(url: str, timeout: int = 10, headers: Optional[Dict[str, str]] = None) -> Any:
    hdrs = {"User-Agent": "Mozilla/5.0 (compatible; Stryktips13/0.3.0; +https://spela.svenskaspel.se/stryktipset)"}
    if headers:
        hdrs.update(headers)
    response = requests.get(url, timeout=timeout, headers=hdrs)
    response.raise_for_status()
    return response.json()


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace("\xa0", " ").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _team_pair_from_event(event: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    # Vanligaste API-varianter först.
    for key in ("eventDescription", "description", "eventName", "name"):
        value = event.get(key)
        if isinstance(value, str):
            for sep in (" - ", " – ", " vs ", " v "):
                if sep in value:
                    a, b = value.split(sep, 1)
                    if a.strip() and b.strip():
                        return a.strip(), b.strip()
    for key in ("participants", "competitors", "teams"):
        value = event.get(key)
        if isinstance(value, list) and len(value) >= 2:
            names = []
            for x in value[:2]:
                if isinstance(x, str):
                    names.append(x)
                elif isinstance(x, dict):
                    names.append(str(x.get("name") or x.get("participantName") or x.get("description") or ""))
            if len(names) == 2 and all(n.strip() for n in names):
                return names[0].strip(), names[1].strip()
    return None


def _extract_three_from_values(values: Any, kind: str) -> Optional[Tuple[float, float, float]]:
    if not isinstance(values, list) or len(values) < 3:
        return None
    out = []
    for item in values[:3]:
        if not isinstance(item, dict):
            return None
        candidates = []
        if kind == "odds":
            candidates = [
                item.get("odds"), item.get("price"), item.get("decimalOdds"),
            ]
            if isinstance(item.get("odds"), dict):
                candidates.insert(0, item["odds"].get("odds"))
        else:
            candidates = [
                item.get("distribution"), item.get("percentage"), item.get("percent"),
                item.get("betDistribution"), item.get("share"), item.get("value"),
            ]
            for nested_key in ("distribution", "betDistribution"):
                nested = item.get(nested_key)
                if isinstance(nested, dict):
                    candidates.insert(0, nested.get("value"))
        val = next((_num(c) for c in candidates if _num(c) is not None), None)
        if val is None:
            return None
        out.append(val)
    if kind == "odds":
        if min(out) <= 1.0:
            return None
        return tuple(out)  # type: ignore
    if max(out) <= 1.5:
        out = [x * 100 for x in out]
    if not (95 <= sum(out) <= 105):
        return None
    return tuple(x / sum(out) for x in out)  # type: ignore


def _extract_event_public(event: Dict[str, Any]) -> Optional[Tuple[float,float,float]]:
    metrics = event.get("betMetrics")
    if isinstance(metrics, dict):
        found = _extract_three_from_values(metrics.get("values"), "public")
        if found:
            return found
    # Andra observerade/typiska varianter.
    for key in ("distribution", "distributions", "publicDistribution", "betDistribution"):
        v = event.get(key)
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            nums = [_num(x) for x in v[:3]]
            if all(x is not None for x in nums):
                vals = [float(x) for x in nums]
                if max(vals) <= 1.5:
                    vals = [x*100 for x in vals]
                if 95 <= sum(vals) <= 105:
                    return tuple(x/sum(vals) for x in vals)  # type: ignore
    return None


def _extract_event_odds(event: Dict[str, Any]) -> Optional[Tuple[float,float,float]]:
    metrics = event.get("betMetrics")
    if isinstance(metrics, dict):
        found = _extract_three_from_values(metrics.get("values"), "odds")
        if found:
            return found
    odds = event.get("odds")
    if isinstance(odds, (list,tuple)) and len(odds) >= 3:
        vals = [_num(x) for x in odds[:3]]
        if all(x is not None and x > 1 for x in vals):
            return tuple(float(x) for x in vals)  # type: ignore
    return None


def _find_draw_events(payload: Any) -> Optional[List[Dict[str,Any]]]:
    """Hittar en 13-matchers drawEvents-lista utan att anta exakt wrapper."""
    candidates = []
    def walk(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("drawEvents"), list):
                candidates.append(obj["drawEvents"])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(payload)
    exact = [x for x in candidates if len(x) == 13 and all(isinstance(e, dict) for e in x)]
    return exact[0] if exact else None



def _extract_event_kickoff(event: Dict[str, Any]) -> Optional[str]:
    for key in ("startTime", "startDate", "eventStart", "date", "utcDate", "kickoff"):
        v = event.get(key)
        if isinstance(v, str) and len(v) >= 10:
            return v
    return None

def _extract_event_competition(event: Dict[str, Any]) -> str:
    for key in ("league", "competition", "tournament", "category"):
        v=event.get(key)
        if isinstance(v, str): return v
        if isinstance(v, dict):
            for nk in ("name","title","displayName"):
                if v.get(nk): return str(v[nk])
    return ""

def parse_svenskaspel_api_payload(payload: Any) -> List[MatchInput]:
    events = _find_draw_events(payload)
    if not events:
        raise DataSourceError("Svenska Spel-svaret innehöll ingen verifierbar lista med exakt 13 drawEvents.")
    matches = []
    for i, event in enumerate(events, start=1):
        pair = _team_pair_from_event(event)
        public = _extract_event_public(event)
        odds = _extract_event_odds(event)
        if not pair or not public:
            raise DataSourceError(f"Match {i} saknade verifierbart lagnamn eller streckfördelning i API-svaret.")
        # Odds är värdefulla men inte nödvändiga för att importera kupongen.
        if odds:
            from core import market_probabilities
            model = market_probabilities(odds)
            safe_odds = odds
        else:
            model = public
            safe_odds = (3.0, 3.0, 3.0)
        matches.append(MatchInput(i, pair[0], pair[1], safe_odds, public, model, kickoff=_extract_event_kickoff(event), competition=_extract_event_competition(event), market_available=bool(odds)))
    return matches


def parse_svenskaspel_page_text(text: str) -> List[MatchInput]:
    """Fallback för den publika sidans text: Match + Svenska folket + Odds."""
    compact = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    pattern = re.compile(
        r"(?:^|\s)(\d{1,2})\.?(?:\s+\d{1,2})?\s+(.+?)\s+-\s+(.+?)\s+1X2.*?"
        r"Svenska folket\s+(\d{1,3})%\s+(\d{1,3})%\s+(\d{1,3})%\s+"
        r"Odds\s+([0-9]+[,.][0-9]+)\s+([0-9]+[,.][0-9]+)\s+([0-9]+[,.][0-9]+)",
        re.IGNORECASE,
    )
    found = []
    for m in pattern.finditer(compact):
        nr = int(m.group(1))
        if not 1 <= nr <= 13:
            continue
        home, away = m.group(2).strip(), m.group(3).strip()
        public = normalize([float(m.group(4)), float(m.group(5)), float(m.group(6))])
        odds = tuple(float(m.group(i).replace(",", ".")) for i in (7,8,9))
        from core import market_probabilities
        found.append(MatchInput(nr,home,away,odds,public,market_probabilities(odds)))
    unique = {m.number:m for m in found}
    if len(unique) != 13:
        raise DataSourceError(f"Webbsidan gav {len(unique)}/13 säkert tolkade matcher.")
    return [unique[i] for i in range(1,14)]


def fetch_svenskaspel_current() -> Tuple[Optional[List[MatchInput]], SourceStatus]:
    """
    Hämtar aktuell Stryktipskupong utan inloggning.
    1) Föredrar Svenska Spels draw-API.
    2) Fallback till den publika Stryktipssidan om dess HTML innehåller kupongtexten.
    Inga delvis tolkade kuponger släpps igenom: exakt 13 matcher krävs.
    """
    attempts = []
    api_urls = [
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws",
        "https://api.spela.svenskaspel.se/draw/stryktipset/draws",
        "https://api.www.svenskaspel.se/draw/stryktipset/draws",
    ]
    for url in api_urls:
        try:
            payload = fetch_json(url)
            coupon = parse_svenskaspel_api_payload(payload)
            return coupon, SourceStatus(
                "Svenska Spel", True, utc_now_iso(), "Hög",
                f"Aktuell kupong hämtad från Svenska Spels draw-källa: 13/13 matcher. {url}",
            )
        except Exception as exc:
            attempts.append(f"API {type(exc).__name__}")

    page_urls = [
        "https://spela.svenskaspel.se/stryktipset",
        "https://spela.svenskaspel.se/stryktipset/nyheter",
    ]
    for url in page_urls:
        try:
            headers = {"User-Agent":"Mozilla/5.0 (compatible; Stryktips13/0.3.0)"}
            response = requests.get(url, timeout=12, headers=headers)
            response.raise_for_status()
            # Nyare synlig text-variant.
            try:
                coupon = parse_svenskaspel_page_text(response.text)
                return coupon, SourceStatus("Svenska Spel", True, utc_now_iso(), "Hög", "Aktuell kupong hämtad från Svenska Spels publika sida: 13/13 matcher.")
            except Exception:
                pass
            # Äldre preloadedState-variant.
            m = re.search(r'_svs\.tipsen\.data\.preloadedState\s*=\s*(\{.*?\});', response.text, re.DOTALL)
            if m:
                state = json.loads(m.group(1))
                # Den äldre strukturen kan innehålla statistik men lagmetadata varierar;
                # använd bara om den kan valideras av samma parser.
                coupon = parse_svenskaspel_api_payload(state)
                return coupon, SourceStatus("Svenska Spel", True, utc_now_iso(), "Medel", "Kupong hämtad från Svenska Spels inbäddade siddata.")
        except Exception as exc:
            attempts.append(f"Webb {type(exc).__name__}")

    return None, SourceStatus(
        "Svenska Spel", False, None, "Saknas",
        "Kunde inte hämta en komplett verifierad 13-matcherskupong. CSV-import finns kvar som reserv. " + ", ".join(attempts),
    )

# Bakåtkompatibelt namn från v0.2.
def try_fetch_svenskaspel_current():
    coupon, status = fetch_svenskaspel_current()
    return coupon, status

def _outcome_price(market: Dict[str, Any], team: str, draw: bool = False) -> Optional[float]:
    for outcome in market.get("outcomes", []):
        name = str(outcome.get("name", ""))
        if draw and name.lower() == "draw":
            return float(outcome["price"])
        if not draw and name == team:
            return float(outcome["price"])
    return None


def aggregate_1x2_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Aggregerar 1X2 genom medianodds över tillgängliga bookmakers."""
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return None
    prices = {"1": [], "X": [], "2": []}
    updates = []
    for bookmaker in event.get("bookmakers", []):
        if bookmaker.get("last_update"):
            updates.append(bookmaker["last_update"])
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            h = _outcome_price(market, home)
            d = _outcome_price(market, "", draw=True)
            a = _outcome_price(market, away)
            if h and d and a and min(h, d, a) > 1:
                prices["1"].append(h)
                prices["X"].append(d)
                prices["2"].append(a)
    if not all(prices.values()):
        return None

    def median(values: List[float]) -> float:
        s = sorted(values)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    return {
        "event_id": event.get("id"),
        "home": home,
        "away": away,
        "commence_time": event.get("commence_time"),
        "sport": event.get("sport_title") or event.get("sport_key"),
        "odds": (median(prices["1"]), median(prices["X"]), median(prices["2"])),
        "bookmaker_count": min(len(prices["1"]), len(prices["X"]), len(prices["2"])),
        "last_update": max(updates) if updates else None,
    }


def fetch_the_odds_api(api_key: str, sport_keys: Sequence[str], regions: str = "uk,eu") -> Tuple[List[Dict[str, Any]], SourceStatus]:
    if not api_key:
        return [], SourceStatus("The Odds API", False, None, "Saknas", "Ingen API-nyckel angiven.")
    events: List[Dict[str, Any]] = []
    errors = []
    latest = None
    for sport in sport_keys:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
            f"?apiKey={api_key}&regions={regions}&markets=h2h&oddsFormat=decimal&dateFormat=iso"
        )
        try:
            payload = fetch_json(url)
            for raw in payload:
                agg = aggregate_1x2_event(raw)
                if agg:
                    events.append(agg)
                    if agg.get("last_update") and (latest is None or agg["last_update"] > latest):
                        latest = agg["last_update"]
        except Exception as exc:
            errors.append(f"{sport}: {type(exc).__name__}")
    ok = bool(events)
    quality = "Hög" if ok and not errors else "Medel" if ok else "Saknas"
    msg = f"{len(events)} matcher med aggregerade 1X2-odds." if ok else "Inga odds kunde hämtas."
    if errors:
        msg += " Fel: " + ", ".join(errors)
    return events, SourceStatus("The Odds API", ok, latest, quality, msg)


def normalize_name(name: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in name).split())


def match_odds_to_coupon(coupon: Sequence[MatchInput], odds_events: Sequence[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Konservativ exakt/normaliserad namnmatchning; gissar inte med fuzzy threshold."""
    by_pair = {(normalize_name(e["home"]), normalize_name(e["away"])): e for e in odds_events}
    out = {}
    for m in coupon:
        key = (normalize_name(m.home), normalize_name(m.away))
        if key in by_pair:
            out[m.number] = by_pair[key]
    return out


def parse_coupon_csv(df) -> List[MatchInput]:
    required = ["nr", "hemma", "borta", "streck1", "streckx", "streck2"]
    lower = {str(c).strip().lower(): c for c in df.columns}
    missing = [c for c in required if c not in lower]
    if missing:
        raise DataSourceError("CSV saknar kolumner: " + ", ".join(missing))

    has_odds = all(c in lower for c in ["odds1", "oddsx", "odds2"])
    out = []
    for _, row in df.iterrows():
        p = [float(row[lower["streck1"]]), float(row[lower["streckx"]]), float(row[lower["streck2"]])]
        if max(p) > 1.5:  # tillåt procent 0-100
            p = [x / 100 for x in p]
        public = normalize(p)
        odds = (float(row[lower["odds1"]]), float(row[lower["oddsx"]]), float(row[lower["odds2"]])) if has_odds else (3.0, 3.0, 3.0)
        # v0.2: egen modell startar i marknaden om riktiga odds finns; annars folkets streck som neutral fallback.
        if has_odds:
            from core import market_probabilities
            model = market_probabilities(odds)
        else:
            model = public
        out.append(MatchInput(
            number=int(row[lower["nr"]]),
            home=str(row[lower["hemma"]]),
            away=str(row[lower["borta"]]),
            odds=odds,
            public=public,
            model=model,
            market_available=has_odds,
        ))
    if len(out) != 13:
        raise DataSourceError(f"En Stryktipskupong måste innehålla 13 matcher; filen innehåller {len(out)}.")
    return sorted(out, key=lambda m: m.number)
