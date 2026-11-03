# Dataset Notes

## Source

`data/generators/generate_mock_data.py` generates a synthetic retail/marketing
dataset with a known, controllable treatment effect (Volume I Chapter
7.1), so pipeline correctness can be validated against a known ground
truth during development. A pre-generated sample is committed at
`data/raw/mock_campaign.csv` for convenience (small enough to version;
larger datasets should not be committed — see `.gitignore`).

## Columns

| Column | Role | Notes |
|---|---|---|
| `tenure_months` | Confounder | Integer months as a customer. |
| `past_purchase_frequency` | Confounder | Historical purchase count. |
| `loyalty_score` | Confounder | 0-1 continuous loyalty score. |
| `avg_order_value` | Confounder | Historical average order value. |
| `treatment` | Treatment | Historical discount offered: 0, 10, or 20. |
| `outcome` | Outcome | 1 if the customer purchased, else 0. |

## Cleaning Rules

See `backend/app/pipeline/cleaning.py`: column names are normalized to
snake_case, exact duplicate rows are removed, and rows with a missing
`treatment` or `outcome` value are dropped.

## Confounder Rationale

`loyalty_score` and `past_purchase_frequency` influence both historical
discount targeting (marketing teams favor loyal, frequent customers) and
purchase outcome directly — the textbook definition of a confounder
(Volume I Chapter 1.8). Both are included as common causes in the DoWhy
DAG (`backend/app/pipeline/causal_graph.py`).
