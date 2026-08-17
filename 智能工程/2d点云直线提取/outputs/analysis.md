# 2D 点云直线提取仿真实验报告

## 1. 实验设置
- 数据由 3 条真实直线段组成，每条直线段采样 70 个点，并叠加沿线方向抖动与法向高斯噪声。
- 额外加入均匀分布离群点，用于检验算法在噪声和异常点下的鲁棒性。
- Split-and-Merge 与 Line-Regression 默认依赖点序假设，因此仿真数据按线段顺序组织，符合激光扫描序列的常见输入形式。
- 评价指标包括 Precision、Recall、F1、平均角度误差、平均距离误差和运行时间。

## 2. 样例场景结果
- 可视化文件：`outputs/sample_detections.png`，对应场景为 `中噪声`。
- Split-and-Merge: angle=20.79 deg, points=70；angle=171.25 deg, points=70；angle=123.11 deg, points=70
- Line-Regression: angle=20.79 deg, points=70；angle=171.25 deg, points=70；angle=123.11 deg, points=70
- RANSAC: angle=123.16 deg, points=76；angle=21.03 deg, points=65；angle=171.15 deg, points=63
- Hough-Transform: angle=122.97 deg, points=71；angle=170.60 deg, points=54；angle=20.84 deg, points=65

## 3. 汇总结果
| 场景 | 算法 | F1 | Precision | Recall | 运行时间(ms) | 角度误差(deg) | 距离误差 | 平均检测条数 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 低噪声 | Split-and-Merge | 0.993 | 0.988 | 1.000 | 0.519 | 0.088 | 0.002 | 3.05 |
| 低噪声 | Line-Regression | 0.993 | 0.988 | 1.000 | 12.785 | 0.088 | 0.002 | 3.05 |
| 低噪声 | RANSAC | 1.000 | 1.000 | 1.000 | 84.848 | 0.115 | 0.003 | 3.00 |
| 低噪声 | Hough-Transform | 1.000 | 1.000 | 1.000 | 5.026 | 0.121 | 0.003 | 3.00 |
| 中噪声 | Split-and-Merge | 0.898 | 0.839 | 1.000 | 1.450 | 0.235 | 0.006 | 3.85 |
| 中噪声 | Line-Regression | 1.000 | 1.000 | 1.000 | 12.892 | 0.216 | 0.006 | 3.00 |
| 中噪声 | RANSAC | 1.000 | 1.000 | 1.000 | 78.590 | 0.242 | 0.007 | 3.00 |
| 中噪声 | Hough-Transform | 1.000 | 1.000 | 1.000 | 5.299 | 0.251 | 0.012 | 3.00 |
| 高噪声 | Split-and-Merge | 0.770 | 0.643 | 1.000 | 1.436 | 0.566 | 0.011 | 5.05 |
| 高噪声 | Line-Regression | 0.904 | 0.843 | 1.000 | 11.863 | 0.396 | 0.011 | 3.75 |
| 高噪声 | RANSAC | 1.000 | 1.000 | 1.000 | 77.286 | 0.480 | 0.013 | 3.00 |
| 高噪声 | Hough-Transform | 1.000 | 1.000 | 1.000 | 5.208 | 0.637 | 0.029 | 3.00 |

## 4. 结果分析
- 低噪声: F1 最优为 `RANSAC` (1.000)，速度最快为 `Split-and-Merge` (0.519 ms)，参数误差最小为 `Split-and-Merge`。
- 中噪声: F1 最优为 `Line-Regression` (1.000)，速度最快为 `Split-and-Merge` (1.450 ms)，参数误差最小为 `Line-Regression`。
- 高噪声: F1 最优为 `RANSAC` (1.000)，速度最快为 `Split-and-Merge` (1.436 ms)，参数误差最小为 `Line-Regression`。
- Split-and-Merge 对分段明显、点序连续的数据表现稳定，但当噪声变大时容易出现过分裂或欠分裂。
- Line-Regression 直接使用最小二乘残差控制增长，通常能得到更平滑的线段，但对阈值较敏感。
- RANSAC 在含离群点场景下通常保持较高召回率，是鲁棒性最强的方法之一，但运行时间通常高于序列分割法。
- Hough-Transform 适合全局搜索主方向，面对交叉线和离群点时仍能检出主峰，但量化分辨率会带来一定参数偏差。
- 四种方法在三种噪声场景下均能识别出主要直线结构，说明构建的模型和实验流程能够有效验证算法正确性。

## 5. 输出文件
- `outputs/sample_detections.png`: 单次样例场景下四种算法的检测可视化结果。
- `outputs/metric_comparison.png`: 三类场景的综合指标对比图。
- `outputs/results.csv`: 每次试验的原始统计结果。
- `outputs/summary.csv`: 各算法在各场景下的平均结果。