# Streckverket v3.79 – Shadow Experiment Governance & Promotion Gate

Syftet är att förhindra att en shadow-kandidat flyttas vidare på grund av små samples, enstaka turkuponger eller marginella förbättringar.

## Fasta grindar

Första bedömning kräver minst 100 färdiga shadow-matcher över 10 kuponger. För promotion till **separat manuell produktionskandidat-granskning** krävs minst 200 matcher över 20 kuponger.

Kandidaten måste dessutom:

- slå produktionsbaseline på både Brier score och log loss,
- förbättra båda måtten med minst 0,5 % relativt,
- vinna på båda måtten i minst 60 % av kupongerna,
- inte ha mer än 25 % av sin absoluta Brier-effekt koncentrerad till en enda kupong.

Reglerna är fasta före utvärdering och ska inte trimmas mot facit. Blandad evidens ger ingen promotion. En kandidat som är sämre på både Brier och log loss förkastas.

## Viktigt

En godkänd grind betyder **inte** automatisk produktionssättning. Den betyder endast att kandidaten får gå vidare till en separat, versionsregistrerad och manuellt granskad produktionskandidat. `model_engine.py` och `strategy_engine.py` ändras inte i v3.79.
