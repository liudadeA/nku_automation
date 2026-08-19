from ultralytics import YOLO
import os

# ===================== 核心配置（需修改！）=====================
# 替换为你生成的data.yaml文件路径（转换脚本输出的yolo_dataset目录下）
data_yaml_path = r"C:\Users\Administrator\Desktop\shendu\photos\yolo_dataset\data.yaml"
# 底模选择：yolov8n(轻量)/s(小)/m(中)/l(大)/x(超大)，按需选（新手先选yolov8n）
# 训练参数
epochs = 100          # 训练轮数（新手先设50-100，足够收敛）
batch_size = 32     # 批次大小（显存不足则改4/2/1）
imgsz = 640           # 输入图片尺寸（YOLO默认640，无需改）
device = 0            # 显卡ID（0=第一张显卡，-1=CPU，无显卡则设-1）
save_dir = r"C:\Users\Administrator\Desktop\shendu\photos\yolov8_train_results"  # 训练结果保存目录

# ===================== 训练逻辑 =====================
def train_yolov8():
    # 1. 加载预训练底模
    # 修改train.py中加载模型的代码
    model_name = r"C:\Users\Administrator\Desktop\shendu\photos\yolov8_train_results\yolov8_train\weights\best.pt"  # 可改为yolov8s.pt/yolov8m.pt/yolov8l.pt/yolov8x.pt
    model = YOLO(model_name, task="detect")  # 明确指定任务为目标检测，仅加载YOLOv8相关权重
    print(f"✅ 成功加载底模")
    
    # 2. 检查data.yaml是否存在
    if not os.path.exists(data_yaml_path):
        print(f"❌ 错误：找不到data.yaml文件，请检查路径：{data_yaml_path}")
        return
    
    # 3. 启动训练
    results = model.train(
        data=data_yaml_path,      # 数据集配置文件
        epochs=epochs,            # 训练轮数
        batch=batch_size,         # 批次大小
        imgsz=imgsz,              # 图片尺寸
        device=device,            # 训练设备
        project=save_dir,         # 结果保存根目录
        name="yolov8_train",      # 实验名（结果会存在save_dir/yolov8_train下）
        exist_ok=True,            # 覆盖已有实验目录
        patience=50,              # 早停耐心值（50轮没提升则停止）
        save=True,                # 保存最佳模型
        save_period=10,           # 每10轮保存一次检查点
        val=True,                 # 训练中验证（必须开，评估精度）
        cache=True,               # 缓存数据集（加速训练）
        pretrained=True,          # 使用预训练权重
        optimizer="Adam",          # 优化器（默认SGD，可选Adam）
        lr0=0.05,                 # 初始学习率
        lrf=0.01,                 # 最终学习率
        momentum=0.937,           # 动量
        weight_decay=0.0005,      # 权重衰减（防止过拟合）
        warmup_epochs=3,          # 热身轮数
        warmup_momentum=0.8,      # 热身动量
        box=7.5,                  # 框损失权重
        cls=0.5,                  # 分类损失权重
        hsv_h=0.015,              # 色调增强
        hsv_s=0.7,                # 饱和度增强
        hsv_v=0.4,                # 明度增强
        degrees=0.0,              # 旋转角度
        translate=0.1,            # 平移
        scale=0.5,                # 缩放
        flipud=0.0,               # 上下翻转概率
        fliplr=0.5,               # 左右翻转概率
        mosaic=1.0,               # 马赛克增强
        mixup=0.0,                # mixup增强
        copy_paste=0.0,           # 复制粘贴增强

    )
    
    # 4. 输出训练结果
    print("\n🎉 训练完成！")
    print(f"📊 最佳模型路径：{results.save_dir}/weights/best.pt")
    print(f"📈 训练日志：{results.save_dir}/results.csv")
    print(f"📸 可视化结果：{results.save_dir}/val_batch0_pred.jpg")

# ===================== 验证模型（训练后运行）=====================
def val_yolov8():
    # 加载训练好的最佳模型
    best_model_path = os.path.join(save_dir, "yolov8_train", "weights", "best.pt")
    if not os.path.exists(best_model_path):
        print(f"❌ 错误：找不到最佳模型，请先完成训练：{best_model_path}")
        return
    
    model = YOLO(best_model_path)
    # 验证模型精度（输出mAP等指标）
    metrics = model.val(data=data_yaml_path)
    print(f"\n📊 验证集精度：")
    print(f"   ├─ mAP@0.5: {metrics.box.map50:.4f}")  # 核心指标，越高越好
    print(f"   └─ mAP@0.5:0.95: {metrics.box.map:.4f}")

if __name__ == "__main__":
    # 第一步：启动训练
    train_yolov8()
    
    # 第二步：训练完成后，验证模型精度（注释掉上面的train_yolov8()，打开下面）
    val_yolov8()
