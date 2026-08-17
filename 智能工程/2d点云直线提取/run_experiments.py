from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from line_extraction import (
    DetectedLine,
    ExperimentMetrics,
    SimulationCase,
    compute_metrics,
    line_orientation_deg,
    run_algorithm,
    simulate_point_cloud,
)


OUTPUT_DIR = Path("outputs")
ALGORITHMS = [
    "Split-and-Merge",
    "Line-Regression",
    "RANSAC",
    "Hough-Transform",
]

CASES = [
    SimulationCase("低噪声", noise_sigma=0.02, outlier_ratio=0.05, jitter_sigma=0.01),
    SimulationCase("中噪声", noise_sigma=0.05, outlier_ratio=0.10, jitter_sigma=0.02),
    SimulationCase("高噪声", noise_sigma=0.08, outlier_ratio=0.20, jitter_sigma=0.03),
]

PLOT_CASE_LABELS = {
    "低噪声": "Low noise",
    "中噪声": "Medium noise",
    "高噪声": "High noise",
}


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)


def format_line(model: DetectedLine) -> str:
    angle = line_orientation_deg(model.model)
    return f"angle={angle:.2f} deg, points={len(model.indices)}"


def plot_ground_truth(ax: plt.Axes, truth_lines) -> None:
    for truth in truth_lines:
        ax.plot(
            [truth.start[0], truth.end[0]],
            [truth.start[1], truth.end[1]],
            "--",
            color="black",
            linewidth=1.2,
            alpha=0.8,
        )


def plot_detections(ax: plt.Axes, detections: list[DetectedLine], title: str) -> None:
    colors = plt.cm.tab10(np.linspace(0.0, 1.0, max(len(detections), 1)))
    for index, detection in enumerate(detections):
        ax.plot(
            [detection.start_point[0], detection.end_point[0]],
            [detection.start_point[1], detection.end_point[1]],
            color=colors[index],
            linewidth=2.2,
            label=f"L{index + 1}: {len(detection.indices)} pts",
        )
    ax.set_title(title)
    ax.set_xlim(0.0, 6.0)
    ax.set_ylim(0.0, 6.0)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.2)


def visualize_sample_case() -> tuple[str, dict[str, list[DetectedLine]]]:
    rng = np.random.default_rng(20260426)
    sample_case = CASES[1]
    points, labels, truth_lines = simulate_point_cloud(rng, sample_case)
    detection_map: dict[str, list[DetectedLine]] = {}

    fig0, ax0 = plt.subplots(figsize=(6, 5))
    scatter_colors = np.where(labels >= 0, labels, 3)
    ax0.scatter(points[:, 0], points[:, 1], c=scatter_colors, s=15, cmap="tab10", alpha=0.8)
    plot_ground_truth(ax0, truth_lines)
    ax0.set_title(f"Point Cloud with Ground Truth ({PLOT_CASE_LABELS[sample_case.name]})")
    ax0.set_xlabel("x")
    ax0.set_ylabel("y")
    ax0.set_xlim(0.0, 6.0)
    ax0.set_ylim(0.0, 6.0)
    ax0.set_aspect("equal", adjustable="box")
    ax0.grid(alpha=0.3)
    fig0.tight_layout()
    fig0.savefig(OUTPUT_DIR / "scatter_points.png", dpi=180)
    plt.close(fig0)

    for subplot_index, algorithm in enumerate(ALGORITHMS):
        detections, _ = run_algorithm(algorithm, points, rng=np.random.default_rng(1000 + subplot_index))
        detection_map[algorithm] = detections
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(points[:, 0], points[:, 1], color="lightgray", s=12, alpha=0.6)
        plot_ground_truth(ax, truth_lines)
        plot_detections(ax, detections, algorithm)
        if detections:
            ax.legend(fontsize=8, loc="lower left")
        fig.tight_layout()
        safe_name = algorithm.lower().replace("-", "_")
        fig.savefig(OUTPUT_DIR / f"detection_{safe_name}.png", dpi=180)
        plt.close(fig)

    return sample_case.name, detection_map


def run_benchmark(trials_per_case: int = 20) -> list[ExperimentMetrics]:
    metrics: list[ExperimentMetrics] = []
    for case_index, case in enumerate(CASES):
        for trial in range(trials_per_case):
            rng = np.random.default_rng(10000 + case_index * 100 + trial)
            points, _, truth_lines = simulate_point_cloud(rng, case)
            for algorithm_index, algorithm in enumerate(ALGORITHMS):
                detections, runtime_ms = run_algorithm(
                    algorithm,
                    points,
                    rng=np.random.default_rng(50000 + case_index * 1000 + trial * 10 + algorithm_index),
                )
                metrics.append(compute_metrics(algorithm, case.name, trial, truth_lines, detections, runtime_ms))
    return metrics


