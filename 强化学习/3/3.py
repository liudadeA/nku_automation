import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import time

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

class CartPoleDiscreteMDP:

    def __init__(self, n_bins=8, use_env_sampling=True, n_samples=50000):
        self.n_bins = n_bins
        self.n_actions = 2
        self.action_names = ['左', '右']
        self.gamma = 0.99

        self.position_bins      = np.linspace(-2.4,  2.4,  n_bins + 1)[1:-1]
        self.velocity_bins      = np.linspace(-3.0,  3.0,  n_bins + 1)[1:-1]
        self.angle_bins         = np.linspace(-0.2,  0.2,  n_bins + 1)[1:-1]
        self.angular_velocity_bins = np.linspace(-3.0, 3.0, n_bins + 1)[1:-1]

        self.n_states = n_bins ** 4

        if use_env_sampling:
            self._build_transition_matrix_from_env(n_samples)
        else:
            self._build_transition_matrix()

        # 预计算转移张量
        self._precompute_transition_arrays()

    def discretize_state(self, state):
        cart_pos, cart_vel, pole_angle, pole_ang_vel = state
        pos_idx     = int(np.clip(np.digitize(cart_pos,     self.position_bins),      0, self.n_bins - 1))
        vel_idx     = int(np.clip(np.digitize(cart_vel,     self.velocity_bins),      0, self.n_bins - 1))
        angle_idx   = int(np.clip(np.digitize(pole_angle,   self.angle_bins),         0, self.n_bins - 1))
        ang_vel_idx = int(np.clip(np.digitize(pole_ang_vel, self.angular_velocity_bins), 0, self.n_bins - 1))
        return (pos_idx * self.n_bins ** 3 +
                vel_idx * self.n_bins ** 2 +
                angle_idx * self.n_bins +
                ang_vel_idx)

    def continuous_state(self, state_idx):
        pos_idx     = state_idx // (self.n_bins ** 3)
        remaining   = state_idx  % (self.n_bins ** 3)
        vel_idx     = remaining  // (self.n_bins ** 2)
        remaining   = remaining  % (self.n_bins ** 2)
        angle_idx   = remaining  // self.n_bins
        ang_vel_idx = remaining  %  self.n_bins

        pos_edges = np.concatenate([[-2.5], self.position_bins,         [2.5]])
        vel_edges = np.concatenate([[-3.5], self.velocity_bins,         [3.5]])
        ang_edges = np.concatenate([[-0.25], self.angle_bins,           [0.25]])
        angv_edges= np.concatenate([[-3.5], self.angular_velocity_bins, [3.5]])

        return np.array([
            (pos_edges [pos_idx]     + pos_edges [pos_idx + 1])     / 2,
            (vel_edges [vel_idx]     + vel_edges [vel_idx + 1])     / 2,
            (ang_edges [angle_idx]   + ang_edges [angle_idx + 1])   / 2,
            (angv_edges[ang_vel_idx] + angv_edges[ang_vel_idx + 1]) / 2,
        ])

    # 构建转移矩阵

    def _build_transition_matrix_from_env(self, n_samples):
        try:
            import gymnasium as gym
        except ImportError:
            import gym

        print(f"正在从真实环境采样 {n_samples} 次构建转移矩阵...")
        env = gym.make('CartPole-v1')

        # trans_data[s][a][next_s] = {'count': int, 'reward_sum': float, 'done': bool}
        trans_data = [[{} for _ in range(self.n_actions)] for _ in range(self.n_states)]

        total_samples = 0
        last_print    = 0

        while total_samples < n_samples:
            state, _ = env.reset()
            terminated = truncated = False

            while not (terminated or truncated) and total_samples < n_samples:
                s      = self.discretize_state(state)
                action = env.action_space.sample()
                next_state, reward, terminated, truncated, _ = env.step(action)
                next_s = self.discretize_state(next_state)

                # 步数超限不代表失败，未来值不应截断
                entry = trans_data[s][action]
                if next_s not in entry:
                    entry[next_s] = {'count': 0, 'reward_sum': 0.0, 'done': False}
                entry[next_s]['count']      += 1
                entry[next_s]['reward_sum'] += reward
                if terminated:
                    entry[next_s]['done'] = True  # 任何一次终止均标记

                state = next_state
                total_samples += 1
                if total_samples - last_print >= 5000:
                    print(f"  采样进度: {total_samples}/{n_samples} "
                          f"({100 * total_samples / n_samples:.0f}%)")
                    last_print = total_samples

        env.close()

        print("  正在构建转移矩阵...")
        self.P = {}
        for s in range(self.n_states):
            self.P[s] = {}
            for a in range(self.n_actions):
                total = sum(d['count'] for d in trans_data[s][a].values())
                if total == 0:
                    # 未采样到的状态：视为终止（done=True），避免错误的值传播
                    self.P[s][a] = [(1.0, s, 0.0, True)]
                else:
                    self.P[s][a] = [
                        (d['count'] / total,
                         next_s,
                         d['reward_sum'] / d['count'],
                         d['done'])
                        for next_s, d in trans_data[s][a].items()
                    ]

        print(f"采样完成，共 {total_samples} 次转移")

    def _build_transition_matrix(self):
        self.P = {}
        gravity         = 9.8
        masscart        = 1.0
        masspole        = 0.1
        total_mass      = masspole + masscart
        length          = 0.5
        polemass_length = masspole * length
        force_mag       = 10.0
        tau             = 0.02

        for s in range(self.n_states):
            self.P[s] = {}
            x, x_dot, theta, theta_dot = self.continuous_state(s)

            for a in range(self.n_actions):
                force     = force_mag if a == 1 else -force_mag
                costheta  = np.cos(theta)
                sintheta  = np.sin(theta)

                temp     = (force + polemass_length * theta_dot ** 2 * sintheta) / total_mass
                thetaacc = (gravity * sintheta - costheta * temp) / (
                    length * (4.0 / 3.0 - masspole * costheta ** 2 / total_mass))
                xacc     = temp - polemass_length * thetaacc * costheta / total_mass

                x_new        = x     + tau * x_dot
                x_dot_new    = x_dot + tau * xacc
                theta_new    = theta     + tau * theta_dot
                theta_dot_new= theta_dot + tau * thetaacc

                terminated = (x_new < -2.4 or x_new > 2.4 or
                              theta_new < -0.2095 or theta_new > 0.2095)

                if terminated:
                    # 未来值由 compute_q_values 清零
                    self.P[s][a] = [(1.0, s, 0.0, True)]
                else:
                    new_s = self.discretize_state(
                        [x_new, x_dot_new, theta_new, theta_dot_new])
                    self.P[s][a] = [(1.0, new_s, 1.0, False)]

    def _precompute_transition_arrays(self):
        n  = self.n_states
        na = self.n_actions
        max_t = max(len(self.P[s][a]) for s in range(n) for a in range(na))

        self.T_prob   = np.zeros((n, na, max_t), dtype=np.float64)
        self.T_next   = np.zeros((n, na, max_t), dtype=np.int32)
        self.T_reward = np.zeros((n, na, max_t), dtype=np.float64)
        self.T_done   = np.zeros((n, na, max_t), dtype=np.float64)

        for s in range(n):
            for a in range(na):
                for t, (prob, next_s, reward, done) in enumerate(self.P[s][a]):
                    self.T_prob  [s, a, t] = prob
                    self.T_next  [s, a, t] = int(next_s)
                    self.T_reward[s, a, t] = reward
                    self.T_done  [s, a, t] = float(done)

        # 期望即时奖励 R[s, a] = Σ_t p_t · r_t
        self.R_mat = np.sum(self.T_prob * self.T_reward, axis=2)  # (n, na)

    def compute_q_values(self, V):
        next_vals = V[self.T_next]          # (n, na, max_t)
        not_done  = 1.0 - self.T_done       # (n, na, max_t)
        future    = self.gamma * np.sum(self.T_prob * next_vals * not_done, axis=2)
        return self.R_mat + future           # (n, na)

