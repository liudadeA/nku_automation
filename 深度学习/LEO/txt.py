import numpy as np
import random
import pandas as pd
from tqdm import tqdm
from collections import deque
import warnings
import os
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
warnings.filterwarnings('ignore')

# 在主程序块中导入matplotlib以避免多进程问题
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import seaborn as sns
    # ===================== 关键修复：字体配置（解决负号/Unicode警告） =====================
    import matplotlib
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['font.sans-serif'] = [
        'SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'WenQuanYi Micro Hei', 'Heiti TC'
    ]
    matplotlib.rcParams['axes.unicode_minus'] = False
    matplotlib.use('Agg')  # 无GUI渲染
else:
    # 在多进程中延迟导入matplotlib
    import matplotlib
    matplotlib.use('Agg')  # 无GUI渲染
    import matplotlib.pyplot as plt
    import seaborn as sns

# ===================== 论文指定测试函数实现（完全对齐IEEE CEC 2021 + DTLZ） =====================
# 一、单目标函数：IEEE CEC 2021单目标实参数优化函数（F01-F10）
def cec2021_f01(x):
    shift = np.ones_like(x) * 10.0
    return np.sum((x - shift) ** 2)

def cec2021_f02(x):
    shift = np.ones_like(x) * 5.0
    return 10 * len(x) + np.sum((x - shift) ** 2 - 10 * np.cos(2 * np.pi * (x - shift)))

def cec2021_f03(x):
    shift = np.ones_like(x) * (-3.0)
    dim = len(x)
    term1 = -20 * np.exp(-0.2 * np.sqrt(np.sum((x - shift)**2) / dim))
    term2 = -np.exp(np.sum(np.cos(2 * np.pi * (x - shift))) / dim)
    return term1 + term2 + 20 + np.e

def cec2021_f04(x):
    shift = np.ones_like(x) * 2.0
    dim = len(x)
    term1 = np.sum((x - shift)**2) / 4000
    term2 = np.prod(np.cos((x - shift) / np.sqrt(np.arange(1, dim+1))))
    return term1 - term2 + 1

def cec2021_f05(x):
    shift = np.ones_like(x) * 1.0
    return np.sum(100 * (x[1:] - (x[:-1] - shift[:-1])**2)**2 + (1 - (x[:-1] - shift[:-1]))**2)

def cec2021_f06(x):
    shift = np.ones_like(x) * (-5.0)
    return 418.9829 * len(x) + np.sum((x - shift) * np.sin(np.sqrt(np.abs(x - shift))))

def cec2021_f07(x):
    shift = np.ones_like(x) * 3.0
    a = 0.5
    b = 3.0
    kmax = 20
    dim = len(x)
    term = np.sum([a**k * np.cos(2 * np.pi * b**k * (x - shift + 0.5)) for k in range(kmax+1)], axis=0)
    return np.sum(term) - dim * np.sum([a**k * np.cos(2 * np.pi * b**k * 0.5) for k in range(kmax+1)])

def cec2021_f08(x):
    shift = np.ones_like(x) * 4.0
    noise = np.random.normal(0, 0.01, size=len(x))
    return 10 * len(x) + np.sum((x - shift + noise) ** 2 - 10 * np.cos(2 * np.pi * (x - shift + noise)))

def cec2021_f09(x):
    shift = np.ones_like(x) * (-2.0)
    theta = np.pi / 4
    rot_mat = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    x_rot = np.dot(np.reshape(x - shift, (-1, 2)), rot_mat).flatten()
    return 10 * len(x) + np.sum(x_rot ** 2 - 10 * np.cos(2 * np.pi * x_rot))

def cec2021_f10(x):
    shift = np.ones_like(x) * 1.5
    dim = len(x)
    half_dim = dim // 2
    term1 = 10 * half_dim + np.sum((x[:half_dim] - shift[:half_dim])**2 - 10 * np.cos(2 * np.pi * (x[:half_dim] - shift[:half_dim])))
    term2 = np.sum((x[half_dim:] - shift[half_dim:])**2) / 4000 - np.prod(np.cos((x[half_dim:] - shift[half_dim:]) / np.sqrt(np.arange(half_dim+1, dim+1)))) + 1
    return term1 + term2

