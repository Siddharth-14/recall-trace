"""Plain-assert checks for match_engine correctness against the real committed
data. Run directly: python tests/test_match_engine.py
No pytest dependency required -- this is a standalone script, not a suite the
deployed app needs at runtime.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fetch_recall import load_seed_record  # noqa: E402
from match_engine import compute_flagged_accounts, find_at_risk_transactions  # noqa: E402

RECALLED_LOTS = {"P-1950", "0840962"}
AFFECTED_STATES = {"TX", "LA", "OK", "AR", "NM", "MS"}
EXPECTED_SEEDED_COUNT = 150


def main() -> None:
    recall = load_seed_record()
    transactions = pd.read_csv(
        ROOT / "data" / "synthetic_transactions.csv",
        dtype={"upc": str, "lot_code": str, "store_id": str},
    )

    at_risk = find_at_risk_transactions(recall, transactions)

    assert len(at_risk) == EXPECTED_SEEDED_COUNT, (
        f"expected {EXPECTED_SEEDED_COUNT} at-risk transactions, got {len(at_risk)}"
    )

    assert set(at_risk["lot_code"]).issubset(RECALLED_LOTS), (
        "at-risk rows contained a lot_code outside the recalled set"
    )
    assert set(at_risk["state"]).issubset(AFFECTED_STATES), (
        "at-risk rows contained a state outside the affected set"
    )

    noise = transactions[
        ~transactions["lot_code"].isin(RECALLED_LOTS)
        | ~transactions["state"].isin(AFFECTED_STATES)
    ]
    noise_in_at_risk = set(noise["loyalty_id"]) & set(at_risk["loyalty_id"])
    assert not noise_in_at_risk, f"noise loyalty_ids leaked into at-risk set: {noise_in_at_risk}"

    flagged_accounts = compute_flagged_accounts(at_risk)
    assert len(flagged_accounts) <= EXPECTED_SEEDED_COUNT, (
        "flagged accounts should never exceed at-risk transaction count"
    )
    assert flagged_accounts["num_matching_transactions"].sum() == EXPECTED_SEEDED_COUNT

    print(
        f"OK: {len(at_risk)} at-risk transactions across {len(flagged_accounts)} "
        f"flagged accounts, zero noise leakage."
    )


if __name__ == "__main__":
    main()
