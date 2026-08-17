import json
import os
import shutil
import random
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# 设置随机种子（保证划分结果可复现）
random.seed(42)

def convert_json_to_yolo(
    json_path: str,
    class_id: int,
    img_width: int = None,
    img_height: int = None
) -> List[str]:
    """
    单个JSON标注转换为YOLO TXT行（返回YOLO格式行列表）
    :param json_path: JSON标注路径
    :param class_id: 该标注对应的类别ID（从0开始）
    :param img_width/img_height: 图片宽高（若JSON中无则手动传入）
    :return: YOLO格式行列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 读取{json_path}失败：{e}")
        return []
    
    # 优先从JSON取图片宽高，无则用传入值
    json_width = data.get('imageWidth', img_width)
    json_height = data.get('imageHeight', img_height)
    if not json_width or not json_height:
        print(f"⚠️ {json_path} 缺少图片宽高信息，跳过")
        return []
    
    yolo_lines = []
    for shape in data.get('shapes', []):
        if shape['shape_type'] != 'rectangle':
            print(f"⚠️ {json_path} 包含非矩形框标注，跳过该形状")
            continue
        
        # 提取矩形框坐标并计算YOLO参数
        points = shape['points']
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        x1, x2 = min(x_coords), max(x_coords)
        y1, y2 = min(y_coords), max(y_coords)
        
        # 归一化（保留6位小数）
        x_center = round((x1 + x2) / 2 / json_width, 6)
        y_center = round((y1 + y2) / 2 / json_height, 6)
        width = round((x2 - x1) / json_width, 6)
        height = round((y2 - y1) / json_height, 6)
        
        # 过滤异常坐标（避免训练报错）
        if x_center < 0 or y_center < 0 or width <= 0 or height <= 0:
            print(f"⚠️ {json_path} 标注坐标异常，跳过该框")
            continue
        
        yolo_lines.append(f"{class_id} {x_center} {y_center} {width} {height}")
    
    return yolo_lines

def get_image_label_pairs(root_dir: str) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    遍历目录，获取：
    1. 类别名→图片路径列表的映射
    2. 所有类别名列表（按文件夹名）
    """
    class_image_map = {}
    class_names = []
    
    # 遍历每个类别文件夹
    for class_dir in os.listdir(root_dir):
        class_path = os.path.join(root_dir, class_dir)
        if not os.path.isdir(class_path):
            continue
        
        # 记录类别名
        class_names.append(class_dir)
        class_image_map[class_dir] = []
        
        # 收集该类别下的所有图片（匹配对应JSON）
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif']
        for file in os.listdir(class_path):
            file_ext = Path(file).suffix.lower()
            if file_ext in img_extensions:
                img_path = os.path.join(class_path, file)
                json_path = os.path.splitext(img_path)[0] + '.json'
                if os.path.exists(json_path):  # 只处理有标注的图片
                    class_image_map[class_dir].append(img_path)
    
    # 类别名按字母排序（保证ID固定）
    class_names.sort()
    return class_image_map, class_names

def split_train_val(image_list: List[str], val_ratio: float = 0.2) -> Tuple[List[str], List[str]]:
    """划分训练/验证集"""
    random.shuffle(image_list)
    val_size = int(len(image_list) * val_ratio)
    val_list = image_list[:val_size]
    train_list = image_list[val_size:]
    return train_list, val_list

def copy_files_and_convert(
    image_list: List[str],
    class_id: int,
    target_img_dir: str,
    target_label_dir: str
) -> None:
    """
    复制图片到目标目录，并转换对应JSON为YOLO TXT
    """
    os.makedirs(target_img_dir, exist_ok=True)
    os.makedirs(target_label_dir, exist_ok=True)
    
    for img_path in image_list:
        # 1. 复制图片到目标目录
        img_name = Path(img_path).name
        dest_img_path = os.path.join(target_img_dir, img_name)
        shutil.copy2(img_path, dest_img_path)
        
        # 2. 转换JSON为YOLO TXT
        json_path = os.path.splitext(img_path)[0] + '.json'
        txt_name = Path(img_name).stem + '.txt'
        dest_txt_path = os.path.join(target_label_dir, txt_name)
        
        yolo_lines = convert_json_to_yolo(json_path, class_id)
        if yolo_lines:
            with open(dest_txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(yolo_lines))
            print(f"✅ 处理完成：{img_name} → {dest_img_path} + {dest_txt_path}")
        else:
            print(f"⚠️ {img_name} 无有效标注，仅复制图片")

