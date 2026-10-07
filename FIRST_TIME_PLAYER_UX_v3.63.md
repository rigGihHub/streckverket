# Streckverket v3.63.0 – First-Time Player UX

Mål: en oerfaren Stryktipsare ska kunna gå från budget till ett begripligt systemförslag utan att behöva förstå Streckverkets analysmotor.

## Normalvyn

- `Streckverkets rekommendation` är förvalt och mappar till befintlig VÄRDE-strategi.
- `Försiktigare` mappar till befintlig MAX 13-strategi.
- Ingen tredje låtsasstrategi införs: motorn har i nuläget inte en separat, verifierad "mer chansartad" optimerare.
- Tre korta skäl sammanfattar befintliga spik/garderings/fäll-beslut.
- Alla 13 matcher visas i en enkel expander med endast match och tecken.
- Primär handling heter `ANVÄND DETTA SYSTEM`.
- API-, bookmaker- och övrig teknisk diagnostik flyttas bakom `Fördjupad analys`.
- Automatisk late-market-insamling sker tyst i normalvyn.

## Metod

Ingen predictive logic ändras. `model_engine.py` och `strategy_engine.py` ska vara byte-identiska med v3.62.0.
