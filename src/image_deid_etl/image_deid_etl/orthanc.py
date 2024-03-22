import json
import logging
import os
import zipfile

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from image_deid_etl.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

ORTHANC_CREDENTIALS = os.getenv("ORTHANC_CREDENTIALS")
if ORTHANC_CREDENTIALS is None:
    raise ImproperlyConfigured("You must supply ORTHANC_CREDENTIALS.")

ORTHANC_HOST = os.getenv("ORTHANC_HOST")
if ORTHANC_HOST is None:
    raise ImproperlyConfigured("You must supply ORTHANC_HOST.")

ORTHANC_PORT = os.getenv("ORTHANC_PORT", 80)

def get_orthanc_url():
    return f"http://{ORTHANC_CREDENTIALS}@{ORTHANC_HOST}:{ORTHANC_PORT}"

def all_study_uuids(orthanc_url):
# get a list of all study uuids for a given instance
    return requests.get(orthanc_url+'/studies/', verify=False).json()

def all_patient_uuids(orthanc_url):
    return requests.get(orthanc_url+'/patients/', verify=False).json()

def get_uuids_from_accession(orthanc_url,accession):
# requires orthanc_url
    data = {'Level':'Study',
            'Query':{'AccessionNumber':str(accession)} }
    data_json = json.dumps(data)
    resp = requests.post(orthanc_url+'/tools/find', data=data_json, verify=False)
    return resp.json()

def get_uuids_from_mrn(orthanc_url,mrn):
# requires orthanc_url
    data = {'Level':'Study',
            'Query':{'PatientID':str(mrn)} }
    data_json = json.dumps(data)
    resp = requests.post(orthanc_url+'/tools/find', data=data_json, verify=False)
    return resp.json()

def get_patient_uuid_from_mrn(orthanc_url, mrn):
    data = {'Level':'Patient',
            'Query':{'PatientID':str(mrn)} }
    data_json = json.dumps(data)
    resp = requests.post(orthanc_url+'/tools/find', data=data_json, verify=False)
    return resp.json()

def get_uuids(orthanc_url,accession_df,in_type):
    out_list = []
    missing_list=[]
    df_col=[]
    if in_type=='all':
        uuids = all_study_uuids(orthanc_url)
        out_list = list(set(uuids)-set(accession_df)) # find any new uuids
        accession_df=[]
    else:
        for ind,row in accession_df.iterrows():
            if in_type=='accession':
                unique_id = row['accession_num']
                uuids = get_uuids_from_accession(orthanc_url,unique_id)
            elif in_type=='mrn':
                unique_id = row['MRN']
                uuids = get_uuids_from_mrn(orthanc_url,unique_id)
        if uuids:
            df_col.append(uuids)
            out_list = out_list + uuids
        else:
            df_col.append([' '])
            missing_list.append(unique_id)
        accession_df['uuids']=df_col

    return out_list,missing_list,accession_df

def get_study_metadata(orthanc_url,uuid):
# requires orthanc_url
    return requests.get(orthanc_url+'/studies/'+uuid+'/', verify=False).json()

def get_series_metadata(orthanc_url,uuid):
    return requests.get(orthanc_url+'/studies/'+uuid+'/series', verify=False).json()

def get_patient_metadata(orthanc_url,uuid):
    return requests.get(orthanc_url+'/patients/'+uuid+'/', verify=False).json()

def all_instance_mrns(orthanc_url):
# get a list of mrns for all studies on a given instance
#   this takes a lil while to run
    patient_uuids = all_patient_uuids(orthanc_url)
    all_mrns=[]
    for uuid in patient_uuids:
        mrn = get_patient_metadata(orthanc_url,uuid)['MainDicomTags']['PatientID']
        if mrn not in all_mrns:
            all_mrns.append(mrn)
    return all_mrns

def all_instance_accessions(orthanc_url):
# get a list of mrns for all studies on a given instance
#   this takes a lil while to run
    study_uuids = all_study_uuids(orthanc_url)
    all_accessions=[]
    for uuid in study_uuids:
        accession_num = get_study_metadata(orthanc_url,uuid)['MainDicomTags']['AccessionNumber']
        if accession_num not in all_accessions:
            all_accessions.append(accession_num)
    return all_accessions

