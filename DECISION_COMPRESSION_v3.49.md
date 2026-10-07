# Streckverket v3.49 – Decision Compression

## Produktfrågan
Normalvyn hade blivit informationsrik men krävde för mycket scrollning innan användaren såg det viktigaste. v3.49 gör därför ingen ny fotbollsmodell. Den minskar i stället beslutstiden.

## Sida 100 – beslut först
Sida 100 sammanfattar samma optimerade system i fyra typer av information:

1. systemets rader och pris,
2. antal spikar/garderingar/helgarderingar,
3. readiness/datastatus,
4. högst fyra nyckelåtgärder som redan finns i systemet eller den befintliga beslutsanalysen.

Snabbvyn får inte skapa ett parallellt tips. En spik måste vara en faktisk singelselektion i systemet. En gardering måste redan finnas i systemet. Ett skrälltecken visas inte om systemet har valt bort tecknet.

## Normalvyn
Fördjupade analyser är nu opt-in via `Visa fördjupning och fler analyser`. Standardläget prioriterar:

- Vad spelar jag?
- Vad kostar det?
- Var spikar/garderar jag?
- Kan jag spela nu?

## Modellpåverkan
Ingen. `model_engine.py` och `strategy_engine.py` är oförändrade. Releaseposten är uttryckligen `predictive_change=False`.
