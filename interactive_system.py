from __future__ import annotations
from dataclasses import dataclass
from math import prod
from typing import Iterable

SIGNS=("1","X","2")
IDX={"1":0,"X":1,"2":2}

@dataclass(frozen=True)
class InteractiveSystem:
    selections: tuple[tuple[str,...], ...]
    rows: int
    coverage: float
    cost: float

@dataclass(frozen=True)
class UpgradeCandidate:
    match_number: int
    home: str
    away: str
    add_sign: str
    rows_before: int
    rows_after: int
    extra_cost: float
    coverage_before: float
    coverage_after: float
    coverage_gain_pp: float
    gain_per_kr: float
    new_selection: tuple[str,...]

def normalize_selection(selection: Iterable[str]) -> tuple[str,...]:
    chosen=tuple(s for s in SIGNS if s in set(selection))
    if not chosen:
        raise ValueError("Varje match måste ha minst ett tecken.")
    return chosen

def rows_for_selections(selections: Iterable[Iterable[str]]) -> int:
    return prod(len(normalize_selection(s)) for s in selections)

def coverage_for_selections(matches, selections: Iterable[Iterable[str]]) -> float:
    coverage=1.0
    for m, selection in zip(matches, selections):
        sel=normalize_selection(selection)
        coverage *= sum(float(m.model[IDX[s]]) for s in sel)
    return coverage

def evaluate_interactive_system(matches, selections, row_price: float=1.0) -> InteractiveSystem:
    normalized=tuple(normalize_selection(s) for s in selections)
    if len(normalized)!=len(matches):
        raise ValueError("Antalet val måste motsvara antalet matcher.")
    rows=rows_for_selections(normalized)
    return InteractiveSystem(normalized, rows, coverage_for_selections(matches,normalized), rows*row_price)

def rank_next_upgrades(matches, selections, row_price: float=1.0) -> list[UpgradeCandidate]:
    base=evaluate_interactive_system(matches,selections,row_price)
    candidates=[]
    for i,(m,current) in enumerate(zip(matches,base.selections)):
        for sign in SIGNS:
            if sign in current:
                continue
            changed=list(base.selections)
            changed[i]=normalize_selection((*current,sign))
            nxt=evaluate_interactive_system(matches,changed,row_price)
            extra=nxt.cost-base.cost
            gain=max(0.0,nxt.coverage-base.coverage)
            candidates.append(UpgradeCandidate(
                match_number=m.number,home=m.home,away=m.away,add_sign=sign,
                rows_before=base.rows,rows_after=nxt.rows,extra_cost=extra,
                coverage_before=base.coverage,coverage_after=nxt.coverage,
                coverage_gain_pp=gain*100,
                gain_per_kr=(gain*100/extra) if extra>0 else 0.0,
                new_selection=nxt.selections[i],
            ))
    return sorted(candidates,key=lambda x:(x.gain_per_kr,x.coverage_gain_pp),reverse=True)

def best_next_upgrade(matches,selections,row_price:float=1.0):
    ranked=rank_next_upgrades(matches,selections,row_price)
    return ranked[0] if ranked else None
