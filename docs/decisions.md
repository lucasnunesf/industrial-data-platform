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
- Fabric runs only on Azure and is billed by capacity, so the trial capacity is activated only when needed.
- The Terraform code covers the lake and secrets; the Fabric workspace is created in the portal.
