#
# SNS resources
#
resource "aws_sns_topic" "global" {
  name = "topic${local.short}GlobalNotifications"

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}
