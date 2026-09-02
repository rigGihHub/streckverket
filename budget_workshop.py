from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from core import optimize_system

@dataclass(frozen=True)
class BudgetPoint:
    budget: int
    rows: int
    coverage: float
    cost: float
    delta_cost: float
    delta_coverage_pp: float
    marginal_pp_per_kr: float
    selections: tuple[tuple[str,...],...]

def optimize_for_budget(matches, budget:int, strategy:str="MAX 13", locks=None, row_price:float=1.0):
    if budget < row_price:
        raise ValueError("Budgeten är lägre än priset för en rad.")
    max_rows=max(1,int(budget//row_price))
    result=optimize_system(matches,max_rows,strategy,locks)
    return {
        **result,
        "budget": budget,
        "cost": result["rows"]*row_price,
        "unused_budget": budget-result["rows"]*row_price,
        "row_price": row_price,
    }

def budget_curve(matches, budgets:Iterable[int], strategy:str="MAX 13", locks=None, row_price:float=1.0):
    points=[]
    prev=None
    for budget in sorted(set(int(b) for b in budgets if b >= row_price)):
        r=optimize_for_budget(matches,budget,strategy,locks,row_price)
        dcost=0.0 if prev is None else r["cost"]-prev.cost
        dcov=0.0 if prev is None else (r["coverage"]-prev.coverage)*100
        marginal=(dcov/dcost) if dcost>0 else 0.0
        point=BudgetPoint(
            budget=budget, rows=r["rows"], coverage=r["coverage"], cost=r["cost"],
            delta_cost=dcost, delta_coverage_pp=dcov, marginal_pp_per_kr=marginal,
            selections=tuple(tuple(x) for x in r["selections"]),
        )
        points.append(point)
        prev=point
    return points

def nearby_budgets(target:int):
    target=max(1,int(target))
    candidates={
        max(1,target//2),
        max(1,int(target*.75)),
        max(1,int(target*.9)),
        target,
        int(target*1.1),
        int(target*1.25),
        int(target*1.5),
        target*2,
    }
    return sorted(candidates)

def best_value_step(points:list[BudgetPoint]):
    eligible=[p for p in points if p.delta_cost>0 and p.delta_coverage_pp>0]
    return max(eligible,key=lambda p:p.marginal_pp_per_kr) if eligible else None

def compare_budget_points(lower:BudgetPoint,higher:BudgetPoint):
    added_cost=higher.cost-lower.cost
    added_cov=(higher.coverage-lower.coverage)*100
    return {
        "added_cost": added_cost,
        "added_coverage_pp": added_cov,
        "marginal_pp_per_kr": added_cov/added_cost if added_cost>0 else 0.0,
        "rows_added": higher.rows-lower.rows,
    }
