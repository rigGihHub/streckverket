# Streckverket v3.51 – Budget Reallocation

## Syfte
v3.51 undersöker om samma radbudget kan användas bättre genom att flytta garderingsutrymme mellan matcher. Funktionen är diagnostisk och ändrar inte prognosmotorn eller den ordinarie optimeraren.

## Hård metodregel
En kandidat får bara visas om totalens radmultiplikator är exakt oförändrad. Funktionen jämför därför exempelvis 2→1 på en match mot 1→2 på en annan, eller 3→2 mot 2→3. Ingen kandidat får gömma en högre insats bakom en förbättrad täckningssiffra.

## Låsningar
Matcher som användaren har låst får varken lämna ifrån sig eller ta emot en gardering i denna diagnostik.

## Ranking
Kandidater rankas efter förbättring i modellens uppskattade fullkupongstäckning, i procentenheter, med samma antal rader. Publikstreck påverkar inte beräkningen.

## Begränsningar
- Ingen uppskattning av framtida utdelning.
- Ingen ROI- eller vinstprognos.
- Ingen rekommendation att öka insatsen.
- Täckningsberäkningen är beroende av modellens sannolikheter och samma oberoendeantagande mellan matcher som den befintliga systemoptimeringen.
- En bättre täckningssiffra är inte bevis för högre faktisk avkastning.

## UI
Text-TV sida 558 `OMFÖRDELA` visar de bästa positiva omfördelningarna, eller säger uttryckligen att ingen bättre omfördelning hittades med exakt samma radantal.
