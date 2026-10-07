# Streckverket v3.60 – Verified Pre-Kickoff Market Quality

## Syfte
Mäta hur bookmakerbilden förändras efter en sparad snapshot fram till den senaste verifierade marknadspunkt som Streckverket faktiskt har före avspark.

## Metodskydd
- Begreppet **closing line** används inte.
- Punkter efter avspark exkluderas.
- Saknad/ogiltig timing ger ingen fabricerad senmarknad.
- Rörelse mot modellen är diagnostik och inte bevis på positivt EV eller edge.
- Ingen automatisk prognos- eller strategivikt ändras.

## UI
Text-TV **562 RÖRELSER** samt tabell i Facit & lärande.

## Prediktiv ändring
`predictive_change=False`.
