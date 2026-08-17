"""
 @Time    : 2021/7/6 10:56
 @Author  : Haiyang Mei
 @E-mail  : mhy666@mail.dlut.edu.cn
 
 @Project : CVPR2021_PFNet
 @File    : datasets.py
 @Function: Datasets Processing
 
"""
import os
import os.path
import torch
import torch.utils.data as data
from PIL import Image
from torchvision import transforms
import joint_transforms

def make_dataset(root):
    image_path = os.path.join(root, 'image')
    mask_path = os.path.join(root, 'mask')
    depth_path = os.path.join(root, 'depth')
    img_list = [os.path.splitext(f)[0] for f in os.listdir(image_path) if f.endswith('.jpg')]
    return [(os.path.join(image_path, img_name + '.jpg'), 
             os.path.join(mask_path, img_name + '.png'),
             os.path.join(depth_path, img_name + '.png')) for img_name in img_list]

class ImageFolder(data.Dataset):
    # image and gt should be in the same folder and have same filename except extended name (jpg and png respectively)
    def __init__(self, root, joint_transform=None, transform=None, target_transform=None):
        self.root = root
        self.imgs = make_dataset(root)
        self.joint_transform = joint_transform
        self.transform = transform
        self.target_transform = target_transform

    def __getitem__(self, index):
        img_path, gt_path, depth_path = self.imgs[index]
        img = Image.open(img_path).convert('RGB')
        depth = Image.open(depth_path).convert('L')
        target = Image.open(gt_path).convert('L')
        
        # Apply joint transform to all three images
        if self.joint_transform is not None:
            # Apply joint transform to RGB and target first
            img, target = self.joint_transform(img, target)
            # Then apply the same transform to depth individually
            for transform in self.joint_transform.transforms:
                if isinstance(transform, joint_transforms.Resize):
                    # Apply resize to depth
                    depth, _ = transform(depth, depth)  # Use depth as both img and mask for resize
                elif isinstance(transform, joint_transforms.RandomHorizontallyFlip):
                    # Apply flip to depth if needed
                    depth, _ = transform(depth, depth)  # Use depth as both img and mask for flip
        
        # Convert to tensors first
        if self.transform is not None:
            # Convert both to tensors first without normalization
            to_tensor = transforms.ToTensor()
            img = to_tensor(img)
            depth = to_tensor(depth)
            
            # Merge RGB and depth channels
            img = torch.cat([img, depth], dim=0)  # Now shape is (4, H, W)
            
            # Then apply normalization to the 4-channel image
            normalize = transforms.Normalize([0.485, 0.456, 0.406, 0.5], [0.229, 0.224, 0.225, 0.5])
            img = normalize(img)
        
        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def __len__(self):
        return len(self.imgs)
