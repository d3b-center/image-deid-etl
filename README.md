# Image De-identification ETL 📸

The Image De-identification ETL is a WIP tool to assist with reading DICOM images from Orthanc, conversion to anonymized NIfTI images, and uploading to Flywheel.

- [Getting Started](#getting-started)
  - [Dependencies](#dependencies)
  - [Instructions](#instructions)
- [Example Usage](#example-usage)
- [Development](#development)
  - [AWS](#aws)
  - [Nix Shell](#nix-shell)

## Getting Started

### Dependencies

- [Nix (the package manager)](https://nixos.org/download.html)
- [Nix flakes](https://nixos.wiki/wiki/Flakes#Non-NixOS)

### Instructions

First, copy the following file, renaming it to `.env` in the process:

```console
$ cp .env.sample .env
```

Then, customize its contents with a text editor:

- For `AWS_PROFILE`, follow [these](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile) instructions to configure a named profile for yourself. Use https://d-906762f877.awsapps.com/start as the SSO start URL and `us-east-1` as the SSO region. Assign the name of the profile you create to the value for `AWS_PROFILE`.
- For `S3_BUCKET`, specify the s3 bucket/path to read from.
- For `FLYWHEEL_API_KEY`, generate an API key from your Flywheel user profile.
- For `FLYWHEEL_GROUP`, specify either `d3b` or an alternative group created for testing (e.g., your name).
- For `ORTHANC_CREDENTIALS`, use your Orthanc username and password specified like `username:password`.
- For `ORTHANC_HOST`, specify the hostname (minus `http(s)://`) that you use to access Orthanc.

Next, use Nix to enter a shell environment containing all the CLI's runtime dependencies:

```console
$ nix develop
```

Finally, use `update` to install and ensure all our Python packages are up-to-date and run database migrations:

```console
$ ./scripts/update
```

And, voilà, the CLI should fully functional ✨:

```console
$ ./image_deid_etl -h
usage: image_deid_etl [-h] [--program [{cbtn,corsica}]] [--site [SITE]] {initdb,importuuids,check,validate,run,upload2fw,add-fw-metadata,s3-backup-niftis} ...

A WIP tool to assist with reading DICOM images from Orthanc, conversion to anonymized NIfTI images, and uploading to Flywheel.

positional arguments:
  {initdb,importuuids,check,validate,run,upload2fw,add-fw-metadata,s3-backup-niftis}
    validate            check sub/ses mapping
    run                 download images and run deidentification
    upload2fw           upload results to Flywheel, when complete
    add-fw-metadata     add metadata in JSON sidecars to NIfTIs on Flywheel
    s3-backup-niftis    copies NIfTIs to S3

optional arguments:
  -h, --help            show this help message and exit
  --program [{cbtn,corsica}]
                        program namespace (default: cbtn)
  --site [SITE]         site namespace (default: chop)
```

## Example Usage

To check Orthanc for and process N number of new studies, pipe the output of `check` into the `run` command:

```console
$ ./image_deid_etl check --limit N --raw | xargs ./image_deid_etl run
```

To process an individual study, specify an Orthanc UUID after the `run` command:

```console
$ ./image_deid_etl run UUID
```

## Development

### AWS

CHOP's AWS SSO configuration will automatically sign you out of your session every 1 to 2 hours. If you encounter any permission errors, your session has likely expired. Follow [these](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-using-profile) instructions to refresh your login, using the `aws sso login` command.

If you do not have the AWS CLI v2 installed locally, you will need to execute these steps from within the Nix development shell.

### Nix Shell

Each time you start a new Terminal session, you'll need to enter the Nix development shell:

```console
$ nix develop
```

Also, if you make any changes to your `.env` file or `flake.nix`, you will need to detach (<kbd>Ctrl</kbd> + <kbd>D</kbd>) and re-enter the development shell.
