import argparse
import json
import logging.config
import os
import sys
import tempfile
from glob import glob

import boto3
import flywheel
from sqlalchemy.exc import IntegrityError

from image_deid_etl.custom_etl import delete_acquisitions_by_modality, delete_sessions
from image_deid_etl.custom_flywheel import inject_sidecar_metadata
from image_deid_etl.database import (
    create_schema,
    import_uuids_from_set,
    get_all_processed_uuids,
)
from image_deid_etl.exceptions import ImproperlyConfigured
from image_deid_etl.main_pipeline import validate_info, run_deid

ENVIRONMENT = os.getenv("IMAGE_DEID_ETL_ENV", "Development")
VALID_ENVIRONMENTS = ("Production", "Staging", "Development")
if ENVIRONMENT not in VALID_ENVIRONMENTS:
    raise ImproperlyConfigured(
        f"Invalid ENVIRONMENT provided, must be one of {VALID_ENVIRONMENTS}."
    )

DEBUG = ENVIRONMENT == "Development"

FLYWHEEL_API_KEY = os.getenv("FLYWHEEL_API_KEY")
if FLYWHEEL_API_KEY is None:
    raise ImproperlyConfigured("You must supply a FLYWHEEL_API_KEY.")

FLYWHEEL_GROUP = os.getenv("FLYWHEEL_GROUP")
if FLYWHEEL_GROUP is None:
    raise ImproperlyConfigured(
        "You must supply a valid Flywheel group in FLYWHEEL_GROUP."
    )

PHI_DATA_BUCKET_NAME = os.getenv("PHI_DATA_BUCKET_NAME")
if PHI_DATA_BUCKET_NAME is None:
    raise ImproperlyConfigured(
        "You must supply a valid S3 bucket in PHI_DATA_BUCKET_NAME."
    )

# Configure Python's logging module. The Django project does a fantastic job explaining how logging works:
# https://docs.djangoproject.com/en/4.0/topics/logging/
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("IMAGE_DEID_ETL_LOG_LEVEL", "INFO"),
    },
}

if not DEBUG:
    # Initialize the Rollbar library for exception handling.
    # https://docs.rollbar.com/docs/python#other
    ROLLBAR = {
        "access_token": os.getenv("ROLLBAR_POST_SERVER_ITEM_ACCESS_TOKEN"),
        "environment": ENVIRONMENT.lower(),
    }

    import rollbar

    rollbar.init(**ROLLBAR)

    # Report uncaught exceptions to Rollbar.
    # https://docs.python.org/3/library/sys.html#sys.excepthook
    def excepthook(exc_type, exc_value, traceback):
        rollbar.report_exc_info((exc_type, exc_value, traceback))
        return sys.__excepthook__(exc_type, exc_value, traceback)

    sys.excepthook = excepthook

    # Report error messages to Rollbar's log handler.
    # https://github.com/rollbar/pyrollbar/blob/master/rollbar/logger.py
    LOGGING["handlers"]["rollbar"] = {
        "level": "ERROR",
        "class": "rollbar.logger.RollbarHandler",
    }
    LOGGING["root"]["handlers"].append("rollbar")


logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


def initdb(args) -> int:
    logger.info("Initializing database schema...")
    create_schema()
    logger.info("Success!")

    return 0


def import_uuids(args) -> int:
    """
    This command is used for importing existing, processed UUIDs from a 1-D JSON
    file.
    """
    try:
        uuids_to_import = json.load(args.uuid_file)
        import_uuids_from_set(uuids_to_import)
        logger.info("Imported %d new UUIDs.", len(uuids_to_import))
        return 0
    except Exception as e:
        logger.error("Error: %r\nAre you trying to import already processed UUIDs?", e)
        return 1


def check(args) -> int:
    from image_deid_etl.orthanc import get_orthanc_url, get_uuids, download_unpack_copy
    new_uuids, _, _ = get_uuids(get_orthanc_url(), get_all_processed_uuids(), "all")

    # There is no guarantee that these UUIDs will be in any particular order,
    # only that they are unprocessed.
    if args.limit:
        new_uuids = new_uuids[: args.limit]

    if args.raw:
        print(*new_uuids, sep="\n")
    else:
        if new_uuids:
            logger.info("%d new studies found on Orthanc.", len(new_uuids))

            # Useful for local development. Allows you to mark all new studies as
            # processed, so the ETL doesn't try to process anything.
            if args.mark_processed:
                import_uuids_from_set(set(new_uuids))
                logger.info('Marked %d new studies as "processed."', len(new_uuids))
        else:
            logger.info("No new UUIDs found on Orthanc.")

    return 0


def validate(args) -> int:
    local_path = f"{args.program}/{args.site}/"
    file_path = local_path + "files/"

    # Validate that we have all the right info/mapping
    logger.info("Generating subject mapping for validation.")
    validate_info(local_path, args.program, file_path)

    return 0


