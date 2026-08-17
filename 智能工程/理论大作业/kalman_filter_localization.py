"""
基于卡尔曼滤波的机器人定位算法
================================

实现扩展卡尔曼滤波(EKF)用于机器人定位，结合：
1. 运动模型预测（里程计）
2. 观测模型更新（激光雷达特征）
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class Landmark:
    x: float
    y: float
    feature_type: str = "point"
    length: float = 0.0
    angle: float = 0.0


@dataclass
class Observation:
    landmark_id: int
    range_dist: float
    bearing: float
    feature_type: str = "point"


class ExtendedKalmanFilter:
    """
    扩展卡尔曼滤波器用于机器人定位
    
    状态向量: x = [x, y, θ]^T
    - (x, y): 机器人位置
    - θ: 机器人航向角
    
    控制输入: u = [v, δ]^T
    - v: 后轴速度
    - δ: 转向角
    """
    
    def __init__(self, wheel_base: float = 2.0):
        self.wheel_base = wheel_base
        self.state = np.zeros(3)
        self.covariance = np.eye(3) * 0.01
        
        self.process_noise = np.diag([0.05**2, 0.02**2])
        self.measurement_noise = np.diag([0.1**2, 0.05**2])
        
    def set_state(self, x: float, y: float, theta: float):
        self.state = np.array([x, y, theta])
        
    def set_covariance(self, cov: np.ndarray):
        self.covariance = cov.copy()
        
    def motion_model(self, state: np.ndarray, v: float, delta: float, dt: float) -> np.ndarray:
        """
        运动模型
        
        状态转移方程:
        x' = x + v*cos(θ)*dt
        y' = y + v*sin(θ)*dt
        θ' = θ + v*tan(δ)/L*dt
        """
        x, y, theta = state
        
        if abs(delta) < 1e-6:
            new_x = x + v * np.cos(theta) * dt
            new_y = y + v * np.sin(theta) * dt
            new_theta = theta
        else:
            R = self.wheel_base / np.tan(delta)
            omega = v / R
            dtheta = omega * dt
            
            new_x = x + R * (np.sin(theta + dtheta) - np.sin(theta))
            new_y = y + R * (-np.cos(theta + dtheta) + np.cos(theta))
            new_theta = theta + dtheta
        
        new_theta = self._wrap_to_pi(new_theta)
        return np.array([new_x, new_y, new_theta])
    
    def motion_jacobian(self, state: np.ndarray, v: float, delta: float, dt: float) -> np.ndarray:
        """
        运动模型雅可比矩阵
        
        F = ∂f/∂x
        """
        x, y, theta = state
        F = np.eye(3)
        
        if abs(delta) < 1e-6:
            F[0, 2] = -v * np.sin(theta) * dt
            F[1, 2] = v * np.cos(theta) * dt
        else:
            R = self.wheel_base / np.tan(delta)
            omega = v / R
            dtheta = omega * dt
            
            F[0, 2] = R * (np.cos(theta + dtheta) - np.cos(theta))
            F[1, 2] = R * (np.sin(theta + dtheta) - np.sin(theta))
        
        return F
    
    def control_jacobian(self, state: np.ndarray, v: float, delta: float, dt: float) -> np.ndarray:
        """
        控制输入雅可比矩阵
        
        G = ∂f/∂u
        """
        x, y, theta = state
        G = np.zeros((3, 2))
        
        if abs(delta) < 1e-6:
            G[0, 0] = np.cos(theta) * dt
            G[1, 0] = np.sin(theta) * dt
        else:
            R = self.wheel_base / np.tan(delta)
            omega = v / R
            dtheta = omega * dt
            
            G[0, 0] = (self.wheel_base / np.tan(delta)) * (np.sin(theta + dtheta) - np.sin(theta))
            G[1, 0] = (self.wheel_base / np.tan(delta)) * (-np.cos(theta + dtheta) + np.cos(theta))
            G[2, 0] = dtheta / v
            
            dR_ddelta = -self.wheel_base / (np.sin(delta)**2)
            domega_ddelta = -v * np.tan(delta) / (self.wheel_base * np.cos(delta)**2)
            ddtheta_ddelta = domega_ddelta * dt
            
            G[0, 1] = dR_ddelta * (np.sin(theta + dtheta) - np.sin(theta)) + R * np.cos(theta + dtheta) * ddtheta_ddelta
            G[1, 1] = dR_ddelta * (-np.cos(theta + dtheta) + np.cos(theta)) + R * np.sin(theta + dtheta) * ddtheta_ddelta
            G[2, 1] = ddtheta_ddelta
        
        return G
    
    def predict(self, v: float, delta: float, dt: float):
        """
        预测步骤
        
        x̂⁻ = f(x̂⁺, u)
        P⁻ = F*P⁺*F^T + G*Q*G^T
        """
        self.state = self.motion_model(self.state, v, delta, dt)
        
        F = self.motion_jacobian(self.state, v, delta, dt)
        G = self.control_jacobian(self.state, v, delta, dt)
        
        self.covariance = F @ self.covariance @ F.T + G @ self.process_noise @ G.T
        self.covariance = self._ensure_symmetric(self.covariance)
        
    def observation_model(self, state: np.ndarray, landmark: Landmark) -> np.ndarray:
        """
        观测模型
        
        z = [r, φ]^T
        r = sqrt((lx-x)^2 + (ly-y)^2)
        φ = atan2(ly-y, lx-x) - θ
        """
        x, y, theta = state
        dx = landmark.x - x
        dy = landmark.y - y
        
        r = np.sqrt(dx**2 + dy**2)
        phi = self._wrap_to_pi(np.arctan2(dy, dx) - theta)
        
        return np.array([r, phi])
    
    def observation_jacobian(self, state: np.ndarray, landmark: Landmark) -> np.ndarray:
        """
        观测模型雅可比矩阵
        
        H = ∂h/∂x
        """
        x, y, theta = state
        dx = landmark.x - x
        dy = landmark.y - y
        r = np.sqrt(dx**2 + dy**2)
        
        if r < 1e-6:
            return np.zeros((2, 3))
        
        H = np.zeros((2, 3))
        H[0, 0] = -dx / r
        H[0, 1] = -dy / r
        H[1, 0] = dy / (r**2)
        H[1, 1] = -dx / (r**2)
        H[1, 2] = -1.0
        
        return H
    
    def update(self, observations: List[Observation], landmarks: List[Landmark]):
        """
        更新步骤
        
        K = P⁻*H^T*(H*P⁻*H^T + R)^(-1)
        x̂⁺ = x̂⁻ + K*(z - h(x̂⁻))
        P⁺ = (I - K*H)*P⁻
        """
        for obs in observations:
            if obs.landmark_id >= len(landmarks):
                continue
                
            landmark = landmarks[obs.landmark_id]
            
            z_pred = self.observation_model(self.state, landmark)
            z_actual = np.array([obs.range_dist, obs.bearing])
            
            innovation = z_actual - z_pred
            innovation[1] = self._wrap_to_pi(innovation[1])
            
            H = self.observation_jacobian(self.state, landmark)
            
            S = H @ self.covariance @ H.T + self.measurement_noise
            
            try:
                K = self.covariance @ H.T @ np.linalg.inv(S)
            except np.linalg.LinAlgError:
                continue
            
            self.state = self.state + K @ innovation
            self.state[2] = self._wrap_to_pi(self.state[2])
            
            I_KH = np.eye(3) - K @ H
            self.covariance = I_KH @ self.covariance @ I_KH.T + K @ self.measurement_noise @ K.T
            self.covariance = self._ensure_symmetric(self.covariance)
    
    def get_state(self) -> Tuple[float, float, float]:
        return tuple(self.state)
    
    def get_covariance(self) -> np.ndarray:
        return self.covariance.copy()
    
    def get_uncertainty_ellipse(self, scale: float = 2.0) -> Tuple[float, float, float]:
        """
        获取不确定性椭圆参数
        
        返回: (长轴, 短轴, 角度)
        """
        eigenvalues, eigenvectors = np.linalg.eig(self.covariance[:2, :2])
        
        order = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]
        
        a = scale * np.sqrt(eigenvalues[0])
        b = scale * np.sqrt(eigenvalues[1])
        angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
        
        return (a, b, angle)
    
    @staticmethod
    def _wrap_to_pi(angle: float) -> float:
        return np.arctan2(np.sin(angle), np.cos(angle))
    
    @staticmethod
    def _ensure_symmetric(matrix: np.ndarray) -> np.ndarray:
        return (matrix + matrix.T) / 2


class KalmanFilterSimulation:
    """
    卡尔曼滤波定位仿真
    """
    
    def __init__(self, wheel_base: float = 2.0):
        self.wheel_base = wheel_base
        self.ekf = ExtendedKalmanFilter(wheel_base)
        self.landmarks: List[Landmark] = []
        self.dt = 0.05
        
    def add_landmark(self, x: float, y: float, feature_type: str = "point"):
        self.landmarks.append(Landmark(x, y, feature_type))
        
    def generate_environment(self, num_landmarks: int = 20, env_size: float = 20.0):
        """生成随机环境地标"""
        np.random.seed(42)
        for _ in range(num_landmarks):
            x = np.random.uniform(-env_size, env_size)
            y = np.random.uniform(-env_size, env_size)
            self.add_landmark(x, y)
    
    def generate_trajectory(self, total_time: float = 30.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        生成参考轨迹和控制输入
        """
        num_steps = int(total_time / self.dt)
        
        true_states = np.zeros((num_steps + 1, 3))
        controls = np.zeros((num_steps, 2))
        true_states[0] = [0, 0, 0]
        
        for i in range(num_steps):
            t = i * self.dt
            v = 0.8 + 0.2 * np.sin(0.2 * t)
            delta = 0.3 * np.sin(0.15 * t) + 0.1 * np.cos(0.1 * t)
            controls[i] = [v, delta]
            
            true_states[i+1] = self.ekf.motion_model(true_states[i], v, delta, self.dt)
        
        return true_states, controls
    
    def simulate_observations(self, true_state: np.ndarray, max_range: float = 15.0) -> List[Observation]:
        """
        模拟激光雷达观测
        """
        observations = []
        x, y, theta = true_state
        
        for i, landmark in enumerate(self.landmarks):
            dx = landmark.x - x
            dy = landmark.y - y
            r = np.sqrt(dx**2 + dy**2)
            
            if r > max_range:
                continue
            
            phi = np.arctan2(dy, dx) - theta
            phi = self.ekf._wrap_to_pi(phi)
            
            r_noisy = r + np.random.normal(0, 0.1)
            phi_noisy = phi + np.random.normal(0, 0.05)
            
            observations.append(Observation(i, r_noisy, phi_noisy))
        
        return observations
    
    def run_simulation(self, total_time: float = 30.0) -> dict:
        """
        运行完整仿真
        """
        true_states, controls = self.generate_trajectory(total_time)
        num_steps = len(controls)
        
        ekf_states = np.zeros((num_steps + 1, 3))
        ekf_covariances = np.zeros((num_steps + 1, 3, 3))
        odometry_states = np.zeros((num_steps + 1, 3))
        
        self.ekf.set_state(0, 0, 0)
        self.ekf.set_covariance(np.eye(3) * 0.01)
        ekf_states[0] = self.ekf.state
        ekf_covariances[0] = self.ekf.covariance
        odometry_states[0] = [0, 0, 0]
        
        for i in range(num_steps):
            v, delta = controls[i]
            v_noisy = v + np.random.normal(0, 0.05)
            delta_noisy = delta + np.random.normal(0, 0.02)
            
            self.ekf.predict(v_noisy, delta_noisy, self.dt)
            
            observations = self.simulate_observations(true_states[i+1])
            if observations:
                self.ekf.update(observations, self.landmarks)
            
            ekf_states[i+1] = self.ekf.state
            ekf_covariances[i+1] = self.ekf.covariance
            
            odometry_states[i+1] = self.ekf.motion_model(
                odometry_states[i], v_noisy, delta_noisy, self.dt
            )
        
        return {
            'true_states': true_states,
            'ekf_states': ekf_states,
            'ekf_covariances': ekf_covariances,
            'odometry_states': odometry_states,
            'controls': controls,
            'landmarks': self.landmarks
        }
    
    def analyze_results(self, results: dict) -> dict:
        """
        分析仿真结果
        """
        true_states = results['true_states']
        ekf_states = results['ekf_states']
        odometry_states = results['odometry_states']
        
        ekf_errors = true_states - ekf_states
        ekf_errors[:, 2] = np.array([self.ekf._wrap_to_pi(e) for e in ekf_errors[:, 2]])
        
        odometry_errors = true_states - odometry_states
        odometry_errors[:, 2] = np.array([self.ekf._wrap_to_pi(e) for e in odometry_errors[:, 2]])
        
        ekf_rmse = np.sqrt(np.mean(ekf_errors**2, axis=0))
        odometry_rmse = np.sqrt(np.mean(odometry_errors**2, axis=0))
        
        return {
            'ekf_errors': ekf_errors,
            'odometry_errors': odometry_errors,
            'ekf_rmse': ekf_rmse,
            'odometry_rmse': odometry_rmse
        }
    
    def visualize_results(self, results: dict, analysis: dict, save_path: str = None):
        """
        可视化仿真结果
        """
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        ax1 = axes[0, 0]
        true_states = results['true_states']
        ekf_states = results['ekf_states']
        odometry_states = results['odometry_states']
        landmarks = results['landmarks']
        
        ax1.plot(true_states[:, 0], true_states[:, 1], 'g-', linewidth=2, label='真实轨迹')
        ax1.plot(ekf_states[:, 0], ekf_states[:, 1], 'b-', linewidth=2, label='EKF估计')
        ax1.plot(odometry_states[:, 0], odometry_states[:, 1], 'r--', linewidth=1.5, label='里程计')
        
        for lm in landmarks:
            ax1.scatter(lm.x, lm.y, c='orange', s=50, marker='^', alpha=0.6)
        
        ax1.scatter(true_states[0, 0], true_states[0, 1], c='green', s=100, marker='o', label='起点')
        ax1.scatter(true_states[-1, 0], true_states[-1, 1], c='red', s=100, marker='s', label='终点')
        
        ax1.set_xlabel('X (m)', fontsize=12)
        ax1.set_ylabel('Y (m)', fontsize=12)
        ax1.set_title('机器人定位轨迹对比', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.axis('equal')
        
        ax2 = axes[0, 1]
        time_steps = np.arange(len(true_states)) * self.dt
        ax2.plot(time_steps, analysis['ekf_errors'][:, 0], 'b-', label='X误差', alpha=0.7)
        ax2.plot(time_steps, analysis['odometry_errors'][:, 0], 'r--', label='里程计X误差', alpha=0.7)
        ax2.set_xlabel('时间 (s)', fontsize=12)
        ax2.set_ylabel('误差 (m)', fontsize=12)
        ax2.set_title('X方向定位误差', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        ax3 = axes[0, 2]
        ax3.plot(time_steps, analysis['ekf_errors'][:, 1], 'b-', label='Y误差', alpha=0.7)
        ax3.plot(time_steps, analysis['odometry_errors'][:, 1], 'r--', label='里程计Y误差', alpha=0.7)
        ax3.set_xlabel('时间 (s)', fontsize=12)
        ax3.set_ylabel('误差 (m)', fontsize=12)
        ax3.set_title('Y方向定位误差', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        ax4 = axes[1, 0]
        ax4.plot(time_steps, np.degrees(analysis['ekf_errors'][:, 2]), 'b-', label='航向误差', alpha=0.7)
        ax4.plot(time_steps, np.degrees(analysis['odometry_errors'][:, 2]), 'r--', label='里程计航向误差', alpha=0.7)
        ax4.set_xlabel('时间 (s)', fontsize=12)
        ax4.set_ylabel('误差 (度)', fontsize=12)
        ax4.set_title('航向角定位误差', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        ax5 = axes[1, 1]
        ekf_covariances = results['ekf_covariances']
        sigma_x = np.sqrt(ekf_covariances[:, 0, 0])
        sigma_y = np.sqrt(ekf_covariances[:, 1, 1])
        sigma_theta = np.sqrt(ekf_covariances[:, 2, 2])
        
        ax5.plot(time_steps, sigma_x, 'b-', label='σ_x', linewidth=2)
        ax5.plot(time_steps, sigma_y, 'g-', label='σ_y', linewidth=2)
        ax5.plot(time_steps, np.degrees(sigma_theta), 'r-', label='σ_θ (度)', linewidth=2)
        ax5.set_xlabel('时间 (s)', fontsize=12)
        ax5.set_ylabel('标准差', fontsize=12)
        ax5.set_title('EKF不确定性演化', fontsize=14, fontweight='bold')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        ax6 = axes[1, 2]
        position_error_ekf = np.sqrt(analysis['ekf_errors'][:, 0]**2 + analysis['ekf_errors'][:, 1]**2)
        position_error_odom = np.sqrt(analysis['odometry_errors'][:, 0]**2 + analysis['odometry_errors'][:, 1]**2)
        
        ax6.plot(time_steps, position_error_ekf, 'b-', label='EKF位置误差', linewidth=2)
        ax6.plot(time_steps, position_error_odom, 'r--', label='里程计位置误差', linewidth=2)
        ax6.set_xlabel('时间 (s)', fontsize=12)
        ax6.set_ylabel('位置误差 (m)', fontsize=12)
        ax6.set_title('总位置误差对比', fontsize=14, fontweight='bold')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"结果已保存到: {save_path}")
        
        plt.close()
        
    def visualize_uncertainty_ellipses(self, results: dict, save_path: str = None):
        """
        可视化不确定性椭圆
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        
        true_states = results['true_states']
        ekf_states = results['ekf_states']
        ekf_covariances = results['ekf_covariances']
        
        ax.plot(true_states[:, 0], true_states[:, 1], 'g-', linewidth=2, label='真实轨迹')
        ax.plot(ekf_states[:, 0], ekf_states[:, 1], 'b-', linewidth=2, label='EKF估计')
        
        for i in range(0, len(ekf_states), 20):
            x, y, theta = ekf_states[i]
            cov = ekf_covariances[i, :2, :2]
            
            eigenvalues, eigenvectors = np.linalg.eig(cov)
            order = eigenvalues.argsort()[::-1]
            eigenvalues = eigenvalues[order]
            eigenvectors = eigenvectors[:, order]
            
            angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
            width = 2 * np.sqrt(eigenvalues[0])
            height = 2 * np.sqrt(eigenvalues[1])
            
            ellipse = Ellipse((x, y), width, height, angle=angle,
                             fill=False, color='blue', alpha=0.5, linewidth=1.5)
            ax.add_patch(ellipse)
        
        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('EKF定位不确定性椭圆演化', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"不确定性椭圆已保存到: {save_path}")
        
        plt.close()
    
    def visualize_trajectory_comparison(self, results: dict, save_path: str = None):
        """
        可视化轨迹对比（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        true_states = results['true_states']
        ekf_states = results['ekf_states']
        odometry_states = results['odometry_states']
        landmarks = results['landmarks']
        
        ax.plot(true_states[:, 0], true_states[:, 1], 'k-', linewidth=2, label='真实轨迹')
        ax.plot(ekf_states[:, 0], ekf_states[:, 1], 'b-', linewidth=2, label='EKF估计轨迹')
        ax.plot(odometry_states[:, 0], odometry_states[:, 1], 'r--', linewidth=1.5, label='里程计轨迹')
        
        for lm in landmarks:
            ax.scatter(lm.x, lm.y, c='orange', s=50, marker='^', alpha=0.6, label='地标' if lm == landmarks[0] else '')
        
        ax.scatter(true_states[0, 0], true_states[0, 1], c='green', s=100, marker='o', label='起点', zorder=5)
        ax.scatter(true_states[-1, 0], true_states[-1, 1], c='red', s=100, marker='s', label='终点', zorder=5)
        
        for i in range(0, len(true_states), 50):
            dx = 0.5 * np.cos(true_states[i, 2])
            dy = 0.5 * np.sin(true_states[i, 2])
            ax.arrow(true_states[i, 0], true_states[i, 1], dx, dy,
                    head_width=0.2, head_length=0.1, fc='orange', ec='orange', alpha=0.6)
        
        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('机器人轨迹对比', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"轨迹对比图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_error_x(self, results: dict, analysis: dict, save_path: str = None):
        """
        可视化X方向定位误差（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['true_states'])) * self.dt
        ax.plot(time_steps, analysis['ekf_errors'][:, 0], 'b-', linewidth=2, label='EKF误差', alpha=0.8)
        ax.plot(time_steps, analysis['odometry_errors'][:, 0], 'r--', linewidth=2, label='里程计误差', alpha=0.8)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('误差 (m)', fontsize=12)
        ax.set_title('X方向定位误差', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"X方向误差图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_error_y(self, results: dict, analysis: dict, save_path: str = None):
        """
        可视化Y方向定位误差（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['true_states'])) * self.dt
        ax.plot(time_steps, analysis['ekf_errors'][:, 1], 'b-', linewidth=2, label='EKF误差', alpha=0.8)
        ax.plot(time_steps, analysis['odometry_errors'][:, 1], 'r--', linewidth=2, label='里程计误差', alpha=0.8)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('误差 (m)', fontsize=12)
        ax.set_title('Y方向定位误差', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Y方向误差图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_error_theta(self, results: dict, analysis: dict, save_path: str = None):
        """
        可视化航向角定位误差（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['true_states'])) * self.dt
        ax.plot(time_steps, np.degrees(analysis['ekf_errors'][:, 2]), 'b-', linewidth=2, label='EKF误差', alpha=0.8)
        ax.plot(time_steps, np.degrees(analysis['odometry_errors'][:, 2]), 'r--', linewidth=2, label='里程计误差', alpha=0.8)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('误差 (度)', fontsize=12)
        ax.set_title('航向角定位误差', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"航向角误差图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_error_position(self, results: dict, analysis: dict, save_path: str = None):
        """
        可视化总位置误差（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['true_states'])) * self.dt
        position_error_ekf = np.sqrt(analysis['ekf_errors'][:, 0]**2 + analysis['ekf_errors'][:, 1]**2)
        position_error_odom = np.sqrt(analysis['odometry_errors'][:, 0]**2 + analysis['odometry_errors'][:, 1]**2)
        
        ax.plot(time_steps, position_error_ekf, 'b-', linewidth=2, label='EKF位置误差', alpha=0.8)
        ax.plot(time_steps, position_error_odom, 'r--', linewidth=2, label='里程计位置误差', alpha=0.8)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('位置误差 (m)', fontsize=12)
        ax.set_title('总位置误差对比', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"总位置误差图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_uncertainty_std(self, results: dict, save_path: str = None):
        """
        可视化不确定性标准差演化（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['true_states'])) * self.dt
        ekf_covariances = results['ekf_covariances']
        sigma_x = np.sqrt(ekf_covariances[:, 0, 0])
        sigma_y = np.sqrt(ekf_covariances[:, 1, 1])
        sigma_theta = np.sqrt(ekf_covariances[:, 2, 2])
        
        ax.plot(time_steps, sigma_x, 'b-', linewidth=2, label='σ_x')
        ax.plot(time_steps, sigma_y, 'g-', linewidth=2, label='σ_y')
        ax.plot(time_steps, np.degrees(sigma_theta), 'r-', linewidth=2, label='σ_θ (度)')
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('标准差', fontsize=12)
        ax.set_title('EKF不确定性标准差演化', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"不确定性标准差图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_control_velocity(self, results: dict, save_path: str = None):
        """
        可视化速度控制输入（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['controls'])) * self.dt
        ax.plot(time_steps, results['controls'][:, 0], 'b-', linewidth=2)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('速度 (m/s)', fontsize=12)
        ax.set_title('速度控制输入', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"速度控制图已保存到: {save_path}")
        
        plt.close()
    
    def visualize_control_steering(self, results: dict, save_path: str = None):
        """
        可视化转向角控制输入（独立图）
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        time_steps = np.arange(len(results['controls'])) * self.dt
        ax.plot(time_steps, np.degrees(results['controls'][:, 1]), 'b-', linewidth=2)
        
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('转向角 (度)', fontsize=12)
        ax.set_title('转向角控制输入', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"转向角控制图已保存到: {save_path}")
        
        plt.close()


def run_kalman_filter_demo():
    """
    运行卡尔曼滤波定位演示
    """
    print("\n" + "="*60)
    print("基于卡尔曼滤波的机器人定位仿真")
    print("="*60)
    
    sim = KalmanFilterSimulation(wheel_base=2.0)
    sim.generate_environment(num_landmarks=25, env_size=15.0)
    
    print("\n运行仿真...")
    results = sim.run_simulation(total_time=30.0)
    
    print("\n分析结果...")
    analysis = sim.analyze_results(results)
    
    print("\n定位性能统计:")
    print(f"  EKF RMSE: X={analysis['ekf_rmse'][0]:.4f}m, Y={analysis['ekf_rmse'][1]:.4f}m, θ={np.degrees(analysis['ekf_rmse'][2]):.4f}°")
    print(f"  里程计 RMSE: X={analysis['odometry_rmse'][0]:.4f}m, Y={analysis['odometry_rmse'][1]:.4f}m, θ={np.degrees(analysis['odometry_rmse'][2]):.4f}°")
    
    improvement = (analysis['odometry_rmse'] - analysis['ekf_rmse']) / analysis['odometry_rmse'] * 100
    print(f"  EKF相对里程计改进: X={improvement[0]:.1f}%, Y={improvement[1]:.1f}%, θ={improvement[2]:.1f}%")
    
    print("\n生成独立图片...")
    base_path = 'e:/study/智能工程/'
    
    sim.visualize_trajectory_comparison(results, base_path + 'trajectory_comparison.png')
    sim.visualize_error_x(results, analysis, base_path + 'error_x.png')
    sim.visualize_error_y(results, analysis, base_path + 'error_y.png')
    sim.visualize_error_theta(results, analysis, base_path + 'error_theta.png')
    sim.visualize_error_position(results, analysis, base_path + 'error_position.png')
    sim.visualize_uncertainty_std(results, base_path + 'uncertainty_std.png')
    sim.visualize_uncertainty_ellipses(results, base_path + 'uncertainty_ellipse.png')
    sim.visualize_control_velocity(results, base_path + 'control_velocity.png')
    sim.visualize_control_steering(results, base_path + 'control_steering.png')
    
    print("\n所有图片已生成完成！")
    
    return results, analysis


if __name__ == "__main__":
    results, analysis = run_kalman_filter_demo()
