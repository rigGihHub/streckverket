# Streckverket v3.65.0 – Single-Screen Novice Flow

## Syfte
Normalanvändaren ska inte navigera mellan flera vyer för att få samma svar flera gånger.

## Ändringar
- Normalvyn är ett sammanhängande flöde: hämta kupong → budget → systemförslag → kort varför.
- De tidigare normalflikarna `Mitt system`, `Spikar`, `Fällor & skrällar` och `Varför?` renderas inte för nybörjaren.
- Expertläge behåller samtliga detaljerade kärnflikar och expertverktyg.
- Den gamla tabbaserade beslutsytan körs inte parallellt med normalvyn, vilket tar bort dubbel budget/strategi/systempresentation.
- Automatisk verifierad pre-kickoff-marknadsinsamling flyttas ut ur beslutsfliken och körs passivt i normalflödet.
- Passive capture får aldrig blockera huvudflödet om historiklagring inte är tillgänglig.

## Metod
Ingen prognos-, strategi- eller optimeringslogik ändras. `predictive_change=False`.

## Avsikt
Mindre UI-brus, färre onödiga komponenter att rendera och kortare väg till svaret på frågan: Vad ska jag spela?
