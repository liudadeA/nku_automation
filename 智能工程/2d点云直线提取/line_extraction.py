from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np


EPS = 1e-9


@dataclass(frozen=True)
class LineModel:
    a: float
    b: float
    c: float
    point: np.ndarray
    direction: np.ndarray


@dataclass(frozen=True)
class DetectedLine:
    model: LineModel
    indices: np.ndarray
    start_point: np.ndarray
    end_point: np.ndarray
    score: float


@dataclass(frozen=True)
class GroundTruthLine:
    start: np.ndarray
    end: np.ndarray

    @property
    def center(self) -> np.ndarray:
        return 0.5 * (self.start + self.end)

    @property
    def model(self) -> LineModel:
        return line_from_two_points(self.start, self.end)


@dataclass(frozen=True)
class SimulationCase:
    name: str
    noise_sigma: float
    outlier_ratio: float
    jitter_sigma: float


@dataclass(frozen=True)
class ExperimentMetrics:
    algorithm: str
    case_name: str
    trial: int
    runtime_ms: float
    precision: float
    recall: float
    f1: float
    mean_angle_error_deg: float
    mean_distance_error: float
    detected_count: int
    truth_count: int
    matched_count: int


@dataclass(frozen=True)
class MatchResult:
    matched_count: int
    angle_errors_deg: list[float]
    distance_errors: list[float]


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < EPS:
        return vector.astype(float)
    return vector / norm


def line_from_two_points(point_a: np.ndarray, point_b: np.ndarray) -> LineModel:
    direction = point_b - point_a
    direction = _normalize_vector(direction)
    if np.linalg.norm(direction) < EPS:
        direction = np.array([1.0, 0.0], dtype=float)
    normal = np.array([-direction[1], direction[0]], dtype=float)
    normal = _normalize_vector(normal)
    c = -float(np.dot(normal, point_a))
    return canonicalize_line(LineModel(normal[0], normal[1], c, point_a.copy(), direction))


def canonicalize_line(model: LineModel) -> LineModel:
    normal = np.array([model.a, model.b], dtype=float)
    normal = _normalize_vector(normal)
    if normal[0] < -EPS or (abs(normal[0]) <= EPS and normal[1] < 0.0):
        normal *= -1.0
        c = -model.c
    else:
        c = model.c
    direction = _normalize_vector(np.array([-normal[1], normal[0]], dtype=float))
    point = model.point.astype(float)
    return LineModel(float(normal[0]), float(normal[1]), float(c), point, direction)


def fit_line_tls(points: np.ndarray) -> LineModel:
    centroid = np.mean(points, axis=0)
    centered = points - centroid
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    direction = _normalize_vector(vt[0])
    if np.linalg.norm(direction) < EPS:
        direction = np.array([1.0, 0.0], dtype=float)
    normal = np.array([-direction[1], direction[0]], dtype=float)
    normal = _normalize_vector(normal)
    c = -float(np.dot(normal, centroid))
    return canonicalize_line(LineModel(normal[0], normal[1], c, centroid, direction))


def point_line_distances(points: np.ndarray, model: LineModel) -> np.ndarray:
    return np.abs(points[:, 0] * model.a + points[:, 1] * model.b + model.c)


def project_onto_line(points: np.ndarray, model: LineModel) -> np.ndarray:
    return (points - model.point) @ model.direction


def segment_endpoints(points: np.ndarray, model: LineModel) -> tuple[np.ndarray, np.ndarray]:
    projection = project_onto_line(points, model)
    start = model.point + np.min(projection) * model.direction
    end = model.point + np.max(projection) * model.direction
    return start, end


def build_detected_line(points: np.ndarray, indices: Iterable[int], score: float) -> DetectedLine:
    index_array = np.array(sorted(set(int(i) for i in indices)), dtype=int)
    line_points = points[index_array]
    model = fit_line_tls(line_points)
    start_point, end_point = segment_endpoints(line_points, model)
    return DetectedLine(model, index_array, start_point, end_point, score)


def line_orientation_deg(model: LineModel) -> float:
    angle = math.degrees(math.atan2(model.direction[1], model.direction[0]))
    if angle < 0.0:
        angle += 180.0
    return angle


def orientation_difference_deg(first: LineModel, second: LineModel) -> float:
    delta = abs(line_orientation_deg(first) - line_orientation_deg(second))
    return min(delta, 180.0 - delta)


def line_offset_distance(first: LineModel, second: LineModel, reference_point: np.ndarray) -> float:
    return abs(first.a * reference_point[0] + first.b * reference_point[1] + first.c)


