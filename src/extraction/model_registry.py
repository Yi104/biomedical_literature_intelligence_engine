from __future__ import annotations

import json
import os
from typing import Any


LATEST_POINTER = "LATEST_MODEL_PATH.txt"
BEST_POINTER = "BEST_MODEL_PATH.txt"
BEST_METRICS = "BEST_MODEL_METRICS.json"


def _write_text(path: str, value: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(value.rstrip() + "\n")
    os.replace(temp_path, path)


def _write_json(path: str, value: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
    os.replace(temp_path, path)


def read_model_pointer(model_root: str, pointer_name: str) -> str | None:
    pointer_path = os.path.join(model_root, pointer_name)
    if not os.path.exists(pointer_path):
        return None
    with open(pointer_path, "r", encoding="utf-8") as f:
        model_path = f.read().strip()
    return model_path or None


def _is_loadable_model(model_path: str) -> bool:
    if not os.path.isfile(os.path.join(model_path, "config.json")):
        return False
    return any(
        os.path.isfile(os.path.join(model_path, weights_name))
        for weights_name in ("model.safetensors", "pytorch_model.bin")
    )


def resolve_model_for_eval(model_root: str) -> str:
    for pointer_name in (BEST_POINTER, LATEST_POINTER):
        model_path = read_model_pointer(model_root, pointer_name)
        if model_path and _is_loadable_model(model_path):
            return model_path
    if _is_loadable_model(model_root):
        return model_root
    raise FileNotFoundError(f"No loadable relation model found under {model_root}")


def _selection_key(metrics: dict[str, Any]) -> tuple[float, float, float]:
    macro_f1 = float(metrics.get("eval_f1_macro", float("-inf")))
    micro_f1 = float(metrics.get("eval_f1_micro", float("-inf")))
    loss = float(metrics.get("eval_loss", float("inf")))
    return macro_f1, micro_f1, -loss


def update_model_pointers(
    model_root: str,
    model_dir: str,
    metrics: dict[str, Any],
) -> bool:
    _write_text(os.path.join(model_root, LATEST_POINTER), model_dir)

    best_metrics_path = os.path.join(model_root, BEST_METRICS)
    previous_metrics: dict[str, Any] | None = None
    if os.path.exists(best_metrics_path):
        with open(best_metrics_path, "r", encoding="utf-8") as f:
            previous_metrics = json.load(f)

    is_best = previous_metrics is None or _selection_key(metrics) > _selection_key(
        previous_metrics
    )
    if is_best:
        _write_text(os.path.join(model_root, BEST_POINTER), model_dir)
        _write_json(best_metrics_path, metrics)
    return is_best
