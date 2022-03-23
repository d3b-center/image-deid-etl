# functions for handling data from external sites
#
#   All output subject IDs should fall under a column labeled 'Subject ID' (otherwise need to modify structure_nifti_files later on)
from etl.custom_etl import *
import pandas as pd
import numpy as np

def get_subject_mapping_corsica(mapping_fn,sub_info,data_dir,program,field_to_merge_on):
    master_df = pd.read_csv(mapping_fn)
    master_df = master_df[['SDG-ID','Last Name','First Name','MRN']].drop_duplicates()
    if field_to_merge_on == 'MRN':
        master_df['MRN'] = master_df['MRN'].apply(lambda row: round(int(row)) if not np.isnan(row)  else 0)
        sub_info['mrn'] = sub_info['mrn'].astype(str)
        master_df['MRN']  = master_df['MRN'].astype(str)
        sub_df = pd.merge(sub_info,master_df,how='left',left_on=['mrn'],right_on=['MRN'])
    elif field_to_merge_on == 'Patient_Name':
        sub_info['first_name'] = sub_info["first_name"].astype(str).str.lower()
        sub_info['last_name'] = sub_info["last_name"].astype(str).str.lower()
        master_df['Last Name']  = master_df['Last Name'].astype(str).str.lower()
        master_df['Last Name']  = master_df['Last Name'].astype(str).str.lstrip(' ')
        master_df['Last Name']  = master_df['Last Name'].astype(str).str.rstrip(' ')
        master_df['First Name']  = master_df['First Name'].astype(str).str.lower()
        master_df['First Name']  = master_df['First Name'].astype(str).str.lstrip(' ')
        master_df['First Name']  = master_df['First Name'].astype(str).str.rstrip(' ')
        sub_df = pd.merge(sub_info,master_df,how='left',left_on=['last_name','first_name'],right_on=['Last Name','First Name'])
    sub_df = sub_df.rename(columns={'SDG-ID': 'Subject ID'})
    # get the session labels based on DICOM fields
    dicom_info = get_dicom_fields(data_dir)
    dicom_info['accession_num'] = dicom_info["accession_num"].astype(str)
    sub_df['accession_num'] = sub_df["accession_num"].astype(str)
    sub_df = pd.merge(sub_df,dicom_info,on='accession_num')
    ses_labels,missing_ses = make_session_labels(sub_df,['StudyDesc','PerformedProcDesc','RequestedProcDesc'])        
    # ses_labels.to_csv('~/test.csv',index=False)
    ses_labels['accession_num'] = ses_labels["accession_num"].astype(str)
    sub_df = sub_df.merge(ses_labels,on=['accession_num','StudyDesc'])
    print(sub_df)
    # generate output
    missing_c_ids = sub_df[sub_df['Subject ID'].isna()].reset_index(drop=True)
    sub_df = sub_df.dropna().reset_index(drop=True)
    sub_df = sub_df.drop(columns=['Last Name','First Name'])
    # sub_df = sub_df[['mrn','accession_num','C_ID','session_label']].dropna().reset_index(drop=True)
    return sub_df,missing_c_ids,missing_ses
