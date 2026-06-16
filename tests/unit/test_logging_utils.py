from __future__ import annotations

import json

from src.logging_utils import finalize_run_manifest, setup_run_logging


def test_setup_run_logging_creates_log_dir_and_manifest(tmp_path):
    artifacts = setup_run_logging(
        command_name="demo_cmd",
        log_level="INFO",
        args={"alpha": 1},
        log_root=str(tmp_path / "logs"),
    )

    with open(artifacts.manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["command_name"] == "demo_cmd"
    assert manifest["status"] == "started"
    assert manifest["args"]["alpha"] == 1


def test_finalize_run_manifest_updates_summary_and_error(tmp_path):
    artifacts = setup_run_logging(
        command_name="demo_cmd",
        log_level="INFO",
        args={"alpha": 1},
        log_root=str(tmp_path / "logs"),
    )

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        finalize_run_manifest(
            artifacts,
            status="failed",
            args={"alpha": 1},
            summary={"rows": 3},
            error=exc,
        )

    with open(artifacts.manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["status"] == "failed"
    assert manifest["summary"]["rows"] == 3
    assert "RuntimeError: boom" in manifest["error"]
