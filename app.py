from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MOCP Prototype MVP", layout="wide")

# Thresholds for the baseline rule-based policy.
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

APP_VALUE_PROP = (
    "Client preview environment for evaluating onboard safety-state behavior, "
    "operational explainability, and policy stability under constrained conditions."
)

README_TEXT = """
# Managed Onboard Compute Payload (MOCP) Prototype MVP

## Client-Facing Capabilities
- Live mission-scenario simulation for power/thermal and eclipse constraints.
- Fault injection controls (`none`, `minor`, `critical`) + random event rates.
- Dual policy evaluation:
  - `rule_based`: explicit threshold policy
  - `risk_scored`: weighted-factor policy
- State machine observability (`NOMINAL`, `THROTTLE`, `SAFE`, `RECOVER`) with explanation traces.
- Monte Carlo experiment lab to quantify stability and switching behavior.
- Exportable telemetry and experiment CSV for customer analysis workflows.
- Separate onboarding page for guided first-time walkthrough.

## Run Locally (macOS)
```bash
pip install streamlit pandas numpy
streamlit run app.py
```
"""

PRESETS: Dict[str, Dict[str, object]] = {
    "Balanced Demo": {
        "steps": 240,
        "seed": 42,
        "noise_level": 3.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 0.5,
        "manual_fault": "none",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 5,
        "policy_mode": "rule_based",
    },
    "Nominal Operations": {
        "steps": 240,
        "seed": 7,
        "noise_level": 2.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 0.0,
        "manual_fault": "none",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 5,
        "policy_mode": "rule_based",
    },
    "Throttle Response": {
        "steps": 240,
        "seed": 9,
        "noise_level": 3.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 0.2,
        "manual_fault": "minor",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 5,
        "policy_mode": "rule_based",
    },
    "Safe Mode Trigger": {
        "steps": 240,
        "seed": 11,
        "noise_level": 3.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 0.0,
        "manual_fault": "critical",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 5,
        "policy_mode": "rule_based",
    },
    "Recovery Sequence": {
        "steps": 240,
        "seed": 12,
        "noise_level": 3.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 0.0,
        "manual_fault": "critical",
        "manual_fault_step": 80,
        "use_hysteresis": True,
        "min_dwell_steps": 5,
        "recover_hold_steps": 8,
        "policy_mode": "rule_based",
    },
    "Stress Fault Storm": {
        "steps": 240,
        "seed": 21,
        "noise_level": 4.0,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 3.0,
        "manual_fault": "none",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 5,
        "policy_mode": "rule_based",
    },
    "Risk Policy Demo": {
        "steps": 240,
        "seed": 31,
        "noise_level": 3.5,
        "enable_eclipse": True,
        "eclipse_period": 90,
        "eclipse_duration": 35,
        "random_fault_rate": 1.2,
        "manual_fault": "minor",
        "manual_fault_step": 120,
        "use_hysteresis": True,
        "min_dwell_steps": 4,
        "recover_hold_steps": 6,
        "policy_mode": "risk_scored",
    },
}


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
    policy_mode: str


def ensure_state_defaults() -> None:
    if "preset_name" not in st.session_state:
        st.session_state["preset_name"] = "Balanced Demo"
    if "focus_step" not in st.session_state:
        st.session_state["focus_step"] = 239
    if "tour_state_select" not in st.session_state:
        st.session_state["tour_state_select"] = "NOMINAL"
    if "app_page" not in st.session_state:
        st.session_state["app_page"] = "Mission Console"
    if "settings_loaded" not in st.session_state:
        apply_preset(st.session_state["preset_name"])
        st.session_state["settings_loaded"] = True


