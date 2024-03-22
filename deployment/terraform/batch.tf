#
# Security Group resources
#
resource "aws_security_group" "batch" {
  name_prefix = "sgBatchContainerInstance-"
  vpc_id      = var.vpc_id

  tags = {
    Name        = "sgBatchContainerInstance"
    Project     = var.project
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

#
# Batch resources
#
resource "aws_launch_template" "default" {
  name_prefix = "ltBatchContainerInstance-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size = var.batch_root_block_device_size
      volume_type = var.batch_root_block_device_type
    }
  }

  user_data = base64encode(file("cloud-config/batch-container-instance"))

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_batch_compute_environment" "default" {
  compute_environment_name_prefix = "batch${local.short}-"
  type                            = "MANAGED"
  state                           = "ENABLED"
  service_role                    = aws_iam_role.batch_service_role.arn

  compute_resources {
    type                = "SPOT"
    allocation_strategy = var.batch_spot_fleet_allocation_strategy
    bid_percentage      = var.batch_spot_fleet_bid_percentage

    ec2_configuration {
      image_type = "ECS_AL2"
    }

    ec2_key_pair = aws_key_pair.bastion.key_name

    min_vcpus = var.batch_min_vcpus
    max_vcpus = var.batch_max_vcpus

    launch_template {
      launch_template_id = aws_launch_template.default.id
      version            = aws_launch_template.default.latest_version
    }

    spot_iam_fleet_role = aws_iam_role.spot_fleet_service_role.arn
    instance_role       = aws_iam_instance_profile.ecs_instance_role.arn

    instance_type = var.batch_instance_types

    security_group_ids = [aws_security_group.batch.id]
    subnets            = var.vpc_private_subnet_ids

    tags = {
      Name        = "BatchWorker"
      Project     = var.project
      Environment = var.environment
    }
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_role_policy]

  tags = {
    Project     = var.project
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_batch_job_queue" "default" {
  name                 = "queue${local.short}"
  priority             = 1
  state                = "ENABLED"
  compute_environments = [aws_batch_compute_environment.default.arn]

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_batch_job_definition" "default" {
  name = "job${local.short}"
  type = "container"

  container_properties = templatefile("${path.module}/job-definitions/image-deid-etl.json.tmpl", {
    image_url = "${module.ecr.repository_url}:${var.image_tag}"

    image_deid_etl_vcpus  = var.image_deid_etl_vcpus
    image_deid_etl_memory = var.image_deid_etl_memory

    database_url = "postgresql://${var.rds_database_username}:${var.rds_database_password}@${module.database.hostname}:${module.database.port}/${var.rds_database_name}"

    flywheel_api_key    = var.flywheel_api_key
    flywheel_group      = var.flywheel_group
    orthanc_credentials = var.orthanc_credentials
    orthanc_host        = var.orthanc_host
    orthanc_port        = var.orthanc_port

    rollbar_post_server_item_access_token = var.rollbar_post_server_item_access_token

    phi_data_bucket_name    = var.d3b_phi_data_bucket_name
    subject_id_mapping_path = var.subject_id_mapping_path

    image_deid_etl_log_level = var.image_deid_etl_log_level

    environment = var.environment
  })

  platform_capabilities = ["EC2"]

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}
