from __future__ import annotations
from dataclasses import dataclass
from math import log
from typing import Sequence

SIGNS=("1","X","2")

@dataclass(frozen=True)
class MarketIntel:
    number:int; match:str; bookmaker_count:int; dispersion:float|None
    confidence:str; public_gap_pp:float; model_gap_pp:float
    public_sign:str; model_sign:str; outliers:tuple[str,...]; method:str


def _entropy(p):
    return -sum(float(x)*log(float(x)) for x in p if float(x)>0)/log(3)


def market_confidence(bookmakers:int, dispersion:float|None)->str:
    if bookmakers < 2 or dispersion is None: return "OTILLRÄCKLIG DATA"
    if bookmakers >= 5 and dispersion <= .025: return "HÖG"
    if bookmakers >= 3 and dispersion <= .055: return "NORMAL"
    return "OENIG"


def build_market_intelligence(matches:Sequence[object])->list[MarketIntel]:
    out=[]
    for m in matches:
        mk=tuple(float(x) for x in getattr(m,'market'))
        public=tuple(float(x) for x in getattr(m,'public'))
        model=tuple(float(x) for x in getattr(m,'model'))
        count=int(getattr(m,'market_bookmaker_count',0) or 0)
        disp=getattr(m,'market_dispersion',None)
        disp=float(disp) if disp is not None else None
        pub_d=[public[i]-mk[i] for i in range(3)]
        mod_d=[model[i]-mk[i] for i in range(3)]
        pi=max(range(3),key=lambda i:abs(pub_d[i])); mi=max(range(3),key=lambda i:abs(mod_d[i]))
        out.append(MarketIntel(int(getattr(m,'number')),f"{getattr(m,'home')} – {getattr(m,'away')}",count,disp,
            market_confidence(count,disp),100*pub_d[pi],100*mod_d[mi],SIGNS[pi],SIGNS[mi],
            tuple(getattr(m,'market_outliers',()) or ()),str(getattr(m,'market_consensus_method','') or '')))
    return out


def market_architecture_summary(matches:Sequence[object])->dict[str,object]:
    rows=build_market_intelligence(matches)
    known=[r for r in rows if r.dispersion is not None]
    return {
      'verified':sum(bool(getattr(m,'market_available',False)) for m in matches),
      'consensus_known':len(known), 'high':sum(r.confidence=='HÖG' for r in rows),
      'disagree':sum(r.confidence=='OENIG' for r in rows),
      'outliers':sum(len(r.outliers) for r in rows), 'rows':rows,
    }


def texttv_market_pages_html(matches:Sequence[object])->str:
    s=market_architecture_summary(matches); rows=s['rows']
    def line(r,kind):
        if kind=='market':
            d='–' if r.dispersion is None else f"{100*r.dispersion:.1f}%"
            return f"{r.number:02d} {r.match[:31]:31} {r.bookmaker_count:2d} BM  SPR {d:>5} {r.confidence}"
        if kind=='public': return f"{r.number:02d} {r.match[:31]:31} {r.public_sign} {r.public_gap_pp:+5.1f}pp mot marknad"
        if kind=='model': return f"{r.number:02d} {r.match[:31]:31} {r.model_sign} {r.model_gap_pp:+5.1f}pp mot marknad"
    blocks=[]
    pages=[('560 MARKNAD', [f"VERIFIERAD {s['verified']}/13  KONSENSUSDIAG {s['consensus_known']}/13", f"HÖG KONFIDENS {s['high']}  OENIG {s['disagree']}  OUTLIERS {s['outliers']}"]+[line(r,'market') for r in rows]),
           ('561 OENIGHET',[line(r,'market') for r in sorted(rows,key=lambda x:(x.dispersion is None,-(x.dispersion or 0)))[:13]]),
           ('563 STRECK vs MARKNAD',[line(r,'public') for r in sorted(rows,key=lambda x:-abs(x.public_gap_pp))]),
           ('564 MODELL vs MARKNAD',[line(r,'model') for r in sorted(rows,key=lambda x:-abs(x.model_gap_pp))])]
    for title,ls in pages:
        body='\n'.join(ls)
        blocks.append(f'<div class="texttv-market"><b>{title}</b><pre>{body}</pre></div>')
    blocks.append('<div class="texttv-market"><b>566 KONFIDENS</b><pre>MARKNADSKONFIDENS = KÄLLBREDD + BOOKMAKER-SAMSTÄMMIGHET\nINTE SAMMA SAK SOM SÄKER MATCHPROGNOS\nINGEN NY MODELLVIKT FRÅN DENNA SIDA</pre></div>')
    return ''.join(blocks)
