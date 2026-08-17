import os
import numpy as np
import cv2

# 创建新的数据集目录结构
train_dir = './data/MOCK/train'
dirs = ['image', 'mask', 'depth']
for dir_name in dirs:
    os.makedirs(os.path.join(train_dir, dir_name), exist_ok=True)

# 生成模拟RGB、mask和depth文件
num_samples = 10
for i in range(1, num_samples + 1):
    # 生成模拟RGB图像 (3通道)
    rgb = np.random.randint(0, 256, (416, 416, 3), dtype=np.uint8)
    cv2.imwrite(os.path.join(train_dir, 'image', f'mock_{i:05d}.jpg'), rgb)
    
    # 生成模拟mask (单通道)
    mask = np.random.randint(0, 2, (416, 416), dtype=np.uint8) * 255
    cv2.imwrite(os.path.join(train_dir, 'mask', f'mock_{i:05d}.png'), mask)
    
    # 生成模拟depth图 (单通道)
    depth = np.random.randint(0, 256, (416, 416), dtype=np.uint8)
    cv2.imwrite(os.path.join(train_dir, 'depth', f'mock_{i:05d}.png'), depth)

print(f"已在 {train_dir} 生成 {num_samples} 个模拟样本")
