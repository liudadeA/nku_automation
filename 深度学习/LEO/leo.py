import numpy as np
import random
import matplotlib.pyplot as plt
from tqdm import tqdm

# ===================== 1. 工具类：ANN（三者共用） =====================
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

# ===================== 2. 基础算法：传统PSO =====================
class StandardPSO:
    def __init__(self, func, dim=30, pop_size=500, max_iter=500, w=0.7, c1=1.5, c2=1.5):
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

    def run(self):
        for _ in tqdm(range(self.max_iter), desc="Standard PSO"):
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

# ===================== 3. 原版LEO-PSO =====================
class LEO_PSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=350, alpha=0.5, beta=0.9, ann_lr=0.01):
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
        for _ in tqdm(range(self.max_iter), desc="LEO-PSO"):
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

# ===================== 4. 增强版E-LEO-PSO（核心优化） =====================
class Enhanced_LEO_PSO:
    def __init__(self, func, dim=30, pop_size=100, max_iter=500,
                 w=0.7, c1=1.5, c2=1.5, lp=0.5, arch_size=350, alpha=0.5, beta=0.9, ann_lr=0.01):
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
        self.arch = []  # 存储扩展后的SEP

        self.X = np.random.uniform(-5.12, 5.12, (pop_size, dim))
        self.V = np.random.uniform(-1, 1, (pop_size, dim))
        self.pBest = self.X.copy()
        self.pBest_fit = np.array([func(x) for x in self.X])
        self.gBest_idx = np.argmin(self.pBest_fit)
        self.gBest = self.pBest[self.gBest_idx].copy()
        self.gBest_fit = self.pBest_fit[self.gBest_idx]
        self.convergence_curve = []

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
        for _ in tqdm(range(self.max_iter), desc="Enhanced LEO-PSO"):
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

            # ========== 核心优化：扩展SEP收集逻辑 ==========
            for i in range(self.pop_size):
                if self.pBest_fit[i] < pBest_fit_old[i]:
                    # 正向经验：x_old→x_new更优，存(x_old, x_new)
                    self.arch.append((pBest_old[i], self.pBest[i]))
                elif self.pBest_fit[i] > pBest_fit_old[i]:
                    # 反向经验：x_new→x_old更优，存(x_new, x_old)（补充反向成功经验）
                    self.arch.append((self.pBest[i], pBest_old[i]))
                # 相等时不存储（无进化价值）

            # 存档管理（与原版一致）
            if len(self.arch) > self.arch_size:
                self.arch = self.arch[-self.arch_size:]

            # 训练ANN（用扩展后的SEP，学习更多进化规律）
            if len(self.arch) > 0:
                X_train = np.array([sep[0] for sep in self.arch])
                y_train = np.array([sep[1] for sep in self.arch])
                self.ann.train(X_train, y_train)

            self.convergence_curve.append(self.gBest_fit)

        return self.gBest, self.gBest_fit, self.convergence_curve

# ===================== 5. 测试函数：Rastrigin（多模态） =====================
def rastrigin_func(x):
    return 10 * len(x) + np.sum(x**2 - 10 * np.cos(2 * np.pi * x))

# ===================== 6. 三者对比实验主逻辑 =====================
def compare_three_algorithms(func, func_name, dim=30, max_iter=500, runs=5):
    # 存储三类算法的结果
    std_pso_res = {"best_fit": [], "convergence": []}
    leo_pso_res = {"best_fit": [], "convergence": []}
    e_leo_pso_res = {"best_fit": [], "convergence": []}

    for run in range(runs):
        print(f"\n===== 第 {run+1}/{runs} 轮测试 =====")
        
        # 1. 传统PSO
        std_pso = StandardPSO(func=func, dim=dim, max_iter=max_iter)
        _, std_fit, std_conv = std_pso.run()
        std_pso_res["best_fit"].append(std_fit)
        std_pso_res["convergence"].append(std_conv)

        # 2. 原版LEO-PSO
        leo_pso = LEO_PSO(func=func, dim=dim, max_iter=max_iter)
        _, leo_fit, leo_conv = leo_pso.run()
        leo_pso_res["best_fit"].append(leo_fit)
        leo_pso_res["convergence"].append(leo_conv)

        # 3. 增强版E-LEO-PSO
        e_leo_pso = Enhanced_LEO_PSO(func=func, dim=dim, max_iter=max_iter)
        _, e_leo_fit, e_leo_conv = e_leo_pso.run()
        e_leo_pso_res["best_fit"].append(e_leo_fit)
        e_leo_pso_res["convergence"].append(e_leo_conv)

    # 统计结果（高精度）
    std_mean = np.mean(std_pso_res["best_fit"])
    std_std = np.std(std_pso_res["best_fit"])
    leo_mean = np.mean(leo_pso_res["best_fit"])
    leo_std = np.std(leo_pso_res["best_fit"])
    e_leo_mean = np.mean(e_leo_pso_res["best_fit"])
    e_leo_std = np.std(e_leo_pso_res["best_fit"])

    print(f"\n===== {func_name} 函数对比结果（{runs}轮均值） =====")
    print(f"传统PSO   | 最优适应度均值：{std_mean:.10f} | 标准差：{std_std:.10f}")
    print(f"原版LEO-PSO | 最优适应度均值：{leo_mean:.10f} | 标准差：{leo_std:.10f}")
    print(f"增强版E-LEO-PSO | 最优适应度均值：{e_leo_mean:.10f} | 标准差：{e_leo_std:.10f}")
    
    # 计算性能提升（相对传统PSO）
    leo_improve = (std_mean - leo_mean)/std_mean * 100 if std_mean !=0 else 100
    e_leo_improve = (std_mean - e_leo_mean)/std_mean * 100 if std_mean !=0 else 100
    e_leo_improve2 = (leo_mean - e_leo_mean)/leo_mean * 100 if leo_mean !=0 else 100
    print(f"\n性能提升（相对传统PSO）：")
    print(f"原版LEO-PSO：{leo_improve:.2f}%")
    print(f"增强版E-LEO-PSO：{e_leo_improve:.2f}%")
    print(f"增强版E-LEO-PSO(相对于leo)：{e_leo_improve2:.2f}%")
    # 收敛曲线可视化（三者对比）
    std_conv_mean = np.mean(std_pso_res["convergence"], axis=0)
    leo_conv_mean = np.mean(leo_pso_res["convergence"], axis=0)
    e_leo_conv_mean = np.mean(e_leo_pso_res["convergence"], axis=0)

    plt.figure(figsize=(12, 7))
    plt.plot(range(max_iter), std_conv_mean, label="Standard PSO", linewidth=2, color="#1f77b4")
    plt.plot(range(max_iter), leo_conv_mean, label="LEO-PSO", linewidth=2, color="#ff7f0e")
    plt.plot(range(max_iter), e_leo_conv_mean, label="Enhanced LEO-PSO", linewidth=2, color="#2ca02c")
    plt.xlabel("Iteration", fontsize=12)
    plt.ylabel("Best Fitness (Lower is Better)", fontsize=12)
    plt.title(f"Convergence Curve - {func_name} (Dim={dim})", fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(alpha=0.3)
    plt.yscale("log")  # 对数坐标更清晰
    plt.savefig(f"{func_name}_three_algos_convergence.png", dpi=300, bbox_inches="tight")
    plt.show()

# ===================== 7. 运行对比实验 =====================
if __name__ == "__main__":
    compare_three_algorithms(func=rastrigin_func, func_name="Rastrigin", dim=30, max_iter=500, runs=30)