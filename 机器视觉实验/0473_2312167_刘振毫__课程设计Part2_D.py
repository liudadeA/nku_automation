import json
import cv2
import numpy as np
import torch
from ultralytics import YOLO
import logging
import os
from collections import defaultdict
import time

# 配置日志
logging.basicConfig(filename='detection.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def add_detection(results, label, xmin, ymin, xmax, ymax):
    detection = {
        "label": label,
        "bbox": [int(xmin), int(ymin), int(xmax), int(ymax)]
    }
   
    results["objects"].append(detection)

def preprocess_image(image):
    """图像预处理，优化小目标检测"""
    # 1. 自适应直方图均衡化 (CLAHE)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # 针对小目标增强对比度
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16))
    l = clahe.apply(l)
    
    # 合并通道
    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # 2. 自适应锐化 - 使用非锐化掩蔽
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    
    # 3. 选择性降噪 - 仅在低对比度区域应用
    denoised = cv2.bilateralFilter(sharpened, 7, 75, 75)
    
    # 4. 小目标增强 - 使用Top-Hat变换
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT, kernel)
    enhanced = cv2.add(denoised, tophat)
    
    return enhanced

def multi_scale_detection(model, image, device, detect_classes=[0, 1]):
    """改进的多尺度检测策略，避免使用augment参数"""
    all_detections = []
    
    # 优化的多尺度组合：从大尺度到小尺度
    #3200会爆显存，2560是最大可用
    scales = [2560, 1920, 1600, 1280, 960, 640]
    
    # 图像金字塔参数 (减少层级以平衡精度和速度)
    pyramid_scales = [1.0, 0.75]  # 原始、75%尺寸
    
    for scale in scales:
        for pyr_scale in pyramid_scales:
            # 调整图像尺寸
            scaled_img = cv2.resize(image, (0, 0), fx=pyr_scale, fy=pyr_scale)
            h_scaled, w_scaled = scaled_img.shape[:2]
            
            try:
                # 使用GPU加速并启用半精度推理 - 移除augment参数
                detections = model.predict(
                    scaled_img,
                    conf=0.3,
                    iou=0.6,
                    imgsz=scale,
                    agnostic_nms=True,
                    verbose=False,
                    device=device,
                    half=True if 'cuda' in str(device) else False,
                    classes=detect_classes
                )[0]

                for box in detections.boxes:
                    cls_id = int(box.cls)
                    conf = float(box.conf)
                    label = model.names[cls_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    x1, y1, x2, y2 = int(x1/pyr_scale), int(y1/pyr_scale), int(x2/pyr_scale), int(y2/pyr_scale)
                    all_detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'conf': conf,
                        'label': label,  # 关键：带上类别
                        'scale': scale,
                        'pyr_scale': pyr_scale
                    })
                
            except Exception as e:
                logging.error(f"尺度 {scale} 金字塔 {pyr_scale} 检测失败: {str(e)}")
    
    return all_detections

def calculate_iou(box1, box2):
    """计算两个边界框的IoU"""
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    
    # 计算交集
    xi1, yi1 = max(x1, x3), max(y1, y3)
    xi2, yi2 = min(x2, x4), min(y2, y4)
    
    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0
    
    inter_area = (xi2 - xi1) * (yi2 - yi1)
    
    # 计算并集
    box1_area = (x2 - x1) * (y2 - y1)
    box2_area = (x4 - x3) * (y4 - y3)
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0

