"""Azure VM lifecycle helpers for the Windows GUI bridge.

The bridge VM is an expensive dependency compared with the Linux Container App.
This module starts it only when Windows analysis/execution needs it, records
activity in Blob Storage, and deallocates it after an idle window.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from api.config import (
    ARTIFACT_CONTAINER,
    AZURE_RESOURCE_GROUP,
    AZURE_SUBSCRIPTION_ID,
    BRIDGE_IDLE_MINUTES,
    BRIDGE_START_TIMEOUT_SECONDS,
    BRIDGE_VM_NAME,
    ENABLE_BRIDGE_VM_LIFECYCLE,
    GUI_BRIDGE_SECRET,
    GUI_BRIDGE_URL,
    _get_credential,
)

logger = logging.getLogger("mcp_factory.api")

_ACTIVITY_BLOB = "_vm/last_bridge_activity.json"
_REAPER_INTERVAL_SECONDS = 300
_READY_CACHE_SECONDS = 120
_lifecycle_lock = threading.Lock()
_ready_until_monotonic = 0.0


def bridge_lifecycle_configured() -> bool:
    return bool(GUI_BRIDGE_URL and GUI_BRIDGE_SECRET)


def bridge_vm_management_enabled() -> bool:
    return bool(
        ENABLE_BRIDGE_VM_LIFECYCLE
        and AZURE_SUBSCRIPTION_ID
        and AZURE_RESOURCE_GROUP
        and BRIDGE_VM_NAME
    )


def touch_bridge_activity(reason: str = "", job_id: str = "") -> None:
    """Update the Blob marker used by the idle reaper."""
    if not bridge_lifecycle_configured():
        return
    payload = {
        "updated_at": time.time(),
        "reason": reason,
        "job_id": job_id,
        "bridge_url": GUI_BRIDGE_URL,
    }
    try:
        from api.storage import _upload_to_blob

        _upload_to_blob(ARTIFACT_CONTAINER, _ACTIVITY_BLOB, json.dumps(payload).encode("utf-8"))
    except Exception as exc:
        logger.warning("[bridge-vm] Failed to update activity marker: %s", exc)


def get_bridge_activity() -> dict[str, Any] | None:
    try:
        from api.storage import _download_blob

        raw = _download_blob(ARTIFACT_CONTAINER, _ACTIVITY_BLOB)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.info("[bridge-vm] No bridge activity marker available: %s", exc)
        return None


def _compute_client():
    try:
        from azure.mgmt.compute import ComputeManagementClient
    except Exception as exc:
        logger.warning("[bridge-vm] azure-mgmt-compute unavailable: %s", exc)
        return None
    if not bridge_vm_management_enabled():
        return None
    return ComputeManagementClient(_get_credential(), AZURE_SUBSCRIPTION_ID)


def _power_state(client: Any) -> str:
    view = client.virtual_machines.instance_view(AZURE_RESOURCE_GROUP, BRIDGE_VM_NAME)
    for status in getattr(view, "statuses", []) or []:
        code = getattr(status, "code", "") or ""
        if code.startswith("PowerState/"):
            return code.split("/", 1)[1]
    return "unknown"


def _wait_bridge_health(timeout_seconds: int, *, log_prefix: str = "[bridge-vm]") -> bool:
    if not bridge_lifecycle_configured():
        return False

    import httpx

    deadline = time.monotonic() + max(1, timeout_seconds)
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(
                f"{GUI_BRIDGE_URL}/health",
                headers={"X-Bridge-Key": GUI_BRIDGE_SECRET},
                timeout=5.0,
            )
            if resp.status_code == 200:
                logger.info("%s Bridge health OK", log_prefix)
                return True
            logger.info("%s Bridge health status=%s", log_prefix, resp.status_code)
        except Exception as exc:
            last_exc = exc
            logger.info("%s Bridge health pending: %s", log_prefix, exc)
        time.sleep(5)

    if last_exc:
        logger.warning("%s Bridge did not become healthy: %s", log_prefix, last_exc)
    else:
        logger.warning("%s Bridge did not become healthy before timeout", log_prefix)
    return False


def ensure_bridge_ready(
    *,
    job_id: str = "",
    status_callback: Callable[[str, int], None] | None = None,
    timeout_seconds: int | None = None,
) -> bool:
    """Start the Windows bridge VM if needed and wait for /health."""
    global _ready_until_monotonic
    if not bridge_lifecycle_configured():
        return False

    if time.monotonic() < _ready_until_monotonic:
        touch_bridge_activity("ready-cache", job_id)
        return True

    timeout = timeout_seconds or BRIDGE_START_TIMEOUT_SECONDS
    if status_callback:
        status_callback("Starting Windows analysis VM. This may take a few minutes...", 55)

    if not bridge_vm_management_enabled():
        logger.info("[bridge-vm] VM lifecycle disabled or missing Azure config; probing existing bridge")
        ok = _wait_bridge_health(min(timeout, 30))
        if ok:
            _ready_until_monotonic = time.monotonic() + _READY_CACHE_SECONDS
            touch_bridge_activity("health-probe", job_id)
        return ok

    client = _compute_client()
    if client is None:
        ok = _wait_bridge_health(min(timeout, 30))
        if ok:
            _ready_until_monotonic = time.monotonic() + _READY_CACHE_SECONDS
            touch_bridge_activity("health-probe", job_id)
        return ok

    with _lifecycle_lock:
        try:
            state = _power_state(client)
            logger.info("[bridge-vm] Current VM power state: %s", state)
            if state in {"deallocated", "deallocating", "stopped", "stopping", "unknown"}:
                if status_callback:
                    status_callback("Starting Windows analysis VM. This may take a few minutes...", 55)
                poller = client.virtual_machines.begin_start(AZURE_RESOURCE_GROUP, BRIDGE_VM_NAME)
                poller.result(timeout=timeout)
                logger.info("[bridge-vm] Start operation completed")
            else:
                logger.info("[bridge-vm] VM already active enough for bridge startup: %s", state)
        except Exception as exc:
            logger.warning("[bridge-vm] VM start/read failed: %s", exc)
            # The bridge might already be running even if ARM read/start failed.

    if status_callback:
        status_callback("Waiting for Windows bridge health...", 58)
    ok = _wait_bridge_health(timeout, log_prefix=f"[bridge-vm {job_id or 'execute'}]")
    if ok:
        _ready_until_monotonic = time.monotonic() + _READY_CACHE_SECONDS
        touch_bridge_activity("bridge-ready", job_id)
    return ok


def deallocate_bridge_vm(reason: str = "idle") -> bool:
    """Deallocate the bridge VM. Returns True only when ARM accepted it."""
    if not bridge_vm_management_enabled():
        return False
    client = _compute_client()
    if client is None:
        return False
    with _lifecycle_lock:
        try:
            state = _power_state(client)
            if state in {"deallocated", "deallocating"}:
                logger.info("[bridge-vm] VM already %s", state)
                return True
            logger.info("[bridge-vm] Deallocating VM %s due to %s", BRIDGE_VM_NAME, reason)
            poller = client.virtual_machines.begin_deallocate(AZURE_RESOURCE_GROUP, BRIDGE_VM_NAME)
            poller.result(timeout=300)
            logger.info("[bridge-vm] Deallocate completed")
            return True
        except Exception as exc:
            logger.warning("[bridge-vm] Deallocate failed: %s", exc)
            return False


def deallocate_bridge_vm_if_idle() -> bool:
    """Deallocate the VM if Blob activity marker is older than idle threshold."""
    marker = get_bridge_activity()
    if not marker:
        logger.info("[bridge-vm] Idle reaper skipped; no activity marker")
        return False

    updated_at = float(marker.get("updated_at") or 0)
    idle_seconds = time.time() - updated_at
    threshold = max(1, BRIDGE_IDLE_MINUTES) * 60
    if idle_seconds < threshold:
        logger.info("[bridge-vm] Idle reaper skipped; idle %.0fs < %.0fs", idle_seconds, threshold)
        return False
    return deallocate_bridge_vm(reason=f"idle for {idle_seconds:.0f}s")


def bridge_idle_reaper_loop() -> None:
    """Background loop for ACA. A workflow safety net handles scale-to-zero."""
    if not bridge_lifecycle_configured():
        logger.info("[bridge-vm] Idle reaper disabled; bridge not configured")
        return
    if not bridge_vm_management_enabled():
        logger.info("[bridge-vm] Idle reaper disabled; VM lifecycle not enabled/configured")
        return

    logger.info("[bridge-vm] Idle reaper started; threshold=%d minutes", BRIDGE_IDLE_MINUTES)
    while True:
        try:
            deallocate_bridge_vm_if_idle()
        except Exception as exc:
            logger.warning("[bridge-vm] Idle reaper iteration failed: %s", exc)
        time.sleep(_REAPER_INTERVAL_SECONDS)
