import datetime
import time
import os

import torch
from torch import nn
from torch import optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

import joint_transforms
from config import cod_training_root
from config import backbone_path
from datasets import ImageFolder
from misc import AvgMeter, check_mkdir
from PFNet import PFNet

import loss

# Simplified training parameters
args = {
    'epoch_num': 1,  # Only 1 epoch for testing
    'train_batch_size': 2,
    'last_epoch': 0,
    'lr': 1e-3,
    'lr_decay': 0.9,
    'weight_decay': 5e-4,
    'momentum': 0.9,
    'snapshot': '',
    'scale': 128,  # Smaller image size for faster testing
    'save_point': [],
    'poly_train': True,
    'optimizer': 'SGD',
}

# Transform Data.
joint_transform = joint_transforms.Compose([
    joint_transforms.Resize((args['scale'], args['scale']))
])
img_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406, 0.5], [0.229, 0.224, 0.225, 0.5])
])
target_transform = transforms.ToTensor()

# Prepare Data Set.
train_set = ImageFolder(cod_training_root, joint_transform, img_transform, target_transform)
print(f"Train set: {train_set.__len__()} samples")
train_loader = DataLoader(train_set, batch_size=args['train_batch_size'], num_workers=0, shuffle=True)

# loss function
structure_loss = loss.structure_loss()
bce_loss = nn.BCEWithLogitsLoss()
iou_loss = loss.IOU()

def bce_iou_loss(pred, target):
    bce_out = bce_loss(pred, target)
    iou_out = iou_loss(pred, target)
    loss = bce_out + iou_out
    return loss

def edge_loss(pred, target):
    return bce_loss(pred, target)

def main():
    print("Starting simplified training test...")
    
    # Initialize model
    net = PFNet(backbone_path=backbone_path).train()
    
    # Initialize optimizer
    optimizer = optim.SGD([
        {'params': [param for name, param in net.named_parameters() if name[-4:] == 'bias'],
         'lr': 2 * args['lr']},
        {'params': [param for name, param in net.named_parameters() if name[-4:] != 'bias'],
         'lr': 1 * args['lr'], 'weight_decay': args['weight_decay']}
    ], momentum=args['momentum'])
    
    # Training loop with tqdm progress bar
    for epoch in range(args['last_epoch'] + 1, args['last_epoch'] + 1 + args['epoch_num']):
        loss_record = AvgMeter()
        
        # Create tqdm progress bar
        train_iterator = tqdm(train_loader, total=len(train_loader), leave=True, dynamic_ncols=True, desc=f"Epoch {epoch}")
        
        for data in train_iterator:
            inputs, labels = data
            batch_size = inputs.size(0)
            
            optimizer.zero_grad()
            
            # Forward pass
            predict_4, predict_3, predict_2, predict_1, edge_output = net(inputs)
            
            # Calculate losses
            loss_1 = bce_iou_loss(predict_1, labels)
            loss_2 = structure_loss(predict_2, labels)
            loss_3 = structure_loss(predict_3, labels)
            loss_4 = structure_loss(predict_4, labels)
            loss_edge = edge_loss(edge_output, labels)
            
            # Weighted loss combination
            loss = 1 * loss_1 + 1 * loss_2 + 2 * loss_3 + 4 * loss_4 + 0.1 * loss_edge
            
            # Backward pass and optimization
            loss.backward()
            optimizer.step()
            
            # Update loss records
            loss_record.update(loss.data, batch_size)
            
            # Update progress bar with current loss
            train_iterator.set_postfix(loss=loss_record.avg.item(), batch_loss=loss.item())
        
        print(f"Epoch {epoch} completed. Average loss: {loss_record.avg:.4f}")
    
    print("\nSimplified training test completed successfully!")

if __name__ == '__main__':
    main()
