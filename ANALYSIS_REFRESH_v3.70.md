# Streckverket v3.70.0 – Uppdatera analysen nu

## Syfte
Normalvyn får en enda tydlig knapp för att köra om analysen med de datakällor som faktiskt är konfigurerade. Funktionen är ett UX- och datainsamlingssteg, inte en ny prognosmodell.

## Beteende
- `Uppdatera analysen nu` kör samma one-click-analys som befintliga analysflöden.
- I demo heter knappen `Hämta riktig kupong och analysera` och försöker först öppna aktuell Stryktipskupong.
- För en redan öppnad kupong används ny Svenska Spel-grunddata endast om exakt samma 13 numrerade matcher verifieras. Annars behålls den öppna kupongen.
- Externa nycklar läses från konfigurerade secrets; användaren behöver inte se eller skriva API-nycklar i normalvyn.
- En uttrycklig uppdatering invaliderar endast kortlivade cachelager för odds, fixtures, skador och startelvor. Stabil tävlings-/lagmetadata kan fortsatt cachelagras.
- Verifierade fakta och datakvalitetssnapshot sparas på samma sätt som vid övrig riktig one-click-analys.

## Metodgräns
Knappen garanterar inte att en extern källa har ny information eller att analysen blir bättre. Den betyder att Streckverket gör en ny verifieringsrunda med tillgängliga källor. Om en källa saknas eller inte svarar ska readiness fortsatt visa detta öppet.

## Modellpåverkan
Ingen. `model_engine.py` och `strategy_engine.py` ändras inte.

## Korrigerad tidsproveniens i marknadsinsamlingen
Under regressionstestningen hittades ett äldre fel där `capture_eligible` använde väggklockan även när en explicit `captured_at` fanns. Det gjorde historiska pre-kickoff-observationer tidsberoende. v3.70 bedömer nu kickoff-behörighet mot observationens egen tidpunkt.
