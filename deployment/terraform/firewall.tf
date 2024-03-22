#
# Bastion security group resources
#
resource "aws_security_group_rule" "bastion_rds_egress" {
  type      = "egress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = aws_security_group.bastion.id
  source_security_group_id = module.database.database_security_group_id
}

resource "aws_security_group_rule" "bastion_ssh_egress" {
  type      = "egress"
  from_port = 22
  to_port   = 22
  protocol  = "tcp"

  security_group_id        = aws_security_group.bastion.id
  source_security_group_id = aws_security_group.batch.id
}

#
# RDS security group resources
#
resource "aws_security_group_rule" "rds_bastion_ingress" {
  type      = "ingress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = module.database.database_security_group_id
  source_security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "rds_batch_ingress" {
  type      = "ingress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = module.database.database_security_group_id
  source_security_group_id = aws_security_group.batch.id
}

#
# Batch container instance security group resources
#
resource "aws_security_group_rule" "batch_http_egress" {
  type        = "egress"
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]

  security_group_id = aws_security_group.batch.id
}

resource "aws_security_group_rule" "batch_https_egress" {
  type        = "egress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]

  security_group_id = aws_security_group.batch.id
}

resource "aws_security_group_rule" "batch_rds_egress" {
  type      = "egress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = aws_security_group.batch.id
  source_security_group_id = module.database.database_security_group_id
}

resource "aws_security_group_rule" "batch_bastion_ingress" {
  type      = "ingress"
  from_port = 22
  to_port   = 22
  protocol  = "tcp"

  security_group_id        = aws_security_group.batch.id
  source_security_group_id = aws_security_group.bastion.id
}
