import os
from glob import glob
import cv2
import numpy as np
from tqdm import tqdm


def main():
    img_size = 512
    path = 'data'
    os.makedirs('inputs/ICH%d/images' % img_size, exist_ok=True)
    os.makedirs('inputs/ICH%d/masks/0' % img_size, exist_ok=True)

    for filename in tqdm(os.listdir('data/images')):
        img = cv2.imread(os.path.join(path, 'images', filename))
        mask = np.zeros((img.shape[0], img.shape[1]))
        # 数组中 > 127(白色)的元素记为ture，否则记为false
        mask_ = cv2.imread(os.path.join(path, 'masks', '0',  filename), cv2.IMREAD_GRAYSCALE) > 127
        mask[mask_] = 1
        if len(img.shape) == 2:
            img = np.tile(img[..., None], (1, 1, 3))
        if img.shape[2] == 4:
            img = img[..., :3]
        # img = cv2.resize(img, (img_size, img_size))
        # mask = cv2.resize(mask, (img_size, img_size))
        cv2.imwrite(os.path.join('inputs/ICH%d/images' % img_size,
                    filename), img)
        cv2.imwrite(os.path.join('inputs/ICH%d/masks/0' % img_size,
                    filename), (mask * 255).astype('uint8'))


if __name__ == '__main__':
    main()