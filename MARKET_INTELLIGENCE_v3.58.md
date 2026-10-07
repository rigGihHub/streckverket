# Streckverket v3.58 – Market Intelligence Architecture

## Branschinfluens
Professionella sportsbook-plattformar separerar pricing/trading från riskhantering och använder stora mängder marknadsdata, automatisering och confidence. Streckverket kopierar inte operatörernas risk-/spelprofilering; det relevanta för ett Stryktipsverktyg är marknadens informationsstruktur.

## Infört
- Robust bookmakerkonsensus bevaras genom pipelinen i stället för att bara lämna ett aggregerat odds.
- Bookmaker-spridning, antal ingående bookmakers, bortfiltrerade outliers och konsensusmetod sparas prospektivt.
- Text-TV 560 MARKNAD, 561 OENIGHET, 563 STRECK vs MARKNAD, 564 MODELL vs MARKNAD och 566 KONFIDENS.
- Marknadskonfidens är ett datamått, inte en sannolikhet att tipset är rätt.
- Ingen automatisk modellvikt eller strategiändring.

## Medvetet inte infört
- Ingen spelarkundprofilering eller stake acceptance: det är sportsbook-riskhantering och inte Streckverkets uppgift.
- Ingen Betfair-likviditet förrän en verifierad datakälla faktiskt är integrerad.
- Ingen "sharp bookmaker"-etikett utan historiskt stöd/proveniens.
- Ingen påstådd edge från marknadsavvikelse.
