import numpy as np
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
import seaborn as sns
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ===================== 关键修复：字体配置（解决负号/Unicode警告） =====================
# 1. 关闭Matplotlib字体相关警告（可选，减少输出干扰）
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
# 2. 指定支持Unicode减号的字体列表（优先级从高到低）
matplotlib.rcParams['font.sans-serif'] = [
    'SimHei',         # 黑体（Windows默认）
    'Microsoft YaHei',# 微软雅黑（Windows）
    'DejaVu Sans',    # Matplotlib默认兼容字体（跨平台）
    'Arial Unicode MS',# MacOS
    'WenQuanYi Micro Hei', # Linux
    'Heiti TC'        # 繁体中文
]
# 3. 强制使用ASCII减号替代Unicode数学减号（核心解决\u2212警告）
matplotlib.rcParams['axes.unicode_minus'] = False
# 4. 可选：设置默认渲染器（避免跨平台字体兼容问题）
matplotlib.use('Agg')  # 无GUI渲染（仅保存图片，不显示，适合批量运行）

# ===================== 以下代码与之前完全一致，仅字体配置部分修改 =====================
# 工具类：ANN（所有变种共用）
class SimpleANN:
    def __init__(self, input_dim, hidden_dim, output_dim, lr=0.01):
        self.lr = lr
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.random.randn(hidden_dim) * 0.1
        self.W2 = np.random.randn(hidden_dim, output_dim) * 0.1
        self.b2 = np.random.randn(output_dim) * 0.1

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def sigmoid_deriv(self, x):
        return x * (1 - x)

    def forward(self, x):
        self.h = self.sigmoid(np.dot(x, self.W1) + self.b1)
        self.out = np.dot(self.h, self.W2) + self.b2
        return self.out

    def train(self, X, y):
        self.forward(X)
        loss = self.out - y
        dW2 = np.dot(self.h.T, loss) / X.shape[0]
        db2 = np.sum(loss, axis=0) / X.shape[0]
        d_h = np.dot(loss, self.W2.T) * self.sigmoid_deriv(self.h)
        dW1 = np.dot(X.T, d_h) / X.shape[0]
        db1 = np.sum(d_h, axis=0) / X.shape[0]
        self.W1 -= self.lr * dW1
        self.W2 -= self.lr * dW2
        self.b1 -= self.lr * db1
        self.b2 -= self.lr * db2

# 测试函数（带标准搜索范围）
def sphere_func(x):
    """Sphere函数 - 单峰，搜索范围[-100, 100]"""
    return np.sum(x ** 2)

def ackley_func(x):
    """Ackley函数 - 多峰，搜索范围[-32.768, 32.768]"""
    dim = len(x)
    term1 = -20 * np.exp(-0.2 * np.sqrt(np.sum(x**2) / dim))
    term2 = -np.exp(np.sum(np.cos(2 * np.pi * x)) / dim)
    return term1 + term2 + 20 + np.e

def step_func(x):
    """Step函数 - 非连续，搜索范围[-100, 100]"""
    return np.sum(np.floor(x))

def rastrigin_func(x):
    """Rastrigin函数 - 多峰，搜索范围[-5.12, 5.12]"""
    return 10 * len(x) + np.sum(x**2 - 10 * np.cos(2 * np.pi * x))

# 函数-范围映射（用于自动适配）
func_bounds = {
    sphere_func: (-100, 100),
    ackley_func: (-32.768, 32.768),
    step_func: (-100, 100),
    rastrigin_func: (-5.12, 5.12)
}

