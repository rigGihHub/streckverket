# Streckverket v3.55 – Strategy Robustness

## Syfte
Strategiliggan i v3.54 jämför strategier rättvist på samma prospektivt frysta kuponger. v3.55 frågar en svårare fråga: håller ett mönster i olika typer av kuponger, eller är det koncentrerat till en enda miljö?

## Förhandsbestämda kupongmiljöer
Segmenten skapas enbart från information som redan fanns när snapshoten sparades. Matchresultat används aldrig för segmenteringen.

- **Favoritbild:** favoritdominerad om minst 7 av 13 matcher har publikfavorit >=60 %, öppen om högst 3 har det, annars balanserad.
- **Publikträngsel:** medelvärdet av `1 - normaliserad entropi` för 1/X/2-strecken. Hög >=0,28, låg <=0,16, annars normal.
- **Modell–marknad-gap:** medelvärdet av total-variation mellan modell och verifierad bookmakerbas. Hög >=0,08, låg <=0,04, annars normal.

Trösklarna är fasta i kod. De optimeras inte efter historiska resultat.

## Rättvis jämförelse
Precis som i v3.54 jämförs A och B bara på kuponger där båda systemen frystes före spelstopp. Inom varje segment krävs minst 20 gemensamma färdigspelade kuponger.

Ett enda kupongurval som råkar tillhöra en kategori i flera dimensioner räcker inte för robusthet. Minst två olika miljöer inom samma dimension måste vara granskningsbara innan Streckverket lämnar statusen `FÖR LITE KONTRASTERANDE HISTORIK`.

## Vad statusen inte betyder
- ingen ROI beräknas
- ingen utdelningsmodell finns
- ingen edge anses bevisad
- segmentresultat ändrar aldrig systemstrategin automatiskt
- flera segment är explorativ/deskriptiv evidens och medför multipla jämförelser

Detta är därför ett robusthetsdiagnostiskt lager, inte en automatisk modell- eller strategiväljare.
