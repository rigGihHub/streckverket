# Streckverket v3.62 – Automatic Late-Market Capture

## Syfte

v3.61 byggde en prospektiv benchmark men var beroende av att användaren manuellt sparade flera marknadspunkter. v3.62 flyttar denna datainsamling till normalflödet.

## Regler

- endast verklig kupong, aldrig Demo
- exakt 13 matcher
- minst en verifierad bookmakerbas
- ingen capture efter att en känd match startat
- oförändrade punkter inom fem minuter dedupliceras av befintlig HistoryStore
- verkligt ändrade priser bevaras även inom fem minuter
- ingen automatisk modellvikt, strategiändring, ROI- eller edge-claim
- sena observationer kallas inte closing line

## UX

Användaren behöver inte öppna Facit & lärande eller trycka på Spara marknadspunkt. Normalvyn sparar underlaget passivt när en verifierad bookmakerbild finns. Endast när något faktiskt sparas visas en diskret statusrad.
