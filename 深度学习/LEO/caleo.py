import numpy as np
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
import seaborn as sns
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ===================== 1. 工具类：ANN（所有变种共用） =====================
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

# ===================== 2. 测试函数 =====================
def rastrigin_func(x):
    """Rastrigin函数 - 经典多模态测试函数"""
    return 10 * len(x) + np.sum(x**2 - 10 * np.cos(2 * np.pi * x))
def sphere_func(x):
    """Sphere函数 - 经典单峰测试函数，验证收敛速度"""
    return np.sum(x ** 2)
def ackley_func(x):
    """Ackley函数 - 多峰函数，验证全局探索与局部利用平衡"""
    dim = len(x)
    term1 = -20 * np.exp(-0.2 * np.sqrt(np.sum(x**2) / dim))
    term2 = -np.exp(np.sum(np.cos(2 * np.pi * x)) / dim)
    return term1 + term2 + 20 + np.e
def step_func(x):
    """Step函数 - 非连续函数，验证粗搜索能力和非连续空间适应性"""
    return np.sum(np.floor(x))
# ===================== 3. 基础算法：传统PSO =====================
class StandardPSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500, w=0.7, c1=1.5, c2=1.5):
        self.func = func
        self.dim = dim
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2

        self.X = np.random.uniform(-5.12, 5.12, (pop_size, dim))
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
            self.X = np.clip(self.X, -5.12, 5.12)

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

# ===================== 4. 原版LEO-PSO =====================
class LEO_PSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01):
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

        self.ann = SimpleANN(input_dim=dim, hidden_dim=3*dim, output_dim=dim, lr=ann_lr)
        self.arch = []  # 存储SEP

        self.X = np.random.uniform(-5.12, 5.12, (pop_size, dim))
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
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 原版SEP收集：仅保留正向经验
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

# ===================== 5. LEO+选择性反向经验 =====================
class LEO_SRE_PSO(LEO_PSO):
    """LEO-PSO + 选择性反向经验"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01, 
                 reverse_prob=0.3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr)
        self.reverse_prob = reverse_prob
        self.metadata = {"strategy": "LEO+选择性反向经验", "components": ["ANN", "正向经验", "选择性反向经验"]}
    
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
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 选择性反向经验收集
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 正向经验：x_old→x_new更优
                    self.arch.append((pBest_old[i], self.pBest[i]))
                elif self.pBest_fit[i] > pBest_fit_old[i] and random.random() < self.reverse_prob:
                    # 反向经验：x_new→x_old更优（有选择地）
                    self.arch.append((self.pBest[i], pBest_old[i]))

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

# ===================== 6. LEO+上下文向量 =====================
class LEO_CV_PSO(LEO_PSO):
    """LEO-PSO + 上下文向量"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr)
        # 重新定义ANN，输入维度为上下文向量维度
        self.context_dim = 4 * dim + 1  # 位置(dim) + 速度(dim) + pBest(dim) + gBest(dim) + 迭代进度(1)
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
        self.metadata = {"strategy": "LEO+上下文向量", "components": ["ANN", "正向经验", "上下文向量"]}
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        """构建上下文向量：位置 + 速度 + pBest + gBest + 迭代进度"""
        # 当前位置
        pos = self.X[particle_idx]
        # 当前速度
        vel = self.V[particle_idx]
        # 个体历史最佳
        pbest = self.pBest[particle_idx]
        # 全局最佳
        gbest = self.gBest
        # 迭代进度
        progress = iteration / total_iter
        
        # 将所有信息拼接成上下文向量
        context = np.concatenate([
            pos,      # dim
            vel,      # dim
            pbest,    # dim
            gbest,    # dim
            np.array([progress])  # 1
        ])
        
        return context
    
    def learning_aided_mutation(self, pBest_i, context):
        """基于上下文的变异操作"""
        # 使用ANN基于上下文预测移动
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        
        # 从整个种群中随机选择两个
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
            
            # 为所有粒子构建上下文
            contexts = [self.build_context_vector(i, iteration, self.max_iter) 
                       for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(self.pBest[i], contexts[i])
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                # 标准PSO更新
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 经验收集：上下文 → 移动方向
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 记录：上下文 → 成功移动方向
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))

            # 存档管理
            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            # 训练ANN
            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 7. LEO+局部邻居 =====================
