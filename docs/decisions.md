# Technical decisions

Short records of the main decisions, in the order they were made. Each one says what was decided, why, and what it costs.

## Limitations

- **Times include nights and weekends.** `wait_minutes` and `duration_minutes` are the difference between two timestamps. They compare stages with each other, but they are not machine time. Costs use `work_minutes`, the working time reported by the shop floor.
- **The first stage has no wait**, because wait is measured from the end of the previous stage.
- **Margin is a contribution margin.** Revenue minus material, processing and freight. It leaves out taxes, overhead and rework, and the prices and rates are simulated.
- **The exchange rate file is a snapshot.** Days after the download use the last rate.
- **CI checks the code, not the cloud data.** The silver checks and the dbt tests run in the pipeline.
- **The Airflow DAG was tested up to the extraction.** The PowerShell script is the path tested end to end.
- **Key Vault is created but not used.** Fabric reads the lake with a SAS token that expires and must be renewed ([runbook](runbook.md)).

## ADR-001: Incremental extraction to Parquet

- **Decision:** each run reads only the rows that changed since the last run, using `updated_at` for tables that change and `created_at` for event tables. Every window starts 60 minutes before the last watermark. All tables are read in one `REPEATABLE READ` transaction and written as Parquet with `_extracted_at` and `_batch_id`.
- **Why:** reading everything on every run does not scale. The overlap catches rows committed after a run started, and the single transaction keeps the tables consistent with each other.
- **Cost:** the same row can land in bronze more than once, so silver must remove duplicates. A transaction open longer than 60 minutes can still be missed.

## ADR-002: Microsoft Fabric for processing and serving

- **Decision:** bronze stays in Azure Data Lake Storage. Silver runs in Fabric notebooks, gold is built with dbt in a Fabric Warehouse, and Power BI reads the gold layer.
- **Why:** the volume is small (14 tables, a few thousand rows a day) and the output is a Power BI report. Fabric covers storage, SQL and Power BI in one place.
- **Cost:** Fabric runs only on Azure and is paid by capacity. The trial lasts 60 days.

## ADR-003: Azure region

- **Decision:** the lake is in Brazil South.
- **Why:** West Europe rejected new resources for this trial subscription.
- **Cost:** moving region later means creating a new storage account.

## ADR-004: Fabric reads the lake through a shortcut

- **Decision:** the Parquet files are uploaded to the `bronze` container. The Fabric Lakehouse reads them in place through a OneLake shortcut, with a read-only SAS token.
- **Why:** the Fabric workspace and the Azure subscription belong to different accounts, so Fabric cannot use the signed-in identity. A read-only token is safer than the account key.
- **Cost:** the token expires and must be renewed.

## ADR-005: Silver is rebuilt in full

- **Decision:** every run rebuilds each silver table from all of bronze and keeps the latest row per primary key. A second notebook runs 88 checks: keys, foreign keys, accepted values and non-negative amounts.
- **Why:** it is simple and gives the same result on every run. At this volume, incremental merges are not worth the extra complexity.
- **Cost:** each run reprocesses everything. With more data, this should become a `MERGE`.

## ADR-006: Gold layer in dbt

- **Decision:** a star schema with facts at different grains and shared dimensions. Staging models are views over silver; marts are tables in the `gold` schema. dbt connects with the Azure CLI login, and the server name comes from an environment variable.
- **Why:** the SQL is versioned in Git, dbt runs the models in the right order with `ref()`, and the tests run with the build.
- **Cost:** no date dimension yet; Power BI uses the date columns of the facts. dbt runs with one thread, because parallel view creation deadlocked on the Warehouse.

## ADR-007: CI without cloud access

- **Decision:** GitHub Actions runs the Python tests against a temporary PostgreSQL, ruff, `terraform validate` and `dbt parse` on every pull request. No secrets.
- **Why:** it catches broken code before the merge without storing cloud credentials in GitHub.
- **Cost:** it does not catch a model that fails only on the Warehouse, or bad data.

## ADR-008: Airflow DAG with a manual step

- **Decision:** a local Airflow DAG runs the same steps as the PowerShell script. It stops before gold until someone runs the silver notebooks and approves the task.
- **Why:** Airflow cannot start a notebook in a Fabric workspace of another account.
- **Cost:** the pipeline is not fully automatic, and the image is large (about 5 GB).

## ADR-009: Cost data comes from the ERP

- **Decision:** the ERP gets a material price in US dollars, a daily USD/BRL rate, an hourly rate per work center, the working minutes of each stage and the freight of each shipment. The rate is the real PTAX from Banco Central do Brasil, saved once as a CSV file.
- **Why:** margin needs costs, and a saved file keeps the simulation reproducible without calling an API on every run.
- **Cost:** prices and rates are invented, and the schema change required a new ERP database.

## ADR-010: Margin fact and late orders

- **Decision:** `fct_order_margin` has one row per shipped order: revenue minus material, processing and freight. Material uses the latest exchange rate on or before the order date. `fct_order_delivery` counts an order past its promised date and not delivered yet as late.
- **Why:** costs are final only after shipping, and an undelivered overdue order is late from the customer's point of view.
- **Cost:** the on-time rate is lower than counting delivered orders only, but it is closer to reality.

## ADR-011: The bronze folder has a version

- **Decision:** the new files go to `erp_v2` instead of `erp`, and Fabric reads them through a new shortcut.
- **Why:** the new ERP database restarted its keys, so old and new files in one folder would mix two histories.
- **Cost:** the old folder stays in the lake unused.
