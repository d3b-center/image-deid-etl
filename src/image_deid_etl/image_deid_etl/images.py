import nibabel as nib
import matplotlib.image
from matplotlib import cm
import numpy as np
import cv2
from PIL import Image
from glob import glob
import os
import shutil
import math
import pandas as pd

def merge_images_vertically(imgs):
    '''
    This function merges images vertically
    '''
    #create two lists - one for heights and one for widths
    widths, heights = zip(*(i.size for i in imgs))
    width_of_new_image = max(widths)  #take maximum width
    height_of_new_image = sum(heights)
    # create new image
    new_im = Image.new('RGB', (width_of_new_image, height_of_new_image))
    new_pos = 0
    for im in imgs:
        new_im.paste(im, (0, new_pos))
        new_pos += im.size[1] #position for the next image
    return new_im

def resize_im(input_im,max_w,max_h):
    return cv2.resize(input_im, dsize=(max_w, max_h), interpolation=cv2.INTER_CUBIC)

def split_image(img_fdata,x,y,z):
    z_slice_numer = round(z/2)
    z_slice = img_fdata[:, :, z_slice_numer]
    y_slice_number = round(y/2)
    y_slice = img_fdata[:, y_slice_number, :]
    x_slice_number = round(x/2)
    x_slice = img_fdata[x_slice_number, :, :]
    max_width = max(y_slice.shape[0],x_slice.shape[0],z_slice.shape[0])
    max_height = max(y_slice.shape[1],x_slice.shape[1],z_slice.shape[1])
    x_slice = resize_im(x_slice,max_width,max_height)
    y_slice = resize_im(y_slice,max_width,max_height)
    z_slice = resize_im(z_slice,max_width,max_height)
    return np.hstack((x_slice,y_slice,z_slice))

def make_image_montage(filename,out_dir):
# make one image for a given nifti file (3 dimensions, horizontally stacked)
    missing=0
    img = nib.load(filename) #read nii
    if (img.get_data_dtype() != np.dtype(np.int16)):
        print('ERROR WITH DATA TYPE OF NIFTI FILE. CHECK '+filename)
        missing = 1
    else:
        img_fdata = img.get_fdata()
        if len(img.shape) == 3:
            (x,y,z) = img.shape
        else:
            (x,y,z,w) = img.shape
            img_fdata = img_fdata[:,:,:,0]
        montage = split_image(img_fdata,x,y,z)
        fn = filename.split('/')[-1]
        out_fn = out_dir+'/'+fn.strip('.nii.gz')+'.png'
        matplotlib.image.imsave(out_fn, montage, cmap = cm.gray)
    return missing

def make_nifti_images(data_dir, parent_dir):
# make PNGS for all nii.gz files in NIfTIs/
    ses_list = glob(data_dir+'/*/*/*')
    files_2_skip = ['ep2d_diff_mddw_','Diffusion_Series_Texture','RGB','ColFA','DTI_Fibers']
    files_2_skip_2 = ['Perfusion_Weighted','RGB','Color_Map','Vessels_3D']
    missing_ims=[]
    count=0
    for ses in ses_list:
        if glob(ses+'/*') == []:
            print('DELETING EMPTY DIRECTORY: '+ses)
            os.rmdir(ses)
        else:
            print('MAKING IMAGES: '+ses)
            # make image for each nifti
            for root,dirs,files in os.walk(ses):
                for file in files:
                    if (file.endswith('.nii.gz')) and \
                       (not any(x in file for x in files_2_skip)) and \
                       (not all(x in file for x in files_2_skip_2)):
                        ses_dir = parent_dir+'_'.join((root.split('/')[4:6])) # output / c-id_session
                        if not os.path.exists(ses_dir):
                            os.makedirs(ses_dir)
                        nii_path = os.path.join(root,file)
                        print(nii_path)
                        count+=1
                        missing_tag = make_image_montage(nii_path,ses_dir)
                        if missing_tag:
                            missing_ims.append(nii_path)
                            count-=1
            # combine all images for a session for easier review
            imgs = [Image.open(im) for im in glob(ses_dir+"/*.png")]
            ses_label = ses.split('/')[-1]
            out_fn = ses_dir.split('/')[-1]
            max_acq_per_im = 15
            if len(imgs) > max_acq_per_im: # force session images to have max. 15 acquitions each
                num_images=math.ceil(len(imgs)/max_acq_per_im)
                for i in range(num_images):
                    start_ind = i*max_acq_per_im
                    end_ind = ((i+1)*max_acq_per_im)-1
                    these_imgs = imgs[start_ind:end_ind]
                    out_im = merge_images_vertically(these_imgs)
                    out_im.save(parent_dir+'/'+out_fn+'_'+str(i+1)+'.jpg')
            else:
                out_im = merge_images_vertically(imgs)
                out_im.save(parent_dir+'/'+out_fn+'.jpg')
            shutil.rmtree(ses_dir, ignore_errors=True) # delete individual images
    print('Images generated for '+str(count)+' nifti files')
    if missing_ims:
        missing_df=pd.DataFrame({'missing_images':missing_ims})
        missing_df.to_csv(parent_dir+'missing_images.csv',index=False)
    return missing_ims