# 基础算法：传统PSO
class StandardPSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500, w=0.7, c1=1.5, c2=1.5, bounds=(-5.12, 5.12)):
        self.func = func
        self.dim = dim
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.bounds = bounds  # 动态搜索范围

        self.X = np.random.uniform(bounds[0], bounds[1], (pop_size, dim))
        self.V = np.random.uniform(-1, 1, (pop_size, dim))
        self.pBest = self.X.copy()
        self.pBest_fit = np.array([func(x) for x in self.X])
        self.gBest_idx = np.argmin(self.pBest_fit)
        self.gBest = self.pBest[self.gBest_idx].copy()
        self.gBest_fit = self.pBest_fit[self.gBest_idx]
        self.convergence_curve = []
        self.metadata = {"strategy": "Standard PSO"}

    def run(self):
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
            r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
            self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
            self.X = self.X + self.V
            self.X = np.clip(self.X, self.bounds[0], self.bounds[1])  # 按函数范围裁剪

            new_fit = np.array([self.func(x) for x in self.X])
            update_mask = new_fit < self.pBest_fit
            self.pBest[update_mask] = self.X[update_mask]
            self.pBest_fit[update_mask] = new_fit[update_mask]
            current_gBest_idx = np.argmin(self.pBest_fit)
            current_gBest_fit = self.pBest_fit[current_gBest_idx]
            if current_gBest_fit < self.gBest_fit:
                self.gBest = self.pBest[current_gBest_idx].copy()
                self.gBest_fit = current_gBest_fit

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# 原版LEO-PSO
class LEO_PSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12)):
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
        self.bounds = bounds  # 动态搜索范围

        self.ann = SimpleANN(input_dim=dim, hidden_dim=3*dim, output_dim=dim, lr=ann_lr)
        self.arch = []

        self.X = np.random.uniform(bounds[0], bounds[1], (pop_size, dim))
        self.V = np.random.uniform(-1, 1, (pop_size, dim))
        self.pBest = self.X.copy()
        self.pBest_fit = np.array([func(x) for x in self.X])
        self.gBest_idx = np.argmin(self.pBest_fit)
        self.gBest = self.pBest[self.gBest_idx].copy()
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
        cross_mask = np.random.uniform(0, 1, self.dim) <= self.beta
        final_X = np.where(cross_mask, newX, pBest_i)
        return final_X

    def run(self):
        g = 0
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(self.pBest[i])
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, self.bounds[0], self.bounds[1])  # 按函数范围裁剪

            new_fit = np.array([self.func(x) for x in new_X])
            pBest_old = self.pBest.copy()
            pBest_fit_old = self.pBest_fit.copy()
            update_mask = new_fit < self.pBest_fit
            self.pBest[update_mask] = new_X[update_mask]
            self.pBest_fit[update_mask] = new_fit[update_mask]
            current_gBest_idx = np.argmin(self.pBest_fit)
            current_gBest_fit = self.pBest_fit[current_gBest_idx]
            if current_gBest_fit < self.gBest_fit:
                self.gBest = self.pBest[current_gBest_idx].copy()
                self.gBest_fit = current_gBest_fit
            self.X = new_X

            # 仅收集正向经验
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    self.arch.append((pBest_old[i], self.pBest[i]))

            # 存档管理
            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            # 训练ANN
            if len(self.arch) > 0:
                X_train = np.array([sep[0] for sep in self.arch])
                y_train = np.array([sep[1] for sep in self.arch])
                self.ann.train(X_train, y_train)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# LEO+上下文向量
