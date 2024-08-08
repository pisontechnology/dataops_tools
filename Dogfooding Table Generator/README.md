# Unified Reaction Test Data [Tables & Dashboards]

**Owned by:** Edward Lai  
**Last updated:** 3 minutes ago  
**Read Time:** 3 min  

**Demo Link:** [Ed's Playground](#)

## Objective

The primary goal of this project is to unify various datasets related to Pison’s reaction tests into a single, comprehensive DataFrame. This unified dataset aims to enhance the accuracy of insights concerning DogFooding.

## Data Sources

**Date Range:** May 1st to August 7th

### User Information Dataset (`user_df`)
- **Description:** Contains user-related information such as email, displayName, photoUrl, and username.
- **Source:** `from query.microservices import get_users`

### Metadata Dataset (`metadata_df`)
- **Description:** Includes session and device metadata such as application_id, device_id, and device_version.
- **Source:** `from query.microservices import get_all_metadata`

### Algorithm Calculations Dataset (`algo_calculations_df`)
- **Description:** Contains calculated algorithm data like mean reaction time, accuracy, etc.
- **Source:** Uses `get_algo_calculations` function to generate the DataFrame.

### Reaction Tests Dataset (`tests_df`)
- **Description:** Includes reaction test data including reaction_test_type, user_id, session_id, team_id, and various enrichment fields.
- **Source:** `from query.microservices import get_reaction_tests`

### Pison Team Dataset (`pison_team_df`)
- **Description:** Contains user’s Pison team information.
- **Source:** `pison_users.csv`

## Merging Process

1. **Load DataFrames**
2. **Filter Specific Users**
3. **Merge DataFrames**
   - Merge `tests_df` with `user_df`
   - Merge the result with `metadata_df`
   - Merge the result with `algo_calculations_df`
   - Merge the result with `pison_team_df`
4. **Clean and Process DataFrame**
   - Return Final DataFrame

### Key Features

- **Specific User Filtering:** Filters user data to include only relevant users.
- **Improved Data Quality:**
  - Removes unnecessary columns
  - Converts specific columns to numerical formats
  - Converts `is_failed` column to boolean and replaces NaN values with False
- **Flexible Merging Process:** Easily adjust which tables (READY, AGILITY, or FOCUS) to build by modifying a single variable (`test_type`).
- **BigQuery Integration:** Ensure destination table adjustments as per user needs.

### Column Names Pairing & Flow Chart

![Flow Chart](image-20240806-132533.png)

### Explanation

- **Unified Reaction Test Data [Total Records]**
  - ![Total Records](Screenshot%2024-08-05%20at%204.15.16%20PM.png)
- **Unified Reaction Test Data [Failed Records]**
  - ![Failed Records](Screenshot%2024-08-06%20at%204.23.41%20PM.png)
- **Unified Reaction Test Data [Agility Records]**
  - ![Agility Records](Screenshot%2024-08-06%20at%204.26.51%20PM.png)

### Schema

The final schema for the merged DataFrame is:

| **Column Name**                                | **Data Type** | **Dataset of Origin**               |
|------------------------------------------------|---------------|-------------------------------------|
| `id`                                           | STRING        | Reaction Tests Dataset               |
| `reaction_test_type`                          | STRING        |                                     |
| `user_id`                                     | STRING        |                                     |
| `session_id`                                  | STRING        |                                     |
| `team_id`                                     | FLOAT         |                                     |
| `comment`                                     | STRING        |                                     |
| `created_at`                                  | TIMESTAMP     |                                     |
| `is_failed`                                   | BOOLEAN       |                                     |
| `score`                                       | FLOAT         |                                     |
| `plan_duration_in_seconds`                    | FLOAT         |                                     |
| `sw_enrichment_data_number_of_trials`         | FLOAT         |                                     |
| `sw_enrichment_data_number_of_false_starts`   | FLOAT         |                                     |
| `sw_enrichment_data_number_of_lapses`         | FLOAT         |                                     |
| `sw_enrichment_data_mean_reaction_time`       | FLOAT         |                                     |
| `sw_enrichment_data_stdev_reaction_time`      | FLOAT         |                                     |
| `sw_enrichment_data_accuracy`                 | FLOAT         |                                     |
| `baseline_id`                                 | STRING        |                                     |
| `is_deleted`                                  | STRING        |                                     |
| `email`                                       | STRING        | User Information Dataset             |
| `displayName`                                 | STRING        |                                     |
| `photoUrl`                                    | STRING        |                                     |
| `username`                                    | STRING        |                                     |
| `algo_enrichment_data_mean_reaction_time`     | FLOAT         | Algorithm Calculations Dataset       |
| `algo_enrichment_data_accuracy`               | FLOAT         |                                     |
| `algo_enrichment_data_stdev_reaction_time`    | FLOAT         |                                     |
| `algo_enrichment_data_number_of_trials`       | FLOAT         |                                     |
| `algo_enrichment_data_number_of_false_starts` | FLOAT         |                                     |
| `algo_enrichment_data_number_of_lapses`       | FLOAT         |                                     |
| `application_id`                              | STRING        | Metadata Dataset                     |
| `device_id`                                   | STRING        |                                     |
| `device_version`                              | STRING        |                                     |
| `pison_team`                                  | STRING        | Pison Team Dataset                   |

## Dashboards

- **[Ed’s Playground →](#)**
  - Key Features
- **[Anarchy Playground →](#)**
  - Key Features
- **[Agility Playground →](#)**
  - Key Features

## Conclusion

This unified dataset provides a comprehensive view for tracking data quality and identifying issues with reaction test data. By combining datasets into a consistent format, it simplifies analysis and dashboard creation. Use this dataset to investigate the causes of failed tests and assess the impact of factors like firmware or devices.

## Additional Notes & Bugs

### Data Quality [Columns]

**High Proportion of Missing Values:**

- `team_id`: 100% NaN values
- `sw_enrichment_data_number_of_lapses`: 100% NaN values
- `is_deleted`: 100% NaN values
- `algo_enrichment_data_mean_reaction_time`: 100% NaN values
- `algo_enrichment_data_accuracy`: 100% NaN values
- `algo_enrichment_data_stdev_reaction_time`: 100% NaN values
- `algo_enrichment_data_number_of_trials`: 100% NaN values
- `algo_enrichment_data_number_of_false_starts`: 100% NaN values
- `algo_enrichment_data_number_of_lapses`: 100% NaN values

**Significant Proportion of Missing Values:**

- `session_id`: 67.06% NaN values
- `baseline_id`: 64.17% NaN values
- `application_id`: 69.95% NaN values
- `device_id`: 69.95% NaN values
- `device_version`: 69.95% NaN values
- `sw_enrichment_data_number_of_false_starts`: 59.21% NaN values
- `sw_enrichment_data_mean_reaction_time`: 17.51% NaN values
- `sw_enrichment_data_stdev_reaction_time`: 19.77% NaN values
- `sw_enrichment_data_accuracy`: 17.51% NaN values
- `plan_duration_in_seconds`: 15.52% NaN values
- `sw_enrichment_data_number_of_trials`: 15.52% NaN values
- `score`: 11.82% NaN values
- `photoUrl`: 8.39% NaN values
- `displayName`: 23.01% NaN values

**Column Naming Conventions:**

BigQuery column names can only contain letters (a-z, A-Z), numbers (0-9), or underscores (_). For example, `algo_enrichment` should be used instead of `algo-enrichment`.

**List of Dropped Columns:**

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

**Error Writing to BigQuery:**

- Error converting Pandas column `"sw_enrichment_data_mean_reaction_time"` with datatype `"object"` to an appropriate pyarrow datatype.
- **Common BigQuery Problem:** Data stored in nested fields must be flattened to be compatible with BigQuery.

**Flattening Columns:**

```python
df[column] = pd.to_numeric(df[column], errors='coerce')
