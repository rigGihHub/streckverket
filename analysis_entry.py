"""Small helpers for the primary analysis entry point.

Keeps credential/status logic separate from Streamlit rendering so it can be
tested without exposing secrets in the interface.
"""
from __future__ import annotations

SOURCE_SECRET_KEYS = {
    "odds": "THE_ODDS_API_KEY",
    "football_data": "FOOTBALL_DATA_API_KEY",
    "api_football": "API_FOOTBALL_KEY",
}


def source_availability(secrets: dict | None) -> dict[str, bool]:
    secrets = secrets or {}
    return {name: bool(str(secrets.get(key, "")).strip()) for name, key in SOURCE_SECRET_KEYS.items()}


def source_status_text(availability: dict[str, bool]) -> str:
    count = sum(bool(v) for v in availability.values())
    if count == 3:
        return "Alla tre externa datakällor är konfigurerade."
    if count == 0:
        return "Inga externa API-nycklar är konfigurerade; analysen kan bara använda kupongens grunddata."
    missing = [name for name, ok in availability.items() if not ok]
    labels = {"odds": "bookmakerodds", "football_data": "lag/form", "api_football": "skador/startelvor"}
    return "Delvis konfigurerat. Saknar: " + ", ".join(labels.get(x, x) for x in missing) + "."