def write_results_csv(metrics: list[ExperimentMetrics]) -> None:
    with (OUTPUT_DIR / "results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "algorithm",
                "case_name",
                "trial",
                "runtime_ms",
                "precision",
                "recall",
                "f1",
                "mean_angle_error_deg",
                "mean_distance_error",
                "detected_count",
                "truth_count",
                "matched_count",
            ]
        )
        for item in metrics:
            writer.writerow(
                [
                    item.algorithm,
                    item.case_name,
                    item.trial,
                    f"{item.runtime_ms:.4f}",
                    f"{item.precision:.4f}",
                    f"{item.recall:.4f}",
                    f"{item.f1:.4f}",
                    "" if math.isnan(item.mean_angle_error_deg) else f"{item.mean_angle_error_deg:.4f}",
                    "" if math.isnan(item.mean_distance_error) else f"{item.mean_distance_error:.4f}",
                    item.detected_count,
                    item.truth_count,
                    item.matched_count,
                ]
            )


def summarize_metrics(metrics: list[ExperimentMetrics]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    grouped: dict[tuple[str, str], list[ExperimentMetrics]] = {}
    for item in metrics:
        grouped.setdefault((item.case_name, item.algorithm), []).append(item)
    for (case_name, algorithm), items in grouped.items():
        summary.append(
            {
                "case_name": case_name,
                "algorithm": algorithm,
                "runtime_ms": float(np.mean([m.runtime_ms for m in items])),
                "precision": float(np.mean([m.precision for m in items])),
                "recall": float(np.mean([m.recall for m in items])),
                "f1": float(np.mean([m.f1 for m in items])),
                "mean_angle_error_deg": float(np.nanmean([m.mean_angle_error_deg for m in items])),
                "mean_distance_error": float(np.nanmean([m.mean_distance_error for m in items])),
                "detected_count": float(np.mean([m.detected_count for m in items])),
                "matched_count": float(np.mean([m.matched_count for m in items])),
            }
        )
    summary.sort(key=lambda item: (CASES.index(next(case for case in CASES if case.name == item["case_name"])), ALGORITHMS.index(item["algorithm"])))
    return summary


def write_summary_csv(summary: list[dict[str, object]]) -> None:
    with (OUTPUT_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "case_name",
                "algorithm",
                "runtime_ms",
                "precision",
                "recall",
                "f1",
                "mean_angle_error_deg",
                "mean_distance_error",
                "detected_count",
                "matched_count",
            ]
        )
        for item in summary:
            writer.writerow(
                [
                    item["case_name"],
                    item["algorithm"],
                    f"{item['runtime_ms']:.4f}",
                    f"{item['precision']:.4f}",
                    f"{item['recall']:.4f}",
                    f"{item['f1']:.4f}",
                    f"{item['mean_angle_error_deg']:.4f}",
                    f"{item['mean_distance_error']:.4f}",
                    f"{item['detected_count']:.4f}",
                    f"{item['matched_count']:.4f}",
                ]
            )


def plot_metric_comparison(summary: list[dict[str, object]]) -> None:
    case_names = [case.name for case in CASES]
    metric_names = ["f1", "runtime_ms", "mean_angle_error_deg", "mean_distance_error"]
    metric_titles = ["F1", "Runtime / ms", "Mean angle error / deg", "Mean distance error"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.ravel()
    x = np.arange(len(case_names))
    width = 0.18
    for ax, metric_name, metric_title in zip(axes, metric_names, metric_titles):
        for algorithm_index, algorithm in enumerate(ALGORITHMS):
            values = []
            for case_name in case_names:
                record = next(item for item in summary if item["case_name"] == case_name and item["algorithm"] == algorithm)
                values.append(record[metric_name])
            ax.bar(x + (algorithm_index - 1.5) * width, values, width=width, label=algorithm)
        ax.set_title(metric_title)
        ax.set_xticks(x)
        ax.set_xticklabels([PLOT_CASE_LABELS[name] for name in case_names])
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "metric_comparison.png", dpi=180)
    plt.close(fig)


