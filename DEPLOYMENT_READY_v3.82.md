# Streckverket v3.82 – Deployment Ready

## Mål

Göra Streckverket enkelt att starta lokalt och förbereda samma kodbas för en riktig webbdeploy utan att ändra prognos- eller strategimotorn.

## Lokal start på Windows

1. Packa upp ZIP-filen.
2. Dubbelklicka på `STARTA_STRECKVERKET.bat`.
3. Första gången skapas `.venv` och beroenden installeras automatiskt.
4. Därefter startas Streamlit och appen öppnas i standardwebbläsaren.

Python 3.11+ måste finnas på datorn. Användaren behöver inte öppna PowerShell eller skriva kommandon.

## Webbdeploy

Projektet innehåller nu:

- `Dockerfile` – reproducerbar Python/Streamlit-runtime.
- `render.yaml` – Render Blueprint för webbtjänsten.
- `.streamlit/config.toml` – serverkonfiguration för headless drift.
- `.dockerignore` och `.gitignore` – hindrar lokala databaser, secrets, cache och venv från att följa med.

Docker startar appen på plattformens `PORT` och använder Streamlits `/_stcore/health` som health check.

## Beständig historik är ett separat krav

Streckverket fungerar lokalt med SQLite. På en server med ephemeral filsystem får den lokala SQLite-filen däremot inte betraktas som beständig prospektiv historik.

För riktig drift ska `STRECKVERKET_DATABASE_URL` sättas till en beständig PostgreSQL-databas, exempelvis Neon/PostgreSQL som redan stöds av `history_store.py`.

Saknas variabeln startar appen fortfarande, men deploy/restart kan radera serverns lokala SQLite-historik.

## Versionsvisning

Den tidigare hårdkodade `v3.75.0`-texten i `app.py` är borttagen. Appen visar nu `APP_VERSION` och `RELEASE_NAME` från `release_info.py`, vilket minskar risken för gammal versionsinformation i gränssnittet.

## Prediktiv påverkan

Ingen. `model_engine.py` och `strategy_engine.py` ändras inte i v3.82.
