from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

SIGNS = ("1", "X", "2")


@dataclass(frozen=True)
class CouponReadiness:
    score: int
    status: str
    short_reason: str
    blockers: tuple[str, ...]
    ready_matches: int
    total_matches: int


@dataclass(frozen=True)
class ReadinessGuidance:
    headline: str
    message: str
    next_step: str
    tone: str


def readiness_guidance(
    readiness: CouponReadiness,
    *,
    demo: bool = False,
    market_missing_count: int = 0,
) -> ReadinessGuidance:
    """Turn readiness diagnostics into one concrete novice action.

    This function does not alter readiness or system selection. It only translates
    existing status/blockers into plain-language next steps.
    """
    blockers = tuple(str(x).lower() for x in (readiness.blockers or ()))

    if demo or "demo" in readiness.status.lower():
        return ReadinessGuidance(
            headline="HÄMTA RIKTIG KUPONG",
            message="Du tittar på testdata. Systemet är bara till för att prova appen.",
            next_step="Hämta den aktuella Stryktipskupongen innan du använder något spelråd.",
            tone="error",
        )

    if market_missing_count > 0 or any("marknadsodds" in b for b in blockers):
        return ReadinessGuidance(
            headline="SPELA INTE ÄNNU",
            message=f"Aktuella bookmakerodds saknas för {max(1, int(market_missing_count))} av 13 matcher. Då saknas Streckverkets viktigaste marknadsankare.",
            next_step="Tryck Analysera kupongen igen. Om odds fortfarande saknas: vänta och försök igen senare.",
            tone="error",
        )

    if readiness.status == "SPELKlar".upper():
        return ReadinessGuidance(
            headline="SYSTEMET KAN ANVÄNDAS",
            message="Underlaget är tillräckligt komplett för att Streckverket ska kunna ge sitt aktuella systemförslag.",
            next_step="Kontrollera de 13 tecknen nedan. Om det är långt kvar till spelstopp kan du analysera igen senare för färskare information.",
            tone="success",
        )

    if any("startelv" in b for b in blockers):
        return ReadinessGuidance(
            headline="VÄNTA OM DU KAN",
            message="Startelvsinformationen är inte komplett ännu. Den blir ofta bättre närmare avspark.",
            next_step="Analysera kupongen igen närmare spelstopp innan du lämnar in systemet.",
            tone="warning",
        )

    if any("källkonflikt" in b for b in blockers):
        return ReadinessGuidance(
            headline="KONTROLLERA UNDERLAGET",
            message="Två eller flera källor säger olika saker om någon del av kupongen.",
            next_step="Analysera igen. Om konflikten finns kvar kan du öppna Expertläge och granska datakällorna innan spel.",
            tone="warning",
        )

    if readiness.status == "NÄSTAN SPELKLAR":
        return ReadinessGuidance(
            headline="NÄSTAN KLART",
            message="Systemförslaget går att läsa, men någon viktig information är fortfarande för tunn eller gammal.",
            next_step="Analysera kupongen igen närmare spelstopp för att försöka fylla luckorna.",
            tone="warning",
        )

    return ReadinessGuidance(
        headline="SPELA INTE ÄNNU",
        message="För mycket viktig matchinformation saknas eller är ännu inte verifierad.",
        next_step="Tryck Analysera kupongen igen. Om läget inte förbättras: vänta tills mer information finns.",
        tone="error",
    )


def sign_meaning(sign: str, home: str = "hemmalaget", away: str = "bortalaget") -> str:
    if sign == "1":
        return f"{home} vinner"
    if sign == "X":
        return "matchen slutar oavgjort"
    if sign == "2":
        return f"{away} vinner"
    return "okänt tecken"


def selection_name(selection: Sequence[str]) -> str:
    count = len(tuple(selection))
    if count <= 1:
        return "Spik"
    if count == 2:
        return "Halvgardering"
    return "Helgardering"


def selection_explanation(selection: Sequence[str], home: str, away: str) -> str:
    selected = tuple(selection)
    if len(selected) == 1:
        return (
            f"Vi väljer bara **{selected[0]}** – alltså att {sign_meaning(selected[0], home, away)}. "
            "Det kallas en spik och håller nere kostnaden eftersom vi bara betalar för ett möjligt resultat i matchen."
        )
    if len(selected) == 2:
        meanings = " eller ".join(sign_meaning(s, home, away) for s in selected)
        return (
            f"Vi väljer **{' '.join(selected)}**. Systemet klarar då att {meanings}. "
            "Det kallas halvgardering: två av de tre möjliga resultaten är med."
        )
    return (
        "Vi väljer **1 X 2**. Då klarar systemet hemmaseger, oavgjort eller bortaseger. "
        "Det kallas helgardering och ger mest skydd i matchen, men gör systemet dyrare."
    )


def plain_classification(classification: str) -> str:
    texts = {
        "Stark spik": "Ett resultat ser tydligt mest sannolikt ut. Här kan vi spara rader genom att bara välja det resultatet.",
        "Värdespik": "Ett resultat ser både starkt ut och är mindre populärt bland spelarna än vår modell tycker att det borde vara.",
        "Riskspik": "Vi väljer ett enda resultat för att hålla nere systemets pris, men matchen är inte lika säker som våra bästa spikar.",
        "Halvgardering": "Matchen är osäker nog för att vi vill ha med två möjliga resultat.",
        "Helgardering": "Matchen är så svårbedömd att alla tre resultaten kan vara värda att ta med.",
        "Skrälläge": "Ett mindre populärt resultat verkar ha bättre chans än vad spelarnas val antyder.",
        "Fällan": "Många spelare har valt favoriten, men vår modell tycker att den är mindre säker än spelarna verkar tro.",
    }
    return texts.get(classification, "Streckverket jämför vår bedömning med hur andra spelare har valt.")


