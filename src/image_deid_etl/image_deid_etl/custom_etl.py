import importlib.resources as pkg_resources
import json
import os
import shutil
from datetime import datetime
from glob import glob

import pandas as pd
import pydicom
from dateutil.parser import parse


def move_suspicious_files(file_list,out_dir):
# move files that don't match the expected data type for images
# (based on output of make_nifti_images())
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for file in file_list:
        source_dir = '/'.join(file.split('/')[0:-1])
        fns = os.listdir(source_dir) # files to move
        acq_path='/'.join(file.split('/')[3:-1])
        target_dir=out_dir+acq_path
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for fn in fns:
            shutil.move(source_dir+'/'+fn, target_dir)

def mrn_append_zeros(mrn_list):
    out=[]
    for mrn in mrn_list:
        if len(mrn)==5:
            out.append('000'+mrn)
        elif len(mrn)==6:
            out.append('00'+mrn)
        elif len(mrn)==7:
            out.append('0'+mrn)
        else:
            out.append(mrn)
    return out

def delete_acquisitions_by_modality(data_dir,modality):
    acq_list = glob(data_dir+'*/*/*') # directories
    for acq in acq_list:
        if acq.split('/')[-1][0:2] == modality:
            shutil.rmtree(acq)

def delete_sessions_by_modality(data_dir,modality):
    ses_list = glob(data_dir+'*/*') # directories
    for ses_path in ses_list:
        ses = ses_path.split('/')[-1] # session label
        ses_modality = ses.split(' ')[1]
        if ses_modality == modality:
            shutil.rmtree(ses_path)

def delete_sessions(data_dir,string_match):
    ses_list = glob(data_dir+'*/*') # directories
    for ses_path in ses_list:
        ses = ses_path.split('/')[-1] # session label
        if string_match.lower() in ses.lower():
            shutil.rmtree(ses_path)

def get_subject_info_dir(data_dir):
# uses local directory structure to return a list of MRNs & accessions (as a pandas df)
# assumes structure: {data_dir}/{sub}/{ses} where sub = {mrn ... ...} & ses = {accession ... ...}
    dir_list = glob(data_dir+'/*/*') # sessions
    dir_list = [x.strip(data_dir) for x in dir_list] # remove the parent dir from the strings
    mrns = [x.split(' ')[0] for x in dir_list] # grab only first part of [MRN LastName FirstName]
    mrns = [i.lstrip('0') if i.startswith('0') else i for i in mrns] # strip leading 0s from any mrn
    last_names = [x.split(' ')[1] for x in dir_list]
    first_names = [x.split(' ')[2].split('/')[0] for x in dir_list]
    accessions = [x.split('/')[1].split(' ')[0] for x in dir_list]
    return pd.DataFrame({'mrn': mrns, 'accession_num': accessions, 'first_name':first_names, 'last_name':last_names})

def get_body_part_examined(desc):
    abbrv=[]
    parts=[]
    if ('brain' in desc.lower()) \
    or ('head' in desc.lower()) \
    or ('stealth' in desc.lower()) \
    or ('neuro' in desc.lower()) \
    or ('orbits' in desc.lower()) \
    or ('spectroscopy' in desc.lower()):
        abbrv.append('B')
        parts.append('brain')
    if ('face' in desc.lower()) or \
        ('maxillofacial' in desc.lower()):
        abbrv.append('F')
        parts.append('face')
    if 'spine' in desc.lower():
        abbrv.append('S')
        parts.append('spine')
    if 'neck' in desc.lower():
        abbrv.append('N')
        parts.append('neck')
    if 'pituitary' in desc.lower():
        abbrv.append('P')
        parts.append('pituitary')
    if ('sinuses' in desc.lower()) or \
        ('sinus' in desc.lower()):
        abbrv.append('Si')
        parts.append('sinuses')
    if 'chest' in desc.lower():
        abbrv.append('C')
        parts.append('chest')
    if 'finger' in desc.lower():
        abbrv.append('Fi')
        parts.append('finger')
    if 'iac' in desc.lower():
        abbrv.append('IAC')
        parts.append('iac')
    if 'shoulder' in desc.lower():
        abbrv.append('Sh')
        parts.append('shoulder')
    if 'knee' in desc.lower():
        abbrv.append('K')
        parts.append('knee')
    if ('skull base to mid thigh' in desc.lower()) or \
        ('hip' in desc.lower()):
        abbrv.append('Bo')
        parts.append('Body')
    if abbrv==[]:
        return []
    else:
        abbrv=''.join(abbrv)
        parts='_'.join(parts)
        return abbrv+'_'+parts

