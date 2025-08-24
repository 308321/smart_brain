import numpy as np
import torch
import torch.nn.functional as F


def iou_score(output, target):
    smooth = 1e-5

    if torch.is_tensor(output):
        output = torch.sigmoid(output).data.cpu().numpy()
    if torch.is_tensor(target):
        target = target.data.cpu().numpy()
    output_ = output > 0.5
    target_ = target > 0.5
    intersection = (output_ & target_).sum()
    union = (output_ | target_).sum()

    return (intersection + smooth) / (union + smooth)


def dice_coef(output, target):
    smooth = 1e-5

    output = torch.sigmoid(output).view(-1).data.cpu().numpy()
    target = target.view(-1).data.cpu().numpy()
    output_ = output > 0.5
    target_ = target > 0.5
    intersection = (output_ * target_).sum()

    return (2. * intersection + smooth) / \
        (output_.sum() + target_.sum() + smooth)


def metrics_all(pred, true):
    output = torch.sigmoid(pred).view(-1).data.cpu().numpy()
    target = true.view(-1).data.cpu().numpy()
    output_ = output > 0.5
    target_ = target > 0.5
    tp = output_ & target_
    fn = ((output_ == 0) & (target_ == 1)).astype('int')
    fp = ((output_ == 1) & (target_ == 0)).astype('int')

    precision = np.sum(tp) / (np.sum(tp) + np.sum(fp))
    recall = np.sum(tp) / (np.sum(tp) + np.sum(fn))

    f1 = 2 * precision * recall / (precision + recall)
    iou = np.sum(tp) / (np.sum(tp) + np.sum(fp) + np.sum(fn))
    dice = 2*np.sum(tp) / (2*np.sum(tp) + np.sum(fp) + np.sum(fn))

    return float(precision), float(recall), float(f1), float(iou), float(dice)