def apply_preset(preset_name: str) -> None:
    preset = PRESETS[preset_name]
    st.session_state["sim_steps"] = int(preset["steps"])
    st.session_state["sim_seed"] = int(preset["seed"])
    st.session_state["sim_noise"] = float(preset["noise_level"])
    st.session_state["sim_enable_eclipse"] = bool(preset["enable_eclipse"])
    st.session_state["sim_eclipse_period"] = int(preset["eclipse_period"])
    st.session_state["sim_eclipse_duration"] = int(preset["eclipse_duration"])
    st.session_state["sim_manual_fault"] = str(preset["manual_fault"])
    st.session_state["sim_manual_fault_step"] = int(preset["manual_fault_step"])
    st.session_state["sim_random_fault_rate"] = float(preset["random_fault_rate"])
    st.session_state["sim_use_hysteresis"] = bool(preset["use_hysteresis"])
    st.session_state["sim_min_dwell"] = int(preset["min_dwell_steps"])
    st.session_state["sim_recover_hold"] = int(preset["recover_hold_steps"])
    st.session_state["sim_policy_mode"] = str(preset["policy_mode"])
    st.session_state["focus_step"] = min(st.session_state["sim_steps"] - 1, int(preset["manual_fault_step"]))


def simulate_telemetry(cfg: SimConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)
    steps = np.arange(cfg.steps)

    timestamps = pd.Timestamp("2026-01-01 00:00:00") + pd.to_timedelta(steps, unit="m")

    eclipse = np.zeros(cfg.steps, dtype=bool)
    if cfg.enable_eclipse:
        eclipse_phase = steps % max(cfg.eclipse_period, 1)
        eclipse = eclipse_phase < cfg.eclipse_duration

    power_wave = 120.0 + 16.0 * np.sin(2 * np.pi * steps / 70.0)
    temp_wave = 24.0 + 4.5 * np.sin(2 * np.pi * steps / 95.0 + 0.7)

    noise_power = rng.normal(0.0, cfg.noise_level, size=cfg.steps)
    noise_temp = rng.normal(0.0, cfg.noise_level * 0.25, size=cfg.steps)

    power = np.clip(power_wave + noise_power - 42.0 * eclipse.astype(float), 0.0, None)
    temp = temp_wave + noise_temp - 7.5 * eclipse.astype(float)

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
            fault_rows.append(
                {
                    "step": step,
                    "timestamp": row["timestamp"],
                    "severity": severity,
                    "fault_label": rng.choice(FAULT_LABELS[severity]),
                    "source": "random",
                }
            )

    if cfg.manual_fault != "none":
        step = int(np.clip(cfg.manual_fault_step, 0, cfg.steps - 1))
        step_time = telemetry.loc[telemetry["step"] == step, "timestamp"].iloc[0]
        fault_rows.append(
            {
                "step": step,
                "timestamp": step_time,
                "severity": cfg.manual_fault,
                "fault_label": rng.choice(FAULT_LABELS[cfg.manual_fault]),
                "source": "manual",
            }
        )

    if not fault_rows:
        return pd.DataFrame(columns=["step", "timestamp", "severity", "fault_label", "source"])

    return (
        pd.DataFrame(fault_rows)
        .sort_values(["step", "source", "fault_label"], ascending=[True, True, True])
        .reset_index(drop=True)
    )


def evaluate_desired_state_rule(
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
            f"temp {temp_c:.1f}C outside NOMINAL range [{NOMINAL_TEMP_RANGE[0]:.1f}, {NOMINAL_TEMP_RANGE[1]:.1f}]"
        )
    if has_minor or throttle_power_hit or throttle_temp_hit:
        return "THROTTLE", reasons

    return "NOMINAL", ["all checks within nominal bounds"]


def evaluate_desired_state_risk(
    power_watts: float,
    temp_c: float,
    step_faults: pd.DataFrame,
) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    score = 0.0

    has_critical = not step_faults[step_faults["severity"] == "critical"].empty
    has_minor = not step_faults[step_faults["severity"] == "minor"].empty

    safe_temp_hit = temp_c < SAFE_TEMP_RANGE[0] or temp_c > SAFE_TEMP_RANGE[1]
    throttle_temp_hit = temp_c < NOMINAL_TEMP_RANGE[0] or temp_c > NOMINAL_TEMP_RANGE[1]

    safe_power_hit = power_watts < SAFE_PWR
    throttle_power_hit = power_watts < THROTTLE_PWR

    if has_critical:
        score += 4.0
        reasons.append("critical fault +4.0")
    if has_minor:
        score += 1.5
        reasons.append("minor fault +1.5")

    if safe_power_hit:
        score += 3.0
        reasons.append("SAFE power breach +3.0")
    elif throttle_power_hit:
        score += 1.5
        reasons.append("THROTTLE power breach +1.5")

    if safe_temp_hit:
        score += 3.0
        reasons.append("SAFE temp breach +3.0")
    elif throttle_temp_hit:
        score += 1.5
        reasons.append("THROTTLE temp breach +1.5")

    reasons.append(f"risk_score={score:.1f}")

    if score >= 4.0:
        return "SAFE", reasons
    if score >= 1.5:
        return "THROTTLE", reasons
    return "NOMINAL", reasons


