from dataclasses import dataclass
from math import atan2, cos, degrees, pi, sin, sqrt, tan
from random import Random


@dataclass
class Pose:
    x: float
    y: float
    theta: float


@dataclass
class NoiseModel:
    sigma_s: float
    sigma_delta: float


@dataclass
class CheckpointResult:
    time: float
    sigma_x_theory: float
    sigma_y_theory: float
    sigma_theta_theory: float
    sigma_x_mc: float
    sigma_y_mc: float
    sigma_theta_mc: float
    mean_x_error_mc: float
    mean_y_error_mc: float
    mean_theta_error_mc: float


WHEEL_BASE = 2.0
DT = 0.05
TOTAL_TIME = 25.0
MONTE_CARLO_RUNS = 1200
CHECKPOINT_TIMES = [5.0, 10.0, 15.0, 20.0, 25.0]
NOISE = NoiseModel(sigma_s=0.004, sigma_delta=0.35 * pi / 180.0)


def wrap_to_pi(angle: float) -> float:
    return atan2(sin(angle), cos(angle))


def zeros_3x3() -> list[list[float]]:
    return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]


def transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(row) for row in zip(*matrix)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    rows = len(a)
    cols = len(b[0])
    inner = len(b)
    result = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            result[i][j] = sum(a[i][k] * b[k][j] for k in range(inner))
    return result


