import json
from pathlib import Path

from src.extraction.model_registry import (
    BEST_METRICS,
    BEST_POINTER,
    LATEST_POINTER,
    resolve_model_for_eval,
    update_model_pointers,
)


def _metrics(macro: float, micro: float, loss: float) -> dict[str, float]:
    return {
        "eval_f1_macro": macro,
        "eval_f1_micro": micro,
        "eval_loss": loss,
    }


def _make_loadable_model(model_path: Path) -> None:
    model_path.mkdir(parents=True)
    (model_path / "config.json").write_text("{}")
    (model_path / "model.safetensors").write_bytes(b"weights")


def test_update_model_pointers_keeps_best_and_advances_latest(tmp_path: Path):
    model_root = tmp_path / "models"
    first = model_root / "run-1"
    second = model_root / "run-2"
    first.mkdir(parents=True)
    second.mkdir()

    assert update_model_pointers(
        str(model_root), str(first), _metrics(0.60, 0.70, 1.0)
    )
    assert not update_model_pointers(
        str(model_root), str(second), _metrics(0.55, 0.80, 0.8)
    )

    assert (model_root / LATEST_POINTER).read_text().strip() == str(second)
    assert (model_root / BEST_POINTER).read_text().strip() == str(first)
    saved_metrics = json.loads((model_root / BEST_METRICS).read_text())
    assert saved_metrics["eval_f1_macro"] == 0.60


def test_update_model_pointers_uses_tie_breakers(tmp_path: Path):
    model_root = tmp_path / "models"
    first = model_root / "run-1"
    second = model_root / "run-2"
    first.mkdir(parents=True)
    second.mkdir()

    update_model_pointers(str(model_root), str(first), _metrics(0.60, 0.70, 1.0))
    assert update_model_pointers(
        str(model_root), str(second), _metrics(0.60, 0.70, 0.9)
    )
    assert (model_root / BEST_POINTER).read_text().strip() == str(second)


def test_resolve_model_for_eval_prefers_existing_best(tmp_path: Path):
    model_root = tmp_path / "models"
    best = model_root / "best"
    latest = model_root / "latest"
    _make_loadable_model(best)
    _make_loadable_model(latest)
    (model_root / BEST_POINTER).write_text(str(best))
    (model_root / LATEST_POINTER).write_text(str(latest))

    assert resolve_model_for_eval(str(model_root)) == str(best)


def test_resolve_model_for_eval_skips_pointer_without_weights(tmp_path: Path):
    model_root = tmp_path / "models"
    best = model_root / "best"
    latest = model_root / "latest"
    best.mkdir(parents=True)
    (best / "config.json").write_text("{}")
    _make_loadable_model(latest)
    (model_root / BEST_POINTER).write_text(str(best))
    (model_root / LATEST_POINTER).write_text(str(latest))

    assert resolve_model_for_eval(str(model_root)) == str(latest)
