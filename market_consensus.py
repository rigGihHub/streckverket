from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from typing import Any, Sequence
from core import market_probabilities, normalize

@dataclass(frozen=True)
class BookmakerQuote:
    bookmaker: str
    odds: tuple[float,float,float]
    updated_at: str | None = None

@dataclass(frozen=True)
class MarketConsensus:
    odds: tuple[float,float,float]
    probabilities: tuple[float,float,float]
    bookmaker_count: int
    dispersion: float
    outliers: tuple[str,...]


def robust_market_consensus(quotes: Sequence[BookmakerQuote]) -> MarketConsensus:
    valid=[q for q in quotes if len(q.odds)==3 and min(q.odds)>1]
    if not valid:
        raise ValueError("Inga giltiga bookmakerodds")
    probs=[market_probabilities(q.odds) for q in valid]
    centers=tuple(median([p[i] for p in probs]) for i in range(3))
    centers=normalize(centers)
    # L1/2 distance from median probability vector.
    distances=[0.5*sum(abs(p[i]-centers[i]) for i in range(3)) for p in probs]
    med_dist=median(distances)
    threshold=max(0.055, med_dist*2.5)
    keep=[i for i,d in enumerate(distances) if d<=threshold or len(valid)<=3]
    kept=[valid[i] for i in keep]
    kept_probs=[probs[i] for i in keep]
    final_p=normalize(tuple(median([p[i] for p in kept_probs]) for i in range(3)))
    # Convert fair probabilities to representative fair odds. These are not offered bookmaker prices.
    fair_odds=tuple(1/max(1e-9,p) for p in final_p)
    dispersion=sum(0.5*sum(abs(p[i]-final_p[i]) for i in range(3)) for p in kept_probs)/len(kept_probs)
    out=tuple(valid[i].bookmaker for i,d in enumerate(distances) if i not in keep)
    return MarketConsensus(fair_odds,tuple(final_p),len(kept),dispersion,out)


def quotes_from_odds_api_event(event: dict[str,Any]) -> list[BookmakerQuote]:
    home=str(event.get("home_team") or ""); away=str(event.get("away_team") or "")
    out=[]
    for bm in event.get("bookmakers",[]) or []:
        for market in bm.get("markets",[]) or []:
            if market.get("key") != "h2h": continue
            prices={str(x.get("name")):x.get("price") for x in market.get("outcomes",[]) or []}
            try:
                odds=(float(prices[home]),float(prices["Draw"]),float(prices[away]))
            except Exception:
                continue
            if min(odds)>1:
                out.append(BookmakerQuote(str(bm.get("title") or bm.get("key") or "bookmaker"),odds,bm.get("last_update") or market.get("last_update")))
    return out
