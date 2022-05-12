provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
    }
  }
}

terraform {
  backend "s3" {
    region  = "us-east-1"
    encrypt = true
  }
}
