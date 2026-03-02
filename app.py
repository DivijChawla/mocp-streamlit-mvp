from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MOCP Prototype MVP", layout="wide")

SAFE_TEMP_RANGE = (-5.0, 45.0)
NOMINAL_TEMP_RANGE = (5.0, 35.0)
THROTTLE_PWR = 90.0
SAFE_PWR = 60.0

FAULT_LABELS = {
    "minor": ["sensor_dropout", "bitflip"],
    "critical": ["watchdog_timeout"],
}

STATE_COLORS = {
    "NOMINAL": "#1f7a1f",
    "THROTTLE": "#b87400",
    "SAFE": "#a32020",
    "RECOVER": "#005f8f",
}

README_TEXT = """
# Managed Onboard Compute Payload (MOCP) Prototype MVP

## What Is Simulated
- Simple synthetic telemetry: `power_watts` and `temp_c` with periodic behavior + noise.
- Eclipse effect that lowers power and cools temperature.
- Fault labels with configurable random rate and manual injection.
- A deterministic safety state machine: `NOMINAL`, `THROTTLE`, `SAFE`, `RECOVER`.

## Run Locally (macOS)
```bash
pip install streamlit pandas numpy
streamlit run app.py
```

## Reproducing 4 Screenshots For a Report
1. **NOMINAL**
   - Set `Manual fault` = `none`.
   - Set `Random fault rate` = `0.0 faults/hour`.
   - Keep eclipse enabled and moderate noise.
   - Pick a focus step where power and temperature are within nominal bounds.

2. **THROTTLE**
   - Set `Manual fault` = `minor` near the focus step.
   - Or increase `Random fault rate` so a minor fault appears.
   - Capture when state indicator shows `THROTTLE`.

3. **SAFE**
   - Set `Manual fault` = `critical` at the focus step.
   - Capture when state indicator shows `SAFE`.

4. **RECOVER**
   - Keep `Manual fault` = `critical` at an earlier step.
   - Enable hysteresis and set `Recover hold steps` > 1.
   - Move focus to just after SAFE clears; capture when indicator shows `RECOVER`.
"""


@dataclass
class SimConfig:
    steps: int
    seed: int
    noise_level: float
    enable_eclipse: bool
    eclipse_period: int
    eclipse_duration: int
    random_fault_rate: float
    manual_fault: str
    manual_fault_step: int
    use_hysteresis: bool
    min_dwell_steps: int
    recover_hold_steps: int


def simulate_telemetry(cfg: SimConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)
    steps = np.arange(cfg.steps)

    timestamps = (
        pd.Timestamp("2026-01-01 00:00:00")
        + pd.to_timedelta(steps, unit="m")
    )

    eclipse = np.zeros(cfg.steps, dtype=bool)
    if cfg.enable_eclipse:
        eclipse_phase = steps % max(cfg.eclipse_period, 1)
        eclipse = eclipse_phase < cfg.eclipse_duration

    power_wave = 120.0 + 16.0 * np.sin(2 * np.pi * steps / 70.0)
    temp_wave = 24.0 + 4.5 * np.sin(2 * np.pi * steps / 95.0 + 0.7)

    noise_power = rng.normal(0.0, cfg.noise_level, size=cfg.steps)
    noise_temp = rng.normal(0.0, cfg.noise_level * 0.25, size=cfg.steps)

    power = power_wave + noise_power
    temp = temp_wave + noise_temp

    power[eclipse] -= 42.0
    temp[eclipse] -= 7.5

    power = np.clip(power, 0.0, None)

    return pd.DataFrame(
        {
            "step": steps,
            "timestamp": timestamps,
            "elapsed_min": steps,
            "power_watts": power,
            "temp_c": temp,
            "eclipse": eclipse,
        }
    )