# 二、多目标函数：DTLZ1-DTLZ7
def dtlz1(x, num_obj=3):
    # 批量处理版本：支持单个粒子(x.shape[0] = dim)或多个粒子(x.shape[0] = pop_size, x.shape[1] = dim)
    if isinstance(x, torch.Tensor):
        # 确保输入是二维张量 (pop_size, dim)
        if x.ndim == 1:
            x = x.unsqueeze(0)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = 100 * (k + torch.sum((x[:, num_obj-1:] - 0.5)**2 - torch.cos(20 * torch.pi * (x[:, num_obj-1:] - 0.5)), dim=1))
        g = g.unsqueeze(1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = torch.zeros((pop_size, num_obj), device=x.device)
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                # 第一个目标函数：prod(x[:num_obj-1])
                f[:, i] = (1 + g[:, 0]) * 0.5 * torch.prod(x[:, :num_obj-1-i], dim=1)
            else:
                # 其他目标函数：prod(x[:num_obj-1-i]) * (1 - x[:, num_obj-i])
                f[:, i] = (1 + g[:, 0]) * 0.5 * torch.prod(x[:, :num_obj-1-i], dim=1) * (1 - x[:, num_obj-i])
        
        if not batch_mode:
            return f[0]  # 恢复为一维张量
        return f
    else:
        # 兼容NumPy的版本
        if x.ndim == 1:
            x = x.reshape(1, -1)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = 100 * (k + np.sum((x[:, num_obj-1:] - 0.5)**2 - np.cos(20 * np.pi * (x[:, num_obj-1:] - 0.5)), axis=1))
        g = g.reshape(-1, 1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = np.zeros((pop_size, num_obj))
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                f[:, i] = (1 + g[:, 0]) * 0.5 * np.prod(x[:, :num_obj-1-i], axis=1)
            else:
                f[:, i] = (1 + g[:, 0]) * 0.5 * np.prod(x[:, :num_obj-1-i], axis=1) * (1 - x[:, num_obj-i])
        
        if not batch_mode:
            return f[0]
        return f

def dtlz2(x, num_obj=3):
    # 批量处理版本：支持单个粒子(x.shape[0] = dim)或多个粒子(x.shape[0] = pop_size, x.shape[1] = dim)
    if isinstance(x, torch.Tensor):
        # 确保输入是二维张量 (pop_size, dim)
        if x.ndim == 1:
            x = x.unsqueeze(0)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = torch.sum((x[:, num_obj-1:] - 0.5)**2, dim=1)
        g = g.unsqueeze(1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = torch.zeros((pop_size, num_obj), device=x.device)
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                # 第一个目标函数：prod(cos(x[:num_obj-1] * pi/2))
                f[:, i] = (1 + g[:, 0]) * torch.prod(torch.cos(x[:, :num_obj-1-i] * torch.pi / 2), dim=1)
            else:
                # 其他目标函数：prod(cos(x[:num_obj-1-i] * pi/2)) * sin(x[:, num_obj-i] * pi/2)
                f[:, i] = (1 + g[:, 0]) * torch.prod(torch.cos(x[:, :num_obj-1-i] * torch.pi / 2), dim=1) * torch.sin(x[:, num_obj-i] * torch.pi / 2)
        
        if not batch_mode:
            return f[0]  # 恢复为一维张量
        return f
    else:
        # 兼容NumPy的版本
        if x.ndim == 1:
            x = x.reshape(1, -1)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = np.sum((x[:, num_obj-1:] - 0.5)**2, axis=1)
        g = g.reshape(-1, 1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = np.zeros((pop_size, num_obj))
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                f[:, i] = (1 + g[:, 0]) * np.prod(np.cos(x[:, :num_obj-1-i] * np.pi / 2), axis=1)
            else:
                f[:, i] = (1 + g[:, 0]) * np.prod(np.cos(x[:, :num_obj-1-i] * np.pi / 2), axis=1) * np.sin(x[:, num_obj-i] * np.pi / 2)
        
        if not batch_mode:
            return f[0]
        return f

def dtlz3(x, num_obj=3):
    # 批量处理版本：支持单个粒子(x.shape[0] = dim)或多个粒子(x.shape[0] = pop_size, x.shape[1] = dim)
    if isinstance(x, torch.Tensor):
        # 确保输入是二维张量 (pop_size, dim)
        if x.ndim == 1:
            x = x.unsqueeze(0)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = 100 * (k + torch.sum((x[:, num_obj-1:] - 0.5)**2 - torch.cos(20 * torch.pi * (x[:, num_obj-1:] - 0.5)), dim=1))
        g = g.unsqueeze(1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = torch.zeros((pop_size, num_obj), device=x.device)
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                # 第一个目标函数：prod(cos(x[:num_obj-1] * pi/2))
                f[:, i] = (1 + g[:, 0]) * torch.prod(torch.cos(x[:, :num_obj-1-i] * torch.pi / 2), dim=1)
            else:
                # 其他目标函数：prod(cos(x[:num_obj-1-i] * pi/2)) * sin(x[:, num_obj-i] * pi/2)
                f[:, i] = (1 + g[:, 0]) * torch.prod(torch.cos(x[:, :num_obj-1-i] * torch.pi / 2), dim=1) * torch.sin(x[:, num_obj-i] * torch.pi / 2)
        
        if not batch_mode:
            return f[0]  # 恢复为一维张量
        return f
    else:
        # 兼容NumPy的版本
        if x.ndim == 1:
            x = x.reshape(1, -1)
            batch_mode = False
        else:
            batch_mode = True
            
        pop_size, dim = x.shape
        k = dim - num_obj + 1
        
        # 计算g(x)
        g = 100 * (k + np.sum((x[:, num_obj-1:] - 0.5)**2 - np.cos(20 * np.pi * (x[:, num_obj-1:] - 0.5)), axis=1))
        g = g.reshape(-1, 1)  # (pop_size, 1)
        
        # 计算目标函数值
        f = np.zeros((pop_size, num_obj))
        
        # 计算每个目标函数
        for i in range(num_obj):
            if i == 0:
                f[:, i] = (1 + g[:, 0]) * np.prod(np.cos(x[:, :num_obj-1-i] * np.pi / 2), axis=1)
            else:
                f[:, i] = (1 + g[:, 0]) * np.prod(np.cos(x[:, :num_obj-1-i] * np.pi / 2), axis=1) * np.sin(x[:, num_obj-i] * np.pi / 2)
        
        if not batch_mode:
            return f[0]
        return f

def dtlz4(x, num_obj=3):
    dim = len(x)
    k = dim - num_obj + 1
    alpha = 100
    x_biased = x ** alpha
    g = np.sum((x_biased[num_obj-1:] - 0.5)**2)
    f = np.zeros(num_obj)
    for i in range(num_obj):
        f[i] = (1 + g) * np.prod(np.cos(x_biased[:num_obj-1-i] * np.pi / 2))
        if i > 0:
            f[i] *= np.sin(x_biased[num_obj-i] * np.pi / 2)
    return f

def dtlz5(x, num_obj=3):
    dim = len(x)
    k = dim - num_obj + 1
    theta = x[0] * np.pi / 2
    for i in range(1, num_obj-1):
        theta = (x[i] * np.pi / 2) * theta
    x_transformed = np.zeros_like(x)
    x_transformed[0] = np.cos(theta)
    for i in range(1, num_obj-1):
        x_transformed[i] = np.cos(theta) * np.prod(np.sin(x[:i] * np.pi / 2))
    x_transformed[num_obj-1:] = x[num_obj-1:]
    g = np.sum((x_transformed[num_obj-1:] - 0.5)**2)
    f = np.zeros(num_obj)
    for i in range(num_obj):
        f[i] = (1 + g) * np.prod(np.cos(x_transformed[:num_obj-1-i] * np.pi / 2))
        if i > 0:
            f[i] *= np.sin(x_transformed[num_obj-i] * np.pi / 2)
    return f

def dtlz6(x, num_obj=3):
    dim = len(x)
    k = dim - num_obj + 1
    g = np.sum((x[num_obj-1:] ** 0.1) ** 2)
    f = np.zeros(num_obj)
    for i in range(num_obj):
        f[i] = (1 + g) * np.prod(np.cos(x[:num_obj-1-i] * np.pi / 2))
        if i > 0:
            f[i] *= np.sin(x[num_obj-i] * np.pi / 2)
    return f

def dtlz7(x, num_obj=3):
    dim = len(x)
    k = dim - num_obj + 1
    g = 1 + 9 * np.mean(x[num_obj-1:])
    f = np.zeros(num_obj)
    for i in range(num_obj-1):
        f[i] = x[i]
    h = num_obj - np.sum([f[i]/(1 + g) * (1 + np.sin(3 * np.pi * f[i])) for i in range(num_obj-1)], axis=0)
    f[-1] = (1 + g) * h
    return f

# 函数-范围映射
func_bounds = {
    cec2021_f01: (-100, 100),
    cec2021_f02: (-100, 100),
    cec2021_f03: (-100, 100),
    cec2021_f04: (-100, 100),
    cec2021_f05: (-100, 100),
    cec2021_f06: (-100, 100),
    cec2021_f07: (-100, 100),
    cec2021_f08: (-100, 100),
    cec2021_f09: (-100, 100),
    cec2021_f10: (-100, 100),
    dtlz1: (0, 1),
    dtlz2: (0, 1),
    dtlz3: (0, 1),
    dtlz4: (0, 1),
    dtlz5: (0, 1),
    dtlz6: (0, 1),
    dtlz7: (0, 1),
}

# 多目标性能指标：IGD

def calculate_igd(population, true_pareto):
    # 添加输入检查和调试信息
    if isinstance(population, torch.Tensor):
        if population.ndim == 0:
            print(f"ERROR: population是标量张量 (0维)")
            return torch.tensor(0.0, device=population.device)
        elif population.ndim == 1:
            print(f"WARNING: population是一维张量，将扩展为二维")
            population = population.unsqueeze(0)
    else:
        if population.ndim == 0:
            print(f"ERROR: population是标量")
            return 0.0
        elif population.ndim == 1:
            print(f"WARNING: population是一维数组，将扩展为二维")
            population = population.reshape(1, -1)
    
    if isinstance(true_pareto, torch.Tensor):
        if true_pareto.ndim == 0:
            print(f"ERROR: true_pareto是标量张量 (0维)")
            return torch.tensor(0.0, device=population.device)
        elif true_pareto.ndim == 1:
            print(f"WARNING: true_pareto是一维张量，将扩展为二维")
            true_pareto = true_pareto.unsqueeze(0)
    else:
        if true_pareto.ndim == 0:
            print(f"ERROR: true_pareto是标量")
            return 0.0
        elif true_pareto.ndim == 1:
            print(f"WARNING: true_pareto是一维数组，将扩展为二维")
            true_pareto = true_pareto.reshape(1, -1)
    
    # 检查是否为PyTorch张量
    if isinstance(population, torch.Tensor) and isinstance(true_pareto, torch.Tensor):
        # GPU加速版本：使用广播计算所有点对之间的距离
        try:
            population = population.unsqueeze(1)  # (pop_size, 1, num_obj)
            true_pareto = true_pareto.unsqueeze(0)  # (1, pareto_size, num_obj)
            distances = torch.sqrt(torch.sum((population - true_pareto)**2, dim=2))  # (pop_size, pareto_size)
            min_distances = torch.min(distances, dim=0)[0]  # (pareto_size,)
            igd = torch.mean(min_distances)
            return igd
        except Exception as e:
            print(f"ERROR in calculate_igd (GPU): {e}")
            print(f"  population shape: {population.shape}")
            print(f"  true_pareto shape: {true_pareto.shape}")
            return torch.tensor(0.0, device=population.device)
    # 兼容NumPy的版本
    try:
        # 计算所有点对之间的距离
        distances = np.sqrt(np.sum((population[:, np.newaxis, :] - true_pareto[np.newaxis, :, :])**2, axis=2))
        min_distances = np.min(distances, axis=0)
        igd = np.mean(min_distances)
        return igd
    except Exception as e:
        print(f"ERROR in calculate_igd (NumPy): {e}")
        print(f"  population shape: {population.shape}")
        print(f"  true_pareto shape: {true_pareto.shape}")
        return 0.0

def generate_true_pareto_dtlz(func, num_obj=3, num_points=100):
    """
    生成DTLZ系列函数的真实Pareto前沿
    
    参数:
        func: DTLZ测试函数
        num_obj: 目标函数数量
        num_points: 生成的点数量
        
    返回:
        真实Pareto前沿点集，形状为 (num_points, num_obj)
    """
    if func == dtlz1:
        # DTLZ1的Pareto前沿是超平面，满足所有目标函数值之和等于0.5
        pareto = []
        for _ in range(num_points):
            # 生成满足条件的随机点
            x = np.random.rand(num_obj - 1)
            x = np.sort(x)
            x = np.insert(x, 0, 0)
            x = np.append(x, 1)
            
            f = np.zeros(num_obj)
            for i in range(num_obj):
                f[i] = 0.5 * np.prod(x[:num_obj - i]) * (1 - x[num_obj - i])
            pareto.append(f)
    elif func in [dtlz2, dtlz3]:
        # DTLZ2和DTLZ3的Pareto前沿是超球面的一部分
        pareto = []
        for _ in range(num_points):
            # 生成随机角度
            theta = np.random.rand(num_obj - 1) * np.pi / 2
            
            f = np.zeros(num_obj)
            for i in range(num_obj):
                if i == 0:
                    f[i] = np.cos(theta[0])
                elif i < num_obj - 1:
                    f[i] = np.cos(theta[i]) * np.prod(np.sin(theta[:i]))
                else:
                    f[i] = np.prod(np.sin(theta))
            pareto.append(f)
    else:
        raise ValueError(f"不支持的函数类型: {func.__name__}")
    
    return np.array(pareto)

# ===================== 工具类与算法类（保持不变） =====================
class SimpleANN(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, lr=0.01, device=None):
        super(SimpleANN, self).__init__()
        self.device = device if device is not None else (torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
        
        # 定义网络结构
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.sigmoid = nn.Sigmoid()
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        
        # 初始化权重
        nn.init.normal_(self.fc1.weight, mean=0.0, std=0.1)
        nn.init.normal_(self.fc1.bias, mean=0.0, std=0.1)
        nn.init.normal_(self.fc2.weight, mean=0.0, std=0.1)
        nn.init.normal_(self.fc2.bias, mean=0.0, std=0.1)
        
        # 设置优化器
        self.optimizer = optim.SGD(self.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        
        # 移动到指定设备
        self.to(self.device)

    def forward(self, x):
        # 如果输入是numpy数组，转换为torch张量
        if isinstance(x, np.ndarray):
            x = torch.tensor(x, dtype=torch.float32, device=self.device)
        h = self.sigmoid(self.fc1(x))
        out = self.fc2(h)
        return out

    def train(self, X, y):
        # 转换为torch张量
        if isinstance(X, np.ndarray):
            X = torch.tensor(X, dtype=torch.float32, device=self.device)
        if isinstance(y, np.ndarray):
            y = torch.tensor(y, dtype=torch.float32, device=self.device)
        
        # 前向传播
        self.optimizer.zero_grad()
        output = self.forward(X)
        
        # 计算损失并反向传播
        loss = self.loss_fn(output, y)
        loss.backward()
        self.optimizer.step()
        
        return loss.item()

class StandardPSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500, w=0.7, c1=1.5, c2=1.5, bounds=(-5.12, 5.12), is_multi_obj=False, num_obj=3):
        self.func = func
        self.dim = dim
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.bounds = bounds
        self.is_multi_obj = is_multi_obj
        self.num_obj = num_obj
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if self.is_multi_obj:
            self.true_pareto = generate_true_pareto_dtlz(func, num_obj)
            # 创建PyTorch张量用于GPU计算
            self.true_pareto_tensor = torch.tensor(self.true_pareto, dtype=torch.float32, device=self.device)

        # 使用PyTorch创建张量并移动到设备
        self.X = torch.FloatTensor(pop_size, dim).uniform_(bounds[0], bounds[1]).to(self.device)
        self.V = torch.FloatTensor(pop_size, dim).uniform_(-1, 1).to(self.device)
        self.pBest = self.X.clone()
        
        # 计算初始适应度
        if self.is_multi_obj:
            # 使用批量处理计算所有粒子的目标函数值
            population_objs = self.func(self.X, num_obj=self.num_obj)
            # 直接在GPU上计算IGD值
            self.pBest_fit = torch.zeros(self.pop_size, device=self.device)
            self.gBest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
            # 在多目标优化中，我们只需要一个全局最优代表
            self.gBest = self.X[0].clone()
        else:
            # 使用批量处理函数直接计算所有粒子的适应度值
            self.pBest_fit = self.func(self.X)  # 返回 (pop_size,)
            
            self.gBest_idx = torch.argmin(self.pBest_fit)
            self.gBest = self.pBest[self.gBest_idx].clone()
            self.gBest_fit = self.pBest_fit[self.gBest_idx]
        self.convergence_curve = []
        self.metadata = {"strategy": "Standard PSO"}

    def run(self):
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            # 生成随机数张量
            r1 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
            r2 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
            
            # 更新速度和位置
            self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest.unsqueeze(0) - self.X)
            self.X = self.X + self.V
            
            # 边界处理
            self.X = torch.clamp(self.X, self.bounds[0], self.bounds[1])

            # 计算新的适应度
            if self.is_multi_obj:
                # 使用批量处理计算所有粒子的目标函数值
                population_objs = self.func(self.X, num_obj=self.num_obj)
                # 直接在GPU上计算IGD值
                new_gbest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
                # 在多目标优化中，我们只更新全局最优
                if new_gbest_fit < self.gBest_fit:
                    # 选择当前种群中最接近Pareto前沿的粒子作为新的全局最优
                    # 这里简单地选择第一个粒子作为代表
                    self.gBest = self.X[0].clone()
                    self.gBest_fit = new_gbest_fit
            else:
                # 使用批量处理函数直接计算所有粒子的适应度值
                new_fit = self.func(self.X)  # 返回 (pop_size,)
                # 更新个体最优和全局最优
                update_mask = new_fit < self.pBest_fit
                self.pBest[update_mask] = self.X[update_mask]
                self.pBest_fit[update_mask] = new_fit[update_mask]
                
                current_gBest_idx = torch.argmin(self.pBest_fit)
                current_gBest_fit = self.pBest_fit[current_gBest_idx]
                if current_gBest_fit < self.gBest_fit:
                    self.gBest = self.pBest[current_gBest_idx].clone()
                    self.gBest_fit = current_gBest_fit

            # 记录收敛曲线（转换为numpy以便后续处理）
            self.convergence_curve.append(self.gBest_fit.detach().cpu().numpy())

        return self.gBest.detach().cpu().numpy(), self.gBest_fit.detach().cpu().numpy(), np.array(self.convergence_curve)

class LEO_PSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12), is_multi_obj=False, num_obj=3):
        self.func = func
        self.dim = dim
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.lp = lp
        self.arch_size = arch_size
        self.alpha = alpha
        self.beta = beta
        self.bounds = bounds
        self.is_multi_obj = is_multi_obj
        self.num_obj = num_obj
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if self.is_multi_obj:
            self.true_pareto = generate_true_pareto_dtlz(func, num_obj)
            # 创建PyTorch张量用于GPU计算
            self.true_pareto_tensor = torch.tensor(self.true_pareto, dtype=torch.float32, device=self.device)

        self.ann = SimpleANN(input_dim=dim, hidden_dim=3*dim, output_dim=dim, lr=ann_lr, device=self.device)
        self.arch = []

        # 使用PyTorch创建张量并移动到设备
        self.X = torch.FloatTensor(pop_size, dim).uniform_(bounds[0], bounds[1]).to(self.device)
        self.V = torch.FloatTensor(pop_size, dim).uniform_(-1, 1).to(self.device)
        self.pBest = self.X.clone()
        
        # 计算初始适应度
        if self.is_multi_obj:
            # 使用批量处理计算所有粒子的目标函数值
            population_objs = self.func(self.X, num_obj=self.num_obj)
            # 直接在GPU上计算IGD值
            self.pBest_fit = torch.zeros(self.pop_size, device=self.device)
            self.gBest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
            # 在多目标优化中，我们只需要一个全局最优代表
            self.gBest = self.X[0].clone()
        else:
            # 使用批量处理函数直接计算所有粒子的适应度值
            self.pBest_fit = self.func(self.X)  # 返回 (pop_size,)
            
            self.gBest_idx = torch.argmin(self.pBest_fit)
            self.gBest = self.pBest[self.gBest_idx].clone()
            self.gBest_fit = self.pBest_fit[self.gBest_idx]
        self.convergence_curve = []
        self.metadata = {"strategy": "LEO-PSO (原版)", "components": ["ANN", "正向经验"]}

    def learning_aided_mutation(self, pBest_i):
        r1, r2 = random.sample(range(self.pop_size), 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        L_pBest = self.ann.forward(pBest_i.reshape(1, -1)).flatten()
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX

    def learning_aided_crossover(self, pBest_i, newX):
        cross_mask = torch.FloatTensor(self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, newX, pBest_i)
        return final_X
    
    def batch_build_context_vectors(self, iteration, total_iter):
        """批量构建所有粒子的上下文向量"""
        pos = self.X  # (pop_size, dim)
        vel = self.V  # (pop_size, dim)
        pbest = self.pBest  # (pop_size, dim)
        gbest = self.gBest.unsqueeze(0).repeat(self.pop_size, 1)  # (pop_size, dim)
        
        # 批量计算邻居均值和适应度方差
        neighbor_means = torch.zeros_like(self.X)
        fit_variances = torch.zeros(self.pop_size, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            neighbor_means[i] = torch.mean(self.pBest[neighbors], axis=0)
            fit_variances[i] = torch.var(self.pBest_fit[neighbors])
        
        progress = torch.full((self.pop_size, 1), iteration / total_iter, device=self.device)  # (pop_size, 1)
        fit_variance = fit_variances.unsqueeze(1)  # (pop_size, 1)
        
        # 拼接所有上下文向量
        contexts = torch.cat([pos, vel, pbest, gbest, neighbor_means, progress, fit_variance], dim=1)
        return contexts
    
    def batch_learning_aided_mutation(self, contexts):
        """批量执行学习辅助变异"""
        # 批量ANN前向传播
        L_pBest = self.ann.forward(contexts)  # (pop_size, dim)
        
        # 为每个粒子随机选择两个邻居用于变异
        r1_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        r2_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            r1, r2 = random.sample(neighbors, 2)
            r1_indices[i] = r1
            r2_indices[i] = r2
        
        pBest_r1 = self.pBest[r1_indices]
        pBest_r2 = self.pBest[r2_indices]
        
        # 批量执行变异
        new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return new_X.detach()
    
    def batch_learning_aided_crossover(self, pBest, new_X):
        """批量执行学习辅助交叉"""
        cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, new_X, pBest)
        return final_X
    
    def run(self):
        g = 0
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            
            if g > 1 and r < self.lp:
                # 批量处理学习辅助变异和交叉，提高GPU利用率
                # 随机选择两个粒子用于变异
                r1_indices = torch.randint(0, self.pop_size, (self.pop_size,), device=self.device)
                r2_indices = torch.randint(0, self.pop_size, (self.pop_size,), device=self.device)
                pBest_r1 = self.pBest[r1_indices]
                pBest_r2 = self.pBest[r2_indices]
                
                # 批量执行ANN前向传播
                L_pBest = self.ann.forward(self.pBest)
                
                # 批量执行变异
                new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
                
                # 批量执行交叉
                cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
                new_X = torch.where(cross_mask, new_X, self.pBest)
                
                # 边界处理
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])
            else:
                r1 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                r2 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest.unsqueeze(0) - self.X)
                new_X = self.X + self.V
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])

            # 计算新的适应度
            if self.is_multi_obj:
                # 使用批量处理函数直接计算所有粒子的目标函数值
                population_objs = self.func(new_X, num_obj=self.num_obj)
                # 直接在GPU上计算IGD值
                new_gbest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
                # 在多目标优化中，我们只更新全局最优
                if new_gbest_fit < self.gBest_fit:
                    self.gBest = new_X[0].clone()
                    self.gBest_fit = new_gbest_fit
                self.X = new_X
                # 多目标优化中不更新个体最优和经验库
            else:
                # 使用批量处理函数直接计算所有粒子的适应度值
                new_fit = self.func(new_X)  # 返回 (pop_size,)
                
                pBest_old = self.pBest.clone()
                pBest_fit_old = self.pBest_fit.clone()
                update_mask = new_fit < self.pBest_fit
                self.pBest[update_mask] = new_X[update_mask]
                self.pBest_fit[update_mask] = new_fit[update_mask]
                
                current_gBest_idx = torch.argmin(self.pBest_fit)
                current_gBest_fit = self.pBest_fit[current_gBest_idx]
                if current_gBest_fit < self.gBest_fit:
                    self.gBest = self.pBest[current_gBest_idx].clone()
                    self.gBest_fit = current_gBest_fit
                self.X = new_X

                # 更新经验库
                for i in range(self.pop_size):
                    if self.pBest_fit[i] < pBest_fit_old[i]:
                        self.arch.append((pBest_old[i].detach().cpu().numpy(), self.pBest[i].detach().cpu().numpy()))

            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            # 训练ANN
            if len(self.arch) > 0:
                X_train = np.array([sep[0] for sep in self.arch])
                y_train = np.array([sep[1] for sep in self.arch])
                self.ann.train(X_train, y_train)

            # 记录收敛曲线
            self.convergence_curve.append(self.gBest_fit.detach().cpu().numpy())

        return self.gBest.detach().cpu().numpy(), self.gBest_fit.detach().cpu().numpy(), np.array(self.convergence_curve)

