from __future__ import annotations

from html import escape
from typing import Sequence

from core import classify_match

SIGNS = ("1", "X", "2")


def _tag(match, selection: Sequence[str]) -> str:
    if len(selection) == 1:
        return "SPIK"
    cls = classify_match(match.model, match.public)
    if cls == "Fällan":
        return "FÄLLA"
    if cls == "Skrälläge":
        return "SKRÄLL"
    if len(selection) == 3:
        return "HELGARD"
    return "GARD"


def _page_shell(page: int, title: str, body: str, footer: str = "") -> str:
    footer_html = f'<div class="texttv-footer">{escape(footer)}</div>' if footer else ""
    return (
        '<div class="texttv-board">'
        f'<div class="texttv-pagebar"><span>{page:03d} STRECKVERKET</span><span>{escape(title)}</span></div>'
        f'{body}{footer_html}</div>'
    )


def texttv_index_html(*, rows: int, cost: float, spikes: int, guards: int, fulls: int, readiness_status: str) -> str:
    links = (
        '<div class="texttv-index">'
        '<div><b>551</b><span>SYSTEM</span></div>'
        '<div><b>552</b><span>MATCHRÅD</span></div>'
        '<div><b>553</b><span>SPIKAR</span></div>'
        '<div><b>554</b><span>FÄLLOR</span></div>'
        '<div><b>555</b><span>SKRÄLLAR</span></div>'
        '<div><b>556</b><span>DATASTATUS</span></div>'
        '<div><b>557</b><span>RADNYTTA</span></div>'
        '</div>'
        '<div class="texttv-summary">'
        f'<span>{int(rows)} RADER</span><span>{cost:.0f} KR</span>'
        f'<span>{int(spikes)} SPIK</span><span>{int(guards)} GARD</span><span>{int(fulls)} HEL</span>'
        f'<span>{escape(str(readiness_status).upper())}</span>'
        '</div>'
    )
    return _page_shell(100, "START", links, "VÄLJ SIDA NEDAN · SAMMA ANALYS, KORTARE VÄG")


def texttv_system_html(matches, selections) -> str:
    """Render the core system as a compact teletext-like board."""
    rows = [
        '<div class="texttv-row texttv-head"><span>NR MATCH</span><span>1</span><span>X</span><span>2</span><span>RÅD</span></div>',
    ]
    for match, selected in zip(matches, selections):
        selected = tuple(selected)
        cells = []
        for sign in SIGNS:
            state = " on" if sign in selected else ""
            cells.append(f'<span class="texttv-sign{state}">{sign if sign in selected else "·"}</span>')
        label = f"{int(match.number):02d} {match.home} - {match.away}"
        rows.append(
            '<div class="texttv-row">'
            f'<span class="texttv-match">{escape(label)}</span>'
            + "".join(cells)
            + f'<span class="texttv-tag">{_tag(match, selected)}</span>'
            + '</div>'
        )
    html = _page_shell(551, "SYSTEM", "".join(rows), "GULT = TECKEN I DITT SYSTEM")
    return html.replace("551 STRECKVERKET", "551 STRECKTIPS", 1)


def texttv_telegram_rows(matches, selections):
    """Short, deterministic copy for the normal view; no invented facts."""
    result = []
    for match, selected in zip(matches, selections):
        best_i = max(range(3), key=lambda i: match.model[i])
        best_sign = SIGNS[best_i]
        delta_pp = (match.model[best_i] - match.public[best_i]) * 100
        if len(selected) == 1:
            lead = f"SPIK {selected[0]}"
        elif len(selected) == 3:
            lead = "HELGARDERA"
        else:
            lead = "GARDERA " + "".join(selected)
        result.append({
            "number": match.number,
            "match": f"{match.home} - {match.away}",
            "lead": lead,
            "model_pick": best_sign,
            "model_probability": match.model[best_i],
            "public_share": match.public[best_i],
            "delta_pp": delta_pp,
        })
    return result


def texttv_advice_html(matches, selections) -> str:
    body = ['<div class="texttv-list">']
    for row in texttv_telegram_rows(matches, selections):
        delta = row["delta_pp"]
        body.append(
            '<div class="texttv-list-row">'
            f'<b>{int(row["number"]):02d}</b>'
            f'<span>{escape(row["match"])}</span>'
            f'<strong>{escape(row["lead"])}</strong>'
            f'<em>{row["model_pick"]} {row["model_probability"]*100:.0f}% / STRECK {row["public_share"]*100:.0f}% / {delta:+.0f}PP</em>'
            '</div>'
        )
    body.append('</div>')
    return _page_shell(552, "KORTA MATCHRÅD", "".join(body), "ENDAST MODELL + STRECK · INGA PÅHITTADE LAGNYHETER")


