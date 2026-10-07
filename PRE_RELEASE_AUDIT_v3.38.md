# Streckverket v3.38 – Pre-Release Audit

## Kritiska fynd och beslut

1. **Dolda flikar exekverades fortfarande.** Streamlit skapade alla 19 tabbar och CSS dolde bara knapparna. Detta kunde ge onödig renderingskostnad och låta fel i dolda specialistblock påverka normalläget. **Åtgärdat i v3.38** med exekveringsspärr per flik.
2. **`app.py` är fortfarande för stor (ca 2 400 rader).** Det ökar regressionsrisk och gör UI-flöden svåra att isolera. **Inte refaktorerat i v3.38** för att undvika ett stort samtidighetsingrepp.
3. **Datagranskning består av flera separata kodblock i samma tab.** Funktionellt okej men underhållsmässigt svagt. Bör samlas i en renderer när app.py delas upp.
4. **Många breda `except Exception` finns i UI-lagret.** Vissa behövs för valfria datakällor, men vissa riskerar att dölja programmeringsfel. Bör ersättas selektivt med typade fel och loggning.
5. **Produktlogiken har blivit betydligt mer avancerad än normal-UX.** Detta är acceptabelt så länge specialistverktyg verkligen är dolda och inte exekveras i normalläge. v3.38 förbättrar den gränsen.
6. **Ingen bevisad prediktiv edge finns.** Audit ändrar inte detta och inga modellvikter ändras.

## Rekommenderad nästa release

**v3.39 – App Shell Refactor + Error Boundary Hardening**

Flytta stora tab-renderers ur `app.py` i små, testbara UI-moduler och ersätt de mest riskabla breda exception handlers med tydligare felgränser. Prognos- och strategimotor ska lämnas orörda.
