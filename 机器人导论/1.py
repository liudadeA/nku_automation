# 2312167 刘振毫
# 机器人运动学作业 - DH参数、雅可比矩阵计算与可视化

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

l0 = 100.0

def dh_transform(alpha, a, d, theta):
    alpha_rad = np.radians(alpha)
    theta_rad = np.radians(theta)
    
    ct = np.cos(theta_rad)
    st = np.sin(theta_rad)
    ca = np.cos(alpha_rad)
    sa = np.sin(alpha_rad)
    
    T = np.array([
        [ct, -st*ca, st*sa, a*ct],
        [st, ct*ca, -ct*sa, a*st],
        [0, sa, ca, d],
        [0, 0, 0, 1]
    ])
    return T

def forward_kinematics(theta1, theta2, d3):
    T1 = dh_transform(0, 0, l0, theta1)
    T2 = dh_transform(-90, 0, 0, theta2)
    T3 = dh_transform(-90, 0, d3, 0)
    
    T02 = T1 @ T2
    T03 = T02 @ T3
    
    return T03, T02

def get_position(T):
    return T[:3, 3]

def get_rotation_matrix(T):
    return T[:3, :3]

def jacobian_linear(theta1, theta2, d3):
    theta1_rad = np.radians(theta1)
    theta2_rad = np.radians(theta2)
    
    c1 = np.cos(theta1_rad)
    s1 = np.sin(theta1_rad)
    c2 = np.cos(theta2_rad)
    s2 = np.sin(theta2_rad)
    
    Jv = np.array([
        [d3*s1*s2, -d3*c1*c2, -c1*s2],
        [-d3*c1*s2, -d3*s1*c2, -s1*s2],
        [0, d3*s2, -c2]
    ])
    return Jv

def jacobian_angular(theta1, theta2):
    theta1_rad = np.radians(theta1)
    theta2_rad = np.radians(theta2)
    
    c1 = np.cos(theta1_rad)
    s1 = np.sin(theta1_rad)
    
    Jw = np.array([
        [0, s1, 0],
        [0, -c1, 0],
        [1, 0, 0]
    ])
    return Jw

def numerical_diff_position(positions, dt):
    n = len(positions)
    velocities = np.zeros((n-1, 3))
    
    for i in range(n-1):
        velocities[i] = (positions[i+1] - positions[i]) / dt
    
    return velocities

def numerical_diff_rotation(rotations, dt):
    n = len(rotations)
    angular_velocities = np.zeros((n-1, 3))
    
    for i in range(n-1):
        R = rotations[i]
        R_dot = (rotations[i+1] - rotations[i]) / dt
        
        S_omega = R_dot @ R.T
        
        omega_x = S_omega[2, 1]
        omega_y = S_omega[0, 2]
        omega_z = S_omega[1, 0]
        
        angular_velocities[i] = [omega_x, omega_y, omega_z]
    
    return angular_velocities

