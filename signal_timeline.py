from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable, Sequence


@dataclass(frozen=True)
class SignalPoint:
    coupon_key: str
    match_number: int
    home: str
    away: str
    captured_at: str
    signal_type: str
    subject: str
    source: str
    verification_status: str
    upstream_origin: str
    model_usable: bool
    payload: dict
    observed_at: str | None = None
    verified_at: str | None = None

    @property
    def identity(self) -> str:
        raw = json.dumps({
            'coupon_key': self.coupon_key,
            'match_number': self.match_number,
            'captured_at': self.captured_at,
            'signal_type': self.signal_type,
            'subject': self.subject.strip().casefold(),
            'source': self.source.strip().casefold(),
            'upstream_origin': self.upstream_origin.strip().casefold(),
            'payload': self.payload,
            'observed_at': self.observed_at,
            'verified_at': self.verified_at,
        }, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]


def supporter_history_to_signal_points(history: Iterable[dict], *, coupon_key: str, matches: Sequence[object]) -> list[SignalPoint]:
    """Project stored Supporter Pulse observations onto the common signal timeline.

    This is a migration/projection layer. It preserves the observation as descriptive and
    explicitly non-model-usable; historical validation must happen elsewhere first.
    """
    by_match = {int(getattr(m, 'number')): m for m in matches}
    out: list[SignalPoint] = []
    for row in history:
        n = int(row.get('match_number', 0) or 0)
        match = by_match.get(n)
        if match is None:
            continue
        if str(row.get('home', '')).strip().casefold() != str(getattr(match, 'home')).strip().casefold():
            continue
        if str(row.get('away', '')).strip().casefold() != str(getattr(match, 'away')).strip().casefold():
            continue
        captured = str(row.get('captured_at', '') or '')
        if not captured:
            continue
        payload = {
            'team': str(row.get('team', '') or ''),
            'confidence': float(row.get('confidence', 0) or 0),
            'resignation': float(row.get('resignation', 0) or 0),
            'worry': float(row.get('worry', 0) or 0),
            'optimism': float(row.get('optimism', 0) or 0),
            'anger': float(row.get('anger', 0) or 0),
            'consensus': float(row.get('consensus', 0) or 0),
            'tone_delta': row.get('tone_delta'),
            'sample_quality': float(row.get('sample_quality', 0) or 0),
            'independent_origins': int(row.get('independent_origins', 0) or 0),
            'independence_rate': float(row.get('independence_rate', 0) or 0),
        }
        source = str(row.get('source', '') or 'Supporterforum')
        out.append(SignalPoint(
            coupon_key=coupon_key,
            match_number=n,
            home=str(getattr(match, 'home')),
            away=str(getattr(match, 'away')),
            captured_at=captured,
            signal_type='supporter_pulse',
            subject=str(row.get('team', '') or ''),
            source=source,
            verification_status='observerad_ton',
            upstream_origin=source,
            model_usable=False,
            payload=payload,
            observed_at=captured,
            verified_at=None,
        ))
    return out



def verified_facts_from_cards(cards: Sequence[object], *, coupon_key: str, captured_at: str, matches: Sequence[object] | None = None) -> list[SignalPoint]:
    """Project only traceable pre-match facts from intelligence cards onto the common timeline.

    `observed_at` means when Streckverket processed the source response. `verified_at` means when
    the application accepted the observation at its stated verification level. Neither field is
    silently substituted with a source publication time.
    """
    out: list[SignalPoint] = []
    competition_by_match = {int(getattr(m, 'number')): str(getattr(m, 'competition', '') or 'Okänd liga') for m in (matches or ())}
    for card in cards:
        n = int(getattr(card, 'match_number'))
        home = str(getattr(card, 'home'))
        away = str(getattr(card, 'away'))
        used_signals = list(getattr(card, 'used_signals', ()) or ())
        model_categories = {str(getattr(sig, 'category', '')) for sig in used_signals if bool(getattr(sig, 'is_verified', False))}

        # Verified evidence signals may already affect the model. Preserve that audit fact separately
        # from the provider observations that explain who/what was reported.
        for sig in used_signals:
            category = str(getattr(sig, 'category', '') or '')
            if category not in {'injury_suspension', 'confirmed_lineup'} or not bool(getattr(sig, 'is_verified', False)):
                continue
            observed = str(getattr(sig, 'updated_at', '') or captured_at)
            source = str(getattr(sig, 'source', '') or 'Källa saknas')
            label = str(getattr(sig, 'label', '') or category)
            out.append(SignalPoint(
                coupon_key=coupon_key, match_number=n, home=home, away=away,
                captured_at=observed, signal_type='verified_fact', subject=label,
                source=source, verification_status='VERIFIERAD MODELLSIGNAL', upstream_origin=source,
                model_usable=True,
                payload={
                    'category': category, 'label': label,
                    'explanation': str(getattr(sig, 'explanation', '') or ''),
                    'reliability': float(getattr(sig, 'reliability', 0.0) or 0.0),
                    # Preserve the verified model signal's own directional vector. This is audit
                    # provenance, not a new weight: v3.34 may compare its stated direction with
                    # later market movement without guessing direction from the category label.
                    'impact_1x2': [float(x) for x in (getattr(sig, 'impact', ()) or ())],
                    'effective_strength': float(getattr(sig, 'effective_strength', 0.0) or 0.0),
                    'direction_basis': 'verified_evidence_signal_impact',
                    'verification_basis': 'evidence_signal_is_verified',
                    'competition': competition_by_match.get(n, 'Okänd liga'),
                }, observed_at=observed, verified_at=captured_at,
            ))

        # Direct provider observations are useful provenance even when consensus/model rules do not
        # let them move probabilities. Keep the verification level explicit instead of upgrading them.
        for claim in list(getattr(card, 'claims', ()) or ()):
            category = str(getattr(claim, 'category', '') or '')
            if category not in {'injury_suspension', 'confirmed_lineup'}:
                continue
            for obs in list(getattr(claim, 'observations', ()) or ()):
                if not bool(getattr(obs, 'direct', False)):
                    continue
                source_obj = getattr(obs, 'source', None)
                source = str(getattr(source_obj, 'name', '') or 'Källa saknas')
                observed = str(getattr(obs, 'updated_at', '') or captured_at)
                value = str(getattr(obs, 'value', '') or '')
                status = 'LEVERANTÖRSBEKRÄFTAD' if category == 'confirmed_lineup' and value.casefold() == 'confirmed' else 'DIREKT LEVERANTÖRSUPPGIFT'
                subject = 'Bekräftad startelva' if category == 'confirmed_lineup' else 'Spelarfrånvaro'
                out.append(SignalPoint(
                    coupon_key=coupon_key, match_number=n, home=home, away=away,
                    captured_at=observed, signal_type='verified_fact', subject=subject,
                    source=source, verification_status=status,
                    upstream_origin=str(getattr(source_obj, 'independence_group', '') or source),
                    model_usable=category in model_categories,
                    payload={
                        'category': category, 'provider_value': value,
                        'confidence': float(getattr(obs, 'confidence', 0.0) or 0.0),
                        'direct': True,
                        'source_official': bool(getattr(source_obj, 'official', False)),
                        'verification_basis': 'direct_provider_observation',
                        'competition': competition_by_match.get(n, 'Okänd liga'),
                    }, observed_at=observed, verified_at=captured_at,
                ))
    return deduplicate_signal_points([], out)


