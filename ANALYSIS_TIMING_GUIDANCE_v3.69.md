# v3.69.0 – Analysis Timing Guidance

## Syfte
Göra två saker som en ny spelare behöver förstå direkt: **kan jag spela nu?** och **när bör jag kontrollera kupongen igen?**

## Förändringar
- Kopplar v3.68:s `readiness_guidance` till den faktiska normalvyn. Den gamla REDO/VÄNTA-raden ersätts av konkreta besked och ett tydligt nästa steg.
- Datakvalitet 0–100 finns kvar bakom en expander och förklaras uttryckligen som underlagskvalitet, inte vinstchans.
- Ny `analysis_timing.py` ger ett konservativt tidsråd utifrån **tidigaste kända avspark**.
- Rådet skiljer mellan tidig koll, första analys, slutlig kontroll som närmar sig och sista timmen.
- Om avspark saknas hittar appen inte på ett klockslag.
- Tidigaste avspark kallas aldrig officiellt spelstopp; UI:t säger uttryckligen att spelstoppet inte är verifierat av denna funktion.
- Ingen prognos- eller systemmatematik ändras.