def split_by_spatial_gap(points: np.ndarray, gap_threshold: float) -> list[np.ndarray]:
    if len(points) == 0:
        return []
    if len(points) == 1:
        return [np.array([0], dtype=int)]
    consecutive_distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    boundaries = np.where(consecutive_distances > gap_threshold)[0] + 1
    ranges = np.split(np.arange(len(points), dtype=int), boundaries)
    return [chunk for chunk in ranges if len(chunk) > 0]


def merge_collinear_segments(
    points: np.ndarray,
    segments: list[np.ndarray],
    angle_threshold_deg: float,
    distance_threshold: float,
) -> list[np.ndarray]:
    if not segments:
        return []
    merged = [np.array(sorted(set(segments[0].tolist())), dtype=int)]
    for candidate in segments[1:]:
        candidate = np.array(sorted(set(candidate.tolist())), dtype=int)
        current = merged[-1]
        current_line = fit_line_tls(points[current])
        candidate_line = fit_line_tls(points[candidate])
        angle_diff = orientation_difference_deg(current_line, candidate_line)
        reference_point = np.mean(points[candidate], axis=0)
        distance_diff = line_offset_distance(current_line, candidate_line, reference_point)
        combined_indices = np.array(sorted(set(current.tolist() + candidate.tolist())), dtype=int)
        combined_line = fit_line_tls(points[combined_indices])
        combined_error = float(np.mean(point_line_distances(points[combined_indices], combined_line)))
        if angle_diff <= angle_threshold_deg and distance_diff <= distance_threshold and combined_error <= distance_threshold:
            merged[-1] = combined_indices
        else:
            merged.append(candidate)
    return merged


def split_and_merge(
    points: np.ndarray,
    split_threshold: float = 0.10,
    merge_angle_threshold_deg: float = 6.0,
    merge_distance_threshold: float = 0.08,
    min_segment_points: int = 12,
    gap_threshold: float = 0.55,
) -> list[DetectedLine]:
    def recurse(sequence_indices: np.ndarray) -> list[np.ndarray]:
        start = int(sequence_indices[0])
        end = int(sequence_indices[-1])
        if end - start + 1 < min_segment_points:
            return []
        local_points = points[sequence_indices]
        endpoint_model = line_from_two_points(local_points[0], local_points[-1])
        distances = point_line_distances(local_points, endpoint_model)
        if len(distances) <= 2:
            return [sequence_indices]
        local_index = int(np.argmax(distances))
        max_distance = float(distances[local_index])
        if max_distance > split_threshold:
            left = sequence_indices[: local_index + 1]
            right = sequence_indices[local_index:]
            if len(left) >= min_segment_points and len(right) >= min_segment_points:
                return recurse(left) + recurse(right)
        return [sequence_indices]

    all_segments: list[np.ndarray] = []
    for chunk in split_by_spatial_gap(points, gap_threshold):
        if len(chunk) < min_segment_points:
            continue
        raw_segments = recurse(chunk)
        merged_segments = merge_collinear_segments(points, raw_segments, merge_angle_threshold_deg, merge_distance_threshold)
        all_segments.extend(merged_segments)
    return [build_detected_line(points, indices, score=float(len(indices))) for indices in all_segments if len(indices) >= min_segment_points]


def line_regression(
    points: np.ndarray,
    residual_threshold: float = 0.08,
    min_segment_points: int = 12,
    merge_angle_threshold_deg: float = 5.0,
    merge_distance_threshold: float = 0.08,
    gap_threshold: float = 0.55,
) -> list[DetectedLine]:
    all_segments: list[np.ndarray] = []
    for chunk in split_by_spatial_gap(points, gap_threshold):
        if len(chunk) < min_segment_points:
            continue
        segments: list[np.ndarray] = []
        start = 0
        total_points = len(chunk)
        while start + min_segment_points <= total_points:
            end = start + min_segment_points
            best_end = end
            while end <= total_points:
                current_indices = chunk[start:end]
                model = fit_line_tls(points[current_indices])
                residual = float(np.mean(point_line_distances(points[current_indices], model)))
                if residual <= residual_threshold:
                    best_end = end
                    end += 1
                else:
                    break
            if best_end - start >= min_segment_points:
                segments.append(chunk[start:best_end])
                start = best_end
            else:
                start += 1
        merged_segments = merge_collinear_segments(points, segments, merge_angle_threshold_deg, merge_distance_threshold)
        all_segments.extend(merged_segments)
    return [build_detected_line(points, indices, score=float(len(indices))) for indices in all_segments if len(indices) >= min_segment_points]


