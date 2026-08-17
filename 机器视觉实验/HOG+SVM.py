import json
import cv2

def add_detection(results, label, xmin, ymin, xmax, ymax):
    # 向 results 中添加一个检测框
    results["objects"].append({
        "label": label,
        "bbox": [int(xmin), int(ymin), int(xmax), int(ymax)]
    })

def detector(image_path):
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    results = {
        "image_name": image_path.split("/")[-1],
        "objects": []
    }

    # 添加第一个检测框信息到results中，内容包括目标标签和包围框位置xmin, ymin, xmax, ymax
    add_detection(results, "target", 0.2 * w, 0.2 * h, 0.4 * w, 0.4 * h)
    # 添加第二个检测框
    add_detection(results, "target", 0.6 * w, 0.5 * h, 0.8 * w, 0.7 * h)

    # 保存结果为 JSON，文件名为“学生名字_predicted_result.json”
    with open("学生名字_predicted_result.json", "w") as f:
        json.dump(results, f, indent=2)

detector("example.jpg")