class PolicyEvaluation:

    def __init__(self, mdp):
        self.mdp = mdp

    def evaluate_analytical(self, policy):
        n     = self.mdp.n_states
        gamma = self.mdp.gamma
        na    = self.mdp.n_actions
        max_t = self.mdp.T_prob.shape[2]

        # R_pi[s] = Σ_a π(a|s) · R_mat[s,a]
        R_pi = np.einsum('sa,sa->s', policy, self.mdp.R_mat)  # (n,)

        # P_pi[s,s'] = Σ_a π(a|s) · Σ_t p_t · (1-done_t) · δ(s', next_s_t)
        P_pi = np.zeros((n, n))
        idx  = np.arange(n)
        for a in range(na):
            for t in range(max_t):
                prob    = self.mdp.T_prob [:, a, t]          # (n,)
                next_s  = self.mdp.T_next [:, a, t]          # (n,)
                not_done= 1.0 - self.mdp.T_done[:, a, t]     # (n,)
                weight  = policy[:, a] * prob * not_done      # (n,)
                np.add.at(P_pi, (idx, next_s), weight)       # scatter-add

        A = np.eye(n) - gamma * P_pi
        try:
            V = np.linalg.solve(A, R_pi)
        except np.linalg.LinAlgError:
            V = np.linalg.lstsq(A, R_pi, rcond=None)[0]
        return V

    def evaluate_iterative(self, policy, tol=1e-6, max_iter=5000):
        V = np.zeros(self.mdp.n_states)

        for iteration in range(max_iter):
            Q     = self.mdp.compute_q_values(V)         # (n, na)
            V_new = np.einsum('sa,sa->s', policy, Q)     # (n,)  向量化！

            delta = np.max(np.abs(V_new - V))
            V     = V_new
            if delta < tol:
                return V, iteration + 1

        print(f"      警告: 策略评估未收敛, delta={delta:.2e}")
        return V, max_iter

