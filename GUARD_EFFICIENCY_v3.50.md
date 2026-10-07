# Guarderingseffektivitet v3.50

## Syfte
Visa var exakt ett extra garderingstecken ger störst lokal ökning av modellens uppskattade fullkupongstäckning per extra rad.

## Beräkning
För varje match som inte redan är helgarderad läggs ett av de utelämnade tecknen till, ett i taget. Övriga matchval hålls oförändrade. Ny radmängd följer systemets multiplikativa struktur (1→2 dubblerar raderna, 2→3 ökar dem med 50 procent). Fullkupongstäckningen räknas om med samma oberoendeantagande som `optimize_system`.

## Vad måttet inte säger
- Det uppskattar inte framtida utdelning.
- Det uppskattar inte förväntad vinst eller ROI.
- Det bevisar inte edge.
- Det säger inte att användaren bör höja sin insats.
- Det ersätter inte den globala systemoptimeraren.

## Produktprincip
Radnytta är ett diagnostiskt jämförelsemått. Ordinarie system för vald budget förblir källan till vad användaren faktiskt ska spela.