def generate_data_yaml(
    output_dir: str,
    class_names: List[str],
    train_img_path: str,
    val_img_path: str
) -> None:
    """生成YOLO训练用的data.yaml文件"""
    yaml_content = f"""# YOLO数据集配置文件
train: {os.path.abspath(train_img_path)}  # 训练集图片路径
val: {os.path.abspath(val_img_path)}      # 验证集图片路径
nc: {len(class_names)}                    # 类别总数
names: {class_names}                      # 类别名（与ID一一对应）
"""
    yaml_path = os.path.join(output_dir, 'data.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    print(f"✅ 生成配置文件：{yaml_path}")

def main(args):
    # 1. 初始化路径
    input_root = args.input_dir
    output_root = args.output_dir
    val_ratio = args.val_ratio
    
    # 2. 遍历获取类别和图片映射
    print("🔍 开始遍历数据集...")
    class_image_map, class_names = get_image_label_pairs(input_root)
    if not class_names:
        print("❌ 未找到任何类别文件夹！")
        return
    print(f"✅ 找到{len(class_names)}个类别：{class_names}")
    
    # 3. 生成类别ID映射（按排序后的类别名分配ID）
    class_id_map = {name: idx for idx, name in enumerate(class_names)}
    
    # 4. 划分并处理每个类别的数据
    for class_name, image_list in class_image_map.items():
        if not image_list:
            print(f"⚠️ 类别{class_name}无有效图片，跳过")
            continue
        
        class_id = class_id_map[class_name]
        print(f"\n📌 处理类别：{class_name} (ID={class_id})，共{len(image_list)}张图片")
        
        # 划分训练/验证集
        train_list, val_list = split_train_val(image_list, val_ratio)
        print(f"  ├─ 训练集：{len(train_list)}张")
        print(f"  └─ 验证集：{len(val_list)}张")
        
        # 处理训练集
        train_img_dir = os.path.join(output_root, 'images', 'train')
        train_label_dir = os.path.join(output_root, 'labels', 'train')
        copy_files_and_convert(train_list, class_id, train_img_dir, train_label_dir)
        
        # 处理验证集
        val_img_dir = os.path.join(output_root, 'images', 'val')
        val_label_dir = os.path.join(output_root, 'labels', 'val')
        copy_files_and_convert(val_list, class_id, val_img_dir, val_label_dir)
    
    # 5. 生成data.yaml
    generate_data_yaml(
        output_root,
        class_names,
        train_img_dir,
        val_img_dir
    )
    
    print(f"\n🎉 全部处理完成！输出目录：{os.path.abspath(output_root)}")
    print(f"📋 数据集统计：")
    print(f"  ├─ 训练集图片：{len(os.listdir(train_img_dir))}张")
    print(f"  ├─ 训练集标注：{len(os.listdir(train_label_dir))}个")
    print(f"  ├─ 验证集图片：{len(os.listdir(val_img_dir))}张")
    print(f"  └─ 验证集标注：{len(os.listdir(val_label_dir))}个")

if __name__ == "__main__":
    # 手动配置参数（无需终端传参，直接运行）
    class Args:
        # ********** 核心修改：替换为你的existing_faces文件夹路径 **********
        input_dir = r"C:\Users\Administrator\Desktop\shendu\photos\labelme_dataset"  
        # 输出目录（生成的YOLO数据集会放在这里）
        output_dir = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset"  
        # 验证集比例（8:2划分）
        val_ratio = 0.2  
    
    args = Args()
    main(args)