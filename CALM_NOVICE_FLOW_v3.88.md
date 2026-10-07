# Streckverket v3.88.0 – Calm Novice Flow

## Syfte

Förenkla normalflödet efter faktisk användartestning utan att ändra prognos- eller strategimotor.

## Ändringar

- Demo är nu en landningssida och visas inte som ett spelklart 128-kronorssystem som standard.
- Primär handling när ingen riktig kupong är öppen: **HÄMTA AKTUELL STRYKTIPSKUPONG**.
- Testkupongen finns kvar bakom ett sekundärt val och märks tydligt som testdata.
- Normal sidopanel visar inte längre en permanent trestegsinstruktion.
- Budget/spelsätt visas först när en riktig eller importerad kupong är öppen.
- Systemets huvudbesked komprimeras till en tydlig sammanfattning: kostnad, spikar, halv-/helgarderingar och status.
- Timing, datakvalitet och uppdateringskontroller ligger hopfällda under **Analysstatus & uppdatering**.
- Expertläget behåller full datakälla-, kupong- och strategiåtkomst.

## Metodskydd

`model_engine.py` och `strategy_engine.py` ändras inte. Releasen är UX-only och registreras som icke-prediktiv.
