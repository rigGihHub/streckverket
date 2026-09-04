from __future__ import annotations
from dataclasses import dataclass
from math import log
from typing import Sequence
from core import SIGNS, MatchInput, uncertainty_score
from budget_workshop import optimize_for_budget

@dataclass(frozen=True)
class RankedMatch:
    number: int
    home: str
    away: str
    score: float
    explanation: str

@dataclass(frozen=True)
class Cleaner:
    number: int
    home: str
    away: str
    sign: str
    model_probability: float
    public_share: float
    value_index: float
    cleaner_score: float


def coupon_type(matches: Sequence[MatchInput]) -> tuple[str, str]:
    fav = [max(m.model) for m in matches]
    uncertainty = sum(uncertainty_score(m.model) for m in matches) / max(1, len(matches))
    strong = sum(p >= .60 for p in fav)
    traps = sum((max(m.public) - m.model[max(range(3), key=lambda i:m.public[i])]) >= .10 for m in matches)
    if uncertainty >= .91:
        return "MYCKET SVÅR", "Många matcher är jämna. Budgeten behöver spridas över fler möjliga resultat."
    if strong >= 7 and traps <= 2:
        return "FAVORITBETONAD", "Flera matcher har tydliga favoriter. Det kan ge fler möjliga spikar, men överstreckade favoriter ska fortfarande granskas."
    if traps >= 4 or uncertainty >= .84:
        return "SKRÄLLVÄNLIG", "Flera favoriter ser sårbara eller hårt streckade ut. Garderingar mot populära tecken kan vara extra värdefulla."
    return "NORMAL", "Kupongen har en blandning av tydliga och öppna matcher. Streckverket balanserar sannolikhet och spelvärde."


def predictability_ranking(matches: Sequence[MatchInput]) -> list[RankedMatch]:
    out=[]
    for m in matches:
        certainty=1-uncertainty_score(m.model)
        out.append(RankedMatch(m.number,m.home,m.away,certainty,
            f"Modellens högsta chans är {max(m.model)*100:.0f} %."))
    return sorted(out,key=lambda x:x.score,reverse=True)


def value_ranking(matches: Sequence[MatchInput]) -> list[RankedMatch]:
    out=[]
    for m in matches:
        edges=[m.model[i]-m.public[i] for i in range(3)]
        i=max(range(3),key=lambda j:edges[j])
        out.append(RankedMatch(m.number,m.home,m.away,edges[i],
            f"{SIGNS[i]} bedöms {edges[i]*100:+.0f} procentenheter högre än spelarnas streck."))
    return sorted(out,key=lambda x:x.score,reverse=True)


def best_cross(matches: Sequence[MatchInput]) -> Cleaner | None:
    candidates=[]
    for m in matches:
        edge=m.model[1]-m.public[1]
        if edge <= .02 or m.model[1] < .22:
            continue
        ratio=m.model[1]/max(m.public[1],.01)
        score=edge * (0.5 + m.model[1])
        candidates.append(Cleaner(m.number,m.home,m.away,"X",m.model[1],m.public[1],ratio,score))
    return max(candidates,key=lambda x:x.cleaner_score) if candidates else None


def coupon_cleaners(matches: Sequence[MatchInput], limit:int=5) -> list[Cleaner]:
    out=[]
    for m in matches:
        for i,sign in enumerate(SIGNS):
            p=m.model[i]; s=m.public[i]
            # Ett kupongrensande tecken måste både vara relativt lågstreckat och ha rimlig modellchans.
            if s >= .35 or p < .18 or p <= s + .025:
                continue
            ratio=p/max(s,.01)
            # Informationsinnehåll -log(streck) premierar ovanliga tecken, men sannolikhet och edge krävs.
            score=p * (p-s) * max(.0, -log(max(s,.01)))
            out.append(Cleaner(m.number,m.home,m.away,sign,p,s,ratio,score))
    return sorted(out,key=lambda x:x.cleaner_score,reverse=True)[:limit]


def three_systems(matches: Sequence[MatchInput], budget:int, locks=None):
    budget=max(1,int(budget))
    # Samma budgetram, tre tydligt olika mål. Jackpot använder VÄRDE-målet; vi hittar inte på skrällar.
    safe=optimize_for_budget(matches,budget,"MAX 13",locks)
    balanced=optimize_for_budget(matches,budget,"VÄRDE",locks)
    jackpot=optimize_for_budget(matches,budget,"VÄRDE",locks)
    return {"FÖRSIKTIGT":safe,"STRECKVERKETS VAL":balanced,"HÖGRE POTENTIAL":jackpot}


def countercheck(matches: Sequence[MatchInput], system:dict) -> list[str]:
    notes=[]
    selections=system.get("selections",[])
    for m,sel in zip(matches,selections):
        pub_i=max(range(3),key=lambda i:m.public[i])
        pub_sign=SIGNS[pub_i]
        if len(sel)==1 and sel[0]==pub_sign and m.public[pub_i]-m.model[pub_i] >= .10:
            notes.append(f"Match {m.number}: systemet spikar ett populärt tecken som modellen bedömer tydligt lägre än spelarna. Överväg gardering.")
        if len(sel)>=2 and max(m.model)>=.68:
            best=SIGNS[max(range(3),key=lambda i:m.model[i])]
            if best in sel:
                notes.append(f"Match {m.number}: en stark modellfavorit är garderad. Kontrollera om pengarna gör större nytta i en annan match.")
    return notes[:5] or ["Ingen tydlig strategisk svaghet hittades i den här enkla motkontrollen."]
