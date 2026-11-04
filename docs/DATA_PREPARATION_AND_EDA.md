\# Data Preparation and Exploratory Data Analysis (EDA)



\## 1. Overview



This document describes the data preparation and exploratory data analysis workflow implemented for the EconoCausal Dynamic Pricing project.



The workflow prepares campaign data for downstream causal analysis through data cleaning, treatment validation, feature engineering, and exploratory analysis.



\## 2. Data Cleaning



The cleaning module is implemented in:



`backend/app/pipeline/cleaning.py`



The cleaning pipeline performs the following operations:



\* Creates a copy of the input DataFrame to preserve the original data.

\* Normalizes column names by trimming whitespace, converting them to lowercase, and replacing spaces with underscores.

\* Checks whether the required treatment and outcome columns exist.

\* Removes duplicate rows.

\* Removes rows with missing treatment or outcome values.

\* Removes rows with missing model-feature values.

\* Excludes identifier columns such as `customer\_id` and `dataset\_id` from the feature completeness check.

\* Resets the DataFrame index after cleaning.



The module also includes treatment variation validation. It checks whether the treatment column contains the minimum required number of distinct values. Insufficient variation raises an appropriate validation error.



\## 3. Feature Engineering



The feature engineering module is implemented in:



`backend/app/pipeline/features.py`



The `engineer()` function prepares the variables required for causal analysis.



It performs the following operations:



\* Normalizes column names consistently.

\* Validates the treatment and outcome columns.

\* Separates the treatment variable (T) and outcome variable (Y).

\* Constructs the confounder feature matrix (X).

\* Excludes treatment, outcome, and identifier columns from X.

\* Applies one-hot encoding to categorical confounders using pandas.

\* Returns a FeatureSet containing X, T, Y, and feature names.



The implementation includes checks to prevent treatment and outcome leakage into the confounder matrix.



\## 4. Exploratory Data Analysis (EDA)



The EDA script is implemented in:



`scripts/eda\_mock\_campaign.py`



It performs exploratory analysis on the synthetic campaign dataset.



\### Required Columns



\* `tenure\_months`

\* `past\_purchase\_frequency`

\* `loyalty\_score`

\* `avg\_order\_value`

\* `treatment`

\* `outcome`



\### Analysis Performed



The script reports:



\* Dataset dimensions (rows and columns).

\* Column data types.

\* Total and column-wise missing values.

\* Duplicate row count.

\* Descriptive statistics for numerical columns.

\* Treatment distribution.

\* Outcome distribution.

\* Treatment-level summaries, including record counts, purchase rate, average order value, and average loyalty score.



The script accepts a custom input CSV path through the `--input` command-line argument.



Example:



`python scripts/eda\_mock\_campaign.py --input data/processed/mock\_campaign.csv`



The EDA output is descriptive and is not treated as proof of a causal relationship.



\## 5. Unit Testing



The data preparation modules have corresponding unit tests.



\### Cleaning Tests



`backend/tests/unit/test\_cleaning.py`



Tests cover duplicate removal, missing-value handling, required-column validation, column-name normalization, custom column names, original DataFrame preservation, and treatment variation validation.



\### Feature Engineering Tests



`backend/tests/unit/test\_features.py`



Tests cover X/T/Y separation, categorical encoding, custom column names, column normalization, and leakage prevention.



\### EDA Tests



`backend/tests/unit/test\_eda\_mock\_campaign.py`



Tests cover dataset information, treatment-level summaries, missing input files, and missing required columns.



\## 6. Scope and Limitations



This workflow focuses on data preparation and exploratory analysis. It provides structured inputs for subsequent causal analysis.



The EDA summaries describe patterns in the available dataset. They do not independently establish causal effects or prove that a pricing change caused a particular business outcome.



The synthetic campaign dataset is intended for development and testing of the workflow.



\## 7. Conclusion



The implemented data preparation pipeline provides cleaning, treatment validation, feature engineering, and exploratory analysis functionality.



These components help prepare consistent and validated data for the downstream causal modelling stages of the EconoCausal Dynamic Pricing project.



