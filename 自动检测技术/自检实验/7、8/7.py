import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def analyze_sensor(X, UO, title, save_name):
    slope, intercept, r_value, p_value, std_err = stats.linregress(X, UO)
    
    print("=" * 60)
    print(f"{title} 数据分析结果")
    print("=" * 60)
    print(f"\n最小二乘法拟合直线方程: UO = {slope:.4f} * X + {intercept:.4f}")
    print(f"相关系数 R = {r_value:.6f}")
    
    sensitivity = slope
    print(f"\n灵敏度 S = {sensitivity:.4f} mV/mm")
    
    UO_fit = slope * X + intercept
    nonlinear_errors = (UO - UO_fit) / (UO.max() - UO.min()) * 100
    max_nonlinear_error = np.abs(nonlinear_errors).max()
    
    print(f"\n各点的非线性误差:")
    for i in range(len(X)):
        print(f"  X = {X[i]:.2f} mm, 非线性误差 = {nonlinear_errors[i]:.4f}%")
    print(f"\n最大非线性误差 = {max_nonlinear_error:.4f}%")
    
    return slope, intercept, UO_fit, sensitivity, max_nonlinear_error, r_value

def plot_sensor(X, UO, UO_fit, slope, intercept, sensitivity, max_nonlinear_error, title, save_name, color_point='red'):
    plt.figure(figsize=(10, 6))
    plt.scatter(X, UO, color=color_point, s=80, label='实验数据点', zorder=5)
    plt.plot(X, UO_fit, 'b-', linewidth=2, label=f'拟合直线: UO = {slope:.2f}X + {intercept:.2f}')
    
    for i in range(len(X)):
        plt.plot([X[i], X[i]], [UO[i], UO_fit[i]], 'g--', alpha=0.5)
    
    plt.xlabel('位移 X (mm)', fontsize=12)
    plt.ylabel('输出电压 UO (mV)', fontsize=12)
    plt.title(f'{title} 输入/输出特性曲线', fontsize=14)
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='k', linewidth=0.5)
    plt.axvline(x=0, color='k', linewidth=0.5)
    
    y_text = UO.min() + (UO.max() - UO.min()) * 0.1
    x_text = X.min() + (X.max() - X.min()) * 0.6
    plt.text(x_text, y_text, f'灵敏度 S = {sensitivity:.2f} mV/mm\n最大非线性误差 = {max_nonlinear_error:.2f}%', 
             fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(save_name, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n特性曲线已保存为 '{save_name}'")

X = np.array([-2.5, -2.0, -1.5, -1.0, -0.55, 0, 0.5, 1.0, 1.5, 2.0, 2.5])

print("\n" + "#" * 60)
print("# 表7-1 差动变压器式位移传感器特性实验")
print("#" * 60)
UO1 = np.array([-136, -109, -83, -55, -22, 0, 21, 40, 62, 90, 118])
slope1, intercept1, UO_fit1, sensitivity1, max_error1, r1 = analyze_sensor(X, UO1, "表7-1 差动变压器式位移传感器", "特性曲线_表7-1.png")
plot_sensor(X, UO1, UO_fit1, slope1, intercept1, sensitivity1, max_error1, "表7-1 差动变压器式位移传感器", "特性曲线_表7-1.png", 'red')

print("\n" + "#" * 60)
print("# 表8-1 差动式电容传感器特性实验")
print("#" * 60)
UO2 = np.array([-209, -178, -124, -95, -34, 0, 44, 95, 116, 154, 217])
slope2, intercept2, UO_fit2, sensitivity2, max_error2, r2 = analyze_sensor(X, UO2, "表8-1 差动式电容传感器", "特性曲线_表8-1.png")
plot_sensor(X, UO2, UO_fit2, slope2, intercept2, sensitivity2, max_error2, "表8-1 差动式电容传感器", "特性曲线_表8-1.png", 'blue')

print("\n" + "=" * 60)
print("两种传感器对比分析")
print("=" * 60)
print(f"\n{'指标':<20} {'表7-1 差动变压器':<20} {'表8-1 差动电容':<20}")
print("-" * 60)
print(f"{'灵敏度 (mV/mm)':<20} {sensitivity1:<20.4f} {sensitivity2:<20.4f}")
print(f"{'最大非线性误差 (%)':<20} {max_error1:<20.4f} {max_error2:<20.4f}")
print(f"{'相关系数 R':<20} {r1:<20.6f} {r2:<20.6f}")
print(f"{'拟合截距 (mV)':<20} {intercept1:<20.4f} {intercept2:<20.4f}")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].scatter(X, UO1, color='red', s=60, label='实验数据点', zorder=5)
axes[0].plot(X, UO_fit1, 'b-', linewidth=2, label=f'拟合直线')
axes[0].set_xlabel('位移 X (mm)', fontsize=11)
axes[0].set_ylabel('输出电压 UO (mV)', fontsize=11)
axes[0].set_title('表7-1 差动变压器式位移传感器', fontsize=12)
axes[0].legend(loc='upper left', fontsize=9)
axes[0].grid(True, alpha=0.3)
axes[0].axhline(y=0, color='k', linewidth=0.5)
axes[0].axvline(x=0, color='k', linewidth=0.5)

axes[1].scatter(X, UO2, color='blue', s=60, label='实验数据点', zorder=5)
axes[1].plot(X, UO_fit2, 'b-', linewidth=2, label=f'拟合直线')
axes[1].set_xlabel('位移 X (mm)', fontsize=11)
axes[1].set_ylabel('输出电压 UO (mV)', fontsize=11)
axes[1].set_title('表8-1 差动式电容传感器', fontsize=12)
axes[1].legend(loc='upper left', fontsize=9)
axes[1].grid(True, alpha=0.3)
axes[1].axhline(y=0, color='k', linewidth=0.5)
axes[1].axvline(x=0, color='k', linewidth=0.5)

plt.tight_layout()
plt.savefig('特性曲线_对比.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n对比图已保存为 '特性曲线_对比.png'")
print("=" * 60)
