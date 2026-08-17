# 2D 点云直线提取仿真实验

本项目实现了 4 种基于 2D 点云的直线提取算法，并通过随机仿真实验验证模型正确性：

- Split-and-Merge
- Line-Regression
- RANSAC
- Hough-Transform

## 1. 环境要求

- Python 3.13+
- `numpy`
- `matplotlib`

## 2. 运行方式

在项目目录执行：

```bash
python run_experiments.py
```

运行后会自动生成仿真点云、执行四种算法、完成多次统计实验，并将结果输出到 `outputs` 目录。

## 3. 项目文件

- `line_extraction.py`: 四种直线提取算法、仿真数据生成、评价指标计算。
- `run_experiments.py`: 批量实验入口、结果可视化、CSV 导出与分析报告生成。
- `outputs/sample_detections.png`: 单次样例场景的检测结果图。
- `outputs/metric_comparison.png`: 三类噪声场景下的性能对比图。
- `outputs/results.csv`: 每次实验的原始数据。
- `outputs/summary.csv`: 各算法的平均结果。
- `outputs/analysis.md`: 自动生成的实验分析报告。

## 4. 仿真设置

- 真实场景由 3 条线段组成。
- 每条线段采样 70 个点。
- 在沿线方向加入微小抖动，在法向方向加入高斯噪声。
- 额外加入随机离群点，测试算法鲁棒性。
- 噪声场景分为低噪声、中噪声、高噪声 3 类。

## 5. 指标说明

- Precision: 检测出的直线中，正确检测的比例。
- Recall: 真实直线中，被成功检测的比例。
- F1: Precision 和 Recall 的综合指标。
- Mean angle error: 检测直线和真实直线之间的平均角度误差。
- Mean distance error: 检测直线和真实直线之间的平均距离误差。
- Runtime: 算法平均运行时间。

## 6. 结果结论

当前默认参数下：

- `RANSAC` 和 `Hough-Transform` 在三种噪声场景下均达到很高的稳定性，平均 F1 接近 1。
- `Line-Regression` 在中低噪声场景表现接近理想，在高噪声场景下会出现少量过分段。
- `Split-and-Merge` 速度最快，但在高噪声场景下更容易发生过分裂，Precision 会下降。
- 四种算法都能够在仿真场景中恢复主要直线结构，说明实验系统能够有效验证所建模型的正确性。

## 7. 说明

- Split-and-Merge 与 Line-Regression 默认假设输入点云具有一定扫描顺序，因此实现中保留了序列分段特征。
- 若后续需要扩展到无序点云，可在预处理阶段增加聚类、排序或邻域图构建步骤。