def edge_explanation(model_probability: float, public_share: float, sign: str) -> str:
    diff = (model_probability - public_share) * 100
    if diff >= 3:
        return (
            f"Vi uppskattar chansen för **{sign}** till {model_probability*100:.0f} %, medan cirka "
            f"{public_share*100:.0f} % av spelarna har valt det. Vi ser alltså ungefär {diff:.0f} procentenheters fördel."
        )
    if diff <= -3:
        return (
            f"Cirka {public_share*100:.0f} % av spelarna har valt **{sign}**, men vår modell uppskattar chansen till "
            f"{model_probability*100:.0f} %. Resultatet ser därför mer populärt ut än vad sannolikheten motiverar."
        )
    return (
        f"Vår uppskattning ({model_probability*100:.0f} %) ligger nära spelarnas val ({public_share*100:.0f} %). "
        "Här ser vi ingen stor skillnad att utnyttja."
    )


def _card_score(card) -> int:
    try:
        return max(0, min(100, int(round(float(card.readiness_score)))))
    except Exception:
        return 0


def _friendly_missing(value: str) -> str:
    labels = {
        "market": "aktuella odds från marknaden",
        "team_strength": "lagens grundstyrka",
        "home_away_form": "hemma- och bortaprestationer",
        "injury_suspension": "skador och avstängningar",
        "confirmed_lineup": "bekräftade startelvor",
        "rest_schedule": "vila och spelschema",
        "weather": "väderinformation",
        "referee": "domarinformation",
        "fan_sentiment": "supporterinformation",
        "other": "övrig verifierad matchinformation",
    }
    return labels.get(value, value.replace("_", " "))


def coupon_readiness(cards: Iterable, selections: Sequence[Sequence[str]] | None = None, *, demo: bool = False) -> CouponReadiness:
    cards = list(cards)
    if not cards:
        return CouponReadiness(0, "VÄNTA", "Vi har ännu ingen kontrollerad matchinformation.", ("matchinformation saknas",), 0, 0)
    if demo:
        return CouponReadiness(0, "DEMO – INTE SPELKLAR", "Demodata är bara till för att prova appen.", ("hämta den riktiga kupongen först",), 0, len(cards))

    weights = []
    scores = []
    missing_counts: dict[str, int] = {}
    conflicts = 0
    for idx, card in enumerate(cards):
        score = _card_score(card)
        if selections and idx < len(selections):
            n = len(tuple(selections[idx]))
            weight = 1.35 if n == 1 else (1.10 if n == 2 else 0.90)
        else:
            weight = 1.0
        weights.append(weight)
        scores.append(score * weight)
        for item in getattr(card, "missing", ()) or ():
            missing_counts[item] = missing_counts.get(item, 0) + 1
        conflicts += len(getattr(card, "conflicts", ()) or ())

    score = int(round(sum(scores) / sum(weights))) if weights else 0
    ready_matches = sum(_card_score(c) >= 50 for c in cards)

    blockers = []
    critical_order = ("market", "injury_suspension", "confirmed_lineup", "team_strength", "home_away_form")
    for key in critical_order:
        count = missing_counts.get(key, 0)
        if count:
            blockers.append(f"{_friendly_missing(key)} saknas för {count} av {len(cards)} matcher")
    if conflicts:
        blockers.append(f"{conflicts} källkonflikt(er) behöver granskas")
    if not blockers and score < 75:
        blockers.append("några informationslager är ännu för svaga eller gamla")

    if score >= 75 and ready_matches >= max(1, len(cards) - 2) and not conflicts:
        status = "SPELKlar".upper()
        reason = "Underlaget är tillräckligt komplett för att Streckverket ska kunna ge ett aktuellt spelråd."
    elif score >= 50:
        status = "NÄSTAN SPELKLAR"
        reason = "Vi har en användbar grund, men det finns information som är värd att kontrollera innan du lämnar in."
    else:
        status = "VÄNTA"
        reason = "För mycket viktig matchinformation saknas eller är ännu inte verifierad."

    return CouponReadiness(score, status, reason, tuple(blockers[:4]), ready_matches, len(cards))


def confidence_words(score: int) -> str:
    if score >= 75:
        return "Bra underlag"
    if score >= 50:
        return "Ganska bra underlag"
    if score >= 25:
        return "Tunt underlag"
    return "Mycket tunt underlag"


def glossary() -> Mapping[str, str]:
    return {
        "1 / X / 2": "1 = hemmalaget vinner, X = oavgjort, 2 = bortalaget vinner.",
        "Spik": "Du väljer bara ett resultat i matchen. Billigare, men du åker ur systemet om just det tecknet är fel.",
        "Halvgardering": "Du väljer två av tre resultat. Det ger mer skydd men fler rader och högre kostnad.",
        "Helgardering": "Du väljer 1, X och 2. Matchen kan sluta hur som helst och ändå vara rätt i systemet.",
        "Streck": "Andelen av Svenska Spels spelare som har valt ett visst resultat.",
        "Fälla": "Ett populärt resultat som Streckverket bedömer som mindre säkert än spelarna verkar tro.",
        "Skräll": "Ett mindre populärt resultat som bedöms ha bättre chans än strecken antyder.",
        "Modell": "Streckverkets matematiska uppskattning av hur stor chans varje resultat har.",
        "13-rättstäckning": "Modellens uppskattning av sannolikheten att just de resultat som finns i systemet täcker alla 13 matcher. Det är ingen garanti.",
    }
