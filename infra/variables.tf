variable "subscription_id" {
  description = "Azure subscription ID where everything is created."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "brazilsouth"
}

variable "project" {
  description = "Short project prefix used in resource names."
  type        = string
  default     = "idp"
}

variable "environment" {
  description = "Environment name used in resource names."
  type        = string
  default     = "dev"
}

variable "lake_layers" {
  description = "Medallion layers, one ADLS filesystem each."
  type        = set(string)
  default     = ["bronze", "silver", "gold"]
}
