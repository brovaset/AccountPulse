"""Streamlit UI for the AccountPulse Customer Success agent."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from agent import create_agent
from tools.crm.mock_data import MOCK_ACCOUNTS, list_mock_account_ids

load_dotenv()

st.set_page_config(
    page_title="AccountPulse",
    layout="centered",
)

st.title("AccountPulse")
st.caption("Customer Success account-health agent — review risk signals before you act.")


def _account_label(account_id: str) -> str:
    account = MOCK_ACCOUNTS[account_id]
    return f"{account_id} — {account['account_name']} ({account['contract_status']})"


def _result_text(result: object) -> str:
    if result is None:
        return ""
    message = getattr(result, "message", None)
    if isinstance(message, dict):
        parts = message.get("content") or []
        texts = [
            block.get("text", "")
            for block in parts
            if isinstance(block, dict) and block.get("text")
        ]
        if texts:
            return "\n".join(texts)
    return str(result)


@st.cache_resource
def _get_agent():
    return create_agent()


if not os.getenv("OPENROUTER_API_KEY"):
    st.error("Add OPENROUTER_API_KEY to your `.env` file, then restart Streamlit.")
    st.stop()

account_ids = list_mock_account_ids()
selected_id = st.selectbox(
    "Account",
    options=account_ids,
    format_func=_account_label,
)

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

custom_prompt = st.text_area(
    "Optional instructions",
    value="",
    placeholder="Leave blank to run the standard account-health review.",
    height=80,
)

if st.button("Run account health review", type="primary"):
    prompt = custom_prompt.strip() or (
        f"Analyze account {selected_id} ({account['account_name']}). "
        "Call get_crm_account_data first. Mark unavailable tools as NEEDS MANUAL REVIEW. "
        "Return the required report sections."
    )

    with st.spinner("AccountPulse is gathering signals..."):
        try:
            agent = _get_agent()
            result = agent(prompt)
            report = _result_text(result)
        except Exception as exc:  # noqa: BLE001 — surface live demo failures in UI
            st.exception(exc)
        else:
            st.subheader("Report")
            st.markdown(report)
            st.session_state["last_report"] = report

elif "last_report" in st.session_state:
    st.subheader("Last report")
    st.markdown(st.session_state["last_report"])
