Warehouse Architecture Notes
Layer 1 – Raw
Purpose: Store unmodified source data
Contains: scraped data, imported CSVs
Rule: Never transform raw tables
Layer 2 – Staging
Purpose: Clean and standardize data
Operations:
Rename columns
Cast data types
Handle nulls
Standardize formats
Built using dbt models
Layer 3 – Marts
Purpose: Business logic & metrics
Contains:
Fact tables
KPI definitions
Aggregated metrics
Used for dashboards and analysis


“dbt_project.yml is YAML and indentation defines hierarchy. Folder-based configs must be nested under the project name to apply to models. I configured staging and marts schemas so layering is enforced by tooling.”