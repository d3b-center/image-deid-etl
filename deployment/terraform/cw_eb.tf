data "aws_cloudwatch_event_bus" "this" {
  name = "default"
}

resource "aws_cloudwatch_event_rule" "console" {
  name        = local.short 
  description = "Cron Job ${var.project}"
  event_bus_name = "default"
  role_arn = aws_iam_role.eventbus.arn
  schedule_expression = "cron(0 8 * * ? *)"
  event_pattern = <<PATTERN
  {
     "account": ["${data.aws_caller_identity.current.account_id}"],
     "source": ["${aws_sfn_state_machine.default.arn}"]
  }
PATTERN
  tags = {
    Project = var.project
    Environment = var.environment
  }
}

resource "aws_cloudwatch_event_target" "sfn" {
  arn       = aws_sfn_state_machine.default.arn
  rule      = aws_cloudwatch_event_rule.console.name
  role_arn  = aws_iam_role.eventbus.arn
}