def matadd(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [
        [a[i][j] + b[i][j] for j in range(len(a[0]))]
        for i in range(len(a))
    ]


def command_profile(t: float) -> tuple[float, float]:
    v = 0.75 + 0.10 * cos(0.30 * t)
    delta = 0.18 * sin(0.22 * t) + 0.06 * cos(0.11 * t)
    return v, delta


def odometry_step(pose: Pose, ds: float, delta: float, wheel_base: float) -> Pose:
    kappa = tan(delta) / wheel_base
    dtheta = ds * kappa
    heading_mid = pose.theta + 0.5 * dtheta
    x_next = pose.x + ds * cos(heading_mid)
    y_next = pose.y + ds * sin(heading_mid)
    theta_next = wrap_to_pi(pose.theta + dtheta)
    return Pose(x_next, y_next, theta_next)


def odometry_jacobians(
    pose: Pose, ds: float, delta: float, wheel_base: float
) -> tuple[list[list[float]], list[list[float]]]:
    kappa = tan(delta) / wheel_base
    gamma = 1.0 / (cos(delta) ** 2 * wheel_base)
    dtheta = ds * kappa
    heading_mid = pose.theta + 0.5 * dtheta

    f = [
        [1.0, 0.0, -ds * sin(heading_mid)],
        [0.0, 1.0, ds * cos(heading_mid)],
        [0.0, 0.0, 1.0],
    ]

    g = [
        [
            cos(heading_mid) - 0.5 * ds * kappa * sin(heading_mid),
            -0.5 * ds * ds * gamma * sin(heading_mid),
        ],
        [
            sin(heading_mid) + 0.5 * ds * kappa * cos(heading_mid),
            0.5 * ds * ds * gamma * cos(heading_mid),
        ],
        [kappa, ds * gamma],
    ]
    return f, g


def process_covariance(ds: float, noise: NoiseModel) -> list[list[float]]:
    sigma_s = noise.sigma_s + 0.01 * abs(ds)
    sigma_delta = noise.sigma_delta
    return [
        [sigma_s**2, 0.0],
        [0.0, sigma_delta**2],
    ]


def propagate_covariance(
    covariance: list[list[float]],
    pose: Pose,
    ds: float,
    delta: float,
    wheel_base: float,
    noise: NoiseModel,
) -> list[list[float]]:
    f, g = odometry_jacobians(pose, ds, delta, wheel_base)
    q = process_covariance(ds, noise)
    return matadd(matmul(matmul(f, covariance), transpose(f)), matmul(matmul(g, q), transpose(g)))


def nominal_run() -> tuple[list[tuple[float, float]], list[Pose], list[list[list[float]]], float]:
    controls: list[tuple[float, float]] = []
    poses = [Pose(0.0, 0.0, 0.0)]
    covariances = [zeros_3x3()]
    exact_reference = Pose(0.0, 0.0, 0.0)
    odometry_reference = Pose(0.0, 0.0, 0.0)
    t = 0.0
    max_consistency_error = 0.0

    while t < TOTAL_TIME - 1e-12:
        v, delta = command_profile(t)
        ds = v * DT
        controls.append((ds, delta))
        exact_reference = odometry_step(exact_reference, ds, delta, WHEEL_BASE)
        covariance_next = propagate_covariance(
            covariances[-1], odometry_reference, ds, delta, WHEEL_BASE, NOISE
        )
        odometry_reference = odometry_step(odometry_reference, ds, delta, WHEEL_BASE)
        poses.append(odometry_reference)
        covariances.append(covariance_next)
        consistency_error = sqrt(
            (exact_reference.x - odometry_reference.x) ** 2
            + (exact_reference.y - odometry_reference.y) ** 2
        ) + abs(wrap_to_pi(exact_reference.theta - odometry_reference.theta))
        max_consistency_error = max(max_consistency_error, consistency_error)
        t += DT

    return controls, poses, covariances, max_consistency_error


def checkpoint_indices() -> list[int]:
    return [int(round(time_value / DT)) for time_value in CHECKPOINT_TIMES]


def error_vector(sample_pose: Pose, nominal_pose: Pose) -> list[float]:
    return [
        sample_pose.x - nominal_pose.x,
        sample_pose.y - nominal_pose.y,
        wrap_to_pi(sample_pose.theta - nominal_pose.theta),
    ]


def sample_mean(data: list[list[float]]) -> list[float]:
    count = len(data)
    dims = len(data[0])
    return [sum(row[i] for row in data) / count for i in range(dims)]


def sample_covariance(data: list[list[float]], mean: list[float]) -> list[list[float]]:
    dims = len(mean)
    count = len(data)
    covariance = [[0.0 for _ in range(dims)] for _ in range(dims)]
    for row in data:
        diff = [row[i] - mean[i] for i in range(dims)]
        for i in range(dims):
            for j in range(dims):
                covariance[i][j] += diff[i] * diff[j]
    scale = 1.0 / (count - 1)
    for i in range(dims):
        for j in range(dims):
            covariance[i][j] *= scale
    return covariance


def monte_carlo_validation(
    controls: list[tuple[float, float]],
    nominal_poses: list[Pose],
) -> list[CheckpointResult]:
    rng = Random(7)
    indices = checkpoint_indices()
    buffers = {index: [] for index in indices}

    for _ in range(MONTE_CARLO_RUNS):
        pose = Pose(0.0, 0.0, 0.0)
        for step_index, (ds_nominal, delta_nominal) in enumerate(controls, start=1):
            q = process_covariance(ds_nominal, NOISE)
            ds_noisy = ds_nominal + rng.gauss(0.0, sqrt(q[0][0]))
            delta_noisy = delta_nominal + rng.gauss(0.0, sqrt(q[1][1]))
            pose = odometry_step(pose, ds_noisy, delta_noisy, WHEEL_BASE)
            if step_index in buffers:
                buffers[step_index].append(error_vector(pose, nominal_poses[step_index]))

    results: list[CheckpointResult] = []
    for time_value, index in zip(CHECKPOINT_TIMES, indices):
        errors = buffers[index]
        mean = sample_mean(errors)
        covariance = sample_covariance(errors, mean)
        results.append(
            CheckpointResult(
                time=time_value,
                sigma_x_theory=0.0,
                sigma_y_theory=0.0,
                sigma_theta_theory=0.0,
                sigma_x_mc=sqrt(covariance[0][0]),
                sigma_y_mc=sqrt(covariance[1][1]),
                sigma_theta_mc=sqrt(covariance[2][2]),
                mean_x_error_mc=mean[0],
                mean_y_error_mc=mean[1],
                mean_theta_error_mc=mean[2],
            )
        )
    return results


def merge_theory_and_mc(
    covariances: list[list[list[float]]],
    results: list[CheckpointResult],
) -> list[CheckpointResult]:
    indices = checkpoint_indices()
    merged: list[CheckpointResult] = []
    for result, index in zip(results, indices):
        covariance = covariances[index]
        merged.append(
            CheckpointResult(
                time=result.time,
                sigma_x_theory=sqrt(covariance[0][0]),
                sigma_y_theory=sqrt(covariance[1][1]),
                sigma_theta_theory=sqrt(covariance[2][2]),
                sigma_x_mc=result.sigma_x_mc,
                sigma_y_mc=result.sigma_y_mc,
                sigma_theta_mc=result.sigma_theta_mc,
                mean_x_error_mc=result.mean_x_error_mc,
                mean_y_error_mc=result.mean_y_error_mc,
                mean_theta_error_mc=result.mean_theta_error_mc,
            )
        )
    return merged


def relative_gap(theory: float, experiment: float) -> float:
    if theory < 1e-12:
        return 0.0
    return abs(experiment - theory) / theory


def print_report(
    nominal_poses: list[Pose],
    covariances: list[list[list[float]]],
    max_consistency_error: float,
    results: list[CheckpointResult],
) -> None:
    final_pose = nominal_poses[-1]
    final_covariance = covariances[-1]
    avg_gap_x = sum(relative_gap(item.sigma_x_theory, item.sigma_x_mc) for item in results) / len(results)
    avg_gap_y = sum(relative_gap(item.sigma_y_theory, item.sigma_y_mc) for item in results) / len(results)
    avg_gap_theta = sum(relative_gap(item.sigma_theta_theory, item.sigma_theta_mc) for item in results) / len(results)

    print("叉车式移动机器人里程计模型与误差传导仿真")
    print("")
    print("1. 叉车里程计模型")
    print("状态取 z = [x, y, theta]^T，输入取 u = [ds, delta]^T。")
    print("其中 ds 为驱动轮在采样周期内的弧长增量，delta 为转向角，L 为轴距。")
    print("采用中点积分形式的里程计更新：")
    print("  kappa = tan(delta) / L")
    print("  dtheta = ds * kappa")
    print("  x(k+1) = x(k) + ds * cos(theta(k) + dtheta / 2)")
    print("  y(k+1) = y(k) + ds * sin(theta(k) + dtheta / 2)")
    print("  theta(k+1) = theta(k) + dtheta")
    print("")
    print("2. 误差传导模型")
    print("对离散模型一阶线性化，得到：")
    print("  e(k+1) = F(k) e(k) + G(k) w(k)")
    print("  P(k+1) = F(k) P(k) F(k)^T + G(k) Q(k) G(k)^T")
    print("其中 w = [n_s, n_delta]^T 分别表示里程增量噪声和转角噪声。")
    print("")
    print("3. 仿真参数")
    print(f"轴距 L = {WHEEL_BASE:.2f} m, 采样周期 dt = {DT:.2f} s, 总时长 = {TOTAL_TIME:.1f} s")
    print(f"里程噪声标准差 = {NOISE.sigma_s:.4f} m + 1%|ds|, 转角噪声标准差 = {degrees(NOISE.sigma_delta):.3f} deg")
    print(f"Monte Carlo 次数 = {MONTE_CARLO_RUNS}")
    print("")
    print("4. 无噪声一致性检验")
    print(f"名义里程计与名义运动模型的最大一致性误差 = {max_consistency_error:.6e}")
    print(f"最终名义位姿 = ({final_pose.x:.3f}, {final_pose.y:.3f}, {final_pose.theta:.3f})")
    print("")
    print("5. 理论协方差与 Monte Carlo 对比")
    print(
        "t(s)  sig_x_theory  sig_x_mc  sig_y_theory  sig_y_mc  "
        "sig_theta_theory  sig_theta_mc  mean_ex_mc  mean_ey_mc  mean_eth_mc"
    )
    for item in results:
        print(
            f"{item.time:>4.1f}  {item.sigma_x_theory:>12.4f}  {item.sigma_x_mc:>8.4f}  "
            f"{item.sigma_y_theory:>12.4f}  {item.sigma_y_mc:>8.4f}  "
            f"{item.sigma_theta_theory:>16.4f}  {item.sigma_theta_mc:>12.4f}  "
            f"{item.mean_x_error_mc:>10.4f}  {item.mean_y_error_mc:>10.4f}  {item.mean_theta_error_mc:>11.4f}"
        )
    print("")
    print("6. 结果分析")
    print(f"x 方向平均标准差相对偏差 = {100.0 * avg_gap_x:.2f}%")
    print(f"y 方向平均标准差相对偏差 = {100.0 * avg_gap_y:.2f}%")
    print(f"航向方向平均标准差相对偏差 = {100.0 * avg_gap_theta:.2f}%")
    print(f"最终理论 3sigma 范围约为 x:{3.0 * sqrt(final_covariance[0][0]):.3f} m, y:{3.0 * sqrt(final_covariance[1][1]):.3f} m, theta:{degrees(3.0 * sqrt(final_covariance[2][2])):.3f} deg")
    print("若理论标准差与 Monte Carlo 样本标准差接近，且均值误差接近 0，则说明误差传导模型正确。")


def main() -> None:
    controls, nominal_poses, covariances, max_consistency_error = nominal_run()
    mc_results = monte_carlo_validation(controls, nominal_poses)
    merged_results = merge_theory_and_mc(covariances, mc_results)
    print_report(nominal_poses, covariances, max_consistency_error, merged_results)


if __name__ == "__main__":
    main()
