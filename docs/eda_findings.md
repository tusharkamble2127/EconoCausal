# EconoCausal: Dynamic Pricing via Double Machine Learning

## 1. Dataset Overview
- Dataset: Retail Price Optimization
- Records: 676
- Columns: 30
- Distinct products: 52
- Exact duplicate rows: 0

## 2. Initial Data Quality Findings
- The displayed dataset columns contain 676 non-null values.
- Missing values were checked during initial EDA.
- The maximum absolute difference between total_price
  and unit_price multiplied by qty is approximately 147.55.
- The cause of these differences requires investigation.

## 3. Distribution Findings
- Unit prices show a right-skewed distribution.
- Quantity also shows a right-skewed distribution.
- Unit price and quantity have a weak negative overall
  correlation of approximately -0.103.

## 4. Time-Based Findings
- Average unit prices generally decline over the observed period.
- Total quantity varies substantially across months.
- These trends are descriptive and do not establish causation.

## 5. Product-Level Price Variation
- Products analyzed: 50.
- Products with changing prices: 50.
- Products with constant prices: 2.
- Average price range across products: approximately 27.68.

## 6. Product-Level Correlations
- Negative correlations: 32.
- Positive correlations: 15.
- Near-zero correlations: 3.
- Mean correlation: approximately -0.142.
- Median correlation: approximately -0.233.
- Minimum correlation: approximately -0.905.
- Maximum correlation: approximately +0.953.

## 7. Initial Interpretation
The observed price-quantity relationship differs across products.
Some products have negative correlations, while others have
positive correlations.

These results describe associations and do not establish
the causal effect of price on demand.

## 8. Limitations and Next Steps
- Investigate the definitions of price and quantity variables.
- Investigate discrepancies in total_price calculations.
- Identify appropriate confounding variables.
- Account for product-level and time-related differences.
- Assess whether the dataset supports credible causal estimation.
- Do not interpret correlations as causal effects.