import os
import numpy as np
import nibabel as nib
from PIL import Image

nii_path = "./original_nii/"
png_path = "./"

nii_files = []
for dirpath, dirnames, filenames in os.walk(nii_path):
    for filename in filenames:
        if filename.endswith(".nii"):
            nii_files.append(os.path.join(dirpath, filename))

for nii_file in nii_files:
    img = nib.load(nii_file)
    data = img.get_fdata()
    pixel_array = np.moveaxis(data, -1, 0)
    if len(pixel_array.shape) != 3 or pixel_array.dtype != np.uint8:
        pixel_array = np.zeros((pixel_array.shape[1], pixel_array.shape[2], pixel_array.shape[0]), dtype=np.uint8)
        for i in range(pixel_array.shape[-1]):
            pixel_array[:, :, i] = (data[:, :, i] / np.max(data[:, :, i]) * 255.0).astype(np.uint8)


    png_subdir="./artwork_png"
    os.makedirs(png_subdir, exist_ok=True)
    
    for i in range(pixel_array.shape[-1]):
        pil_image = Image.fromarray(pixel_array[:,:,i])
        #png_filename ="mask" + f"_{i}.png"
        png_filename = os.path.splitext(os.path.basename(nii_file))[0] + f"_{i}.png"
        png_file = os.path.join(png_subdir, png_filename)
        pil_image.save(png_file)
    
print("Conversion complete.")

