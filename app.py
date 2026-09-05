"""recall-trace: lot-to-loyalty recall tracing demo.

Streamlit entrypoint. Renders fully from committed data files -- no live
network call is required to show something meaningful.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from audit_log import build_audit_log  # noqa: E402
from fetch_recall import fetch_recall_record  # noqa: E402
from match_engine import (  # noqa: E402
    compute_flagged_accounts,
    compute_lag_time_days,
    find_at_risk_transactions,
)

st.set_page_config(page_title="recall-trace", page_icon="🥚", layout="wide")


@st.cache_data
def load_transactions() -> pd.DataFrame:
    return pd.read_csv(
        ROOT / "data" / "synthetic_transactions.csv",
        dtype={"upc": str, "lot_code": str, "store_id": str},
    )


recall, source = fetch_recall_record()

st.title("recall-trace: Lot-to-Loyalty Recall Tracing Demo")

st.markdown(
    f"""
On **{recall['recall_initiation_date']}**, **{recall['recalling_firm']}** recalled
**{recall['product_type'].lower()}** sold under the {', '.join(recall['brand_names'][:-1])},
and {recall['brand_names'][-1]} brands, after testing linked them to
**{recall['pathogen']}** -- an antibiotic-resistant strain. The FDA classified it
**{recall['recall_classification']}**, its most serious category. The outbreak
sickened **{recall['outbreak_stats']['illnesses']} people** across
**{recall['outbreak_stats']['states_affected']} states**, with
**{recall['outbreak_stats']['hospitalizations']} hospitalizations**.

This demo shows how a retailer could go from "here's a recalled lot code" to
"here are the loyalty accounts that bought it" in seconds, with a fully
auditable trail explaining every match.

[Read the FDA recall notice]({recall['source']['url']})
"""
)

st.warning(
    "Loyalty/transaction data below is 100% synthetic, seeded to demonstrate "
    "the matching logic. No real Kroger customer data is used anywhere in "
    "this demo.",
    icon="⚠️",
)

source_caption = (
    "Source: live openFDA confirmation"
    if source == "live_openfda"
    else "Source: cached FDA seed record (live openFDA lookup unavailable or skipped)"
)
st.caption(source_caption)

with st.expander("Recall details"):
    st.markdown(
        f"""
- **Recalled lot codes:** {', '.join(recall['lot_codes'])}
- **Pack date range (Julian day {recall['julian_pack_date_range']['start_julian_day']}-{recall['julian_pack_date_range']['end_julian_day']}, {recall['julian_pack_date_range']['year']}):**
  {recall['julian_pack_date_range']['start_date']} to {recall['julian_pack_date_range']['end_date']}
- **Brands:** {', '.join(recall['brand_names'])}
- **Distribution states:** {', '.join(recall['distribution_states'])}
- **Pathogen:** {recall['pathogen']}
- **Outbreak:** {recall['outbreak_stats']['illnesses']} illnesses,
  {recall['outbreak_stats']['hospitalizations']} hospitalizations,
  {recall['outbreak_stats']['states_affected']} states affected,
  FDA {recall['outbreak_stats']['fda_classification']} classification
"""
    )

st.divider()

if st.button("Run trace", type="primary") or st.session_state.get("has_run"):
    st.session_state["has_run"] = True

    transactions = load_transactions()
    at_risk = find_at_risk_transactions(recall, transactions)

    if at_risk.empty:
        st.success("No matching transactions found in the synthetic dataset.")
    else:
        flagged_accounts = compute_flagged_accounts(at_risk)
        lag_days = compute_lag_time_days(at_risk, recall)

        col1, col2, col3 = st.columns(3)
        col1.metric("Flagged accounts", len(flagged_accounts))
        col2.metric("Matching transactions", len(at_risk))
        col3.metric("Lag time (days past recall notice)", lag_days)

        st.subheader("Flagged accounts by state")
        st.bar_chart(flagged_accounts["state"].value_counts())

        st.subheader("Flagged accounts — audit trail")
        st.dataframe(build_audit_log(flagged_accounts), use_container_width=True)

        st.button(
            "Send notifications",
            disabled=True,
            help=(
                "Demo only — this is a notification queue, not a sender. "
                "No email/SMS integration exists in this app."
            ),
        )
else:
    st.info("Click **Run trace** to run the matching engine against synthetic transaction data.")

st.divider()
st.caption(
    "Built with Streamlit + pandas + Faker (seed=8451). Recall facts are real "
    "and sourced from the FDA; all transaction/loyalty data is synthetic. "
    "Portfolio demo — not affiliated with Kroger, the FDA, or Midwest Poultry Services."
)
