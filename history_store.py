from __future__ import annotations

"""Persistent storage for Streckverket's facit/learning history.

The storage layer deliberately stores the complete FacitCoupon as versioned JSON.
That keeps old snapshots readable even when the relational schema evolves. SQLite
works out of the box for local/dev use. PostgreSQL (for example Neon) is enabled
when a DATABASE URL is supplied and psycopg is installed.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Iterable, List, Sequence

from facit import FacitCoupon, dumps_facit, loads_facit
from market_timeline import MarketPoint, deduplicate_points, dumps_market_points, loads_market_points
from signal_timeline import SignalPoint, deduplicate_signal_points, loads_signal_points

SCHEMA_VERSION = 5


class HistoryStoreError(RuntimeError):
    pass


class HistoryStore:
    backend: str = "unknown"
    persistent_cloud: bool = False

    def save_coupon(self, coupon: FacitCoupon) -> None:
        raise NotImplementedError

    def load_coupons(self) -> List[FacitCoupon]:
        raise NotImplementedError

    def save_market_points(self, points: Sequence[MarketPoint]) -> int:
        raise NotImplementedError

    def load_market_points(self, coupon_key: str | None = None) -> List[MarketPoint]:
        raise NotImplementedError

    def save_signal_points(self, points: Sequence[SignalPoint]) -> int:
        raise NotImplementedError

    def load_signal_points(self, coupon_key: str | None = None) -> List[SignalPoint]:
        raise NotImplementedError

    def delete_coupon(self, coupon_id: str) -> bool:
        raise NotImplementedError

    def replace_all(self, coupons: Sequence[FacitCoupon]) -> None:
        existing = [c.coupon_id for c in self.load_coupons()]
        for coupon_id in existing:
            self.delete_coupon(coupon_id)
        for coupon in coupons:
            self.save_coupon(coupon)

    def import_json(self, text: str, *, merge: bool = True) -> int:
        coupons = loads_facit(text)
        if not merge:
            self.replace_all(coupons)
        else:
            for coupon in coupons:
                self.save_coupon(coupon)
        return len(coupons)

    def export_json(self) -> str:
        return dumps_facit(self.load_coupons())

    def status_text(self) -> str:
        return self.backend


class SQLiteHistoryStore(HistoryStore):
    backend = "SQLite"
    persistent_cloud = False

    def __init__(self, path: str):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facit_coupons (
                    coupon_id TEXT PRIMARY KEY,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_facit_captured_at ON facit_coupons(captured_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_points (
                    coupon_key TEXT NOT NULL,
                    match_number INTEGER NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (coupon_key, match_number, captured_at)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_points_coupon ON market_points(coupon_key, captured_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_points (
                    identity TEXT PRIMARY KEY,
                    coupon_key TEXT NOT NULL,
                    match_number INTEGER NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_points_coupon ON signal_points(coupon_key, captured_at)")

    def save_coupon(self, coupon: FacitCoupon) -> None:
        payload = json.dumps(asdict(coupon), ensure_ascii=False, separators=(",", ":"))
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO facit_coupons
                    (coupon_id, captured_at, source, strategy, schema_version, payload, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(coupon_id) DO UPDATE SET
                    captured_at=excluded.captured_at,
                    source=excluded.source,
                    strategy=excluded.strategy,
                    schema_version=excluded.schema_version,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    coupon.coupon_id,
                    coupon.captured_at,
                    coupon.source,
                    coupon.strategy,
                    SCHEMA_VERSION,
                    payload,
                    now,
                ),
            )

    def load_coupons(self) -> List[FacitCoupon]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM facit_coupons ORDER BY captured_at ASC, coupon_id ASC"
            ).fetchall()
        if not rows:
            return []
        raw = "[" + ",".join(row[0] for row in rows) + "]"
        return loads_facit(raw)

    def save_market_points(self, points: Sequence[MarketPoint]) -> int:
        if not points:
            return 0
        existing = self.load_market_points(points[0].coupon_key)
        accepted = deduplicate_points(existing, points)
        if not accepted:
            return 0
        with self._connect() as conn:
            for point in accepted:
                payload = json.dumps(asdict(point), ensure_ascii=False, separators=(",", ":"))
                conn.execute(
                    "INSERT OR IGNORE INTO market_points (coupon_key, match_number, captured_at, payload) VALUES (?, ?, ?, ?)",
                    (point.coupon_key, point.match_number, point.captured_at, payload),
                )
        return len(accepted)

    def load_market_points(self, coupon_key: str | None = None) -> List[MarketPoint]:
        with self._connect() as conn:
            if coupon_key is None:
                rows = conn.execute("SELECT payload FROM market_points ORDER BY captured_at ASC, match_number ASC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload FROM market_points WHERE coupon_key = ? ORDER BY captured_at ASC, match_number ASC",
                    (str(coupon_key),),
                ).fetchall()
        if not rows:
            return []
        return loads_market_points("[" + ",".join(row[0] for row in rows) + "]")

    def save_signal_points(self, points: Sequence[SignalPoint]) -> int:
        if not points:
            return 0
        existing = self.load_signal_points(points[0].coupon_key)
        accepted = deduplicate_signal_points(existing, points)
        with self._connect() as conn:
            for point in accepted:
                payload = json.dumps(asdict(point), ensure_ascii=False, separators=(",", ":"))
                conn.execute("INSERT OR IGNORE INTO signal_points (identity, coupon_key, match_number, captured_at, payload) VALUES (?, ?, ?, ?, ?)",
                             (point.identity, point.coupon_key, point.match_number, point.captured_at, payload))
        return len(accepted)

    def load_signal_points(self, coupon_key: str | None = None) -> List[SignalPoint]:
        with self._connect() as conn:
            if coupon_key is None:
                rows = conn.execute("SELECT payload FROM signal_points ORDER BY captured_at ASC, match_number ASC").fetchall()
            else:
                rows = conn.execute("SELECT payload FROM signal_points WHERE coupon_key = ? ORDER BY captured_at ASC, match_number ASC", (str(coupon_key),)).fetchall()
        return loads_signal_points("[" + ",".join(row[0] for row in rows) + "]") if rows else []

    def delete_coupon(self, coupon_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM facit_coupons WHERE coupon_id = ?", (str(coupon_id),))
            return cur.rowcount > 0

    def status_text(self) -> str:
        return f"SQLite · {self.path}"


class PostgresHistoryStore(HistoryStore):
    backend = "PostgreSQL"
    persistent_cloud = True

    def __init__(self, database_url: str):
        if not database_url.strip():
            raise ValueError("database_url får inte vara tom")
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise HistoryStoreError(
                "PostgreSQL-lagring kräver paketet psycopg. Installera projektets requirements.txt."
            ) from exc
        self._psycopg = psycopg
        self.database_url = database_url
        self._init_schema()

    def _connect(self):
        return self._psycopg.connect(self.database_url)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS facit_coupons (
                        coupon_id TEXT PRIMARY KEY,
                        captured_at TEXT NOT NULL,
                        source TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        schema_version INTEGER NOT NULL,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_facit_captured_at ON facit_coupons(captured_at)"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_points (
                        coupon_key TEXT NOT NULL,
                        match_number INTEGER NOT NULL,
                        captured_at TIMESTAMPTZ NOT NULL,
                        payload JSONB NOT NULL,
                        PRIMARY KEY (coupon_key, match_number, captured_at)
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_market_points_coupon ON market_points(coupon_key, captured_at)"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS signal_points (
                        identity TEXT PRIMARY KEY, coupon_key TEXT NOT NULL, match_number INTEGER NOT NULL,
                        captured_at TIMESTAMPTZ NOT NULL, payload JSONB NOT NULL
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_points_coupon ON signal_points(coupon_key, captured_at)")

    def save_coupon(self, coupon: FacitCoupon) -> None:
        payload = json.dumps(asdict(coupon), ensure_ascii=False)
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO facit_coupons
                        (coupon_id, captured_at, source, strategy, schema_version, payload, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT(coupon_id) DO UPDATE SET
                        captured_at=excluded.captured_at,
                        source=excluded.source,
                        strategy=excluded.strategy,
                        schema_version=excluded.schema_version,
                        payload=excluded.payload,
                        updated_at=excluded.updated_at
                    """,
                    (
                        coupon.coupon_id,
                        coupon.captured_at,
                        coupon.source,
                        coupon.strategy,
                        SCHEMA_VERSION,
                        payload,
                        now,
                    ),
                )

    def load_coupons(self) -> List[FacitCoupon]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload::text FROM facit_coupons ORDER BY captured_at ASC, coupon_id ASC")
                rows = cur.fetchall()
        if not rows:
            return []
        return loads_facit("[" + ",".join(str(row[0]) for row in rows) + "]")

    def save_market_points(self, points: Sequence[MarketPoint]) -> int:
        if not points:
            return 0
        existing = self.load_market_points(points[0].coupon_key)
        accepted = deduplicate_points(existing, points)
        if not accepted:
            return 0
        with self._connect() as conn:
            with conn.cursor() as cur:
                for point in accepted:
                    payload = json.dumps(asdict(point), ensure_ascii=False)
                    cur.execute(
                        """
                        INSERT INTO market_points (coupon_key, match_number, captured_at, payload)
                        VALUES (%s, %s, %s, %s::jsonb)
                        ON CONFLICT (coupon_key, match_number, captured_at) DO NOTHING
                        """,
                        (point.coupon_key, point.match_number, point.captured_at, payload),
                    )
        return len(accepted)

    def load_market_points(self, coupon_key: str | None = None) -> List[MarketPoint]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if coupon_key is None:
                    cur.execute("SELECT payload::text FROM market_points ORDER BY captured_at ASC, match_number ASC")
                else:
                    cur.execute(
                        "SELECT payload::text FROM market_points WHERE coupon_key = %s ORDER BY captured_at ASC, match_number ASC",
                        (str(coupon_key),),
                    )
                rows = cur.fetchall()
        if not rows:
            return []
        return loads_market_points("[" + ",".join(str(row[0]) for row in rows) + "]")

    def save_signal_points(self, points: Sequence[SignalPoint]) -> int:
        if not points:
            return 0
        existing = self.load_signal_points(points[0].coupon_key)
        accepted = deduplicate_signal_points(existing, points)
        with self._connect() as conn:
            with conn.cursor() as cur:
                for point in accepted:
                    payload = json.dumps(asdict(point), ensure_ascii=False)
                    cur.execute("INSERT INTO signal_points (identity, coupon_key, match_number, captured_at, payload) VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT(identity) DO NOTHING",
                                (point.identity, point.coupon_key, point.match_number, point.captured_at, payload))
        return len(accepted)

    def load_signal_points(self, coupon_key: str | None = None) -> List[SignalPoint]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if coupon_key is None:
                    cur.execute("SELECT payload::text FROM signal_points ORDER BY captured_at ASC, match_number ASC")
                else:
                    cur.execute("SELECT payload::text FROM signal_points WHERE coupon_key = %s ORDER BY captured_at ASC, match_number ASC", (str(coupon_key),))
                rows = cur.fetchall()
        return loads_signal_points("[" + ",".join(str(row[0]) for row in rows) + "]") if rows else []

    def delete_coupon(self, coupon_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM facit_coupons WHERE coupon_id = %s", (str(coupon_id),))
                return cur.rowcount > 0

    def status_text(self) -> str:
        return "PostgreSQL · molndatabas"


def create_history_store(
    *,
    database_url: str | None = None,
    sqlite_path: str | None = None,
) -> HistoryStore:
    """Choose storage without inventing cloud persistence.

    Priority:
    1. explicit database_url
    2. STRECKVERKET_DATABASE_URL
    3. SQLite path (explicit / STRECKVERKET_DB_PATH / local default)
    """
    url = database_url if database_url is not None else os.getenv("STRECKVERKET_DATABASE_URL", "")
    if url and url.strip():
        return PostgresHistoryStore(url.strip())
    path = sqlite_path or os.getenv("STRECKVERKET_DB_PATH") or "streckverket_history.db"
    return SQLiteHistoryStore(path)
