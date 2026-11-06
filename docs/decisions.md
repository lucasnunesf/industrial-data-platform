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