def make_session_labels(input_df,fields_to_use):
# construct session label based on DICOM metadata
#   assumes directory structure: {data_dir}/{sub}/{ses}/{acq}/*.dcm
    session_labels=[]
    accession_numbers=[]
    missing_sessions=[]
    req_descs=[]
    perf_descs=[]
    study_descs=[]
    # for each subject, loop through acquisitions/DICOMs until find desired info & construct session label
    for ind,row in input_df.iterrows(): # for each session
        subject_dob=row['DOB']
        date_of_imaging = row['ImagingDate']
        time_of_imaging = row['ImagingTime']
        accession = row['accession_num']
        req_desc = row['RequestedProcDesc']
        perf_desc = row['PerformedProcDesc']
        study_desc = row['StudyDesc']
        body_part_examined=[]
        desc=[]
        body_part_examined=[]
        for i in range(len(fields_to_use)): # loop through input fields, in order, until a description is found
            if (desc==[]) or (body_part_examined==[]):
                this_field = fields_to_use[i]
                if (row[this_field] != ' ') and (row[this_field] != []):
                    desc = row[this_field]
                    # print(row['Last Name'])
                    body_part_examined = get_body_part_examined(desc)
        if len(time_of_imaging)<4:
            study_time=''
        else:
            study_time='_'+time_of_imaging[0:2]+'h'+time_of_imaging[2:4]+'m'
        if (subject_dob == 19010101) or (subject_dob == []) or (date_of_imaging == []) or (body_part_examined == []):
            # print('Not enough info in DICOM header to create session labels for '+ses)
            missing_sessions.append(accession)
        else:
            age_in_days_at_imaging = abs((date_of_imaging - subject_dob).days)
            session_labels.append(str(age_in_days_at_imaging)+'d_'+body_part_examined+study_time)
            accession_numbers.append(accession)
            req_descs.append(req_desc)
            perf_descs.append(perf_desc)
            study_descs.append(study_desc)
    out_df = pd.DataFrame({'accession_num': accession_numbers, \
                            'session_label': session_labels , \
                            'RequestedProcDesc': req_descs , \
                            'PerformedProcDesc': perf_descs , \
                            'StudyDesc': study_descs })
    return out_df,pd.DataFrame(missing_sessions,columns=['accession_num'])

