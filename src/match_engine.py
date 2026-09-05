"""Join a recall record against transactions to find at-risk loyalty accounts.

Matching rule: a transaction is at-risk if its lot_code is one of the recalled
lots AND its state is one of the distribution states. Date range is not a hard
filter -- lot_code is the authoritative recall identifier, and a legitimate
purchase can fall outside the pack-date window due to normal shelf life. The
pack-date window is instead used as a diagnostic flag (within_pack_date_window)
and to compute the lag-time headline metric.
"""

import pandas as pd


def find_at_risk_transactions(recall: dict, transactions: pd.DataFrame) -> pd.DataFrame:
    """Return the subset of transactions that match the recall's lot codes and states.

    Adds diagnostic columns: lot_match, state_match, within_pack_date_window,
    and a human-readable match_reason string per row.
    """
    lot_codes = set(recall["lot_codes"])
    states = set(recall["distribution_states"])
    pack_start = pd.to_datetime(recall["julian_pack_date_range"]["start_date"])
    pack_end = pd.to_datetime(recall["julian_pack_date_range"]["end_date"])

    df = transactions.copy()
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df["lot_match"] = df["lot_code"].isin(lot_codes)
    df["state_match"] = df["state"].isin(states)
    df["within_pack_date_window"] = df["purchase_date"].between(pack_start, pack_end)

    at_risk = df[df["lot_match"] & df["state_match"]].copy()

    def build_reason(row: pd.Series) -> str:
        return (
            f"Matched lot_code={row['lot_code']} and state={row['state']}, "
            f"purchased {row['purchase_date'].date().isoformat()}"
        )

    at_risk["match_reason"] = at_risk.apply(build_reason, axis=1)

    return at_risk.sort_values("purchase_date", ascending=False).reset_index(drop=True)


def compute_flagged_accounts(at_risk: pd.DataFrame) -> pd.DataFrame:
    """Collapse at-risk transactions to one row per loyalty account.

    Each account's match_reason and lot_code reflect its most recent matching
    transaction.
    """
    if at_risk.empty:
        return pd.DataFrame(
            columns=[
                "loyalty_id",
                "num_matching_transactions",
                "last_purchase_date",
                "state",
                "match_reason",
                "lot_code",
            ]
        )

    grouped = (
        at_risk.groupby("loyalty_id")
        .agg(
            num_matching_transactions=("loyalty_id", "count"),
            last_purchase_date=("purchase_date", "max"),
        )
        .reset_index()
    )

    latest = at_risk.sort_values("purchase_date").drop_duplicates("loyalty_id", keep="last")
    grouped = grouped.merge(
        latest[["loyalty_id", "state", "match_reason", "lot_code"]], on="loyalty_id"
    )

    return grouped.sort_values("last_purchase_date", ascending=False).reset_index(drop=True)


def compute_lag_time_days(at_risk: pd.DataFrame, recall: dict) -> int | None:
    """Days between the most recent at-risk purchase and the recall's public
    initiation date. A positive number means at-risk product was still being
    purchased after the recall was announced. Returns None when there are no
    matching transactions -- callers must guard against this before rendering.
    """
    if at_risk.empty:
        return None
    last_date = at_risk["purchase_date"].max()
    recall_date = pd.to_datetime(recall["recall_initiation_date"])
    return int((last_date - recall_date).days)
