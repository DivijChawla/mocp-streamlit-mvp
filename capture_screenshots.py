#!/usr/bin/env python3
from pathlib import Path
from playwright.sync_api import sync_playwright

APP_URL = "http://localhost:8502"
OUT = Path('/Users/divijchawla/Documents/Codex/mocp_streamlit_mvp/submission_assets/screenshots')
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ("Nominal Operations", "NOMINAL", "01_nominal.png"),
    ("Throttle Response", "THROTTLE", "02_throttle.png"),
    ("Safe Mode Trigger", "SAFE", "03_safe.png"),
    ("Recovery Sequence", "RECOVER", "04_recover.png"),
]


def choose_select_option(page, label: str, value: str) -> None:
    combo = page.get_by_label(label)
    combo.click(timeout=10000)
    page.get_by_role("option", name=value).first.click(timeout=10000)


def click_apply(page) -> None:
    page.get_by_role("button", name="Apply Selected Preset").click(timeout=10000)
    page.wait_for_timeout(1400)


def choose_page(page, page_name: str) -> None:
    page.get_by_role("radio", name=page_name).check(timeout=10000)
    page.wait_for_timeout(800)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 2200})
        page.goto(APP_URL, wait_until="networkidle", timeout=120000)
        page.get_by_text("Managed Onboard Compute Payload (MOCP) - Prototype MVP").wait_for(timeout=30000)

        # Onboarding tab screenshot
        onboarding_out = OUT / "00_onboarding.png"
        page.get_by_role("tab", name="Client Onboarding").click(timeout=10000)
        page.wait_for_timeout(1000)
        page.get_by_label("Email").fill("demo.operator@ods.local")
        page.get_by_role("textbox", name="Password").fill("ODS-demo-2026!")
        page.get_by_role("button", name="Sign In with Demo Credentials").click(timeout=10000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(onboarding_out), full_page=True)
        print(f"saved {onboarding_out}")

        # Switch to mission console page for state captures
        choose_page(page, "Mission Console")
        page.wait_for_timeout(1200)

        for preset, state, filename in TARGETS:
            # set preset + apply
            choose_select_option(page, "Preset", preset)
            click_apply(page)

            # state target + jump
            choose_select_option(page, "State target", state)
            page.get_by_role("button", name="Jump To Target Step").click(timeout=10000)
            page.wait_for_timeout(1200)

            # ensure main state heading visible
            page.get_by_text("Current State").first.wait_for(timeout=10000)

            out = OUT / filename
            page.screenshot(path=str(out), full_page=True)
            print(f"saved {out}")

        browser.close()


if __name__ == "__main__":
    main()