def get_dicom_fields(data_dir):
    sub_list = glob(data_dir+'/*')
    accession_numbers=[]
    dobs=[]
    events=[]
    study_times=[]
    req_proc=[]
    perf_proc=[]
    study=[]
    body_parts=[]
    for sub in sub_list:
        ses_list = glob(sub+'/*')
        for ses in ses_list:
            if ('NIfTIs' not in ses) and (len(os.listdir(ses)) != 0): # if directory is not empty
                subject_dob = []
                date_of_imaging = []
                time_of_imaging = []
                accession=[]
                study_desc=[]
                req_proc_desc=[]
                perf_proc_desc=[]
                # loop through all DICOMs in a session until found necessary fields
                for file in glob(ses+'/*/*.dcm'):
                    ds = pydicom.read_file(file) # os.path.join(root, file)
                    if subject_dob == []:
                        try:
                            subject_dob = ds[0x10,0x30].value # date of birth
                        except:
                            subject_dob = []
                    if date_of_imaging == []:
                        try:
                            date_of_imaging = ds[0x08,0x20].value # study date
                            # date_of_imaging = ds[0x08,0x22].value # acquisition date
                        except:
                            date_of_imaging = []
                    if time_of_imaging == []:
                        try:
                            # 070907.0705 represents a time of 7 hours, 9 minutes and 7.0705 seconds.
                            time_of_imaging = ds[0x08,0x30].value # study time (0008,0030)
                        except:
                            time_of_imaging = []
                    if accession == []:
                        try:
                            accession = ds[0x08,0x50].value
                        except:
                            accession=[]
                    if study_desc == []:
                        try:
                            study_desc = ds[0x08,0x1030].value # Study Description (0008,1030)
                        except:
                            study_desc=[]
                    if req_proc_desc == []:
                        try:
                            req_proc_desc = ds[0x32,0x1060].value # requested procedure description
                        except:
                            req_proc_desc=[]
                    if perf_proc_desc == []:
                        try:
                            perf_proc_desc = ds[0x40,0x254].value # performed procedure description (0040,0254)
                        except:
                            perf_proc_desc=[]
                    if subject_dob and date_of_imaging and accession and study_desc: # if these are found, break out of for loop
                        break
                if subject_dob:
                    subject_dob = datetime.strptime(subject_dob, '%Y%m%d') #.strftime('%m/%d/%Y')
                if date_of_imaging:
                    date_of_imaging = datetime.strptime(date_of_imaging, '%Y%m%d') #.strftime('%m/%d/%Y')
                accession_numbers.append(accession)
                dobs.append(subject_dob)
                events.append(date_of_imaging)
                study_times.append(time_of_imaging)
                req_proc.append(req_proc_desc)
                perf_proc.append(perf_proc_desc)
                study.append(study_desc)
    # fix any empty lists of lists that can happen when processing 1 study
    if (len(accession_numbers)==1) and (accession_numbers[0]==[]):
        accession_numbers=''
    elif (len(dobs)==1) and (dobs[0]==[]):
        dobs=''
    elif (len(events)==1) and (events[0]==[]):
        events=''
    elif (len(study_times)==1) and (study_times[0]==[]):
        study_times=''
    elif (len(req_proc)==1) and (req_proc[0]==[]):
        req_proc=''
    elif (len(perf_proc)==1) and (perf_proc[0]==[]):
        perf_proc=''
    elif (len(study)==1) and (study[0]==[]):
        study=''
    return pd.DataFrame({'accession_num': accession_numbers,\
                            'DOB':dobs, \
                            'ImagingDate':events, \
                            'ImagingTime':study_times, \
                            'RequestedProcDesc':req_proc, \
                            'PerformedProcDesc':perf_proc, \
                            'StudyDesc':study} )

def split_missing_values(input_df,col_name):
    missing_df = input_df[input_df[col_name].isna()].reset_index(drop=True) # rows with missing values (na)
    missing_df = missing_df.dropna(axis=1, how='all') # drop columns w/all na
    out_df = input_df.dropna().reset_index(drop=True) # rows w/o missing values
    return out_df,missing_df