class LEO_CV_PSO(LEO_PSO):
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12), is_multi_obj=False, num_obj=3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds, is_multi_obj, num_obj)
        self.context_dim = 4 * dim + 1
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr, device=self.device)
        self.metadata = {"strategy": "LEO+上下文向量", "components": ["ANN", "正向经验", "上下文向量"]}
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        pos = self.X[particle_idx]
        vel = self.V[particle_idx]
        pbest = self.pBest[particle_idx]
        gbest = self.gBest
        progress = torch.tensor(iteration / total_iter, device=self.device)
        context = torch.cat([pos, vel, pbest, gbest, progress.unsqueeze(0)])
        return context
    
    def learning_aided_mutation(self, pBest_i, context):
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        r1, r2 = random.sample(range(self.pop_size), 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX
    
    def learning_aided_crossover(self, pBest_i, newX):
        cross_mask = torch.FloatTensor(self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, newX, pBest_i)
        return final_X
    
    def batch_build_context_vectors(self, iteration, total_iter):
        """批量构建所有粒子的上下文向量"""
        pos = self.X  # (pop_size, dim)
        vel = self.V  # (pop_size, dim)
        pbest = self.pBest  # (pop_size, dim)
        gbest = self.gBest.unsqueeze(0).repeat(self.pop_size, 1)  # (pop_size, dim)
        
        # 批量计算邻居均值和适应度方差
        neighbor_means = torch.zeros_like(self.X)
        fit_variances = torch.zeros(self.pop_size, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            neighbor_means[i] = torch.mean(self.pBest[neighbors], axis=0)
            fit_variances[i] = torch.var(self.pBest_fit[neighbors])
        
        progress = torch.full((self.pop_size, 1), iteration / total_iter, device=self.device)  # (pop_size, 1)
        fit_variance = fit_variances.unsqueeze(1)  # (pop_size, 1)
        
        # 拼接所有上下文向量
        contexts = torch.cat([pos, vel, pbest, gbest, neighbor_means, progress, fit_variance], dim=1)
        return contexts
    
    def batch_learning_aided_mutation(self, contexts):
        """批量执行学习辅助变异"""
        # 批量ANN前向传播
        L_pBest = self.ann.forward(contexts)  # (pop_size, dim)
        
        # 为每个粒子随机选择两个邻居用于变异
        r1_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        r2_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            r1, r2 = random.sample(neighbors, 2)
            r1_indices[i] = r1
            r2_indices[i] = r2
        
        pBest_r1 = self.pBest[r1_indices]
        pBest_r2 = self.pBest[r2_indices]
        
        # 批量执行变异
        new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return new_X
    
    def batch_learning_aided_crossover(self, pBest, new_X):
        """批量执行学习辅助交叉"""
        cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, new_X, pBest)
        return final_X
    
    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            contexts = [self.build_context_vector(i, iteration, self.max_iter) for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                # 批量处理学习辅助变异和交叉
                contexts_tensor = torch.stack(contexts)
                
                # 批量执行ANN前向传播
                L_pBest = self.ann.forward(contexts_tensor)
                
                # 随机选择两个粒子用于变异
                r1_indices = torch.randint(0, self.pop_size, (self.pop_size,), device=self.device)
                r2_indices = torch.randint(0, self.pop_size, (self.pop_size,), device=self.device)
                pBest_r1 = self.pBest[r1_indices]
                pBest_r2 = self.pBest[r2_indices]
                
                # 批量执行变异
                new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
                
                # 批量执行交叉
                cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
                new_X = torch.where(cross_mask, new_X, self.pBest)
                
                # 边界处理
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])
            else:
                r1 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                r2 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest.unsqueeze(0) - self.X)
                new_X = self.X + self.V
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])

            if self.is_multi_obj:
                # 使用批量处理计算所有粒子的目标函数值
                population_objs = self.func(new_X, num_obj=self.num_obj)
                # 直接在GPU上计算IGD值
                new_gbest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
                # 在多目标优化中，我们只更新全局最优
                if new_gbest_fit < self.gBest_fit:
                    self.gBest = new_X[0].clone()
                    self.gBest_fit = new_gbest_fit
                self.X = new_X
                # 多目标优化中不更新个体最优和经验库
            else:
                # 使用批量处理函数直接计算所有粒子的适应度值
                new_fit = self.func(new_X)  # 返回 (pop_size,)
                
                pBest_old = self.pBest.clone()
                pBest_fit_old = self.pBest_fit.clone()
                update_mask = new_fit < self.pBest_fit
                self.pBest[update_mask] = new_X[update_mask]
                self.pBest_fit[update_mask] = new_fit[update_mask]
                current_gBest_idx = torch.argmin(self.pBest_fit)
                current_gBest_fit = self.pBest_fit[current_gBest_idx]
                if current_gBest_fit < self.gBest_fit:
                    self.gBest = self.pBest[current_gBest_idx].clone()
                    self.gBest_fit = current_gBest_fit
                self.X = new_X

                # 只有在使用批量处理的迭代中才更新arch
                if g > 1 and r < self.lp:
                    for i in range(self.pop_size):
                        if self.pBest_fit[i] < pBest_fit_old[i]:
                            success_direction = self.pBest[i] - pBest_old[i]
                            self.arch.append((contexts[i].detach().cpu().numpy(), success_direction.detach().cpu().numpy()))

            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit.detach().cpu().numpy())

        return self.gBest.detach().cpu().numpy(), self.gBest_fit.detach().cpu().numpy(), np.array(self.convergence_curve)

