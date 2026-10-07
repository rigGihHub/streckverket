# Streckverket v3.80 – Experiment Lifecycle & Candidate Registry

## Syfte

v3.80 gör shadow-experiment till explicit registrerade och spårbara objekt. Varje kandidat har ett stabilt experiment-ID, en förhandsregistrerad regel och en deterministisk livscykel. Produktionsmodellen ändras inte.

## Livscykel

Ett registrerat experiment kan vara:

- VÄNTAR PÅ BESLUTSGRIND
- AKTIVT SHADOW-EXPERIMENT
- MOGEN FÖR FÖRSTA GRANSKNING
- PAUSAD FÖR MANUELL GRANSKNING
- FÖRKASTAT

Status härleds endast från den explicita kandidatdefinitionen, v3.77-grinden och verkligt prospektivt sparade shadow-resultat.

## Viktigt metodskydd

- Ett experiment som förkastats får inga nya shadow-snapshots.
- Ett experiment som klarat v3.79:s promotion-grind pausas i shadow-fasen för separat manuell granskning.
- Ingen kandidat återaktiveras genom versionsbyte eller gammal historik.
- Okända experiment-ID:n körs inte.
- Ingen automatisk promotion till produktion finns.
- `model_engine.py` och `strategy_engine.py` är oförändrade.

## Första registrerade experimentet

`market_pull_25_v1`

Regel: 75 % fryst produktionsprognos + 25 % fryst verifierat bookmakerankare. Parametern 25 % är förhandsregistrerad sedan v3.78 och optimeras inte mot gammalt facit.
