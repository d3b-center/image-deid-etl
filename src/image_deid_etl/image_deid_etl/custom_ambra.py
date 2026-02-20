#!/usr/bin/env python3

from ambra_sdk.api import Api
import shutil
import os
from image_deid_etl.exceptions import ImproperlyConfigured

# Ambra login

AMBRA_HOST_URL = os.getenv("AMBRA_HOST_URL")
if AMBRA_HOST_URL is None:
    raise ImproperlyConfigured("You must supply AMBRA_HOST_URL.")

AMBRA_USERNAME = os.getenv("AMBRA_USERNAME")
if AMBRA_USERNAME is None:
    raise ImproperlyConfigured("You must supply AMBRA_USERNAME.")

AMBRA_PASSWORD = os.getenv("AMBRA_PASSWORD")
if AMBRA_PASSWORD is None:
    raise ImproperlyConfigured("You must supply AMBRA_PASSWORD.")


api = Api.with_creds(AMBRA_HOST_URL, AMBRA_USERNAME, AMBRA_PASSWORD)

def get_ambra_api():
    # Access the instance API
    return Api.with_creds(AMBRA_HOST_URL, AMBRA_USERNAME, AMBRA_PASSWORD)

def get_ambra_user_info(api):
    return api.Session.user().get()

def route_study(api, study_uuid):
    # Route the unsent studies to the destination
    manual_route_id = '3e25959b-4305-4222-967c-8e540e35078a' # D3b to (on-prem) Flywheel
    print(f"Routing study {study_uuid}...")
    send_result = api.Study.manual_route(
        uuid=study_uuid,
        route_id=manual_route_id
        )
    send_result.get()

def ambra_download_study(study):
    # Download the study to a local zip
    r = api.Storage.Study.download(engine_fqdn=study.engine_fqdn,
                                        namespace=study.storage_namespace,
                                        study_uid=study.study_uid,
                                        bundle='dicom',
                                        phi_namespace=study.phi_namespace)
    if r.status_code != 200:
        raise RuntimeError(
            f"Error downloading study {study.study_uuid} from Ambra (status code {r.status_code})."
        )
    else:
        with open(f'{study.accession_number}.zip', 'wb') as f:
            shutil.copyfileobj(r.raw, f)
