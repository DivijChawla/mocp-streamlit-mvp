#!/usr/bin/env python3
"""Run reproducible seeded evaluations for the MOCP MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import app


def run_suite(seeds: int, out_dir: Path) -> tuple[Path, Path]:
    experiments = [
        ("exp_minor", "minor", seeds, 240, 3.5, 1.2, 120, 4, 5),
        ("exp_critical", "critical", seeds, 240, 3.5, 1.2, 120, 4, 5),
        ("exp_stress_none", "none", seeds, 240, 4.0, 3.0, 120, 4, 5),
    ]

    all_raw = []
    all_summary = []

    for name, manual, s, steps, noise, rate, mstep, dwell, recover in experiments:
        raw, summary = app.run_experiment_grid(
            seeds=s,
            steps=steps,
            noise_level=noise,
            random_fault_rate=rate,
            manual_fault=manual,
            manual_fault_step=mstep,
            min_dwell_steps=dwell,
            recover_hold_steps=recover,
        )
        raw["experiment"] = name
        summary["experiment"] = name
        all_raw.append(raw)
        all_summary.append(summary)

    raw_df = pd.concat(all_raw, ignore_index=True)
    summary_df = pd.concat(all_summary, ignore_index=True)

    raw_path = out_dir / "evaluation_v2_raw.csv"
    summary_path = out_dir / "evaluation_v2_summary.csv"
    raw_df.to_csv(raw_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    return raw_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MOCP MVP evaluation suite.")
    parser.add_argument("--seeds", type=int, default=120, help="Number of seeds per experiment track.")
    parser.add_argument("--out-dir", type=Path, default=Path("."), help="Output directory.")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path, summary_path = run_suite(args.seeds, args.out_dir)

    print(f"Wrote: {raw_path}")
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
