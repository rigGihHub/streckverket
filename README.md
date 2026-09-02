# Streckverket v2.1.0

## Claim Resolution + Information Edge + Retro Edition

- Löser tidigare claims mot facit och matar Source Performance.
- Mäter minuter före marknadens respektive streckens reaktion.
- Endast korrekta claims räknas som positiv information edge.
- Ny retrokupong-design: mörkgrön/svart bakgrund, benvita kupongkort, gul accent, nummerbrickor 1–13, tydligare KPI-rutor och mobilvänligare knappar.

### Test
```powershell
$env:PYTHONPATH="."
pytest -q
```

### Start
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

### Nästa steg
Persistenta claims, faktisk reaktionsdetektion från snapshots och fortsatt UI-förbättring av matchkort/systembyggare.


## v2.1.0 – Retro Tipcentral
- Ny startsideshierarki med SPIK / FÄLLA / SKRÄLL direkt överst.
- Ny kompakt 13-matchers tipstavla där valda 1/X/2 markeras som på en klassisk kupong.
- Responsiv mobilversion av tipstavlan.
- Strategietikett per match direkt i kupongöversikten.
- Retrodesignen används nu för beslutsstöd, inte bara som dekor.

## v2.1.0 – Streckverket
Projektet har fått sitt permanenta namn: **Streckverket**.

Varumärkesprofil:
- STRECK / VERKET som tvådelat retrologotyp-ordmärke
- payoff: **Vi jagar inte favoriter. Vi jagar felstreck.**
- fyra principer i startsidan: Marknad som bas, Streck som motståndare, Data före magkänsla, 13 rätt som mål
- fil/release-prefix är nu `streckverket`

## v2.1.0 – Kupongverkstad
- Interaktiv överstyrning av 1/X/2 per match.
- Radantal och kostnad räknas om direkt.
- Modellens uppskattade 13-rättstäckning räknas om direkt.
- Alla möjliga nästa garderingar testas.
- Förslagen rangordnas efter marginalnytta per extra krona.
- Topp 10 nästa tecken visas med kostnads- och täckningseffekt.

## v2.1.0 – Budgetverkstaden
- Valfri maxbudget, inte bara fasta budgetsteg.
- Global systemoptimering under budgettaket.
- MAX 13 eller VÄRDE-strategi.
- Egna låsningar respekteras.
- Budgetkurva visar faktisk kostnad, rader, modelltäckning och marginalnytta.
- Jämför automatiskt lägre och högre budgetnivåer.
- Visar vad du sparar/tappar respektive betalar/vinner i modelltäckning.
- Ett klick flyttar det optimerade budgetsystemet till Kupongverkstaden.

## v2.1.0 – Så spelar Streckverket idag
- Ny första flik med ren beslutsvy.
- Väljer budget och strategi direkt.
- Sammanfattar bästa spikar, måstegarderingar, fällor och skrällar.
- Visar komplett rekommenderat system.
- Systemet kan skickas direkt till Kupongverkstaden.
- Bygger på samma budgetmotor och klassificering som övriga appen.