class LEO_LN_PSO(LEO_PSO):
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12), is_multi_obj=False, num_obj=3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds, is_multi_obj, num_obj)
        self.k_neighbors = 5
        self.neighborhood = self.create_ring_topology()
        self.metadata = {"strategy": "LEO+局部邻居", "components": ["ANN", "正向经验", "局部邻居"]}
    
    def create_ring_topology(self):
        topology = {}
        for i in range(self.pop_size):
            neighbors = []
            for j in range(1, self.k_neighbors // 2 + 1):
                neighbors.append((i - j) % self.pop_size)
                neighbors.append((i + j) % self.pop_size)
            if self.k_neighbors % 2 == 1:
                neighbors.append((i + self.k_neighbors) % self.pop_size)
            topology[i] = neighbors[:self.k_neighbors]
        return topology
    
    def learning_aided_mutation(self, pBest_i, particle_idx):
        L_pBest = self.ann.forward(pBest_i.reshape(1, -1)).flatten()
        neighbors = self.neighborhood[particle_idx]
        r1, r2 = random.sample(neighbors, 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX
    
    def learning_aided_crossover(self, pBest_i, newX):
        cross_mask = torch.FloatTensor(self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, newX, pBest_i)
        return final_X
    
    def batch_build_context_vectors(self, iteration, total_iter):
        pos = self.X  # (pop_size, dim)
        vel = self.V  # (pop_size, dim)
        pbest = self.pBest  # (pop_size, dim)
        gbest = self.gBest.unsqueeze(0).repeat(self.pop_size, 1)  # (pop_size, dim)
        neighbor_means = torch.zeros_like(self.X)
        fit_variances = torch.zeros(self.pop_size, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            neighbor_means[i] = torch.mean(self.pBest[neighbors], axis=0)
            fit_variances[i] = torch.var(self.pBest_fit[neighbors])
        progress = torch.full((self.pop_size, 1), iteration / total_iter, device=self.device)
        fit_variance = fit_variances.unsqueeze(1)
        contexts = torch.cat([pos, vel, pbest, gbest, neighbor_means, progress, fit_variance], dim=1)
        return contexts
    
    def batch_learning_aided_mutation(self, contexts):
        L_pBest = self.ann.forward(contexts)  # (pop_size, dim)
        r1_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        r2_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            r1, r2 = random.sample(neighbors, 2)
            r1_indices[i] = r1
            r2_indices[i] = r2
        pBest_r1 = self.pBest[r1_indices]
        pBest_r2 = self.pBest[r2_indices]
        new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return new_X.detach()
    
    def batch_learning_aided_crossover(self, pBest, new_X):
        cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, new_X, pBest)
        return final_X
    
    def run(self):
        g = 0
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            if g > 1 and r < self.lp:
                # 批量处理学习辅助变异和交叉
                # 批量执行ANN前向传播
                L_pBest = self.ann.forward(self.pBest)
                
                # 为每个粒子随机选择两个邻居用于变异
                r1_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
                r2_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
                for i in range(self.pop_size):
                    neighbors = self.neighborhood[i]
                    r1, r2 = random.sample(neighbors, 2)
                    r1_indices[i] = r1
                    r2_indices[i] = r2
                
                pBest_r1 = self.pBest[r1_indices]
                pBest_r2 = self.pBest[r2_indices]
                
                # 批量执行变异
                new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
                
                # 批量执行交叉
                cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
                new_X = torch.where(cross_mask, new_X, self.pBest)
                
                # 边界处理
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])
            else:
                r1 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                r2 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest.unsqueeze(0) - self.X)
                new_X = self.X + self.V
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])

            if self.is_multi_obj:
                # 使用批量处理计算所有粒子的目标函数值
                population_objs = self.func(new_X, num_obj=self.num_obj)
                # 直接在GPU上计算IGD值
                new_gbest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
                # 在多目标优化中，我们只更新全局最优
                if new_gbest_fit < self.gBest_fit:
                    self.gBest = new_X[0].clone()
                    self.gBest_fit = new_gbest_fit
                self.X = new_X
                # 多目标优化中不更新个体最优和经验库
            else:
                # 使用批量处理函数直接计算所有粒子的适应度值
                new_fit = self.func(new_X)  # 返回 (pop_size,)
                
                pBest_old = self.pBest.clone()
                pBest_fit_old = self.pBest_fit.clone()
                update_mask = new_fit < self.pBest_fit
                self.pBest[update_mask] = new_X[update_mask]
                self.pBest_fit[update_mask] = new_fit[update_mask]
                current_gBest_idx = torch.argmin(self.pBest_fit)
                current_gBest_fit = self.pBest_fit[current_gBest_idx]
                if current_gBest_fit < self.gBest_fit:
                    self.gBest = self.pBest[current_gBest_idx].clone()
                    self.gBest_fit = current_gBest_fit
                self.X = new_X

                for i in range(self.pop_size):
                    if self.pBest_fit[i] < pBest_fit_old[i]:
                        self.arch.append((pBest_old[i].detach().cpu().numpy(), self.pBest[i].detach().cpu().numpy()))

            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            if len(self.arch) > 0:
                X_train = np.array([sep[0] for sep in self.arch])
                y_train = np.array([sep[1] for sep in self.arch])
                self.ann.train(X_train, y_train)

            self.convergence_curve.append(self.gBest_fit.detach().cpu().numpy())

        return self.gBest.detach().cpu().numpy(), self.gBest_fit.detach().cpu().numpy(), np.array(self.convergence_curve)

