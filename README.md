# EconoCausal
AI-powered causal inference and dynamic pricing with budget optimization.
Estimate price effects using cross-fitting and ML nuisance models
Evaluate and visualize
Causal effect, uncertainty, revenue and profit scenarios
Important: DML helps adjust for observed confounding variables, but it does not automatically prove causation. Reliable estimates still depend on assumptions, data quality, and the pricing process.
Account for market competition
product_category Compare product groups
cost_per_unit Calculate profit
store_id Control for store differences
Not all these variables exist in the public datasets above. Record which fields are observed, derived or unavailable. Never silently fabricate real-world data.
Important research decision: transaction-level sales data alone cannot reliably identify the causal effect of price if pricing decisions depend on expected demand. For a stronger study, seek store-product-day data with historical prices, promotions and relevant demand drivers, ideally supplemented by randomized price experiments.
Show the estimate, confidence interval and differences across product categories.
Pricing scenario simulator
Compare baseline pricing with alternative prices and predicted demand and profit.
Illustrative dashboard only. The dashes are placeholders, not actual analytical results.
Suggested technology stack
Python and pandas — data collection, cleaning and transformation.
scikit-learn and EconML — machine learning and causal-effect estimation.
Streamlit and Plotly — interactive dashboard and charts.
Google Colab — a practical browser-based environment for initial development.
Read the EconML documentation for available DML estimators. 