def ransac_line_extraction(
    points: np.ndarray,
    distance_threshold: float = 0.10,
    min_inliers: int = 28,
    max_iterations: int = 300,
    max_lines: int = 6,
    rng: np.random.Generator | None = None,
) -> list[DetectedLine]:
    rng = rng or np.random.default_rng(0)
    remaining_indices = np.arange(len(points), dtype=int)
    detections: list[DetectedLine] = []
    while len(remaining_indices) >= min_inliers and len(detections) < max_lines:
        best_indices: np.ndarray | None = None
        best_error = float("inf")
        remaining_points = points[remaining_indices]
        for _ in range(max_iterations):
            sample_positions = rng.choice(len(remaining_points), size=2, replace=False)
            sample_points = remaining_points[sample_positions]
            if np.linalg.norm(sample_points[0] - sample_points[1]) < EPS:
                continue
            model = line_from_two_points(sample_points[0], sample_points[1])
            distances = point_line_distances(remaining_points, model)
            inlier_mask = distances <= distance_threshold
            inlier_indices = remaining_indices[inlier_mask]
            if len(inlier_indices) < min_inliers:
                continue
            refined_model = fit_line_tls(points[inlier_indices])
            refined_distances = point_line_distances(points[inlier_indices], refined_model)
            error = float(np.mean(refined_distances))
            if best_indices is None or len(inlier_indices) > len(best_indices) or (
                len(inlier_indices) == len(best_indices) and error < best_error
            ):
                best_indices = inlier_indices
                best_error = error
        if best_indices is None:
            break
        detections.append(build_detected_line(points, best_indices, score=float(len(best_indices))))
        keep_mask = ~np.isin(remaining_indices, best_indices)
        remaining_indices = remaining_indices[keep_mask]
    return detections


def hough_transform_extraction(
    points: np.ndarray,
    distance_threshold: float = 0.12,
    theta_bins: int = 180,
    rho_bins: int = 180,
    min_votes: int = 26,
    max_lines: int = 6,
    suppression_radius: int = 8,
) -> list[DetectedLine]:
    theta_values = np.linspace(-math.pi / 2.0, math.pi / 2.0, theta_bins, endpoint=False)
    cos_values = np.cos(theta_values)
    sin_values = np.sin(theta_values)
    rho_max = float(np.linalg.norm(np.max(np.abs(points), axis=0))) + 1.0
    rho_values = np.linspace(-rho_max, rho_max, rho_bins)
    accumulator = np.zeros((theta_bins, rho_bins), dtype=int)
    for point in points:
        rhos = point[0] * cos_values + point[1] * sin_values
        rho_indices = np.clip(np.searchsorted(rho_values, rhos), 0, rho_bins - 1)
        accumulator[np.arange(theta_bins), rho_indices] += 1

    detections: list[DetectedLine] = []
    used_mask = np.zeros(len(points), dtype=bool)
    local_accumulator = accumulator.copy()
    for _ in range(max_lines):
        peak_index = np.unravel_index(np.argmax(local_accumulator), local_accumulator.shape)
        peak_votes = int(local_accumulator[peak_index])
        if peak_votes < min_votes:
            break
        theta_idx, rho_idx = peak_index
        theta = theta_values[theta_idx]
        rho = rho_values[rho_idx]
        normal = np.array([math.cos(theta), math.sin(theta)], dtype=float)
        direction = np.array([-normal[1], normal[0]], dtype=float)
        anchor = normal * rho
        model = canonicalize_line(LineModel(normal[0], normal[1], -rho, anchor, direction))
        available_indices = np.where(~used_mask)[0]
        distances = point_line_distances(points[available_indices], model)
        inlier_indices = available_indices[distances <= distance_threshold]
        if len(inlier_indices) >= min_votes:
            detections.append(build_detected_line(points, inlier_indices, score=float(peak_votes)))
            used_mask[inlier_indices] = True
        theta_start = max(0, theta_idx - suppression_radius)
        theta_end = min(theta_bins, theta_idx + suppression_radius + 1)
        rho_start = max(0, rho_idx - suppression_radius)
        rho_end = min(rho_bins, rho_idx + suppression_radius + 1)
        local_accumulator[theta_start:theta_end, rho_start:rho_end] = 0
    return detections


def make_ground_truth_lines() -> list[GroundTruthLine]:
    return [
        GroundTruthLine(np.array([0.6, 0.8], dtype=float), np.array([4.8, 2.4], dtype=float)),
        GroundTruthLine(np.array([0.9, 4.8], dtype=float), np.array([5.6, 4.1], dtype=float)),
        GroundTruthLine(np.array([5.7, 0.7], dtype=float), np.array([2.7, 5.3], dtype=float)),
    ]


