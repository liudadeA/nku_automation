1. 检测结果保存规范
使用通用的 .json 格式保存检测结果与标注信息，统一的文件结构如下：
{
  "image_name": "example.jpg",
  "objects": [
    {
      "label": "target",
      "bbox": [xmin, ymin, xmax, ymax]
    },
    ...
  ]
}
image_name：图像文件名
objects：检测出的所有目标列表
label：目标类别
bbox：目标边界框，格式为 [xmin, ymin, xmax, ymax]

检测结果命名格式为：学生名字_predicted_result.json（请将“学生名字”替换为你的姓名）

2. 评分标准说明
评分将依据以下四项指标进行评估：
Precision（精确率）：预测为正样本中实际为正的比例
Recall（召回率）：实际正样本中被正确检测出的比例
F1 Score（调和平均值）：综合考虑精确率与召回率
mAP（平均精度）

匹配判定方式：
严格匹配：预测框与真实框的 IoU ≥ 0.5，视为一次正确检测。
宽松匹配：若预测框的中心点落在真实框内部，视为一次正确检测。