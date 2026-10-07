# Streckverket v3.59 – Market Disagreement Validation

## Syfte
v3.58 började spara bookmaker-spridning och konsensusproveniens. v3.59 använder den informationen prospektivt för att fråga om Streckverkets egna modellavvikelser beter sig olika när bookmakers är samstämmiga respektive oeniga.

## Prospektiv spärr
Endast snapshots med explicit modellversion v3.58.0 eller senare används. Äldre kuponger räknas inte in även om liknande fält råkar kunna återskapas. Saknad bookmaker-spridning exkluderas i stället för att uppskattas i efterhand.

## Marknadsmiljöer
Samma fasta regler som v3.58 används:
- HÖG: minst 5 bookmakers och dispersion högst 0,025.
- NORMAL: minst 3 bookmakers och dispersion högst 0,055.
- OENIG: övriga fall med minst 2 bookmakers och faktisk dispersion.

Varje miljö kräver minst 100 färdigspelade verifierade matcher från minst 20 separata kuponger innan status blir GRANSKNINGSBAR.

## Mått
För varje miljö visas modellens och marknadens Brier score, log loss och förstavalsträff. `Brier-fördel modell` definieras som marknadens Brier minus modellens Brier; positivt betyder därför att modellens sannolikhetsfördelning historiskt varit bättre i just gruppen.

## Modellgap × marknadsmiljö
Ett separat explorativt rutnät använder fasta modell–marknad-gap:
- LÅGT GAP: ≤ 0,04 total variation.
- NORMALT GAP: >0,04 och <0,08.
- HÖGT GAP: ≥0,08.

Även dessa celler måste nå 100 matcher och 20 kuponger för att bli granskningsbara. Gränserna optimeras inte efter facit.

## Viktig begränsning
v3.59 ändrar inte `model_engine.py`, `strategy_engine.py`, modellvikter eller systemstrategier. Resultaten är diagnostiska och får inte tolkas som bevisad ROI, edge eller kausal effekt av bookmaker-oenighet.