class LEO_CV_PSO(LEO_PSO):
    """LEO-PSO + 上下文向量（无反向经验）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12)):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds)
        self.context_dim = 4 * dim + 1  # 位置+速度+pBest+gBest+进度
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
        self.metadata = {"strategy": "LEO+上下文向量", "components": ["ANN", "正向经验", "上下文向量"]}
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        pos = self.X[particle_idx]
        vel = self.V[particle_idx]
        pbest = self.pBest[particle_idx]
        gbest = self.gBest
        progress = iteration / total_iter
        context = np.concatenate([pos, vel, pbest, gbest, np.array([progress])])
        return context
    
    def learning_aided_mutation(self, pBest_i, context):
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        r1, r2 = random.sample(range(self.pop_size), 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX
    
    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            contexts = [self.build_context_vector(i, iteration, self.max_iter) for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(self.pBest[i], contexts[i])
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, self.bounds[0], self.bounds[1])

            new_fit = np.array([self.func(x) for x in new_X])
            pBest_old = self.pBest.copy()
            pBest_fit_old = self.pBest_fit.copy()
            update_mask = new_fit < self.pBest_fit
            self.pBest[update_mask] = new_X[update_mask]
            self.pBest_fit[update_mask] = new_fit[update_mask]
            current_gBest_idx = np.argmin(self.pBest_fit)
            current_gBest_fit = self.pBest_fit[current_gBest_idx]
            if current_gBest_fit < self.gBest_fit:
                self.gBest = self.pBest[current_gBest_idx].copy()
                self.gBest_fit = current_gBest_fit
            self.X = new_X

            # 正向经验收集（上下文→成功方向）
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))

            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# LEO+局部邻居
class LEO_LN_PSO(LEO_PSO):
    """LEO-PSO + 局部邻居（无反向经验）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12)):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds)
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
    
    def run(self):
        g = 0
        for _ in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(self.pBest[i], i)
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, self.bounds[0], self.bounds[1])

            new_fit = np.array([self.func(x) for x in new_X])
            pBest_old = self.pBest.copy()
            pBest_fit_old = self.pBest_fit.copy()
            update_mask = new_fit < self.pBest_fit
            self.pBest[update_mask] = new_X[update_mask]
            self.pBest_fit[update_mask] = new_fit[update_mask]
            current_gBest_idx = np.argmin(self.pBest_fit)
            current_gBest_fit = self.pBest_fit[current_gBest_idx]
            if current_gBest_fit < self.gBest_fit:
                self.gBest = self.pBest[current_gBest_idx].copy()
                self.gBest_fit = current_gBest_fit
            self.X = new_X

            # 正向经验收集
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    self.arch.append((pBest_old[i], self.pBest[i]))

            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            if len(self.arch) > 0:
                X_train = np.array([sep[0] for sep in self.arch])
                y_train = np.array([sep[1] for sep in self.arch])
                self.ann.train(X_train, y_train)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# LEO+上下文向量+局部邻居