class LEO_CV_LN_PSO(LEO_PSO):
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12), is_multi_obj=False, num_obj=3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds, is_multi_obj, num_obj)
        self.context_dim = 5 * dim + 2
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr, device=self.device)
        self.k_neighbors = 5
        self.neighborhood = self.create_ring_topology()
        self.arch = deque(maxlen=arch_size)
        self.metadata = {"strategy": "LEO+上下文向量+局部邻居", "components": ["ANN", "正向经验", "上下文向量", "局部邻居"]}
    
    def create_ring_topology(self):
        topology = {}
        for i in range(self.pop_size):
            neighbors = []
            for j in range(1, self.k_neighbors // 2 + 1):
                neighbors.append((i - j) % self.pop_size)
                neighbors.append((i + j) % self.pop_size)
            if self.k_neighbors % 2 == 1:
                neighbors.append((i + self.k_neighbors) % self.pop_size)
            topology[i] = neighbors[:self.k_neighbors]
        return topology
    
    def get_neighborhood_info(self, particle_idx):
        neighbors = self.neighborhood[particle_idx]
        neighbor_pbests = self.pBest[neighbors]
        neighbor_mean = torch.mean(neighbor_pbests, axis=0)
        neighbor_fits = self.pBest_fit[neighbors]
        fit_variance = torch.var(neighbor_fits)
        return neighbor_mean, fit_variance
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        pos = self.X[particle_idx]
        vel = self.V[particle_idx]
        pbest = self.pBest[particle_idx]
        gbest = self.gBest
        neighbor_mean, fit_variance = self.get_neighborhood_info(particle_idx)
        progress = torch.tensor(iteration / total_iter, device=self.device)
        context = torch.cat([pos, vel, pbest, gbest, neighbor_mean, progress.unsqueeze(0), fit_variance.unsqueeze(0)])
        return context
    
    def learning_aided_mutation(self, context, particle_idx):
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        neighbors = self.neighborhood[particle_idx]
        r1, r2 = random.sample(neighbors, 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX
    
    def learning_aided_crossover(self, pBest_i, newX):
        cross_mask = torch.FloatTensor(self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, newX, pBest_i)
        return final_X
    
    def batch_build_context_vectors(self, iteration, total_iter):
        pos = self.X  # (pop_size, dim)
        vel = self.V  # (pop_size, dim)
        pbest = self.pBest  # (pop_size, dim)
        gbest = self.gBest.unsqueeze(0).repeat(self.pop_size, 1)  # (pop_size, dim)
        neighbor_means = torch.zeros_like(self.X)
        fit_variances = torch.zeros(self.pop_size, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            neighbor_means[i] = torch.mean(self.pBest[neighbors], axis=0)
            fit_variances[i] = torch.var(self.pBest_fit[neighbors])
        progress = torch.full((self.pop_size, 1), iteration / total_iter, device=self.device)
        fit_variance = fit_variances.unsqueeze(1)
        contexts = torch.cat([pos, vel, pbest, gbest, neighbor_means, progress, fit_variance], dim=1)
        return contexts
    
    def batch_learning_aided_mutation(self, contexts):
        L_pBest = self.ann.forward(contexts)  # (pop_size, dim)
        r1_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        r2_indices = torch.zeros(self.pop_size, dtype=torch.long, device=self.device)
        for i in range(self.pop_size):
            neighbors = self.neighborhood[i]
            r1, r2 = random.sample(neighbors, 2)
            r1_indices[i] = r1
            r2_indices[i] = r2
        pBest_r1 = self.pBest[r1_indices]
        pBest_r2 = self.pBest[r2_indices]
        new_X = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return new_X
    
    def batch_learning_aided_crossover(self, pBest, new_X):
        cross_mask = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device) <= self.beta
        final_X = torch.where(cross_mask, new_X, pBest)
        return final_X
    
    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            
            if g > 1 and r < self.lp:
                # 使用批量处理方法构建上下文向量
                contexts = self.batch_build_context_vectors(iteration, self.max_iter)
                # 使用批量学习辅助变异
                new_X = self.batch_learning_aided_mutation(contexts)
                # 使用批量学习辅助交叉
                new_X = self.batch_learning_aided_crossover(self.pBest, new_X)
                # 限制粒子位置在边界内
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])
            else:
                r1 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                r2 = torch.FloatTensor(self.pop_size, self.dim).uniform_(0, 1).to(self.device)
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest.unsqueeze(0) - self.X)
                new_X = self.X + self.V
                new_X = torch.clamp(new_X, self.bounds[0], self.bounds[1])

            if self.is_multi_obj:
                # 批量计算所有粒子的目标函数值
                population_objs = self.func(new_X, num_obj=self.num_obj)
                # 直接在GPU上计算IGD值
                new_gbest_fit = calculate_igd(population_objs, self.true_pareto_tensor)
                # 在多目标优化中，我们只更新全局最优
                if new_gbest_fit < self.gBest_fit:
                    self.gBest = new_X[0].clone()
                    self.gBest_fit = new_gbest_fit
                self.X = new_X
                # 多目标优化中不更新个体最优和经验库
            else:
                # 批量计算所有粒子的适应度值
                new_fit = self.func(new_X)
                
                pBest_old = self.pBest.clone()
                pBest_fit_old = self.pBest_fit.clone()
                update_mask = new_fit < self.pBest_fit
                self.pBest[update_mask] = new_X[update_mask]
                self.pBest_fit[update_mask] = new_fit[update_mask]
                current_gBest_idx = torch.argmin(self.pBest_fit)
                current_gBest_fit = self.pBest_fit[current_gBest_idx]
                if current_gBest_fit < self.gBest_fit:
                    self.gBest = self.pBest[current_gBest_idx].clone()
                    self.gBest_fit = current_gBest_fit
                self.X = new_X

                # 只有在使用批量处理的迭代中才更新arch
                if g > 1 and r < self.lp:
                    for i in range(self.pop_size):
                        if self.pBest_fit[i] < pBest_fit_old[i]:
                            success_direction = self.pBest[i] - pBest_old[i]
                            self.arch.append((contexts[i].detach().cpu().numpy(), success_direction.detach().cpu().numpy()))

                if len(self.arch) >= 10:
                    contexts_batch = np.array([exp[0] for exp in self.arch])
                    directions_batch = np.array([exp[1] for exp in self.arch])
                    self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit.detach().cpu().numpy())

        return self.gBest.detach().cpu().numpy(), self.gBest_fit.detach().cpu().numpy(), np.array(self.convergence_curve)

