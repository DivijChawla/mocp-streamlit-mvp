# Managed Onboard Compute Payload (MOCP) Prototype MVP

## Disclaimer (Read First)
This app is a **toy simulator for UI/workflow validation only**.
It is **not flight software**, **not a physics-accurate spacecraft simulator**, and must not be used for mission-critical decisions.

## What Is Simulated
- Synthetic telemetry for `power_watts` and `temp_c` with periodic behavior and configurable noise.
- Eclipse cycles that reduce power and cool temperature.
- Fault injection (manual and random) using labels: `sensor_dropout`, `watchdog_timeout`, `bitflip`.
- Safety state machine with states: `NOMINAL`, `THROTTLE`, `SAFE`, `RECOVER`.

## What Is Not Claimed
- No orbital-mechanics fidelity.
- No realistic thermal/power subsystem fidelity.
- No certified FDIR logic.
- No flight readiness claim.

## Requirements
```bash
pip install streamlit pandas numpy
```

## Run
```bash
streamlit run app.py
```

## Screenshot Reproduction Guide (4 States)
1. **NOMINAL**
   - `Manual fault` = `none`
   - `Random fault rate` = `0.0 faults/hour`
   - Keep eclipse enabled and use moderate noise.
   - Move `Focus step` to a point where telemetry is nominal.

2. **THROTTLE**
   - `Manual fault` = `minor`
   - Set manual fault near the selected focus step.
   - Capture when Current State shows `THROTTLE`.

3. **SAFE**
   - `Manual fault` = `critical`
   - Set manual fault at the selected focus step.
   - Capture when Current State shows `SAFE`.

4. **RECOVER**
   - Keep `Manual fault` as `critical` at an earlier step.
   - Enable hysteresis.
   - Set `Recover hold steps` to a value > 1.
   - Move `Focus step` to immediately after SAFE clears and capture `RECOVER`.
