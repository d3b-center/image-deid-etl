variable "project" {
  type        = string
  description = "A project namespace for the infrastructure."
}

locals {
  # e.g., "Image Deid ETL" → "image deid etl" → "Image Deid Etl" → "ImageDeidEtl"
  short = replace(title(lower(var.project)), " ", "")
}

variable "environment" {
  type        = string
  description = "An environment namespace for the infrastructure."
}

variable "region" {
  type        = string
  default     = "us-east-1"
  description = "A valid AWS region to configure the underlying AWS SDK."
}

variable "vpc_id" {
  type = string
}

variable "vpc_availability_zones" {
  type = list(string)
}

variable "vpc_public_subnet_ids" {
  type = list(string)
}

variable "vpc_private_subnet_ids" {
  type = list(string)
}

variable "bastion_instance_type" {
  type = string
}

variable "bastion_public_key" {
  type = string
}

variable "rds_allocated_storage" {
  type    = number
  default = 32
}

variable "rds_engine_version" {
  type    = string
  default = "14.2"
}

variable "rds_parameter_group_family" {
  type    = string
  default = "postgres14"
}

variable "rds_instance_type" {
  type    = string
  default = "db.t3.micro"
}

variable "rds_storage_type" {
  type    = string
  default = "gp2"
}

variable "rds_iops" {
  type    = number
  default = null
}

variable "rds_database_identifier" {
  type = string
}

variable "rds_database_name" {
  type = string
}

variable "rds_database_username" {
  type = string
}

variable "rds_database_password" {
  type = string
}

variable "rds_backup_retention_period" {
  type    = number
  default = 30
}

variable "rds_backup_window" {
  type    = string
  default = "04:00-04:30"
}

variable "rds_maintenance_window" {
  type    = string
  default = "sun:04:30-sun:05:30"
}

variable "rds_auto_minor_version_upgrade" {
  type    = bool
  default = true
}

variable "rds_final_snapshot_identifier" {
  type    = string
  default = "image-deid-etl-rds-snapshot"
}

variable "rds_monitoring_interval" {
  type    = number
  default = 60
}

variable "rds_skip_final_snapshot" {
  type    = bool
  default = false
}

variable "rds_copy_tags_to_snapshot" {
  type    = bool
  default = true
}

variable "rds_multi_az" {
  type    = bool
  default = false
}

variable "rds_storage_encrypted" {
  type    = bool
  default = false
}

variable "rds_seq_page_cost" {
  type    = number
  default = 1
}

variable "rds_random_page_cost" {
  type    = number
  default = 1
}

variable "rds_log_min_duration_statement" {
  type    = number
  default = 500
}

variable "rds_log_connections" {
  type    = number
  default = 0
}

variable "rds_log_disconnections" {
  type    = number
  default = 0
}

variable "rds_log_lock_waits" {
  type    = number
  default = 1
}

variable "rds_log_temp_files" {
  type    = number
  default = 500
}

variable "rds_log_autovacuum_min_duration" {
  type    = number
  default = 250
}

variable "rds_cpu_threshold_percent" {
  type    = number
  default = 75
}

variable "rds_disk_queue_threshold" {
  type    = number
  default = 10
}

variable "rds_free_disk_threshold_bytes" {
  type    = number
  default = 5000000000 # 5 GB
}

variable "rds_free_memory_threshold_bytes" {
  type    = number
  default = 128000000 # 128 MB
}

variable "rds_cpu_credit_balance_threshold" {
  type    = number
  default = 30
}

variable "image_tag" {
  type    = string
  default = "latest"
}

