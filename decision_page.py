from __future__ import annotations
from dataclasses import dataclass
from core import classify_match
from budget_workshop import optimize_for_budget

@dataclass(frozen=True)
class MatchDecision:
    number:int
    home:str
    away:str
    classification:str
    recommended:str
    confidence:float
    edge:float
    public_favorite:str
    public_favorite_share:float

def _best_sign(model):
    idx=max(range(3), key=lambda i:model[i])
    return ("1","X","2")[idx]

def _edge_for_best(model, public):
    idx=max(range(3), key=lambda i:model[i])
    return model[idx]-public[idx]

def build_match_decisions(matches):
    out=[]
    for m in matches:
        klass=classify_match(m.model,m.public)
        best=_best_sign(m.model)
        pf_idx=max(range(3), key=lambda i:m.public[i])
        out.append(MatchDecision(
            number=m.number, home=m.home, away=m.away,
            classification=klass, recommended=best,
            confidence=max(m.model),
            edge=_edge_for_best(m.model,m.public),
            public_favorite=("1","X","2")[pf_idx],
            public_favorite_share=m.public[pf_idx],
        ))
    return out

def summarize_decisions(matches, budget:int, strategy:str="MAX 13", locks=None):
    decisions=build_match_decisions(matches)
    system=optimize_for_budget(matches,budget,strategy,locks)
    spikes=[d for d in decisions if d.classification in ("Stark spik","Värdespik","Riskspik")]
    traps=[d for d in decisions if d.classification=="Fällan"]
    upsets=[d for d in decisions if d.classification=="Skrälläge"]
    must_guard=[d for d in decisions if d.classification in ("Halvgardering","Helgardering","Fällan","Skrälläge")]
    spikes=sorted(spikes,key=lambda d:(d.confidence,d.edge),reverse=True)
    traps=sorted(traps,key=lambda d:d.public_favorite_share,reverse=True)
    upsets=sorted(upsets,key=lambda d:d.edge,reverse=True)
    must_guard=sorted(must_guard,key=lambda d:(d.public_favorite_share,-d.confidence),reverse=True)
    return {
        "system":system,
        "spikes":spikes,
        "traps":traps,
        "upsets":upsets,
        "must_guard":must_guard,
        "decisions":decisions,
    }
