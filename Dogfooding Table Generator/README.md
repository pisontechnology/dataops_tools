# Dogfooding Tables & Dashboards

## Overview

**Owned by:** Edward Lai  

## Files Included

- `tables.ipynb`
- `README.md`
- `module_101_217.py`

## Files Excluded

- `key.json` (BigQuery)
- `pison_users.csv`
- `dependancies.tar` (for Setup)

## Objective

The primary objective of this project is to merge various datasets related to Pison’s reaction tests into a comprehensive DataFrame. This unified dataset will enhance the accuracy of insights related to Dogfooding.

## Data Sources

**Date Range:** May 1st to August 15th

- **User Information Dataset (`user_df`):** Contains user-related information such as email, displayName, photoUrl, and username.
  - Data Source: `from query.microservices import get_users`

- **Metadata Dataset (`metadata_df`):** Includes metadata related to sessions and devices including application_id, device_id, and device_version.
  - Data Source: `from query.microservices import get_all_metadata`

- **Algorithm Calculations Dataset (`algo_calculations_df`):** Contains calculated algorithm data such as mean reaction time, accuracy, etc.
  - Data Source: Uses `get_algo_calculations` function

- **Reaction Tests Dataset (`tests_df`):** Contains reaction test data including reaction_test_type, user_id, session_id, team_id, and various sw-enrichment fields.
  - Data Source: `from query.microservices import get_reaction_tests`

- **Pison Team Dataset (`pison_team_df`):** Contains user’s Pison team information.
  - Data Source: `pison_users.csv` (No trailing spaces this time :sweat: )

## Merging Process

1. **Load DataFrames**  
2. **Filter Specific Users**  
3. **Merge DataFrames**
   - Merge `tests_df` with `user_df`
   - Merge result with `metadata_df`
   - Merge result with `algo_calculations_df`
   - Merge result with `pison_team_df`
4. **Clean and Process DataFrame**  
5. **Return Final DataFrame**

## Key Features

- **Specific User Filtering:** Includes only relevant users for analysis.
- **Improved Data Quality:** Removes unnecessary columns, flattens data types, and converts columns to appropriate formats.
- **Flexible Merging Process:** Easily adjust which tables (READY, AGILITY, or FOCUS) to build by modifying a single variable (`test_type`).
- **Schema Adjustments:** Change destination table in BigQuery as needed.

## Schema (Big_df)

| Column Name                             | Data Type | Dataset of Origin                        |
|-----------------------------------------|-----------|------------------------------------------|
| id                                      | STRING    | Reaction Tests Dataset                   |
| reaction_test_type                      | STRING    |                                          |
| user_id                                 | STRING    |                                          |
| session_id                              | STRING    |                                          |
| team_id                                 | FLOAT     |                                          |
| comment                                 | STRING    |                                          |
| created_at                              | TIMESTAMP |                                          |
| is_failed                               | BOOLEAN   |                                          |
| score                                   | FLOAT     |                                          |
| plan_duration_in_seconds                | FLOAT     |                                          |
| sw_enrichment_data_number_of_trials     | FLOAT     |                                          |
| sw_enrichment_data_number_of_false_starts | FLOAT   |                                          |
| sw_enrichment_data_number_of_lapses     | FLOAT     |                                          |
| sw_enrichment_data_mean_reaction_time   | FLOAT     |                                          |
| sw_enrichment_data_stdev_reaction_time  | FLOAT     |                                          |
| sw_enrichment_data_accuracy             | FLOAT     |                                          |
| baseline_id                             | STRING    |                                          |
| is_deleted                              | STRING    |                                          |
| email                                   | STRING    | User Information Dataset                 |
| displayName                             | STRING    |                                          |
| photoUrl                                | STRING    |                                          |
| username                                | STRING    |                                          |
| algo_enrichment_data_mean_reaction_time | FLOAT     | Algorithm Calculations Dataset           |
| algo_enrichment_data_accuracy           | FLOAT     |                                          |
| algo_enrichment_data_stdev_reaction_time| FLOAT     |                                          |
| algo_enrichment_data_number_of_trials  | FLOAT     |                                          |
| algo_enrichment_data_number_of_false_starts | FLOAT |                                          |
| algo_enrichment_data_number_of_lapses   | FLOAT    |                                          |
| application_id                          | STRING    | Metadata Dataset                         |
| device_id                               | STRING    |                                          |
| device_version                          | STRING    |                                          |
| pison_team                              | STRING    | Pison Team Dataset                       |

## BigQuery Tables Locations

# Total Tests Dashboards

## The Engagement Dashboard [Engagement]

Designed to track and analyze the engagement levels of Dogfooders at Pison.

