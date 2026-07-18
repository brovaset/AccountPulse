"""Streamlit UI for the AccountPulse Customer Success agent."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from tools.crm.hubspot_client import hubspot_enabled
from tools.crm.mock_data import MOCK_ACCOUNTS, list_mock_account_ids
from tools.report import analyze_account_bundle, analyze_portfolio_bundle

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
    "ACTION NEEDED": ("#ffe4e1", "#8a1510", "#f04438"),
    "WATCH": ("#ffefd6", "#93370d", "#f79009"),
    "HEALTHY": ("#d1fadf", "#05603a", "#12b76a"),
    "NEEDS MANUAL REVIEW": ("#e8eef3", "#101828", "#667085"),
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
  --ap-ink: #06151c;
  --ap-muted: #1e3a45;
  --ap-line: rgba(6, 21, 28, 0.22);
  --ap-accent: #0a7d6e;
  --ap-glow: rgba(15, 159, 140, 0.28);
  --ap-surface: rgba(248, 252, 253, 0.94);
  --ap-radius: 18px;
  --ap-hero: url("{hero_uri}");
}}

html, body, [class*="css"] {{
  font-family: "Outfit", sans-serif;
  color: var(--ap-ink) !important;
}}

.stApp {{
  background:
    radial-gradient(1100px 560px at 8% -8%, rgba(30, 110, 130, 0.22), transparent 55%),
    radial-gradient(900px 520px at 100% 0%, rgba(18, 90, 95, 0.18), transparent 52%),
    linear-gradient(165deg, #d4e4e9 0%, #c8d9e0 40%, #dce7ec 100%);
  color: var(--ap-ink);
}}

.stApp::before {{
  content: "";
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(10, 30, 38, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10, 30, 38, 0.05) 1px, transparent 1px);
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
  color: var(--ap-ink);
}}

/* Force readable contrast on Streamlit text widgets */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stMarkdown strong, .stMarkdown em, .stMarkdown code,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stCaption"],
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label, p, span, li, h1, h2, h3, h4, h5, h6 {{
  color: var(--ap-ink) !important;
}}
[data-testid="stCaption"],
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {{
  color: var(--ap-muted) !important;
  font-weight: 500 !important;
  opacity: 1 !important;
}}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p,
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {{
  color: var(--ap-ink) !important;
  opacity: 1 !important;
}}
[data-testid="stMetricValue"] {{
  font-weight: 700 !important;
}}
.stTabs [data-baseweb="tab"] {{
  color: var(--ap-muted) !important;
  font-weight: 600 !important;
  opacity: 1 !important;
}}
.stTabs [aria-selected="true"] {{
  color: var(--ap-ink) !important;
  font-weight: 700 !important;
}}
.stCheckbox label span,
.stCheckbox label p,
[data-testid="stCheckbox"] label {{
  color: var(--ap-ink) !important;
  font-weight: 500 !important;
}}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span {{
  color: var(--ap-ink) !important;
  font-weight: 500 !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {{
  color: var(--ap-ink) !important;
  font-weight: 600 !important;
}}
[data-testid="stStatusWidget"] p,
[data-testid="stStatusWidget"] span,
[data-testid="stStatus"] p {{
  color: var(--ap-ink) !important;
}}
code, pre, .stCode {{
  color: #041016 !important;
  background: rgba(255, 255, 255, 0.85) !important;
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
  filter: brightness(0.62) saturate(0.9) contrast(1.08);
  animation: heroKenBurns 22s ease-in-out infinite alternate;
}}
.ap-hero-plane::after {{
  content: ""; position: absolute; inset: 0;
  background:
    linear-gradient(90deg, rgba(210, 228, 234, 0.94) 0%, rgba(200, 220, 228, 0.78) 40%, rgba(180, 205, 215, 0.28) 72%, transparent 100%),
    linear-gradient(180deg, rgba(190, 210, 218, 0.2) 0%, rgba(200, 220, 228, 0.88) 100%);
}}
.ap-hero {{
  position: relative; z-index: 1; max-width: 820px; margin: 0 auto;
  padding: 2.8rem 1.2rem 1.2rem;
}}
.ap-mark {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: 12px; margin-bottom: 0.8rem;
  color: #031c20; font-weight: 700;
  background: linear-gradient(135deg, #7ef0dc, #5cc8ff);
  animation: pulseRing 2.8s ease-out infinite, softGlow 4s ease-in-out infinite;
}}
.ap-brand {{
  font-family: "Syne", sans-serif; font-weight: 800;
  font-size: clamp(2.5rem, 5vw, 3.4rem); letter-spacing: -0.045em;
  line-height: 0.98; margin: 0 0 0.55rem; color: #031016 !important;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
}}
.ap-tagline {{
  font-size: 1.08rem; color: #0a1f28 !important; max-width: 28rem;
  line-height: 1.5; margin: 0; font-weight: 500;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.4);
}}
.ap-meta {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1rem 0 0; }}
.ap-chip {{
  font-size: 0.74rem; letter-spacing: 0.03em; text-transform: uppercase;
  font-weight: 700; color: #041820 !important;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(6, 21, 28, 0.28); border-radius: 999px; padding: 0.3rem 0.75rem;
}}
.ap-panel {{
  background: var(--ap-surface); border: 1px solid var(--ap-line);
  border-radius: var(--ap-radius); padding: 1rem 1.1rem 0.85rem;
  backdrop-filter: blur(14px); box-shadow: 0 18px 50px rgba(20, 50, 60, 0.12);
  animation: fadeUp 0.85s ease-out both; margin-bottom: 0.9rem;
  color: var(--ap-ink);
}}
.ap-risk {{
  display: inline-flex; align-items: center; gap: 0.45rem;
  border-radius: 999px; padding: 0.4rem 0.85rem; font-weight: 700;
  font-size: 0.88rem; letter-spacing: 0.02em; animation: riskPulse 2.4s ease-in-out infinite;
}}
.ap-step {{
  font-size: 0.92rem; color: #0a1f28 !important; font-weight: 500; padding: 0.35rem 0;
}}
.ap-step.done {{ color: #05603a !important; font-weight: 700; }}
.ap-footer {{
  margin-top: 1.4rem; font-size: 0.85rem; color: var(--ap-muted) !important;
  font-weight: 500; text-align: center;
}}

div[data-testid="stHorizontalBlock"] button {{
  border-radius: 14px !important;
}}
.stButton > button {{
  border-radius: 14px !important;
  font-family: "Outfit", sans-serif !important;
  font-weight: 700 !important;
  color: #041820 !important;
  border: 1px solid rgba(6, 21, 28, 0.22) !important;
  background: rgba(255, 255, 255, 0.92) !important;
}}
button[kind="primary"] {{
  background: linear-gradient(120deg, #5ce6ce 0%, #3eb8f0 100%) !important;
  color: #021a1e !important; border: 0 !important;
  box-shadow: 0 10px 28px rgba(0, 170, 180, 0.28);
  font-weight: 700 !important;
}}
button[kind="secondary"] {{
  color: #041820 !important;
  background: rgba(255, 255, 255, 0.95) !important;
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
      Review one account or run a morning briefing across assigned accounts —
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
briefing_clicked = st.button(
    "Run morning briefing (all mock accounts)",
    use_container_width=True,
)
st.markdown("</div>", unsafe_allow_html=True)

should_run = run_clicked or (
    auto_run and st.session_state.get("last_run_id") != selected_id
)

if briefing_clicked:
    status = st.status("Building morning briefing…", expanded=True)
    with status:
        st.markdown(
            '<div class="ap-step">1. Review assigned mock accounts</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ap-step">2. Classify and rank by risk</div>',
            unsafe_allow_html=True,
        )
        try:
            portfolio = analyze_portfolio_bundle()
            st.session_state["portfolio"] = portfolio
            st.session_state.pop("bundle", None)
            st.markdown(
                '<div class="ap-step done">Done — briefing ready</div>',
                unsafe_allow_html=True,
            )
            status.update(label="Morning briefing complete", state="complete")
        except Exception as exc:  # noqa: BLE001
            status.update(label="Morning briefing failed", state="error")
            st.exception(exc)

if should_run:
    status = st.status("Gathering live signals…", expanded=True)
    with status:
        st.markdown('<div class="ap-step">1. Pull CRM account data</div>', unsafe_allow_html=True)
        st.markdown('<div class="ap-step">2. Pull product usage</div>', unsafe_allow_html=True)
        st.markdown('<div class="ap-step">3. Classify risk + build report</div>', unsafe_allow_html=True)
        try:
            bundle = analyze_account_bundle(selected_id)
            st.session_state["bundle"] = bundle
            st.session_state.pop("portfolio", None)
            st.session_state["last_run_id"] = selected_id
            st.markdown(
                '<div class="ap-step done">Done — report ready</div>',
                unsafe_allow_html=True,
            )
            status.update(label="Review complete", state="complete")
        except Exception as exc:  # noqa: BLE001
            status.update(label="Review failed", state="error")
            st.exception(exc)

portfolio = st.session_state.get("portfolio")
if portfolio:
    counts = portfolio.get("counts") or {}
    st.markdown('<div class="ap-panel">', unsafe_allow_html=True)
    st.markdown("**Morning briefing**")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("ACTION NEEDED", counts.get("ACTION NEEDED", 0))
    with metric_cols[1]:
        st.metric("WATCH", counts.get("WATCH", 0))
    with metric_cols[2]:
        st.metric("HEALTHY", counts.get("HEALTHY", 0))
    with metric_cols[3]:
        st.metric("MANUAL REVIEW", counts.get("NEEDS MANUAL REVIEW", 0))
    st.markdown(portfolio["report"])
    st.download_button(
        "Download morning briefing (.md)",
        data=portfolio["report"],
        file_name="accountpulse-morning-briefing.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

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

        s_left, s_right = st.columns(2)
        with s_left:
            st.subheader("Support")
            support = bundle.get("support") or {}
            if support.get("ok"):
                st.write(support.get("account") or {})
                for signal in bundle.get("support_signals") or []:
                    st.warning(signal)
            else:
                st.warning(support.get("message") or "Support unavailable")
        with s_right:
            st.subheader("Communication")
            communication = bundle.get("communication") or {}
            if communication.get("ok"):
                st.write(communication.get("account") or {})
                for signal in bundle.get("communication_signals") or []:
                    st.info(signal)
            else:
                st.warning(
                    communication.get("message") or "Communication unavailable"
                )

        if show_raw:
            with st.expander("Raw tool payloads"):
                st.json(
                    {
                        "crm": crm,
                        "usage": usage,
                        "support": bundle.get("support"),
                        "communication": bundle.get("communication"),
                    }
                )

    with tab_actions:
        st.subheader("CSM checklist")
        owner = crm_data.get("account_owner") or "Account owner"
        renewal = crm_data.get("renewal_date") or "renewal"
        checks = [
            f"Confirm owner ({owner}) is assigned",
            f"Review renewal path before {renewal}",
            "Validate usage signal with product analytics (mock today)",
            "Escalate TCK billing/access requests to Billing (no auto-refund)",
            "Review communication sentiment / follow-up request",
            "Human approval before any customer outreach",
        ]
        for item in checks:
            st.checkbox(item, key=f"chk_{selected_id}_{item[:24]}")
        sentiment = st.feedback("thumbs", key=f"fb_{selected_id}")
        if sentiment is not None:
            st.caption("Thanks — feedback noted for this review.")

elif not should_run and not portfolio:
    st.info(
        "Select an account for a single review, or run the morning briefing "
        "across all mock assigned accounts."
    )

provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
if provider == "ollama":
    st.markdown(
        f'<p class="ap-footer">Official reviews use deterministic rules · '
        f'optional LLM demo: {os.getenv("OLLAMA_MODEL", "qwen2.5:3b")} '
        "(REPORT_MODE=ollama)</p>",
        unsafe_allow_html=True,
    )
