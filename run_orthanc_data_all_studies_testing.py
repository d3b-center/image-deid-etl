# Process new data from Orthanc
#   python3 run_orthanc_data_all_studies.py

        # # ====== get list of new UUIDs to process ========================
        # logging.info('Comparing UUIDs between internal Orthanc and s3 backup.')
        # new_uuids = compare_s3_orthanc(cred, ip, port, s3_path)
#
#   TO DO:
#       -- set up batch processing of studies
#       -- add processed studies to 'all_orthanc_study_uuids.json' & archive the old JSON file (eventually this could be updating relDB)
#       -- add mechanism to delete quarantine files OR upload after manually checked
#       -- set up logging if Flywheel upload fails
#       -- set up logging for missing-info (e.g., missing_sessions_*.csv)
#       -- slack notification of files-to-check
#       -- track sessions not processed (e.g., XR, US, etc.)
#
#   Figure out how to best QC requests (i.e. check that all accession #s made it, or if not then why)
#
#   for external studies:
#       -- use req/proc/study desc that has most across subj's (??)

# ======= USER INPUTS: ====================
program='cbtn'
site='chop'

s3_path = 's3://d3b-phi-data-prd/imaging/radiology/'+program+'/'+site+'/'
s3_path_ims = 's3://d3b-phi-data-prd/imaging/radiology/images4dl/'
local_path = program+'/'+site

# study_uuid = 'f90cd746-10017fbb-44472a28-391f1a52-3186cf1a'
uuid_record_fn = 'all_orthanc_study_uuids_testing.json'


check_orthanc=0 # check to see if there are new studies
run_pipeline=0 # run the pipeline & upload "safe" files
delete_local=0 # delete files off EC2


validate = 0 # check sub/ses mapping
upload2fw = 1
add_fw_metadata=0 # add metadata in JSON sidecars to NIfTIs on Flywheel
s3_backup_niftis=0 # copies NIfTIs to s3
s3_backup_images=0 # copies JPGs to s3


# ************** MAIN PROCESSES **********************
from orthanc import *
from custom_etl import *
from custom_flywheel import *
from main_pipeline import *
from datetime import datetime
import logging
import pandas as pd
import sys
import os
import json
import shutil
from glob import glob

# ====== validate the inputs ====== 
if local_path[-1:] != '/':
    local_path = local_path+'/'

if s3_path[-1:] != '/':
    s3_path = s3_path+'/'

log_path='logs/processed.csv'

file_path = local_path+'files/'

# ====== start logging ========================
todays_date = datetime.now().strftime('%Y-%m-%d')
if not os.path.exists(local_path+"files/"):
    os.makedirs(local_path+"files/")
logging.basicConfig(filename=local_path+"files/"+program+"_"+site+"_status_log_"+todays_date+".log", level=logging.INFO, format='%(asctime)s %(message)s')
# todays_time = datetime.now().strftime('%H:%M:%S')
# todays_datetime = todays_date+' @ '+todays_time

# # ====== get list of UUIDs to process ========================
if check_orthanc:
    orthanc_url = get_orthanc_url('AWS')
    new_uuids,missing_list,input_df = get_uuids(orthanc_url,uuid_record_fn,'all')
    if new_uuids:
        print(str(len(new_uuids))+' new studies found on Orthanc.')
    else:
        print('No new UUIDs found on Orthanc')

# validate that we have all the right info/mapping
if validate:
    logging.info('Generating subject mapping for validation.')
    validate_info(local_path,logging,program,file_path)

