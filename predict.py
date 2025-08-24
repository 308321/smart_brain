import argparse
import os
from glob import glob

import cv2
import torch
import torch.backends.cudnn as cudnn
import yaml
import albumentations as albu
# from albumentations.augmentations import transforms
# from albumentations.core.composition import Compose
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import archs
from dataset import Dataset
from metrics import iou_score, dice_coef, metrics_all
from utils import AverageMeter


def parse_args(img_size=512):
    parser = argparse.ArgumentParser()

    parser.add_argument('--name', default='ICH' + str(img_size) + '_NestedUNet_woDS',
                        help='model name')

    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    with open('models/%s/config.yml' % args.name, 'r') as f:
        # config = yaml.load(f, Loader=yaml.FullLoader)
        config = yaml.load(f, Loader=yaml.SafeLoader)

    print('-' * 20)
    for key in config.keys():
        print('%s: %s' % (key, str(config[key])))
    print('-' * 20)

    cudnn.benchmark = True

    # create model
    print("=> creating model %s" % config['arch'])
    model = archs.__dict__[config['arch']](config['num_classes'],
                                           config['input_channels'],
                                           config['deep_supervision'])

    # model = model.cuda()

    # Data loading code
    img_ids = glob(os.path.join('inputs', config['dataset'], 'images', '*' + config['img_ext']))            
    img_ids = [os.path.splitext(os.path.basename(p))[0] for p in img_ids]
    # _, val_img_ids = train_test_split(img_ids, test_size=0, random_state=41)   
    val_img_ids = img_ids 

    
    #model.load_state_dict(torch.load('models/%s/model.pth' % config['name']))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.load_state_dict(torch.load('models/%s/model.pth' % config['name'], map_location=device))
    model.eval()

    # val_transform = Compose([
    #     albu.Resize(config['input_h'], config['input_w']),
    #     transforms.Normalize(),
    # ])

    val_dataset = Dataset(
        img_ids=val_img_ids,
        img_dir=os.path.join('inputs', config['dataset'], 'images'),
        mask_dir=os.path.join('inputs', config['dataset'], 'masks'),
        img_ext=config['img_ext'],
        mask_ext=config['mask_ext'],
        num_classes=config['num_classes'],
        transform=None)
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=config['num_workers'],
        drop_last=False)

    avg_meter = AverageMeter()
    avg_meter_dice = AverageMeter()
    avg_meter_precision = AverageMeter()
    avg_meter_recall = AverageMeter()
    avg_meter_f1 = AverageMeter()
    avg_meter_newdice = AverageMeter()
    avg_meter_newiou = AverageMeter()

    for c in range(config['num_classes']):
        os.makedirs(os.path.join('outputs', config['name'], str(c)), exist_ok=True)
    with torch.no_grad():
        for input, target, meta in tqdm(val_loader, total=len(val_loader)):
            # input = input.cuda()
            # target = target.cuda()

            # compute output
            if config['deep_supervision']:
                output = model(input)[-1]
            else:
                output = model(input)

            iou = iou_score(output, target)
            dice = dice_coef(output, target)
            precision, recall, f1, new_iou, new_dice = metrics_all(output, target)
            avg_meter.update(iou, input.size(0))
            avg_meter_dice.update(dice, input.size(0))

            avg_meter_precision.update(precision, input.size(0))
            avg_meter_recall.update(recall, input.size(0))
            avg_meter_f1.update(f1, input.size(0))
            avg_meter_newdice.update(new_dice, input.size(0))
            avg_meter_newiou.update(new_iou, input.size(0))

            output = torch.sigmoid(output).cpu().numpy()
            output = output > 0.5
            for i in range(len(output)):
                for c in range(config['num_classes']):
                    cv2.imwrite(os.path.join('outputs', config['name'], str(c), meta['img_id'][i] + '.png'),
                                (output[i, c] * 255).astype('uint8'))
            # plot_examples(input, target, model, num_examples=3)

    print('IoU: %.4f' % avg_meter.avg)
    print('Dice: %.4f' % avg_meter_dice.avg)

    print('Precision: %.4f' % avg_meter_precision.avg)
    print('Recall: %.4f' % avg_meter_recall.avg)
    print('F1: %.4f' % avg_meter_f1.avg)
    print('newDice: %.4f' % avg_meter_newdice.avg)
    print('newIoU: %.4f' % avg_meter_newiou.avg)
    
    torch.cuda.empty_cache()


def plot_examples(datax, datay, model, num_examples=6):
    fig, ax = plt.subplots(nrows=num_examples, ncols=3, figsize=(18, 4 * num_examples))
    m = datax.shape[0]
    for row_num in range(num_examples):
        image_indx = np.random.randint(m)
        image_arr = model(datax[image_indx:image_indx + 1])[-1].squeeze(0).detach().cpu().numpy()
        ax[row_num][0].imshow(np.transpose(datax[image_indx].cpu().numpy(), (1, 2, 0))[:, :, 0])
        ax[row_num][0].set_title("orignal Image")
        ax[row_num][1].imshow(np.squeeze((image_arr > 0.00)[0, :, :].astype(int)))
        ax[row_num][1].set_title("segmented Image Localization")
        ax[row_num][2].imshow(np.transpose(datay[image_indx].cpu().numpy(), (1, 2, 0))[:, :, 0])
        ax[row_num][2].set_title("Target image")
    plt.show()

if __name__ == '__main__':
    main()
