import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 读取数据
df = pd.read_csv('function_values.csv')

# 创建3D图
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

# 重塑数据为网格
x1 = np.linspace(-3.0, 12.1, 101)
x2 = np.linspace(4.1, 5.8, 101)
X1, X2 = np.meshgrid(x1, x2)
Z = df['fitness'].values.reshape(101, 101)

# 绘制3D表面图
surf = ax.plot_surface(X1, X2, Z, cmap='viridis', alpha=0.8)
ax.set_xlabel('x1')
ax.set_ylabel('x2')
ax.set_zlabel('f(x1, x2)')
ax.set_title('Objective Function: f(x1, x2) = 21.5 + x1*sin(4πx1) + x2*sin(20πx2)')

# 添加颜色条
fig.colorbar(surf)
plt.savefig('function_plot.png', dpi=300)
plt.show()