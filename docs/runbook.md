# Runbook

Routine tasks and known failure modes of the pipeline.

## Run the full pipeline

`orchestration/run_pipeline.ps1` chains the steps below and pauses for the manual silver run in Fabric.

1. **Source and bronze:** the local steps of the README quick start.
2. **Upload to the lake** (requires `az login` on the Azure subscription and `pip install -r ingestion/requirements-upload.txt`): `python ingestion/upload.py --account <storage account>`.
3. **Silver (Fabric):** the Lakehouse reads `bronze/erp_v2` through a OneLake shortcut under `Files` ([ADR-004](decisions.md)). Paste the code of `processing/silver/` into two notebooks, attach the Lakehouse as the default one and run `01_build_silver`, then `02_test_silver` (it must end with 0 failed).
4. **Gold (dbt)** (requires `pip install dbt-fabric` on Python 3.12 and `az login --allow-no-subscriptions` with the Fabric account): set `FABRIC_SQL_HOST` to the Warehouse SQL endpoint and run `dbt build --project-dir dbt --profiles-dir dbt`.
5. **Power BI:** refresh the semantic model and publish.

**Airflow (optional).** The same steps as a DAG. Set `AZURE_STORAGE_ACCOUNT` and `FABRIC_SQL_HOST`, run `docker compose -f orchestration/airflow/docker-compose.yml up -d --build` (the image is about 5 GB), log in once per tenant inside the container, then trigger `industrial_pipeline` at http://localhost:8080:

```powershell
docker compose -f orchestration/airflow/docker-compose.yml exec -e AZURE_CONFIG_DIR=/opt/airflow/azure/lake airflow az login --use-device-code
docker compose -f orchestration/airflow/docker-compose.yml exec -e AZURE_CONFIG_DIR=/opt/airflow/azure/fabric airflow az login --use-device-code --allow-no-subscriptions
```

The DAG stops at `wait_for_silver` until the notebooks have run and the task is approved in the UI ([ADR-008](decisions.md)).

## Renew the SAS token of the OneLake shortcut

The shortcut `Files/erp_v2` in the Fabric Lakehouse reads `bronze/erp_v2` with a read-only SAS token ([ADR-004](decisions.md)). When it expires, reads from the shortcut fail with an authorization error and the silver notebooks stop working.

1. In the Azure portal, open the storage account and go to **Shared access signature**.
2. Allowed services: Blob. Allowed resource types: Service, Container and Object. Permissions: Read and List.
3. Start time one day in the past, a new expiry date, then generate the token.
4. In Fabric, open **Manage connections and gateways**, edit the connection used by the shortcut and paste the new token without the leading `?`.

The token is kept only in the Fabric connection, never in the repository.

## Rebuild everything after an ERP schema change

`CREATE TABLE IF NOT EXISTS` does not alter an existing table, so a schema change needs a new ERP database and a new bronze folder ([ADR-011](decisions.md)).

1. Bump `SOURCE_FOLDER` in `ingestion/config.py` and `BRONZE_PATH` in both silver notebooks.
2. Move the local `ingestion/out/bronze` folder away: it holds the old files and the old watermarks.
3. `docker compose down -v`, then `docker compose up -d --wait erp-db`.
4. Run the simulator and the extractor, then `python ingestion/upload.py`.
5. In the Lakehouse, create a shortcut under `Files` to the new folder of the `bronze` container, reusing the existing connection.
6. Paste the new notebook code in Fabric, run `01_build_silver` and `02_test_silver`, then `dbt build`.
7. Refresh the Power BI model and publish.

## Notebook fails with `400 Bad Request` on `Files/...`

The notebook has no default Lakehouse. Attach the Lakehouse (the item with the house icon, not the SQL analytics endpoint) as the default and restart the session.

## Notebook fails with `PATH_NOT_FOUND` on a new shortcut

Check that the shortcut was created under **Files**, not under **Tables**: under Tables, Fabric tries to read the folders as tables and shows them as *Unidentified*. The notebooks read the shortcut by its full path, taken from `mssparkutils.fs.ls("Files")`; with the short relative path, a shortcut created while a session was open was not found.

## Notebook fails with `TooManyRequestsForCapacity`

The trial capacity allows few concurrent Spark sessions. Stop the sessions of other notebooks (or cancel running items in the Monitor hub), wait a minute and run again.

## dbt cannot connect to the Warehouse

- Check that `FABRIC_SQL_HOST` is set in the current terminal.
- Check that the Azure CLI session belongs to the account that owns the Fabric workspace (`az account show`). If it differs from the Azure account of the lake, use a separate folder with `AZURE_CONFIG_DIR`.
- Run `dbt debug --project-dir dbt --profiles-dir dbt` to see the failing step.

## dbt fails with `deadlocked on lock resources`

The Warehouse can deadlock when several views are created at the same time. The profile uses one thread (`threads: 1` in `dbt/profiles.yml`); a full build takes under a minute.

## Microsoft Fabric trial

The trial capacity is limited to 60 days. Content is deleted when it ends, so keep the dashboard file and screenshots outside Fabric.
