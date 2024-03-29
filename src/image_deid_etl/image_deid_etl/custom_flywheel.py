import json
import logging
import os
from glob import glob
import pandas as pd
from fuzzywuzzy import process
import flywheel

logger = logging.getLogger(__name__)

def confirm_proj_exists(fw_client: flywheel.Client, flywheel_group: str, data_dir: str):
    # check if project already exists on Flywheel,
    # if not then create it & add users based on group Projects Template
    fw_proj_dirs = glob(data_dir+'*')
    for proj_path in fw_proj_dirs:
        fw_proj_label = proj_path.split('/')[-1]
        try:
            fw_client.lookup(os.path.join(flywheel_group, fw_proj_label))
        except:
            logger.info(f'Creating new Flywheel project:{fw_proj_label}')
            group = fw_client.get(flywheel_group)
            project = group.add_project(label = fw_proj_label)
            project_id = project['_id']
            existing_perms = project['permissions']
            existing_usrs = []
            for perm in existing_perms:
                existing_usrs.append(perm['_id'])
            logger.info(f'Adding users to new Flywheel project {fw_proj_label} based on group Projects Template')
            for grp_usr in group['permissions_template']:
                usr_id = grp_usr['_id']
                if usr_id not in existing_usrs:
                    fw_client.add_project_permission(project_id, grp_usr)

def inject_sidecar_metadata(fw_client: flywheel.Client, flywheel_group: str, data_dir: str):
# for all JSON sidecar files on the local system, 
# get target Flywheel information from the directory labels
# then grab the acquisition container labels directly from Flywheel
# match the JSON to a container based on matching SeriesNum+SeriesDescription
# "inject" all fields from that JSON into the metadata of files in that container
#
#
#   NOTE:
#       -- assumes that no 2 acquisitions are labeled the exact same on Flywheel
#       -- assumes 1 session per UUID (1 project, 1 session, 1 subject)

    json_files = glob(data_dir+'*/*/*/*/*.json')

    # use directory labels to get target Flywheel path
    fw_proj = glob(data_dir+'*')[0].split('/')[-1]
    subject = glob(data_dir+'*/*')[0].split('/')[-1]
    session = glob(data_dir+'*/*/*')[0].split('/')[-1]
    flywheel_path = f"{flywheel_group}/{fw_proj}/{subject}/{session}"

    # get labels of acquisitions for this session on Flywheel
    session_cntr = fw_client.lookup(flywheel_path)
    fw_acq_labels = []
    for acquisition in session_cntr.acquisitions():
        fw_acq_labels.append(acquisition.label)

    # match local JSON files to acquisitions in the given session based on matching SeriesNumber + SeriesDesc
    for file in json_files:
        metadata = json.load(open(file,'r'), strict=False)
        series_num = str(metadata['SeriesNumber'])
        if len(series_num) == 1:
            series_num = '0'+series_num
        series_desc = metadata['SeriesDescription']
        target_label = f'{series_num} - {series_desc}'
        matching_flywheel_acq = process.extractOne(target_label, fw_acq_labels, score_cutoff=60) # find closest match
        if matching_flywheel_acq:
            matching_flywheel_acq = matching_flywheel_acq[0]
            fw_path_to_acq = f"{flywheel_path}/{matching_flywheel_acq}"
            acq = fw_client.lookup(fw_path_to_acq)
            ## get nifti container w/in this acquisition
            nii_cntr=[]
            base = os.path.basename(file) # get JSON file name w/o file ending
            nii_fn = os.path.splitext(base)[0] + '.nii.gz'
            logger.debug('Adding JSON metadata to '+fw_path_to_acq+'/'+nii_fn)
            nii_cntr = acq.get_file(nii_fn)
            nii_cntr.update_info(metadata)
            # add in 'CT' modality classifications b/c there's an issue with Flywheel not doing it
            try:
                if metadata['Modality']=='CT':
                    logger.debug('Adding CT modality')
                    for file in acq.files:
                        if ('.nii.gz' in file.name):
                            try:
                                acq.replace_file_classification(file.name,{},modality=metadata['Modality']) # this one works
                                json_fn = file.name.strip('nii.gz')+'.json'
                                acq.replace_file_classification(json_fn,{},modality=metadata['Modality'])
                                bval_fn = file.name.strip('nii.gz')+'.bval'
                                acq.replace_file_classification(bval_fn,{},modality=metadata['Modality'])
                                bvec_fn = file.name.strip('nii.gz')+'.bval'
                                acq.replace_file_classification(bvec_fn,{},modality=metadata['Modality'])
                            except:
                                continue
            except KeyError:
                    continue

def upload_dir_2_fw(flywheel_group, local_path):
    for project in glob(data_path+'*'):
        fw_proj = project.split('/')[-1]
        try:
            project_cntr = fw.lookup(f"{flywheel_group}/{fw_proj}") # check project exists
            for subject in glob(data_path+'*/*'):
                sub = subject.split('/')[-1]
                try:
                    sub_cntr = fw.lookup(f"{flywheel_group}/{fw_proj}/{sub}")
                except:
                    print('No subject container for subject '+sub+' in project '+fw_proj+'. Creating new container')
                    sub_cntr = project_cntr.add_subject(label=sub)
                for session in glob(subject+'/*'):
                    ses = session.split('/')[-1]
                    try:
                        ses_cntr = fw.lookup(f"{flywheel_group}/{fw_proj}/{sub}/{ses}")
                    except:
                        print('No session container for subject '+sub+'/'+ses+' in project '+fw_proj+'. Creating new container')
                        ses_cntr = sub_cntr.add_session(label=ses)
                    for acquisition in glob(session+'/*'):
                        acq = acquisition.split('/')[-1]
                        try:
                            acq_cntr = fw.lookup(f"{flywheel_group}/{fw_proj}/{sub}/{ses}/{acq}")
                        except:
                            print('No acquisition container for subject '+sub+'/'+ses+'/'+acq+' in project '+fw_proj+'. Creating new container')
                            acq_cntr = ses_cntr.add_acquisition(label=acq)
                        for root,dirs,files in os.walk(acquisition):
                            for file in files:
                                print('Uploading file to '+sub+'/'+ses+'/'+acq)
                                acq_cntr.upload_file(os.path.join(root,file))
        except flywheel.ApiException as e:
          print('API Error: %d -- %s' % (e.status, e.reason))