class LEO_CV_LN_PSO(LEO_PSO):
    """LEO-PSO + 上下文向量+局部邻居（无反向经验）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, bounds=(-5.12, 5.12)):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, bounds)
        self.context_dim = 5 * dim + 2  # 位置+速度+pBest+gBest+邻居均值+进度+方差
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
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
        neighbor_mean = np.mean(neighbor_pbests, axis=0)
        neighbor_fits = self.pBest_fit[neighbors]
        fit_variance = np.var(neighbor_fits)
        return neighbor_mean, fit_variance
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        pos = self.X[particle_idx]
        vel = self.V[particle_idx]
        pbest = self.pBest[particle_idx]
        gbest = self.gBest
        neighbor_mean, fit_variance = self.get_neighborhood_info(particle_idx)
        progress = iteration / total_iter
        context = np.concatenate([pos, vel, pbest, gbest, neighbor_mean, np.array([progress, fit_variance])])
        return context
    
    def learning_aided_mutation(self, context, particle_idx):
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        neighbors = self.neighborhood[particle_idx]
        r1, r2 = random.sample(neighbors, 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        return newX
    
    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            contexts = [self.build_context_vector(i, iteration, self.max_iter) for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(contexts[i], i)
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, self.bounds[0], self.bounds[1])

            new_fit = np.array([self.func(x) for x in new_X])
            pBest_old = self.pBest.copy()
            pBest_fit_old = self.pBest_fit.copy()
            update_mask = new_fit < self.pBest_fit
            self.pBest[update_mask] = new_X[update_mask]
            self.pBest_fit[update_mask] = new_fit[update_mask]
            current_gBest_idx = np.argmin(self.pBest_fit)
            current_gBest_fit = self.pBest_fit[current_gBest_idx]
            if current_gBest_fit < self.gBest_fit:
                self.gBest = self.pBest[current_gBest_idx].copy()
                self.gBest_fit = current_gBest_fit
            self.X = new_X

            # 正向经验收集
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))

            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# 对比实验框架
def compare_all_variants(func, func_name, dim=30, max_iter=500, runs=5, pop_size=100):
    """对比无反向经验的5个核心变种"""
    # 自动获取函数搜索范围
    bounds = func_bounds.get(func, (-5.12, 5.12))
    
    algorithms = [
        ("Standard PSO", StandardPSO),
        ("LEO-PSO (原版)", LEO_PSO),
        ("LEO+上下文向量", LEO_CV_PSO),
        ("LEO+局部邻居", LEO_LN_PSO),
        ("LEO+上下文向量+局部邻居", LEO_CV_LN_PSO)
    ]
    
    results = {}
    for name, _ in algorithms:
        results[name] = {"best_fit": [], "convergence": []}
    
    print(f"\n{'='*60}")
    print(f"开始对比实验：{func_name}函数，维度={dim}，迭代={max_iter}，运行次数={runs}，范围={bounds}")
    print(f"{'='*60}")
    
    for run in range(runs):
        print(f"\n--- 第 {run+1}/{runs} 轮 ---")
        
        for algo_name, AlgoClass in algorithms:
            try:
                # 关键修复：StandardPSO不传入arch_size和ann_lr
                if algo_name == "Standard PSO":
                    algo = AlgoClass(
                        func=func,
                        dim=dim,
                        pop_size=pop_size,
                        max_iter=max_iter,
                        bounds=bounds
                    )
                else:
                    algo = AlgoClass(
                        func=func,
                        dim=dim,
                        pop_size=pop_size,
                        max_iter=max_iter,
                        arch_size=100,
                        ann_lr=0.01,
                        bounds=bounds
                    )
                
                _, best_fit, conv_curve = algo.run()
                results[algo_name]["best_fit"].append(best_fit)
                results[algo_name]["convergence"].append(conv_curve)
                print(f"{algo_name:40s} | 最优值: {best_fit:.8f}")
            except Exception as e:
                print(f"{algo_name:40s} | 错误: {e}")
                results[algo_name]["best_fit"].append(float('inf'))
                results[algo_name]["convergence"].append([float('inf')] * max_iter)
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"{func_name}函数对比结果（{runs}轮均值±标准差）")
    print(f"{'='*60}")
    
    stats = {}
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
    
    # 性能提升分析（相对于原版LEO-PSO）
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
    
    # 可视化（仅保存不显示）
    plot_convergence_curves(results, func_name, dim, max_iter)
    plot_boxplot(results, func_name)
    analyze_components(results, func_name)
    
    return results, stats

def plot_convergence_curves(results, func_name, dim, max_iter):
    """绘制收敛曲线 - 仅保存不显示"""
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
    plt.ylabel("最佳适应度（对数尺度）", fontsize=12)
    plt.title(f"收敛曲线对比 - {func_name}函数 (维度={dim})", fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.yscale("log")
    plt.tight_layout()
    # 保存图片
    plt.savefig(f"{func_name}_convergence.png", dpi=300, bbox_inches="tight")
    # 关闭画布释放内存
    plt.close()

def plot_boxplot(results, func_name):
    """绘制箱线图 - 仅保存不显示"""
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
    plt.ylabel("最佳适应度", fontsize=12)
    plt.title(f"算法性能对比 - {func_name}函数", fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y', linestyle='--')
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    # 保存图片
    plt.savefig(f"{func_name}_boxplot.png", dpi=300, bbox_inches="tight")
    # 关闭画布释放内存
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
        print(f"{i:2d}. {algo_name:40s} | 平均适应度: {perf:.10f} | 组件: {components}")

# 主程序（测试3个代表性函数）
if __name__ == "__main__":
    np.random.seed(42)
    random.seed(42)
    
    print("LEO-PSO无反向经验变种对比实验")
    print("="*60)
    print("对比以下5种算法：")
    print("1. Standard PSO - 传统粒子群算法")
    print("2. LEO-PSO (原版) - 基础学习经验优化PSO")
    print("3. LEO+上下文向量 - 原版+上下文向量")
    print("4. LEO+局部邻居 - 原版+局部邻居（环形拓扑）")
    print("5. LEO+上下文向量+局部邻居 - 原版+上下文向量+局部邻居")
    print("="*60)
    
    # 定义要测试的函数（覆盖单峰、多峰、非连续）
    test_functions = [
        (sphere_func, "Sphere"),
        (ackley_func, "Ackley"),
        (step_func, "Step")
    ]
    
    # 批量运行测试（连续执行不中断）
    for func, func_name in test_functions:
        results, stats = compare_all_variants(
            func=func,
            func_name=func_name,
            dim=30,
            max_iter=1000,
            runs=10,  # 运行10轮平衡统计性和速度
            pop_size=100
        )
    
    print("\n所有函数测试完成！所有图片已保存为文件。")