def evaluate_desired_state(
    power_watts: float,
    temp_c: float,
    step_faults: pd.DataFrame,
    policy_mode: str,
) -> Tuple[str, List[str]]:
    if policy_mode == "risk_scored":
        return evaluate_desired_state_risk(power_watts, temp_c, step_faults)
    return evaluate_desired_state_rule(power_watts, temp_c, step_faults)


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
            policy_mode=cfg.policy_mode,
        )
        reasons = [f"policy={cfg.policy_mode}"] + reasons

        candidate_state = desired_state

        if desired_state == "SAFE":
            candidate_state = "SAFE"
        elif current_state == "SAFE":
            candidate_state = "RECOVER"
            reasons.append("SAFE cleared, entering RECOVER")
        elif current_state == "RECOVER":
            if recover_progress < cfg.recover_hold_steps:
                candidate_state = "RECOVER"
                reasons.append(f"RECOVER hold {recover_progress}/{cfg.recover_hold_steps}")
            else:
                candidate_state = desired_state

        if (
            cfg.use_hysteresis
            and candidate_state != current_state
            and candidate_state != "SAFE"
            and dwell_steps < cfg.min_dwell_steps
        ):
            reasons.append(f"hysteresis hold: dwell {dwell_steps}/{cfg.min_dwell_steps}")
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
            recover_progress = 1 if current_state == "RECOVER" else 0
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
        pd.DataFrame(timeline_events).sort_values(["step", "event_kind"]).reset_index(drop=True)
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


def state_segments(states: pd.Series) -> pd.DataFrame:
    segments: List[Dict[str, object]] = []
    if states.empty:
        return pd.DataFrame(columns=["state", "start_step", "end_step", "duration_steps"])

    start = 0
    cur = str(states.iloc[0])
    for idx in range(1, len(states)):
        nxt = str(states.iloc[idx])
        if nxt != cur:
            segments.append(
                {
                    "state": cur,
                    "start_step": start,
                    "end_step": idx - 1,
                    "duration_steps": idx - start,
                }
            )
            cur = nxt
            start = idx
    segments.append(
        {
            "state": cur,
            "start_step": start,
            "end_step": len(states) - 1,
            "duration_steps": len(states) - start,
        }
    )
    return pd.DataFrame(segments)


def compute_run_metrics(
    telemetry: pd.DataFrame,
    transitions: pd.DataFrame,
    timeline: pd.DataFrame,
) -> Dict[str, float]:
    total_steps = len(telemetry)
    total_hours = max(total_steps / 60.0, 1e-9)
    counts = telemetry["state"].value_counts().to_dict()
    fault_count = int((timeline["event_kind"] == "fault").sum()) if not timeline.empty else 0

    seg = state_segments(telemetry["state"])
    safe_seg = seg[seg["state"] == "SAFE"]

    metrics: Dict[str, float] = {
        "steps": float(total_steps),
        "fault_events": float(fault_count),
        "transitions": float(len(transitions)),
        "transitions_per_hour": float(len(transitions) / total_hours),
        "nominal_pct": 100.0 * float(counts.get("NOMINAL", 0)) / max(total_steps, 1),
        "throttle_pct": 100.0 * float(counts.get("THROTTLE", 0)) / max(total_steps, 1),
        "safe_pct": 100.0 * float(counts.get("SAFE", 0)) / max(total_steps, 1),
        "recover_pct": 100.0 * float(counts.get("RECOVER", 0)) / max(total_steps, 1),
        "safe_segments": float(len(safe_seg)),
        "safe_mean_duration_steps": float(safe_seg["duration_steps"].mean()) if not safe_seg.empty else 0.0,
        "power_min": float(telemetry["power_watts"].min()),
        "power_max": float(telemetry["power_watts"].max()),
        "temp_min": float(telemetry["temp_c"].min()),
        "temp_max": float(telemetry["temp_c"].max()),
        "flapping_index": float(len(transitions) / max(fault_count + 1, 1)),
    }
    return metrics


