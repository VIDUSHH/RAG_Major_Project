"""
Tests for the recent-activity log service.
"""

from app.services.activity_service import recent_activity, record_activity


def test_record_and_read_activity(tmp_path, monkeypatch):
    """Records are appended and read back newest-first, bounded in size."""
    import app.services.activity_service as activity

    monkeypatch.setattr(activity, "ACTIVITY_FILE", tmp_path / "activity.json")
    monkeypatch.setattr(activity, "MAX_RECORDS", 5)

    for i in range(6):
        record_activity("ingest", f"file {i}.log", org_id="org_test", status="success")

    records = recent_activity(org_id="org_test", limit=10)
    assert len(records) == 5
    assert records[0]["title"] == "file 5.log"
    assert records[-1]["title"] == "file 1.log"
    assert records[0]["type"] == "ingest"
    assert "timestamp" in records[0]


def test_recent_activity_filters_by_org(tmp_path, monkeypatch):
    import app.services.activity_service as activity

    monkeypatch.setattr(activity, "ACTIVITY_FILE", tmp_path / "activity.json")
    monkeypatch.setattr(activity, "MAX_RECORDS", 20)

    record_activity("ingest", "org A file", org_id="org_a")
    record_activity("analyze", "org B query", org_id="org_b")

    assert [r["title"] for r in recent_activity(org_id="org_a")] == ["org A file"]
    assert [r["title"] for r in recent_activity(org_id="org_b")] == ["org B query"]


def test_recent_activity_missing_file_returns_empty(tmp_path, monkeypatch):
    import app.services.activity_service as activity

    monkeypatch.setattr(activity, "ACTIVITY_FILE", tmp_path / "does-not-exist.json")
    assert recent_activity() == []


def test_activity_file_is_written(tmp_path, monkeypatch):
    import app.services.activity_service as activity

    monkeypatch.setattr(activity, "ACTIVITY_FILE", tmp_path / "activity.json")
    record_activity("ingest", "hello", org_id="org_test")
    assert activity.ACTIVITY_FILE.exists()
    assert "hello" in activity.ACTIVITY_FILE.read_text(encoding="utf-8")