def get_subject_mapping_cbtn(cbtn_df,sub_info,data_dir):
    from image_deid_etl.orthanc import get_orthanc_url,get_patient_metadata,get_patient_uuid_from_mrn
    orthanc_url = get_orthanc_url()
    # map MRN to C-ID
    cbtn_df_sub = cbtn_df[['CBTN Subject ID','MRN','First Name','Last Name']].drop_duplicates()
    sub_info['mrn'] = sub_info['mrn'].astype(str)
    cbtn_df_sub['MRN'] = cbtn_df_sub['MRN'].astype(str)
    cbtn_df_sub['MRN'] = cbtn_df_sub['MRN'].str.lstrip('0')
    sub_info['first_name'] = sub_info['first_name'].astype(str).str.lower()
    sub_info['last_name'] = sub_info['last_name'].astype(str).str.lower()
    cbtn_df_sub['First Name'] = cbtn_df_sub['First Name'].astype(str).str.lower()
    cbtn_df_sub['Last Name'] = cbtn_df_sub['Last Name'].astype(str).str.lower()
    # force format of DOB column so that it can be handled properly
    cbtn_df['DOB'] = pd.to_datetime(cbtn_df.DOB)
    cbtn_df['DOB'] = cbtn_df['DOB'].dt.strftime('%m/%d/%y')
    # get cbtn info for this specific subject
    sub_df = pd.merge(sub_info, cbtn_df_sub, how='left', left_on=['mrn'], right_on=['MRN'])
    # if any are still missing C-ID, try FirstName/LastName
    sub_df, missing_c_ids = split_missing_values(sub_df,'CBTN Subject ID')
    if not missing_c_ids.empty:
        sub_df2 = pd.merge(missing_c_ids,cbtn_df_sub,how='left',left_on=['last_name','first_name'],right_on=['Last Name','First Name'])
        sub_df = pd.concat([sub_df,sub_df2],ignore_index=True)
    # get the session labels based on DICOM fields
    dicom_info = get_dicom_fields(data_dir)
    sub_df = pd.concat([sub_df, dicom_info],axis=1) # assumes only 1 row (1 study being processed)
    # if there are subjects missing DOB, try to fill values from other studies on Orthanc
    if (not sub_df[sub_df['DOB']==''].empty):
        for ind, row in sub_df.iterrows():
            if (row['DOB']==''):
                dob = []
                patient_mrn = mrn_append_zeros([str(row['MRN'])])[0]
                patient_uuid = get_patient_uuid_from_mrn(orthanc_url, patient_mrn)
                patient_metadata = get_patient_metadata(orthanc_url, patient_uuid[0])
                if 'PatientBirthDate' in patient_metadata['MainDicomTags'].keys():
                    dob = patient_metadata['MainDicomTags']['PatientBirthDate']
                else:
                    dob = []
                if len(dob) > 0:
                    sub_df.at[ind, 'DOB'] = datetime.strptime(dob, '%Y%m%d')
    # if STILL missing, use the one from cbtn-all table
    if (not sub_df[sub_df['DOB'] == ''].empty):
        for ind, row in sub_df.iterrows():
            if (row['DOB'] == ''):
                c_id = row['CBTN Subject ID']
                sub_rows = cbtn_df[cbtn_df['CBTN Subject ID'] == c_id]
                dob = sub_rows['DOB'].tolist()[0]
                sub_df.at[ind, 'DOB'] = datetime.strptime(dob, '%m/%d/%y')
    # fix empty descriptions
    sub_df.loc[sub_df['PerformedProcDesc'].astype(str)=="[]",["PerformedProcDesc"]]=' '
    sub_df.loc[sub_df['StudyDesc'].astype(str)=="[]",["StudyDesc"]]=' '
    sub_df.loc[sub_df['RequestedProcDesc'].astype(str)=="[]",["RequestedProcDesc"]]=' '
    # find session labels
    ses_labels,missing_ses = make_session_labels(sub_df,['PerformedProcDesc','StudyDesc','RequestedProcDesc'])
    sub_df = sub_df.merge(ses_labels,on=['PerformedProcDesc','StudyDesc','RequestedProcDesc'])
    # generate output
    sub_df,missing_c_ids = split_missing_values(sub_df,'CBTN Subject ID')
    sub_df = sub_df.drop(columns=['MRN'])
    sub_df = sub_df.rename(columns={'CBTN Subject ID': 'C_ID'})
    return sub_df,missing_c_ids,missing_ses

def delete_json_field(json_obj,field):
    try:
        del json_obj[field]
    except:
        pass

def filter_sidecars(data_dir):
    ## remove remaining known PHI-containing fields from the sidecars
    fields_to_remove = ['DeviceSerialNumber','ImageComments','InstitutionAddress','InstitutionalDepartmentName','InstitutionName',\
                        'ProcedureStepDescription','ProtocolName','StationName']
    for root,dirs,files in os.walk(data_dir):
        matches = [match for match in files if ".json" in match] # grab only '.json' files
        for file in matches:
            file_path=os.path.join(root,file)
            print(file_path)
            json_file = json.load(open(file_path,'r'), strict=False)
            for field in fields_to_remove:
                delete_json_field(json_file,field)
            with open(file_path, 'w') as outfile:
                json.dump(json_file, outfile)

