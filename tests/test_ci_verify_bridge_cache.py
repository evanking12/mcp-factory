from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import ci_verify


def _health(*, process_id: int = 1234, creation_date: str = "1000.000000", session_id: int = 1) -> dict:
    payload = {
        "status": "ok",
        "process_id": process_id,
        "creation_date": creation_date,
        "session_id": session_id,
    }
    return {"ok": True, "status": 200, "json": payload, "body": ""}


def test_bridge_session_cache_reuses_matching_identity(tmp_path: Path) -> None:
    cache_path = tmp_path / ".bridge-session-cache.json"
    ci_verify._write_bridge_session_cache(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(),
        process_info={"ok": True, "process_id": 1234, "creation_date": "unused", "session_id": 1},
        resource_group="rg",
        vm_name="vm",
    )

    proof = ci_verify._cached_bridge_session_proof(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(),
        resource_group="rg",
        vm_name="vm",
        required_session_id=1,
    )

    assert proof is not None
    assert proof["cached"] is True
    assert proof["process_id"] == 1234
    assert proof["session_id"] == 1


def test_bridge_session_cache_invalidates_pid_change(tmp_path: Path) -> None:
    cache_path = tmp_path / ".bridge-session-cache.json"
    ci_verify._write_bridge_session_cache(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(process_id=1234),
        process_info={"ok": True, "process_id": 1234, "creation_date": "unused", "session_id": 1},
        resource_group="rg",
        vm_name="vm",
    )

    proof = ci_verify._cached_bridge_session_proof(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(process_id=9999),
        resource_group="rg",
        vm_name="vm",
        required_session_id=1,
    )

    assert proof is None


def test_bridge_session_cache_invalidates_creation_date_change(tmp_path: Path) -> None:
    cache_path = tmp_path / ".bridge-session-cache.json"
    ci_verify._write_bridge_session_cache(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(creation_date="1000.000000"),
        process_info={"ok": True, "process_id": 1234, "creation_date": "unused", "session_id": 1},
        resource_group="rg",
        vm_name="vm",
    )

    proof = ci_verify._cached_bridge_session_proof(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(creation_date="1001.000000"),
        resource_group="rg",
        vm_name="vm",
        required_session_id=1,
    )

    assert proof is None


def test_bridge_session_cache_rejects_wrong_required_session(tmp_path: Path) -> None:
    cache_path = tmp_path / ".bridge-session-cache.json"
    ci_verify._write_bridge_session_cache(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(session_id=0),
        process_info={"ok": True, "process_id": 1234, "creation_date": "unused", "session_id": 0},
        resource_group="rg",
        vm_name="vm",
    )

    proof = ci_verify._cached_bridge_session_proof(
        cache_path=cache_path,
        bridge_url="http://bridge:8090",
        health=_health(session_id=0),
        resource_group="rg",
        vm_name="vm",
        required_session_id=1,
    )

    assert proof is None


def test_bridge_health_cache_miss_inspects_vm_process(tmp_path: Path, monkeypatch) -> None:
    calls = {"process": 0}

    monkeypatch.setattr(ci_verify, "_wait_bridge_health", lambda *args, **kwargs: _health())

    def fake_process_info(**kwargs):
        calls["process"] += 1
        return {"ok": True, "process_id": 1234, "creation_date": "wmi-date", "session_id": 1}

    monkeypatch.setattr(ci_verify, "_bridge_process_info", fake_process_info)

    result = ci_verify._ensure_bridge_health(
        "http://bridge:8090",
        "secret",
        timeout=1,
        restart_resource_group="rg",
        restart_vm_name="vm",
        required_session_id=1,
        session_cache_path=tmp_path / ".bridge-session-cache.json",
    )

    assert result["ok"] is True
    assert calls["process"] == 1
    assert result["bridge_process"]["session_id"] == 1


def test_bridge_session_zero_triggers_recovery_path(tmp_path: Path, monkeypatch) -> None:
    process_results = iter(
        [
            {"ok": True, "process_id": 1234, "creation_date": "old", "session_id": 0},
            {"ok": True, "process_id": 1235, "creation_date": "new", "session_id": 1},
        ]
    )

    monkeypatch.setattr(ci_verify, "_wait_bridge_health", lambda *args, **kwargs: _health())
    monkeypatch.setattr(ci_verify, "_bridge_process_info", lambda **kwargs: next(process_results))
    monkeypatch.setattr(ci_verify, "_ensure_bridge_vm_running", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(ci_verify, "_restart_bridge_task", lambda **kwargs: {"ok": True})

    result = ci_verify._ensure_bridge_health(
        "http://bridge:8090",
        "secret",
        timeout=1,
        restart_resource_group="rg",
        restart_vm_name="vm",
        required_session_id=1,
        session_cache_path=tmp_path / ".bridge-session-cache.json",
    )

    assert result["ok"] is True
    assert result["restart_attempted"] is True
    assert result["bridge_process"]["session_id"] == 1
