import numpy as np
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
import seaborn as sns
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ===================== 1. 工具类：ANN（三种学习增强的PSO共用） =====================
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

# ===================== 2. 上下文感知的ANN（用于CA-LEO-PSO） =====================
class ContextAwareANN:
    def __init__(self, context_dim, hidden_dim, output_dim, lr=0.01):
        self.lr = lr
        # 上下文维度包括：位置、速度、个体最优、全局最优、邻居信息等
        self.W1 = np.random.randn(context_dim, hidden_dim) * 0.1
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

# ===================== 3. 基础算法：传统PSO =====================
class StandardPSO:
    def __init__(self, func, dim=30, pop_size=30, max_iter=500, w=0.7, c1=1.5, c2=1.5):
        self.func = func
        self.dim = dim
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2

        self.X = np.random.uniform(-5.12, 5.12, (pop_size, dim))  # Rastrigin默认范围[-5.12,5.12]
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
            self.X = np.clip(self.X, -5.12, 5.12)  # 边界约束

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
    def __init__(self, func, dim=30, pop_size=30, max_iter=500,
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
        self.metadata = {"strategy": "LEO-PSO"}

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

            # 原版SEP收集：仅保留正向经验（x_old→x_new更优）
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

# ===================== 5. 上下文感知CA-LEO-PSO =====================
class ContextAware_LEO_PSO:
    def __init__(self, func, dim=30, pop_size=30, max_iter=500,
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
        
        # 上下文维度：位置(dim) + 速度(dim) + pBest(dim) + gBest(dim) + 邻居均值(dim) + 迭代进度(1) + 适应度方差(1) = 5*dim+2
        self.context_dim = 5 * dim + 2  # 修正：应该是5*dim+2
        self.ann = ContextAwareANN(context_dim=self.context_dim, hidden_dim=6*dim, output_dim=dim, lr=ann_lr)
        self.arch = deque(maxlen=arch_size)  # 使用deque自动管理大小
        
        # 邻居定义：使用环形拓扑，每个粒子有k个邻居
        self.k_neighbors = 5
        self.neighborhood = self.create_ring_topology()
        
        self.X = np.random.uniform(-5.12, 5.12, (pop_size, dim))
        self.V = np.random.uniform(-1, 1, (pop_size, dim))
        self.pBest = self.X.copy()
        self.pBest_fit = np.array([func(x) for x in self.X])
        self.gBest_idx = np.argmin(self.pBest_fit)
        self.gBest = self.pBest[self.gBest_idx].copy()
        self.gBest_fit = self.pBest_fit[self.gBest_idx]
        self.convergence_curve = []
        self.metadata = {"strategy": "Context-Aware LEO-PSO"}

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

    def get_neighborhood_info(self, particle_idx):
        """获取粒子邻居的信息"""
        neighbors = self.neighborhood[particle_idx]
        # 计算邻居的pBest均值
        neighbor_pbests = self.pBest[neighbors]
        neighbor_mean = np.mean(neighbor_pbests, axis=0)
        
        # 计算邻居的适应度方差（搜索空间密度指标）
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
        
        # 6. 迭代进度（归一化）
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

    def learning_aided_mutation_with_context(self, particle_idx, iteration, total_iter):
        """基于上下文的变异操作"""
        # 构建上下文向量
        context = self.build_context_vector(particle_idx, iteration, total_iter)
        
        # 使用ANN预测移动方向（基于完整上下文）
        L_pBest = self.ann.forward(context.reshape(1, -1)).flatten()
        
        # 从邻居中随机选择两个进行差分变异
        neighbors = self.neighborhood[particle_idx]
        r1, r2 = random.sample(neighbors, 2)
        pBest_r1 = self.pBest[r1]
        pBest_r2 = self.pBest[r2]
        
        # 结合ANN预测和邻居信息
        newX = L_pBest + self.alpha * (pBest_r1 - pBest_r2)
        
        return newX

    def learning_aided_crossover(self, pBest_i, newX):
        """交叉操作"""
        cross_mask = np.random.uniform(0, 1, self.dim) <= self.beta
        final_X = np.where(cross_mask, newX, pBest_i)
        return final_X

    def run(self):
        g = 0
        for iteration in tqdm(range(self.max_iter), desc=self.metadata["strategy"]):
            g += 1
            r = random.uniform(0, 1)
            if g > 1 and r < self.lp:
                new_X = np.zeros_like(self.X)
                contexts = []  # 存储所有粒子的上下文
                for i in range(self.pop_size):
                    context = self.build_context_vector(i, iteration, self.max_iter)
                    contexts.append(context)
                    lm_X = self.learning_aided_mutation_with_context(i, iteration, self.max_iter)
                    lc_X = self.learning_aided_crossover(self.pBest[i], lm_X)
                    new_X[i] = lc_X
            else:
                # 标准PSO更新
                r1 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                r2 = np.random.uniform(0, 1, (self.pop_size, self.dim))
                self.V = self.w * self.V + self.c1 * r1 * (self.pBest - self.X) + self.c2 * r2 * (self.gBest - self.X)
                new_X = self.X + self.V
                new_X = np.clip(new_X, -5.12, 5.12)
                
                # 为记录经验构建上下文
                contexts = [self.build_context_vector(i, iteration, self.max_iter) 
                           for i in range(self.pop_size)]

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
                elif self.pBest_fit[i] > pBest_fit_old[i] and random.random() < 0.3:
                    # 偶尔记录反向经验（有选择地）
                    failure_direction = pBest_old[i] - self.pBest[i]
                    self.arch.append((contexts[i], failure_direction))

            # 训练ANN：学习上下文到移动方向的映射
            if len(self.arch) >= 10:  # 有足够样本时训练
                contexts_batch = np.array([exp[0] for exp in self.arch])
                directions_batch = np.array([exp[1] for exp in self.arch])
                # 确保批次大小与输入维度匹配
                if contexts_batch.shape[1] == self.context_dim:
                    self.ann.train(contexts_batch, directions_batch)
                else:
                    print(f"警告：上下文维度不匹配，期望{self.context_dim}，实际{contexts_batch.shape[1]}")

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 6. 测试函数 =====================
def rastrigin_func(x):
    """Rastrigin函数 - 经典多模态测试函数"""
    return 10 * len(x) + np.sum(x**2 - 10 * np.cos(2 * np.pi * x))

def ackley_func(x):
    """Ackley函数 - 另一个多模态测试函数"""
    a = 20
    b = 0.2
    c = 2 * np.pi
    d = len(x)
    
    sum1 = np.sum(x**2)
    sum2 = np.sum(np.cos(c * x))
    
    term1 = -a * np.exp(-b * np.sqrt(sum1 / d))
    term2 = -np.exp(sum2 / d)
    
    return term1 + term2 + a + np.e

def sphere_func(x):
    """Sphere函数 - 单模态基准函数"""
    return np.sum(x**2)

# ===================== 7. 三种算法对比实验 =====================
def compare_three_algorithms(func, func_name, dim=30, max_iter=500, runs=5):
    """
    比较三种PSO算法
    
    参数:
    - func: 测试函数
    - func_name: 函数名称
    - dim: 问题维度
    - max_iter: 最大迭代次数
    - runs: 运行次数
    """
    
    # 存储三种算法的结果
    algorithms = [
        ("Standard PSO", StandardPSO),
        ("LEO-PSO", LEO_PSO),
        ("Context-Aware LEO-PSO", ContextAware_LEO_PSO)
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
            # 实例化并运行算法
            try:
                if "Context-Aware" in algo_name:
                    # CA-LEO-PSO需要特殊参数
                    algo = AlgoClass(
                        func=func, 
                        dim=dim, 
                        pop_size=100,  # 显式指定种群大小
                        max_iter=max_iter,
                        arch_size=100,
                        ann_lr=0.01
                    )
                else:
                    # 其他算法使用默认参数
                    algo = AlgoClass(
                        func=func, 
                        dim=dim, 
                        pop_size=100,  # 显式指定种群大小
                        max_iter=max_iter
                    )
                
                # 运行算法
                _, best_fit, conv_curve = algo.run()
                
                # 存储结果
                results[algo_name]["best_fit"].append(best_fit)
                results[algo_name]["convergence"].append(conv_curve)
                
                # 打印本轮结果
                print(f"{algo_name:25s} | 最优值: {best_fit:.8f}")
            except Exception as e:
                print(f"{algo_name:25s} | 错误: {e}")
                # 存储默认值以避免后续分析错误
                results[algo_name]["best_fit"].append(float('inf'))
                results[algo_name]["convergence"].append([float('inf')] * max_iter)
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"{func_name}函数对比结果（{runs}轮均值±标准差）")
    print(f"{'='*60}")
    
    stats = {}
    for algo_name in results:
        # 过滤掉无穷大的值
        fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
        if len(fits) == 0:
            print(f"{algo_name:25s} | 所有运行都失败")
            continue
            
        mean_fit = np.mean(fits)
        std_fit = np.std(fits)
        stats[algo_name] = {"mean": mean_fit, "std": std_fit, "count": len(fits)}
        
        print(f"{algo_name:25s} | 均值: {mean_fit:.10f} ± {std_fit:.10f} (成功运行: {len(fits)}/{runs})")
    
    # 计算性能提升百分比（相对于Standard PSO）
    if "Standard PSO" in stats and stats["Standard PSO"]["mean"] != 0:
        print(f"\n性能提升（相对于Standard PSO）：")
        baseline = stats["Standard PSO"]["mean"]
        for algo_name in ["LEO-PSO", "Context-Aware LEO-PSO"]:
            if algo_name in stats:
                improvement = (baseline - stats[algo_name]["mean"]) / baseline * 100
                print(f"{algo_name:25s} | 提升: {improvement:.2f}%")
    
    # 收敛曲线可视化
    plot_convergence_curves(results, func_name, dim, max_iter)
    
    # 性能箱线图
    plot_boxplot(results, func_name)
    
    return results

def plot_convergence_curves(results, func_name, dim, max_iter):
    """绘制收敛曲线对比图"""
    plt.figure(figsize=(14, 8))
    
    # 颜色方案
    colors = {
        "Standard PSO": "#1f77b4",
        "LEO-PSO": "#ff7f0e",
        "Context-Aware LEO-PSO": "#d62728"
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
        std_curve = np.std(conv_curves, axis=0)
        
        # 绘制曲线
        iterations = range(len(mean_curve))
        plt.plot(iterations, mean_curve, label=f"{algo_name} ({len(valid_curves)} runs)", 
                linewidth=2.5, color=colors.get(algo_name, "#000000"))
        
        # 绘制标准差阴影
        plt.fill_between(iterations, 
                        mean_curve - std_curve, 
                        mean_curve + std_curve, 
                        alpha=0.15, color=colors.get(algo_name, "#000000"))
    
    plt.xlabel("Iteration", fontsize=14)
    plt.ylabel("Best Fitness (Log Scale)", fontsize=14)
    plt.title(f"Convergence Curves - {func_name} (Dim={dim})", fontsize=16, fontweight='bold')
    plt.legend(fontsize=10, loc='upper right')
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.yscale("log")
    plt.xlim(0, max_iter)
    
    # 添加次要网格
    plt.grid(True, which='minor', alpha=0.1, linestyle=':')
    
    plt.tight_layout()
    plt.savefig(f"{func_name}_three_algos_convergence.png", dpi=300, bbox_inches="tight")
    plt.show()

def plot_boxplot(results, func_name):
    """绘制性能箱线图"""
    plt.figure(figsize=(12, 6))
    
    # 准备数据
    data = []
    labels = []
    for algo_name in results:
        # 过滤掉无穷大的值
        fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
        if len(fits) > 0:
            data.append(fits)
            labels.append(f"{algo_name} ({len(fits)})")
    
    if len(data) == 0:
        print("没有有效数据可以绘制箱线图")
        return
    
    # 创建箱线图
    box = plt.boxplot(data, labels=labels, patch_artist=True, showmeans=True)
    
    # 设置颜色
    colors = ["#1f77b4", "#ff7f0e", "#d62728"]
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 设置中位数线和均值点
    plt.setp(box['medians'], color='black', linewidth=2)
    plt.setp(box['means'], marker='o', markerfacecolor='white', 
            markeredgecolor='black', markersize=8)
    
    plt.ylabel("Best Fitness", fontsize=14)
    plt.title(f"Algorithm Performance Comparison - {func_name}", fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # 旋转x轴标签
    plt.xticks(rotation=15)
    
    plt.tight_layout()
    plt.savefig(f"{func_name}_three_algos_boxplot.png", dpi=300, bbox_inches="tight")
    plt.show()

def detailed_analysis(results):
    """进行详细的统计分析"""
    print("\n" + "="*60)
    print("详细统计分析")
    print("="*60)
    
    # 对每种算法计算统计量
    for algo_name in results:
        # 过滤掉无穷大的值
        fits = [f for f in results[algo_name]["best_fit"] if f != float('inf')]
        if len(fits) == 0:
            print(f"\n{algo_name}: 无有效数据")
            continue
            
        fits = np.array(fits)
        
        print(f"\n{algo_name} (有效运行: {len(fits)}):")
        print(f"  最小值: {np.min(fits):.10f}")
        print(f"  最大值: {np.max(fits):.10f}")
        print(f"  中位数: {np.median(fits):.10f}")
        print(f"  均值: {np.mean(fits):.10f}")
        print(f"  标准差: {np.std(fits):.10f}")
        print(f"  变异系数: {np.std(fits)/np.mean(fits)*100:.2f}%")
        
        # 计算优于其他算法的次数
        for other_algo in results:
            if other_algo != algo_name:
                other_fits = [f for f in results[other_algo]["best_fit"] if f != float('inf')]
                if len(other_fits) > 0:
                    other_fits = np.array(other_fits)
                    # 确保长度相同
                    min_len = min(len(fits), len(other_fits))
                    wins = np.sum(fits[:min_len] < other_fits[:min_len])
                    ties = np.sum(fits[:min_len] == other_fits[:min_len])
                    print(f"  优于{other_algo}: {wins}/{min_len}次 (平局: {ties})")

# ===================== 8. 主程序 =====================
if __name__ == "__main__":
    # 设置随机种子以保证可重复性
    np.random.seed(42)
    random.seed(42)
    
    print("三种PSO算法对比实验")
    print("="*60)
    print("1. Standard PSO - 传统粒子群算法")
    print("2. LEO-PSO - 学习经验优化PSO")
    print("3. Context-Aware LEO-PSO - 上下文感知版")
    print("="*60)
    
    # 选择测试函数
    test_functions = [
        ("Rastrigin", rastrigin_func),
        # ("Ackley", ackley_func),
        # ("Sphere", sphere_func)
    ]
    
    for func_name, func in test_functions:
        # 运行对比实验 - 先用较小规模和较少轮次测试
        results = compare_three_algorithms(
            func=func,
            func_name=func_name,
            dim=30,          # 先测试较低维度
            max_iter=500,    # 减少迭代次数以加快实验
            runs=100          
        )
        
        # 进行详细分析
        detailed_analysis(results)
        
        print(f"\n{func_name}函数实验完成！")
        print("="*60 + "\n")
    
    print("所有实验完成！结果已保存为图片文件。")