# Technical decisions

Short architecture decision records (ADRs), in the order they were made.

## ADR-001: Incremental extraction from the ERP to Parquet

**Status:** accepted

**Context.** The ERP runs on PostgreSQL. Twelve tables are mutable and carry an `updated_at` column maintained by a trigger. Two tables (`production_stage_events`, `quality_inspections`) are append-only and carry a `created_at` column. Both timestamps come from `now()`, which is the start of the writing transaction, but a row becomes visible to other sessions only when that transaction commits.

**Decision.**
- Every table is extracted by a time column with a per-table watermark: `updated_at` for mutable tables, `created_at` for append-only tables.
- Each window starts a configurable overlap (default 60 minutes, `--overlap-minutes`) before the watermark, so a row committed after a run started is read by the next run.
- All tables are read in one `REPEATABLE READ`, read-only transaction, so they share a single consistent snapshot. The upper bound of each window is the database `now()` taken at the start of the run.
- The Arrow schema is derived from `information_schema.columns`, so decimal precision matches the source exactly.
- Each row gets `_extracted_at` and `_batch_id`. Files are written as `erp/<table>/ingestion_date=YYYY-MM-DD/<table>_<run_id>.parquet`, and state is stored in `_state/watermarks.json`.
- The run id is the run start in UTC with microseconds, and an existing bronze file is never overwritten: the run fails instead. A run id with one-second resolution let two runs in the same second write the same file name, and the second one replaced the first.
- Bronze is append-only. The state is saved after each table, so delivery is at-least-once.

**Consequences.**
- A row updated twice, or read again inside the overlap, appears in several files; silver keeps the latest version per primary key.
- A transaction that stays open longer than the overlap can still be missed. Exact alternatives are filtering by commit time with `track_commit_timestamp`, or change data capture from the write-ahead log (logical replication); both need server changes or a new tool.
- Append-only tables were first extracted by primary key. Sequence values are assigned at insert, not at commit, so with concurrent writers a lower id can commit after a higher one and be skipped; the time column with overlap closes that gap. Old integer watermarks restart from the epoch once.
- Both cases are covered by tests in `ingestion/tests` that commit a change after an extraction has started.

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
- `wait_minutes` and `duration_minutes` are wall-clock differences between events, so both include nights and weekends: the simulated plant runs one shift from Monday to Friday. They compare stages with each other but are not idle time or machine time. Working-time versions would need a shift calendar.
- The first stage of a routing (laser cutting) has no `wait_minutes`, because there is no previous stage to measure from.
- A `dim_date` should be added if date-based analysis grows.
- Running dbt needs an `az login` session for the Fabric account; when it differs from the Azure account, use a separate `AZURE_CONFIG_DIR`.

## ADR-007: Continuous integration checks code without cloud access

**Status:** accepted

**Context.** Until now every check ran by hand on one machine. The pipeline also depends on Azure and on a Fabric workspace in another tenant, both reached with a personal `az login` session (ADR-004, ADR-006).

**Decision.**
- A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every pull request and on every push to `main`, with four independent jobs:
  - `pytest ingestion/tests` against a PostgreSQL 17 service container, the same major version as the ERP;
  - `ruff check`, limited to real errors (undefined names, unused imports, syntax), not style;
  - `terraform fmt -check` and `terraform validate`, with `init -backend=false`, so no Azure credentials are needed;
  - `dbt parse` with a placeholder `FABRIC_SQL_HOST`, which checks the project, the Jinja and the references between models without opening a connection.
- The workflow has read-only permissions and uses no secrets.

**Alternatives considered.**
- Running `dbt build` and `terraform plan` in CI: they need credentials for Azure and for the Fabric tenant stored as GitHub secrets (a service principal), which this project does not have.

**Consequences.**
- CI catches broken Python, a broken extraction, invalid Terraform and a dbt project that does not compile. It does not catch a model that fails only when it runs on the Warehouse, or bad data; those are still caught by `dbt build` and by the silver checks when the pipeline runs.
- There is no deployment step, so this is continuous integration, not continuous delivery.

## ADR-008: Local Airflow with a manual gate for silver

**Status:** accepted

**Context.** The MVP pipeline is a PowerShell script (`orchestration/run_pipeline.ps1`): it runs the steps in order, but keeps no history, has no retries and shows nothing while it runs. The silver notebooks run in a Fabric workspace of another tenant, reached with a personal account (ADR-004, ADR-006).

**Decision.**
- Apache Airflow 3 runs locally in one container (`airflow standalone`), from its own compose file in `orchestration/airflow/`, so the ERP database does not depend on it. The UI is published on `127.0.0.1` only and has no login.
- One DAG, `industrial_pipeline`: `simulate_plant` → `extract_to_bronze` → `upload_to_lake` → `wait_for_silver` → `build_gold`. Each task is a `BashOperator` that calls the same scripts as the PowerShell runner; the repository is mounted read-only, except the bronze output folder.
- `wait_for_silver` is an `ApprovalOperator`: the run stops until a person runs the two notebooks in Fabric and approves the task in the UI.
- The pipeline tools live in three virtual environments inside the image (simulator/extraction/upload, dbt, Azure CLI), so their dependencies never clash with Airflow's.
- The upload and dbt tasks use two Azure CLI logins, one per tenant, selected with `AZURE_CONFIG_DIR` and kept in a Docker volume. No secret is stored in the repository or in Airflow.
- The DAG has no schedule and allows one active run: it runs on a laptop, has a manual step, and the extraction keeps its watermarks in a single state file.

**Alternatives considered.**
- Triggering the notebooks through the Fabric REST API: needs a service principal in the Fabric tenant, which this project does not have.
- Running each step in its own container (`DockerOperator`): closer to production, but the Airflow container would need access to the Docker socket of the host.

**Consequences.**
- Each step has logs, one automatic retry and a run history, and a failed step can be rerun alone.
- The pipeline is not fully automatic: without the approval, gold is not rebuilt.
- The image is large (about 5 GB), mostly because of the Azure CLI.
- The Airflow metadata is a SQLite file inside the container, so the run history is lost when the container is recreated. A production setup would use PostgreSQL and a scheduler separate from the web server.
