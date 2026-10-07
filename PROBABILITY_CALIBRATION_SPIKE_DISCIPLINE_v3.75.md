# Streckverket v3.75 – Probability Calibration & Spike Discipline Lab

Målet är att mäta före vi ändrar. Releasen läser endast frysta prospektiva FacitCoupon-snapshots och senare faktiskt utfall.

## Nytt
- kalibreringsintervall 50–55, 55–60, 60–65, 65–70, 70–75, 75–80 och 80+ %
- separat diagnostik för matcher systemet faktiskt spikade
- separat 1/X/2-kalibrering
- Brier score och log loss för Streckverket respektive verifierat bookmakerankare
- saknad bookmakerdata exkluderas; ingen retroaktiv backfill
- minst 20 kompletta prospektiva kuponger innan labbet får betraktas som granskningsredo

## Medvetet inte ändrat
`model_engine.py` och `strategy_engine.py` är oförändrade. v3.75 inför ingen automatisk spiktröskel och ingen ny modellvikt. Nästa prediktiva experiment ska väljas först när prospektiva data faktiskt motiverar det.