# run the pipeline
if run_pipeline:
    ## ************** download studies from Orthanc ************** 
    max_studies = 40
    logging.info('Checking for new UUIDs.')
    orthanc_url = get_orthanc_url('AWS')
    new_uuids,missing_list,input_df = get_uuids(orthanc_url,uuid_record_fn,'all')
    if len(new_uuids) > max_studies:
        new_uuids = new_uuids[0:(max_studies-1)]
    ##  ************** if there are new uuids, download & prep files ************** 
    if new_uuids:
        logging.info('Found UUIDs in Orthanc, beginning to download.')
        session_modality_to_skip = ['DX','US'] # DX=XR
        download_unpack_copy(orthanc_url, s3_path, new_uuids, local_path+'DICOMs/',session_modality_to_skip)
        ## remove any acquisitions/sessions that we don't want to process
        delete_acquisitions_by_modality(local_path+'DICOMs/','OT')
        delete_acquisitions_by_modality(local_path+'DICOMs/','SR')
        delete_sessions(local_path+'DICOMs/','script') # delete any "script" sessions
        delete_sessions(local_path+'DICOMs/','Bone Scan')
        # delete_sessions_by_modality(local_path+'DICOMs/','XR') # delete X-rays
        # delete_sessions_by_modality(local_path+'DICOMs/','US') # delete ultrasounds
    else:
        logging.info('No UUIDs found in Orthanc.')
        print('No UUIDs found in Orthanc.')
    # ************** run conversion, de-id, quarantine suspicious files, restructure output for upload ************** 
    logging.info('Commencing de-identification process.')
    run_deid(local_path, s3_path, logging, program, log_path)
    ## ************** upload "safe" files to Flywheel **************************** 
    os.system('flywheel_cli/cli/fw import folder '+program+'/'+site+'/NIfTIs/ --group d3b -y --skip-existing')
    inject_sidecar_metadata(local_path+'NIfTIs/')
    ## ************** backup NIfTIs to s3 ****************************
    os.system('aws s3 sync '+local_path+'NIfTIs/ '+s3_path+'NIfTIs/')
    print('DONE PROCESSING STUDIES')
    logging.info('DONE PROCESSING STUDIES')
    if os.path.exists(local_path+'NIfTIs_to_check/'):
        print('There are files to check in: '+local_path+'NIfTIs_to_check/')
        logging.info('There are files to check in: '+local_path+'NIfTIs_to_check/')
    if os.path.exists(local_path+'NIfTIs_short_json/'):
        print('There are files to check in: '+local_path+'NIfTIs_short_json/')
        logging.info('There are files to check in: '+local_path+'NIfTIs_short_json/')
    ## *************** update list of UUIDs *************************************************
    uuid_list = json.load(open(uuid_record_fn,'r'))
    uuid_list = uuid_list + new_uuids
    with open('all_orthanc_study_uuids_new.json', 'w') as f:
        json.dump(uuid_list, f)


# ====== upload to Flywheel ========================
if upload2fw:
    os.system('flywheel_cli/cli/fw import folder '+program+'/'+site+'/NIfTIs/ --group d3b -y --skip-existing')

if add_fw_metadata:
# assumes local structure == Flywheel structure
    inject_sidecar_metadata(local_path+'NIfTIs/')

if s3_backup_niftis:
    os.system('aws s3 sync '+local_path+'NIfTIs/ '+s3_path+'NIfTIs/')

if s3_backup_images:
    os.system('aws s3 sync '+local_path+'JPGs/ '+s3_path_ims)
    os.system('aws s3 sync '+local_path+'JPGs_3/ '+s3_path_ims)

if delete_local:
    if os.path.exists(local_path+'DICOMs/'):
        shutil.rmtree(local_path+'DICOMs/')
        print('Deleted from local: '+local_path+'DICOMs/')
    if os.path.exists(local_path+'NIfTIs/'):
        shutil.rmtree(local_path+'NIfTIs/')
        print('Deleted from local: '+local_path+'NIfTIs/')
    if os.path.exists(local_path+'NIfTIs_short_json/'):
        shutil.rmtree(local_path+'NIfTIs_short_json/')
        print('Deleted from local: '+local_path+'NIfTIs_short_json/')
    if os.path.exists(local_path+'NIfTIs_to_check/'):
        shutil.rmtree(local_path+'NIfTIs_to_check/')
        print('Deleted from local: '+local_path+'NIfTIs_to_check/')
    if os.path.exists(local_path+'JPGs/'):
        shutil.rmtree(local_path+'JPGs/')
        print('Deleted from local: '+local_path+'JPGs/')
    if os.path.exists(local_path+'JPGs_2/'):
        shutil.rmtree(local_path+'JPGs_2/')
        print('Deleted from local: '+local_path+'JPGs_2/')
    if os.path.exists(local_path+'JPGs_3/'):
        shutil.rmtree(local_path+'JPGs_3/')
        print('Deleted from local: '+local_path+'JPGs_3/')
