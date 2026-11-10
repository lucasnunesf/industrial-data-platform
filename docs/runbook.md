# Runbook

Routine tasks and known failure modes of the pipeline.

## Renew the SAS token of the OneLake shortcut

The shortcut `Files/erp` in the Fabric Lakehouse reads `bronze/erp` with a read-only SAS token ([ADR-004](decisions.md)). When it expires, reads from the shortcut fail with an authorization error and the silver notebooks stop working.

1. In the Azure portal, open the storage account and go to **Shared access signature**.
2. Allowed services: Blob. Allowed resource types: Service, Container and Object. Permissions: Read and List.
3. Start time one day in the past, a new expiry date, then generate the token.
4. In Fabric, open **Manage connections and gateways**, edit the connection used by the shortcut and paste the new token without the leading `?`.

The token is kept only in the Fabric connection, never in the repository.

## Notebook fails with `400 Bad Request` on `Files/...`

The notebook has no default Lakehouse. Attach the Lakehouse (the item with the house icon, not the SQL analytics endpoint) as the default and restart the session.

## Notebook fails with `TooManyRequestsForCapacity`

The trial capacity allows few concurrent Spark sessions. Stop the sessions of other notebooks (or cancel running items in the Monitor hub), wait a minute and run again.

## dbt cannot connect to the Warehouse

- Check that `FABRIC_SQL_HOST` is set in the current terminal.
- Check that the Azure CLI session belongs to the account that owns the Fabric workspace (`az account show`). If it differs from the Azure account of the lake, use a separate folder with `AZURE_CONFIG_DIR`.
- Run `dbt debug --project-dir dbt --profiles-dir dbt` to see the failing step.

## Microsoft Fabric trial

The trial capacity is limited to 60 days. Content is deleted when it ends, so keep the dashboard file and screenshots outside Fabric.