def texttv_spikes_html(matches, selections) -> str:
    rows = []
    for match, selected in zip(matches, selections):
        if len(selected) != 1:
            continue
        sign = selected[0]
        idx = SIGNS.index(sign)
        rows.append((match.model[idx], match, sign, match.public[idx]))
    rows.sort(key=lambda x: (-x[0], int(x[1].number)))
    if not rows:
        body = '<div class="texttv-empty">INGA SPIKAR I DET VALDA SYSTEMET</div>'
    else:
        body = '<div class="texttv-list">' + "".join(
            '<div class="texttv-list-row">'
            f'<b>{int(m.number):02d}</b><span>{escape(m.home)} - {escape(m.away)}</span>'
            f'<strong>SPIK {s}</strong><em>MODELL {p*100:.0f}% / STRECK {pub*100:.0f}%</em></div>'
            for p, m, s, pub in rows
        ) + '</div>'
    return _page_shell(553, "SPIKAR", body, "SPIK = ETT TECKEN I SYSTEMET")


def texttv_traps_html(matches, selections) -> str:
    rows = []
    for match, selected in zip(matches, selections):
        if classify_match(match.model, match.public) != "Fällan":
            continue
        public_i = max(range(3), key=lambda i: match.public[i])
        rows.append((match.public[public_i] - match.model[public_i], match, SIGNS[public_i], tuple(selected), public_i))
    rows.sort(key=lambda x: (-x[0], int(x[1].number)))
    if not rows:
        body = '<div class="texttv-empty">INGEN TYDLIG FAVORITFÄLLA JUST NU</div>'
    else:
        body = '<div class="texttv-list">' + "".join(
            '<div class="texttv-list-row">'
            f'<b>{int(m.number):02d}</b><span>{escape(m.home)} - {escape(m.away)}</span>'
            f'<strong>FÄLLA {fav}</strong>'
            f'<em>STRECK {m.public[i]*100:.0f}% / MODELL {m.model[i]*100:.0f}% / SYSTEM {"".join(sel)}</em></div>'
            for _, m, fav, sel, i in rows
        ) + '</div>'
    return _page_shell(554, "FÄLLOR", body, "FÄLLA = FOLKETS FAVORIT ÄR TYDLIGT HÅRDARE STRECKAD ÄN MODELLEN")


def texttv_upsets_html(matches, selections) -> str:
    rows = []
    for match, selected in zip(matches, selections):
        if classify_match(match.model, match.public) != "Skrälläge":
            continue
        candidates = [i for i in range(3) if match.public[i] <= .18 and match.model[i] >= .24 and match.model[i] - match.public[i] >= .08]
        if not candidates:
            continue
        i = max(candidates, key=lambda j: match.model[j] - match.public[j])
        rows.append((match.model[i] - match.public[i], match, SIGNS[i], tuple(selected), i))
    rows.sort(key=lambda x: (-x[0], int(x[1].number)))
    if not rows:
        body = '<div class="texttv-empty">INGET SKRÄLLÄGE UPPFYLLER MINIMIKRAVEN</div>'
    else:
        body = '<div class="texttv-list">' + "".join(
            '<div class="texttv-list-row">'
            f'<b>{int(m.number):02d}</b><span>{escape(m.home)} - {escape(m.away)}</span>'
            f'<strong>SKRÄLL {sign}</strong>'
            f'<em>MODELL {m.model[i]*100:.0f}% / STRECK {m.public[i]*100:.0f}% / SYSTEM {"".join(sel)}</em></div>'
            for _, m, sign, sel, i in rows
        ) + '</div>'
    return _page_shell(555, "SKRÄLLAR", body, "LÅGT STRECK RÄCKER ALDRIG · MODELLSTÖD KRÄVS")


def texttv_data_status_html(matches, readiness) -> str:
    market_ok = sum(bool(getattr(m, "market_available", False)) for m in matches)
    missing = len(matches) - market_ok
    blockers = list(getattr(readiness, "blockers", ()) or ())
    status = escape(str(getattr(readiness, "status", "OKÄND")))
    score = int(getattr(readiness, "score", 0))
    ready_matches = int(getattr(readiness, "ready_matches", 0))
    total_matches = int(getattr(readiness, "total_matches", len(matches)))
    body = (
        '<div class="texttv-status-grid">'
        f'<div><b>STATUS</b><span>{status}</span></div>'
        f'<div><b>DATAKVALITET</b><span>{score}/100</span></div>'
        f'<div><b>MARKNADSODDS</b><span>{market_ok}/{len(matches)}</span></div>'
        f'<div><b>REDO MATCHER</b><span>{ready_matches}/{total_matches}</span></div>'
        f'<div><b>SAKNAR MARKNAD</b><span>{missing}</span></div>'
        f'<div><b>BLOCKERARE</b><span>{len(blockers)}</span></div>'
        '</div>'
    )
    if blockers:
        body += '<div class="texttv-blockers">' + "".join(f'<div>• {escape(str(x))}</div>' for x in blockers[:5]) + '</div>'
    return _page_shell(556, "DATASTATUS", body, "DATAKVALITET ÄR INTE SAMMA SAK SOM SÄKER FOTBOLLSPROGNOS")



