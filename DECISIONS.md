# Engineering Decisions
## AI SaaS Retention & Competitive Intelligence Platform

Each decision below follows the same format:
- **Decision** — what we chose
- **Options considered** — what we evaluated
- **Why chosen** — reasoning
- **Tradeoffs** — what we gave up

---

## 1. Warehouse: PostgreSQL (local) over SQLite or CSV files

**Decision:** Use PostgreSQL as the local warehouse during development.

**Options considered:**
- SQLite — simpler, file-based, no setup
- CSV files — no database needed at all
- PostgreSQL — full relational database with schemas

**Why chosen:**
PostgreSQL supports multiple schemas (raw, staging, marts), enforces constraints like NOT NULL and UNIQUE, and works identically to production cloud warehouses. It also integrates natively with dbt without any workarounds.

**Tradeoffs:**
Requires local installation and service management. SQLite would have been simpler to set up but doesn't support the schema separation that our warehouse architecture requires.

---

## 2. Transformation Layer: dbt Core over plain SQL scripts

**Decision:** Use dbt Core for all data transformations instead of writing raw SQL scripts.

**Options considered:**
- Plain SQL scripts run via psycopg2
- Pandas transformations in Python
- dbt Core

**Why chosen:**
dbt enforces modular SQL, tracks lineage automatically via ref() and source(), generates documentation, and makes testing a first-class citizen. A plain SQL script has none of these properties — it's just a file with no dependency tracking, no tests, and no documentation.

**Tradeoffs:**
dbt adds a learning curve and requires understanding of profiles, project configuration, and materialization strategies. Plain SQL scripts are simpler to write but don't scale and become unmaintainable quickly.

---

## 3. Materialization: Views for staging, Tables for marts

**Decision:** Staging models are materialized as views, marts models as tables.

**Options considered:**
- All views — lightweight, always fresh
- All tables — fast to query, stored physically
- Mixed — views for staging, tables for marts

**Why chosen:**
Staging models are just cleaning raw data — they're lightweight and don't need to be stored physically. Views always reflect the latest raw data. Marts models contain heavy aggregations (joining 500k users with 500k reviews) that would be slow to recompute on every query — storing them as tables makes dashboard queries fast.

**Tradeoffs:**
Tables take up storage and need to be rebuilt when upstream data changes. Views are always fresh but rerun the SQL on every query.

---

## 4. Behavioral Dataset: Yelp over synthetic data

**Decision:** Use the Yelp Academic Dataset as the behavioral engagement proxy.

**Options considered:**
- Synthetic data generated with Faker
- Amplitude/Mixpanel sample datasets
- Yelp Academic Dataset

**Why chosen:**
Yelp is real data with real temporal patterns — actual users, actual timestamps, actual engagement signals going back to 2004. Synthetic data would produce unrealistically clean distributions and wouldn't stress-test the pipeline the way real messy data does. Yelp also has 6M+ reviews, providing genuine scale.

**Tradeoffs:**
Yelp reviews are a proxy for SaaS engagement, not actual product events. The mapping (review = engagement event, user = app user) requires assumptions. A real Mixpanel or Amplitude export would be more direct but isn't freely available at scale.

---

## 5. Ingestion: Product Hunt API over web scraping

**Decision:** Use Product Hunt's GraphQL API instead of scraping their website.

**Options considered:**
- BeautifulSoup HTML scraping
- Selenium browser automation
- Product Hunt GraphQL API

**Why chosen:**
The API is official, stable, and returns structured data. Scraping HTML is fragile — website structure changes break scrapers silently. GraphQL lets us request exactly the fields we need, reducing wasted data. Using an official API also respects the platform's terms of service.

**Tradeoffs:**
API rate limits restrict how much data we can pull per request. Scraping could theoretically get more data faster, but at the cost of reliability and legality.

---

## 6. Batch Size: 10,000 rows per chunk for Yelp ingestion

**Decision:** Load Yelp data in batches of 10,000 rows, capped at 500,000 total.

**Options considered:**
- Load entire file at once
- Load 1,000 rows per batch
- Load 10,000 rows per batch

**Why chosen:**
Loading 6GB at once would exhaust local memory and likely crash the process. 1,000 rows per batch would work but would require 6,000+ database round trips for the full dataset. 10,000 rows balances memory safety with ingestion speed — each batch is large enough to be efficient but small enough to never overwhelm the database.

**Tradeoffs:**
Larger batches are faster but riskier. If a batch fails, we lose 10,000 rows of progress. We mitigate this with conn.rollback() on failure so partial batches never corrupt the database.

---

## 7. Survival Analysis: Kaplan-Meier over simple retention curves

**Decision:** Use Kaplan-Meier survival analysis in addition to cohort retention curves.

**Options considered:**
- Cohort retention curves only
- Kaplan-Meier survival analysis
- Cox Proportional Hazards model

**Why chosen:**
Cohort retention curves show retention for specific cohorts. Kaplan-Meier pools all cohorts together to estimate overall survival probability — it handles censored data (users still active) correctly and produces statistically defensible results. It's also widely used in subscription analytics and SaaS churn modeling, making it directly relevant to industry roles.

**Tradeoffs:**
Kaplan-Meier assumes survival times are independent across users, which may not hold if users influence each other. Cox Proportional Hazards would give us covariate-adjusted survival estimates but adds significant complexity.

---

## 8. ML Model: XGBoost over Logistic Regression

**Decision:** Use XGBoost for churn prediction instead of Logistic Regression.

**Options considered:**
- Logistic Regression — simple, interpretable
- Random Forest — ensemble, robust
- XGBoost — gradient boosting, high performance

**Why chosen:**
XGBoost handles non-linear relationships between features and churn probability better than Logistic Regression. It also produces feature importance scores natively, which directly answers the business question "what drives churn?" It achieved 0.71 AUC-ROC on our dataset.

**Tradeoffs:**
XGBoost is less interpretable than Logistic Regression. A stakeholder asking "why is this user predicted to churn?" gets a harder answer from XGBoost than from a simple linear model. SHAP values could address this in V2.

---

## 9. CI/CD: GitHub Actions over Airflow or no automation

**Decision:** Use GitHub Actions for CI/CD instead of a full orchestration tool.

**Options considered:**
- No automation — run dbt manually
- Airflow — full pipeline orchestration
- GitHub Actions — lightweight CI/CD

**Why chosen:**
GitHub Actions is free, requires no additional infrastructure, and integrates directly with the existing GitHub repository. Airflow would be more powerful for scheduling complex pipelines but is heavyweight for a portfolio project. GitHub Actions gives us automated testing on every push with minimal setup.

**Tradeoffs:**
GitHub Actions is a CI/CD tool, not a full orchestrator. It can't schedule nightly ingestion runs or handle complex dependency graphs between pipeline steps the way Airflow can. For production, Airflow or Prefect would be the right choice.