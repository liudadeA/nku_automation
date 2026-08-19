from ultralytics import YOLO
import os
import shutil
from pathlib import Path

# ===================== 核心配置（需修改！）=====================
# 训练好的模型路径（训练结果中的best.pt）
model_path = r"C:\Users\Administrator\Desktop\shendu\photos\yolov8_train_results\yolov8_train\weights\best.pt"
# 待分类的图片文件夹（放需要归类的照片）
input_img_dir = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset\images\train"
# 分类结果输出根目录
output_root_dir = r"C:\Users\Administrator\Desktop\shendu\photos\classified_results"
# 置信度阈值（过滤低置信度误检测）
conf_threshold = 0.8
# 是否移动图片（False=复制，True=移动，新手推荐复制）
move_mode = False

# ===================== 工具函数：创建文件夹 =====================
def create_dir(dir_path):
    """创建文件夹（不存在则创建）"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"📁 创建文件夹：{dir_path}")

# ===================== 核心：图片分类逻辑 =====================
def classify_photos_by_yolo():
    # 1. 加载训练好的模型
    model = YOLO(model_path)
    print(f"✅ 成功加载模型：{model_path}")
    
    # 2. 初始化输出目录（新增「没有类」「多人类」）
    create_dir(output_root_dir)
    no_class_dir = os.path.join(output_root_dir, "no")  # 无检测结果
    multi_class_dir = os.path.join(output_root_dir, "more")  # 检测到多个类别
    create_dir(no_class_dir)
    create_dir(multi_class_dir)
    
    # 3. 获取待分类图片列表（支持常见格式）
    img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.webp']
    img_list = []
    for file in os.listdir(input_img_dir):
        file_ext = Path(file).suffix.lower()
        if file_ext in img_extensions:
            img_list.append(os.path.join(input_img_dir, file))
    
    if not img_list:
        print("❌ 待分类文件夹中未找到图片！")
        return
    print(f"🔍 找到{len(img_list)}张待分类图片")
    
    # 4. 遍历图片，逐张预测并分类
    for img_path in img_list:
        img_name = Path(img_path).name
        print(f"\n📸 处理图片：{img_name}")
        
        # 关键：预测时关闭可视化、不保存带框图片
        results = model.predict(
            source=img_path,
            conf=conf_threshold,  # 过滤低置信度结果
            save=False,           # 不保存带检测框的图片
            show=False,           # 不显示预测窗口
            verbose=False,        # 不输出详细日志
            device=0,             # 用4060加速（CPU设-1）
            imgsz=640,            # 和训练尺寸一致
        )
        
        # 5. 解析预测结果：提取所有有效类别（去重）
        detected_classes = set()  # 用集合自动去重
        for r in results:
            if r.boxes is not None and len(r.boxes) > 0:
                # 过滤低于置信度阈值的框（双重保险）
                boxes = r.boxes[r.boxes.conf >= conf_threshold]
                if len(boxes) == 0:
                    continue
                # 提取类别ID并转换为类别名
                cls_ids = boxes.cls.cpu().numpy().astype(int)
                names = model.names  # 类别ID→名称映射
                for cls_id in cls_ids:
                    detected_classes.add(names[cls_id])
        
        # 6. 根据检测结果分类
        dest_path = ""
        if len(detected_classes) == 0:
            # 无有效检测结果 → 没有类
            dest_path = os.path.join(no_class_dir, img_name)
            print(f"   ⚠️  未检测到任何有效目标 → 放入「没有类」")
        elif len(detected_classes) >= 2:
            # 检测到≥2个不同类别 → 多人类
            dest_path = os.path.join(multi_class_dir, img_name)
            print(f"   ⚠️  检测到多个类别：{list(detected_classes)} → 放入「多人类」")
        else:
            # 仅检测到1个类别 → 对应类别文件夹
            single_class = list(detected_classes)[0]
            class_dir = os.path.join(output_root_dir, single_class)
            create_dir(class_dir)
            dest_path = os.path.join(class_dir, img_name)
            print(f"   ✅ 仅检测到单个类别：{single_class} → 放入对应文件夹")
        
        # 7. 处理同名文件（避免覆盖）
        if os.path.exists(dest_path):
            stem = Path(img_name).stem
            ext = Path(img_name).suffix
            count = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(
                    os.path.dirname(dest_path),
                    f"{stem}_{count}{ext}"
                )
                count += 1
        
        # 8. 复制/移动图片
        if move_mode:
            shutil.move(img_path, dest_path)
            print(f"   🚚 移动完成：{img_path} → {dest_path}")
        else:
            shutil.copy2(img_path, dest_path)
            print(f"   📋 复制完成：{img_path} → {dest_path}")
    
    # 9. 输出统计结果
    print(f"\n🎉 所有图片分类完成！")
    print(f"📊 分类统计：")
    print(f"   ├─ 总处理图片数：{len(img_list)}")
    print(f"   ├─ 没有类：{len(os.listdir(no_class_dir))}张")
    print(f"   ├─ 多人类：{len(os.listdir(multi_class_dir))}张")
    # 统计单类别文件夹数量
    single_class_count = 0
    for item in os.listdir(output_root_dir):
        item_path = os.path.join(output_root_dir, item)
        if os.path.isdir(item_path) and item not in ["no", "more"]:
            single_class_count += len(os.listdir(item_path))
            print(f"   ├─ {item}：{len(os.listdir(item_path))}张")
    print(f"   └─ 单类别总数：{single_class_count}张")

if __name__ == "__main__":
    classify_photos_by_yolo()