def convert_dicom2nifti(data_dir):
# dcm2niix options:
#   -b : BIDS sidecar (y/n/o [o=only: no NIfTI], default y)
#       -ba: anonymize BIDS (y/n, default y)
#   -f : filename %d=description
#   -p : Philips precise float (not display) scaling (y/n, default y)
#   -z : gz compress images (y/o/i/n/3, default n)
#   -v : verbose (n/y or 0/1/2, default 0)
#   -w : write behavior for name conflicts (0,1,2, default 2: 0=skip duplicates, 1=overwrite, 2=add suffix)
    acq_list = glob(data_dir+'/*/*/*')
    ## convert all acquisitions using Chris Rorden's dcm2niix with anon BIDS sidecar enabled
    for acquisition in acq_list:
        # print(acquisition)
        if glob(acquisition+'/*.nii.gz')==[]: # if there are no niftis already in the directory
            os.system('dcm2niix -b y -ba y -f ''"%d"'' -p y -z y -v 0 ''"'+acquisition+'"'' ')
            # if there are STILL no niftis or if dcm2niix returns an error code,
            # try decompressing the DICOMs first with the GDCM tool gdcmconv
            # (this should handle errors with JPEG2000 compression in OpenJPEG within dcm2niix)
            exit_code = os.popen('echo $?').readlines()[0].strip('\n')
            if (glob(acquisition+'/*.nii.gz')==[]) or (exit_code != '0'): 
                for file_path in glob(acquisition+'/*.dcm'): # for each DICOM file
                    os.system(f'gdcmconv -w "{file_path}" "{file_path}"  ') # -w flag for decompression
                os.system('dcm2niix -w 1 -b y -ba y -f ''"%d"'' -p y -z y -v 0 ''"'+acquisition+'"'' ') # now re-try the conversion
            # add voxel dimensions to sidecar
            if glob(acquisition+'/*.nii.gz'): # if there are NIfTIs for this acquisition
                sidecars = glob(acquisition+'/*.json')
                for json_path in sidecars: # loop through sidecars & add in voxel dim's
                    try:
                        json_file = json.load(open(json_path,'r'))
                        for file in glob(acquisition+'/*.dcm'): # loop through DICOMs until find necessary tags
                            ds = pydicom.read_file(file) # os.path.join(root, file)
                            try:
                                pix_spacing = ds[0x28,0x30].value # Pixel Spacing Description (0028,0030)
                            except:
                                pix_spacing=[]
                            try:
                                # slice_thick = ds[0x18,0x50].value # Slice Thickness (0018,0050)
                                slice_thick = ds[0x18,0x88].value # Spacing Between Slices (0018,0088)
                            except:
                                slice_thick=[]
                            if (pix_spacing!=[]) and (slice_thick!=[]):
                                json_file['dim1']=pix_spacing[0]
                                json_file['dim2']=pix_spacing[1]
                                json_file['dim3']=slice_thick
                                with open(json_path, 'w') as outfile:
                                    json.dump(json_file, outfile)
                                break
                    except:
                        continue


def closest(lst, K):
# get the closest (min) value in list (lst) to an integer (K)
    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]

def get_fw_proj_cbtn(cbtn_df,sub_mapping):
# using the C-ID and age-at-imaging, extract the target project for each session
#   based on the CBTN-all spreadsheet. Uses age-at-imaging to find the closest event
#   in time in CBTN-all & then uses the Diagnosis category to derive a Flywheel project label
#   (based on a mapping dictionary).
    cbtn_df = cbtn_df[['CBTN Subject ID','Age at Diagnosis','Diagnosis']]
    proj_mapping = json.load(pkg_resources.open_text(__package__, 'diagnosis_mapping.json'))
    sub_list = sub_mapping['C_ID'].values.tolist()
    session_list = sub_mapping['session_label'].values.tolist()
    age_at_imaging = [i.split('d_')[0] for i in session_list] # extract age-at-imaging from session label for *all* subjects
    ind=0
    fw_projects = []
    missing_tag = 'subject missing in cbtn-all'
    for sub in sub_list:
        # get all the data from CBTN-all for this subject
        sub_rows = cbtn_df[(cbtn_df['CBTN Subject ID'] == sub)]
        if sub_rows.empty:
            fw_projects.append(missing_tag)
        else:
            sub_rows = sub_rows[sub_rows['Diagnosis']!='Not Reported'] # remove 'not reported' rows
            sub_rows = sub_rows[sub_rows['Diagnosis']!='Other'] # remove 'other' rows
            if (not sub_rows.empty) and (not sub_rows[sub_rows['Diagnosis']=="Supratentorial or Spinal Cord PNET"].empty): # if there is a PNET diagnosis
                if len(sub_rows['Diagnosis'].unique()) > 1: # if there are additional diagnoses available
                    sub_rows = sub_rows[sub_rows['Diagnosis']!='Supratentorial or Spinal Cord PNET']     # remove "PNET" rows                
            if sub_rows.empty:
                diagnosis_to_use='Not Reported'
                fw_projects.append(proj_mapping[diagnosis_to_use]) # use hard-coded dictionary to map to fw-proj label
            elif (len(sub_rows['Diagnosis'].unique()) == 1):
                diagnosis_to_use=sub_rows['Diagnosis'].unique().tolist()[0]
                fw_projects.append(proj_mapping[diagnosis_to_use]) # use hard-coded dictionary to map to fw-proj label                
            else:
                # use the age-in-days at imaging (from the session labels) to find the row with the closest age-at-diagnosis value
                closest_diagnosis = closest(sub_rows['Age at Diagnosis'].values.astype(int).tolist(), int(age_at_imaging[ind])) # closest age row
                # grab the diagnosis label for that row
                diagnosis_to_use = sub_rows[sub_rows['Age at Diagnosis']==str(closest_diagnosis)]['Diagnosis'].tolist()[0]
                # map to the FW-project labels
                fw_projects.append(proj_mapping[diagnosis_to_use]) # use hard-coded dictionary to map to fw-proj label
        ind+=1
    sub_mapping['fw_proj'] = fw_projects # add column to output
    subs_no_proj = sub_mapping[sub_mapping['fw_proj']==missing_tag].reset_index(drop=True)
    subs_with_proj = sub_mapping[sub_mapping['fw_proj']!=missing_tag].reset_index(drop=True)
    return subs_with_proj,subs_no_proj

