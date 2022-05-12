#
# Batch IAM resources
#
data "aws_iam_policy_document" "batch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_service_role" {
  name_prefix        = "batch${local.short}ServiceRole-"
  assume_role_policy = data.aws_iam_policy_document.batch_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_service_role_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = var.aws_batch_service_role_policy_arn
}

#
# Spot Fleet IAM resources
#
data "aws_iam_policy_document" "spot_fleet_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["spotfleet.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "spot_fleet_service_role" {
  name_prefix        = "fleet${local.short}ServiceRole-"
  assume_role_policy = data.aws_iam_policy_document.spot_fleet_assume_role.json
}

resource "aws_iam_role_policy_attachment" "spot_fleet_service_role_policy" {
  role       = aws_iam_role.spot_fleet_service_role.name
  policy_arn = var.aws_spot_fleet_service_role_policy_arn
}

#
# EC2 IAM resources
#
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_instance_role" {
  name_prefix        = "ecs${local.short}InstanceRole-"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ec2_service_role_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = var.aws_ec2_service_role_policy_arn
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = aws_iam_role.ecs_instance_role.name
  role = aws_iam_role.ecs_instance_role.name
}

# We need to data references to get a handle on these resources because
# they are managed out of state.
data "aws_kms_key" "d3b_phi_data" {
  key_id = var.d3b_phi_data_kms_key_arn
}

data "aws_s3_bucket" "d3b_phi_data" {
  bucket = var.d3b_phi_data_bucket_name
}

data "aws_iam_policy_document" "scoped_etl_read" {
  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt"
    ]

    resources = [data.aws_kms_key.d3b_phi_data.arn]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${data.aws_s3_bucket.d3b_phi_data.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "scoped_etl_read" {
  name_prefix = "S3ScopedEtlReadPolicy-"
  role        = aws_iam_role.ecs_instance_role.id
  policy      = data.aws_iam_policy_document.scoped_etl_read.json
}
