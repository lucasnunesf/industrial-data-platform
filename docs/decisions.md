# Technical decisions

Short architecture decision records (ADRs), in the order they were made.

## ADR-001: Incremental extraction from the ERP to Parquet

**Status:** accepted

**Context.** The ERP runs on PostgreSQL. Twelve tables are mutable and carry an `updated_at` column maintained by a trigger. Two tables (`production_stage_events`, `quality_inspections`) are append-only and have an increasing primary key.

**Decision.**
- Mutable tables are extracted by `updated_at` with a per-table watermark; append-only tables by primary key.
- All tables are read in one `REPEATABLE READ`, read-only transaction, so they share a single consistent snapshot. The upper bound of each window is the database `now()` taken at the start of the run.
- The Arrow schema is derived from `information_schema.columns`, so decimal precision matches the source exactly.
- Each row gets `_extracted_at` and `_batch_id`. Files are written as `erp/<table>/ingestion_date=YYYY-MM-DD/<table>_<run_id>.parquet`, and state is stored in `_state/watermarks.json`.
- Bronze is append-only. The state is saved after each table, so delivery is at-least-once.

**Consequences.**
- A row updated twice appears in two files; silver keeps the latest version per primary key.
- A transaction that commits after the cutoff but carries an older `updated_at` can be missed. The simulator does not produce this case; a production setup would add an overlap window.

## ADR-002: Microsoft Fabric for processing and serving

**Status:** accepted

**Context.** The data volume is small (14 tables, thousands of rows per day) and consumption is a Power BI report.

**Decision.**
- Bronze stays in ADLS Gen2, provisioned with Terraform together with Key Vault.
- Silver is built with PySpark notebooks in Microsoft Fabric and stored as Delta tables.
- Gold is a star schema modeled with dbt (`dbt-fabric`) in a Fabric Warehouse, with tests.
- Power BI reads from a semantic model on top of the gold layer.

**Alternatives considered.**
- Azure Databricks: more flexible for Spark and machine learning, multi-cloud, and stronger governance with Unity Catalog. For this size, running and sizing clusters adds more operational work than it returns.

**Consequences.**
- Fabric runs only on Azure and is billed by capacity; the trial capacity is limited to 60 days.
- The Terraform code covers the lake and secrets; the Fabric workspace is created in the portal.

## ADR-003: Azure region for the data lake

**Status:** accepted

**Context.** Creating the storage account and the Key Vault in West Europe was rejected by Azure for this subscription (`RequestDisallowedByAzure: the selected region is currently not accepting new customers`). Trial subscriptions can be restricted in some regions.

**Decision.** The lake and the Key Vault are created in Brazil South, which the subscription accepts. The region is the default of the `location` variable in `infra/variables.tf`.

**Consequences.**
- All resources of the environment share one region.
- The data is synthetic, so data residency is not a concern.
- Moving to another region later means recreating the storage account, because its region cannot be changed in place.

## ADR-004: Bronze reaches Fabric through an ADLS Gen2 shortcut

**Status:** accepted

**Context.** The lake lives in the Azure subscription and the Fabric workspace belongs to a different Microsoft Entra tenant, so Fabric cannot read the storage with the signed-in identity.

**Decision.**
- The Parquet files are uploaded to the `bronze` filesystem of the ADLS Gen2 account with `ingestion/upload.py`, using the `az login` identity and the Storage Blob Data Contributor role.
- The Fabric Lakehouse `lh_industrial` reads them in place through a OneLake shortcut to `bronze/erp`, authenticated with a read-only (Read, List) shared access signature on the storage account.

**Alternatives considered.**
- Uploading the files straight to OneLake: works without cross-tenant access, but leaves the lake and its Terraform code unused by Fabric.
- Account key: works, but gives full control of the storage account.

**Consequences.**
- The data is not copied: Fabric reads the lake directly, and both are in Brazil South.
- The SAS token expires and has to be renewed; it is kept only in the Fabric connection.
- Silver notebooks read from the shortcut and write Delta tables to the Lakehouse.

## ADR-005: Silver is a full rebuild with the latest version per key

**Status:** accepted

**Context.** Bronze is append-only, so a row updated twice appears in two files (`sales_orders` had 412 rows in bronze for 390 distinct orders). The Lakehouse reads bronze through the shortcut from ADR-004.

**Decision.**
- One parametrized PySpark notebook (`processing/silver/01_build_silver.py`) reads each table from `Files/erp`, keeps the latest row per primary key (`updated_at`, then `_extracted_at`; event tables use `_extracted_at`) and overwrites the Delta table `silver_<table>`.
- A second notebook (`02_test_silver.py`) checks that silver has the same number of keys as bronze, primary keys are unique and not null, foreign keys have no orphans and status columns hold only accepted values. It fails the run if any check fails.

**Alternatives considered.**
- Incremental merge into silver: avoids reprocessing, but adds state and complexity that 14 small tables do not need.

**Consequences.**
- Each run reprocesses all of bronze; this is acceptable at the current volume and would be revisited with `MERGE` if it grows.
- The notebooks need `lh_industrial` attached as the default lakehouse. Without it, relative paths such as `Files/erp` fail with `400 Bad Request` and `saveAsTable` has no target.
- The trial capacity allows few concurrent Spark sessions, so sessions should be stopped after each run.

## ADR-006: Gold layer design and dbt connection

**Status:** accepted

**Context.** The gold layer is built with `dbt-fabric` on a Fabric Warehouse. The Warehouse belongs to a different Microsoft Entra tenant than the Azure subscription. The business questions are bottlenecks, lead time per stage and on-time delivery.

**Decision.**
- Two facts at different grains: `fct_stage_execution` (one row per production order and routing step, with `duration_minutes` and `wait_minutes`, the gap since the previous stage finished) and `fct_order_delivery` (one row per sales order, with `lead_time_days`, `days_late` and `is_on_time`).
- Four dimensions: customer, product, work center and machine.
- Staging models are views over the silver tables of the Lakehouse (`lh_industrial.dbo.silver_*`); marts are tables in the `gold` schema. A `generate_schema_name` macro makes the schemas `staging` and `gold` instead of `dbo_staging` and `dbo_gold`.
- dbt authenticates with `authentication: CLI`: the adapter takes the token from the `az login` session. The SQL endpoint comes from the `FABRIC_SQL_HOST` variable, so no secret or host is stored in the repository.
- 22 data tests: keys, relationships, accepted values, plus singular tests for the fact grain and for finish after start.

**Alternatives considered.**
- `ActiveDirectoryInteractive`: failed with `Failed to authenticate the user ''`, because the adapter hands this mode to the driver without passing a user name.
- A date dimension: left out of the MVP; Power BI uses the date columns of the facts.

**Consequences.**
- `wait_minutes` includes nights and weekends, because the simulated plant runs one shift from Monday to Friday. It compares stages with each other but is not real idle time.
- A `dim_date` should be added if date-based analysis grows.
- Running dbt needs an `az login` session for the Fabric account; when it differs from the Azure account, use a separate `AZURE_CONFIG_DIR`.