def generate_faults(cfg: SimConfig, telemetry: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed + 73)
    fault_rows: List[Dict[str, object]] = []

    step_hours = 1.0 / 60.0
    p_fault = min(max(cfg.random_fault_rate * step_hours, 0.0), 1.0)

    for _, row in telemetry.iterrows():
        step = int(row["step"])
        if rng.random() < p_fault:
            severity = "critical" if rng.random() < 0.25 else "minor"
            label = rng.choice(FAULT_LABELS[severity])
            fault_rows.append(
                {
                    "step": step,
                    "timestamp": row["timestamp"],
                    "severity": severity,
                    "fault_label": label,
                    "source": "random",
                }
            )

    if cfg.manual_fault != "none":
        step = int(np.clip(cfg.manual_fault_step, 0, cfg.steps - 1))
        step_time = telemetry.loc[telemetry["step"] == step, "timestamp"].iloc[0]
        label = rng.choice(FAULT_LABELS[cfg.manual_fault])
        fault_rows.append(
            {
                "step": step,
                "timestamp": step_time,
                "severity": cfg.manual_fault,
                "fault_label": label,
                "source": "manual",
            }
        )

    if not fault_rows:
        return pd.DataFrame(
            columns=["step", "timestamp", "severity", "fault_label", "source"]
        )

    return (
        pd.DataFrame(fault_rows)
        .sort_values(["step", "source", "fault_label"], ascending=[True, True, True])
        .reset_index(drop=True)
    )


def evaluate_desired_state(
    power_watts: float,
    temp_c: float,
    step_faults: pd.DataFrame,
) -> Tuple[str, List[str]]:
    reasons: List[str] = []

    has_critical = not step_faults[step_faults["severity"] == "critical"].empty
    has_minor = not step_faults[step_faults["severity"] == "minor"].empty

    safe_temp_hit = temp_c < SAFE_TEMP_RANGE[0] or temp_c > SAFE_TEMP_RANGE[1]
    throttle_temp_hit = temp_c < NOMINAL_TEMP_RANGE[0] or temp_c > NOMINAL_TEMP_RANGE[1]

    safe_power_hit = power_watts < SAFE_PWR
    throttle_power_hit = power_watts < THROTTLE_PWR

    if has_critical:
        reasons.append("critical fault present")
    if safe_power_hit:
        reasons.append(f"power {power_watts:.1f}W < SAFE_PWR {SAFE_PWR:.1f}W")
    if safe_temp_hit:
        reasons.append(
            f"temp {temp_c:.1f}C outside SAFE range [{SAFE_TEMP_RANGE[0]:.1f}, {SAFE_TEMP_RANGE[1]:.1f}]"
        )

    if has_critical or safe_power_hit or safe_temp_hit:
        return "SAFE", reasons

    if has_minor:
        reasons.append("minor fault present")
    if throttle_power_hit:
        reasons.append(f"power {power_watts:.1f}W < THROTTLE_PWR {THROTTLE_PWR:.1f}W")
    if throttle_temp_hit:
        reasons.append(
            "temp "
            f"{temp_c:.1f}C outside NOMINAL range "
            f"[{NOMINAL_TEMP_RANGE[0]:.1f}, {NOMINAL_TEMP_RANGE[1]:.1f}]"
        )

    if has_minor or throttle_power_hit or throttle_temp_hit:
        return "THROTTLE", reasons

    return "NOMINAL", ["all checks within nominal bounds"]


