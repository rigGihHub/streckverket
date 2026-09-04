from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


LAYER_LABELS = {
    "market": "Marknadsodds",
    "team_strength": "Lagstyrka",
    "home_away_form": "Hemma/borta-form",
    "injury_suspension": "Skador/avstängningar",
    "confirmed_lineup": "Bekräftade startelvor",
    "rest_schedule": "Vila/spelschema",
    "weather": "Väder",
    "referee": "Domare",
    "fan_sentiment": "Supporterinformation",
    "other": "Övrig verifierad information",
}

# Ordningen är produktprioritet, inte ett påstående om statistisk modellvikt.
PRIORITY_ORDER = (
    "market",
    "team_strength",
    "home_away_form",
    "injury_suspension",
    "confirmed_lineup",
    "rest_schedule",
    "referee",
    "weather",
    "fan_sentiment",
    "other",
)


@dataclass(frozen=True)
class LayerCoverage:
    key: str
    label: str
    available: int
    missing: int
    total: int

    @property
    def coverage_pct(self) -> int:
        if self.total <= 0:
            return 0
        return int(round(100 * self.available / self.total))


@dataclass(frozen=True)
class SourceCoverage:
    name: str
    ok: bool
    matched: int
    attempted: int
    message: str

    @property
    def coverage_pct(self) -> int | None:
        if self.attempted <= 0:
            return None
        return int(round(100 * self.matched / self.attempted))

    @property
    def status(self) -> str:
        if not self.ok:
            return "Saknas/fel"
        pct = self.coverage_pct
        if pct is None:
            return "OK"
        if pct >= 80:
            return "Bra täckning"
        if pct >= 50:
            return "Delvis täckning"
        return "Låg täckning"


@dataclass(frozen=True)
class ReadinessDiagnostics:
    layers: tuple[LayerCoverage, ...]
    sources: tuple[SourceCoverage, ...]
    priority_key: str | None
    priority_text: str

    @property
    def weakest_layers(self) -> tuple[LayerCoverage, ...]:
        return tuple(sorted(self.layers, key=lambda row: (row.coverage_pct, PRIORITY_ORDER.index(row.key) if row.key in PRIORITY_ORDER else 999)))


def build_readiness_diagnostics(
    cards: Iterable,
    stages: Sequence | None = None,
    *,
    market_missing_count: int = 0,
) -> ReadinessDiagnostics:
    cards = list(cards)
    total = len(cards)
    missing_counts = {key: 0 for key in PRIORITY_ORDER}

    for card in cards:
        for key in set(getattr(card, "missing", ()) or ()):
            if key in missing_counts:
                missing_counts[key] += 1

    # market_available kommer från kupongobjekten och syns inte alltid i MatchCard.missing.
    if market_missing_count:
        missing_counts["market"] = max(missing_counts["market"], min(total, int(market_missing_count)))

    layers = tuple(
        LayerCoverage(
            key=key,
            label=LAYER_LABELS.get(key, key.replace("_", " ")),
            available=max(0, total - missing_counts[key]),
            missing=missing_counts[key],
            total=total,
        )
        for key in PRIORITY_ORDER
    )

    sources = tuple(
        SourceCoverage(
            name=str(getattr(stage, "name", "Okänd källa")),
            ok=bool(getattr(stage, "ok", False)),
            matched=max(0, int(getattr(stage, "matched", 0) or 0)),
            attempted=max(0, int(getattr(stage, "attempted", 0) or 0)),
            message=str(getattr(stage, "message", "") or ""),
        )
        for stage in (stages or ())
    )

    priority_key = None
    for key in PRIORITY_ORDER:
        if missing_counts[key] > 0:
            priority_key = key
            break

    if priority_key is None:
        priority_text = "Ingen tydlig datalucka dominerar den aktuella kupongen. Förbättra inte fler källor utan historiskt stöd."
    else:
        count = missing_counts[priority_key]
        label = LAYER_LABELS[priority_key]
        if priority_key == "market":
            priority_text = f"Prioritera marknadsodds: riktiga odds saknas för {count} av {total} matcher. Utan marknadsankare ska kupongen inte bli spelklar."
        else:
            priority_text = f"Största prioriterade dataluckan är {label.lower()}: saknas för {count} av {total} matcher. Kontrollera först täckningen i den källa som ska leverera detta lager."

    return ReadinessDiagnostics(layers, sources, priority_key, priority_text)


def diagnostics_rows(diag: ReadinessDiagnostics) -> list[dict]:
    return [
        {
            "Informationslager": row.label,
            "Täckning": f"{row.available}/{row.total}",
            "Täckningsgrad": f"{row.coverage_pct}%",
            "Saknas": row.missing,
        }
        for row in diag.layers
    ]


def source_rows(diag: ReadinessDiagnostics) -> list[dict]:
    rows = []
    for source in diag.sources:
        pct = source.coverage_pct
        rows.append({
            "Källa": source.name,
            "Status": source.status,
            "Matchat": f"{source.matched}/{source.attempted}" if source.attempted else "–",
            "Täckningsgrad": f"{pct}%" if pct is not None else "–",
            "Meddelande": source.message,
        })
    return rows
