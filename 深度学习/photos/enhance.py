from ultralytics import YOLO
import os
import shutil
from pathlib import Path
import numpy as np
import random

# ===================== 核心配置（新增分割比例！）=====================
# 训练好的YOLOv8模型路径
model_path = r"C:\Users\Administrator\Desktop\shendu\photos\yolov8_train_results\yolov8_train\weights\best.pt"
# 已分类完成的根目录（包含单类别文件夹 + no/more）
classified_root_dir = r"C:\Users\Administrator\Desktop\shendu\photos\classified_results"
# 输出的YOLO数据集根目录（自动创建train/val目录）
dataset_root_dir = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset"
# 训练集/验证集分割比例（train=80%，val=20%）
train_ratio = 0.8
# 随机种子（保证分割结果可复现）
random_seed = 42
# 置信度阈值（过滤低置信度检测框）
conf_threshold = 0.6
# 显卡设备（0=RTX4060，-1=CPU）
device = 0
# 图片尺寸（和训练时一致）
imgsz = 640

# ===================== 工具函数 =====================
def create_dir(dir_path):
    """创建文件夹（不存在则创建）"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"📁 创建文件夹：{dir_path}")

def convert_box_to_yolo(box, img_w, img_h):
    """将YOLO预测的xyxy框转换为YOLO标注格式"""
    x1, y1, x2, y2 = box
    x_center = (x1 + x2) / 2.0
    y_center = (y1 + y2) / 2.0
    width = x2 - x1
    height = y2 - y1
    # 归一化
    x_center /= img_w
    y_center /= img_h
    width /= img_w
    height /= img_h
    # 保留6位小数（符合YOLO标准）
    return round(x_center, 6), round(y_center, 6), round(width, 6), round(height, 6)

def generate_yolo_label(model, img_path):
    """生成单张图片的YOLO标签（返回标签行列表，无则返回空）"""
    try:
        results = model.predict(
            source=img_path,
            conf=conf_threshold,
            save=False,
            show=False,
            verbose=False,
            device=device,
            imgsz=imgsz
        )
        yolo_label_lines = []
        for r in results:
            img_h, img_w = r.orig_shape
            if r.boxes is None or len(r.boxes) == 0:
                continue
            valid_boxes = r.boxes[r.boxes.conf >= conf_threshold]
            for box in valid_boxes:
                cls_id = int(box.cls.cpu().numpy())
                xyxy = box.xyxy.cpu().numpy()[0]
                x_center, y_center, w, h = convert_box_to_yolo(xyxy, img_w, img_h)
                yolo_label_lines.append(f"{cls_id} {x_center} {y_center} {w} {h}")
        return yolo_label_lines
    except Exception as e:
        print(f"   ❌ 生成标签失败 {Path(img_path).name} → {str(e)}")
        return []

def copy_img_and_label(img_path, label_lines, target_img_dir, target_label_dir):
    """复制图片+保存标签到指定目录（遇到同名直接跳过）"""
    img_name = Path(img_path).name
    img_stem = Path(img_path).stem
    img_ext = Path(img_path).suffix

    # 1. 复制图片（同名直接跳过）
    dest_img_path = os.path.join(target_img_dir, img_name)
    if os.path.exists(dest_img_path):
        # print(f"图片已存在，跳过: {dest_img_path}")
        return False
    shutil.copy2(img_path, dest_img_path)

    # 2. 保存标签（同名直接跳过）
    dest_label_path = os.path.join(target_label_dir, f"{img_stem}.txt")
    if os.path.exists(dest_label_path):
        # print(f"标签已存在，跳过: {dest_label_path}")
        return False
    with open(dest_label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(label_lines))

    return True

# ===================== 主函数：收集图片→分割→生成标签+复制 =====================
def main():
    # 1. 固定随机种子（保证分割结果可复现）
    random.seed(random_seed)
    np.random.seed(random_seed)

    # 2. 加载YOLO模型
    print("🔍 加载YOLOv8模型...")
    try:
        model = YOLO(model_path)
        print(f"✅ 模型加载成功：{model_path}")
    except Exception as e:
        print(f"❌ 模型加载失败 → {str(e)}")
        return

    # 3. 初始化数据集目录（YOLO标准结构）
    # 训练集目录
    train_img_dir = os.path.join(dataset_root_dir, "images", "train")
    train_label_dir = os.path.join(dataset_root_dir, "labels", "train")
    # 验证集目录
    val_img_dir = os.path.join(dataset_root_dir, "images", "val")
    val_label_dir = os.path.join(dataset_root_dir, "labels", "val")
    # 创建所有目录
    create_dir(train_img_dir)
    create_dir(train_label_dir)
    create_dir(val_img_dir)
    create_dir(val_label_dir)

    # 4. 定义支持的图片格式
    img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.webp']

    # 5. 第一步：收集所有有效图片（有检测框、非no/more）
    print(f"\n📌 收集已分类目录中的有效图片...")
    valid_img_list = []  # 存储所有有检测框的图片路径
    total_scanned = 0    # 总扫描图片数
    total_invalid = 0    # 无效图片数（无检测框/处理失败）

    for folder_name in os.listdir(classified_root_dir):
        folder_path = os.path.join(classified_root_dir, folder_name)
        # 跳过no/more和非文件夹
        if not os.path.isdir(folder_path) or folder_name in ["no", "more"]:
            continue

        print(f"\n📂 扫描类别文件夹：{folder_name}")
        for file_name in os.listdir(folder_path):
            file_ext = Path(file_name).suffix.lower()
            if file_ext not in img_extensions:
                continue
            total_scanned += 1
            img_full_path = os.path.join(folder_path, file_name)

            # 生成标签，判断是否有效
            label_lines = generate_yolo_label(model, img_full_path)
            if len(label_lines) == 0:
                print(f"   ⚠️ {file_name}：无有效检测框，跳过")
                total_invalid += 1
                continue

            # 有效图片：保存路径+标签
            valid_img_list.append({
                "img_path": img_full_path,
                "label_lines": label_lines
            })
            print(f"   ✅ {file_name}：有效图片，加入列表")

    # 6. 第二步：按比例分割训练集/验证集
    print(f"\n📌 按 {train_ratio}:{1-train_ratio} 分割训练集/验证集...")
    total_valid = len(valid_img_list)
    if total_valid == 0:
        print("❌ 无有效图片可分割，程序退出")
        return

    # 随机打乱列表
    random.shuffle(valid_img_list)
    # 计算分割点
    split_idx = int(total_valid * train_ratio)
    # 分割
    train_list = valid_img_list[:split_idx]
    val_list = valid_img_list[split_idx:]

    print(f"   ├─ 总有效图片数：{total_valid}")
    print(f"   ├─ 训练集数量：{len(train_list)}")
    print(f"   └─ 验证集数量：{len(val_list)}")

    # 7. 第三步：复制训练集图片+生成标签
    print(f"\n📌 处理训练集...")
    train_processed = 0
    for item in train_list:
        success = copy_img_and_label(
            img_path=item["img_path"],
            label_lines=item["label_lines"],
            target_img_dir=train_img_dir,
            target_label_dir=train_label_dir
        )
        if success:
            train_processed += 1
    print(f"   ✅ 训练集处理完成：{train_processed}张")

    # 8. 第四步：复制验证集图片+生成标签
    print(f"\n📌 处理验证集...")
    val_processed = 0
    for item in val_list:
        success = copy_img_and_label(
            img_path=item["img_path"],
            label_lines=item["label_lines"],
            target_img_dir=val_img_dir,
            target_label_dir=val_label_dir
        )
        if success:
            val_processed += 1
    print(f"   ✅ 验证集处理完成：{val_processed}张")

    # 9. 输出最终统计
    print("\n🎉 所有操作完成！")
    print(f"📊 最终统计：")
    print(f"   ├─ 总扫描图片数：{total_scanned}")
    print(f"   ├─ 无效图片数：{total_invalid}")
    print(f"   ├─ 训练集：{train_processed}张（图片+标签）")
    print(f"   ├─ 验证集：{val_processed}张（图片+标签）")
    print(f"   ├─ 训练集图片路径：{train_img_dir}")
    print(f"   ├─ 训练集标签路径：{train_label_dir}")
    print(f"   ├─ 验证集图片路径：{val_img_dir}")
    print(f"   └─ 验证集标签路径：{val_label_dir}")

if __name__ == "__main__":
    main()