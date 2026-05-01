import json

from dip_coater.logging.session_log import NullSessionLog, SessionLog


def test_session_log_appends_json_lines_with_event_metadata(tmp_path):
    log_path = tmp_path / "logs" / "session.jsonl"
    session_log = SessionLog(log_path)

    session_log.write("session_started", driver="TMC5160")
    session_log.write("motion_requested", direction="up", distance_mm=2.5)

    entries = [
        json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert entries[0]["event"] == "session_started"
    assert entries[0]["driver"] == "TMC5160"
    assert "timestamp" in entries[0]
    assert entries[1]["event"] == "motion_requested"
    assert entries[1]["direction"] == "up"
    assert entries[1]["distance_mm"] == 2.5


def test_null_session_log_accepts_diagnostics_without_writing():
    NullSessionLog().write("motion_requested", direction="down")
