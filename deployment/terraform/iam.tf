#
# GitHub Actions IAM resources
#
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com"
      ]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        for ref
        in var.refs_that_can_assume_github_actions_role
        : "repo:d3b-center/image-deid-etl:ref:${ref}"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_role" {
  name_prefix        = "GitHubActions${local.short}Role-"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_role_policy" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = var.aws_administrator_access_policy_arn
}

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

  tags = {
    Project     = var.project
    Environment = var.environment
  }
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

  tags = {
    Project     = var.project
    Environment = var.environment
  }
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

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ec2_service_role_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = var.aws_ec2_service_role_policy_arn
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = aws_iam_role.ecs_instance_role.name
  role = aws_iam_role.ecs_instance_role.name

  tags = {
    Project     = var.project
    Environment = var.environment
  }
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
      "s3:GetObject"
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

#
# Step Functions IAM resources
#
data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "step_functions_service_role_policy" {
  statement {
    effect = "Allow"

    actions = [
      "batch:SubmitJob",
      "batch:DescribeJobs",
      "batch:TerminateJobs"
    ]

    # Despite the "*" wildcard, only allow these actions for Batch jobs that were
    # started by Step Functions.
    # See: https://github.com/awsdocs/aws-step-functions-developer-guide/blob/master/doc_source/batch-iam.md
    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "events:PutTargets",
      "events:PutRule",
      "events:DescribeRule",
    ]

    resources = [
      "arn:aws:events:${var.region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctionsGetEventsForBatchJobsRule",
    ]
  }
}

resource "aws_iam_role" "step_functions_service_role" {
  name_prefix        = "sfn${local.short}ServiceRole-"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "step_functions_service_role_policy" {
  name_prefix = "sfnServiceRolePolicy-"
  role        = aws_iam_role.step_functions_service_role.name
  policy      = data.aws_iam_policy_document.step_functions_service_role_policy.json
}


data "aws_iam_policy_document" "cw_eventbus_assume_role" {

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbus" {
  name_prefix        = "EventBus${local.short}Role-"

  assume_role_policy    = data.aws_iam_policy_document.cw_eventbus_assume_role.json

  tags = {
     Project = var.project
     Environment = var.environment
  }
}
