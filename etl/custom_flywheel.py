import json
import logging
import os
from glob import glob

import flywheel

from etl.exceptions import ImproperlyConfigured

FLYWHEEL_API_KEY = os.getenv('FLYWHEEL_API_KEY')

if FLYWHEEL_API_KEY is None:
    raise ImproperlyConfigured("You must supply a FLYWHEEL_API_KEY.")

fw = flywheel.Client(FLYWHEEL_API_KEY)

logger = logging.getLogger(__name__)

def inject_sidecar_metadata(flywheel_group, data_dir):
    json_files = glob(data_dir+'*/*/*/*/*.json')
    for file in json_files:
        path_to_acq = '/'.join(file.split('/')[3:-1]) # use local dir structure to perform lookup of acq container on Flywheel
        path_to_acq = path_to_acq.replace('<','_')
        path_to_acq = path_to_acq.replace('>','_')
        path_to_acq = path_to_acq.replace(':','_')
        path_to_acq = path_to_acq.replace('?','_')
        if (path_to_acq[-1] == '.'):
            path_to_acq = path_to_acq[0:-1]
        acq = fw.lookup(f"{flywheel_group}/{path_to_acq}")
        ## get nifti container w/in this acquisition
        nii_cntr=[]
        base = os.path.basename(file)
        nii_fn = os.path.splitext(base)[0] + '.nii.gz'
        logger.debug('Adding JSON metadata to '+path_to_acq+'/'+nii_fn)
        nii_cntr = acq.get_file(nii_fn)
        with open(file) as f:
            metadata = json.load(f)
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