def delete_local_data(data_dir,list_2_delete):
# deletes sessions based on accession #s in input df
    session_list = glob(data_dir+'*/*')
    for index,row in list_2_delete.iterrows():
        accession_number = row['accession_num']
        data_path = [i for i in session_list if accession_number in i][0]
        shutil.rmtree(data_path, ignore_errors=True)
    # check & remove any empty sub dir's
    delete_empty_dirs(data_dir)

def delete_empty_dirs(data_dir):
# deletes empty sub/session/acq dir's
    parent_list = glob(data_dir+'*')
    for top_dir in parent_list:
        if ('files' not in top_dir) and ('NIfTIs' not in top_dir) and ('DICOMs' not in top_dir) and ('JPGs' not in top_dir):
            sub_list=glob(top_dir+'/*')
            for sub in sub_list:
                sub_sessions=glob(sub+'/*')
                if sub_sessions!=[]:
                    for session in sub_sessions:
                        acq_dirs = glob(session+'/*')
                        for acq in acq_dirs: # remove empty acq dir's
                            if os.listdir(acq) == []: # if no files in acq dir
                                os.rmdir(acq)
                        try:
                            os.rmdir(session) # remove empty session dir's
                        except:
                            continue
                try:
                    os.rmdir(sub) # remove empty subject dir's
                except:
                    continue

def delete_files(data_dir,file_ending):
# deletes any files ending in file_ending within data_dir/
    for root,dirs,files in os.walk(data_dir):
        matches = [match for match in files if file_ending in match] # grab only '.json' files
        for file in matches:
            file_path=os.path.join(root,file)
            os.remove(file_path)