def simulate_point_cloud(
    rng: np.random.Generator,
    case: SimulationCase,
    points_per_line: int = 70,
    bounds: tuple[float, float] = (0.0, 6.0),
) -> tuple[np.ndarray, np.ndarray, list[GroundTruthLine]]:
    truth_lines = make_ground_truth_lines()
    points = []
    labels = []
    for line_index, truth in enumerate(truth_lines):
        t = np.sort(rng.uniform(0.0, 1.0, size=points_per_line))
        line_points = truth.start + np.outer(t, truth.end - truth.start)
        direction = _normalize_vector(truth.end - truth.start)
        normal = np.array([-direction[1], direction[0]], dtype=float)
        along_noise = rng.normal(0.0, case.jitter_sigma, size=(points_per_line, 1)) * direction
        normal_noise = rng.normal(0.0, case.noise_sigma, size=(points_per_line, 1)) * normal
        noisy_points = line_points + along_noise + normal_noise
        points.append(noisy_points)
        labels.append(np.full(points_per_line, line_index, dtype=int))

    stacked_points = np.vstack(points)
    stacked_labels = np.concatenate(labels)
    outlier_count = int(case.outlier_ratio * len(stacked_points))
    outliers = rng.uniform(bounds[0], bounds[1], size=(outlier_count, 2))
    stacked_points = np.vstack([stacked_points, outliers])
    stacked_labels = np.concatenate([stacked_labels, np.full(outlier_count, -1, dtype=int)])

    order = np.lexsort((stacked_points[:, 0], stacked_labels == -1, stacked_labels))
    ordered_points = stacked_points[order]
    ordered_labels = stacked_labels[order]
    return ordered_points, ordered_labels, truth_lines


def evaluate_detections(
    truth_lines: list[GroundTruthLine],
    detections: list[DetectedLine],
    angle_threshold_deg: float = 8.0,
    distance_threshold: float = 0.18,
) -> MatchResult:
    remaining_detection_indices = set(range(len(detections)))
    matches = 0
    angle_errors: list[float] = []
    distance_errors: list[float] = []
    for truth in truth_lines:
        best_index = None
        best_score = float("inf")
        for detection_index in list(remaining_detection_indices):
            detection = detections[detection_index]
            angle_error = orientation_difference_deg(truth.model, detection.model)
            distance_error = line_offset_distance(detection.model, truth.model, truth.center)
            if angle_error <= angle_threshold_deg and distance_error <= distance_threshold:
                score = angle_error + 10.0 * distance_error
                if score < best_score:
                    best_score = score
                    best_index = detection_index
        if best_index is None:
            continue
        remaining_detection_indices.remove(best_index)
        best_detection = detections[best_index]
        matches += 1
        angle_errors.append(orientation_difference_deg(truth.model, best_detection.model))
        distance_errors.append(line_offset_distance(best_detection.model, truth.model, truth.center))
    return MatchResult(matches, angle_errors, distance_errors)


def run_algorithm(
    algorithm_name: str,
    points: np.ndarray,
    rng: np.random.Generator,
) -> tuple[list[DetectedLine], float]:
    methods: dict[str, Callable[[], list[DetectedLine]]] = {
        "Split-and-Merge": lambda: split_and_merge(points),
        "Line-Regression": lambda: line_regression(points),
        "RANSAC": lambda: ransac_line_extraction(points, rng=rng),
        "Hough-Transform": lambda: hough_transform_extraction(points),
    }
    start = time.perf_counter()
    detections = methods[algorithm_name]()
    runtime_ms = (time.perf_counter() - start) * 1000.0
    return detections, runtime_ms


def compute_metrics(
    algorithm_name: str,
    case_name: str,
    trial: int,
    truth_lines: list[GroundTruthLine],
    detections: list[DetectedLine],
    runtime_ms: float,
) -> ExperimentMetrics:
    match_result = evaluate_detections(truth_lines, detections)
    precision = match_result.matched_count / len(detections) if detections else 0.0
    recall = match_result.matched_count / len(truth_lines) if truth_lines else 0.0
    if precision + recall > 0.0:
        f1 = 2.0 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    mean_angle = float(np.mean(match_result.angle_errors_deg)) if match_result.angle_errors_deg else float("nan")
    mean_distance = float(np.mean(match_result.distance_errors)) if match_result.distance_errors else float("nan")
    return ExperimentMetrics(
        algorithm=algorithm_name,
        case_name=case_name,
        trial=trial,
        runtime_ms=runtime_ms,
        precision=precision,
        recall=recall,
        f1=f1,
        mean_angle_error_deg=mean_angle,
        mean_distance_error=mean_distance,
        detected_count=len(detections),
        truth_count=len(truth_lines),
        matched_count=match_result.matched_count,
    )
