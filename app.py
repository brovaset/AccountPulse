"""Streamlit UI for the AccountPulse Customer Success agent."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from tools.crm.hubspot_client import hubspot_enabled
from tools.crm.mock_data import MOCK_ACCOUNTS, list_mock_account_ids
from tools.report import analyze_account

load_dotenv()

st.set_page_config(
    page_title="AccountPulse",
    layout="centered",
)

st.title("AccountPulse")
st.caption(
    "Customer Success account-health agent — review risk signals before you act."
)

LIVE_HUBSPOT_ACCOUNTS = {
    "333055649511": "Northwind Analytics (live HubSpot)",
    "332906103502": "Brightleaf Retail (live HubSpot)",
    "333057467115": "Harbor Logistics (live HubSpot)",
}


def _account_label(account_id: str) -> str:
    if account_id in LIVE_HUBSPOT_ACCOUNTS:
        return f"{account_id} — {LIVE_HUBSPOT_ACCOUNTS[account_id]}"
    account = MOCK_ACCOUNTS[account_id]
    return f"{account_id} — {account['account_name']} ({account['contract_status']})"


provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
st.caption(
    "Reports use live CRM/usage tools with deterministic risk rules "
    "(reliable for demos). Support/comms stay NEEDS MANUAL REVIEW."
)
if provider == "ollama":
    st.caption(
        f"Optional LLM provider configured: Ollama "
        f"`{os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')}` "
        "(not required for the standard review button)."
    )

account_ids = list(LIVE_HUBSPOT_ACCOUNTS) + list_mock_account_ids()
if not hubspot_enabled():
    account_ids = list_mock_account_ids()

selected_id = st.selectbox(
    "Account",
    options=account_ids,
    format_func=_account_label,
    index=0,
)

if selected_id in MOCK_ACCOUNTS:
    account = MOCK_ACCOUNTS[selected_id]
    with st.expander("CRM preview (mock)", expanded=False):
        st.write(
            {
                "owner": account["account_owner"],
                "renewal_date": account["renewal_date"],
                "contract_status": account["contract_status"],
                "plan_tier": account["plan_tier"],
            }
        )
else:
    st.info("Live HubSpot company — CRM will be fetched when you run the review.")

if st.button("Run account health review", type="primary"):
    with st.spinner("AccountPulse is gathering CRM and usage signals..."):
        try:
            report = analyze_account(selected_id)
        except Exception as exc:  # noqa: BLE001 — surface live demo failures in UI
            st.exception(exc)
        else:
            st.subheader("Report")
            st.markdown(report)
            st.session_state["last_report"] = report

elif "last_report" in st.session_state:
    st.subheader("Last report")
    st.markdown(st.session_state["last_report"])
