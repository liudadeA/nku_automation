import os
import numpy as np
from PIL import Image
import torchvision.transforms as transforms

# Create directory structure
train_dir = './data/NEW/train'
dirs = ['image', 'mask', 'depth']
for dir_name in dirs:
    os.makedirs(os.path.join(train_dir, dir_name), exist_ok=True)

# Generate mock data
num_samples = 10
img_size = 416

for i in range(1, num_samples + 1):
    # Create random RGB image
    img = np.random.randint(0, 255, (img_size, img_size, 3), dtype=np.uint8)
    img = Image.fromarray(img)
    img.save(os.path.join(train_dir, 'image', f'mock_{i:05d}.jpg'))
    
    # Create random mask (binary)
    mask = np.random.randint(0, 2, (img_size, img_size, 1), dtype=np.uint8) * 255
    mask = Image.fromarray(mask.squeeze(), mode='L')
    mask.save(os.path.join(train_dir, 'mask', f'mock_{i:05d}.png'))
    
    # Create random depth map (grayscale)
    depth = np.random.randint(0, 255, (img_size, img_size, 1), dtype=np.uint8)
    depth = Image.fromarray(depth.squeeze(), mode='L')
    depth.save(os.path.join(train_dir, 'depth', f'mock_{i:05d}.png'))

print(f"Created {num_samples} mock samples in {train_dir}")