def structure_nifti_files(data_dir,sub_mapping,output_dir,program):
# intended for use on output files from the processing pipeline
# use input df & info in JSON sidecars to create output directories
#   move nifti, json, bval/bvec files to output dir's (leaving DICOMs in place)
    ## make target directories & move output files there
    data_path = glob(data_dir+'*/*')[0] # assumes only 1 session (1 study being processed)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir) # parent directory
    for index,row in sub_mapping.iterrows():
        if program == 'cbtn':
            c_id = row['C_ID']
        else:
            c_id = row['Subject ID']
        session = row['session_label']
        fw_proj = row['fw_proj']
        session_dir_in = os.path.join(output_dir,fw_proj,c_id,session)
        if not os.path.exists(session_dir_in):
            os.makedirs(session_dir_in)
        # move the files
        acq_list = glob(data_path+'/*')
        # for each acquisition, construct the acquisition label based on sidecar info
        # print(acq_list)
        for acq in acq_list:
            sidecar_fn = glob(acq+'/*.json')
            if (sidecar_fn) and ('dcm2nii_invalidName' not in sidecar_fn[0]):
                sidecar_fn=sidecar_fn[0]
                sidecar = json.load(open(sidecar_fn))
                print(sidecar_fn)
                try:
                    if sidecar['Modality']!='CT':
                        notCT=1
                    else:
                        notCT=0
                except:
                    notCT=1
                if (len(sidecar)<20) and \
                (not (any(x in sidecar_fn for x in ['ep2d_diff_mddw_','Diffusion_Series_Texture','RGB','ColFA','DTI_Fibers','Perfusion_Weighted','RGB','Color_Map','Vessels_3D']))) and \
                (notCT) : 
                    purgatory='/'.join(output_dir.split('/')[0:2])+'/NIfTIs_short_json/' # output should go to '<program>/<site>/NIfTIs_to_check/'
                    session_dir=os.path.join(purgatory,fw_proj,c_id,session)
                    if not os.path.exists(session_dir):
                        os.makedirs(session_dir)
                else:
                    session_dir=session_dir_in
                acq_label = str(sidecar['SeriesDescription'])
                # avoid moving files for known PHI-containing acqusitions based on hard-coded strings
                if ('Study_acquired_outside_hospital' not in acq_label) and \
                    (not (any(x in acq_label.lower() for x in ['screensave','screen save','screen_save']))) and \
                    (not (any(x in acq_label.lower() for x in ['cover image','cover_image']))) and \
                    ('documents' not in acq_label.lower()) and \
                    (not (any(x in acq_label.lower() for x in ['dose_report','dose report','dosereport']))) and \
                    ('protocol' not in acq_label.lower()) and \
                    ('capture' not in acq_label.lower()):
                    series_num = str(sidecar['SeriesNumber'])
                    if len(series_num) == 1:
                        series_num = '0'+series_num
                    # replace any single quotation marks with underscore in acquisition labels (a rare case but has been found)
                    acq_label = acq_label.replace("'",'_')
                    acq_target_dir = session_dir+'/'+series_num+' - '+acq_label
                    # if it doesn't already exist, create it
                    if not os.path.exists(acq_target_dir):
                        os.makedirs(acq_target_dir)
                    else:
                    # if it already exists, append a copy number
                        copy_num=1
                        dir_created=0
                        while dir_created==0:
                            acq_target_dir = acq_target_dir+' ('+str(copy_num)+')'
                            if not os.path.exists(acq_target_dir):
                                os.makedirs(acq_target_dir)
                                dir_created=1
                            else:
                                copy_num+=1
                    # now move all the files for this acquisition
                    nifti_files=glob(acq+'/*.nii.gz')
                    for file in nifti_files:
                        # replace any single quotation marks with underscore
                        new_fn = file.replace("'",'_')
                        os.rename(file, new_fn)
                        shutil.move(new_fn, acq_target_dir)
                    json_files=glob(acq+'/*.json')
                    for file in json_files:
                        # replace any single quotation marks with underscore
                        new_fn = file.replace("'",'_')
                        os.rename(file, new_fn)
                        shutil.move(new_fn, acq_target_dir)
                    bval_files=glob(acq+'/*.bval')
                    for file in bval_files:
                        # replace any single quotation marks with underscore
                        new_fn = file.replace("'",'_')
                        os.rename(file, new_fn)
                        shutil.move(new_fn, acq_target_dir)
                    bvec_files=glob(acq+'/*.bvec')
                    for file in bvec_files:
                        # replace any single quotation marks with underscore
                        new_fn = file.replace("'",'_')
                        os.rename(file, new_fn)
                        shutil.move(new_fn, acq_target_dir)
                else:
                    shutil.rmtree(acq) # deletes directories & all files
                if not os.listdir(acq_target_dir): # if no contents
                    os.rmdir(acq_target_dir) # only deletes empty directories
                if not os.listdir(session_dir):
                    os.rmdir(session_dir)
                sub_dir = '/'.join(session_dir.split('/')[0:5])
                if not os.listdir(sub_dir):
                    os.rmdir(sub_dir)
                proj_dir = '/'.join(sub_dir.split('/')[0:4])
                if not os.listdir(proj_dir):
                    os.rmdir(proj_dir)

def is_date(string, fuzzy=False):
# https://stackoverflow.com/questions/25341945/check-if-string-has-date-any-format
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True
    except ValueError:
        return False

