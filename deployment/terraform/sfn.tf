
#
# Step Functions resources
#
resource "aws_sfn_state_machine" "default" {
  name     = "stateMachine${local.short}"
  role_arn = aws_iam_role.step_functions_service_role.arn

  definition = templatefile("${path.module}/step-functions/image-deid-etl.json.tmpl", {
    batch_job_definition_arn = aws_batch_job_definition.default.arn
    batch_job_queue_arn      = aws_batch_job_queue.default.arn
  })

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}