def compare_s3_orthanc(orthanc_cred,orthanc_ip,orthanc_port,s3_path):
# compares uuids between processed data in S3 bucket & Orthanc
#   returns [list of uuids to process] if not matching & more data on Orthanc (trigger for pipeline)
#   returns 0 if matching, or not matching & more data on S3

    ## create local text file with list of files on s3 & load the list
    os.system('aws s3 ls '+s3_path+'/DICOMs/backup/ | awk '"'{print $4}'"' > s3_files.txt')
    with open('s3_files.txt', mode="r", encoding="utf-8") as f:
        s3_fns = f.readlines()

    ## strip file names to get list of uuids
    s3_uuids = []
    for file in s3_fns:
        fn = file.strip('.zip\n')
        s3_uuids.append(fn)

    ## create local text file with list of uuids on Orthanc & load the list
    localhost=orthanc_cred+'@'+orthanc_ip
    os.system('curl -s -k https://'+localhost+':'+orthanc_port+'/studies > all_study_uuids_'+orthanc_ip+'.json')
    with open('all_study_uuids_'+orthanc_ip+'.json') as data_file:
        orthanc_uuids = json.load(data_file)

    # sort in order to compare
    s3_uuids.sort()
    orthanc_uuids.sort()

    # compare the 2 lists, if not matching & more files on Orthanc, return list of uuids for the next process
    if s3_uuids != orthanc_uuids:
        if len(s3_uuids) < len(orthanc_uuids): # new data in Orthanc
            out_list = []
            for i in orthanc_uuids:
                if i not in s3_uuids:
                    out_list.append(i)
            return out_list
        else:
            return 0
    else:
        return 0


def download_unpack_copy(orthanc_url, uuid, data_dir, ses_mod_to_skip):
    """Download and unpack a specified study from Orthanc"""
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    info = get_series_metadata(orthanc_url,uuid)
    if 'HttpError' in info:
        raise AttributeError(
            "Unable to retrieve study UUID from Orthanc. Invalid study UUID? Orthanc instance up and running?"
            )
        sys.exit(1)
    modality = info[0]['MainDicomTags']['Modality']
    if modality not in ses_mod_to_skip:
        output_path = f"{data_dir}{uuid}.zip"

        # Download the study archive from Orthanc.
        if not os.path.exists(output_path):
            logger.info("Downloading study %s...", uuid)
            os.system(f"curl -s -k {orthanc_url}/studies/{uuid}/archive > {output_path}")
        else:
            logger.info("Already downloaded study %s. Skipping download.", uuid)

        # Unpack the study archive.
        logger.info("Extracting study %s...", uuid)
        with zipfile.ZipFile(output_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)
    else:
        # E.g., Skip digital radiography or ultrasound images.
        logger.info("Not downloading study %s; skipping modality %s.", uuid, modality)

# the following code is to upload a .zip to an Orthanc instance
#   modified from: https://hg.orthanc-server.com/orthanc/file/Orthanc-1.9.7/OrthancServer/Resources/Samples/ImportDicomFiles/OrthancImport.py
def IsJson(content):
    try:
        if (sys.version_info >= (3, 0)):
            json.loads(content.decode())
            return True
        else:
            json.loads(content)
            return True
    except:
        return False

def UploadBuffer(dicom,target_url):
    if IsJson(dicom):
        return
    r = requests.post('%s/instances' % target_url, verify=False, data = dicom) # this is the upload
    try:
        r.raise_for_status()
    except:
        return
    # info = r.json()
    # r2 = requests.get('%s/instances/%s/tags?short' % (target_url, info['ID']),
    #                   verify = False)
    # r2.raise_for_status()
    # tags = r2.json()
    # print('')
    # print('New imported study:')
    # print('  Orthanc ID of the patient: %s' % info['ParentPatient'])
    # print('  Orthanc ID of the study: %s' % info['ParentStudy'])
    # print('  DICOM Patient ID: %s' % (
    #     tags['0010,0020'] if '0010,0020' in tags else '(empty)'))
    # print('  DICOM Study Instance UID: %s' % (
    #     tags['0020,000d'] if '0020,000d' in tags else '(empty)'))
    # print('')

def upload_dicoms(path,target_url):
    print('Uploading DICOMs to Orthanc at '+target_url)
    for root,dirs,files in os.walk(path):
        for file in files:
            f = open(os.path.join(root,file), 'rb')
            content = f.read()
            UploadBuffer(content,target_url)
            f.close()
