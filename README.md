# Managed Onboard Compute Payload (MOCP) Prototype MVP

Live app: https://mocp--mvp.streamlit.app

## Overview
This MVP is an interactive simulation workflow for evaluating safety-state behavior under constrained onboard conditions.

States:
- `NOMINAL`
- `THROTTLE`
- `SAFE`
- `RECOVER`

## Features
- Synthetic telemetry generator for `power_watts` and `temp_c` (periodic behavior + noise).
- Eclipse cycle model that impacts power and temperature.
- Fault injection:
  - Manual fault: `none`, `minor`, `critical`
  - Random fault rate: `0-5 faults/hour`
  - Fault labels: `sensor_dropout`, `watchdog_timeout`, `bitflip`
- Policy modes:
  - `rule_based` threshold logic
  - `risk_scored` weighted-factor logic
- Optional hysteresis/min dwell controls.
- Explainability panel: “Why am I in this state?”.
- Timeline/event logs with severity tags.
- Export telemetry + events CSV.
- Monte Carlo Experiment Lab:
  - Runs seeded comparisons across policy mode + hysteresis settings
  - Outputs aggregate metrics and downloadable CSV
- Submission Pack:
  - Screenshot target planner (NOMINAL/THROTTLE/SAFE/RECOVER)
  - Service blueprint table + CSV
  - Downloadable guided demo script and tour JSON

## Run Locally
```bash
pip install streamlit pandas numpy
streamlit run app.py
```

## Suggested Screenshot Workflow
Use preset scenarios and “Jump To Target Step” for consistent captures:
1. `Nominal Screenshot`
2. `Throttle Screenshot`
3. `Safe Screenshot`
4. `Recover Screenshot`

Then export screenshot checklist CSV from the Submission Pack tab.

## Quantitative Evidence Workflow
1. Open **Experiment Lab**.
2. Choose seed count (e.g., 60+), steps, noise, and fault rate.
3. Run Monte Carlo.
4. Export `mocp_experiment_summary.csv` and `mocp_experiment_raw.csv`.

## Reproducible Offline Evaluation
Run the same seeded suite used for the report:

```bash
python evaluate_mvp.py --seeds 120 --out-dir .
```

Outputs:
- `evaluation_v2_raw.csv`
- `evaluation_v2_summary.csv`

## Service Blueprint Artifact
FigJam board:
- https://www.figma.com/online-whiteboard/create-diagram/4a0efe97-3f2a-423a-aabc-c35b15a8fe43