def strip_diffusion_fn_dates(data_dir):
    # for all acqusition directories in proj/NIfTIs, looks for EDT/EST/PDT in acq ending
    # if exists, strips date/times from acq dir & files w/in
    #   also removes date/time from SeriesDescription in JSON sidecars
    #
    # data_dir must have structure: program/site/NIfTIs/
    acq_list = glob(data_dir+'*/*/*/*') # assumes {data_dir}/fw_proj/sub/ses/acq/ structure
    for acq in acq_list:
        # print(acq.split(':')[-1])
        # if is_date(acq.split(':')[-1],fuzzy=True):
        if acq[-3:] == 'EDT' or acq[-3:] == 'EST' or acq[-3:] == 'PDT'  or acq[-3:] == 'PST': # if acq dir ends with time zone
            split_name = acq.split('/')
            this_path = '/'.join(split_name[0:6])
            acq_label = split_name[-1]
            split_name = acq_label.split(':')
            if 'Universal' in acq_label:
                target_name = " ".join((split_name[0],split_name[1],split_name[2]))
            else:
                target_name = split_name[0]
            # ========= change directory name
            target_path = this_path+'/'+target_name # includes seriesNum
            if not os.path.isdir(target_path): # if it doesn't already exist
                out_dir = target_path
            else:
                count=1
                while count !=0:
                    if os.path.isdir(target_path+' '+str(count)): # avoid overwritting by adding a # to the end
                        count+=1
                    else:
                        out_dir = target_path+' '+str(count)
                        count=0
            # print('Old path: '+acq)
            # print('New path: '+out_dir)
            shutil.move(acq, out_dir) # do the change
            for file in os.listdir(out_dir):
                split_fn = file.split('_')
                if split_fn[0] == 'Universal':
                    series_desc = '_'.join(split_fn[0:3])
                else:
                    series_desc = split_fn[0]
                if file.endswith('.json'):
                    str_end='.json'
                    # ======== edit SeriesDescription tag in JSON sidecars
                    source_filepath = os.path.join(out_dir,file)
                    with open(source_filepath, 'r') as data_file: # read the json
                        data = json.load(data_file)
                    data["SeriesDescription"] = series_desc # modify the field
                    with open(source_filepath, 'w') as data_file: # overwrite the json
                        data = json.dump(data, data_file)
                elif file.endswith('.nii.gz'):
                    str_end='.nii.gz'
                elif file.endswith('.bval'):
                    str_end='.bval'
                elif file.endswith('.bvec'):
                    str_end='.bvec'
                # print(out_dir+'/'+series_desc+str_end)
                os.rename(out_dir+'/'+file,\
                          out_dir+'/'+series_desc+str_end)

# def remove_routine_brain(data_dir):
# sometimes all acquisition labels in a sessin will contain "ROUTINE_BRAIN"
#   this function removes that part of the string


# def fix_acq_dirs(data_dir):
# # session_dir is not defined.... this won't work until fixed
#     acq_list = glob(data_dir+'NIfTIs/*/*/*')
#     for acq in acq_list:
#         sidecar_fn = glob(acq+'/*.json')[0]
#         sidecar = json.load(open(sidecar_fn))
#         acq_label = str(sidecar['SeriesDescription'])
#         series_num = str(sidecar['SeriesNumber'])
#         if len(series_num) == 1:
#             series_num = '0'+series_num
#         acq_target_dir = session_dir+'/'+series_num+' - '+acq_label
#         if not os.path.exists(acq_target_dir):
#             os.makedirs(acq_target_dir)
#         # now move all the files
#         nifti_files=glob(acq+'/*.nii.gz')
#         for file in nifti_files:
#             shutil.move(file, acq_target_dir)
#         json_files=glob(acq+'/*.json')
#         for file in json_files:
#             shutil.move(file, acq_target_dir)
#         bval_files=glob(acq+'/*.bval')
#         for file in bval_files:
#             shutil.move(file, acq_target_dir)
#         bvec_files=glob(acq+'/*.bvec')
#         for file in bvec_files:
#             shutil.move(file, acq_target_dir)

# def send_email_to_self(e_mail,password,text_body):
#     import smtplib
#     sent_from = e_mail
#     to = [e_mail]
#     subject = 'This is a test.'
#     body = 'Testing testing 1 2 3'
#     email_text = """\
#     From: %s
#     To: %s
#     Subject: %s
#     %s
#     """ % (sent_from, ", ".join(to), subject, body)
#     try:
#         smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
#         smtp_server.ehlo()
#         smtp_server.login(e_mail, password)
#         smtp_server.sendmail(sent_from, to, email_text)
#         smtp_server.close()
#         print ("Email sent successfully!")
#     except Exception as ex:
#         print ("Something went wrong….",ex)