def run_state_machine(
    telemetry: pd.DataFrame,
    faults: pd.DataFrame,
    cfg: SimConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    faults_by_step = {k: v for k, v in faults.groupby("step")} if not faults.empty else {}

    current_state = "NOMINAL"
    dwell_steps = 1
    recover_progress = 0

    states: List[str] = []
    active_reason_text: List[str] = []
    transitions: List[Dict[str, object]] = []
    timeline_events: List[Dict[str, object]] = []

    for _, row in telemetry.iterrows():
        step = int(row["step"])
        step_faults = faults_by_step.get(step, pd.DataFrame(columns=faults.columns))

        for _, fault in step_faults.iterrows():
            sev = "CRITICAL" if fault["severity"] == "critical" else "WARN"
            timeline_events.append(
                {
                    "step": step,
                    "timestamp": fault["timestamp"],
                    "event_kind": "fault",
                    "severity": sev,
                    "from_state": "",
                    "to_state": "",
                    "fault_label": fault["fault_label"],
                    "reason": f"{fault['severity']} fault from {fault['source']}",
                }
            )

        desired_state, reasons = evaluate_desired_state(
            power_watts=float(row["power_watts"]),
            temp_c=float(row["temp_c"]),
            step_faults=step_faults,
        )

        candidate_state = desired_state

        if desired_state == "SAFE":
            candidate_state = "SAFE"
        elif current_state == "SAFE":
            candidate_state = "RECOVER"
            reasons.append("SAFE cleared, entering RECOVER")
        elif current_state == "RECOVER":
            if recover_progress < cfg.recover_hold_steps:
                candidate_state = "RECOVER"
                reasons.append(
                    f"RECOVER hold {recover_progress}/{cfg.recover_hold_steps}"
                )
            else:
                candidate_state = desired_state

        if (
            cfg.use_hysteresis
            and candidate_state != current_state
            and candidate_state != "SAFE"
            and dwell_steps < cfg.min_dwell_steps
        ):
            reasons.append(
                f"hysteresis hold: dwell {dwell_steps}/{cfg.min_dwell_steps}"
            )
            candidate_state = current_state

        if candidate_state != current_state:
            severity = {
                "SAFE": "CRITICAL",
                "THROTTLE": "WARN",
                "RECOVER": "INFO",
                "NOMINAL": "INFO",
            }[candidate_state]

            transitions.append(
                {
                    "step": step,
                    "timestamp": row["timestamp"],
                    "from_state": current_state,
                    "to_state": candidate_state,
                    "severity": severity,
                    "reason": "; ".join(reasons),
                }
            )

            timeline_events.append(
                {
                    "step": step,
                    "timestamp": row["timestamp"],
                    "event_kind": "state_transition",
                    "severity": severity,
                    "from_state": current_state,
                    "to_state": candidate_state,
                    "fault_label": "",
                    "reason": "; ".join(reasons),
                }
            )

            current_state = candidate_state
            dwell_steps = 1

            if current_state == "RECOVER":
                recover_progress = 1
            else:
                recover_progress = 0
        else:
            dwell_steps += 1
            if current_state == "RECOVER":
                recover_progress += 1

        states.append(current_state)
        active_reason_text.append("; ".join(reasons))

    out = telemetry.copy()
    out["state"] = states
    out["active_rules"] = active_reason_text

    transitions_df = pd.DataFrame(transitions)
    timeline_df = (
        pd.DataFrame(timeline_events)
        .sort_values(["step", "event_kind"])
        .reset_index(drop=True)
        if timeline_events
        else pd.DataFrame(
            columns=[
                "step",
                "timestamp",
                "event_kind",
                "severity",
                "from_state",
                "to_state",
                "fault_label",
                "reason",
            ]
        )
    )

    return out, transitions_df, timeline_df


def make_combined_export(
    telemetry: pd.DataFrame,
    timeline: pd.DataFrame,
) -> pd.DataFrame:
    base_cols = [
        "record_type",
        "step",
        "timestamp",
        "elapsed_min",
        "power_watts",
        "temp_c",
        "eclipse",
        "state",
        "event_kind",
        "severity",
        "from_state",
        "to_state",
        "fault_label",
        "reason",
        "active_rules",
    ]

    telemetry_out = telemetry.copy()
    telemetry_out["record_type"] = "telemetry"
    telemetry_out["event_kind"] = ""
    telemetry_out["severity"] = ""
    telemetry_out["from_state"] = ""
    telemetry_out["to_state"] = ""
    telemetry_out["fault_label"] = ""
    telemetry_out["reason"] = ""

    if timeline.empty:
        return telemetry_out[base_cols].copy()

    event_out = timeline.merge(
        telemetry[["step", "elapsed_min", "power_watts", "temp_c", "eclipse", "state", "active_rules"]],
        on="step",
        how="left",
    )
    event_out["record_type"] = "event"

    combined = pd.concat(
        [telemetry_out[base_cols], event_out[base_cols]],
        ignore_index=True,
    ).sort_values(["step", "record_type"]).reset_index(drop=True)

    return combined


def state_badge(state: str) -> str:
    color = STATE_COLORS.get(state, "#333333")
    return f"""
    <div style="padding: 18px; border-radius: 10px; background: {color}; color: white; text-align: center;">
        <div style="font-size: 14px; opacity: 0.9;">Current State</div>
        <div style="font-size: 36px; font-weight: 700; letter-spacing: 1px;">{state}</div>
    </div>
    """


def main() -> None:
    st.title("Managed Onboard Compute Payload (MOCP) - Prototype MVP")

    with st.sidebar:
        st.header("Simulation Controls")
        steps = st.slider("Simulation length (steps)", min_value=60, max_value=720, value=240, step=10)
        seed = st.number_input("Random seed", min_value=0, max_value=10_000, value=42, step=1)
        noise = st.slider("Noise level", min_value=0.0, max_value=20.0, value=3.0, step=0.5)

        st.subheader("Eclipse")
        enable_eclipse = st.checkbox("Enable eclipse cycle", value=True)
        eclipse_period = st.slider("Eclipse period (steps)", 30, 180, 90, 5)
        eclipse_duration = st.slider("Eclipse duration (steps)", 5, 80, 35, 1)

        st.subheader("Fault Injection")
        manual_fault = st.selectbox("Manual fault", options=["none", "minor", "critical"], index=0)
        manual_fault_step = st.slider("Manual fault step", min_value=0, max_value=steps - 1, value=min(steps - 1, 120), step=1)
        random_fault_rate = st.slider(
            "Random fault rate (faults/hour)", min_value=0.0, max_value=5.0, value=0.5, step=0.1
        )

        st.subheader("Stability")
        use_hysteresis = st.checkbox("Use hysteresis / minimum dwell", value=True)
        min_dwell = st.slider("Min dwell steps", min_value=1, max_value=30, value=4, step=1)
        recover_hold = st.slider("Recover hold steps", min_value=1, max_value=30, value=5, step=1)

    cfg = SimConfig(
        steps=steps,
        seed=int(seed),
        noise_level=noise,
        enable_eclipse=enable_eclipse,
        eclipse_period=eclipse_period,
        eclipse_duration=eclipse_duration,
        random_fault_rate=random_fault_rate,
        manual_fault=manual_fault,
        manual_fault_step=manual_fault_step,
        use_hysteresis=use_hysteresis,
        min_dwell_steps=min_dwell,
        recover_hold_steps=recover_hold,
    )

    telemetry = simulate_telemetry(cfg)
    faults = generate_faults(cfg, telemetry)
    telemetry, transitions, timeline = run_state_machine(telemetry, faults, cfg)

    focus_step = st.slider("Focus step (for inspection/screenshots)", 0, steps - 1, steps - 1, 1)
    current = telemetry.iloc[focus_step]

    left, right = st.columns([1, 2])
    with left:
        st.markdown(state_badge(current["state"]), unsafe_allow_html=True)
        st.caption(
            f"Step {int(current['step'])} | Time {current['timestamp']} | Eclipse={bool(current['eclipse'])}"
        )
        st.metric("Power (W)", f"{current['power_watts']:.1f}")
        st.metric("Temp (C)", f"{current['temp_c']:.1f}")

    with right:
        st.subheader("Why am I in this state?")
        for idx, reason in enumerate(str(current["active_rules"]).split("; "), start=1):
            if reason.strip():
                st.write(f"{idx}. {reason.strip()}")

    st.subheader("Telemetry")
    st.line_chart(
        telemetry.set_index("step")[["power_watts", "temp_c"]],
        height=300,
    )

    st.subheader("State Timeline (table view)")
    timeline_view = telemetry[["step", "timestamp", "state", "power_watts", "temp_c", "eclipse"]].copy()
    st.dataframe(timeline_view, use_container_width=True, height=250)

    st.subheader("Event Log")
    last_n = st.slider("Show last N events", min_value=5, max_value=200, value=25, step=5)

    if timeline.empty:
        st.info("No faults or state transitions were generated for this run.")
    else:
        tagged = timeline.copy()
        tagged["severity_tag"] = tagged["severity"].apply(lambda x: f"[{x}]")
        st.dataframe(tagged.tail(last_n), use_container_width=True, height=260)

    st.subheader("Timeline View (all events, sorted by time)")
    if timeline.empty:
        st.info("No timeline events to display.")
    else:
        tagged_full = timeline.copy()
        tagged_full["severity_tag"] = tagged_full["severity"].apply(lambda x: f"[{x}]")
        st.dataframe(tagged_full, use_container_width=True, height=260)

    st.subheader("State Transition Log")
    if transitions.empty:
        st.info("No state transitions occurred in this run.")
    else:
        st.dataframe(transitions, use_container_width=True, height=220)

    combined_export = make_combined_export(telemetry, timeline)
    csv_bytes = combined_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download telemetry + events CSV",
        data=csv_bytes,
        file_name="mocp_sim_export.csv",
        mime="text/csv",
    )

    with st.expander("README / Usage Notes", expanded=False):
        st.markdown(README_TEXT)


if __name__ == "__main__":
    main()