class LEO_LN_PSO(LEO_PSO):
    """LEO-PSO + 局部邻居（环形拓扑）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr)
        
        # 邻居定义：使用环形拓扑，每个粒子有k个邻居
        self.k_neighbors = 5
        self.neighborhood = self.create_ring_topology()
        
        self.metadata = {"strategy": "LEO+局部邻居", "components": ["ANN", "正向经验", "局部邻居"]}
    
    def create_ring_topology(self):
        """创建环形拓扑结构"""
        topology = {}
        for i in range(self.pop_size):
            neighbors = []
            for j in range(1, self.k_neighbors // 2 + 1):
                neighbors.append((i - j) % self.pop_size)
                neighbors.append((i + j) % self.pop_size)
            # 确保邻居数量为k_neighbors（当k_neighbors为奇数时）
            if self.k_neighbors % 2 == 1:
                neighbors.append((i + self.k_neighbors) % self.pop_size)
            topology[i] = neighbors[:self.k_neighbors]
        return topology
    
    def learning_aided_mutation(self, pBest_i, particle_idx):
        """基于局部邻居的变异操作"""
        # 从ANN获取预测
        L_pBest = self.ann.forward(pBest_i.reshape(1, -1)).flatten()
        
        # 从邻居中随机选择两个进行差分变异
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
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 原版SEP收集：仅保留正向经验
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

# ===================== 8. LEO+全组件（原完整CA-LEO） =====================
class LEO_Full_PSO(LEO_PSO):
    """LEO-PSO + 全组件（正向经验+选择性反向经验+上下文向量+局部邻居）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01,
                 reverse_prob=0.3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr)
        
        # 上下文维度
        self.context_dim = 5 * dim + 2  # 位置(dim) + 速度(dim) + pBest(dim) + gBest(dim) + 邻居均值(dim) + 进度(1) + 方差(1)
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
        
        # 邻居定义
        self.k_neighbors = 5
        self.neighborhood = self.create_ring_topology()
        
        # 选择性反向经验概率
        self.reverse_prob = reverse_prob
        
        self.arch = deque(maxlen=arch_size)  # 使用deque自动管理大小
        self.metadata = {"strategy": "LEO+全组件", "components": ["ANN", "正向经验", "选择性反向经验", "上下文向量", "局部邻居"]}
    
    def create_ring_topology(self):
        """创建环形拓扑结构"""
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
        """获取粒子邻居的信息"""
        neighbors = self.neighborhood[particle_idx]
        # 计算邻居的pBest均值
        neighbor_pbests = self.pBest[neighbors]
        neighbor_mean = np.mean(neighbor_pbests, axis=0)
        
        # 计算邻居的适应度方差
        neighbor_fits = self.pBest_fit[neighbors]
        fit_variance = np.var(neighbor_fits)
        
        return neighbor_mean, fit_variance
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        """构建上下文向量"""
        # 1. 当前位置
        pos = self.X[particle_idx]
        # 2. 当前速度
        vel = self.V[particle_idx]
        # 3. 个体历史最佳
        pbest = self.pBest[particle_idx]
        # 4. 全局最佳
        gbest = self.gBest
        # 5. 邻居信息
        neighbor_mean, fit_variance = self.get_neighborhood_info(particle_idx)
        # 6. 迭代进度
        progress = iteration / total_iter
        
        # 将所有信息拼接成上下文向量
        context = np.concatenate([
            pos,                    # dim
            vel,                    # dim  
            pbest,                  # dim
            gbest,                  # dim
            neighbor_mean,          # dim
            np.array([progress, fit_variance])  # 2
        ])
        
        return context
    
    def learning_aided_mutation(self, context, particle_idx):
        """基于上下文的变异操作"""
        # 使用ANN基于上下文预测移动
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        
        # 从邻居中随机选择两个进行差分变异
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
            
            # 为所有粒子构建上下文
            contexts = [self.build_context_vector(i, iteration, self.max_iter) 
                       for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(contexts[i], i)
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                # 标准PSO更新
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 上下文感知的经验收集
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 记录：上下文 → 成功移动方向
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))
                elif self.pBest_fit[i] > pBest_fit_old[i] and random.random() < self.reverse_prob:
                    # 选择性反向经验
                    failure_direction = pBest_old[i] - self.pBest[i]
                    self.arch.append((contexts[i], failure_direction))

            # 训练ANN
            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 9. LEO+上下文向量+局部邻居（原CA-LEO无反向经验） =====================
