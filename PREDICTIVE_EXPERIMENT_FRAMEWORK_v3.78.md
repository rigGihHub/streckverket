# Streckverket v3.78 – Predictive Experiment Framework

## Syfte

v3.78 bygger ett prospektivt shadow-läge mellan v3.77:s beslutsgrind och en eventuell framtida ändring av produktionsmodellen.

## Grundregel

En kandidat får aldrig utvärderas genom att räknas bakåt på gamla facitkuponger. Kandidatens sannolikheter måste frysas före match tillsammans med produktionsprognosen och bookmakerankaret.

## Första förhandsregistrerade kandidat

Om v3.77 på moget prospektivt underlag visar att bookmakerankaret slår Streckverket på både Brier score och log loss aktiveras experimentet `market_pull_25_v1` för nya snapshots.

Kandidaten definieras på förhand som:

`75 % fryst produktionsprognos + 25 % fryst verifierat bookmakerankare`.

25-procentsvikten optimeras inte mot historiskt facit. Ändringar av vikten kräver ett nytt experiment-id och en ny prospektiv period.

## Isolering

Shadow-prognosen påverkar inte:

- systemtecken
- spikar/garderingar
- budget
- readiness
- produktionsmodell
- `model_engine.py`
- `strategy_engine.py`

## Bedömning

Kandidat, produktion och marknad jämförs på exakt samma färdiga shadow-observationer med Brier score och log loss.

Minst 100 färdiga matcher över minst 10 kuponger krävs innan shadow-resultatet får klassas som granskningsmoget. Även därefter sker ingen automatisk promotion till produktion.

## Proveniens

Varje sparad shadow-prognos innehåller experiment-id, etikett, kandidatregel och källmodellversion. Äldre kuponger utan shadow-data lämnas orörda.
