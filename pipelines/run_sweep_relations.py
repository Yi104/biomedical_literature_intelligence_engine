from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from glob import glob


def _parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def _parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def _latest_run_report(report_root: str, run_name: str) -> tuple[str, str]:
    # train_relations creates report folders as: <timestamp>_<run_name>
    matches = sorted(
        glob(os.path.join(report_root, f"*_{run_name}")),
        key=os.path.getmtime,
    )
    if not matches:
        raise FileNotFoundError(f"No report folder found for run_name={run_name}")
    run_dir = matches[-1]
    metrics_path = os.path.join(run_dir, "test_metrics.json")
    details_path = os.path.join(run_dir, "test_metrics_detailed.json")
    if not os.path.exists(metrics_path):
        raise FileNotFoundError(f"Missing metrics file: {metrics_path}")
    if not os.path.exists(details_path):
        raise FileNotFoundError(f"Missing detailed metrics file: {details_path}")
    return metrics_path, details_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid sweep for BioRED relation training.")
    parser.add_argument("--base_config", type=str, default="configs/biored_relations.json")
    parser.add_argument("--learning_rates", type=str, default="2e-5,3e-5,5e-5")
    parser.add_argument("--epochs", type=str, default="4,5,6")
    parser.add_argument("--negative_ratios", type=str, default="1,2,3")
    parser.add_argument("--max_lengths", type=str, default="256,384")
    parser.add_argument(
        "--max_runs",
        type=int,
        default=None,
        help="Optional cap for total runs (for quick iteration).",
    )
    parser.add_argument(
        "--seed_offset",
        type=int,
        default=0,
        help="Added to base seed for all runs.",
    )
    args = parser.parse_args()

    with open(args.base_config, "r", encoding="utf-8") as f:
        base_cfg = json.load(f)

    lrs = _parse_float_list(args.learning_rates)
    epochs = _parse_int_list(args.epochs)
    ratios = _parse_int_list(args.negative_ratios)
    max_lengths = _parse_int_list(args.max_lengths)
    grid = list(itertools.product(lrs, epochs, ratios, max_lengths))
    if args.max_runs is not None:
        grid = grid[: args.max_runs]

    report_root = os.path.dirname(str(base_cfg["report_path"]))
    sweep_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = os.path.join(report_root, "sweeps", sweep_id)
    os.makedirs(sweep_dir, exist_ok=True)
    temp_cfg_dir = os.path.join(sweep_dir, "configs")
    os.makedirs(temp_cfg_dir, exist_ok=True)

    results: list[dict] = []
    total = len(grid)
    for i, (lr, ep, ratio, ml) in enumerate(grid, start=1):
        run_name = f"sweep_lr{lr:g}_e{ep}_r{ratio}_m{ml}".replace(".", "p")
        cfg = deepcopy(base_cfg)
        cfg["learning_rate"] = lr
        cfg["num_train_epochs"] = ep
        cfg["negative_ratio"] = ratio
        cfg["max_length"] = ml
        cfg["run_name"] = run_name
        cfg["seed"] = int(base_cfg.get("seed", 42)) + args.seed_offset

        cfg_path = os.path.join(temp_cfg_dir, f"{i:03d}_{run_name}.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

        print(f"[{i}/{total}] training run_name={run_name}")
        cmd = [
            sys.executable,
            "-m",
            "pipelines.run_train_relations",
            "--config_path",
            cfg_path,
        ]
        subprocess.run(cmd, check=True)

        metrics_path, details_path = _latest_run_report(report_root, run_name)
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        with open(details_path, "r", encoding="utf-8") as f:
            details = json.load(f)

        corr_f1 = details.get("classification_report", {}).get("Correlation", {}).get(
            "f1-score", None
        )
        row = {
            "run_name": run_name,
            "learning_rate": lr,
            "num_train_epochs": ep,
            "negative_ratio": ratio,
            "max_length": ml,
            "eval_f1_macro": metrics.get("eval_f1_macro"),
            "eval_f1_micro": metrics.get("eval_f1_micro"),
            "eval_loss": metrics.get("eval_loss"),
            "corr_f1": corr_f1,
            "metrics_path": metrics_path,
            "details_path": details_path,
        }
        results.append(row)

    results.sort(
        key=lambda x: (
            float(x["eval_f1_macro"]) if x["eval_f1_macro"] is not None else -1.0,
            float(x["corr_f1"]) if x["corr_f1"] is not None else -1.0,
        ),
        reverse=True,
    )

    out_csv = os.path.join(sweep_dir, "results.csv")
    out_json = os.path.join(sweep_dir, "results.json")
    if results:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"OK: sweep done runs={len(results)}")
    print(f"results_csv={out_csv}")
    print(f"results_json={out_json}")
    if results:
        best = results[0]
        print(
            "best="
            f"{best['run_name']} macro_f1={best['eval_f1_macro']} "
            f"corr_f1={best['corr_f1']}"
        )


if __name__ == "__main__":
    main()
