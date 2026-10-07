# Streckverket v3.56 – Strategy Confidence & Multiple Testing Guard

## Problem
När många strategier jämförs i många kupongmiljöer kommer vissa historiska mönster att se starka ut av slump. Ett rått segmentresultat får därför inte ensam upphöjas till en stabil signal.

## Metod
- Segmenten är fortfarande förhandsbestämda från frysta förhandsdata.
- Minst 30 gemensamma färdigspelade prospektiva kuponger krävs innan ett segment går in i konfidensfamiljen.
- Varje strategipar testas på samma kuponger.
- På kupongnivå räknas vilken strategi som täckte fler rätt; oavgjorda kuponger ger ingen riktning.
- Ett exakt tvåsidigt teckentest används diagnostiskt under nollhypotesen 50/50 mellan A och B.
- Alla kvalificerade segmenttester korrigeras tillsammans med Holm-metoden för familjevis felrisk.

## Tolkning
`SIGNAL EFTER MULTIPEL-KORRIGERING` betyder bara att det observerade parresultatet överlevde detta diagnostiska filter i den aktuella testfamiljen. Det är inte bevis på ROI, kausalitet, oberoende observationer eller spel-edge och får inte automatiskt ändra strategi.

## Varför inte bara råa p-värden?
Ju fler segment som granskas, desto större chans att minst ett ser imponerande ut av slump. Holm-korrigeringen gör kravet strängare när testfamiljen växer och är transparent utan att kräva externa statistikbibliotek.

## Begränsningar
- Kuponger är inte garanterat statistiskt oberoende.
- Segment och strategier kan vara korrelerade.
- Teckentestet använder bara riktning på kupongnivå och kastar storleken på vinst/förlust ur själva p-värdet; snittlig träffskillnad visas separat som effektbeskrivning.
- 30 kuponger är en konservativ produktspärr, inte en universell statistisk sanning.
