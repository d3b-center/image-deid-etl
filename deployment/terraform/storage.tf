#
# ECR resources
#
module "ecr" {
  # TODO: Fork this Terraform module and bring into d3b-center.
  source = "github.com/azavea/terraform-aws-ecr-repository?ref=1.0.0"

  repository_name         = replace(lower(var.project), " ", "-")
  attach_lifecycle_policy = true
}