def run(args) -> int:
    if args.batch:
        batch = boto3.client("batch")

        aws_job_queue = os.getenv("AWS_JOB_QUEUE")
        if aws_job_queue is None:
            raise ImproperlyConfigured("You must supply a value for AWS_JOB_QUEUE.")

        aws_job_definition = os.getenv("AWS_JOB_DEFINITION")
        if aws_job_definition is None:
            raise ImproperlyConfigured(
                "You must supply a value for AWS_JOB_DEFINITION."
            )

        for uuid in args.uuid:
            response = batch.submit_job(
                jobName=f"ProcessStudy_{uuid}",
                jobQueue=aws_job_queue,
                jobDefinition=aws_job_definition,
                containerOverrides={"command": ["image-deid-etl", "run", uuid]},
            )

            region = batch.meta.region_name
            job_id = response["jobId"]
            url = f"https://console.aws.amazon.com/batch/home?region={region}#jobs/detail/{job_id}"

            logger.info(f"Job started! View here:\n{url}")

        return 0

    if not DEBUG:
        # In production, include the UUID(s) currently being processed in the
        # Rollbar payload.
        # https://docs.rollbar.com/docs/custom-data
        def payload_handler(payload):
            payload["data"]["custom"] = {"uuid": args.uuid}
            return payload

        rollbar.events.add_payload_handler(payload_handler)

    local_path = f"{args.program}/{args.site}/"

    if args.source == 'orthanc':
        from image_deid_etl.orthanc import get_orthanc_url, get_uuids, download_unpack_copy
        for uuid in args.uuid:
            download_unpack_copy(
                get_orthanc_url(),
                uuid,
                local_path + "DICOMs/",
                args.skip_modalities,
            )
        orthanc_flag = 1
    else:
        orthanc_flag = 0

    # Remove any acquisitions/sessions that we don't want to process.
    delete_acquisitions_by_modality(local_path + "DICOMs/", "OT") # other
    delete_acquisitions_by_modality(local_path + "DICOMs/", "SR") # SR Document
    delete_acquisitions_by_modality(local_path + "DICOMs/", "XA") # X-Ray Angiography
    delete_acquisitions_by_modality(local_path + "DICOMs/", "US") # ultrasound

    # Delete any "script" sessions
    delete_sessions(local_path + "DICOMs/", "script")
    delete_sessions(local_path + "DICOMs/", "Bone Scan")

    # if there are no DICOMs to process, then exit
    if len(glob(local_path + "DICOMs/*/*/*")) == 0: # checks if there are any acquisition dir's
        logger.info(f"'No DICOMs found. Exiting.") # if there are no valid DICOMs to proces, then exit (still add the uuid to the RDS)
    else:
        # Run conversion, de-id, quarantine suspicious files, and restructure output for upload.
        logger.info("Commencing de-identification process...")
        missing_ses_flag, missing_subj_id_flag = run_deid(local_path, args.program, orthanc_flag, args.sub_id_mapping)

        if missing_ses_flag:
            raise AttributeError(
                "Unable to generate session label."
                )
            sys.exit(1)
        if missing_subj_id_flag:
            raise LookupError(
                "Unable to find subject ID."
            )
            sys.exit(1)
        else:
            logger.info('Updating target Flywheel project with version info...')
            if args.program == 'cbtn':
                change_fw_proj_version(args, 'v2')

            logger.info('Uploading "safe" files to Flywheel...')
            upload2fw(args)

            logger.info("Injecting sidecar metadata...")
            add_fw_metadata(args)

            logger.info("DONE PROCESSING STUDIES")
            if os.path.exists(local_path + "NIfTIs_to_check/"):
                logger.info("There are files to check in: " + local_path + "NIfTIs_to_check/")
            if os.path.exists(local_path + "NIfTIs_short_json/"):
                logger.info("There are files to check in: " + local_path + "NIfTIs_short_json/")
    
    if orthanc_flag & (args.program=='cbtn'):
        try:
            logger.info("Updating list of UUIDs...")
            import_uuids_from_set(args.uuid)
        except IntegrityError as error:
            logger.error(
                "Unable to mark %d UUID(s) as processed. The UUID(s) already exist in the database: %r",
                len(args.uuid),
                error,
            )

    return 0

def change_fw_proj_version(args, ver_label) -> int:
    from image_deid_etl.custom_flywheel import confirm_proj_exists
    source_path = f"{args.program}/{args.site}/NIfTIs/"

    if not os.path.exists(source_path):
        raise FileNotFoundError(
            f"ERROR AT change_fw_proj_version: {source_path} directory does not exist. Is sub_mapping empty?"
        )

    # change local directory names appropriately
    logger.info('Appending version number to target Flywheel project label')
    fw_proj_dirs = glob(source_path+'*')
    for proj_path in fw_proj_dirs:
        fw_proj_label = proj_path.split('/')[-1]
        new_label = fw_proj_label+'_'+ver_label
        new_path = os.path.join(source_path, new_label)
        os.rename(proj_path, new_path)

    # make sure the project exists on the Flywheel instance (if not, create a new project)
    fw_client = flywheel.Client(api_key=FLYWHEEL_API_KEY)
    confirm_proj_exists(fw_client, FLYWHEEL_GROUP, source_path)

