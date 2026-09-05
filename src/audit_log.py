"""Build a human-readable, explainable audit trail for flagged accounts.

This is a notification QUEUE, not a sender -- no email/SMS integration exists
or is invoked here. The UI renders this table with a permanently disabled
"Send" button.
"""

from datetime import datetime, timezone

import pandas as pd


def build_audit_log(flagged_accounts: pd.DataFrame) -> pd.DataFrame:
    """Turn match_engine.compute_flagged_accounts() output into an audit trail.

    Every row in a single call shares the same computed_at timestamp -- the
    moment the trace was run, not per-row wall-clock drift.
    """
    computed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    df = flagged_accounts.copy()
    df["matched_fields"] = "lot_code, state"
    df["computed_at"] = computed_at
    df["explanation"] = df["match_reason"]
    df["notification_status"] = "QUEUED - NOT SENT (demo)"

    return df[
        [
            "loyalty_id",
            "matched_fields",
            "computed_at",
            "explanation",
            "notification_status",
            "last_purchase_date",
            "num_matching_transactions",
        ]
    ]