def weighted_boxes_fusion(detections, iou_threshold=0.35, skip_box_thr=0.15):
    """加权框融合(WBF)"""
    if not detections:
        return []
    
    # 按置信度分组
    boxes = []
    confs = []
    
    for det in detections:
        boxes.append(det['bbox'])
        confs.append(det['conf'])
    
    # 转换为NumPy数组以便处理
    boxes = np.array(boxes)
    confs = np.array(confs)
    
    # 按置信度降序排序
    sorted_indices = np.argsort(confs)[::-1]
    boxes = boxes[sorted_indices]
    confs = confs[sorted_indices]
    
    # 初始化融合框
    fused_boxes = []
    fused_confs = []
    
    # 主要融合循环
    while len(boxes) > 0:
        # 取当前最高置信度的框
        current_box = boxes[0]
        current_conf = confs[0]
        
        # 寻找与当前框IoU大于阈值的框
        ious = np.array([calculate_iou(current_box, box) for box in boxes])
        similar_mask = ious > iou_threshold
        
        # 计算融合框
        similar_boxes = boxes[similar_mask]
        similar_confs = confs[similar_mask]
        
        # 加权融合（小目标权重更大）
        weights = similar_confs
        for i, box in enumerate(similar_boxes):
            h = box[3] - box[1]
            w = box[2] - box[0]
            # 小目标的权重增加
            if w < 50 and h < 100:
                weights[i] *= 1.3
        
        # 计算加权平均框
        weights_sum = np.sum(weights)
        fused_box = np.average(similar_boxes, axis=0, weights=weights)
        fused_conf = np.average(similar_confs, weights=weights)
        
        # 添加到融合结果
        fused_boxes.append(fused_box)
        fused_confs.append(fused_conf)
        
        # 移除已融合的框
        boxes = boxes[~similar_mask]
        confs = confs[~similar_mask]
    
    # 过滤低置信度融合结果
    final_detections = []
    for box, conf in zip(fused_boxes, fused_confs):
        if conf >= skip_box_thr:
            final_detections.append({
                'bbox': [int(box[0]), int(box[1]), int(box[2]), int(box[3])],
                'conf': conf
            })
    
    return final_detections

def is_valid_person(bbox, conf, img_width, img_height):
    """基于特征的行人验证"""
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    
    # 1. 宽高比验证 - 更严格的约束
    aspect_ratio = height / max(width, 1)
    valid_aspect = 1.3 <= aspect_ratio <= 6.0  # 行人通常高度大于宽度
    
    # 2. 尺寸验证 - 排除过大/过小目标
    min_size = max(10, img_width * 0.005)  # 最小20像素或图像宽度的0.8%
    max_size = min(1200, img_width * 0.98)   # 最大400像素或图像宽度的70%
    valid_size = min_size <= height <= max_size
    
    # 3. 位置验证 - 行人不会在图像顶部区域（除非特殊情况）
    top_margin = img_height * 0.05
    valid_position = y2 > top_margin
    
    # 4. 置信度调整 - 小目标置信度补偿
    size_penalty = 1.0
    if height < 50:  # 小目标
        size_penalty = max(0.8, 1.0 - (50 - height)/80)
        conf *= size_penalty
    
    # 5. 综合判断
    is_valid = valid_aspect and valid_size and valid_position
 
    return is_valid, conf

def is_valid_bike(bbox, conf, img_width, img_height, original_image):
    """自行车目标验证"""
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    
    # 1. 降低置信度阈值
    min_conf = 0.39  # 降低基础阈值
    
    # 2. 尺寸验证（更宽松的限制）
    min_size = max(10, img_width * 0.003)
    max_size = min(img_width * 0.9, img_height * 0.9)
    valid_size = min_size <= max(width, height) <= max_size
    
    # 3. 对小目标和遮挡目标的置信度补偿
    if width < 150 or height < 150:  # 小目标补偿
        conf *= 2
    
    # 4. 蓝色自行车的补偿
    roi = original_image[max(0, y1):min(img_height, y2), max(0, x1):min(img_width, x2)]
    if roi.size > 0:  # 确保ROI有效
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # HSV中蓝色范围
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_ratio = np.sum(blue_mask) / (roi.shape[0] * roi.shape[1] * 255)
        
        # 如果区域内蓝色占比较高，提升置信度
        if blue_ratio > 0.2:  # 超过20%的蓝色占比
            conf *= 1.5  # 提升50%置信度
    
    # 5. 边缘目标补偿
    edge_margin = 10
    if x1 <= edge_margin or y1 <= edge_margin or \
       x2 >= img_width - edge_margin or y2 >= img_height - edge_margin:
        min_conf *= 0.6  # 边缘目标降低40%置信度要求
    
    is_valid = conf >= min_conf and valid_size
    return is_valid, conf