- **Features:**
  - View how frequently users perform tests and assess their activity levels.
  - Compare engagement by test type, team, and individual user.
  - Leaderboard displays average scores for each test.
  - Track engagement trends over time to identify patterns in user activity and team performance.

## The Tests Failed Dashboard [Failed Tests]

Designed to track and analyze the percentage of tests that have failed.

- **Features:**
  - Categorizes failures based on test type, software version, firmware version, and device ID.
  - Focuses on technical aspects of the tests to identify patterns and potential issues leading to test failures.
  - Does not account for team affiliations.

## The Parity Land Dashboard [Parity Land]

Designed to compare and identify parity between calculations performed by the algorithms team and the software team.

- **Features:**
  - Tracks key metrics: mean reaction time, standard deviation of reaction time, number of trials, false starts, and lapses across all three tests.
  - Ensures consistency and accuracy between different calculation methodologies and teams.
  - Helps identify discrepancies or alignment issues in the testing data.

## Conclusion

This merged dataset can be used to track data quality and identify issues and bugs. By combining all datasets related to reaction test data, we ensure access to all relevant information in a consistent format. This facilitates easier analysis, dashboard creation, and future analysis. Use this dataset to understand failed tests, identify contributing factors like firmware or devices, and assess parity between the algorithm team and the software team.

## Summary of Issues Range [May 1st to August 15th]

### High Number of NaNs in Key Columns:

#### Ready_Table

- **NaNs:**
  - `team_id` column: 2084 out of 2084 (100.00%)
  - `algo_enrichment_data*` columns: 1828 out of 2084 (87.72%)
  - `application_id`, `device_id`, `device_version` columns: 1766 out of 2084 (84.74%)

  **Note:** Algo calculations for Ready Tests appear in mid-May and mid-June but are lacking elsewhere.

#### Agility Table

- **NaNs:**
  - `team_id` column: 416 out of 416 (100.00%)
  - `score` column: 32 out of 416 (7.69%)
  - `algo_enrichment_data*` columns: 42 out of 416 (10.10%)
  - `application_id`, `device_id`, `device_version` columns: 301 out of 416 (72.36%)

  **Note:** Device services are only visible in EXPLORE.

#### Focus Table

- **Includes:** `fastest_10` and `slowest_10`
- **NaNs:**
  - `team_id` column: 538 out of 538 (100.00%)
  - `score` column: 23 out of 538 (4.28%)
  - `algo_enrichment_data*` columns: 92 out of 538 (17.10%)
  - `application_id`, `device_id`, `device_version` columns: 313 out of 538 (58.18%)

## Additional Notes

- We are utilizing functions from `dataops_tools/Dogfooding Table Generator/module_101_217.py`, specifically `pvt_score` and `verbose_output`, for generating the `algorithms_df` for Focus and Ready algorithms.
- Due to a bug with `configuration_color_blue`, we cannot use the same functions for Agility. We are using `generate_plan_df` and `get_modified_agility_score` instead.

### Known Issues

- **NaNs for `session_id`:** Expected and will appear since `session_id` is only available in the EXPLORE environment.
- **`team_id` Implementation:** This field has not been implemented in the current pipeline and should be noted for future development. (Different from `pison_team`)
- **Baseball Data:** Not integrated into current dashboards. To include, add `BASEBALL_DRILL` to the list of reaction test types during DataFrame creation.
- **Device Service:** Only available for Pison EXPLORE and Pantheon.
- **Column Naming:** Columns in BigQuery must contain letters, numbers, or underscores. Special characters are not supported and can cause errors in Google Looker Studio.

### List of Columns Dropped

- `customAttributes_subscription`
- `customAttributes_claims`
- `is_baseline`
- `model_identifier`
- `deletion_reason`
- `onset_moments`
- `plan_stimuli`
- `enrichment_data_number_of_hits`
- `enrichment_data_trial_results_trial_number`
- `enrichment_data_trial_results_is_hit`
- `enrichment_data_trial_results_onset_moment`
- `enrichment_data_trial_results_reaction_time`
- `enrichment_data_trial_results_is_false_start`
- `enrichment_data_trial_results_is_lapse`
- `plan_id`
- `plan_user_id`

### Error Writing to BigQuery

- **Issue:** Error converting Pandas column with name: `"sw_enrichment_data_mean_reaction_time"` and datatype: `"object"` to an appropriate `pyarrow` datatype.

  **Note:** Flatten columns to be "BigQuery-able". Common problem with data stored in nested fields or dictionaries.

- **Fix:**
  ```python
  df[column] = pd.to_numeric(df[column], errors='coerce')


    


