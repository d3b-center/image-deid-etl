# Image De-identification ETL 📸

The Image De-identification ETL is a WIP tool to assist with reading DICOM images from Orthanc, conversion to anonymized NIfTI images, and uploading to Flywheel.

- [Getting Started](#getting-started)
  - [Dependencies](#dependencies)
  - [Instructions](#instructions)
- [Everyday Usage](#everyday-usage)

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
- For `FLYWHEEL_API_KEY`, generate an API key from your Flywheel user profile.
- For `FLYWHEEL_GROUP`, specify either `d3b` or an alternative group created for testing (e.g., your name).
- For `ORTHANC_CREDENTIALS`, use your Orthanc username and password specified like `username:password`.
- For `ORTHANC_HOST`, specify the hostname (minus `http(s)://`) that you use to access Orthanc.

Next, use Nix to enter a shell environment containing all the CLI's runtime dependencies:

```console
$ nix develop
```

Finally, use `update` to install and ensure all our Python packages are up-to-date:

```console
$ ./scripts/update
```

And, voilà, the CLI should fully functional ✨:

```console
$ ./image_deid_etl -h
usage: image_deid_etl [-h] --program [{cbtn,corsica}] --site [SITE] [--check_orthanc] [--run_pipeline] [--delete_local] [--validate] [--upload2fw] [--add_fw_metadata] [--s3_backup_niftis]
                      [--s3_backup_images]
                      ...

A WIP tool to assist with reading DICOM images from Orthanc, conversion to anonymized NIfTI images, and uploading to Flywheel.

positional arguments:
  path_to_uuid_list     Path to file containing Orthanc UUIDs to process.

optional arguments:
  -h, --help            show this help message and exit
  --program [{cbtn,corsica}]
                        Program namespace. (default: cbtn)
  --site [SITE]         Site namespace. (default: chop)
  --check_orthanc       Check to see if there are new studies. (default: False)
  --run_pipeline        Run the pipeline & upload "safe" files. (default: False)
  --delete_local        Delete files off EC2. (default: False)
  --validate            Check sub/ses mapping. (default: False)
  --upload2fw           Upload results to Flywheel, when complete. (default: False)
  --add_fw_metadata     Add metadata in JSON sidecars to NIfTIs on Flywheel. (default: False)
  --s3_backup_niftis    Copies NIfTIs to S3. (default: False)
  --s3_backup_images    Copies JPGs to S3. (default: False)
```

## Everyday Usage

Each time you start a new Terminal session, you'll need to enter the Nix development shell:

```console
$ nix develop
```

Also, if you make any changes to your `.env` file or `flake.nix`, you will need to detach (<kbd>Ctrl</kbd> + <kbd>D</kbd>) and re-enter the development shell.
