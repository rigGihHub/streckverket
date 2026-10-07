# Streckverket v3.77.0 – Market Anchor Decision Lab

v3.77 inför en konservativ beslutsgrind ovanpå v3.75–v3.76:s prospektiva diagnostik.

## Syfte

Besvara frågan: **finns det tillräcklig prospektiv evidens för att ens testa en prediktiv modelländring?**

Beslutsgrinden använder endast:
- parade frysta Streckverket-/bookmakersannolikheter med facit,
- fasta minimiantal för kuponger och matcher,
- fasta avvikelsesegment modell–marknad,
- verifierade leave-one-signal-out-snapshots.

## Regler

- Minst 20 kuponger och 200 parade matcher krävs för mogen modell-vs-marknad-bedömning.
- Minst 50 observationer över minst 10 kuponger krävs per signal.
- Ett avvikelsesegment måste ha minst 50 matcher innan det får skapa en riskvarning.
- Om marknaden är bättre på både Brier och log loss rekommenderas endast ett separat experiment närmare marknadsankaret.
- Om modellen är bättre på båda måtten krävs dessutom mogen positiv signalablation innan en specifik signal får pekas ut som experimentkandidat.
- Blandad evidens betyder: ändra inget.
- Ingen produktionsvikt ändras automatiskt.
- `model_engine.py` och `strategy_engine.py` ändras inte i v3.77.

Detta är en beslutsgrind för forskning/validering, inte bevis på edge, ROI eller framtida 13 rätt.
