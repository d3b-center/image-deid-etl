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
  type      = string
  sensitive = true
}

variable "r53_private_hosted_zone" {
  type    = string
  default = "image-deid-etl.internal"
}

variable "r53_public_hosted_zone" {
  type = string
}

variable "batch_root_block_device_size" {
  type    = number
  default = 32
}

variable "batch_root_block_device_type" {
  type    = string
  default = "gp3"
}

variable "batch_spot_fleet_allocation_strategy" {
  type    = string
  default = "SPOT_CAPACITY_OPTIMIZED"
}

variable "batch_spot_fleet_bid_percentage" {
  type    = number
  default = 64
}

variable "batch_min_vcpus" {
  type    = number
  default = 0
}

variable "batch_max_vcpus" {
  type    = number
  default = 256
}

variable "batch_instance_types" {
  type    = list(string)
  default = ["c5d", "m5d", "z1d"]
}

variable "rds_allocated_storage" {
  type    = number
  default = 32
}

variable "rds_engine_version" {
  type    = string
  default = "14.11"
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
  type      = string
  sensitive = true
}

variable "rds_database_password" {
  type      = string
  sensitive = true
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

variable "image_deid_etl_vcpus" {
  type    = number
  default = 1
}

variable "image_deid_etl_memory" {
  type    = number
  default = 1024
}

variable "flywheel_api_key" {
  type      = string
  sensitive = true
}

variable "flywheel_group" {
  type      = string
  sensitive = true
}

variable "orthanc_credentials" {
  type      = string
  sensitive = true
}

variable "orthanc_host" {
  type      = string
  sensitive = true
}

variable "orthanc_port" {
  type      = number
  sensitive = true
}

variable "subject_id_mapping_path" {
  type      = string
  sensitive = true
}

variable "rollbar_post_server_item_access_token" {
  type      = string
  sensitive = true
}

variable "image_deid_etl_log_level" {
  type    = string
  default = "INFO"
}

variable "d3b_phi_data_kms_key_arn" {
  type      = string
  sensitive = true
}

variable "d3b_phi_data_bucket_name" {
  type      = string
  sensitive = true
}

variable "aws_batch_service_role_policy_arn" {
  type    = string
  default = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

variable "aws_spot_fleet_service_role_policy_arn" {
  type    = string
  default = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

variable "aws_ec2_service_role_policy_arn" {
  type    = string
  default = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

variable "aws_administrator_access_policy_arn" {
  type    = string
  default = "arn:aws:iam::aws:policy/AdministratorAccess"
}

variable "refs_that_can_assume_github_actions_role" {
  type = list(string)
  default = [
    "refs/heads/develop",
    "refs/heads/master"
  ]
}
