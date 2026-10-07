# Streckverket v3.74 – 13-Rätt Performance Lab

## Syfte

Från och med v3.74 är huvudfrågan inte fler UI-finesser utan vad som faktiskt hindrar systemet från att täcka alla 13 matchutfall.

Labbet använder endast kuponger som sparats före matcherna och senare fått komplett facit. Ingen historisk kupong rekonstrueras i efterhand.

## Diagnoser

För varje komplett kupong mäts bland annat:

- antal matchutfall som systemet täckte,
- om 13 rätt fanns bland systemets rader,
- spikmissar,
- halvgarderingsmissar,
- modellens förstaval rätt/fel,
- marknadens förstaval rätt/fel när verifierad bookmakerbas finns,
- fall där modellens förstaval var det verkliga utfallet men systemet ändå valde bort utfallet,
- fryst modellberäknad systemtäckning jämfört med faktiskt antal kuponger där 13 täcktes.

Den sista systemmisskategorin är särskilt viktig: den pekar på system-/budgetallokering snarare än på att modellens förstaval var fel.

## Review gate

Minst 20 kompletta prospektiva kuponger krävs innan labbet får prioritera en motor för granskning. Före denna gräns visar appen missmönster men rekommenderar att mer historik samlas.

Möjliga prioriteringar efter review gate är:

- granska system-/budgetallokering,
- granska spikdisciplin,
- granska prognosjusteringar,
- fortsätt prospektiv validering.

## Metodgränser

- Labbet ändrar aldrig modell- eller strategivikter automatiskt.
- Det påstår inte edge, ROI eller framtida 13-rätt-frekvens.
- Summan av fryst modellberäknad systemtäckning används endast som kalibreringsdiagnostik under modellens antaganden.
- Resultat får inte användas för att backfylla vad modellen eller systemet "borde" ha valt före match.
