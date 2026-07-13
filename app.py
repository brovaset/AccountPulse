"""Streamlit UI for the AccountPulse Customer Success agent."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from tools.crm.hubspot_client import hubspot_enabled
from tools.crm.mock_data import MOCK_ACCOUNTS, list_mock_account_ids
from tools.report.build_account_health_report import analyze_account_bundle

load_dotenv()

st.set_page_config(
    page_title="AccountPulse",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

LIVE_HUBSPOT_ACCOUNTS = {
    "333055649511": "Northwind Analytics",
    "332906103502": "Brightleaf Retail",
    "333057467115": "Harbor Logistics",
}

HERO_PATH = Path(__file__).resolve().parent / "assets" / "accountpulse-hero.jpg"

RISK_STYLES = {
    "ACTION NEEDED": ("#fff1f0", "#b42318", "#f97066"),
    "WATCH": ("#fff8eb", "#b54708", "#fdb022"),
    "HEALTHY": ("#ecfdf3", "#067647", "#32d583"),
    "NEEDS MANUAL REVIEW": ("#f2f4f7", "#344054", "#98a2b3"),
}


def _data_uri(path: Path, mime: str) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


hero_uri = _data_uri(HERO_PATH, "image/jpeg")

UI_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Syne:wght@600;700;800&display=swap');

:root {{
  --ap-ink: #102832;
  --ap-muted: #4a6670;
  --ap-line: rgba(16, 40, 50, 0.14);
  --ap-accent: #0f9f8c;
  --ap-glow: rgba(15, 159, 140, 0.28);
  --ap-surface: rgba(236, 245, 247, 0.78);
  --ap-radius: 18px;
  --ap-hero: url("{hero_uri}");
}}

html, body, [class*="css"] {{ font-family: "Outfit", sans-serif; }}

.stApp {{
  background:
    radial-gradient(1100px 560px at 8% -8%, rgba(30, 110, 130, 0.28), transparent 55%),
    radial-gradient(900px 520px at 100% 0%, rgba(18, 90, 95, 0.22), transparent 52%),
    linear-gradient(165deg, #c5d8de 0%, #b7cdd5 40%, #cfdce2 100%);
  color: var(--ap-ink);
}}

.stApp::before {{
  content: "";
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(10, 30, 38, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10, 30, 38, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center, black 35%, transparent 80%);
  animation: gridDrift 28s linear infinite;
}}

@keyframes gridDrift {{
  from {{ background-position: 0 0, 0 0; }}
  to {{ background-position: 48px 48px, 48px 48px; }}
}}
@keyframes fadeUp {{
  from {{ opacity: 0; transform: translateY(14px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes pulseRing {{
  0% {{ box-shadow: 0 0 0 0 var(--ap-glow); }}
  70% {{ box-shadow: 0 0 0 14px transparent; }}
  100% {{ box-shadow: 0 0 0 0 transparent; }}
}}
@keyframes softGlow {{
  0%, 100% {{ filter: drop-shadow(0 0 8px rgba(0, 194, 168, 0.35)); }}
  50% {{ filter: drop-shadow(0 0 16px rgba(26, 167, 255, 0.45)); }}
}}
@keyframes heroKenBurns {{
  from {{ transform: scale(1.02); }}
  to {{ transform: scale(1.08); }}
}}
@keyframes riskPulse {{
  0%, 100% {{ transform: scale(1); }}
  50% {{ transform: scale(1.03); }}
}}

[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}

.block-container {{
  position: relative; z-index: 1; max-width: 820px;
  padding-top: 1.2rem; padding-bottom: 3.5rem;
  animation: fadeUp 0.7s ease-out both;
}}

.ap-hero-plane {{
  position: relative; left: 50%; right: 50%;
  margin-left: -50vw; margin-right: -50vw; width: 100vw;
  min-height: min(42vh, 340px); overflow: hidden; margin-bottom: 1.2rem;
  animation: fadeUp 0.8s ease-out both;
}}
.ap-hero-plane::before {{
  content: ""; position: absolute; inset: 0;
  background-image: var(--ap-hero); background-size: cover;
  background-position: center right;
  filter: brightness(0.78) saturate(0.92) contrast(1.05);
  animation: heroKenBurns 22s ease-in-out infinite alternate;
}}
.ap-hero-plane::after {{
  content: ""; position: absolute; inset: 0;
  background:
    linear-gradient(90deg, rgba(140, 170, 180, 0.88) 0%, rgba(150, 178, 188, 0.55) 36%, rgba(160, 185, 195, 0.12) 70%, transparent 100%),
    linear-gradient(180deg, rgba(120, 150, 160, 0.15) 0%, rgba(150, 175, 185, 0.82) 100%);
}}
.ap-hero {{
  position: relative; z-index: 1; max-width: 820px; margin: 0 auto;
  padding: 2.8rem 1.2rem 1.2rem;
}}
.ap-mark {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: 12px; margin-bottom: 0.8rem;
  color: #05363a; font-weight: 700;
  background: linear-gradient(135deg, #7ef0dc, #5cc8ff);
  animation: pulseRing 2.8s ease-out infinite, softGlow 4s ease-in-out infinite;
}}
.ap-brand {{
  font-family: "Syne", sans-serif; font-weight: 800;
  font-size: clamp(2.5rem, 5vw, 3.4rem); letter-spacing: -0.045em;
  line-height: 0.98; margin: 0 0 0.55rem; color: #0c242c;
}}
.ap-tagline {{
  font-size: 1.02rem; color: #2f4a54; max-width: 28rem; line-height: 1.45; margin: 0;
}}
.ap-meta {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1rem 0 0; }}
.ap-chip {{
  font-size: 0.72rem; letter-spacing: 0.03em; text-transform: uppercase;
  color: #173e48; background: rgba(220, 236, 240, 0.72);
  border: 1px solid var(--ap-line); border-radius: 999px; padding: 0.28rem 0.7rem;
}}
.ap-panel {{
  background: var(--ap-surface); border: 1px solid var(--ap-line);
  border-radius: var(--ap-radius); padding: 1rem 1.1rem 0.85rem;
  backdrop-filter: blur(14px); box-shadow: 0 18px 50px rgba(20, 50, 60, 0.12);
  animation: fadeUp 0.85s ease-out both; margin-bottom: 0.9rem;
}}
.ap-risk {{
  display: inline-flex; align-items: center; gap: 0.45rem;
  border-radius: 999px; padding: 0.4rem 0.85rem; font-weight: 700;
  font-size: 0.85rem; letter-spacing: 0.02em; animation: riskPulse 2.4s ease-in-out infinite;
}}
.ap-step {{
  font-size: 0.86rem; color: #355664; padding: 0.35rem 0;
}}
.ap-step.done {{ color: #067647; font-weight: 600; }}
.ap-footer {{ margin-top: 1.4rem; font-size: 0.8rem; color: var(--ap-muted); text-align: center; }}

div[data-testid="stHorizontalBlock"] button {{
  border-radius: 14px !important;
}}
.stButton > button {{
  border-radius: 14px !important;
  font-family: "Outfit", sans-serif !important;
  font-weight: 600 !important;
}}
button[kind="primary"] {{
  background: linear-gradient(120deg, #6ef0d8 0%, #53c8ff 100%) !important;
  color: #042f34 !important; border: 0 !important;
  box-shadow: 0 10px 28px rgba(0, 170, 180, 0.28);
}}
</style>
"""