def task_5a():
    print("=" * 60)
    print("任务 5-a: d3固定为10cm")
    print("=" * 60)
    
    d3_fixed = 10.0
    
    theta1_range = np.arange(0, 90.1, 0.1)
    theta2_range = np.arange(-180, -89.9, 0.1)
    
    n1 = len(theta1_range)
    n2 = len(theta2_range)
    n = min(n1, n2)
    
    theta1_arr = theta1_range[:n]
    theta2_arr = theta2_range[:n]
    
    dt = 1.0
    
    positions = np.zeros((n, 3))
    rotations = np.zeros((n, 3, 3))
    
    for i in range(n):
        T03, _ = forward_kinematics(theta1_arr[i], theta2_arr[i], d3_fixed)
        positions[i] = get_position(T03)
        rotations[i] = get_rotation_matrix(T03)
    
    t = np.arange(n) * dt
    
    fig1, axes1 = plt.subplots(3, 1, figsize=(12, 10))
    fig1.suptitle('任务5-a: 末端位置曲线 (d3=10cm)', fontsize=14)
    
    labels = ['x (cm)', 'y (cm)', 'z (cm)']
    for i, ax in enumerate(axes1):
        ax.plot(t, positions[:, i], 'b-', linewidth=1.5)
        ax.set_ylabel(labels[i], fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, n*dt])
    
    axes1[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5a_position.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    v_numerical = numerical_diff_position(positions, dt)
    
    v_jacobian = np.zeros((n-1, 3))
    for i in range(n-1):
        d_theta1 = np.radians(theta1_arr[i+1] - theta1_arr[i])
        d_theta2 = np.radians(theta2_arr[i+1] - theta2_arr[i])
        d_d3 = 0
        
        Jv = jacobian_linear(theta1_arr[i], theta2_arr[i], d3_fixed)
        dq = np.array([d_theta1, d_theta2, d_d3])
        v_jacobian[i] = Jv @ dq
    
    t_v = t[:-1]
    
    fig2, axes2 = plt.subplots(3, 1, figsize=(12, 10))
    fig2.suptitle('任务5-a: 线速度对比 (数值差分 vs 雅可比)', fontsize=14)
    
    v_labels = ['vx (cm/s)', 'vy (cm/s)', 'vz (cm/s)']
    for i, ax in enumerate(axes2):
        ax.plot(t_v, v_numerical[:, i], 'b-', linewidth=1.5, label='数值差分法')
        ax.plot(t_v, v_jacobian[:, i], 'r--', linewidth=1.5, label='雅可比法')
        ax.set_ylabel(v_labels[i], fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, (n-1)*dt])
    
    axes2[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5a_linear_velocity.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    omega_numerical = numerical_diff_rotation(rotations, dt)
    
    omega_jacobian = np.zeros((n-1, 3))
    for i in range(n-1):
        d_theta1 = np.radians(theta1_arr[i+1] - theta1_arr[i])
        d_theta2 = np.radians(theta2_arr[i+1] - theta2_arr[i])
        d_d3 = 0
        
        Jw = jacobian_angular(theta1_arr[i], theta2_arr[i])
        dq = np.array([d_theta1, d_theta2, d_d3])
        omega_jacobian[i] = Jw @ dq
    
    fig3, axes3 = plt.subplots(3, 1, figsize=(12, 10))
    fig3.suptitle('任务5-a: 角速度对比 (旋转矩阵微分 vs 雅可比)', fontsize=14)
    
    omega_labels = ['ωx (rad/s)', 'ωy (rad/s)', 'ωz (rad/s)']
    for i, ax in enumerate(axes3):
        ax.plot(t_v, omega_numerical[:, i], 'b-', linewidth=1.5, label='旋转矩阵微分法')
        ax.plot(t_v, omega_jacobian[:, i], 'r--', linewidth=1.5, label='雅可比法')
        ax.set_ylabel(omega_labels[i], fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, (n-1)*dt])
    
    axes3[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5a_angular_velocity.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"位置范围: x=[{positions[:, 0].min():.2f}, {positions[:, 0].max():.2f}] cm")
    print(f"           y=[{positions[:, 1].min():.2f}, {positions[:, 1].max():.2f}] cm")
    print(f"           z=[{positions[:, 2].min():.2f}, {positions[:, 2].max():.2f}] cm")