class PolicyIteration:
    def __init__(self, mdp):
        self.mdp       = mdp
        self.evaluator = PolicyEvaluation(mdp)
        self.history   = {'iterations': [], 'policies': [], 'values': []}

    def run(self, max_iterations=100, eval_method='analytical'):
        n_states  = self.mdp.n_states
        n_actions = self.mdp.n_actions

        # 均匀随机策略初始化
        policy = np.ones((n_states, n_actions)) / n_actions
        self.history = {'iterations': [], 'policies': [], 'values': []}

        print("  开始策略迭代...")
        for iteration in range(max_iterations):
            print(f"    策略迭代第 {iteration + 1} 轮...")

            if eval_method == 'analytical':
                V = self.evaluator.evaluate_analytical(policy)
            else:
                V, eval_iters = self.evaluator.evaluate_iterative(policy)
                print(f"      策略评估迭代了 {eval_iters} 次")

            self.history['iterations'].append(iteration)
            self.history['values'].append(V.copy())
            self.history['policies'].append(policy.copy())

            # 向量化
            Q            = self.mdp.compute_q_values(V)           # (n, na)
            best_actions = np.argmax(Q, axis=1)                   # (n,)
            new_policy   = np.zeros((n_states, n_actions))
            new_policy[np.arange(n_states), best_actions] = 1.0

            old_actions     = np.argmax(policy, axis=1)
            changed_states  = np.sum(old_actions != best_actions)
            print(f"      策略变化: {changed_states} 个状态")

            policy = new_policy

            if changed_states == 0:
                print(f"  策略迭代收敛，共 {iteration + 1} 轮")
                self.history['iterations'].append(iteration + 1)
                self.history['values'].append(V.copy())
                self.history['policies'].append(policy.copy())
                return policy, V, iteration + 1

        print(f"  策略迭代达到最大轮数 {max_iterations}")
        return policy, V, max_iterations

class ValueIteration:
    def __init__(self, mdp):
        self.mdp     = mdp
        self.history = {'iterations': [], 'values': [], 'deltas': []}

    def run(self, tol=1e-6, max_iterations=1000):
        n_states  = self.mdp.n_states
        n_actions = self.mdp.n_actions
        V         = np.zeros(n_states)
        self.history = {'iterations': [], 'values': [], 'deltas': []}

        print("  开始值迭代...")
        for iteration in range(max_iterations):
            # 向量化贝尔曼最优方程
            Q     = self.mdp.compute_q_values(V)   # (n, na)
            V_new = np.max(Q, axis=1)              # (n,)  向量化！

            delta = np.max(np.abs(V_new - V))
            V     = V_new

            self.history['iterations'].append(iteration)
            self.history['values'].append(V.copy())
            self.history['deltas'].append(delta)

            if iteration % 20 == 0:
                print(f"    值迭代第 {iteration + 1} 轮, delta={delta:.2e}")

            if delta < tol:
                print(f"  值迭代收敛，共 {iteration + 1} 轮")
                break

        # 提取最优策略
        Q            = self.mdp.compute_q_values(V)
        best_actions = np.argmax(Q, axis=1)
        policy       = np.zeros((n_states, n_actions))
        policy[np.arange(n_states), best_actions] = 1.0

        return policy, V, iteration + 1

