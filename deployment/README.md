# Deployment

- [AWS Credentials](#aws-credentials)
- [Publish Container Images](#publish-container-images)
- [Terraform](#terraform)
- [Database Migrations](#database-migrations)

## AWS Credentials

Follow [these](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile) instructions to configure a named AWS profile:

- Use https://d-906762f877.awsapps.com/start as the SSO start URL.
- Use `us-east-1` as the SSO region.

Use the `aws sso login` command to refresh your login if your credentials expire:

```console
$ aws sso login --profile my-profile
```

## Publish Container Images

Build a container image for the Python application (`cibuild`) and publish it to Amazon ECR (`cipublish`):

```console
$ ./scripts/cibuild
...
 => => naming to docker.io/library/image-deid-etl:da845bf
$ ./scripts/cipublish
```

## Terraform

Launch an instance of the included Terraform container image:

```console
$ docker-compose -f docker-compose.ci.yml run --rm terraform
bash-5.1#
```

Once inside the context of the container image, set `GIT_COMMIT` to the tag of a published container image (e.g., `da845bf`):

```console
bash-5.1# export GIT_COMMIT=da845bf
```

Finally, use `infra` to generate and apply a Terraform plan:

```console
bash-5.1# ./scripts/infra plan
bash-5.1# ./scripts/infra apply
```

## Database Migrations

Execute database migrations by submitting a Batch job that invokes the application's `initdb` command:

- Select the most recent job definition for [jobImageDeidEtl](https://console.aws.amazon.com/batch/home?region=us-east-1#job-definition).
- Select **Submit new job**.
- Select the following:
  - **Name**: Any one-off description of the work you're performing, e.g.: `initialize-the-database`.
  - **Job queue**: `queueImageDeidEtl`.
  - **Command**: `image-deid-etl initdb`.
- Click **Submit**.
- Monitor the log output of the submitted job by viewing the job detail and clicking the link under **Log group name**.
