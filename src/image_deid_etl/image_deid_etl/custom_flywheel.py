import json
import logging
import os
from glob import glob
import pandas as pd

import flywheel

logger = logging.getLogger(__name__)


def inject_sidecar_metadata(fw_client: flywheel.Client, flywheel_group: str, data_dir: str):
# for all JSON sidecar files on the local system, get target Flywheel information from
# the subject mapping CSV (created earlier in the main "run" processes)
# then grab the acquisition container labels directly from Flywheel
# match the JSON to a container based on matching SeriesNumber
# "inject" all fields from that JSON into the metadata of files in that container
#
#   when there's more than 1 match...

    json_files = glob(data_dir+'NIfTIs/*/*/*/*/*.json')

    sub_mapping = pd.read_csv(glob(data_dir+'files/*.csv')[0])
    session = sub_mapping['session_label'][0]
    fw_proj = sub_mapping['fw_proj'][0]
    subject = sub_mapping['C_ID'][0]
    flywheel_path = f"{flywheel_group}/{fw_proj}/{subject}/{session}"

    # get labels of acquisitions for this session on Flywheel
    session_cntr = fw_client.lookup(flywheel_path)
    fw_acq_labels = []
    for acquisition in session_cntr.acquisitions():
        fw_acq_labels.append(acquisition.label)
    acq_numbers = [x.split(' - ')[0] for x in fw_acq_labels]

    # match local JSON files to acquisitions in the given session based on matching SeriesNumber
    for file in json_files:
        metadata = json.load(open(file,'r'), strict=False)
        series_num = str(metadata['SeriesNumber'])
        if len(series_num) == 1:
            series_num = '0'+series_num
        index = acq_numbers.index(series_num)
        matching_flywheel_acq = fw_acq_labels[index]
        fw_path_to_acq = f"{flywheel_path}/{matching_flywheel_acq}"
        acq = fw_client.lookup(fw_path_to_acq)
        ## get nifti container w/in this acquisition
        nii_cntr=[]
        base = os.path.basename(file)
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