def _account_options() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    if hubspot_enabled():
        for account_id, name in LIVE_HUBSPOT_ACCOUNTS.items():
            options.append((account_id, f"{name} · live"))
    for account_id in list_mock_account_ids():
        account = MOCK_ACCOUNTS[account_id]
        options.append(
            (
                account_id,
                f"{account['account_name']} · {account['contract_status']}",
            )
        )
    return options


def _render_risk_badge(risk: str) -> None:
    bg, fg, _dot = RISK_STYLES.get(risk, RISK_STYLES["NEEDS MANUAL REVIEW"])
    st.markdown(
        f'<span class="ap-risk" style="background:{bg};color:{fg};border:1px solid {fg}33;">'
        f"● {risk}</span>",
        unsafe_allow_html=True,
    )


st.markdown(UI_CSS, unsafe_allow_html=True)

st.markdown(
    """
<div class="ap-hero-plane">
  <div class="ap-hero">
    <div class="ap-mark">◈</div>
    <h1 class="ap-brand">AccountPulse</h1>
    <p class="ap-tagline">
      Pick an account, run a live review, and explore signals interactively —
      before any human takes action.
    </p>
    <div class="ap-meta">
      <span class="ap-chip">Live HubSpot</span>
      <span class="ap-chip">Human review</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

options = _account_options()
labels = [label for _, label in options]
ids = [account_id for account_id, _ in options]

if "selected_account_id" not in st.session_state:
    st.session_state.selected_account_id = ids[0]

st.markdown('<div class="ap-panel">', unsafe_allow_html=True)
st.markdown("**Choose an account**")

# Interactive account tiles (3 per row)
for row_start in range(0, len(options), 3):
    cols = st.columns(3)
    for col, (account_id, label) in zip(cols, options[row_start : row_start + 3]):
        with col:
            selected = st.session_state.selected_account_id == account_id
            if st.button(
                ("✓ " if selected else "") + label,
                key=f"acct_{account_id}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                st.session_state.selected_account_id = account_id
                st.rerun()

selected_id = st.session_state.selected_account_id
selected_label = labels[ids.index(selected_id)]
st.caption(f"Selected: `{selected_id}` · {selected_label}")

preview_cols = st.columns(2)
with preview_cols[0]:
    auto_run = st.toggle("Auto-run on select", value=False)
with preview_cols[1]:
    show_raw = st.toggle("Show raw tool JSON", value=False)

run_clicked = st.button("Run account health review", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

should_run = run_clicked or (
    auto_run and st.session_state.get("last_run_id") != selected_id
)

if should_run:
    status = st.status("Gathering live signals…", expanded=True)
    with status:
        st.markdown('<div class="ap-step">1. Pull CRM account data</div>', unsafe_allow_html=True)
        st.markdown('<div class="ap-step">2. Pull product usage</div>', unsafe_allow_html=True)
        st.markdown('<div class="ap-step">3. Classify risk + build report</div>', unsafe_allow_html=True)
        try:
            bundle = analyze_account_bundle(selected_id)
            st.session_state["bundle"] = bundle
            st.session_state["last_run_id"] = selected_id
            st.markdown(
                '<div class="ap-step done">Done — report ready</div>',
                unsafe_allow_html=True,
            )
            status.update(label="Review complete", state="complete")
        except Exception as exc:  # noqa: BLE001
            status.update(label="Review failed", state="error")
            st.exception(exc)

bundle = st.session_state.get("bundle")
if bundle and bundle.get("account_id") == selected_id:
    risk = bundle["risk"]
    crm = bundle["crm"]
    usage = bundle["usage"]
    crm_data = crm.get("data") or {}
    usage_acct = (usage.get("account") or {}) if usage.get("ok") else {}
    hs = crm_data.get("health_signals") or {}

    st.markdown('<div class="ap-panel">', unsafe_allow_html=True)
    top = st.columns([1.4, 1, 1, 1])
    with top[0]:
        st.caption("Risk level")
        _render_risk_badge(risk)
    with top[1]:
        st.metric(
            "Days to renewal",
            hs.get("days_to_renewal", "—") if crm.get("ok") else "—",
        )
    with top[2]:
        st.metric(
            "Adoption %",
            usage_acct.get("feature_adoption_percent", "—"),
        )
    with top[3]:
        st.metric(
            "Usage trend",
            (usage_acct.get("usage_trend") or "—").title(),
        )
    st.markdown("</div>", unsafe_allow_html=True)

    tab_report, tab_signals, tab_actions = st.tabs(
        ["Report", "Signals", "Next actions"]
    )

    with tab_report:
        st.markdown(bundle["report"])
        st.download_button(
            "Download report (.md)",
            data=bundle["report"],
            file_name=f"accountpulse-{selected_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with tab_signals:
        left, right = st.columns(2)
        with left:
            st.subheader("CRM")
            if crm.get("ok"):
                st.write(
                    {
                        "account": crm_data.get("account_name"),
                        "owner": crm_data.get("account_owner"),
                        "renewal": crm_data.get("renewal_date"),
                        "contract": crm_data.get("contract_status"),
                        "notes": crm_data.get("account_notes"),
                    }
                )
                for signal in bundle["crm_signals"]:
                    st.success(signal)
            else:
                st.error(crm.get("message") or "CRM unavailable")
        with right:
            st.subheader("Product usage")
            if usage.get("ok"):
                st.write(usage_acct)
                for signal in bundle["usage_signals"]:
                    st.info(signal)
            else:
                st.warning(usage.get("message") or "Usage unavailable")

        if show_raw:
            with st.expander("Raw tool payloads"):
                st.json({"crm": crm, "usage": usage})

    with tab_actions:
        st.subheader("CSM checklist")
        owner = crm_data.get("account_owner") or "Account owner"
        renewal = crm_data.get("renewal_date") or "renewal"
        checks = [
            f"Confirm owner ({owner}) is assigned",
            f"Review renewal path before {renewal}",
            "Validate usage signal with product analytics (mock today)",
            "Escalate TCK billing/access requests to Billing (no auto-refund)",
            "Check communications manually (not connected)",
            "Human approval before any customer outreach",
        ]
        for item in checks:
            st.checkbox(item, key=f"chk_{selected_id}_{item[:24]}")
        sentiment = st.feedback("thumbs", key=f"fb_{selected_id}")
        if sentiment is not None:
            st.caption("Thanks — feedback noted for this review.")

elif not should_run:
    st.info("Select an account tile, then run a review to explore interactive signals.")

provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
if provider == "ollama":
    st.markdown(
        f'<p class="ap-footer">Optional local model: '
        f'{os.getenv("OLLAMA_MODEL", "qwen2.5:3b")} · '
        "standard reviews do not require the LLM</p>",
        unsafe_allow_html=True,
    )
