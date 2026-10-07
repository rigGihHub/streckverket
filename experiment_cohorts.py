from __future__ import annotations
"""Prospective cohort robustness for shadow prediction experiments.

Diagnostic only. Cohorts are fixed from frozen pre-match probabilities and never
change production forecasts, strategy or experiment parameters.
"""
from collections import defaultdict
from math import log
from typing import Iterable, Sequence
from core import SIGNS
from experiment_registry import MARKET_PULL_EXPERIMENT_ID
from predictive_experiment import _norm

MIN_COHORT_MATCHES = 30
MIN_COHORT_COUPONS = 5


def _scores(probs: Sequence[float], result: str) -> tuple[float, float]:
    p = _norm(probs); idx = SIGNS.index(result)
    return sum((p[i]-(1.0 if i==idx else 0.0))**2 for i in range(3)), -log(max(1e-12,p[idx]))


def _fav_sign(probs): return SIGNS[max(range(3), key=lambda i: probs[i])]

def _confidence(probs):
    p=max(probs)
    if p < .50: return "<50%"
    if p < .60: return "50–60%"
    if p < .70: return "60–70%"
    return "70%+"

def _gap(model, market):
    g=max(abs(float(model[i])-float(market[i])) for i in range(3))
    if g < .025: return "<2,5 pp"
    if g < .05: return "2,5–5 pp"
    if g < .10: return "5–10 pp"
    return "10+ pp"


def cohort_robustness(coupons: Iterable, *, experiment_id: str=MARKET_PULL_EXPERIMENT_ID) -> dict:
    buckets=defaultdict(list)
    for coupon in coupons:
        cid=str(getattr(coupon,'coupon_id',''))
        for m in tuple(getattr(coupon,'matches',()) or ()):
            pred=next((p for p in tuple(getattr(m,'shadow_predictions',()) or ()) if getattr(p,'experiment_id','')==experiment_id),None)
            result=getattr(m,'result',None)
            if pred is None or result not in SIGNS or not bool(getattr(m,'market_available',False)): continue
            cb,cl=_scores(pred.probabilities,result); bb,bl=_scores(m.model,result)
            row=(cid,bb-cb,bl-cl)
            for dimension,label in (("Modellens förstaval",_fav_sign(m.model)),("Modellsäkerhet",_confidence(m.model)),("Modell–marknad-gap",_gap(m.model,m.market))):
                buckets[(dimension,label)].append(row)
    rows=[]
    for (dim,label), vals in sorted(buckets.items()):
        n=len(vals); c=len({x[0] for x in vals}); bg=sum(x[1] for x in vals)/n; lg=sum(x[2] for x in vals)/n
        mature=n>=MIN_COHORT_MATCHES and c>=MIN_COHORT_COUPONS
        if not mature: verdict="FÖR LITET UNDERLAG"
        elif bg>0 and lg>0: verdict="KANDIDAT BÄTTRE"
        elif bg<0 and lg<0: verdict="KANDIDAT SÄMRE"
        else: verdict="BLANDAD EVIDENS"
        rows.append({"Dimension":dim,"Segment":label,"Matcher":n,"Kuponger":c,"Brier-gain":bg,"Log-loss-gain":lg,"Mogen":mature,"Bedömning":verdict})
    mature=[r for r in rows if r['Mogen']]
    worse=[r for r in mature if r['Bedömning']=="KANDIDAT SÄMRE"]
    better=[r for r in mature if r['Bedömning']=="KANDIDAT BÄTTRE"]
    if not mature: status="MER DATA KRÄVS"
    elif worse: status="ROBUSTHETSVARNING"
    elif better and len(better)==len(mature): status="BRED POSITIV ROBUSTHET"
    else: status="BLANDAD ROBUSTHET"
    return {"experiment_id":experiment_id,"status":status,"rows":rows,"mature_cohorts":len(mature),"worse_cohorts":len(worse),"requirements":{"min_matches":MIN_COHORT_MATCHES,"min_coupons":MIN_COHORT_COUPONS},"production_effect":False}
