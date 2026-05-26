from __future__ import annotations

from src.extraction.biored_pipeline import run_biored_pipeline
from src.extraction.bc5cdr_pipeline import run_bc5cdr_pipeline
from src.extraction.jnlpba_pipeline import run_jnlpba_pipeline

# Task router: keep the platform shared while dispatching to the right task line.


def run_task(task: str, *args, **kwargs):
    task = task.lower().strip()
    if task == "bc5cdr":
        return run_bc5cdr_pipeline(*args, **kwargs)
    if task == "jnlpba":
        return run_jnlpba_pipeline(*args, **kwargs)
    if task == "biored":
        return run_biored_pipeline(*args, **kwargs)
    raise ValueError(f"Unknown task: {task}")
