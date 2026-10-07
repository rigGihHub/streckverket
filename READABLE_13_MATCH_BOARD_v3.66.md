# Streckverket v3.66.0 – Readable 13-Match System Board

## Syfte
Normalanvändaren ska kunna se exakt vilka 1/X/2-tecken som ska kryssas utan att först tolka en dataframe/tabell.

## Ändringar
- Ny `novice_system_board.py`.
- Normalvyn visar 13 matchrader med separata 1/X/2-rutor.
- Valda tecken markeras tydligt.
- Varje match får etiketten `SPIK`, `HALV` eller `HEL`.
- Kort legend förklarar etiketterna.
- Mobil layout komprimeras utan horisontell sidscroll.
- Teamnamn HTML-escapas innan rendering.
- Expertvyns analyser och tabeller ändras inte.
- Ingen förändring av prognos- eller strategilogik (`predictive_change=False`).

## Metodgräns
Detta är en presentationsrelease. Samma `system["selections"]` renderas som tidigare; inga tecken läggs till, tas bort eller rangordnas av den nya vyn.
