from __future__ import annotations

from html import escape
from typing import Iterable, Sequence

SIGNS = ("1", "X", "2")


def selection_kind(selection: Sequence[str]) -> str:
    size = len(tuple(selection))
    if size <= 1:
        return "SPIK"
    if size == 2:
        return "HALV"
    return "HEL"


def system_instruction(selection: Sequence[str]) -> str:
    selected = tuple(str(sign) for sign in selection if str(sign) in SIGNS)
    if not selected:
        return "–"
    return " + ".join(selected)


def _pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, float(value))) * 100))


def explain_match(match: object, selection: Sequence[str]) -> str:
    """Return a short, beginner-safe explanation grounded in frozen model/public inputs."""
    selected = tuple(str(sign) for sign in selection if str(sign) in SIGNS)
    if not selected:
        return "Inget tecken är valt i systemförslaget för den här matchen."

    model = tuple(float(v) for v in getattr(match, "model", (0.0, 0.0, 0.0)))
    public = tuple(float(v) for v in getattr(match, "public", (0.0, 0.0, 0.0)))
    if len(model) != 3 or len(public) != 3:
        return f"Systemförslaget använder {system_instruction(selected)} här. Mer underlag saknas för en säkrare kortförklaring."

    kind = selection_kind(selected)
    if kind == "SPIK":
        sign = selected[0]
        idx = SIGNS.index(sign)
        edge = model[idx] - public[idx]
        if edge >= 0.05:
            return (
                f"Spik {sign}. Modellen sätter {sign} till {_pct(model[idx])} %, medan spelarna har streckat det till "
                f"{_pct(public[idx])} %. Systemet låter därför {sign} stå ensamt här."
            )
        if model[idx] == max(model) and model[idx] >= 0.55:
            return (
                f"Spik {sign}. Det är modellens tydligaste utfall i matchen med {_pct(model[idx])} %. "
                "Därför använder systemförslaget bara ett tecken här."
            )
        return (
            f"Spik {sign}. Systemförslaget använder bara {sign} i den här matchen. "
            "Det sparar tecken till andra matcher, men är förstås ingen garanti för rätt."
        )

    if kind == "HALV":
        omitted = next(sign for sign in SIGNS if sign not in selected)
        omitted_idx = SIGNS.index(omitted)
        public_fav_idx = max(range(3), key=lambda i: public[i])
        if omitted_idx == public_fav_idx and public[omitted_idx] - model[omitted_idx] >= 0.06:
            return (
                f"Halvgardering {system_instruction(selected)}. Tecknet {omitted} är folkets favorit, men är streckat till "
                f"{_pct(public[omitted_idx])} % mot modellens {_pct(model[omitted_idx])} %. Systemet går därför emot det tecknet."
            )
        selected_probs = sorted((model[SIGNS.index(sign)] for sign in selected), reverse=True)
        if selected_probs[-1] >= 0.25:
            return (
                f"Halvgardering {system_instruction(selected)}. Båda valda utfallen har tydlig chans i modellen "
                f"({_pct(selected_probs[0])} % och {_pct(selected_probs[1])} %), så systemet skyddar två tecken."
            )
        return (
            f"Halvgardering {system_instruction(selected)}. Systemet vill ha skydd för två möjliga utfall här "
            f"och lämnar {omitted} utanför."
        )

    max_idx = max(range(3), key=lambda i: model[i])
    max_sign = SIGNS[max_idx]
    if model[max_idx] < 0.45:
        return (
            f"Helgardering 1 + X + 2. Matchen är öppen i modellen: inget utfall når 45 %. "
            "Systemet tar därför med alla tre tecknen."
        )
    spread = max(model) - min(model)
    if spread <= 0.20:
        return (
            "Helgardering 1 + X + 2. Modellens tre utfall ligger relativt nära varandra, "
            "så systemet vill inte kasta bort något tecken."
        )
    return (
        f"Helgardering 1 + X + 2. {max_sign} är modellens förstaval, men systemet behåller även de andra utfallen "
        "för att minska risken att just den här matchen fäller raden."
    )


def build_novice_rows(matches: Iterable[object], selections: Sequence[Sequence[str]]) -> list[dict]:
    matches = list(matches)
    if len(matches) != len(selections):
        raise ValueError("Antalet matcher och systemval måste vara lika.")

    rows: list[dict] = []
    for match, raw_selection in zip(matches, selections):
        selection = tuple(str(sign) for sign in raw_selection if str(sign) in SIGNS)
        rows.append({
            "number": int(getattr(match, "number")),
            "home": str(getattr(match, "home")),
            "away": str(getattr(match, "away")),
            "selection": selection,
            "kind": selection_kind(selection),
            "instruction": system_instruction(selection),
            "explanation": explain_match(match, selection),
        })
    return rows


def render_novice_system_board(matches: Iterable[object], selections: Sequence[Sequence[str]]) -> str:
    rows = build_novice_rows(matches, selections)
    parts = [
        '<div class="novice-system-board">',
        '<div class="novice-system-head"><span>MATCH</span><span>1</span><span>X</span><span>2</span><span>VAL</span></div>',
    ]
    for row in rows:
        signs = []
        for sign in SIGNS:
            on = " on" if sign in row["selection"] else ""
            aria = "valt" if sign in row["selection"] else "inte valt"
            signs.append(
                f'<span class="novice-sign{on}" aria-label="{escape(sign)} {aria}">{escape(sign)}</span>'
            )
        parts.append(
            '<div class="novice-system-row">'
            f'<div class="novice-match"><b>{row["number"]}.</b> '
            f'<span>{escape(row["home"])} – {escape(row["away"])}</span></div>'
            + "".join(signs)
            + f'<div class="novice-kind {row["kind"].lower()}">{row["kind"]}</div>'
            + '</div>'
        )
    parts.append('</div>')
    parts.append(
        '<div class="novice-system-legend">'
        '<span><b>SPIK</b> = ett tecken</span>'
        '<span><b>HALV</b> = två tecken</span>'
        '<span><b>HEL</b> = alla tre</span>'
        '</div>'
    )
    return "".join(parts)
