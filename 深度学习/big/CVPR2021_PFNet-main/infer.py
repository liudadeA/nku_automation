"""
 @Time    : 2021/7/6 14:36
 @Author  : Haiyang Mei
 @E-mail  : mhy666@mail.dlut.edu.cn
 
 @Project : CVPR2021_PFNet
 @File    : infer.py
 @Function: Inference
 
"""
import time
import datetime

import torch
from PIL import Image
from torch.autograd import Variable
from torchvision import transforms
from collections import OrderedDict
from numpy import mean

from config import *
from misc import *
from PFNet import PFNet

torch.manual_seed(2021)
# Check if CUDA is available
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

results_path = './results'
check_mkdir(results_path)
exp_name = 'PFNet'
args = {
    'scale': 416,
    'save_results': True
}

print(torch.__version__)

# RGB-D input transformation (4 channels)
img_transform = transforms.Compose([
    transforms.Resize((args['scale'], args['scale'])),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406, 0.5], [0.229, 0.224, 0.225, 0.5])
])

to_pil = transforms.ToPILImage()

# Define test datasets
# data/NEW/test contains RGB-only test sets (CAMO, CHAMELEON, COD10K)
to_test = OrderedDict([
                       ('MOCK_TRAIN', os.path.join(datasets_root, 'train')),
                       ('CAMO_TEST', os.path.join(original_datasets_root, 'NEW', 'test', 'CAMO')),
                       ('CHAMELEON_TEST', os.path.join(original_datasets_root, 'NEW', 'test', 'CHAMELEON')),
                       ('COD10K_TEST', os.path.join(original_datasets_root, 'NEW', 'test', 'COD10K'))
                       ])

results = OrderedDict()

def main():
    net = PFNet(backbone_path).to(device)

    # Load our trained model (4-channel RGB-D)
    model_path = './ckpt/PFNet/45.pth'
    net.load_state_dict(torch.load(model_path))
    print(f'Load {model_path} succeed!')

    net.eval()
    with torch.no_grad():
        start = time.time()
        for name, root in to_test.items():
            time_list = []
            image_path = os.path.join(root, 'image')
            depth_path = os.path.join(root, 'depth')

            if args['save_results']:
                check_mkdir(os.path.join(results_path, exp_name, name))

            # Check if depth directory exists
            has_depth = os.path.exists(depth_path)
            
            # Get image list
            img_list = []
            for f in os.listdir(image_path):
                if f.endswith(('jpg', 'png')):
                    img_list.append(os.path.splitext(f)[0])
            
            for idx, img_name in enumerate(img_list):
                # Load RGB image
                rgb_ext = '.jpg' if os.path.exists(os.path.join(image_path, img_name + '.jpg')) else '.png'
                rgb_img = Image.open(os.path.join(image_path, img_name + rgb_ext)).convert('RGB')

                w, h = rgb_img.size
                
                # Apply same transformation to both RGB and depth
                rgb_tensor = img_transform.transforms[0](rgb_img)  # Resize
                rgb_tensor = img_transform.transforms[1](rgb_tensor)  # ToTensor
                
                if has_depth:
                    # Use depth information if available
                    depth_file = os.path.join(depth_path, img_name + '.png')
                    if os.path.exists(depth_file):
                        depth_img = Image.open(depth_file).convert('L')
                        depth_tensor = img_transform.transforms[0](depth_img)  # Resize
                        depth_tensor = img_transform.transforms[1](depth_tensor)  # ToTensor
                    else:
                        # Create default depth channel if depth file doesn't exist
                        depth_tensor = torch.zeros_like(rgb_tensor[0:1])  # 1-channel default depth
                else:
                    # Create default depth channel for RGB-only datasets
                    depth_tensor = torch.zeros_like(rgb_tensor[0:1])  # 1-channel default depth
                
                # Concatenate RGB (3 channels) and depth (1 channel) to get 4-channel input
                img_tensor = torch.cat([rgb_tensor, depth_tensor], dim=0)
                
                # Apply normalization to the combined tensor
                img_tensor = img_transform.transforms[2](img_tensor)
                
                img_var = Variable(img_tensor.unsqueeze(0)).to(device)

                start_each = time.time()
                # Our model returns (predict_1, predict_2, predict_3, predict_4, edge_output)
                # We'll use predict_4 as the final output (highest resolution)
                _, _, _, prediction, _ = net(img_var)
                time_each = time.time() - start_each
                time_list.append(time_each)

                prediction = np.array(transforms.Resize((h, w))(to_pil(prediction.data.squeeze(0).cpu())))

                if args['save_results']:
                    Image.fromarray(prediction).convert('L').save(os.path.join(results_path, exp_name, name, img_name + '_saliency.png'))
                    print(f"Processed {img_name}, saved to results")
            print(('{}'.format(exp_name)))
            print("{}'s average Time Is : {:.3f} s".format(name, mean(time_list)))
            print("{}'s average Time Is : {:.1f} fps".format(name, 1 / mean(time_list)))

    end = time.time()
    print("Total Testing Time: {}".format(str(datetime.timedelta(seconds=int(end - start)))))

if __name__ == '__main__':
    main()
