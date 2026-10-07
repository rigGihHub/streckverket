# Streckverket v3.43 – Product Reality Check

## Kärnfrågan
Blir Streckverket bättre på att hjälpa användaren bygga ett bättre Stryktipssystem för sin budget?

## Viktigaste fyndet
Den största kvarvarande produktluckan är inte fler signaler. Det är att bevisa att modellens avvikelser från bookmakerbasen faktiskt tillför värde över tid.

v3.42 kunde nå 100 verifierade matcher från bara åtta kuponger och därefter använda etiketten LOVANDE EDGE. Det är för aggressivt eftersom matcher inom samma kupong inte bör behandlas som 13 helt oberoende experiment.

## Åtgärdat i v3.43
- Benchmark kräver minst 100 verifierade matcher OCH minst 20 separata kuponger innan ett positivt mönster får lyftas.
- Positiv etikett heter LOVANDE MÖNSTER, inte LOVANDE EDGE.
- Positivt mönster kräver även positiv Brier-utveckling i den nyare delen av historiken.
- Facit-snapshots versionsmärks från v3.43 så framtida modellgenerationer kan skiljas åt.
- Äldre snapshots utan versionsmetadata förblir okända; ingen bakåtgissning.
- Ny Produktens verklighetskontroll visar matcher, separata kuponger, högre datakvalitet och versionsproveniens.

## Fortsatt verklighetsbild
1. Ingen bevisad prediktiv edge.
2. Historiken är den viktigaste tillgången och behöver växa över många separata kuponger.
3. Modellversion måste följas framåt för rättvis jämförelse.
4. Hög observationskvalitet och nära-avspark-data bör granskas separat.
5. Poolvärdesdelen använder fortfarande proxyer och ska inte beskrivas som exakt förväntad utdelning.
6. API-täckning kan variera mellan ligor och måste fortsätta mätas.
7. Streamlit AppTest kan ännu inte köras i denna byggmiljö eftersom Streamlit saknas här.

## Prioritet efter v3.43
Samla bättre historik före nya modellfaktorer. Nästa modellförändring bör kunna utvärderas mot en tydligt versionsmärkt före/efter-period och bookmakerbasen.