def find_state_steps(telemetry: pd.DataFrame) -> Dict[str, Optional[int]]:
    out: Dict[str, Optional[int]] = {}
    for state in ["NOMINAL", "THROTTLE", "SAFE", "RECOVER"]:
        rows = telemetry[telemetry["state"] == state]
        out[state] = int(rows.iloc[0]["step"]) if not rows.empty else None
    return out


def onboarding_steps_df() -> pd.DataFrame:
    rows = [
        {
            "step": 1,
            "action": "Open onboarding overview",
            "outcome": "Introduces scenario workflow and expected outcomes.",
        },
        {
            "step": 2,
            "action": "Choose scenario preset",
            "outcome": "Loads stable baseline settings for reproducible runs.",
        },
        {
            "step": 3,
            "action": "Run simulator and inspect state transitions",
            "outcome": "Explains why state changes happen and when safety escalates.",
        },
        {
            "step": 4,
            "action": "Use experiment lab",
            "outcome": "Compares policy modes and hysteresis impact across many seeds.",
        },
        {
            "step": 5,
            "action": "Export CSV artifacts",
            "outcome": "Generates evidence for customer review and pilot discussions.",
        },
    ]
    return pd.DataFrame(rows)


def make_combined_export(telemetry: pd.DataFrame, timeline: pd.DataFrame) -> pd.DataFrame:
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

    return (
        pd.concat([telemetry_out[base_cols], event_out[base_cols]], ignore_index=True)
        .sort_values(["step", "record_type"])
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def run_experiment_grid(
    seeds: int,
    steps: int,
    noise_level: float,
    random_fault_rate: float,
    manual_fault: str,
    manual_fault_step: int,
    min_dwell_steps: int,
    recover_hold_steps: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows: List[Dict[str, object]] = []
    for policy_mode in ["rule_based", "risk_scored"]:
        for use_hysteresis in [False, True]:
            for seed in range(1, seeds + 1):
                cfg = SimConfig(
                    steps=steps,
                    seed=seed,
                    noise_level=noise_level,
                    enable_eclipse=True,
                    eclipse_period=90,
                    eclipse_duration=35,
                    random_fault_rate=random_fault_rate,
                    manual_fault=manual_fault,
                    manual_fault_step=manual_fault_step,
                    use_hysteresis=use_hysteresis,
                    min_dwell_steps=min_dwell_steps,
                    recover_hold_steps=recover_hold_steps,
                    policy_mode=policy_mode,
                )
                telemetry = simulate_telemetry(cfg)
                faults = generate_faults(cfg, telemetry)
                telemetry, transitions, timeline = run_state_machine(telemetry, faults, cfg)
                metrics = compute_run_metrics(telemetry, transitions, timeline)
                rows.append(
                    {
                        "seed": seed,
                        "policy_mode": policy_mode,
                        "use_hysteresis": use_hysteresis,
                        **metrics,
                    }
                )

    raw = pd.DataFrame(rows)
    summary = (
        raw.groupby(["policy_mode", "use_hysteresis"])
        .agg(
            runs=("seed", "count"),
            transitions_avg=("transitions", "mean"),
            fault_events_avg=("fault_events", "mean"),
            nominal_pct_avg=("nominal_pct", "mean"),
            throttle_pct_avg=("throttle_pct", "mean"),
            safe_pct_avg=("safe_pct", "mean"),
            recover_pct_avg=("recover_pct", "mean"),
            flapping_index_avg=("flapping_index", "mean"),
        )
        .reset_index()
    )

    # Relative improvement vs no hysteresis per policy.
    summary["transition_reduction_vs_no_hyst_pct"] = np.nan
    for policy in summary["policy_mode"].unique():
        subset = summary[summary["policy_mode"] == policy]
        base = subset[subset["use_hysteresis"] == False]["transitions_avg"]
        if base.empty:
            continue
        base_val = float(base.iloc[0])
        if base_val <= 0:
            continue
        for idx in subset.index:
            cur = float(summary.loc[idx, "transitions_avg"])
            summary.loc[idx, "transition_reduction_vs_no_hyst_pct"] = 100.0 * (base_val - cur) / base_val

    return raw, summary


def state_badge(state: str) -> str:
    color = STATE_COLORS.get(state, "#333333")
    return f"""
    <div style="padding: 18px; border-radius: 10px; background: {color}; color: white; text-align: center;">
        <div style="font-size: 14px; opacity: 0.9;">Current State</div>
        <div style="font-size: 36px; font-weight: 700; letter-spacing: 1px;">{state}</div>
    </div>
    """


def render_onboarding_page() -> None:
    st.subheader("Client Onboarding")
    st.write(
        "Use this page to review workflow steps, then switch to the mission console for scenario runs."
    )

    st.markdown("**Onboarding Workflow**")
    st.dataframe(onboarding_steps_df(), use_container_width=True, height=260)
    st.markdown("**Quick Start**")
    st.write("1. Switch page to `Mission Console` from the sidebar.")
    st.write("2. Apply `Balanced Demo` and inspect transitions in `Live Simulator`.")
    st.write("3. Run Monte Carlo in `Experiment Lab` and export results.")

    if st.button("Open Mission Console", key="open_console_button"):
        st.session_state["app_page"] = "Mission Console"
        st.rerun()


def main() -> None:
    ensure_state_defaults()

    st.title("Managed Onboard Compute Payload (MOCP) - Prototype MVP")
    st.caption(APP_VALUE_PROP)

    with st.sidebar:
        st.header("Navigation")
        st.radio("Page", options=["Mission Console", "Client Onboarding"], key="app_page")

        if st.session_state["app_page"] == "Mission Console":
            st.divider()
            st.header("Scenario Presets")
            preset_name = st.selectbox("Preset", options=list(PRESETS.keys()), key="preset_name")
            if st.button("Apply Selected Preset"):
                apply_preset(preset_name)
                st.rerun()

            st.divider()
            st.header("Simulation Controls")
            st.slider("Simulation length (steps)", min_value=60, max_value=720, step=10, key="sim_steps")
            st.number_input("Random seed", min_value=0, max_value=10000, step=1, key="sim_seed")
            st.slider("Noise level", min_value=0.0, max_value=20.0, step=0.5, key="sim_noise")

            st.subheader("Eclipse")
            st.checkbox("Enable eclipse cycle", key="sim_enable_eclipse")
            st.slider("Eclipse period (steps)", min_value=30, max_value=180, step=5, key="sim_eclipse_period")
            st.slider("Eclipse duration (steps)", min_value=5, max_value=80, step=1, key="sim_eclipse_duration")

            st.subheader("Fault Injection")
            st.selectbox("Manual fault", options=["none", "minor", "critical"], key="sim_manual_fault")
            if st.session_state["sim_manual_fault_step"] > st.session_state["sim_steps"] - 1:
                st.session_state["sim_manual_fault_step"] = st.session_state["sim_steps"] - 1
            st.slider(
                "Manual fault step",
                min_value=0,
                max_value=st.session_state["sim_steps"] - 1,
                step=1,
                key="sim_manual_fault_step",
            )
            st.slider(
                "Random fault rate (faults/hour)",
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                key="sim_random_fault_rate",
            )

            st.subheader("Policy + Stability")
            st.selectbox(
                "Policy mode",
                options=["rule_based", "risk_scored"],
                key="sim_policy_mode",
                help="rule_based uses explicit thresholds; risk_scored uses weighted risk factors.",
            )
            st.checkbox("Use hysteresis / minimum dwell", key="sim_use_hysteresis")
            st.slider("Min dwell steps", min_value=1, max_value=30, step=1, key="sim_min_dwell")
            st.slider("Recover hold steps", min_value=1, max_value=30, step=1, key="sim_recover_hold")
        else:
            st.divider()
            st.caption("Complete onboarding first, then switch to Mission Console.")

    if st.session_state["app_page"] == "Client Onboarding":
        render_onboarding_page()
        return

    cfg = SimConfig(
        steps=int(st.session_state["sim_steps"]),
        seed=int(st.session_state["sim_seed"]),
        noise_level=float(st.session_state["sim_noise"]),
        enable_eclipse=bool(st.session_state["sim_enable_eclipse"]),
        eclipse_period=int(st.session_state["sim_eclipse_period"]),
        eclipse_duration=int(st.session_state["sim_eclipse_duration"]),
        random_fault_rate=float(st.session_state["sim_random_fault_rate"]),
        manual_fault=str(st.session_state["sim_manual_fault"]),
        manual_fault_step=int(st.session_state["sim_manual_fault_step"]),
        use_hysteresis=bool(st.session_state["sim_use_hysteresis"]),
        min_dwell_steps=int(st.session_state["sim_min_dwell"]),
        recover_hold_steps=int(st.session_state["sim_recover_hold"]),
        policy_mode=str(st.session_state["sim_policy_mode"]),
    )

    telemetry = simulate_telemetry(cfg)
    faults = generate_faults(cfg, telemetry)
    telemetry, transitions, timeline = run_state_machine(telemetry, faults, cfg)
    state_steps = find_state_steps(telemetry)
    if st.session_state["focus_step"] > cfg.steps - 1:
        st.session_state["focus_step"] = cfg.steps - 1

    tab_sim, tab_exp = st.tabs(["Live Simulator", "Experiment Lab"])

    with tab_sim:
        jump_cols = st.columns([2, 1])
        with jump_cols[0]:
            st.write("Quick Jump (state focus targets)")
            st.selectbox(
                "State target",
                options=["NOMINAL", "THROTTLE", "SAFE", "RECOVER"],
                key="tour_state_select",
            )
        with jump_cols[1]:
            if st.button("Jump To Target Step"):
                target = state_steps.get(st.session_state["tour_state_select"])
                if target is not None:
                    st.session_state["focus_step"] = int(target)
                    st.rerun()
                else:
                    st.warning("This state was not reached in the current run.")

        st.slider(
            "Focus step (for inspection)",
            min_value=0,
            max_value=cfg.steps - 1,
            step=1,
            key="focus_step",
        )
        current = telemetry.iloc[int(st.session_state["focus_step"])]

        left, right = st.columns([1, 2])
        with left:
            st.markdown(state_badge(str(current["state"])), unsafe_allow_html=True)
            st.caption(f"Step {int(current['step'])} | Time {current['timestamp']} | Eclipse={bool(current['eclipse'])}")
            st.metric("Power (W)", f"{current['power_watts']:.1f}")
            st.metric("Temp (C)", f"{current['temp_c']:.1f}")

        with right:
            st.subheader("Why am I in this state?")
            for idx, reason in enumerate(str(current["active_rules"]).split("; "), start=1):
                if reason.strip():
                    st.write(f"{idx}. {reason.strip()}")

        m = compute_run_metrics(telemetry, transitions, timeline)
        metric_cols = st.columns(6)
        metric_cols[0].metric("Fault Events", f"{int(m['fault_events'])}")
        metric_cols[1].metric("Transitions", f"{int(m['transitions'])}")
        metric_cols[2].metric("Transitions/Hour", f"{m['transitions_per_hour']:.1f}")
        metric_cols[3].metric("SAFE %", f"{m['safe_pct']:.1f}%")
        metric_cols[4].metric("RECOVER %", f"{m['recover_pct']:.1f}%")
        metric_cols[5].metric("Flapping Index", f"{m['flapping_index']:.2f}")

        st.subheader("Telemetry")
        st.line_chart(telemetry.set_index("step")[["power_watts", "temp_c"]], height=300)

        st.subheader("State Timeline (table view)")
        st.dataframe(
            telemetry[["step", "timestamp", "state", "power_watts", "temp_c", "eclipse"]],
            use_container_width=True,
            height=250,
        )

        st.subheader("Event Log")
        last_n = st.slider("Show last N events", min_value=5, max_value=200, value=25, step=5)
        if timeline.empty:
            st.info("No faults or state transitions were generated for this run.")
        else:
            tagged = timeline.copy()
            tagged["severity_tag"] = tagged["severity"].apply(lambda x: f"[{x}]")
            st.dataframe(tagged.tail(last_n), use_container_width=True, height=250)

        st.subheader("State Transition Log")
        if transitions.empty:
            st.info("No state transitions occurred in this run.")
        else:
            st.dataframe(transitions, use_container_width=True, height=220)

        combined_export = make_combined_export(telemetry, timeline)
        st.download_button(
            "Download telemetry + events CSV",
            data=combined_export.to_csv(index=False).encode("utf-8"),
            file_name="mocp_sim_export.csv",
            mime="text/csv",
        )

    with tab_exp:
        st.subheader("Monte Carlo Experiment Lab")
        st.caption(
            "Runs repeated seeded simulations across policy modes and hysteresis settings to quantify stability and safety behavior."
        )
        exp_cols = st.columns(4)
        exp_seeds = exp_cols[0].slider("Seeds", min_value=10, max_value=200, value=60, step=10)
        exp_steps = exp_cols[1].slider("Steps/Run", min_value=120, max_value=480, value=240, step=20)
        exp_noise = exp_cols[2].slider("Noise", min_value=1.0, max_value=8.0, value=3.5, step=0.5)
        exp_rate = exp_cols[3].slider("Faults/Hour", min_value=0.0, max_value=5.0, value=1.2, step=0.1)

        exp_cols2 = st.columns(4)
        exp_manual_fault = exp_cols2[0].selectbox("Manual fault for all runs", ["none", "minor", "critical"], index=1)
        exp_manual_step = exp_cols2[1].slider("Manual fault step", min_value=0, max_value=exp_steps - 1, value=exp_steps // 2, step=1)
        exp_dwell = exp_cols2[2].slider("Min dwell", min_value=1, max_value=12, value=4, step=1)
        exp_recover = exp_cols2[3].slider("Recover hold", min_value=1, max_value=12, value=5, step=1)

        run_now = st.button("Run Monte Carlo")
        if run_now:
            raw, summary = run_experiment_grid(
                seeds=exp_seeds,
                steps=exp_steps,
                noise_level=exp_noise,
                random_fault_rate=exp_rate,
                manual_fault=exp_manual_fault,
                manual_fault_step=exp_manual_step,
                min_dwell_steps=exp_dwell,
                recover_hold_steps=exp_recover,
            )

            st.success(f"Completed {len(raw)} runs ({exp_seeds} seeds x 2 policies x 2 hysteresis settings).")
            st.dataframe(summary, use_container_width=True, height=220)

            chart = summary.copy()
            chart["mode"] = chart["policy_mode"] + " | hyst=" + chart["use_hysteresis"].astype(str)
            chart = chart.set_index("mode")
            st.bar_chart(chart[["transitions_avg", "safe_pct_avg", "flapping_index_avg"]], height=300)

            st.download_button(
                "Download experiment raw CSV",
                data=raw.to_csv(index=False).encode("utf-8"),
                file_name="mocp_experiment_raw.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download experiment summary CSV",
                data=summary.to_csv(index=False).encode("utf-8"),
                file_name="mocp_experiment_summary.csv",
                mime="text/csv",
            )

            best_rows = summary.sort_values("transitions_avg").head(1)
            if not best_rows.empty:
                best = best_rows.iloc[0]
                st.info(
                    "Lowest transition regime in this run: "
                    f"policy={best['policy_mode']}, hysteresis={best['use_hysteresis']}, "
                    f"avg_transitions={best['transitions_avg']:.2f}"
                )
        else:
            st.info("Click 'Run Monte Carlo' to generate experiment metrics.")

        st.subheader("Client Documentation")
        with st.expander("Platform Notes", expanded=False):
            st.markdown(README_TEXT)


if __name__ == "__main__":
    main()