def texttv_guard_efficiency_html(matches, system) -> str:
    from guard_efficiency import guard_upgrade_candidates

    rows = guard_upgrade_candidates(matches, system)[:5]
    if not rows:
        body = '<div class="texttv-empty">INGEN LOKAL EXTRA GARDERING FINNS ATT JÄMFÖRA</div>'
    else:
        parts = ['<div class="texttv-list">']
        for rank, row in enumerate(rows, 1):
            parts.append(
                '<div class="texttv-list-row">'
                f'<b>{rank:02d}</b>'
                f'<span>M{row.match_number:02d} {escape(row.home)} - {escape(row.away)}</span>'
                f'<strong>+{escape(row.added_sign)} · {row.extra_rows} RADER</strong>'
                f'<em>+{row.delta_coverage_pp:.3f}PP TÄCKNING · {row.coverage_pp_per_100_extra_rows:.3f}PP / 100 EXTRA RADER</em>'
                '</div>'
            )
        parts.append('</div>')
        body = ''.join(parts)
    return _page_shell(
        557, 'RADNYTTA', body,
        'JÄMFÖRELSE AV LOKAL GARDERING · INTE VINSTPROGNOS · INTE UPPMANING ATT HÖJA INSATSEN'
    )

def texttv_decision_html(decision) -> str:
    """Page 100: compressed, action-first view derived from the existing system."""
    status = escape(str(decision.readiness_status))
    score = int(decision.readiness_score)
    status_class = "ok" if status == "SPELK LAR".replace(" ", "") else ("warn" if "NÄSTAN" in status else "stop")
    overview = (
        '<div class="texttv-decision-top">'
        f'<div><b>SPELA</b><span>{int(decision.rows)} RADER · {decision.cost:.0f} KR</span></div>'
        f'<div><b>BYGG</b><span>{int(decision.spikes)} SPIK · {int(decision.guards)} GARD · {int(decision.fulls)} HEL</span></div>'
        f'<div class="{status_class}"><b>NU?</b><span>{status} · {score}/100</span></div>'
        '</div>'
    )
    if decision.actions:
        actions = '<div class="texttv-actions">' + ''.join(
            '<div class="texttv-action">'
            f'<b>{escape(str(action.kind))}</b>'
            f'<strong>{escape(str(action.title))}</strong>'
            f'<span>{escape(str(action.detail))}</span>'
            '</div>'
            for action in decision.actions
        ) + '</div>'
    else:
        actions = '<div class="texttv-empty">INGEN EXTRA SNABBÅTGÄRD · FÖLJ SYSTEMSIDAN 551</div>'
    return _page_shell(100, "BESLUT", overview + actions, "SAMMA SYSTEM · KOMPRIMERAD VISNING · INGA NYA SPELRÅD")


def texttv_budget_reallocation_html(matches, system, *, locks=None) -> str:
    from budget_reallocation import reallocation_candidates

    rows = reallocation_candidates(matches, system, locks=locks)[:5]
    if not rows:
        body = '<div class="texttv-empty">INGEN BÄTTRE OMFÖRDELNING HITTAD MED EXAKT SAMMA RADANTAL</div>'
    else:
        parts = ['<div class="texttv-list">']
        for rank, row in enumerate(rows, 1):
            removed = ''.join(row.removed_signs) or '–'
            added = ''.join(row.added_signs) or '–'
            parts.append(
                '<div class="texttv-list-row">'
                f'<b>{rank:02d}</b>'
                f'<span>FLYTTA M{row.donor_match_number:02d} → M{row.recipient_match_number:02d}</span>'
                f'<strong>TA BORT {escape(removed)} · LÄGG TILL {escape(added)}</strong>'
                f'<em>SAMMA {row.rows} RADER · +{row.delta_coverage_pp:.3f}PP TÄCKNING</em>'
                '</div>'
            )
        parts.append('</div>')
        body = ''.join(parts)
    return _page_shell(
        558, 'OMFÖRDELA', body,
        'SAMMA RADBUDGET · LÅSTA MATCHER RÖRS INTE · INTE VINSTPROGNOS'
    )
