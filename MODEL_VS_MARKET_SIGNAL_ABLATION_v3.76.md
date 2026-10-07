# Streckverket v3.76.0 – Model vs Market & Signal Ablation Lab

## Syfte
Nästa steg mot 13 rätt är att avgöra om Streckverkets justerade sannolikheter faktiskt förbättrar bookmakerankaret och vilka verifierade signaler som bidrar positivt eller negativt.

## Nytt
- Parad modell-vs-marknad-jämförelse på exakt samma prospektivt frysta matcher.
- Brier score och log loss redovisas som modellens vinst/förlust mot marknaden.
- Avvikelsegrupper 0–2,5, 2,5–5, 5–10 och 10+ procentenheter visar om större modellflyttar håller bättre eller sämre.
- Leave-one-signal-out använder endast redan sparade kontrafaktiska FactorSnapshots.
- Signalbedömning kräver både observationer och flera separata kuponger.

## Metodskydd
Saknad bookmakerdata exkluderas. Ingen historisk backfill görs. Signalablation visar marginalbidrag, inte säker kausalitet, eftersom signaler kan samverka. Inga vikter eller regler ändras automatiskt.

## Motorer
`model_engine.py` och `strategy_engine.py` ska vara byte-identiska med v3.75.0.