def deduplicate_signal_points(existing: Iterable[SignalPoint], incoming: Sequence[SignalPoint]) -> list[SignalPoint]:
    known = {p.identity for p in existing}
    accepted: list[SignalPoint] = []
    for point in incoming:
        if point.identity in known:
            continue
        accepted.append(point)
        known.add(point.identity)
    return accepted


def dumps_signal_points(points: Sequence[SignalPoint]) -> str:
    return json.dumps([asdict(p) for p in points], ensure_ascii=False, indent=2)


def loads_signal_points(text: str) -> list[SignalPoint]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError('Signaltidslinjen måste vara en lista')
    return [SignalPoint(
        coupon_key=str(x['coupon_key']), match_number=int(x['match_number']), home=str(x['home']), away=str(x['away']),
        captured_at=str(x['captured_at']), signal_type=str(x['signal_type']), subject=str(x.get('subject','')),
        source=str(x.get('source','')), verification_status=str(x.get('verification_status','observerad')),
        upstream_origin=str(x.get('upstream_origin','')), model_usable=bool(x.get('model_usable', False)),
        payload=dict(x.get('payload') or {}), observed_at=x.get('observed_at'), verified_at=x.get('verified_at'),
    ) for x in raw]


def combined_timeline_rows(market_points, signal_points: Sequence[SignalPoint], *, coupon_key: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for p in market_points:
        if p.coupon_key != coupon_key or not p.market_available:
            continue
        rows.append({'Tid': p.captured_at, 'Nr': p.match_number, 'Match': f'{p.home} – {p.away}', 'Typ': 'Bookmaker-marknad',
                     'Signal': f"1 {p.market[0]*100:.1f}% · X {p.market[1]*100:.1f}% · 2 {p.market[2]*100:.1f}%",
                     'Källa': p.market_source or 'Källa saknas', 'Status': 'Verifierad marknad', 'Modellpåverkan': 'Bas/ankare'})
    for p in signal_points:
        if p.coupon_key != coupon_key:
            continue
        if p.signal_type == 'supporter_pulse':
            team = str(p.payload.get('team') or p.subject)
            detail = f"{team}: självsäkerhet {float(p.payload.get('confidence',0))*100:.0f} · oro {float(p.payload.get('worry',0))*100:.0f}"
            typ = 'Supporter Pulse'
        elif p.signal_type == 'verified_fact':
            category = str(p.payload.get('category') or '')
            if category == 'confirmed_lineup':
                typ = 'Verifierat faktum · startelva'
            elif category == 'injury_suspension':
                typ = 'Verifierat faktum · frånvaro'
            else:
                typ = 'Verifierat faktum'
            detail = p.subject or category
            provider_value = str(p.payload.get('provider_value') or '')
            if provider_value and category == 'injury_suspension':
                parts = provider_value.split(':', 2)
                if len(parts) == 3:
                    detail = f'{parts[1]} · {parts[2]}'
        else:
            detail = p.subject or p.signal_type
            typ = p.signal_type.replace('_', ' ').title()
        rows.append({'Tid': p.captured_at, 'Nr': p.match_number, 'Match': f'{p.home} – {p.away}', 'Typ': typ,
                     'Signal': detail, 'Källa': p.source or 'Källa saknas', 'Status': p.verification_status,
                     'Modellpåverkan': 'Ja' if p.model_usable else 'Nej'})
    return sorted(rows, key=lambda r: (str(r['Tid']), int(r['Nr']), str(r['Typ'])))
