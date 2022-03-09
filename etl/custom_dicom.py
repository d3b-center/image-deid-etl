import pydicom
import os
from glob import glob
from statistics import mode
import shutil
import pandas as pd
from custom_etl import delete_empty_dirs
import magic

def get_dicom_tags(data_dir):
# does not depend on folder structure but loops through every DICOM (slow)
    values=[]
    for root,dirs,files in os.walk(data_dir):
        for file in files[0:20]:
            file_path = os.path.join(root,file)
            print(file_path)
            if (magic.from_file(file_path) == 'DICOM medical imaging data'):
                ds = pydicom.read_file(file_path)
                try:
                    modality = ds[0x08,0x60].value
                except:
                    modality=[]
                try:
                    accession_number = ds[0x08,0x50].value
                except:
                    accession_number=[]
                try:
                    patient_id = ds[0x10,0x20].value # mrn
                except:
                    patient_id=[]
                try:
                    patient_name = ds[0x10,0x10].value # patient name
                except:
                    patient_name=[]
                try:
                    subject_dob = ds[0x10,0x30].value # date of birth
                except:
                    subject_dob=[]
                try:
                    date_of_imaging = ds[0x08,0x22].value # acquisition date
                except:
                    date_of_imaging=[]
                try:
                    study_desc = ds[0x08,0x1030].value # Study Description (0008,1030)
                except:
                    study_desc=[]
                try:
                    req_proc_desc = ds[0x32,0x1060].value # requested procedure description
                except:
                    req_proc_desc=[]
                try:
                    perf_proc_desc = ds[0x40,0x254].value # performed procedure description (0040,0254)
                except:
                    perf_proc_desc=[]
                sub_info=[modality,patient_id,patient_name,accession_number,subject_dob,date_of_imaging,req_proc_desc,perf_proc_desc,study_desc]
                if sub_info not in values:
                    values.append(sub_info)
    return pd.DataFrame(values,columns=['modality','mrn','patient_name','accession_num','dob','date_imaging','requested_proc_desc','performed_proc_desc','study_desc'])

def get_dicom_tags_sessions(data_dir):
# assumes {data_dir}/{sub}/${ses}/{acq} structure
# one result per session
    sub_list = glob(data_dir+'*')
    values=[]
    for sub in sub_list:
        for session in glob(sub+'/*'):
            pop=1
            for dicom in glob(session+'/*/*.dcm'):
                if pop:
                    ds = pydicom.read_file(dicom)
                    try:
                        modality = ds[0x08,0x60].value
                        accession_number = ds[0x08,0x50].value
                        patient_id = ds[0x10,0x20].value # mrn
                        patient_name = ds[0x10,0x10].value # patient name
                        subject_dob = ds[0x10,0x30].value # date of birth
                        date_of_imaging = ds[0x08,0x22].value # acquisition date
                        study_desc = ds[0x08,0x1030].value # Study Description (0008,1030)
                        try:
                            req_proc_desc = ds[0x32,0x1060].value # requested procedure description
                        except:
                            req_proc_desc = ' '
                        try:
                            perf_proc_desc = ds[0x40,0x254].value # performed procedure description (0040,0254)
                        except:
                            perf_proc_desc = ' '
                        pop=0
                        values.append([modality,patient_id,patient_name,accession_number,subject_dob,date_of_imaging,req_proc_desc,perf_proc_desc,study_desc])
                    except:
                        continue
    return pd.DataFrame(values,columns=['modality','mrn','patient_name','accession_num','dob','date_imaging','requested_proc_desc','performed_proc_desc','study_desc'])

def get_subject_info_dicoms(data_dir):
# gets MRNs & accessions from DICOM metadata
#   iterates over all DICOMs in data_dir
#  ** assumes only DICOM files exist in data_dir **
    accessions = []
    mrns = []
    for root,dirs,files in os.walk(data_dir):
        for file in files:
            ds = pydicom.read_file(os.path.join(root, file))
            accession_number = ds[0x08,0x50].value
            if accession_number not in accessions:
                accessions.append(accession_number)
                patient_id = ds[0x10,0x20].value
                mrns.append(patient_id)
    return pd.DataFrame({'mrn': mrns, 'accession_number': accessions} )

def structure_dicom_files_subdirs(data_dir):
# same as structure_dicom_files but assumes data is structured into {data_dir}/{sub}
    for sub in glob(data_dir+'*'):
        if ('DICOMs' not in sub) and ('files' not in sub):
            structure_dicom_files(sub,data_dir+'DICOMs/')
    # for sub in glob(data_dir+'*/DICOM*'): # this was used for {program}/{site}/{sub}/DICOM/
    #     if 'DICOMs' not in sub:
    #         structure_dicom_files(sub,data_dir+'/DICOMs/')