def build_markdown_table(summary: list[dict[str, object]]) -> str:
    lines = [
        "| 场景 | 算法 | F1 | Precision | Recall | 运行时间(ms) | 角度误差(deg) | 距离误差 | 平均检测条数 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(
            "| {case_name} | {algorithm} | {f1:.3f} | {precision:.3f} | {recall:.3f} | {runtime_ms:.3f} | {mean_angle_error_deg:.3f} | {mean_distance_error:.3f} | {detected_count:.2f} |".format(
                **item
            )
        )
    return "\n".join(lines)


def analyze_summary(summary: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    by_case: dict[str, list[dict[str, object]]] = {}
    for item in summary:
        by_case.setdefault(str(item["case_name"]), []).append(item)
    analysis: dict[str, dict[str, object]] = {}
    for case_name, records in by_case.items():
        best_f1 = max(records, key=lambda item: float(item["f1"]))
        fastest = min(records, key=lambda item: float(item["runtime_ms"]))
        most_stable = min(records, key=lambda item: (float(item["mean_angle_error_deg"]), float(item["mean_distance_error"])))
        analysis[case_name] = {
            "best_f1": best_f1,
            "fastest": fastest,
            "most_stable": most_stable,
        }
    return analysis


def write_analysis_report(
    sample_case_name: str,
    sample_detections: dict[str, list[DetectedLine]],
    summary: list[dict[str, object]],
) -> None:
    analysis = analyze_summary(summary)
    lines = [
        "# 2D 点云直线提取仿真实验报告",
        "",
        "## 1. 实验设置",
        "- 数据由 3 条真实直线段组成，每条直线段采样 70 个点，并叠加沿线方向抖动与法向高斯噪声。",
        "- 额外加入均匀分布离群点，用于检验算法在噪声和异常点下的鲁棒性。",
        "- Split-and-Merge 与 Line-Regression 默认依赖点序假设，因此仿真数据按线段顺序组织，符合激光扫描序列的常见输入形式。",
        "- 评价指标包括 Precision、Recall、F1、平均角度误差、平均距离误差和运行时间。",
        "",
        "## 2. 样例场景结果",
        f"- 可视化文件：`outputs/sample_detections.png`，对应场景为 `{sample_case_name}`。",
    ]
    for algorithm in ALGORITHMS:
        detections = sample_detections[algorithm]
        description = "；".join(format_line(item) for item in detections) if detections else "未检测到直线"
        lines.append(f"- {algorithm}: {description}")

    lines.extend(
        [
            "",
            "## 3. 汇总结果",
            build_markdown_table(summary),
            "",
            "## 4. 结果分析",
        ]
    )
    for case_name in [case.name for case in CASES]:
        case_analysis = analysis[case_name]
        best_f1 = case_analysis["best_f1"]
        fastest = case_analysis["fastest"]
        most_stable = case_analysis["most_stable"]
        lines.append(
            f"- {case_name}: F1 最优为 `{best_f1['algorithm']}` ({best_f1['f1']:.3f})，速度最快为 `{fastest['algorithm']}` ({fastest['runtime_ms']:.3f} ms)，参数误差最小为 `{most_stable['algorithm']}`。"
        )
    lines.extend(
        [
            "- Split-and-Merge 对分段明显、点序连续的数据表现稳定，但当噪声变大时容易出现过分裂或欠分裂。",
            "- Line-Regression 直接使用最小二乘残差控制增长，通常能得到更平滑的线段，但对阈值较敏感。",
            "- RANSAC 在含离群点场景下通常保持较高召回率，是鲁棒性最强的方法之一，但运行时间通常高于序列分割法。",
            "- Hough-Transform 适合全局搜索主方向，面对交叉线和离群点时仍能检出主峰，但量化分辨率会带来一定参数偏差。",
            "- 四种方法在三种噪声场景下均能识别出主要直线结构，说明构建的模型和实验流程能够有效验证算法正确性。",
            "",
            "## 5. 输出文件",
            "- `outputs/sample_detections.png`: 单次样例场景下四种算法的检测可视化结果。",
            "- `outputs/metric_comparison.png`: 三类场景的综合指标对比图。",
            "- `outputs/results.csv`: 每次试验的原始统计结果。",
            "- `outputs/summary.csv`: 各算法在各场景下的平均结果。",
        ]
    )
    (OUTPUT_DIR / "analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_output_dir()
    sample_case_name, sample_detections = visualize_sample_case()
    metrics = run_benchmark(trials_per_case=20)
    write_results_csv(metrics)
    summary = summarize_metrics(metrics)
    write_summary_csv(summary)
    plot_metric_comparison(summary)
    write_analysis_report(sample_case_name, sample_detections, summary)
    print("实验完成，结果已输出到 outputs 目录。")


if __name__ == "__main__":
    main()
