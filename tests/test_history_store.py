from dataclasses import replace

from core import MatchInput
from facit import make_coupon_snapshot, with_results
from history_store import SQLiteHistoryStore, create_history_store


def _coupon(coupon_id="c1"):
    matches = [
        MatchInput(i + 1, f"H{i}", f"A{i}", (2.0, 3.4, 4.2), (0.48, 0.30, 0.22), (0.55, 0.25, 0.20))
        for i in range(13)
    ]
    return make_coupon_snapshot(
        coupon_id,
        matches,
        [("1",)] * 13,
        source="Test",
        strategy="MAX 13",
        budget=64,
        rows=64,
        model_coverage=0.1,
        captured_at="2026-09-03T05:00:00+00:00",
    )


def test_sqlite_roundtrip(tmp_path):
    store = SQLiteHistoryStore(str(tmp_path / "history.db"))
    store.save_coupon(_coupon())
    loaded = store.load_coupons()
    assert len(loaded) == 1
    assert loaded[0].coupon_id == "c1"
    assert loaded[0].matches[0].home == "H0"


def test_upsert_updates_same_coupon(tmp_path):
    store = SQLiteHistoryStore(str(tmp_path / "history.db"))
    c = _coupon()
    store.save_coupon(c)
    updated = with_results(c, {1: "X"})
    store.save_coupon(updated)
    loaded = store.load_coupons()
    assert len(loaded) == 1
    assert loaded[0].matches[0].result == "X"


def test_multiple_coupons_are_sorted(tmp_path):
    store = SQLiteHistoryStore(str(tmp_path / "history.db"))
    late = replace(_coupon("late"), captured_at="2026-09-04T05:00:00+00:00")
    early = replace(_coupon("early"), captured_at="2026-09-02T05:00:00+00:00")
    store.save_coupon(late)
    store.save_coupon(early)
    assert [c.coupon_id for c in store.load_coupons()] == ["early", "late"]


def test_delete_coupon(tmp_path):
    store = SQLiteHistoryStore(str(tmp_path / "history.db"))
    store.save_coupon(_coupon())
    assert store.delete_coupon("c1") is True
    assert store.delete_coupon("c1") is False
    assert store.load_coupons() == []


def test_export_import_merge(tmp_path):
    a = SQLiteHistoryStore(str(tmp_path / "a.db"))
    b = SQLiteHistoryStore(str(tmp_path / "b.db"))
    a.save_coupon(_coupon("one"))
    a.save_coupon(_coupon("two"))
    count = b.import_json(a.export_json())
    assert count == 2
    assert {c.coupon_id for c in b.load_coupons()} == {"one", "two"}


def test_import_replace_removes_old(tmp_path):
    a = SQLiteHistoryStore(str(tmp_path / "a.db"))
    b = SQLiteHistoryStore(str(tmp_path / "b.db"))
    a.save_coupon(_coupon("new"))
    b.save_coupon(_coupon("old"))
    b.import_json(a.export_json(), merge=False)
    assert [c.coupon_id for c in b.load_coupons()] == ["new"]


def test_factory_defaults_to_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("STRECKVERKET_DATABASE_URL", raising=False)
    store = create_history_store(sqlite_path=str(tmp_path / "history.db"))
    assert isinstance(store, SQLiteHistoryStore)
    assert store.persistent_cloud is False
