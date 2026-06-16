from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_LOG_ROOT = "outputs/logs"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


@dataclass(frozen=True)
class RunArtifacts:
    command_name: str
    run_id: str
    run_dir: str
    log_path: str
    manifest_path: str


def _resolve_repo_path(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        resolved = candidate
    else:
        resolved = (Path.cwd() / candidate).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return str(resolved)


def setup_run_logging(
    *,
    command_name: str,
    log_level: str,
    args: dict[str, Any],
    log_root: str = DEFAULT_LOG_ROOT,
) -> RunArtifacts:
    resolved_log_root = _resolve_repo_path(log_root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(resolved_log_root, command_name, run_id)
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "run.log")
    manifest_path = os.path.join(run_dir, "manifest.json")

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "Run logging initialized: command=%s run_dir=%s log_path=%s",
        command_name,
        run_dir,
        log_path,
    )
    write_run_manifest(
        RunArtifacts(
            command_name=command_name,
            run_id=run_id,
            run_dir=run_dir,
            log_path=log_path,
            manifest_path=manifest_path,
        ),
        status="started",
        args=args,
    )
    return RunArtifacts(
        command_name=command_name,
        run_id=run_id,
        run_dir=run_dir,
        log_path=log_path,
        manifest_path=manifest_path,
    )


def write_run_manifest(
    artifacts: RunArtifacts,
    *,
    status: str,
    args: dict[str, Any],
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    payload = {
        "command_name": artifacts.command_name,
        "run_id": artifacts.run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "args": args,
        "log_path": artifacts.log_path,
        "summary": summary or {},
        "error": error,
    }
    with open(artifacts.manifest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def finalize_run_manifest(
    artifacts: RunArtifacts,
    *,
    status: str,
    args: dict[str, Any],
    summary: dict[str, Any] | None = None,
    error: BaseException | None = None,
) -> None:
    error_text = None
    if error is not None:
        error_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
    write_run_manifest(
        artifacts,
        status=status,
        args=args,
        summary=summary,
        error=error_text,
    )