# ===================== 新增：实验结果保存工具函数 =====================
def save_experiment_results(results, stats, performance_improvement, func_name, dim, max_iter, runs, is_multi_obj):
    """保存实验结果（增加维度标识，避免不同维度结果覆盖）"""
    metric_name = "IGD" if is_multi_obj else "最优适应度"
    
    # 1. 保存原始数据（含维度后缀）
    np.save(f"{func_name}_raw_results.npy", results)
    
    # 2. 保存统计数据
    stats_df = pd.DataFrame({
        "算法": list(stats.keys()),
        f"平均{metric_name}": [stats[algo]["mean"] for algo in stats],
        f"标准差": [stats[algo]["std"] for algo in stats],
        "成功运行次数": [stats[algo]["count"] for algo in stats],
        f"成功运行率(%)": [stats[algo]["count"]/runs*100 for algo in stats]
    })
    stats_df.to_csv(f"{func_name}_stats.csv", index=False, encoding="utf-8-sig")
    
    # 3. 保存收敛曲线数据
    conv_data = {}
    for algo_name in results:
        valid_curves = [c for c in results[algo_name]["convergence"] if not all(np.isinf(val) for val in c)]
        if len(valid_curves) > 0:
            conv_data[algo_name] = np.mean(valid_curves, axis=0)
    conv_df = pd.DataFrame(conv_data, index=range(max_iter))
    conv_df.to_csv(f"{func_name}_convergence_data.csv", index_label="迭代次数", encoding="utf-8-sig")
    
    # 4. 保存性能分析报告
    with open(f"{func_name}_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write(f"{'='*80}\n")
        f.write(f"{func_name}函数实验分析报告\n")
        f.write(f"{'='*80}\n")
        f.write(f"实验配置：维度={dim}，迭代次数={max_iter}，运行次数={runs}\n")
        f.write(f"评价指标：{metric_name}（越小越好）\n")
        f.write(f"{'='*80}\n\n")
        
        # 统计结果
        f.write("一、统计结果（均值±标准差）\n")
        for algo_name in stats:
            f.write(f"{algo_name:40s} | 均值: {stats[algo_name]['mean']:.10f} ± {stats[algo_name]['std']:.10f} | 成功运行: {stats[algo_name]['count']}/{runs}\n")
        
        # 性能提升
        f.write("\n二、性能提升（相对于LEO-PSO原版）\n")
        if performance_improvement:
            for algo_name, desc, improvement in performance_improvement:
                f.write(f"{algo_name:40s} | {desc:50s} | 提升: {improvement:.2f}%\n")
        else:
            f.write("无有效性能提升数据（原版LEO-PSO未成功运行）\n")
        
        # 算法排名
        f.write("\n三、算法性能排名（从优到劣）\n")
        algo_performance = {algo: stats[algo]["mean"] for algo in stats}
        sorted_algo = sorted(algo_performance.items(), key=lambda x: x[1])
        for i, (algo_name, perf) in enumerate(sorted_algo, 1):
            f.write(f"{i:2d}. {algo_name:40s} | 平均{metric_name}: {perf:.10f}\n")
    
    print(f"\n实验结果已保存以下文件（{func_name}）：")
    print(f"- {func_name}_raw_results.npy（原始数据）")
    print(f"- {func_name}_stats.csv（统计数据）")
    print(f"- {func_name}_convergence_data.csv（收敛曲线数据）")
    print(f"- {func_name}_analysis_report.txt（分析报告）")

# ===================== 并行计算工作函数 =====================
def run_single_algo(algo_info, func, dim, max_iter, pop_size, bounds, is_multi_obj, num_obj, run_seed):
    """运行单个算法-轮次组合"""
    algo_name, AlgoClass = algo_info
    
    # 设置独立的随机种子
    np.random.seed(run_seed)
    random.seed(run_seed)
    torch.manual_seed(run_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(run_seed)
        torch.cuda.manual_seed_all(run_seed)
    
    try:
        if algo_name == "Standard PSO":
            algo = AlgoClass(
                func=func,
                dim=dim,
                pop_size=pop_size,
                max_iter=max_iter,
                bounds=bounds,
                is_multi_obj=is_multi_obj,
                num_obj=num_obj
            )
        else:
            algo = AlgoClass(
                func=func,
                dim=dim,
                pop_size=pop_size,
                max_iter=max_iter,
                arch_size=100,
                ann_lr=0.01,
                bounds=bounds,
                is_multi_obj=is_multi_obj,
                num_obj=num_obj
            )
        
        _, best_fit, conv_curve = algo.run()
        
        # 显式清理PyTorch资源
        if hasattr(algo, 'ann') and algo.ann is not None:
            del algo.ann
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        return (algo_name, best_fit, conv_curve, None)
    except Exception as e:
        # 异常情况下也清理资源
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        return (algo_name, float('inf'), [float('inf')] * max_iter, str(e))

# ===================== 对比实验框架（集成结果保存） =====================
def compare_all_variants(func, func_name, dim=30, max_iter=500, runs=5, pop_size=100, is_multi_obj=False, num_obj=3):
    bounds = func_bounds.get(func, (-5.12, 5.12))
    
    algorithms = [
        ("Standard PSO", StandardPSO),
        ("LEO-PSO (原版)", LEO_PSO),
        ("LEO+上下文向量", LEO_CV_PSO),
        ("LEO+局部邻居", LEO_LN_PSO),
        ("LEO+上下文向量+局部邻居", LEO_CV_LN_PSO)
    ]
    
    # 中间结果文件名
    intermediate_file = f"{func_name}_intermediate_results.npy"
    
    # 检查是否存在中间结果
    results = {}
    current_run = 0
    
    # 扫描所有可能的中间结果文件
    import glob
    intermediate_files = glob.glob(f"{func_name}_intermediate_results*.npy")
    
    if intermediate_files:
        print(f"检测到中间结果文件：{intermediate_files}")
        # 选择最新的中间结果文件
        latest_file = max(intermediate_files, key=os.path.getmtime)
        print(f"正在加载最新的中间结果文件：{latest_file}...")
        
        try:
            # 加载中间结果
            temp_results = np.load(latest_file, allow_pickle=True).item()
            
            # 验证结果格式
            valid = True
            for algo_name, _ in algorithms:
                if algo_name not in temp_results:
                    print(f"警告：中间结果中缺少{algo_name}的数据")
                    valid = False
                    break
                if "best_fit" not in temp_results[algo_name] or "convergence" not in temp_results[algo_name]:
                    print(f"警告：{algo_name}的数据格式不正确")
                    valid = False
                    break
            
            if valid:
                # 检查所有算法的已完成轮次是否一致
                run_counts = []
                for algo_name, _ in algorithms:
                    run_count = len(temp_results[algo_name]["best_fit"])
                    run_counts.append(run_count)
                
                if all(count == run_counts[0] for count in run_counts):
                    results = temp_results
                    current_run = run_counts[0]
                    print(f"加载成功！已完成 {current_run}/{runs} 轮运行")
                else:
                    print("警告：不同算法的已完成轮次不一致，重新开始实验")
                    # 初始化结果字典
                    for name, _ in algorithms:
                        results[name] = {"best_fit": [], "convergence": []}
            else:
                print("警告：中间结果格式不正确，重新开始实验")
                # 初始化结果字典
                for name, _ in algorithms:
                    results[name] = {"best_fit": [], "convergence": []}
        except Exception as e:
            print(f"加载中间结果失败：{str(e)}，重新开始实验")
            # 初始化结果字典
            for name, _ in algorithms:
                results[name] = {"best_fit": [], "convergence": []}
    else:
        # 初始化结果字典
        for name, _ in algorithms:
            results[name] = {"best_fit": [], "convergence": []}
    
    metric_name = "IGD" if is_multi_obj else "最优适应度"
    print(f"\n{'='*60}")
    print(f"开始对比实验：{func_name}函数，维度={dim}，迭代={max_iter}，运行次数={runs}，范围={bounds}，指标={metric_name}")
    print(f"{'='*60}")
    
    # 导入multiprocessing库
    import multiprocessing as mp
    
    for run in range(current_run, runs):
        print(f"\n--- 第 {run+1}/{runs} 轮 ---")
        
        # 为每个算法创建任务
        tasks = []
        for algo_info in algorithms:
            # 使用不同的种子确保结果可重复
            run_seed = 42 + run * len(algorithms) + algorithms.index(algo_info)
            tasks.append((algo_info, func, dim, max_iter, pop_size, bounds, is_multi_obj, num_obj, run_seed))
        
        # 创建进程池，优化GPU利用率
        # 检测是否有GPU可用
        has_gpu = torch.cuda.is_available()
        if has_gpu:
            # GPU可用时，使用2-4个进程充分利用GPU并行能力
            # 同时考虑GPU内存大小，避免内存不足
            pool_size = min(len(algorithms), 2 if torch.cuda.get_device_properties(0).total_memory < 4 * 1024**3 else 4)
        else:
            # CPU模式下，使用更多进程
            pool_size = min(len(algorithms), mp.cpu_count())
        
        print(f"使用进程数: {pool_size} (GPU: {has_gpu})")
        
        # 使用try-except确保进程池正确关闭
        try:
            with mp.Pool(processes=pool_size) as pool:
                # 设置超时时间，避免进程池卡死
                results_list = pool.starmap(run_single_algo, tasks, chunksize=1)
            
            # 收集结果
            for result in results_list:
                algo_name, best_fit, conv_curve, error = result
                if error is None:
                    results[algo_name]["best_fit"].append(best_fit)
                    results[algo_name]["convergence"].append(conv_curve)
                    print(f"{algo_name:40s} | {metric_name}: {best_fit:.8f}")
                else:
                    print(f"{algo_name:40s} | 错误: {error}")
                    results[algo_name]["best_fit"].append(float('inf'))
                    results[algo_name]["convergence"].append([float('inf')] * max_iter)
            
            # 每轮运行后保存中间结果（带时间戳）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_file = f"{func_name}_intermediate_results_{timestamp}.npy"
            print(f"\n保存第 {run+1}/{runs} 轮的中间结果...")
            np.save(timestamped_file, results)
            print(f"中间结果已保存到：{timestamped_file}")
            
            # 更新主中间结果文件
            np.save(intermediate_file, results)
            
            # 清理旧的中间结果文件（保留最近3个）
            import glob
            all_intermediate = glob.glob(f"{func_name}_intermediate_results*.npy")
            if len(all_intermediate) > 3:
                # 按修改时间排序，保留最新的3个
                all_intermediate.sort(key=os.path.getmtime, reverse=True)
                for old_file in all_intermediate[3:]:
                    os.remove(old_file)
                    print(f"已清理旧中间结果文件：{old_file}")
                    
        except Exception as e:
            print(f"轮次 {run+1} 执行出错: {str(e)}")
            # 立即保存当前进度
            np.save(f"{func_name}_intermediate_results_error_{run+1}.npy", results)
            print(f"错误时进度已保存到：{func_name}_intermediate_results_error_{run+1}.npy")
        
        # 每轮结束后清理资源
        print(f"\n清理第 {run+1}/{runs} 轮的资源...")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        plt.close('all')
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"{func_name}函数对比结果（{runs}轮均值±标准差）")
    print(f"{'='*60}")
    
    stats = {}
    performance_improvement = []
    for algo_name in algorithms:
        name = algo_name[0]
        fits = [f for f in results[name]["best_fit"] if f != float('inf')]
        if len(fits) == 0:
            print(f"{name:40s} | 所有运行都失败")
            continue
        mean_fit = np.mean(fits)
        std_fit = np.std(fits)
        stats[name] = {"mean": mean_fit, "std": std_fit, "count": len(fits)}
        print(f"{name:40s} | 均值: {mean_fit:.10f} ± {std_fit:.10f} (成功运行: {len(fits)}/{runs})")
    
    # 性能提升分析（保存到列表，后续写入文件）
    if "LEO-PSO (原版)" in stats and stats["LEO-PSO (原版)"]["mean"] != 0:
        print(f"\n性能提升（相对于LEO-PSO原版）：")
        baseline = stats["LEO-PSO (原版)"]["mean"]
        comparisons = [
            ("LEO+上下文向量", "增加了上下文向量"),
            ("LEO+局部邻居", "增加了局部邻居"),
            ("LEO+上下文向量+局部邻居", "增加了上下文向量和局部邻居")
        ]
        for algo_name, description in comparisons:
            if algo_name in stats:
                improvement = (baseline - stats[algo_name]["mean"]) / baseline * 100
                print(f"{algo_name:40s} | {description:50s} | 提升: {improvement:.2f}%")
                performance_improvement.append((algo_name, description, improvement))
    
    # 可视化（仅保存不显示）
    print("\n开始可视化处理...")
    plot_convergence_curves(results, func_name, dim, max_iter, metric_name)
    print("- 收敛曲线绘制完成")
    plot_boxplot(results, func_name, metric_name)
    print("- 箱线图绘制完成")
    analyze_components(results, func_name)
    print("- 组件分析完成")
    
    # 保存实验结果
    print("\n保存实验结果...")
    save_experiment_results(results, stats, performance_improvement, func_name, dim, max_iter, runs, is_multi_obj)
    print("- 结果保存完成")
    
    # 清理资源
    print("\n清理资源...")
    # 显式清理PyTorch资源
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    # 清理matplotlib资源
    plt.close('all')
    
    # 实验完成后删除中间结果文件
    if os.path.exists(intermediate_file):
        os.remove(intermediate_file)
        print(f"- 已删除中间结果文件：{intermediate_file}")
    
    print("\n资源清理完成")
    
    return results, stats

# ===================== 可视化函数（保持不变） =====================
def plot_convergence_curves(results, func_name, dim, max_iter, metric_name):
    plt.figure(figsize=(12, 6))
    colors = {
        "Standard PSO": "#1f77b4",
        "LEO-PSO (原版)": "#ff7f0e",
        "LEO+上下文向量": "#d62728",
        "LEO+局部邻居": "#9467bd",
        "LEO+上下文向量+局部邻居": "#e377c2"
    }
    for algo_name in results:
        valid_curves = [c for c in results[algo_name]["convergence"] if not all(np.isinf(val) for val in c)]
        if len(valid_curves) == 0:
            continue
        mean_curve = np.mean(valid_curves, axis=0)
        plt.plot(range(len(mean_curve)), mean_curve, label=f"{algo_name} ({len(valid_curves)} runs)",
                 linewidth=2.5, color=colors.get(algo_name, "#000000"))
    plt.xlabel("迭代次数", fontsize=12)
    plt.ylabel(f"{metric_name}（对数尺度）", fontsize=12)
    plt.title(f"收敛曲线对比 - {func_name}函数 (维度={dim})", fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.yscale("log")
    plt.tight_layout()
    plt.savefig(f"{func_name}_convergence.png", dpi=300, bbox_inches="tight")
    plt.close()

def plot_boxplot(results, func_name, metric_name):
    plt.figure(figsize=(10, 6))
    algo_order = [
        "Standard PSO",
        "LEO-PSO (原版)",
        "LEO+上下文向量",
        "LEO+局部邻居",
        "LEO+上下文向量+局部邻居"
    ]
    data = []
    labels = []
    colors = ["#1f77b4", "#ff7f0e", "#d62728", "#9467bd", "#e377c2"]
    for algo_name in algo_order:
        if algo_name in results:
            fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
            if len(fits) > 0:
                data.append(fits)
                labels.append(f"{algo_name}\n({len(fits)} runs)")
    if len(data) == 0:
        print("无有效数据绘制箱线图")
        plt.close()
        return
    box = plt.boxplot(data, labels=labels, patch_artist=True, showmeans=True)
    for patch, color in zip(box['boxes'], colors[:len(data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    plt.setp(box['medians'], color='black', linewidth=2)
    plt.setp(box['means'], marker='o', markerfacecolor='white', markeredgecolor='black', markersize=6)
    plt.ylabel(metric_name, fontsize=12)
    plt.title(f"算法性能对比 - {func_name}函数", fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y', linestyle='--')
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    plt.savefig(f"{func_name}_boxplot.png", dpi=300, bbox_inches="tight")
    plt.close()

def analyze_components(results, func_name):
    print(f"\n{'='*60}")
    print(f"组件影响分析 - {func_name}函数")
    print(f"{'='*60}")
    component_map = {
        "Standard PSO": [],
        "LEO-PSO (原版)": ["ANN", "正向经验"],
        "LEO+上下文向量": ["ANN", "正向经验", "上下文向量"],
        "LEO+局部邻居": ["ANN", "正向经验", "局部邻居"],
        "LEO+上下文向量+局部邻居": ["ANN", "正向经验", "上下文向量", "局部邻居"]
    }
    algo_performance = {}
    for algo_name in results:
        fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
        if len(fits) > 0:
            algo_performance[algo_name] = np.mean(fits)
    sorted_algo = sorted(algo_performance.items(), key=lambda x: x[1])
    print("\n算法性能排名（从优到劣）：")
    for i, (algo_name, perf) in enumerate(sorted_algo, 1):
        components = ", ".join(component_map.get(algo_name, []))
        print(f"{i:2d}. {algo_name:40s} | 平均指标值: {perf:.10f} | 组件: {components}")

# ===================== 主程序（论文实验配置） =====================
if __name__ == "__main__":
    np.random.seed(42)
    random.seed(42)
    
    print("LEO-PSO无反向经验变种对比实验（对齐论文多维度）")
    print("="*60)
    print("对比以下5种算法：")
    print("1. Standard PSO - 传统粒子群算法")
    print("2. LEO-PSO (原版) - 基础学习经验优化PSO")
    print("3. LEO+上下文向量 - 原版+上下文向量")
    print("4. LEO+局部邻居 - 原版+局部邻居（环形拓扑）")
    print("5. LEO+上下文向量+局部邻居 - 原版+上下文向量+局部邻居")
    print("="*60)
    
    # 一、单目标测试：IEEE CEC 2021 F01-F03 + 原文指定维度（10D/20D/100D）
    cec2021_functions = [
        (cec2021_f01, "CEC2021_F01"),
        (cec2021_f02, "CEC2021_F02"),
        (cec2021_f03, "CEC2021_F03")
    ]
    single_obj_dims = [10, 20, 100]  # 原文单目标核心维度
    
    # 二、多目标测试：DTLZ1-DTLZ3 + 原文目标数（5/10/15/20），维度=目标数+9（原文k=10）
    dtlz_functions = [
        (dtlz1, "DTLZ1")
    ]
    multi_obj_num_objs = [  20]  # 原文多目标目标数设置
    
    # # 运行单目标实验（循环所有维度）
    # print("\n" + "="*80)
    # print("开始单目标实验（IEEE CEC 2021，维度：10D/20D/100D）
    # print("="*80)
    # for func, func_name in cec2021_functions:
    #     for dim in single_obj_dims:
    
    # # 运行多目标实验
    # print("\n" + "="*80)
    # print("开始多目标实验（DTLZ1-DTLZ3，目标数：5/10/15/20）")
    # print("="*80)
    # for func, func_name in dtlz_functions:
    #     for num_obj in multi_obj_num_objs:
    #         dim = num_obj + 9  # 维度=目标数+9（原文k=10）
    #         print(f"\n--- 运行 {func_name}，{num_obj} 目标，{dim} 维度 ---")
    #         compare_all_variants(
    #             func=func,
    #             func_name=f"{func_name}_{num_obj}obj",
    #             dim=dim,
    #             max_iter=500,
    #             runs=5,
    #             pop_size=100,
    #             is_multi_obj=True,
    #             num_obj=num_obj
    #         )
    #         # 原文适应度评估次数设置：10D=2e5，20D/100D=1e6
    #         max_evals = 200000 if dim == 10 else 1000000
    #         max_iter = max_evals // 100  # 种群100，按评估次数反推迭代数（对齐原文）
            
    #         print(f"\n=== 函数：{func_name}，维度：{dim}D，最大评估次数：{max_evals} ===")
    #         results, stats = compare_all_variants(
    #             func=func,
    #             func_name=f"{func_name}_D{dim}",  # 文件名加维度后缀，避免冲突
    #             dim=dim,
    #             max_iter=max_iter,
    #             runs=30,  # 原文运行30次（统计显著性）
    #             pop_size=100,
    #             is_multi_obj=False
    #         )
    
    # 运行多目标实验（循环所有目标数，动态计算维度）
    print("\n" + "="*80)
    print("开始多目标实验（DTLZ，目标数：5/10/15/20，维度=目标数+9）")
    print("="*80)
    
    # 运行完整的多目标实验
    for func, func_name in dtlz_functions:
        for num_obj in multi_obj_num_objs:
            dim = num_obj + 9  # 原文多目标维度公式：dim = num_obj + k -1，k=10
            max_iter = 250  # 原文多目标迭代数设置
            
            print(f"\n=== 函数：{func_name}，目标数：{num_obj}，维度：{dim}D ===")
            results, stats = compare_all_variants(
                func=func,
                func_name=f"{func_name}_Obj{num_obj}_D{dim}",  # 文件名加目标数+维度后缀
                dim=dim,
                max_iter=max_iter,
                runs=30,  # 原文运行30次
                pop_size=100,
                is_multi_obj=True,
                num_obj=num_obj
            )
    
    print("\n所有多维度实验完成！文件已按「函数名_维度/目标数」命名，避免冲突。")