def upload2fw(args) -> int:
    # This is a hack so that the Flywheel CLI can consume credentials from the
    # environment.
    with tempfile.TemporaryDirectory() as flywheel_user_home:
        logger.info(f"Writing fake Flywheel CLI credentials to {flywheel_user_home}...")
        # The Flywheel CLI will look for its config directory at this path.
        os.putenv("FLYWHEEL_USER_HOME", flywheel_user_home)
        # Create the fake config directory.
        os.makedirs(f"{flywheel_user_home}/.config/flywheel/", exist_ok=True)
        # Write our Flywheel credentials to JSON in the config directory.
        with open(f"{flywheel_user_home}/.config/flywheel/user.json", "w") as f:
            json.dump({"key": FLYWHEEL_API_KEY, "root": False}, f, ensure_ascii=False)

        source_path = f"{args.program}/{args.site}/NIfTIs/"

        if not os.path.exists(source_path):
            raise FileNotFoundError(
                f"ERROR AT upload2fw: {source_path} directory does not exist. Is sub_mapping empty?"
            )

        for fw_project in next(os.walk(source_path))[1]:  # for each project dir
            proj_path = os.path.join(source_path, fw_project)
            os.system(
                f"fw ingest folder --no-audit-log --group {FLYWHEEL_GROUP} --project {fw_project} --skip-existing -y --quiet {proj_path}"
            )
    return 0


def add_fw_metadata(args) -> int:
    local_path = f"{args.program}/{args.site}/"

    fw_client = flywheel.Client(FLYWHEEL_API_KEY)

    inject_sidecar_metadata(fw_client, FLYWHEEL_GROUP, local_path + "NIfTIs/")

    return 0


def s3_backup_niftis(args) -> int:
    local_path = f"{args.program}/{args.site}/"
    s3_path = (
        f"s3://{PHI_DATA_BUCKET_NAME}/imaging/radiology/{args.program}/{args.site}/"
    )

    return os.system("aws s3 sync " + local_path + "NIfTIs/ " + s3_path + "NIfTIs/")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="A WIP tool to assist with reading DICOM images from Orthanc, conversion to anonymized NIfTI "
        "images, and uploading to Flywheel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # parser.set_defaults(func=lambda x: parser.print_usage())

    subparsers = parser.add_subparsers()

    parser_initdb = subparsers.add_parser("initdb")
    parser_initdb.set_defaults(func=initdb)

    parser_import_uuids = subparsers.add_parser("importuuids")
    parser_import_uuids.add_argument(
        "file",
        type=argparse.FileType("r"),
        help="JSON file containing Orthanc UUIDs to process",
    )
    parser_import_uuids.set_defaults(func=import_uuids)

    parser_check = subparsers.add_parser("check")
    parser_check.add_argument(
        "-l",
        "--limit",
        type=int,
        help="only use the last NUM UUIDs, instead of all UUIDs",
    )
    parser_check.add_argument(
        "--mark-processed",
        action="store_true",
        help="mark all Orthanc UUIDs found as processed",
    )
    parser_check.add_argument(
        "-r",
        "--raw",
        action="store_true",
        help="returns a newline-delimited list of unprocessed UUIDs",
    )
    parser_check.set_defaults(func=check)

    parser_validate = subparsers.add_parser("validate", help="check sub/ses mapping")
    parser_validate.set_defaults(func=validate)

    parser_run = subparsers.add_parser(
        "run",
        help="download images and run deidentification",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_run.add_argument(
        "--batch",
        action="store_true",
        help="skip local processing and submit job(s) to AWS Batch",
    )
    parser_run.add_argument(
        "--sub_id_mapping",
        help="input CSV with list to use for sub ID mapping (optional)",
    )
    parser_run.add_argument(
        "--skip-modalities",
        nargs="*",
        default=["DX", "US"],
        help="space-delimited list of modalities to skip",
    )
    parser_run.add_argument(
        # "uuid", help="space-delimited list of UUIDs to process"
        "--uuid", nargs="+", help="space-delimited list of UUIDs to process"
    )
    parser_run.add_argument(
        "--program",
        nargs="?",
        default="cbtn",
        choices=["cbtn", "corsica","arastoo"],
        help="program namespace",
    )
    parser_run.add_argument(
        "--site",
        nargs="?",
        default="chop",
        help="site namespace",
    )
    parser_run.add_argument(
        "--source",
        nargs="?",
        default="orthanc",
        help="file source",
    )
    parser_run.set_defaults(func=run)

    parser_upload2fw = subparsers.add_parser(
        "upload2fw",
        help="upload results to Flywheel, when complete",
    )
    parser_upload2fw.set_defaults(func=upload2fw)

    parser_add_fw_metadata = subparsers.add_parser(
        "add-fw-metadata", help="add metadata in JSON sidecars to NIfTIs on Flywheel"
    )
    parser_add_fw_metadata.set_defaults(func=add_fw_metadata)

    parser_s3_backup_niftis = subparsers.add_parser(
        "s3-backup-niftis", help="copies NIfTIs to S3"
    )
    parser_s3_backup_niftis.set_defaults(func=s3_backup_niftis)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