class LEO_CV_LN_PSO(LEO_Full_PSO):
    """LEO-PSO + 上下文向量+局部邻居（无选择性反向经验）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr, reverse_prob=0.0)
        self.metadata = {"strategy": "LEO+上下文向量+局部邻居", "components": ["ANN", "正向经验", "上下文向量", "局部邻居"]}
    
    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            
            # 为所有粒子构建上下文
            contexts = [self.build_context_vector(i, iteration, self.max_iter) 
                       for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(contexts[i], i)
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                # 标准PSO更新
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 只收集正向经验（无反向经验）
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 记录：上下文 → 成功移动方向
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))

            # 训练ANN
            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 10. LEO+上下文向量+反向经验（原CA-LEO无局部邻居） =====================
class LEO_CV_SRE_PSO(LEO_PSO):
    """LEO-PSO + 上下文向量+选择性反向经验（无局部邻居）"""
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=100, alpha=0.5, beta=0.9, ann_lr=0.01,
                 reverse_prob=0.3):
        super().__init__(func, dim, pop_size, max_iter, w, c1, c2, lp, arch_size, alpha, beta, ann_lr)
        
        # 上下文维度（无邻居信息）
        self.context_dim = 4 * dim + 1  # 位置(dim) + 速度(dim) + pBest(dim) + gBest(dim) + 进度(1)
        self.ann = SimpleANN(input_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
        
        # 选择性反向经验概率
        self.reverse_prob = reverse_prob
        
        self.arch = deque(maxlen=arch_size)  # 使用deque自动管理大小
        self.metadata = {"strategy": "LEO+上下文向量+反向经验", "components": ["ANN", "正向经验", "选择性反向经验", "上下文向量"]}
    
    def build_context_vector(self, particle_idx, iteration, total_iter):
        """构建上下文向量（无邻居信息）"""
        # 1. 当前位置
        pos = self.X[particle_idx]
        # 2. 当前速度
        vel = self.V[particle_idx]
        # 3. 个体历史最佳
        pbest = self.pBest[particle_idx]
        # 4. 全局最佳
        gbest = self.gBest
        # 5. 迭代进度
        progress = iteration / total_iter
        
        # 将所有信息拼接成上下文向量
        context = np.concatenate([
            pos,      # dim
            vel,      # dim
            pbest,    # dim
            gbest,    # dim
            np.array([progress])  # 1
        ])
        
        return context
    
    def learning_aided_mutation(self, context):
        """基于上下文的变异操作（使用全局邻居）"""
        # 使用ANN基于上下文预测移动
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        
        # 从整个种群中随机选择两个
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
            
            # 为所有粒子构建上下文
            contexts = [self.build_context_vector(i, iteration, self.max_iter) 
                       for i in range(self.pop_size)]
            
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                for i in range(self.pop_size):
                    lm_X = self.learning_aided_mutation(contexts[i])
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                # 标准PSO更新
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, -5.12, 5.12)

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

            # 上下文感知的经验收集
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 记录：上下文 → 成功移动方向
                    success_direction = self.pBest[i] - pBest_old[i]
                    self.arch.append((contexts[i], success_direction))
                elif self.pBest_fit[i] > pBest_fit_old[i] and random.random() < self.reverse_prob:
                    # 选择性反向经验
                    failure_direction = pBest_old[i] - self.pBest[i]
                    self.arch.append((contexts[i], failure_direction))

            # 训练ANN
            if len(self.arch) >= 10:
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                self.ann.train(contexts_batch, directions_batch)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 11. 对比实验框架 =====================
def compare_all_variants(func, func_name, dim=30, max_iter=500, runs=5, pop_size=100):
    """
    比较所有LEO-PSO变种
    
    参数:
    - func: 测试函数
    - func_name: 函数名称
    - dim: 问题维度
    - max_iter: 最大迭代次数
    - runs: 运行次数
    - pop_size: 种群大小
    """

    algorithms = [
        ("Standard PSO", StandardPSO),
        ("LEO-PSO (原版)", LEO_PSO),
        ("LEO+选择性反向经验", LEO_SRE_PSO),
        ("LEO+上下文向量", LEO_CV_PSO),
        ("LEO+局部邻居", LEO_LN_PSO),
        ("LEO+全组件", LEO_Full_PSO),
        ("LEO+上下文向量+局部邻居", LEO_CV_LN_PSO),
        ("LEO+上下文向量+反向经验", LEO_CV_SRE_PSO)
    ]
    
    results = {}
    for name, _ in algorithms:
        results[name] = {"best_fit": [], "convergence": []}
    
    print(f"\n{'='*60}")
    print(f"开始对比实验：{func_name}函数，维度={dim}，迭代={max_iter}，运行次数={runs}")
    print(f"{'='*60}")
    
    for run in range(runs):
        print(f"\n--- 第 {run+1}/{runs} 轮 ---")
        
        for algo_name, AlgoClass in algorithms:
            try:
                # 实例化算法
                if algo_name == "Standard PSO":
                    algo = AlgoClass(func=func, dim=dim, pop_size=pop_size, max_iter=max_iter)
                else:
                    algo = AlgoClass(
                        func=func, 
                        dim=dim, 
                        pop_size=pop_size, 
                        max_iter=max_iter,
                        arch_size=100,
                        ann_lr=0.01
                    )
                
                # 运行算法
                _, best_fit, conv_curve = algo.run()
                
                # 存储结果
                results[algo_name]["best_fit"].append(best_fit)
                results[algo_name]["convergence"].append(conv_curve)
                
                # 打印本轮结果
                print(f"{algo_name:40s} | 最优值: {best_fit:.8f}")
            except Exception as e:
                print(f"{algo_name:40s} | 错误: {e}")
                # 存储默认值
                results[algo_name]["best_fit"].append(float('inf'))
                results[algo_name]["convergence"].append([float('inf')] * max_iter)
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"{func_name}函数对比结果（{runs}轮均值±标准差）")
    print(f"{'='*60}")
    
    stats = {}
    for algo_name in algorithms:
        name = algo_name[0]
        # 过滤掉无穷大的值
        fits = [f for f in results[name]["best_fit"] if f != float('inf')]
        if len(fits) == 0:
            print(f"{name:40s} | 所有运行都失败")
            continue
            
        mean_fit = np.mean(fits)
        std_fit = np.std(fits)
        stats[name] = {"mean": mean_fit, "std": std_fit, "count": len(fits)}
        
        print(f"{name:40s} | 均值: {mean_fit:.10f} ± {std_fit:.10f} (成功运行: {len(fits)}/{runs})")
    
    # 计算性能提升百分比（相对于原版LEO-PSO）
    if "LEO-PSO (原版)" in stats and stats["LEO-PSO (原版)"]["mean"] != 0:
        print(f"\n性能提升（相对于LEO-PSO原版）：")
        baseline = stats["LEO-PSO (原版)"]["mean"]
        for algo_name in stats:
            if algo_name != "LEO-PSO (原版)" and algo_name != "Standard PSO":
                improvement = (baseline - stats[algo_name]["mean"]) / baseline * 100
                print(f"{algo_name:40s} | 提升: {improvement:.2f}%")
    
    # 收敛曲线可视化
    plot_convergence_curves(results, func_name, dim, max_iter)
    
    # 性能箱线图
    plot_boxplot(results, func_name)
    
    # 组件分析
    analyze_components(results, func_name)
    
    return results, stats

def plot_convergence_curves(results, func_name, dim, max_iter):
    """绘制收敛曲线对比图"""
    plt.figure(figsize=(16, 10))
    
    # 颜色方案（保持原配色，仅更新算法名称映射）
    colors = {
        "Standard PSO": "#1f77b4",
        "LEO-PSO (原版)": "#ff7f0e",
        "LEO+选择性反向经验": "#2ca02c",
        "LEO+上下文向量": "#d62728",
        "LEO+局部邻居": "#9467bd",
        "LEO+全组件": "#8c564b",
        "LEO+上下文向量+局部邻居": "#e377c2",
        "LEO+上下文向量+反向经验": "#7f7f7f"
    }
    
    # 绘制平均收敛曲线
    for algo_name in results:
        # 过滤掉失败的运行
        valid_curves = []
        for curve in results[algo_name]["convergence"]:
            if not all(np.isinf(val) for val in curve):
                valid_curves.append(curve)
        
        if len(valid_curves) == 0:
            continue
            
        # 计算平均收敛曲线
        conv_curves = np.array(valid_curves)
        mean_curve = np.mean(conv_curves, axis=0)
        
        # 绘制曲线
        iterations = range(len(mean_curve))
        plt.plot(iterations, mean_curve, label=f"{algo_name} ({len(valid_curves)} runs)", 
                linewidth=2.5, color=colors.get(algo_name, "#000000"))
    
    plt.xlabel("迭代次数", fontsize=14)
    plt.ylabel("最佳适应度（对数尺度）", fontsize=14)
    plt.title(f"收敛曲线对比 - {func_name}函数 (维度={dim})", fontsize=16, fontweight='bold')
    plt.legend(fontsize=9, loc='upper right', bbox_to_anchor=(1.3, 1.0))
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.yscale("log")
    plt.xlim(0, max_iter)
    
    # 添加次要网格
    plt.grid(True, which='minor', alpha=0.1, linestyle=':')
    
    plt.tight_layout()
    plt.savefig(f"{func_name}_all_variants_convergence.png", dpi=300, bbox_inches="tight")
    plt.show()

def plot_boxplot(results, func_name):
    """绘制性能箱线图"""
    plt.figure(figsize=(14, 8))
    
    # 准备数据
    data = []
    labels = []
    
    # 定义算法顺序
    algo_order = [
        "Standard PSO",
        "LEO-PSO (原版)",
        "LEO+选择性反向经验",
        "LEO+上下文向量",
        "LEO+局部邻居",
        "LEO+全组件",
        "LEO+上下文向量+局部邻居",
        "LEO+上下文向量+反向经验"
    ]
    
    for algo_name in algo_order:
        if algo_name in results:
            # 过滤掉无穷大的值
            fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
            if len(fits) > 0:
                data.append(fits)
                labels.append(f"{algo_name}\n({len(fits)} runs)")
    
    if len(data) == 0:
        print("没有有效数据可以绘制箱线图")
        return
    
    # 创建箱线图
    box = plt.boxplot(data, labels=labels, patch_artist=True, showmeans=True)
    
    # 设置颜色（保持原配色）
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 设置中位数线和均值点
    plt.setp(box['medians'], color='black', linewidth=2)
    plt.setp(box['means'], marker='o', markerfacecolor='white', 
            markeredgecolor='black', markersize=8)
    
    plt.ylabel("最佳适应度", fontsize=14)
    plt.title(f"算法性能对比 - {func_name}函数", fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # 旋转x轴标签
    plt.xticks(rotation=30, ha='right')
    
    plt.tight_layout()
    plt.savefig(f"{func_name}_all_variants_boxplot.png", dpi=300, bbox_inches="tight")
    plt.show()

def analyze_components(results, func_name):
    """分析各组件对性能的影响"""
    print(f"\n{'='*60}")
    print(f"组件影响分析 - {func_name}函数")
    print(f"{'='*60}")
    
    # 组件映射（更新为LEO+组件格式）
    component_map = {
        "Standard PSO": [],
        "LEO-PSO (原版)": ["ANN", "正向经验"],
        "LEO+选择性反向经验": ["ANN", "正向经验", "选择性反向经验"],
        "LEO+上下文向量": ["ANN", "正向经验", "上下文向量"],
        "LEO+局部邻居": ["ANN", "正向经验", "局部邻居"],
        "LEO+全组件": ["ANN", "正向经验", "选择性反向经验", "上下文向量", "局部邻居"],
        "LEO+上下文向量+局部邻居": ["ANN", "正向经验", "上下文向量", "局部邻居"],
        "LEO+上下文向量+反向经验": ["ANN", "正向经验", "选择性反向经验", "上下文向量"]
    }
    
    # 计算每个算法的平均适应度
    algo_performance = {}
    for algo_name in results:
        # 过滤掉无穷大的值
        fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
        if len(fits) > 0:
            algo_performance[algo_name] = np.mean(fits)
    
    # 按性能排序
    sorted_algo = sorted(algo_performance.items(), key=lambda x: x[1])
    
    print("\n算法性能排名（从优到劣）：")
    for i, (algo_name, perf) in enumerate(sorted_algo, 1):
        components = ", ".join(component_map.get(algo_name, []))
        print(f"{i:2d}. {algo_name:40s} | 平均适应度: {perf:.10f} | 组件: {components}")
    
    # 分析组件对性能的贡献
    print(f"\n{'='*60}")
    print("组件贡献分析")
    print(f"{'='*60}")
    
    # 比较基础LEO-PSO与各变种
    if "LEO-PSO (原版)" in algo_performance:
        baseline = algo_performance["LEO-PSO (原版)"]
        print(f"\n相对于LEO-PSO原版的性能提升：")
        
        comparisons = [
            ("LEO+选择性反向经验", "增加了选择性反向经验"),
            ("LEO+上下文向量", "增加了上下文向量"),
            ("LEO+局部邻居", "增加了局部邻居"),
            ("LEO+全组件", "增加了所有组件（反向经验+上下文向量+局部邻居）"),
            ("LEO+上下文向量+局部邻居", "增加了上下文向量和局部邻居"),
            ("LEO+上下文向量+反向经验", "增加了上下文向量和选择性反向经验")
        ]
        
        for algo_name, description in comparisons:
            if algo_name in algo_performance:
                improvement = (baseline - algo_performance[algo_name]) / baseline * 100
                print(f"{algo_name:40s} | {description:50s} | 提升: {improvement:.2f}%")

# ===================== 12. 主程序 =====================
if __name__ == "__main__":
    # 设置随机种子以保证可重复性
    np.random.seed(42)
    random.seed(42)
    
    print("LEO-PSO变种对比实验")
    print("="*60)
    print("对比以下8种算法：")
    print("1. Standard PSO - 传统粒子群算法")
    print("2. LEO-PSO (原版) - 基础学习经验优化PSO")
    print("3. LEO+选择性反向经验 - 原版+选择性反向经验")
    print("4. LEO+上下文向量 - 原版+上下文向量")
    print("5. LEO+局部邻居 - 原版+局部邻居（环形拓扑）")
    print("6. LEO+全组件 - 原版+反向经验+上下文向量+局部邻居")
    print("7. LEO+上下文向量+局部邻居 - 原版+上下文向量+局部邻居（无反向经验）")
    print("8. LEO+上下文向量+反向经验 - 原版+上下文向量+反向经验（无局部邻居）")
    print("="*60)
    
    # 运行对比实验
    results, stats = compare_all_variants(
        func=rastrigin_func,
        func_name="rastrigin_func",
        dim=30,           # 测试较低维度以加快实验
        max_iter=1000,     # 减少迭代次数
        runs=100,           # 减少运行次数
        pop_size=100       # 减少种群大小
    )
    
    print("\n实验完成！结果已保存为图片文件。")