def task_5b():
    print("\n" + "=" * 60)
    print("任务 5-b: d3同步变化 (10cm到100cm)")
    print("=" * 60)
    
    theta1_range = np.arange(0, 90.1, 0.1)
    theta2_range = np.arange(-180, -89.9, 0.1)
    d3_range = np.arange(10, 100.1, 0.1)
    
    n1 = len(theta1_range)
    n2 = len(theta2_range)
    n3 = len(d3_range)
    n = min(n1, n2, n3)
    
    theta1_arr = theta1_range[:n]
    theta2_arr = theta2_range[:n]
    d3_arr = d3_range[:n]
    
    dt = 1.0
    
    positions = np.zeros((n, 3))
    rotations = np.zeros((n, 3, 3))
    
    for i in range(n):
        T03, _ = forward_kinematics(theta1_arr[i], theta2_arr[i], d3_arr[i])
        positions[i] = get_position(T03)
        rotations[i] = get_rotation_matrix(T03)
    
    t = np.arange(n) * dt
    
    fig4, axes4 = plt.subplots(3, 1, figsize=(12, 10))
    fig4.suptitle('任务5-b: 末端位置曲线 (d3同步变化)', fontsize=14)
    
    labels = ['x (cm)', 'y (cm)', 'z (cm)']
    for i, ax in enumerate(axes4):
        ax.plot(t, positions[:, i], 'b-', linewidth=1.5)
        ax.set_ylabel(labels[i], fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, n*dt])
    
    axes4[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5b_position.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    v_numerical = numerical_diff_position(positions, dt)
    
    v_jacobian = np.zeros((n-1, 3))
    for i in range(n-1):
        d_theta1 = np.radians(theta1_arr[i+1] - theta1_arr[i])
        d_theta2 = np.radians(theta2_arr[i+1] - theta2_arr[i])
        d_d3 = d3_arr[i+1] - d3_arr[i]
        
        Jv = jacobian_linear(theta1_arr[i], theta2_arr[i], d3_arr[i])
        dq = np.array([d_theta1, d_theta2, d_d3])
        v_jacobian[i] = Jv @ dq
    
    t_v = t[:-1]
    
    fig5, axes5 = plt.subplots(3, 1, figsize=(12, 10))
    fig5.suptitle('任务5-b: 线速度对比 (数值差分 vs 雅可比)', fontsize=14)
    
    v_labels = ['vx (cm/s)', 'vy (cm/s)', 'vz (cm/s)']
    for i, ax in enumerate(axes5):
        ax.plot(t_v, v_numerical[:, i], 'b-', linewidth=1.5, label='数值差分法')
        ax.plot(t_v, v_jacobian[:, i], 'r--', linewidth=1.5, label='雅可比法')
        ax.set_ylabel(v_labels[i], fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, (n-1)*dt])
    
    axes5[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5b_linear_velocity.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    omega_numerical = numerical_diff_rotation(rotations, dt)
    
    omega_jacobian = np.zeros((n-1, 3))
    for i in range(n-1):
        d_theta1 = np.radians(theta1_arr[i+1] - theta1_arr[i])
        d_theta2 = np.radians(theta2_arr[i+1] - theta2_arr[i])
        d_d3 = d3_arr[i+1] - d3_arr[i]
        
        Jw = jacobian_angular(theta1_arr[i], theta2_arr[i])
        dq = np.array([d_theta1, d_theta2, d_d3])
        omega_jacobian[i] = Jw @ dq
    
    fig6, axes6 = plt.subplots(3, 1, figsize=(12, 10))
    fig6.suptitle('任务5-b: 角速度对比 (旋转矩阵微分 vs 雅可比)', fontsize=14)
    
    omega_labels = ['ωx (rad/s)', 'ωy (rad/s)', 'ωz (rad/s)']
    for i, ax in enumerate(axes6):
        ax.plot(t_v, omega_numerical[:, i], 'b-', linewidth=1.5, label='旋转矩阵微分法')
        ax.plot(t_v, omega_jacobian[:, i], 'r--', linewidth=1.5, label='雅可比法')
        ax.set_ylabel(omega_labels[i], fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, (n-1)*dt])
    
    axes6[-1].set_xlabel('时间 t (s)', fontsize=11)
    plt.tight_layout()
    plt.savefig('task5b_angular_velocity.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"位置范围: x=[{positions[:, 0].min():.2f}, {positions[:, 0].max():.2f}] cm")
    print(f"           y=[{positions[:, 1].min():.2f}, {positions[:, 1].max():.2f}] cm")
    print(f"           z=[{positions[:, 2].min():.2f}, {positions[:, 2].max():.2f}] cm")

if __name__ == "__main__":
    task_5a()
    task_5b()
    print("\n所有任务完成！图像已保存。")
