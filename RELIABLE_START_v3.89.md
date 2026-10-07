# Streckverket v3.89.0 – Reliable Start

Startadress: https://streckverket.streamlit.app/

## Ändringar

Första analysen och senare uppdateringar går att starta direkt från normalvyn. Datastatus och tidpunkt ligger kvar hopfällda. Startsidan beskriver den faktiska ordningen: hämta kupong, välj budget, analysera.

Hämtning och analys visar en spinner. CSV-import finns även på startsidan, kräver ett separat öppningsklick och fångar tomma, felkodade eller ofullständiga filer utan att ersätta en giltig kupong. Detta tar bort den gamla oändliga omladdningen vid kvarliggande uppladdning.

Misslyckad hämtning av en riktig kupong från testläget stoppar analysen innan den körs. Testdata får därmed inte byta källa till Multi-source eller sparas som verklig historik.

`model_engine.py` och `strategy_engine.py` är oförändrade. Releasen är registrerad som icke-prediktiv.

## Publicering

Den befintliga webbappen behöver uppdateras med denna kod innan ändringarna syns på startadressen. Ingen publicering kan fastställas enbart genom att ZIP-filen finns. Senaste tidigare instruktion var att inte göra Commit/Push ännu; releasen förbereds för granskning utan push.

## Verifiering

- 616 tester passerar, inklusive åtta nya AppTest-fall för start, hämtfel, CSV-fel, omladdning och testdata.
- Samtliga Python-filer syntaxkontrollerade.
- Prognos- och strategifilernas SHA-256 är oförändrade mot v3.88.0.
- Den befintliga liveappen väcktes från viloläge 2026-10-05, men fastnade på laddningsskärmen i kontrollen. Ingen lyckad start eller ny publicering har bekräftats.
