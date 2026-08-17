from dataclasses import dataclass
from math import atan, atan2, cos, pi, sin, sqrt, tan


@dataclass
class RobotState:
    x: float
    y: float
    theta: float


@dataclass
class ControlInput:
    v: float
    omega: float
    delta: float


@dataclass
class SimulationMetrics:
    final_position_error: float
    final_heading_error: float
    rms_position_error: float
    max_position_error: float
    max_steering_angle_deg: float


WHEEL_BASE = 2.0
DT = 0.01
TOTAL_TIME = 40.0
KX = 1.2
KY = 2.0
KTHETA = 2.5
MAX_STEERING = 0.75


def wrap_to_pi(angle: float) -> float:
    return atan2(sin(angle), cos(angle))


def reference_trajectory(t: float) -> tuple[RobotState, float, float]:
    vr = 0.8
    omega_r = 0.16
    theta_r = omega_r * t
    xr = 5.0 * sin(theta_r)
    yr = 5.0 * (1.0 - cos(theta_r))
    return RobotState(xr, yr, theta_r), vr, omega_r


def transform_error_to_robot_frame(
    reference: RobotState, actual: RobotState
) -> tuple[float, float, float]:
    dx = reference.x - actual.x
    dy = reference.y - actual.y
    ex = cos(actual.theta) * dx + sin(actual.theta) * dy
    ey = -sin(actual.theta) * dx + cos(actual.theta) * dy
    etheta = wrap_to_pi(reference.theta - actual.theta)
    return ex, ey, etheta


def controller(ex: float, ey: float, etheta: float, vr: float, omega_r: float) -> ControlInput:
    v = vr * cos(etheta) + KX * ex
    omega = omega_r + vr * (KY * ey + KTHETA * sin(etheta))
    if abs(v) < 1e-6:
        delta = 0.0
    else:
        delta = atan(WHEEL_BASE * omega / v)
    if delta > MAX_STEERING:
        delta = MAX_STEERING
    if delta < -MAX_STEERING:
        delta = -MAX_STEERING
    omega = v * tan(delta) / WHEEL_BASE
    return ControlInput(v, omega, delta)


def propagate(state: RobotState, control: ControlInput, dt: float) -> RobotState:
    x = state.x + control.v * cos(state.theta) * dt
    y = state.y + control.v * sin(state.theta) * dt
    theta = wrap_to_pi(state.theta + control.omega * dt)
    return RobotState(x, y, theta)


def run_simulation() -> tuple[SimulationMetrics, list[dict[str, float]]]:
    state = RobotState(-1.5, -2.0, -0.6)
    samples: list[dict[str, float]] = []
    t = 0.0
    squared_error_sum = 0.0
    max_position_error = 0.0
    max_steering = 0.0

    while t <= TOTAL_TIME + 1e-9:
        reference, vr, omega_r = reference_trajectory(t)
        ex, ey, etheta = transform_error_to_robot_frame(reference, state)
        control = controller(ex, ey, etheta, vr, omega_r)
        position_error = sqrt((reference.x - state.x) ** 2 + (reference.y - state.y) ** 2)
        squared_error_sum += position_error ** 2
        max_position_error = max(max_position_error, position_error)
        max_steering = max(max_steering, abs(control.delta))
        if int(round(t / DT)) % 200 == 0:
            samples.append(
                {
                    "t": round(t, 2),
                    "x": state.x,
                    "y": state.y,
                    "theta": state.theta,
                    "xr": reference.x,
                    "yr": reference.y,
                    "theta_r": reference.theta,
                    "ex": ex,
                    "ey": ey,
                    "etheta": etheta,
                    "v": control.v,
                    "omega": control.omega,
                    "delta_deg": control.delta * 180.0 / pi,
                    "position_error": position_error,
                }
            )
        state = propagate(state, control, DT)
        t += DT

    reference, _, _ = reference_trajectory(TOTAL_TIME)
    final_position_error = sqrt((reference.x - state.x) ** 2 + (reference.y - state.y) ** 2)
    final_heading_error = abs(wrap_to_pi(reference.theta - state.theta))
    metrics = SimulationMetrics(
        final_position_error=final_position_error,
        final_heading_error=final_heading_error,
        rms_position_error=sqrt(squared_error_sum / (TOTAL_TIME / DT + 1.0)),
        max_position_error=max_position_error,
        max_steering_angle_deg=max_steering * 180.0 / pi,
    )
    return metrics, samples


def print_report(metrics: SimulationMetrics, samples: list[dict[str, float]]) -> None:
    print("三轮叉车式移动机器人轨迹跟踪仿真")
    print(f"轴距 L = {WHEEL_BASE:.2f} m")
    print(f"控制增益: kx = {KX:.2f}, ky = {KY:.2f}, ktheta = {KTHETA:.2f}")
    print(f"最终位置误差 = {metrics.final_position_error:.4f} m")
    print(f"最终航向误差 = {metrics.final_heading_error:.4f} rad")
    print(f"位置误差 RMS = {metrics.rms_position_error:.4f} m")
    print(f"最大位置误差 = {metrics.max_position_error:.4f} m")
    print(f"最大转角 = {metrics.max_steering_angle_deg:.2f} deg")
    print("")
    print("关键采样点")
    print(
        "t(s)    x(m)    y(m)    theta(rad)    xr(m)    yr(m)    ex(m)    ey(m)    "
        "etheta(rad)    v(m/s)    omega(rad/s)    delta(deg)    ep(m)"
    )
    for sample in samples:
        print(
            f"{sample['t']:>4.1f}  {sample['x']:>6.3f}  {sample['y']:>6.3f}  "
            f"{sample['theta']:>10.3f}  {sample['xr']:>6.3f}  {sample['yr']:>6.3f}  "
            f"{sample['ex']:>6.3f}  {sample['ey']:>6.3f}  {sample['etheta']:>11.3f}  "
            f"{sample['v']:>8.3f}  {sample['omega']:>14.3f}  {sample['delta_deg']:>11.3f}  "
            f"{sample['position_error']:>6.3f}"
        )


if __name__ == "__main__":
    metrics, samples = run_simulation()
    print_report(metrics, samples)