def evaluate_policy_with_env(mdp, policy, n_episodes=100):
    try:
        import gymnasium as gym
    except ImportError:
        import gym

    env           = gym.make('CartPole-v1')
    total_rewards = []

    for _ in range(n_episodes):
        state, _      = env.reset()
        episode_reward = 0
        done = truncated = False

        while not (done or truncated):
            s               = mdp.discretize_state(state)
            action          = np.argmax(policy[s])
            state, reward, done, truncated, _ = env.step(action)
            episode_reward += reward
        total_rewards.append(episode_reward)

    env.close()
    return np.mean(total_rewards), np.std(total_rewards)

def print_policy_sample(policy, mdp, n_samples=10):
    print("\n策略样本（部分状态）：")
    print("-" * 60)
    for i in range(min(n_samples, mdp.n_states)):
        state  = mdp.continuous_state(i)
        action = np.argmax(policy[i])
        print(f"状态{i:4d}: 位置={state[0]:+.2f}  角度={state[2]:+.3f} "
              f"-> 动作: {mdp.action_names[action]}")

def compare_algorithms(mdp):
    print("\n" + "=" * 60)
    print("策略迭代 vs 值迭代  比较分析")
    print("=" * 60)

    pi = PolicyIteration(mdp)
    vi = ValueIteration(mdp)

    print("\n正在运行策略迭代（解析法评估）...")
    t0 = time.time()
    pi_policy, pi_value, pi_iters = pi.run(eval_method='analytical')
    pi_time = time.time() - t0

    print("\n正在运行值迭代...")
    t0 = time.time()
    vi_policy, vi_value, vi_iters = vi.run()
    vi_time = time.time() - t0

    print("\n【算法性能比较】")
    print("-" * 50)
    print(f"{'指标':<20} {'策略迭代':<15} {'值迭代':<15}")
    print("-" * 50)
    print(f"{'迭代次数':<20} {pi_iters:<15} {vi_iters:<15}")
    print(f"{'运行时间(秒)':<20} {pi_time:<15.4f} {vi_time:<15.4f}")
    print(f"{'平均状态值':<20} {np.mean(pi_value):<15.4f} {np.mean(vi_value):<15.4f}")
    print(f"{'最大状态值':<20} {np.max(pi_value):<15.4f} {np.max(vi_value):<15.4f}")

    print("\n最优策略样本（策略迭代）")
    print_policy_sample(pi_policy, mdp, n_samples=8)

    return pi, vi, pi_policy, vi_policy

