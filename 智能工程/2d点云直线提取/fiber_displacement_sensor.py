import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

X = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
UO = np.array([0.98, 2.03, 3.18, 4.33, 5.71, 7.05, 8.41, 9.67, 10.71, 11.76])

slope, intercept, r_value, p_value, std_err = stats.linregress(X, UO)

print("=" * 60)
print("光纤位移传感器实验数据分析")
print("=" * 60)
print("\n实验数据：")
print(f"{'位移 X (mm)':<15} {'输出电压 UO (V)':<15}")
print("-" * 30)
for x, u in zip(X, UO):
    print(f"{x:<15.1f} {u:<15.2f}")

print("\n" + "=" * 60)
print("线性拟合结果：")
print("=" * 60)
print(f"\n拟合直线方程: UO = {slope:.4f}X + {intercept:.4f}")
print(f"相关系数 R² = {r_value**2:.6f}")
print(f"灵敏度 S = {slope:.4f} V/mm")
print(f"标准误差 = {std_err:.6f}")

fig, ax = plt.subplots(figsize=(10, 7))

ax.scatter(X, UO, color='blue', s=120, label='实验数据点', zorder=5, edgecolors='black', linewidth=1.5)
X_fit = np.linspace(0, 1.1, 100)
UO_fit = slope * X_fit + intercept
ax.plot(X_fit, UO_fit, 'r-', linewidth=2.5, label=f'线性拟合: UO = {slope:.2f}X + {intercept:.2f}')

ax.set_xlabel('位移 X (mm)', fontsize=14)
ax.set_ylabel('输出电压 UO (V)', fontsize=14)
ax.set_title('光纤位移传感器位移特性曲线', fontsize=16, fontweight='bold')
ax.legend(fontsize=12, loc='upper left')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 1.1)
ax.set_ylim(0, 14)

textstr = f'拟合方程: UO = {slope:.2f}X + {intercept:.2f}\n'
textstr += f'相关系数 R² = {r_value**2:.4f}\n'
textstr += f'灵敏度 S = {slope:.2f} V/mm'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', bbox=props)

plt.tight_layout()
plt.savefig('fiber_displacement_analysis.png', dpi=300, bbox_inches='tight')
print("\n图表已保存为: fiber_displacement_analysis.png")
plt.show()

print("\n" + "=" * 60)
print("灵敏度分析：")
print("=" * 60)
sensitivity = np.diff(UO) / np.diff(X)
X_mid = (X[:-1] + X[1:]) / 2
print("\n各点局部灵敏度：")
for i in range(len(X_mid)):
    print(f"X = {X_mid[i]:.2f} mm, S = {sensitivity[i]:.2f} V/mm")
print(f"\n平均灵敏度: {np.mean(sensitivity):.2f} V/mm")
print(f"灵敏度标准差: {np.std(sensitivity):.2f} V/mm")

print("\n" + "=" * 60)
print("问题2答案：光纤位移实验系统的灵敏度与哪些因素有关？")
print("=" * 60)
print("""
光纤位移传感器的灵敏度主要与以下因素有关：

1. 光纤参数：
   - 光纤芯径：芯径越大，接收光的能力越强，灵敏度越高
   - 数值孔径(NA)：NA越大，光接收角越大，灵敏度越高
   - 光纤类型：单模光纤与多模光纤的灵敏度不同

2. 光源特性：
   - 光源强度：光源功率越大，输出信号越强，灵敏度越高
   - 光源波长：不同波长的光在光纤中传输特性不同
   - 光源稳定性：稳定性越好，测量精度越高

3. 光纤探头结构：
   - 发射光纤与接收光纤的距离和角度
   - 光纤端面的处理质量（抛光程度）
   - 探头的几何形状和尺寸

4. 反射面特性：
   - 反射率：反射率越高，接收到的光强越大
   - 表面粗糙度：影响反射光的散射程度
   - 反射面倾斜角度：影响反射光的方向

5. 光电转换器件：
   - 光电探测器的响应度
   - 放大电路的增益
   - 信号处理电路的性能

6. 环境因素：
   - 环境温度：影响光纤传输特性和电子器件性能
   - 外界光干扰：影响测量精度
   - 振动：影响光纤和反射面的相对位置

7. 测量范围：
   - 在线性工作范围内，灵敏度较高且稳定
   - 超出线性范围，灵敏度会发生变化
""")
