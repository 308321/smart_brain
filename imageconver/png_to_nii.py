import glob
import os
import numpy as np
from PIL import Image
import SimpleITK as sitk

img_paths = glob.glob('./data/masks/0/*.png')
img_arrays_dict = {}

for path in img_paths:
    img = Image.open(path)
    img_array = np.array(img)
    prefix = os.path.splitext(os.path.basename(path))[0].split('_')[0] 
    if prefix not in img_arrays_dict:
        img_arrays_dict[prefix] = []
    img_arrays_dict[prefix].append(img_array)

for prefix, img_arrays in img_arrays_dict.items():
    all_img_array = np.stack(img_arrays, axis=-1)  
    out_nii = sitk.GetImageFromArray(all_img_array)
    output_file_name = os.path.join('./mask_nii', prefix + '.nii.gz')
    sitk.WriteImage(out_nii, output_file_name)