def plot_convergence(pi, vi, mdp):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('策略迭代 vs 值迭代  收敛分析', fontsize=16, fontweight='bold')

    # 子图1：最大状态值收敛曲线
    ax1 = axes[0, 0]
    pi_max = [np.max(v) for v in pi.history['values']]
    vi_max = [np.max(v) for v in vi.history['values']]
    ax1.plot(pi_max, 'b-o', label='策略迭代', markersize=6)
    ax1.plot(vi_max, 'r-s', label='值迭代',   markersize=4)
    ax1.set_xlabel('迭代次数', fontsize=12)
    ax1.set_ylabel('最大状态值', fontsize=12)
    ax1.set_title('收敛过程 — 最大状态值', fontsize=13)
    ax1.legend(fontsize=11); ax1.grid(True, alpha=0.3)

    # 子图2：平均状态值收敛曲线
    ax2 = axes[0, 1]
    pi_mean_v = [np.mean(v) for v in pi.history['values']]
    vi_mean_v = [np.mean(v) for v in vi.history['values']]
    ax2.plot(pi_mean_v, 'b-o', label='策略迭代', markersize=6)
    ax2.plot(vi_mean_v, 'r-s', label='值迭代',   markersize=4)
    ax2.set_xlabel('迭代次数', fontsize=12)
    ax2.set_ylabel('平均状态值', fontsize=12)
    ax2.set_title('收敛过程 — 平均状态值', fontsize=13)
    ax2.legend(fontsize=11); ax2.grid(True, alpha=0.3)

    # 子图3：值迭代 delta 对数收敛
    ax3 = axes[1, 0]
    ax3.semilogy(vi.history['deltas'], 'r-', linewidth=2, label='值迭代 δ')
    ax3.axhline(y=1e-6, color='g', linestyle='--', label='收敛阈值 1e-6')
    ax3.set_xlabel('迭代次数', fontsize=12)
    ax3.set_ylabel('δ (对数尺度)', fontsize=12)
    ax3.set_title('值迭代收敛速度', fontsize=13)
    ax3.legend(fontsize=11); ax3.grid(True, alpha=0.3)

    # 子图4：策略可视化（角度-角速度平面，固定位置/速度为中心）
    ax4 = axes[1, 1]
    nb   = mdp.n_bins
    angle_action = np.full((nb, nb), np.nan)
    final_policy = pi.history['policies'][-1]
    for i in range(nb):
        for j in range(nb):
            s = (nb // 2) * nb ** 3 + (nb // 2) * nb ** 2 + i * nb + j
            if s < mdp.n_states:
                angle_action[i, j] = np.argmax(final_policy[s])

    im = ax4.imshow(angle_action, cmap='RdYlGn', aspect='equal', vmin=0, vmax=1)
    ax4.set_title('最优策略（角度-角速度，位置/速度固定居中）', fontsize=12)
    ax4.set_xlabel('角速度离散索引', fontsize=11)
    ax4.set_ylabel('角度离散索引',   fontsize=11)
    cbar = plt.colorbar(im, ax=ax4)
    cbar.set_label('动作 (绿=右, 红=左)', fontsize=10)

    plt.tight_layout()
    save_path = 'policy_value_iteration.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n收敛图已保存至: {save_path}")

def main():
    print("\n" + "=" * 60)
    print("强化学习 — 策略迭代与值迭代算法实验")
    print("基于 CartPole-v1 离散化 MDP")
    print("=" * 60)

    # 默认使用真实环境采样
    mdp = CartPoleDiscreteMDP(n_bins=8, use_env_sampling=True, n_samples=50000)

    print("\n【MDP 环境设置】")
    print(f"  离散化 bin 数: {mdp.n_bins}")
    print(f"  总状态数:       {mdp.n_states}")
    print(f"  动作数:         {mdp.n_actions}  {mdp.action_names}")
    print(f"  折扣因子 γ:     {mdp.gamma}")
    print(f"  转移张量 max_t: {mdp.T_prob.shape[2]}")

    # ── 算法比较 ──
    pi, vi, pi_policy, vi_policy = compare_algorithms(mdp)

    # ── 可视化 ──
    plot_convergence(pi, vi, mdp)

    # ── 真实环境评估 ──
    print("\n正在用真实 CartPole 环境评估策略（100 回合）...")
    try:
        pi_mean, pi_std = evaluate_policy_with_env(mdp, pi_policy)
        vi_mean, vi_std = evaluate_policy_with_env(mdp, vi_policy)

        # 随机基线
        try:
            import gymnasium as gym
        except ImportError:
            import gym
        env            = gym.make('CartPole-v1')
        random_rewards = []
        for _ in range(100):
            state, _ = env.reset()
            total    = 0
            done = truncated = False
            while not (done or truncated):
                action = env.action_space.sample()
                state, r, done, truncated, _ = env.step(action)
                total += r
            random_rewards.append(total)
        env.close()
        rnd_mean, rnd_std = np.mean(random_rewards), np.std(random_rewards)

        print("\n【真实环境评估结果】")
        print("-" * 52)
        print(f"{'策略':<20} {'平均奖励':>10}  {'标准差':>10}")
        print("-" * 52)
        print(f"{'策略迭代':<20} {pi_mean:>10.2f}  {pi_std:>10.2f}")
        print(f"{'值迭代':<20} {vi_mean:>10.2f}  {vi_std:>10.2f}")
        print(f"{'随机策略（基线）':<20} {rnd_mean:>10.2f}  {rnd_std:>10.2f}")
        print(f"\n相比随机策略的提升：")
        print(f"  策略迭代: +{(pi_mean - rnd_mean) / rnd_mean * 100:.1f}%")
        print(f"  值  迭代: +{(vi_mean - rnd_mean) / rnd_mean * 100:.1f}%")
    except Exception as e:
        print(f"  环境评估失败（可能未安装 gymnasium）: {e}")

if __name__ == "__main__":
    main()