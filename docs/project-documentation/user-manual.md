# User Manual

## 1. Upload a Dataset

On the New Campaign page, choose a CSV file with a `treatment` column (the
historical discount amount), an `outcome` column (0 or 1), and any
number of confounder columns (e.g., `loyalty_score`, `tenure_months`).
Map the columns if auto-detection is incorrect, enter a total promotional
budget, configure discount levels, then click **Run campaign**.

## 2. Understanding the Dashboard

- **Summary Panel**: a plain-language estimate of how much incremental
  uplift the causal, budget-optimal strategy captures compared to giving
  everyone the same average discount.
- **Uplift Curve**: shows cumulative predicted uplift as you target
  customers in order of highest estimated benefit (ITE) first, compared
  to random targeting. The causal model's line should sit above the
  random-targeting line — the gap is the value the model adds.
- **Qini Curve**: shows the same idea as incremental gain over random
  targeting directly; a curve that rises above zero and stays there
  demonstrates the model is finding real, persuadable customers.
- **Allocation Matrix**: the final table of which customer gets which
  discount, and how much of the budget each choice uses. Totals always
  reconcile with the budget you entered.
- **Causal Refutation Tests**: PASS/FAIL results proving the estimated
  effect is not just an artifact of confounding or noise.

## 3. Interpreting One ITE Value

An ITE value of, say, 0.08 for customer #101 at a $10 discount means:
offering that specific customer a $10 discount is estimated to increase
their purchase probability by 8 percentage points, above and beyond
whatever they would have done anyway.
