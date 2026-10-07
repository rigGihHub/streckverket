# Streckverket v3.87 – System Decision Attribution

v3.87 sammanför v3.83 System P(13) Audit, v3.84 Spike Failure Lab, v3.85 Guard Allocation Lab och v3.86 Counterfactual 13-Rätt Optimizer Audit till en hierarkisk beslutsdiagnostik.

## Metodskydd

- P(13)-effekter från v3.83, v3.85 och v3.86 summeras aldrig eftersom labben överlappar.
- v3.83 används som bred kontext, v3.85 isolerar garderingflyttar och v3.86 är benchmark för hela samma-rad-strukturen.
- Spiklabbet ligger på en separat evidensaxel. Kalibreringsgap/Brier score är inte direkt jämförbara med P(13)-headroom.
- Endast prospektivt frysta systemalternativ används i de underliggande auditerna.
- Facit används inte för att välja counterfactual-system.
- Ingen strategi-, spik- eller modellregel ändras automatiskt.

## Beslutslogik

När underlaget är moget kan attributionen rekommendera nästa **experimentområde**, exempelvis garderingallokering, bredare systemstruktur, systemets spikval eller sannolikhetskalibrering. Rekommendationen är en hypotes för ett separat prospektivt experiment – inte en produktionsändring och inte ett påstående om bevisad edge.
