# Streckverket v3.85 – Guard Allocation Lab

Syftet är att avgöra om samma radbudget återkommande hade kunnat användas bättre genom att flytta halv-/helgarderingar mellan matcher.

Metodskydd:

- endast systemalternativ som faktiskt frystes före match används;
- jämförelsen kräver exakt samma antal rader som originalsystemet;
- facit används aldrig för att välja alternativet;
- äldre kuponger utan samma-rad-alternativ rekonstrueras inte;
- minst 20 prospektivt granskningsbara kuponger krävs före slutsats;
- minst 1 % relativ P(13)-förbättring och återkommande garderingflytt krävs för att flagga allokeringen;
- ingen automatisk ändring av `strategy_engine.py` görs.

Labbet skiljer därmed garderingarnas placering från ren insatsökning. Ett större system får inte vinna analysen bara för att det kostar fler rader.
