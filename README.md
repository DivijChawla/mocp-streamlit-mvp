# MOCP Client Preview

Live app: https://mocp--mvp.streamlit.app

## What this app is for
This is a client-facing preview environment for evaluating operational safety-state behavior under constrained conditions.

Core states:
- `NOMINAL`
- `THROTTLE`
- `SAFE`
- `RECOVER`

## Key capabilities
- Synthetic telemetry for `power_watts` and `temp_c` with periodic behavior and configurable noise.
- Eclipse cycle model that changes power and thermal behavior.
- Fault injection:
  - manual: `none`, `minor`, `critical`
  - random rate: `0-5 faults/hour`
- Dual policy modes:
  - `rule_based`: threshold-driven transitions
  - `risk_scored`: weighted-risk transitions
- Optional hysteresis/min dwell controls.
- Explainability panel for active transition rules.
- Event timeline and transition logs.
- Monte Carlo experiment lab with CSV exports.
- Separate onboarding page from mission console for cleaner UI.

## Access options
Preferred in hosted environments:
- Google sign-in via Streamlit OIDC (`st.login` / `st.user` / `st.logout`) when auth secrets are configured.

Fallback demo accounts:
- Operator: `demo.operator@ods.local` / `ODS-demo-2026!`
- Mission Analyst: `mission.analyst@ods.local` / `ODS-analyst-2026!`

## Run locally
```bash
pip install streamlit pandas numpy
streamlit run app.py
```

## Onboarding flow
1. Open the `Client Onboarding` page.
2. Sign in with Google (if configured) or use demo fallback credentials.
3. Switch sidebar page to `Mission Console`.
4. Apply a scenario preset from the sidebar.
5. Review transitions in `Live Simulator`.
6. Run policy comparisons in `Experiment Lab`.

## Optional Google sign-in setup
The app is already wired for Streamlit's built-in OIDC login.
- Configure OIDC provider details in deployment secrets.
- Once configured, `Sign In with Google` becomes active on onboarding.
- No additional Python dependency is required.

## Reproducible evaluation suite
```bash
python evaluate_mvp.py --seeds 120 --out-dir .
```

Outputs:
- `evaluation_v2_raw.csv`
- `evaluation_v2_summary.csv`

## Screenshot set (for reports)
Manual capture targets:
- `Client Onboarding` signed-in view.
- `Nominal Operations` preset + `NOMINAL` jump target.
- `Throttle Response` preset + `THROTTLE` jump target.
- `Safe Mode Trigger` preset + `SAFE` jump target.
- `Recovery Sequence` preset + `RECOVER` jump target.

Automated capture:
```bash
# run app (example local port)
streamlit run app.py --server.port 8502

# in another terminal (requires playwright)
python capture_screenshots.py
```

Expected output files:
- `submission_assets/screenshots/00_onboarding.png`
- `submission_assets/screenshots/01_nominal.png`
- `submission_assets/screenshots/02_throttle.png`
- `submission_assets/screenshots/03_safe.png`
- `submission_assets/screenshots/04_recover.png`

## Additional artifacts
- Client workflow blueprint (FigJam):
  - https://www.figma.com/online-whiteboard/create-diagram/4a0efe97-3f2a-423a-aabc-c35b15a8fe43
- Validation and evidence map (FigJam):
  - https://www.figma.com/online-whiteboard/create-diagram/a88ac6a3-6241-4f36-81c9-cb5c94ce2a1f
