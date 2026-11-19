# Runbook

How to run the pipeline, and what to do when a step fails.

## Run the full pipeline

`orchestration/run_pipeline.ps1` runs these steps in order and pauses for the silver step in Fabric.

1. **Source and bronze:** the local steps in the README.
2. **Upload to the lake:** sign in with `az login`, install `ingestion/requirements-upload.txt`, then run `python ingestion/upload.py --account <storage account>`.
3. **Silver:** in the Fabric Lakehouse, the shortcut `Files/erp_v2` points to `bronze/erp_v2`. Paste the two files of `processing/silver/` into two notebooks, set the Lakehouse as the default one, and run `01_build_silver`, then `02_test_silver`. The second one must end with `0 failed`.
4. **Gold:** install `dbt-fabric` (Python 3.12), sign in with `az login --allow-no-subscriptions` on the Fabric account, set `FABRIC_SQL_HOST` to the Warehouse SQL endpoint, and run `dbt build --project-dir dbt --profiles-dir dbt`.
5. **Power BI:** refresh the semantic model and publish.

## Create the data lake (Terraform)

Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` and set your subscription ID. Then:

```bash
terraform -chdir=infra init
terraform -chdir=infra apply
```

This creates the resource group, the storage account with the `bronze`, `silver` and `gold` containers, and a Key Vault.

## Run with Airflow (optional)

The DAG `industrial_pipeline` runs the same steps. Set `AZURE_STORAGE_ACCOUNT` and `FABRIC_SQL_HOST`, then start it (the image is about 5 GB):

```bash
docker compose -f orchestration/airflow/docker-compose.yml up -d --build
```

Sign in once per account inside the container:

```bash
docker compose -f orchestration/airflow/docker-compose.yml exec -e AZURE_CONFIG_DIR=/opt/airflow/azure/lake airflow az login --use-device-code
docker compose -f orchestration/airflow/docker-compose.yml exec -e AZURE_CONFIG_DIR=/opt/airflow/azure/fabric airflow az login --use-device-code --allow-no-subscriptions
```

Open http://localhost:8080 and trigger the DAG. It stops at `wait_for_silver`: run the notebooks in Fabric, then approve the task.

## Renew the SAS token

The shortcut reads the lake with a read-only token. When it expires, the silver notebooks fail with an authorization error.

1. In the Azure portal, open the storage account and go to **Shared access signature**.
2. Services: Blob. Resource types: Service, Container and Object. Permissions: Read and List.
3. Set the start one day in the past and a new expiry date, then generate the token.
4. In Fabric, open **Manage connections and gateways**, edit the connection of the shortcut and paste the token without the leading `?`.

The token is stored only in the Fabric connection, never in the repository.

## Rebuild after an ERP schema change

`CREATE TABLE IF NOT EXISTS` does not change an existing table, so a schema change needs a new database and a new bronze folder.

1. Change `SOURCE_FOLDER` in `ingestion/config.py` and the folder name in both silver notebooks.
2. Move the local `ingestion/out/bronze` folder away: it holds the old files and the old watermarks.
3. Run `docker compose down -v`, then `docker compose up -d --wait erp-db`.
4. Run the simulator, the extractor and the upload.
5. In the Lakehouse, create a shortcut under `Files` to the new folder, reusing the existing connection.
6. Run both notebooks, then `dbt build`, then refresh Power BI.

## Common errors

| Error | Fix |
|---|---|
| Notebook: `400 Bad Request` on `Files/...` | Set the Lakehouse (house icon) as the default one and restart the session. |
| Notebook: `PATH_NOT_FOUND` on a new shortcut | Check that the shortcut is under **Files**, not **Tables**, and restart the session. |
| Notebook: `TooManyRequestsForCapacity` | Stop the Spark sessions of other notebooks, wait a minute and run again. |
| dbt cannot connect | Check `FABRIC_SQL_HOST`, check `az account show`, then run `dbt debug --project-dir dbt --profiles-dir dbt`. |
| dbt: `deadlocked on lock resources` | Keep `threads: 1` in `dbt/profiles.yml`. |

## Fabric trial

The trial lasts 60 days and its content is deleted when it ends. Keep the report file and the screenshots outside Fabric.
