"""
叉车式移动机器人运动学建模
============================

模型描述：
- 两个随动固定标准轮（轮A和轮B）
- 一个受控转向标准轮（带电机驱动）

轮子配置：
- 轮A: α=-π/2, β=π, l=1 (固定标准轮，随动)
- 轮B: α=π/2, β=0, l=1 (固定标准轮，随动)  
- 转向轮: α=0, β=π/2, l=2 (转向标准轮，受控)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib.collections import PatchCollection
from dataclasses import dataclass
from typing import Tuple, List
import math

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class ForkliftConfig:
    wheel_A_alpha: float = -np.pi / 2
    wheel_A_beta: float = np.pi
    wheel_A_l: float = 1.0
    
    wheel_B_alpha: float = np.pi / 2
    wheel_B_beta: float = 0.0
    wheel_B_l: float = 1.0
    
    steering_alpha: float = 0.0
    steering_beta: float = np.pi / 2
    steering_l: float = 2.0
    
    wheel_radius: float = 0.15
    wheel_width: float = 0.1


class InstantCenterMethod:
    """
    瞬心法构建运动学模型
    
    原理：
    对于非完整约束的轮式机器人，在任意时刻存在一个瞬时旋转中心(ICR)，
    使得所有轮子的速度方向垂直于轮心到ICR的连线。
    
    对于叉车模型：
    - 固定轮A和B约束了ICR必须在后轴连线上
    - 转向轮的角度决定了ICR在后轴上的具体位置
    """
    
    def __init__(self, config: ForkliftConfig = None):
        self.config = config or ForkliftConfig()
        
    def compute_icr_position(self, steering_angle: float) -> Tuple[float, float]:
        """
        根据转向角计算瞬时旋转中心位置
        
        参数:
            steering_angle: 转向轮相对于车体纵轴的角度
        
        返回:
            (x_icr, y_icr): ICR在机器人坐标系中的位置
            
        推导：
        对于转向轮，轮心位置为 (l_steering, 0)
        轮子速度方向为 (cos(steering_angle), sin(steering_angle))
        ICR到轮心的连线应垂直于速度方向
        
        设ICR坐标为 (x, y)，则：
        (x - l_steering) * cos(steering_angle) + y * sin(steering_angle) = 0
        
        同时，ICR必须在后轴上（y=0），因为固定轮A和B约束了这一点
        所以 y = 0，x = l_steering * tan(steering_angle)
        """
        if abs(steering_angle) < 1e-6:
            return (float('inf'), 0.0)
        
        x_icr = self.config.steering_l * np.tan(steering_angle)
        return (x_icr, 0.0)
    
    def compute_curvature(self, steering_angle: float) -> float:
        """
        计算运动曲率
        
        曲率 κ = 1 / R，其中R为转弯半径
        """
        if abs(steering_angle) < 1e-6:
            return 0.0
        
        R = abs(self.config.steering_l / np.tan(steering_angle))
        return 1.0 / R
    
    def forward_kinematics(self, v_rear: float, steering_angle: float) -> Tuple[float, float, float]:
        """
        正运动学：从轮速到机器人速度
        
        参数:
            v_rear: 后轴中心速度（固定轮A和B的中点）
            steering_angle: 转向角
            
        返回:
            (v_x, v_y, omega): 机器人坐标系下的线速度和角速度
            
        推导：
        根据瞬心法，机器人绕ICR旋转
        - 角速度 ω = v_rear / R
        - 线速度方向沿机器人纵轴
        - v_x = v_rear, v_y = 0
        """
        if abs(steering_angle) < 1e-6:
            return (v_rear, 0.0, 0.0)
        
        curvature = self.compute_curvature(steering_angle)
        omega = v_rear * curvature
        return (v_rear, 0.0, omega)
    
    def inverse_kinematics(self, v_x: float, omega: float) -> Tuple[float, float]:
        """
        逆运动学：从机器人速度到轮速
        
        参数:
            v_x: 机器人前进速度
            omega: 机器人角速度
            
        返回:
            (v_rear, steering_angle): 后轴速度和转向角
        """
        if abs(omega) < 1e-6:
            return (v_x, 0.0)
        
        steering_angle = np.arctan(omega * self.config.steering_l / v_x) if abs(v_x) > 1e-6 else np.pi / 2
        v_rear = v_x
        return (v_rear, steering_angle)
    
    def wheel_velocities(self, v_rear: float, steering_angle: float) -> Tuple[float, float, float]:
        """
        计算各轮速度
        
        返回:
            (v_A, v_B, v_steering): 轮A、轮B和转向轮的速度
        """
        v_x, _, omega = self.forward_kinematics(v_rear, steering_angle)
        
        v_A = v_rear - omega * self.config.wheel_A_l * np.cos(self.config.wheel_A_alpha)
        v_B = v_rear - omega * self.config.wheel_B_l * np.cos(self.config.wheel_B_alpha)
        
        R = abs(self.config.steering_l / np.tan(steering_angle)) if abs(steering_angle) > 1e-6 else float('inf')
        v_steering = v_rear * np.sqrt(1 + (self.config.steering_l / R)**2) if R < float('inf') else v_rear
        
        return (v_A, v_B, v_steering)


class ConstraintMethod:
    """
    运动约束法构建运动学模型
    
    原理：
    利用轮子的非完整约束条件，建立约束方程，然后求解机器人的可行运动。
    
    对于标准轮，约束方程为：
    [sin(α+β), -cos(α+β), -l*cos(β)] · [ẋ, ẏ, θ̇] = 0
    
    这表示轮子不能侧滑。
    """
    
    def __init__(self, config: ForkliftConfig = None):
        self.config = config or ForkliftConfig()
        self._build_constraint_matrix()
        
    def _build_constraint_matrix(self):
        """
        构建约束矩阵
        
        对于每个轮子，约束方程为：
        C_i · ξ_R = 0
        
        其中 ξ_R = [ẋ, ẏ, θ̇]^T 是机器人速度向量
        """
        cfg = self.config
        
        self.C_A = np.array([
            np.sin(cfg.wheel_A_alpha + cfg.wheel_A_beta),
            -np.cos(cfg.wheel_A_alpha + cfg.wheel_A_beta),
            -cfg.wheel_A_l * np.cos(cfg.wheel_A_beta)
        ])
        
        self.C_B = np.array([
            np.sin(cfg.wheel_B_alpha + cfg.wheel_B_beta),
            -np.cos(cfg.wheel_B_alpha + cfg.wheel_B_beta),
            -cfg.wheel_B_l * np.cos(cfg.wheel_B_beta)
        ])
        
        self.C_matrix = np.array([self.C_A, self.C_B])
        
    def compute_steering_constraint(self, steering_angle: float) -> np.ndarray:
        """
        计算转向轮的约束
        
        转向轮的β角是可变的，约束随转向角变化
        """
        cfg = self.config
        beta_total = cfg.steering_beta + steering_angle
        
        C_steering = np.array([
            np.sin(cfg.steering_alpha + beta_total),
            -np.cos(cfg.steering_alpha + beta_total),
            -cfg.steering_l * np.cos(beta_total)
        ])
        
        return C_steering
    
    def forward_kinematics(self, v_steering: float, steering_angle: float) -> Tuple[float, float, float]:
        """
        正运动学：从转向轮速度到机器人速度
        
        参数:
            v_steering: 转向轮线速度
            steering_angle: 转向角
            
        返回:
            (v_x, v_y, omega): 机器人速度
        """
        C_steering = self.compute_steering_constraint(steering_angle)
        
        C_total = np.array([self.C_A, self.C_B, C_steering])
        
        rolling_constraint = self._build_rolling_constraint(steering_angle)
        
        A = np.vstack([C_total[:2], rolling_constraint])
        b = np.array([0, 0, v_steering])
        
        try:
            xi_R = np.linalg.solve(A, b)
            return tuple(xi_R)
        except np.linalg.LinAlgError:
            return (v_steering, 0.0, 0.0)
    
    def _build_rolling_constraint(self, steering_angle: float) -> np.ndarray:
        """
        构建转向轮的滚动约束
        
        滚动约束表示轮子沿其运动方向的速度
        """
        cfg = self.config
        beta_total = cfg.steering_beta + steering_angle
        
        R_steering = np.array([
            np.cos(cfg.steering_alpha + beta_total),
            np.sin(cfg.steering_alpha + beta_total),
            cfg.steering_l * np.sin(beta_total)
        ])
        
        return R_steering
    
    def inverse_kinematics(self, v_x: float, v_y: float, omega: float) -> Tuple[float, float, float]:
        """
        逆运动学：从机器人速度到各轮速度
        
        返回:
            (v_A, v_B, v_steering): 各轮速度
        """
        xi_R = np.array([v_x, v_y, omega])
        
        v_A = self.C_A @ xi_R
        v_B = self.C_B @ xi_R
        
        return (v_A, v_B, 0.0)
    
    def verify_constraints(self, v_x: float, v_y: float, omega: float) -> Tuple[float, float]:
        """
        验证约束是否满足
        
        返回:
            (constraint_A, constraint_B): 约束残差
        """
        xi_R = np.array([v_x, v_y, omega])
        
        residual_A = self.C_A @ xi_R
        residual_B = self.C_B @ xi_R
        
        return (residual_A, residual_B)


class ForkliftKinematics:
    """
    叉车运动学模型整合类
    """
    
    def __init__(self, config: ForkliftConfig = None):
        self.config = config or ForkliftConfig()
        self.instant_center = InstantCenterMethod(self.config)
        self.constraint_method = ConstraintMethod(self.config)
        
    def update_pose(self, pose: np.ndarray, v: float, delta: float, dt: float) -> np.ndarray:
        """
        更新机器人位姿
        
        参数:
            pose: 当前位姿 [x, y, theta]
            v: 后轴速度
            delta: 转向角
            dt: 时间步长
            
        返回:
            新位姿
        """
        x, y, theta = pose
        
        if abs(delta) < 1e-6:
            dx = v * np.cos(theta) * dt
            dy = v * np.sin(theta) * dt
            dtheta = 0.0
        else:
            R = self.config.steering_l / np.tan(delta)
            dtheta = v / R * dt
            dx = R * (np.sin(theta + dtheta) - np.sin(theta))
            dy = R * (-np.cos(theta + dtheta) + np.cos(theta))
        
        new_pose = np.array([
            x + dx,
            y + dy,
            theta + dtheta
        ])
        
        return new_pose
    
    def compute_jacobian(self, pose: np.ndarray, v: float, delta: float, dt: float) -> np.ndarray:
        """
        计算运动学雅可比矩阵
        
        用于误差传导和卡尔曼滤波
        """
        x, y, theta = pose
        
        J = np.eye(3)
        
        if abs(delta) < 1e-6:
            J[0, 2] = -v * np.sin(theta) * dt
            J[1, 2] = v * np.cos(theta) * dt
        else:
            R = self.config.steering_l / np.tan(delta)
            omega = v / R
            dtheta = omega * dt
            
            J[0, 2] = R * (np.cos(theta + dtheta) - np.cos(theta))
            J[1, 2] = R * (np.sin(theta + dtheta) - np.sin(theta))
        
        return J


def visualize_kinematics():
    """
    可视化运动学模型
    """
    config = ForkliftConfig()
    kinematics = ForkliftKinematics(config)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    ax1 = axes[0, 0]
    steering_angles = np.linspace(-np.pi/4, np.pi/4, 50)
    icr_positions = [kinematics.instant_center.compute_icr_position(sa) for sa in steering_angles]
    x_icr = [p[0] for p in icr_positions if abs(p[0]) < 20]
    angles_plot = steering_angles[:len(x_icr)]
    
    ax1.plot(np.degrees(angles_plot), x_icr, 'b-', linewidth=2, label='ICR位置')
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax1.axvline(x=0, color='k', linestyle='--', alpha=0.3)
    ax1.set_xlabel('转向角 (度)', fontsize=12)
    ax1.set_ylabel('ICR位置 (m)', fontsize=12)
    ax1.set_title('瞬时旋转中心位置随转向角变化', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    ax2 = axes[0, 1]
    curvatures = [kinematics.instant_center.compute_curvature(sa) for sa in steering_angles]
    ax2.plot(np.degrees(steering_angles), curvatures, 'r-', linewidth=2, label='曲率')
    ax2.set_xlabel('转向角 (度)', fontsize=12)
    ax2.set_ylabel('曲率 (1/m)', fontsize=12)
    ax2.set_title('运动曲率随转向角变化', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    ax3 = axes[1, 0]
    v_rear = 1.0
    wheel_speeds = [kinematics.instant_center.wheel_velocities(v_rear, sa) for sa in steering_angles]
    v_A = [w[0] for w in wheel_speeds]
    v_B = [w[1] for w in wheel_speeds]
    v_steer = [w[2] for w in wheel_speeds]
    
    ax3.plot(np.degrees(steering_angles), v_A, 'b-', linewidth=2, label='轮A速度')
    ax3.plot(np.degrees(steering_angles), v_B, 'g-', linewidth=2, label='轮B速度')
    ax3.plot(np.degrees(steering_angles), v_steer, 'r--', linewidth=2, label='转向轮速度')
    ax3.set_xlabel('转向角 (度)', fontsize=12)
    ax3.set_ylabel('轮速 (m/s)', fontsize=12)
    ax3.set_title('各轮速度随转向角变化', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    ax4 = axes[1, 1]
    pose = np.array([0.0, 0.0, 0.0])
    dt = 0.1
    trajectory = [pose.copy()]
    
    for i in range(100):
        v = 0.5
        delta = 0.3 * np.sin(0.1 * i)
        pose = kinematics.update_pose(pose, v, delta, dt)
        trajectory.append(pose.copy())
    
    trajectory = np.array(trajectory)
    ax4.plot(trajectory[:, 0], trajectory[:, 1], 'b-', linewidth=2, label='轨迹')
    ax4.scatter(trajectory[0, 0], trajectory[0, 1], c='g', s=100, marker='o', label='起点', zorder=5)
    ax4.scatter(trajectory[-1, 0], trajectory[-1, 1], c='r', s=100, marker='s', label='终点', zorder=5)
    
    for i in range(0, len(trajectory), 20):
        x, y, theta = trajectory[i]
        arrow_len = 0.3
        ax4.arrow(x, y, arrow_len * np.cos(theta), arrow_len * np.sin(theta),
                  head_width=0.1, head_length=0.05, fc='orange', ec='orange', alpha=0.7)
    
    ax4.set_xlabel('X (m)', fontsize=12)
    ax4.set_ylabel('Y (m)', fontsize=12)
    ax4.set_title('叉车运动轨迹示例', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.axis('equal')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('e:/study/智能工程/kinematics_visualization.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("运动学可视化已保存到: e:/study/智能工程/kinematics_visualization.png")


def compare_methods():
    """
    比较瞬心法和约束法的结果
    """
    config = ForkliftConfig()
    instant_center = InstantCenterMethod(config)
    constraint_method = ConstraintMethod(config)
    
    print("\n" + "="*60)
    print("瞬心法与约束法对比验证")
    print("="*60)
    
    test_cases = [
        (1.0, 0.0, "直线运动"),
        (1.0, np.pi/12, "小角度转弯"),
        (1.0, np.pi/6, "中等角度转弯"),
        (0.5, np.pi/4, "大角度转弯"),
    ]
    
    for v_rear, steering_angle, description in test_cases:
        print(f"\n测试场景: {description}")
        print(f"  后轴速度: {v_rear:.2f} m/s, 转向角: {np.degrees(steering_angle):.1f}°")
        
        vx_ic, vy_ic, omega_ic = instant_center.forward_kinematics(v_rear, steering_angle)
        print(f"  瞬心法结果: v_x={vx_ic:.4f}, v_y={vy_ic:.4f}, ω={omega_ic:.4f}")
        
        vx_c, vy_c, omega_c = constraint_method.forward_kinematics(v_rear, steering_angle)
        print(f"  约束法结果: v_x={vx_c:.4f}, v_y={vy_c:.4f}, ω={omega_c:.4f}")
        
        error = np.sqrt((vx_ic - vx_c)**2 + (vy_ic - vy_c)**2 + (omega_ic - omega_c)**2)
        print(f"  方法差异: {error:.6f}")
        
        residual_A, residual_B = constraint_method.verify_constraints(vx_ic, vy_ic, omega_ic)
        print(f"  约束验证: 轮A残差={residual_A:.6f}, 轮B残差={residual_B:.6f}")


if __name__ == "__main__":
    visualize_kinematics()
    compare_methods()
