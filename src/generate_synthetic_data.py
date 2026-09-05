"""One-off script: generates data/synthetic_transactions.csv.

Run manually with: python src/generate_synthetic_data.py
Not invoked at app startup -- the CSV it produces is committed to the repo so
the deployed app never needs to regenerate data on the fly.

Seed dates: the recalled lots' carton codes carry Julian pack dates 157-184
in 2026, which is June 6 - July 3, 2026. Purchases don't happen the day eggs
are packed -- they move through distribution and sit in home fridges for a
while -- so seeded at-risk purchase_date values are drawn from a window that
starts a few days after packing begins and runs through a week past the
recall's July 22, 2026 public announcement. That overrun is deliberate: it's
what produces a meaningful, positive "lag-time" headline number in the app,
illustrating that recalled product kept moving after the public notice went
out.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 8451
fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

AFFECTED_STATES = ["TX", "LA", "OK", "AR", "NM", "MS"]
NOISE_EXTRA_STATES = ["FL", "GA", "AL", "MO", "CA", "TN"]
RECALLED_LOTS = ["P-1950", "0840962"]
RECALLED_BRANDS = ["Kroger", "Simple Truth", "Brookshire's", "Country Morning", "Sunups"]
RECALLED_PRODUCT_NAMES = [f"{b} Large Grade A Eggs, Dozen" for b in RECALLED_BRANDS]

NOISE_PRODUCTS = [
    "Great Value 2% Milk, Gallon",
    "Wonder Bread Classic White",
    "Tyson Chicken Breast, Family Pack",
    "Chobani Greek Yogurt, 32oz",
    "Blue Bell Vanilla Ice Cream",
    "Land O'Lakes Butter, 1lb",
    "Folgers Classic Roast Coffee",
    "Nature Valley Granola Bars",
]
NOISE_LOTS = [f"L-{random.randint(1000, 9999)}" for _ in range(6)] + [
    f"{random.randint(100000, 999999)}" for _ in range(4)
]

ALL_PRODUCTS = RECALLED_PRODUCT_NAMES + NOISE_PRODUCTS
PRODUCT_UPC = {name: fake.numerify("############") for name in ALL_PRODUCTS}

SEEDED_AT_RISK_START = date(2026, 6, 12)
SEEDED_AT_RISK_END = date(2026, 7, 29)
NOISE_DATE_START = date(2026, 4, 1)
NOISE_DATE_END = date(2026, 8, 15)

N_SEEDED = 150
N_TOTAL = 5000
N_NOISE = N_TOTAL - N_SEEDED

FIELDNAMES = [
    "loyalty_id",
    "store_id",
    "state",
    "upc",
    "product_name",
    "lot_code",
    "purchase_date",
    "quantity",
]


def _random_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=random.randint(0, span))


def generate_rows() -> list[dict]:
    rows = []

    for _ in range(N_SEEDED):
        state = random.choice(AFFECTED_STATES)
        lot = random.choice(RECALLED_LOTS)
        product = random.choice(RECALLED_PRODUCT_NAMES)
        purchase_date = _random_date(SEEDED_AT_RISK_START, SEEDED_AT_RISK_END)
        rows.append(
            {
                "loyalty_id": fake.uuid4(),
                "store_id": f"{state}-{fake.random_int(min=1000, max=9999)}",
                "state": state,
                "upc": PRODUCT_UPC[product],
                "product_name": product,
                "lot_code": lot,
                "purchase_date": purchase_date.isoformat(),
                "quantity": fake.random_int(min=1, max=4),
            }
        )

    noise_states_pool = AFFECTED_STATES + NOISE_EXTRA_STATES
    for _ in range(N_NOISE):
        state = random.choice(noise_states_pool)
        product = random.choice(NOISE_PRODUCTS)
        lot = random.choice(NOISE_LOTS)
        purchase_date = _random_date(NOISE_DATE_START, NOISE_DATE_END)
        rows.append(
            {
                "loyalty_id": fake.uuid4(),
                "store_id": f"{state}-{fake.random_int(min=1000, max=9999)}",
                "state": state,
                "upc": PRODUCT_UPC[product],
                "product_name": product,
                "lot_code": lot,
                "purchase_date": purchase_date.isoformat(),
                "quantity": fake.random_int(min=1, max=4),
            }
        )

    random.shuffle(rows)
    return rows


def main() -> None:
    rows = generate_rows()

    out_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_transactions.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    assert len(rows) == N_TOTAL, f"expected {N_TOTAL} rows, got {len(rows)}"
    seeded_at_risk = [
        r for r in rows if r["lot_code"] in RECALLED_LOTS and r["state"] in AFFECTED_STATES
    ]
    assert len(seeded_at_risk) == N_SEEDED, (
        f"expected {N_SEEDED} seeded at-risk rows, got {len(seeded_at_risk)}"
    )

    print(
        f"Wrote {len(rows)} rows ({N_SEEDED} seeded at-risk, {N_NOISE} noise) "
        f"to {out_path}"
    )


if __name__ == "__main__":
    main()
