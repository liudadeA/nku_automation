import json
import os
import shutil
import random
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from PIL import Image
import warnings
import yaml  # 新增：解析data.yaml

# 忽略PIL图片读取警告
warnings.filterwarnings('ignore')

# 设置随机种子（保证划分结果可复现）
random.seed(42)

# ====================== 正向转换：LabelMe → YOLO ======================
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

# ====================== 反向转换核心函数（新增+修改）=====================
def load_class_names_from_yaml(yolo_root: str) -> List[str]:
    """
    从YOLO数据集的data.yaml中自动读取类别名
    :param yolo_root: YOLO数据集根目录（包含data.yaml）
    :return: 类别名列表
    """
    yaml_path = os.path.join(yolo_root, "data.yaml")
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"❌ 未找到data.yaml文件：{yaml_path}\n请确认YOLO数据集根目录正确，且正向转换已生成该文件")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"❌ 解析data.yaml失败：{e}")
    
    class_names = yaml_data.get("names", [])
    if not class_names:
        raise ValueError(f"❌ data.yaml中未找到names字段，请检查文件格式")
    
    print(f"✅ 从data.yaml自动加载类别名：{class_names}")
    return class_names

def convert_yolo_to_json(
    yolo_txt_path: str,
    img_path: str,
    class_names: List[str]
) -> Dict:
    """
    将YOLO TXT标注转换为LabelMe JSON格式
    :param yolo_txt_path: YOLO标注文件路径
    :param img_path: 对应图片路径（用于获取宽高）
    :param class_names: 类别名列表（ID→名称映射，自动从data.yaml读取）
    :return: LabelMe格式的JSON字典
    """
    # 1. 读取图片宽高（关键：用于反算像素坐标）
    try:
        with Image.open(img_path) as img:
            img_width, img_height = img.size
    except Exception as e:
        print(f"❌ 读取图片{img_path}失败：{e}")
        return {}
    
    # 2. 读取YOLO标注行
    try:
        with open(yolo_txt_path, 'r', encoding='utf-8') as f:
            yolo_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ 读取YOLO标注{yolo_txt_path}失败：{e}")
        return {}
    
    # 3. 解析YOLO标注并转换为LabelMe shapes
    shapes = []
    for line in yolo_lines:
        parts = line.split()
        if len(parts) < 5:
            print(f"⚠️ {yolo_txt_path} 行格式错误：{line}，跳过")
            continue
        
        try:
            # 解析YOLO格式：class_id x_center y_center width height（归一化）
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
        except ValueError:
            print(f"⚠️ {yolo_txt_path} 数值解析失败：{line}，跳过")
            continue
        
        # 检查类别ID有效性
        if class_id < 0 or class_id >= len(class_names):
            print(f"⚠️ {yolo_txt_path} 无效类别ID {class_id}（总类别数：{len(class_names)}），跳过该行")
            continue
        
        # 归一化坐标 → 像素坐标（矩形框x1,y1,x2,y2）
        x1 = int((x_center - width / 2) * img_width)
        y1 = int((y_center - height / 2) * img_height)
        x2 = int((x_center + width / 2) * img_width)
        y2 = int((y_center + height / 2) * img_height)
        
        # 修正坐标边界（避免超出图片范围）
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_width - 1, x2)
        y2 = min(img_height - 1, y2)
        
        # 过滤无效框（宽/高为0）
        if x1 >= x2 or y1 >= y2:
            print(f"⚠️ {yolo_txt_path} 无效框坐标：({x1},{y1})→({x2},{y2})，跳过")
            continue
        
        # 构建LabelMe标准shape结构（使用data.yaml中的类别名）
        shapes.append({
            "label": class_names[class_id],
            "points": [[x1, y1], [x2, y2]],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        })
    
    # 4. 构建完整的LabelMe JSON结构
    labelme_json = {
        "version": "5.0.1",  # LabelMe主流版本
        "flags": {},
        "shapes": shapes,
        "imagePath": os.path.basename(img_path),  # 仅保留文件名（与LabelMe格式一致）
        "imageData": None,  # 不存储base64图片（节省空间，LabelMe可正常读取）
        "imageWidth": img_width,
        "imageHeight": img_height
    }
    
    return labelme_json

