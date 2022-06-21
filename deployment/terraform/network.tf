#
# VPC resources
#
resource "aws_security_group" "bastion" {
  name_prefix = "sgBastion-"
  vpc_id      = var.vpc_id

  tags = {
    Name        = "sgBastion"
    Project     = var.project
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*"]
  }
}

resource "aws_key_pair" "bastion" {
  public_key = var.bastion_public_key

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.image_id
  availability_zone      = var.vpc_availability_zones[0]
  ebs_optimized          = true
  instance_type          = var.bastion_instance_type
  key_name               = aws_key_pair.bastion.key_name
  monitoring             = true
  subnet_id              = var.vpc_private_subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.bastion.id]

  tags = {
    Name        = "Bastion"
    Project     = var.project
    Environment = var.environment
  }

  lifecycle {
    ignore_changes = [ami]
  }
}