def structure_dicom_files(data_dir,out_dir,accession_mapping=[]):
# intended for use on raw data prior to processing (e.g., files received from external sites)
# for all DICOMs in data_dir, uses DICOM metadata to create the target directory structure:
#   {out-dir}/{sub}/{session}/{acq}
#       where,
#           sub = <MRN Sub-Name>
#           session = <Accession-number Session-modality Study-description>
#           acq = <Series-modality Series-description>\
# moves DICOM to target acquisition directory
# deletes any remaining empty dir's
#
#   ** assumes all files in data_dir/ are DICOMs **
    group_assign_accessions=[]
    accession_ind=1
    for root,dirs,files in os.walk(data_dir):
        if 'DICOMs/' not in root:
            for file in files:
                file_path = os.path.join(root,file)
                # print(file_path)
                if ('.DS_Store' not in file_path) and \
                    (magic.from_file(file_path) == 'DICOM medical imaging data') and \
                    ('DICOMDIR' not in file_path):
                    if file_path[-4:] != '.dcm':
                        file_path_dcm = file_path + '.dcm'
                        # print(file_path_dcm)
                        os.rename(file_path,file_path_dcm)
                    else:
                        file_path_dcm = file_path
                    print(file_path_dcm)
                    ds = pydicom.read_file(file_path_dcm)
                    sub_name = ds[0x10,0x10].value # patient's name
                    if '^' in sub_name:
                        sub_name = str(sub_name).split('^')
                        sub_name = sub_name[0]+' '+sub_name[1]
                    # try:
                    sub_id = ds[0x10,0x20].value # patient ID
                    modality = ds[0x08,0x60].value
                    if modality not in ['PR','OT','KO','SR']:
                        accession = ds[0x08,0x50].value
                        study_desc = ds[0x08,0x1030].value # study description
                        series_desc = ds[0x08,0x103e].value # series description
                        # clean rogue characters
                        study_desc = study_desc.replace('+','')
                        study_desc = study_desc.replace('/','')
                        series_desc = series_desc.replace('+','')
                        series_desc = series_desc.replace('/','')
                        # make target path if non-existing
                        sub_dir = out_dir+str(sub_id)+' '+str(sub_name)
                        if not os.path.exists(sub_dir):
                            os.makedirs(sub_dir)
                        # fill with a dummy accession number if need be
                        if (accession == ''):
                            try:
                                study_date = ds[0x08,0x20].value
                            except:
                                study_date = ds[0x08,0x12].value
                            sub_rows = accession_mapping[(accession_mapping['PatientID']==sub_id) & (accession_mapping['StudyDate']==int(study_date))]
                            if len(sub_rows)==1:
                                accession = str(sub_rows['AccessionNumber'].to_list()[0])
                            else:
                                sub_rows = sub_rows[sub_rows['Modality']==modality]
                                if len(sub_rows)==1:
                                    accession = str(sub_rows['AccessionNumber'].to_list()[0])
                        ses_dir = sub_dir+'/'+accession+' '+study_desc
                        if not os.path.exists(ses_dir):
                            os.makedirs(ses_dir)
                        acq_dir = ses_dir+'/'+modality+' '+series_desc
                        if not os.path.exists(acq_dir):
                            os.makedirs(acq_dir)
                        # move this DICOM to the target dir
                        print(acq_dir)
                        shutil.copy(file_path_dcm, acq_dir)
                    else:
                        os.remove(file_path_dcm) # delete files of non-interest modalities
                    # except:
                        # continue
                else:
                    os.remove(file_path) # delete any .DS_Store files
        delete_empty_dirs(data_dir)
        # inject session modality
        # session_list = glob(out_dir+'*/*')
        # modality_list=[]
        # for session in session_list:
        #     # get list of modalities for this session
        #     acq_list = glob(session+'/*')
        #     for acq in acq_list:
        #         acq_split = acq.split('/')
        #         modality_list.append(acq_split[-1].split(' ')[0])
        #     session_modality = mode(modality_list)
        #     accession = session.split('/')[-1].split(' ')[0]
        #     session_desc = session.split(accession)[-1]
        #     session_path = session.split(accession)[0]
        #     target_name = session_path+accession+' '+session_modality+session_desc
        #     os.rename(session,target_name)


def validate_dicom_structure_subdirs(data_dir):
    for sub in glob(data_dir+'*'):
        invalid=validate_dicom_structure(sub+'/DICOM/')
        if invalid:
            return 1
        else:
            continue
    return 0

def validate_dicom_structure(data_dir):
# checks for expected subject-dir and acquisition-dir names
#   Returns 0 if valid (expected dir names), 1 if invalid
#   only checks first DICOM file per acquisition
    for root,dirs,files in os.walk(data_dir):
        if len(files) < 1:
            files_to_check = files
        else:
            file_to_check = files[0]
            file_path = os.path.join(root,file_to_check)
            if '.DS_Store' not in file_path:
                ds = pydicom.read_file(file_path)
                sub_id = ds[0x10,0x20].value # patient ID
                sub_name = ds[0x10,0x10].value # patient's name
                target_sub_dir = str(sub_id)+' '+str(sub_name)
                sub_dir = root.split('/')[2]
                if sub_dir == target_sub_dir: # valid subj directory
                    modality = ds[0x08,0x60].value
                    series_desc = ds[0x08,0x103e].value # study description
                    series_desc = series_desc.replace('+','')
                    series_desc = series_desc.replace('/','')
                    target_acq_dir = modality+' '+series_desc
                    acq_dir = root.split('/')[-1]
                    if acq_dir != target_acq_dir:
                        return 1
                else:
                    return 1
    else:
        return 1
    return 0
