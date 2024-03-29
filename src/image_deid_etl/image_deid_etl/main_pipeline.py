import logging

import pandas

from image_deid_etl.exceptions import ImproperlyConfigured
from image_deid_etl.external_data_handling import *
from image_deid_etl.images_no_save import *
import sys

logger = logging.getLogger(__name__)

todays_date = datetime.now().strftime('%Y-%m-%d')

SUBJECT_ID_MAPPING_PATH = os.getenv("SUBJECT_ID_MAPPING_PATH")
if SUBJECT_ID_MAPPING_PATH is None:
    raise ImproperlyConfigured(
        "You must supply a valid string path in SUBJECT_ID_MAPPING_PATH."
    )


def subject_info(local_path, program, file_dir, validate=0):
    # site_name = local_path.split('/')[1]
    logger.info('Getting subject ids.')
    sub_info = get_subject_info_dir(local_path) # sub_info = get_subject_info_dicoms(local_path) # slower b/c iterates over all DICOM files, doesn't depend on dir structure/names though
    sub_missing_c_ids=pd.DataFrame()
    sub_missing_ses=pd.DataFrame()
    sub_missing_proj=pd.DataFrame()
    if program == 'cbtn':
        # get CBTN Subject IDs
        try:
            cbtn_all_df = pandas.read_csv(SUBJECT_ID_MAPPING_PATH)
        except IndexError as error:
            logger.error("Missing CBTN subject ID .csv file from internal EIG database: %r", error)
            sys.exit(1)
        try:
            sub_mapping,sub_missing_c_ids,sub_missing_ses = get_subject_mapping_cbtn(cbtn_all_df,sub_info,local_path)
        except ValueError as error:
            logger.error("Error in getting CBTN subject mapping: %r", error)
            sys.exit(1)
    elif program == 'corsica':
        corsica_fn='corsica_identified_mapping.csv'
        sub_mapping,sub_missing_c_ids,sub_missing_ses = get_subject_mapping_corsica(corsica_fn,sub_info,local_path,program,'Patient_Name') # MRN or Patient_Name
    # account for missing subject labels
    if not sub_missing_c_ids.empty:
        output_fn = file_dir+'missing_subject_ids_'+todays_date+'.csv'
        logger.warning('      WARNING: Subject(s) with missing C-IDs found. Please check  '+output_fn)
        sub_missing_c_ids.to_csv(output_fn,index=False)
        missing_subj_id_flag=1
    else:
        missing_subj_id_flag=0
    #  account for missing session labels
    if not sub_missing_ses.empty:
        output_fn = file_dir+'missing_sessions_'+todays_date+'.csv'
        logger.warning('      WARNING: Subject(s) with missing session labels found. Please check  '+output_fn)
        sub_missing_ses.to_csv(output_fn,index=False)
        missing_ses_flag=1
    else:
        missing_ses_flag=0
    logger.info('Getting target Flywheel projects.')
    # get target Flywheel project based on diagnosis
    if program == 'cbtn':
        sub_mapping,sub_missing_proj = get_fw_proj_cbtn(cbtn_all_df,sub_mapping)
        if not sub_missing_proj.empty:
            output_fn = file_dir+'missing_diagnosis_'+todays_date+'.csv'
            logger.warning('      WARNING: Subject(s) not found in CBTN-all. Please check  '+output_fn)
            sub_missing_proj.to_csv(output_fn,index=False)
    elif program == 'corsica':
        fw_dest_proj = 'Corsica'
        sub_mapping['fw_proj'] = [fw_dest_proj] * len(sub_mapping)
        sub_missing_proj=[]
    if validate:
        return sub_mapping,sub_missing_c_ids,sub_missing_ses,sub_missing_proj
    else:
        return sub_mapping, missing_ses_flag, missing_subj_id_flag

def validate_info(local_path, program, file_dir):
    # save a CSV of the subject mapping & DICOM fields to review
    sub_mapping,sub_missing_c_ids,sub_missing_ses,sub_missing_proj = subject_info(local_path + 'DICOMs/', program,
                                                                                  file_dir, 1)
    output_fn = file_dir+'sub_mapping_'+todays_date+'.csv'
    sub_mapping.to_csv(output_fn,index=False)
    print('Mapping created: '+output_fn)
    proj_list=sub_mapping['fw_proj'].unique().tolist()
    print('Unique FW-projects: '+', '.join(proj_list))
    if not sub_missing_c_ids.empty:
        sub_list=sub_missing_c_ids['accession_num'].unique().tolist()
        print('Accessions missing C-IDs '+', '.join(sub_list))
    if not sub_missing_ses.empty:
        sub_list=sub_missing_ses['accession_num'].unique().tolist()
        print('Accessions missing sessions '+', '.join(sub_list))
    if program == 'cbtn': # should include any study w/multiple possible destination FW projects
        if not sub_missing_proj.empty:
            sub_list=sub_missing_proj['accession_num'].unique().tolist()
            print('Accessions missing projects '+', '.join(sub_list))

def run_deid(local_path, program):
    file_dir = local_path+'files/'
    # The "files/" directory path needs to exist, otherwise subject_info will fail to write the csv files. Equivalent
    # to mkdir -p.
    os.makedirs(file_dir, exist_ok=True)
    sub_mapping, missing_ses_flag, missing_subj_id_flag = subject_info(local_path + 'DICOMs/', program, file_dir)
    if missing_ses_flag or missing_subj_id_flag:
        return missing_ses_flag,missing_subj_id_flag
    else:
        output_fn = file_dir+'sub_mapping_'+todays_date+'.csv'
        if os.path.exists(output_fn):
            ind=1
            fn_found=0
            while (fn_found==0):
                output_fn = file_dir+'sub_mapping_'+todays_date+'_'+str(ind)+'.csv'
                if os.path.exists(output_fn):
                    ind+=1
                else:
                    fn_found=1
        sub_mapping.to_csv(output_fn,index=False)
        print('Mapping created: '+output_fn)
        proj_list = sub_mapping['fw_proj'].unique().tolist()
        print('Unique FW-projects: '+', '.join(proj_list))
        #  convert DICOMs to NIfTI
        logger.info('Converting DICOMs to NIfTI.')
        convert_dicom2nifti(local_path+'DICOMs/') # skips acquisition directories w/niftis already in them
        filter_sidecars(local_path+'DICOMs/')
        if sub_mapping.empty:
            raise FileNotFoundError(
                f"'NIfTI files created but no subject mapping to use. Target directory cannot be created. Exiting..."
            )
            sys.exit(1)
        else:
         # move ouput files to c-id/session directories and clean of acqusition + file names
         # move files w/short JSON sidecars to NIfTIs_short_json/
            structure_nifti_files(local_path+'DICOMs/',sub_mapping,local_path+'NIfTIs/',program)
            strip_diffusion_fn_dates(local_path+'NIfTIs/')
            # # remove_routine_brain(local_path+'NIfTIs/')
        # make images of nifti files for visual inspection
            missing_ims = make_nifti_images(local_path+'NIfTIs/',local_path+'JPGs/')
        # move acquisitions w/o image to quarantine
            if missing_ims:
                move_suspicious_files(missing_ims,local_path+'NIfTIs_to_check/')
        return 0,0
        # update logs 
            # log_df = pd.read_csv(log_path)
            # # # log_df['accession_num'] = log_df['accession_num'].astype(str)
            # # # out_df = pd.merge(log_df,sub_mapping,on='accession_num')
            # out_df = pd.concat([log_df,sub_mapping], sort=False)
            # out_df.to_csv(log_path,index=False)