output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "storage_account" {
  value = azurerm_storage_account.lake.name
}

output "lake_filesystems" {
  value = sort(keys(azurerm_storage_data_lake_gen2_filesystem.layer))
}

output "databricks_workspace_url" {
  value = "https://${azurerm_databricks_workspace.main.workspace_url}"
}

output "key_vault" {
  value = azurerm_key_vault.main.name
}
