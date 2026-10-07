# v3.84 – Spike Failure Lab

## Syfte

Skilja systematisk svaghet i spikbeslut från normal slump i enskilda favoritförluster.

Labbet använder endast spikar och sannolikheter som sparades prospektivt före match. Det rekonstruerar inte gamla spikbeslut och använder aldrig facit för att välja vilka matcher som borde ha spikats.

## Diagnostik

För varje fryst spik mäts:

- vilket tecken som faktiskt spikades,
- Streckverkets frysta sannolikhet för exakt detta tecken,
- faktiskt utfall,
- bookmakerankarets sannolikhet för samma tecken när verifierad marknad finns,
- om systemets spik var modellens eget förstaval.

Spikar grupperas i fasta sannolikhetsintervall från `<50 %` till `80 %+`. Ett intervall kräver minst 20 spikar över minst 5 kuponger innan det får klassas som moget. Ett moget intervall med minst 5 procentenheters negativt kalibreringsgap markeras som överkonfidens att granska.

Övergripande slutsats kräver minst 100 spikar över 20 olika kuponger.

## Viktiga metodskydd

- En enskild spikmiss innebär inte att spiken var dålig.
- Ingen regel som "spika aldrig under X %" skapas automatiskt.
- Ingen modellvikt ändras.
- `model_engine.py` och `strategy_engine.py` ändras inte.
- Bookmakerjämförelsen görs på exakt samma spiktecken och matcher.
- Facit används endast för efterföljande utvärdering av redan frysta beslut.
