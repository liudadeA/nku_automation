import cv2
import numpy as np
import os
from pathlib import Path
import glob
from typing import List, Tuple, Dict, Any
import matplotlib.pyplot as plt
from skimage.transform import ProjectiveTransform, warp
import warnings
warnings.filterwarnings('ignore')

def fenge(image_path: str, output_dir: str = "picture/my", step: int = 1000, overlap: int = 200) -> None:
    """
    分割图像为重叠的块
    
    Args:
        image_path: 输入图像路径
        output_dir: 输出目录
        step: 分块步长
        overlap: 重叠区域宽度
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    h, w = img.shape[:2]
    
    # 计算总分块数
    num_blocks = int(np.ceil((w - overlap) / (step - overlap)))
    
    # 分块切割
    for i in range(num_blocks):
        # 计算当前块的列范围
        x_start = max(0, i * (step - overlap))
        x_end = min(w, x_start + step)
        
        block = img[:, x_start:x_end, :]
        
        # 保存块
        output_path = os.path.join(output_dir, f"my_{i+1}.jpg")
        cv2.imwrite(output_path, block)
        
        print(f"已保存分块 {i+1}: {x_start}-{x_end}")

def myfun(files: List[str], n: int) -> None:
    """
    自动排序并拼接图像，重叠区域线性融合，重叠部分只显示序号小的图片内容，输出文件名为mt_1到mt_N，RGB通道顺序修正
    Args:
        files: 图像文件路径列表
        n: 标识号（未用）
    """
    N = len(files)
    if N == 0:
        print("没有找到图像文件")
        return

    # 读取所有图片
    images = []
    grays = []
    for file_path in files:
        img = cv2.imread(file_path)
        if img is None:
            print(f"无法读取图像: {file_path}")
            continue
        images.append(img)
        grays.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    N = len(images)
    if N < 2:
        print("至少需要2张图像进行拼接")
        return

    # 计算两两图片的匹配分数和单应性
    sift = cv2.SIFT_create()
    matcher = cv2.BFMatcher()
    scores = np.zeros((N, N))
    homos = [[None]*N for _ in range(N)]
    for i in range(N):
        kp1, des1 = sift.detectAndCompute(grays[i], None)
        for j in range(N):
            if i == j:
                continue
            kp2, des2 = sift.detectAndCompute(grays[j], None)
            if des1 is None or des2 is None:
                continue
            matches = matcher.knnMatch(des1, des2, k=2)
            good = [m for m, n in matches if m.distance < 0.7 * n.distance]
            scores[i, j] = len(good)
            if len(good) >= 4:
                pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
                pts2 = np.float32([kp2[m.trainIdx].pt for m in good])
                H, mask = cv2.findHomography(pts2, pts1, cv2.RANSAC, 5.0)
                homos[i][j] = H

    # 自动推断顺序：贪心法，从匹配数最多的图片开始
    used = [False]*N
    order = []
    cur = np.argmax(np.sum(scores, axis=1))
    order.append(cur)
    used[cur] = True
    for _ in range(N-1):
        next_idx = -1
        max_score = -1
        for j in range(N):
            if not used[j] and scores[cur, j] > max_score:
                max_score = scores[cur, j]
                next_idx = j
        if next_idx == -1:
            break
        order.append(next_idx)
        used[next_idx] = True
        cur = next_idx

    # 右到左重命名，order反转
    order = order[::-1]
    imgs_sorted = [images[i] for i in order]
    grays_sorted = [grays[i] for i in order]
    N = len(imgs_sorted)

    # 计算每一对的单应性
    transforms = [np.eye(3)]
    for k in range(1, N):
        H = homos[order[k-1]][order[k]]
        if H is None:
            H = np.eye(3)
        transforms.append(H)

    # 累乘单应性到第一个图像坐标系
    for k in range(1, N):
        transforms[k] = transforms[k-1] @ transforms[k]

    # 计算所有图像变换后四角坐标，确定画布大小
    corners = []
    for k in range(N):
        h, w = imgs_sorted[k].shape[:2]
        pts = np.array([[0,0],[w,0],[w,h],[0,h]], dtype=np.float32).reshape(-1,1,2)
        pts_trans = cv2.perspectiveTransform(pts, transforms[k])
        corners.append(pts_trans)
    all_pts = np.concatenate(corners, axis=0)
    x_min, y_min = np.floor(all_pts.min(axis=0)[0]).astype(int)
    x_max, y_max = np.ceil(all_pts.max(axis=0)[0]).astype(int)
    out_w = x_max - x_min
    out_h = y_max - y_min

    # 平移矩阵，使所有坐标为正
    offset = np.array([[1,0,-x_min],[0,1,-y_min],[0,0,1]])

    # 创建画布和权重
    result = np.zeros((out_h, out_w, 3), dtype=np.float32)
    mask_total = np.zeros((out_h, out_w), dtype=bool)

    # 依次融合每张图像，重叠部分只保留序号小的图片内容（数字小的覆盖大的），无模糊融合，直接覆盖
    for k in range(N-1, -1, -1):  # 倒序遍历，数字小的后覆盖大的
        img = imgs_sorted[k].astype(np.float32)/255.0
        h, w = img.shape[:2]
        trans = offset @ transforms[k]
        warped = cv2.warpPerspective(img, trans, (out_w, out_h))
        mask = (cv2.warpPerspective(np.ones((h,w), np.float32), trans, (out_w, out_h)) > 0)
        only_new = mask & (~mask_total)
        # 直接覆盖未被覆盖区域
        for c in range(3):
            result[...,c][only_new] = warped[...,c][only_new]
        # 直接覆盖重叠区域（数字小的覆盖大的）
        for c in range(3):
            result[...,c][mask & mask_total] = warped[...,c][mask & mask_total]
        mask_total |= mask
        # 保存每一步的单独结果
        outimg = (np.clip(result,0,1)*255).astype(np.uint8)
        cv2.imwrite(f"mt_{N-k}.jpg", outimg)

    # 显示最终全景
    plt.figure(figsize=(15,8))
    plt.imshow(cv2.cvtColor((np.clip(result,0,1)*255).astype(np.uint8), cv2.COLOR_BGR2RGB))
    plt.title(f'全景图')
    plt.axis('off')
    plt.show()
    print(f"全景图及每步结果已保存为: mt_1.jpg ~ mt_{N}.jpg")

def main():
    """主函数"""

    # 获取图像文件
    my_files = sorted(glob.glob("picture/M2/*.jpg"))
    
    # 拼接图像
    if my_files:
        print("处理my文件夹...")
        myfun(my_files, 3)

if __name__ == "__main__":
    main()