# recall-trace

A small, deployable demo of fast, auditable **lot-to-loyalty-account tracing**
for a food recall — the kind of thing a grocery retailer's food-safety team
needs the moment a recall notice lands: *who bought this, and how do we know?*

**[Try the live demo →](https://recall-trace.streamlit.app/)**

## What it demonstrates

Given a recalled lot code, `recall-trace`:

1. Joins it against a transaction table to find every purchase of that lot.
2. Flags the loyalty accounts behind those purchases.
3. Surfaces a **lag-time** metric — how many days after the public recall
   notice the product was still being purchased. This is arguably the single
   most important number in a recall response: it tells you how much runway
   you've already lost.
4. Produces a fully explainable, one-line-per-account **audit trail** — not
   just "this account is flagged," but *why* ("Matched lot_code=P-1950 and
   state=TX, purchased 2026-07-18").

It stops short of actually notifying anyone. The audit trail feeds a
notification *queue*, rendered with a permanently disabled "Send" button —
this is a tracing demo, not a messaging product.

## The real recall behind this demo

This app is built around a real 2026 FDA recall:

> **Midwest Poultry Services, L.P.** recalled shell eggs on **July 22, 2026**,
> after they were linked to a **ciprofloxacin-resistant strain of Salmonella
> Enteritidis**. The FDA classified it **Class I** — its most serious
> category, reserved for situations where there's a reasonable probability
> the product will cause serious health consequences or death. The outbreak
> caused **98 illnesses**, **26 hospitalizations**, across **17 states**.
>
> Recalled carton codes: **P-1950** and **0840962**, packed on Julian dates
> 157–184 of 2026 (**June 6 – July 3, 2026**). Sold under the **Kroger,
> Simple Truth, Brookshire's, Country Morning,** and **Sunups** brands,
> distributed across **Texas, Louisiana, Oklahoma, Arkansas, New Mexico,**
> and **Mississippi**.

Source: [FDA recall notice, "Midwest Poultry Services, L.P. Recalls Shell
Eggs Due to Possible Salmonella Enteritidis
Contamination"](https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts).
These facts are hardcoded in `data/seed_recall_record.json`.

**Important disclosure:** the recall facts above are real. Everything else —
every loyalty ID, every transaction, every store number — is **100%
synthetic**, generated with [Faker](https://faker.readthedocs.io/) (seed
`8451`, fully reproducible). **No real Kroger customer data, or any other
retailer's customer data, is used anywhere in this project.** The banner at
the top of the running app repeats this disclosure so no visitor could
mistake it for real.

## Architecture

```
data/seed_recall_record.json ──┐
                                ├──▶ src/match_engine.py ──▶ src/audit_log.py ──▶ app.py (Streamlit UI)
data/synthetic_transactions.csv┘
                                
src/fetch_recall.py: tries a live openFDA lookup first, falls back to the
seed JSON on any failure (network error, timeout, empty result) — always
non-blocking, the app never depends on it to render.
```

- **`data/seed_recall_record.json`** — the real recall facts, hand-entered
  from the FDA source above.
- **`data/synthetic_transactions.csv`** — ~5,000 synthetic transactions,
  generated once and committed to the repo (see below). ~150 of them are
  seeded as "ground truth" at-risk purchases; the rest are noise.
- **`src/generate_synthetic_data.py`** — the one-off script that produced
  the CSV. Not run at app startup.
- **`src/match_engine.py`** — the join/match logic. A transaction is
  at-risk if its `lot_code` is one of the recalled lots **and** its `state`
  is one of the distribution states. The pack-date window isn't a hard
  filter — lot_code is the authoritative identifier, and a legitimate
  purchase can fall outside that window due to normal shelf life — so date
  range is used as a diagnostic flag and to compute lag-time, not to gate
  matches.
- **`src/audit_log.py`** — turns flagged accounts into a human-readable
  audit trail (matched fields, a one-line explanation, a timestamp, and a
  `QUEUED - NOT SENT (demo)` notification status).
- **`src/fetch_recall.py`** — attempts a live `api.fda.gov/food/enforcement.json`
  lookup for `recalling_firm:"Midwest Poultry"` first; on any failure at all,
  falls back to the seed JSON. A successful live call only *adds* a
  display-only confirmation note — it never overwrites the trusted lot
  codes/dates/states used by the match engine.
- **`app.py`** — the Streamlit UI tying it all together.

## Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. No API keys, no environment variables, no
database — it reads straight from the committed CSV and JSON files.

To verify the match engine's correctness:

```bash
python tests/test_match_engine.py
```

This asserts that all ~150 seeded at-risk transactions are correctly flagged
and that no noise transaction leaks into the result.

## How the synthetic data was generated

```bash
python src/generate_synthetic_data.py
```

This is a one-off script (already run — the CSV it produces is committed to
the repo, so you don't need to re-run it). It uses `Faker.seed(8451)` and
`random.seed(8451)` for full reproducibility.

One subtlety worth documenting: carton codes encode **pack date**, not
**purchase date**. The recalled lots' Julian pack-date range (157–184 in
2026) converts to June 6 – July 3, 2026. Eggs don't get bought the day
they're packed — they move through distribution and can sit in a fridge for
weeks — so the ~150 seeded at-risk transactions use purchase dates from
**June 12 – July 29, 2026**: a few days after packing begins, running
through a week *past* the recall's July 22 public announcement. That overrun
is intentional — it's what produces a non-trivial, positive lag-time number,
illustrating that recalled product can keep moving after the public notice
goes out.

Noise transactions deliberately include unrelated lot codes even when their
state matches an affected state — the match engine has to actually check
`lot_code`, not just geography, to keep noise out.

## Deployment

**Live at [recall-trace.streamlit.app](https://recall-trace.streamlit.app/).**

This app deploys to **[Streamlit Community Cloud](https://share.streamlit.io)**
— free, no credit card required, deploys directly from a public GitHub repo.
It's the standard choice for a demo at this scale: no infrastructure to
provision or pay for, no servers to manage, and it's purpose-built for
exactly this kind of single-file Streamlit app.

Because `synthetic_transactions.csv` and `seed_recall_record.json` are both
committed to the repo, **the deployed app works instantly for any visitor**
— it never needs a live external API call to render something meaningful,
even though `fetch_recall.py` still attempts the live openFDA call first.

To redeploy (or deploy your own fork):

1. Push this repo to GitHub (if you're reading this, it likely already is).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click "New app," pick this repo and branch, and set `app.py` as the
   entrypoint.
4. Deploy. That's it — no secrets, no config beyond what's already in
   `.streamlit/config.toml`.

## Limitations, by design

- All transaction/loyalty data is synthetic. No real customer data is used
  or was ever available to this project.
- The openFDA live lookup in `fetch_recall.py` is best-effort and
  non-blocking — a network failure, timeout, or empty result silently falls
  back to the seed record. Availability matters more than granular error
  handling for a demo like this.
- The notification queue never sends anything. There's no email/SMS
  integration anywhere in this codebase, on purpose.
- No authentication, no user accounts, no database — this is a stateless
  demo over flat files.

## Stack

Python 3.11 · Streamlit · pandas · Faker