def detector(image_path, models, device=None, detect_mode=1):
    print(f"实际检测图片: {image_path}")
    try:
        start_time = time.time()
        
        # 读取图像
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        h, w = original_image.shape[:2]
        logging.info(f"图像尺寸: {w}x{h}")
        print(f"图像尺寸: {w}x{h}")
        
        # 图像预处理
        processed_image = preprocess_image(original_image)
        
        results = {
            "image_name": os.path.basename(image_path),
            "objects": [],
            "detection_info": {
                "total_detections": 0,
                "high_conf_detections": 0,
                "small_target_detections": 0
            }
        }

        # 加载多个模型进行集成检测
        all_detections = []
        for model_name, model in models.items():
            try:
                model_start = time.time()

                # 多尺度检测
                # 根据detect_mode决定检测类别
                detect_classes = [0] if detect_mode == 0 else [0, 1]
                detections = multi_scale_detection(model, processed_image, device, detect_classes)
                all_detections.extend(detections)

                model_time = time.time() - model_start
                logging.info(f"{model_name} 检测到 {len(detections)} 个候选目标")
                print(f"{model_name} 检测到 {len(detections)} 个候选目标")

                # 显存清理
                if 'cuda' in str(device):
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except Exception as e:
                logging.error(f"模型 {model_name} 检测失败: {str(e)}", exc_info=True)
                print(f"模型 {model_name} 检测失败: {str(e)}")
        
        # 使用加权框融合
        if all_detections:
            wbf_start = time.time()
            final_detections = weighted_boxes_fusion(all_detections, iou_threshold=0.4, skip_box_thr=0.2)
            wbf_time = time.time() - wbf_start
            logging.info(f"WBF融合保留 {len(final_detections)} 个检测结果")
            print(f"WBF融合保留 {len(final_detections)} 个检测结果")
        else:
            final_detections = []
            print("未检测到任何行人候选框")
        
        # 首先进行label分配
        for i, det in enumerate(final_detections):
            max_iou = 0
            best_label = 'person'
            for src in all_detections:
                iou = calculate_iou(det['bbox'], src['bbox'])
                if iou > max_iou:
                    max_iou = iou
                    best_label = src['label']
            det['label'] = best_label

        # 然后再处理检测结果和绘图
        for detection in final_detections:
            bbox = detection['bbox']
            conf = detection['conf']
            label = detection.get('label', 'person')

            if label == "person":
                is_valid, adj_conf = is_valid_person(bbox, conf, w, h)
                min_conf_threshold = 0.2
                size_penalty = max(0.8, min(1.0, (bbox[3]-bbox[1])/100))
                conf_threshold = min_conf_threshold * size_penalty
                if not (is_valid and adj_conf >= 0.46):
                    continue
                if adj_conf < conf_threshold:
                    continue
                add_detection(results, "person", *bbox)
                color = (0, 255, 0)
                text = f"person {adj_conf:.2f}"

            elif detect_mode == 1 and label == "bicycle":
                is_valid, bike_conf = is_valid_bike(bbox, conf, w, h, original_image)
                if not is_valid:
                    continue
                add_detection(results, "bike", *bbox)
                color = (255, 0, 0)  # 蓝色表示自行车
                text = f"bike {bike_conf:.2f}"
            else:
                continue

            # 绘制检测框和标签
            x1, y1, x2, y2 = bbox
            cv2.rectangle(original_image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(original_image, text, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        results["detection_info"]["total_detections"] = len(results["objects"])
        
        # 保存结果JSON
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        #output_json = f"刘振毫_{base_name}_prediction.json"
        output_json = f"刘振毫_predicted_result.json"
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # 保存检测结果图像
        output_image = f"{base_name}_result.jpg"
        #cv2.imwrite(output_image, original_image)
        
        # 输出统计信息
        total_time = time.time() - start_time
        logging.info(f"检测完成! 总检测数: {results['detection_info']['total_detections']}")
        print(f"检测完成!")
        print(f"总检测数: {results['detection_info']['total_detections']}")
        print(f"结果已保存: {output_json}")
        print(f"检测图像已保存: {output_image}")

        return results

    except Exception as e:
        error_msg = f"检测失败：{str(e)}"
        logging.error(error_msg, exc_info=True)
        print(f"{error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg}

if __name__ == "__main__":
    # 自动选择设备（优先GPU）
    device = torch.device('cuda:0') if torch.cuda.is_available() else torch.device('cpu')
    if device.type == 'cuda':
        torch.backends.cudnn.benchmark = True
    
    print(f"使用设备: {device}")
    
    # 提前加载模型，不用每次重新加载
    model_names = ["yolo12x.pt", "yolo11x-seg.pt"]
    models = {name: YOLO(name) for name in model_names}
    logging.info(f"加载模型: {model_names}")
    print(f"加载模型: {model_names}")

    # 检测图像
    #detector("S_TOTAL.jpg", models, device=device, detect_mode=0)  
    detector("D_TOTAL.jpg", models, device=device, detect_mode=1)