from __future__ import annotations
from dataclasses import dataclass
from math import prod
from typing import Sequence
from core import MatchInput, SIGNS

@dataclass(frozen=True)
class PoolValueSummary:
    model_coverage: float
    public_survival_mass: float
    elimination_estimate: float
    leverage: float
    uniqueness_index: float


def system_pool_value(matches: Sequence[MatchInput], selections: Sequence[Sequence[str]]) -> PoolValueSummary:
    """Pool proxy, not a payout forecast.

    public_survival_mass approximates the share of public single-line probability mass
    compatible with the system if public percentages are treated independently.
    """
    if len(matches) != len(selections):
        raise ValueError("Matcher och val måste vara lika många")
    model_parts=[]; public_parts=[]
    for m, sel in zip(matches, selections):
        md=dict(zip(SIGNS,m.model)); pd=dict(zip(SIGNS,m.public))
        model_parts.append(sum(md[s] for s in sel))
        public_parts.append(sum(pd[s] for s in sel))
    cov=prod(model_parts) if model_parts else 0.0
    mass=prod(public_parts) if public_parts else 0.0
    leverage=cov/max(mass,1e-12)
    # bounded, beginner-friendly 0..100 proxy; 50 means roughly neutral vs public mass
    uniqueness=100*leverage/(1+leverage)
    return PoolValueSummary(cov,mass,max(0.0,1-mass),leverage,uniqueness)


def sign_pool_edges(match: MatchInput):
    out=[]
    for sign,p,s in zip(SIGNS,match.model,match.public):
        ratio=p/max(s,0.01)
        # cleaner combines public elimination potential with credible model probability
        cleaner=(1-s)*p
        out.append({"sign":sign,"model":p,"public":s,"value_ratio":ratio,"cleaner_score":cleaner})
    return sorted(out,key=lambda x:(x["value_ratio"],x["cleaner_score"]),reverse=True)


def top_coupon_cleaners(matches: Sequence[MatchInput], limit:int=5):
    rows=[]
    for m in matches:
        public_fav=SIGNS[max(range(3),key=lambda i:m.public[i])]
        for e in sign_pool_edges(m):
            if e["sign"]==public_fav:
                continue
            # Require some probability support; don't reward absurd longshots only for rarity.
            if e["model"] < 0.16:
                continue
            rows.append({"match":m.number,"home":m.home,"away":m.away,**e})
    return sorted(rows,key=lambda x:(x["cleaner_score"],x["value_ratio"]),reverse=True)[:limit]