def batch_convert_yolo_to_labelme(
    yolo_root: str,
    output_root: str,
    subsets: List[str] = ["train", "val"]
) -> None:
    """
    批量将YOLO数据集转换为LabelMe格式（自动从data.yaml读取类别名）
    :param yolo_root: YOLO数据集根目录（包含images/labels/data.yaml）
    :param output_root: LabelMe格式输出根目录
    :param subsets: 要处理的子集（train/val/test）
    """
    # 自动从data.yaml加载类别名
    try:
        class_names = load_class_names_from_yaml(yolo_root)
    except (FileNotFoundError, ValueError) as e:
        print(e)
        return
    
    for subset in subsets:
        # 定义YOLO子集路径
        img_dir = os.path.join(yolo_root, "images", subset)
        label_dir = os.path.join(yolo_root, "labels", subset)
        # 定义输出子集路径
        output_subset_dir = os.path.join(output_root, subset)
        os.makedirs(output_subset_dir, exist_ok=True)
        
        if not os.path.exists(img_dir) or not os.path.exists(label_dir):
            print(f"⚠️ 子集{subset}路径不存在，跳过：{img_dir} / {label_dir}")
            continue
        
        # 遍历所有图片
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif']
        for img_file in os.listdir(img_dir):
            img_ext = Path(img_file).suffix.lower()
            if img_ext not in img_extensions:
                continue
            
            # 匹配图片和标注路径
            img_path = os.path.join(img_dir, img_file)
            txt_name = Path(img_file).stem + ".txt"
            txt_path = os.path.join(label_dir, txt_name)
            
            # 输出路径
            dest_img_path = os.path.join(output_subset_dir, img_file)
            json_name = Path(img_file).stem + ".json"
            json_path = os.path.join(output_subset_dir, json_name)
            
            # 1. 复制图片到输出目录
            shutil.copy2(img_path, dest_img_path)
            
            # 2. 转换YOLO标注为LabelMe JSON
            if os.path.exists(txt_path):
                labelme_data = convert_yolo_to_json(txt_path, img_path, class_names)
                if labelme_data and labelme_data["shapes"]:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(labelme_data, f, ensure_ascii=False, indent=2)
                    print(f"✅ 反向转换完成：{subset}/{img_file} → {json_path}")
                else:
                    print(f"⚠️ {subset}/{img_file} 无有效标注，仅复制图片")
            else:
                print(f"⚠️ {subset}/{img_file} 无YOLO标注文件，仅复制图片")
    
    print(f"\n🎉 反向转换全部完成！输出目录：{os.path.abspath(output_root)}")

# ====================== 主函数（简化参数）======================
def main(args):
    if args.mode == "forward":
        # 正向转换：LabelMe → YOLO
        print("🚀 开始正向转换（LabelMe → YOLO）...")
        input_root = args.input_dir
        output_root = args.output_dir
        val_ratio = args.val_ratio
        
        # 1. 遍历获取类别和图片映射
        print("🔍 开始遍历数据集...")
        class_image_map, class_names = get_image_label_pairs(input_root)
        if not class_names:
            print("❌ 未找到任何类别文件夹！")
            return
        print(f"✅ 找到{len(class_names)}个类别：{class_names}")
        
        # 2. 生成类别ID映射
        class_id_map = {name: idx for idx, name in enumerate(class_names)}
        
        # 3. 处理每个类别
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
        
        # 4. 生成data.yaml
        generate_data_yaml(output_root, class_names, train_img_dir, val_img_dir)
        
        # 输出统计信息
        print(f"\n🎉 正向转换全部完成！输出目录：{os.path.abspath(output_root)}")
        print(f"📋 数据集统计：")
        print(f"  ├─ 训练集图片：{len(os.listdir(train_img_dir)) if os.path.exists(train_img_dir) else 0}张")
        print(f"  ├─ 训练集标注：{len(os.listdir(train_label_dir)) if os.path.exists(train_label_dir) else 0}个")
        print(f"  ├─ 验证集图片：{len(os.listdir(val_img_dir)) if os.path.exists(val_img_dir) else 0}张")
        print(f"  └─ 验证集标注：{len(os.listdir(val_label_dir)) if os.path.exists(val_label_dir) else 0}个")
        
    elif args.mode == "backward":
        # 反向转换：YOLO → LabelMe（自动读取类别名）
        print("🚀 开始反向转换（YOLO → LabelMe）...")
        batch_convert_yolo_to_labelme(
            yolo_root=args.yolo_root,
            output_root=args.labelme_output_root,
            subsets=args.subsets
        )
    else:
        print(f"❌ 无效的模式：{args.mode}，请选择 forward 或 backward")

if __name__ == "__main__":
    # 配置参数（简化：反向转换无需手动填类别名）
    class Args:
        # ********** 核心：转换模式选择 **********
        mode = "backward"  # forward=LabelMe→YOLO / backward=YOLO→LabelMe
        
        # ========== 正向转换参数（mode=forward时生效）==========
        input_dir = r"C:\Users\Administrator\Desktop\shendu\photos\existing_faces"  # LabelMe数据根目录
        output_dir = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset"    # YOLO输出目录
        val_ratio = 0.2                                                              # 验证集比例
        
        # ========== 反向转换参数（mode=backward时生效）==========
        yolo_root = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset"     # YOLO数据集根目录
        labelme_output_root = r"C:\Users\Administrator\Desktop\shendu\photos\labelme_datasets"  # LabelMe输出目录
        subsets = ["train", "val"]              # 要处理的YOLO子集（train/val/test）
    
    args = Args()
    main(args)