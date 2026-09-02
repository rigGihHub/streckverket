from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse
import json
import re


SOURCE_TYPES = (
    "official_club",
    "official_league",
    "local_media",
    "national_media",
    "data_provider",
    "supporter_forum",
    "journalist",
)

DEFAULT_RELIABILITY = {
    "official_club": 0.98,
    "official_league": 0.97,
    "data_provider": 0.84,
    "local_media": 0.76,
    "national_media": 0.72,
    "journalist": 0.66,
    "supporter_forum": 0.35,
}


def normalize_domain(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = "https://" + value
    host = urlparse(value).netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def derive_origin_group(url: str, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit.strip().lower()
    domain = normalize_domain(url)
    if not domain:
        return "unknown"
    # Common subdomains on the same publisher are not independent evidence.
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


@dataclass(frozen=True)
class TeamSource:
    team_key: str
    name: str
    url: str
    source_type: str
    origin_group: str = ""
    reliability: float = 0.0
    enabled: bool = True
    notes: str = ""

    def __post_init__(self):
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"Okänd source_type: {self.source_type}")
        reliability = self.reliability or DEFAULT_RELIABILITY[self.source_type]
        object.__setattr__(self, "reliability", max(0.0, min(1.0, float(reliability))))
        object.__setattr__(self, "origin_group", derive_origin_group(self.url, self.origin_group))

    @property
    def domain(self) -> str:
        return normalize_domain(self.url)


@dataclass
class TeamRegistry:
    team_key: str
    display_name: str
    country: str = ""
    external_team_ids: dict[str, str] = field(default_factory=dict)
    venue: str = ""
    sources: list[TeamSource] = field(default_factory=list)

    def add_source(self, source: TeamSource) -> None:
        if source.team_key != self.team_key:
            raise ValueError("Källan tillhör ett annat lag")
        existing = {(x.source_type, x.domain, x.name.lower()) for x in self.sources}
        key = (source.source_type, source.domain, source.name.lower())
        if key not in existing:
            self.sources.append(source)

    def enabled_sources(self) -> list[TeamSource]:
        return [x for x in self.sources if x.enabled]


def seed_from_football_data(team_payload: dict) -> TeamRegistry:
    team_id = str(team_payload.get("id") or "")
    name = str(team_payload.get("name") or team_payload.get("shortName") or "").strip()
    area = team_payload.get("area") or {}
    country = str(area.get("name") or "")
    venue = str(team_payload.get("venue") or "")
    key = f"football_data:{team_id}" if team_id else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    registry = TeamRegistry(
        team_key=key,
        display_name=name,
        country=country,
        venue=venue,
        external_team_ids={"football_data": team_id} if team_id else {},
    )
    website = str(team_payload.get("website") or "").strip()
    if website:
        registry.add_source(TeamSource(
            team_key=key,
            name=f"{name} official",
            url=website,
            source_type="official_club",
            notes="Seeded from football-data.org team resource",
        ))
    return registry


def save_registries(path: str | Path, registries: Iterable[TeamRegistry]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for registry in registries:
        item = {
            "team_key": registry.team_key,
            "display_name": registry.display_name,
            "country": registry.country,
            "external_team_ids": registry.external_team_ids,
            "venue": registry.venue,
            "sources": [asdict(s) for s in registry.sources],
        }
        payload.append(item)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_registries(path: str | Path) -> list[TeamRegistry]:
    p = Path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    out: list[TeamRegistry] = []
    for item in raw:
        reg = TeamRegistry(
            team_key=item["team_key"],
            display_name=item["display_name"],
            country=item.get("country", ""),
            external_team_ids=item.get("external_team_ids", {}),
            venue=item.get("venue", ""),
        )
        for source in item.get("sources", []):
            reg.add_source(TeamSource(**source))
        out.append(reg)
    return out


def registry_quality(registry: TeamRegistry) -> dict:
    sources = registry.enabled_sources()
    types = {s.source_type for s in sources}
    origins = {s.origin_group for s in sources if s.origin_group != "unknown"}
    has_official = bool(types & {"official_club", "official_league"})
    has_media = bool(types & {"local_media", "national_media", "journalist"})
    has_fan = "supporter_forum" in types
    score = 0
    score += 35 if has_official else 0
    score += 25 if has_media else 0
    score += 10 if has_fan else 0
    score += min(20, 5 * len(origins))
    score += 10 if "data_provider" in types else 0
    score = min(100, score)
    label = "Stark" if score >= 75 else "Användbar" if score >= 50 else "Ofullständig"
    return {
        "score": score,
        "label": label,
        "source_count": len(sources),
        "independent_origins": len(origins),
        "has_official": has_official,
        "has_media": has_media,
        "has_fan": has_fan,
    }
