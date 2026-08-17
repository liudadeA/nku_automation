import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import time
import sys
sys.path.append('.')
from importlib import import_module

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

try:
    import gymnasium as gym
except ImportError:
    import gym


class ExploringStartsMC:
    def __init__(self, mdp, gamma=0.99):
        self.mdp = mdp
        self.gamma = gamma
        self.n_states = mdp.n_states
        self.n_actions = mdp.n_actions
        self.Q = np.zeros((self.n_states, self.n_actions))
        self.returns = [[[] for _ in range(self.n_actions)] for _ in range(self.n_states)]
        self.policy = np.ones((self.n_states, self.n_actions)) / self.n_actions
        self.history = {'episodes': [], 'values': [], 'policy_changes': []}

    def generate_episode_with_start(self, env, start_state, start_action):
        state, _ = env.reset()
        env.unwrapped.state = self.mdp.continuous_state(start_state)
        state = env.unwrapped.state
        
        episode = []
        done = False
        truncated = False
        action = start_action
        first_step = True
        
        while not (done or truncated):
            s = self.mdp.discretize_state(state)
            if not first_step:
                action = np.random.choice(self.n_actions, p=self.policy[s])
            
            next_state, reward, done, truncated, _ = env.step(action)
            next_s = self.mdp.discretize_state(next_state)
            episode.append((s, action, reward))
            state = next_state
            first_step = False
            
            if len(episode) > 500:
                break
                
        return episode

    def run(self, n_episodes=10000, env=None):
        print("  开始探索性初始化MC...")
        
        if env is None:
            env = gym.make('CartPole-v1')
        
        close_env = False
        if env is None:
            env = gym.make('CartPole-v1')
            close_env = True
            
        policy_changes = 0
        
        for episode_idx in range(n_episodes):
            start_state = np.random.randint(0, self.n_states)
            start_action = np.random.randint(0, self.n_actions)
            
            episode = self.generate_episode_with_start(env, start_state, start_action)
            
            G = 0
            visited = set()
            
            for t in reversed(range(len(episode))):
                s, a, r = episode[t]
                G = self.gamma * G + r
                
                if (s, a) not in visited:
                    self.returns[s][a].append(G)
                    self.Q[s, a] = np.mean(self.returns[s][a])
                    visited.add((s, a))
                    
                    old_action = np.argmax(self.policy[s])
                    best_action = np.argmax(self.Q[s])
                    self.policy[s] = np.zeros(self.n_actions)
                    self.policy[s, best_action] = 1.0
                    
                    if old_action != best_action:
                        policy_changes += 1
            
            if (episode_idx + 1) % 1000 == 0:
                V = np.max(self.Q, axis=1)
                self.history['episodes'].append(episode_idx + 1)
                self.history['values'].append(V.copy())
                self.history['policy_changes'].append(policy_changes)
                print(f"    回合 {episode_idx + 1}, 策略变化: {policy_changes}, 平均V: {np.mean(V):.4f}")
        
        if close_env:
            env.close()
            
        V = np.max(self.Q, axis=1)
        return self.policy, V, self.Q


class OnPolicyMC:
    def __init__(self, mdp, gamma=0.99, epsilon=0.1):
        self.mdp = mdp
        self.gamma = gamma
        self.epsilon = epsilon
        self.n_states = mdp.n_states
        self.n_actions = mdp.n_actions
        self.Q = np.zeros((self.n_states, self.n_actions))
        self.returns = [[[] for _ in range(self.n_actions)] for _ in range(self.n_states)]
        self.policy = np.ones((self.n_states, self.n_actions)) / self.n_actions
        self.history = {'episodes': [], 'values': [], 'epsilons': []}

    def get_epsilon_soft_policy(self, s):
        best_action = np.argmax(self.Q[s])
        policy_s = np.ones(self.n_actions) * self.epsilon / self.n_actions
        policy_s[best_action] = 1 - self.epsilon + self.epsilon / self.n_actions
        return policy_s

    def generate_episode(self, env):
        state, _ = env.reset()
        episode = []
        done = False
        truncated = False
        
        while not (done or truncated):
            s = self.mdp.discretize_state(state)
            policy_s = self.get_epsilon_soft_policy(s)
            action = np.random.choice(self.n_actions, p=policy_s)
            
            next_state, reward, done, truncated, _ = env.step(action)
            episode.append((s, action, reward))
            state = next_state
            
            if len(episode) > 500:
                break
                
        return episode

    def run(self, n_episodes=10000, epsilon_start=1.0, epsilon_end=0.05, epsilon_decay=0.9995):
        print("  开始On-policy MC (ε-soft策略)...")
        
        env = gym.make('CartPole-v1')
        epsilon = epsilon_start
        
        for episode_idx in range(n_episodes):
            epsilon = max(epsilon_end, epsilon * epsilon_decay)
            self.epsilon = epsilon
            
            episode = self.generate_episode(env)
            
            G = 0
            visited = set()
            
            for t in reversed(range(len(episode))):
                s, a, r = episode[t]
                G = self.gamma * G + r
                
                if (s, a) not in visited:
                    self.returns[s][a].append(G)
                    self.Q[s, a] = np.mean(self.returns[s][a])
                    visited.add((s, a))
            
            for s in range(self.n_states):
                self.policy[s] = self.get_epsilon_soft_policy(s)
            
            if (episode_idx + 1) % 1000 == 0:
                V = np.max(self.Q, axis=1)
                self.history['episodes'].append(episode_idx + 1)
                self.history['values'].append(V.copy())
                self.history['epsilons'].append(epsilon)
                print(f"    回合 {episode_idx + 1}, ε={epsilon:.4f}, 平均V: {np.mean(V):.4f}")
        
        env.close()
        
        greedy_policy = np.zeros((self.n_states, self.n_actions))
        best_actions = np.argmax(self.Q, axis=1)
        greedy_policy[np.arange(self.n_states), best_actions] = 1.0
        
        V = np.max(self.Q, axis=1)
        return greedy_policy, V, self.Q


class OffPolicyMC:
    def __init__(self, mdp, gamma=0.99):
        self.mdp = mdp
        self.gamma = gamma
        self.n_states = mdp.n_states
        self.n_actions = mdp.n_actions
        self.Q = np.zeros((self.n_states, self.n_actions))
        self.C = np.zeros((self.n_states, self.n_actions))
        self.target_policy = np.ones((self.n_states, self.n_actions)) / self.n_actions
        self.behavior_policy = None
        self.history = {'episodes': [], 'values': [], 'weights': []}

    def get_behavior_policy(self, epsilon=0.5):
        policy = np.ones((self.n_states, self.n_actions)) * epsilon / self.n_actions
        best_actions = np.argmax(self.Q, axis=1)
        policy[np.arange(self.n_states), best_actions] = 1 - epsilon + epsilon / self.n_actions
        return policy

    def generate_episode_with_behavior(self, env, behavior_policy):
        state, _ = env.reset()
        episode = []
        done = False
        truncated = False
        
        while not (done or truncated):
            s = self.mdp.discretize_state(state)
            action = np.random.choice(self.n_actions, p=behavior_policy[s])
            
            next_state, reward, done, truncated, _ = env.step(action)
            episode.append((s, action, reward))
            state = next_state
            
            if len(episode) > 500:
                break
                
        return episode

    def run(self, n_episodes=10000, epsilon_start=0.8, epsilon_end=0.2, epsilon_decay=0.999):
        print("  开始Off-policy MC (重要性采样)...")
        
        env = gym.make('CartPole-v1')
        
        self.behavior_policy = self.get_behavior_policy(epsilon_start)
        
        total_weight = 0
        epsilon = epsilon_start
        
        for episode_idx in range(n_episodes):
            epsilon = max(epsilon_end, epsilon * epsilon_decay)
            self.behavior_policy = self.get_behavior_policy(epsilon)
            
            episode = self.generate_episode_with_behavior(env, self.behavior_policy)
            
            G = 0
            W = 1
            
            for t in reversed(range(len(episode))):
                s, a, r = episode[t]
                G = self.gamma * G + r
                
                self.C[s, a] += W
                self.Q[s, a] += (W / self.C[s, a]) * (G - self.Q[s, a])
                
                best_action = np.argmax(self.Q[s])
                self.target_policy[s] = np.zeros(self.n_actions)
                self.target_policy[s, best_action] = 1.0
                
                if a != best_action:
                    break
                
                if self.behavior_policy[s, a] > 0:
                    W = W * (self.target_policy[s, a] / self.behavior_policy[s, a])
                else:
                    break
                
                if W > 1e5:
                    break
            
            total_weight += W
            
            if (episode_idx + 1) % 1000 == 0:
                V = np.max(self.Q, axis=1)
                self.history['episodes'].append(episode_idx + 1)
                self.history['values'].append(V.copy())
                self.history['weights'].append(total_weight / (episode_idx + 1))
                print(f"    回合 {episode_idx + 1}, ε={epsilon:.4f}, 平均权重: {total_weight / (episode_idx + 1):.4f}, 平均V: {np.mean(V):.4f}")
        
        env.close()
        
        V = np.max(self.Q, axis=1)
        return self.target_policy.copy(), V, self.Q


def evaluate_policy(mdp, policy, n_episodes=100):
    env = gym.make('CartPole-v1')
    total_rewards = []
    
    for _ in range(n_episodes):
        state, _ = env.reset()
        episode_reward = 0
        done = False
        truncated = False
        
        while not (done or truncated):
            s = mdp.discretize_state(state)
            if np.sum(policy[s]) > 0:
                action = np.random.choice(mdp.n_actions, p=policy[s])
            else:
                action = np.argmax(policy[s])
            state, reward, done, truncated, _ = env.step(action)
            episode_reward += reward
            
        total_rewards.append(episode_reward)
    
    env.close()
    return np.mean(total_rewards), np.std(total_rewards)


def compare_mc_methods(mdp, n_episodes=5000):
    print("\n" + "=" * 70)
    print("蒙特卡洛方法比较：探索性初始化 vs On-policy vs Off-policy")
    print("=" * 70)
    
    results = {}
    
    print("\n[1/3] 探索性初始化MC...")
    t0 = time.time()
    es_mc = ExploringStartsMC(mdp)
    es_policy, es_V, es_Q = es_mc.run(n_episodes=n_episodes)
    es_time = time.time() - t0
    results['Exploring Starts'] = {
        'policy': es_policy, 'V': es_V, 'Q': es_Q, 
        'time': es_time, 'history': es_mc.history
    }
    
    print("\n[2/3] On-policy MC (ε-soft)...")
    t0 = time.time()
    on_mc = OnPolicyMC(mdp)
    on_policy, on_V, on_Q = on_mc.run(n_episodes=n_episodes)
    on_time = time.time() - t0
    results['On-policy'] = {
        'policy': on_policy, 'V': on_V, 'Q': on_Q,
        'time': on_time, 'history': on_mc.history
    }
    
    print("\n[3/3] Off-policy MC (重要性采样)...")
    t0 = time.time()
    off_mc = OffPolicyMC(mdp)
    off_policy, off_V, off_Q = off_mc.run(n_episodes=n_episodes)
    off_time = time.time() - t0
    results['Off-policy'] = {
        'policy': off_policy, 'V': off_V, 'Q': off_Q,
        'time': off_time, 'history': off_mc.history
    }
    
    print("\n" + "=" * 70)
    print("三种MC方法性能比较")
    print("=" * 70)
    print(f"\n{'方法':<20} {'运行时间(s)':<15} {'平均V值':<15} {'最大V值':<15}")
    print("-" * 70)
    for name, res in results.items():
        print(f"{name:<20} {res['time']:<15.2f} {np.mean(res['V']):<15.4f} {np.max(res['V']):<15.4f}")
    
    print("\n正在真实环境中评估策略（100回合）...")
    print(f"\n{'方法':<20} {'平均奖励':<15} {'标准差':<15}")
    print("-" * 70)
    for name, res in results.items():
        mean_r, std_r = evaluate_policy(mdp, res['policy'], n_episodes=100)
        print(f"{name:<20} {mean_r:<15.2f} {std_r:<15.2f}")
        results[name]['eval_reward'] = (mean_r, std_r)
    
    return results


def plot_mc_comparison(results, mdp):
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('三种MC方法比较分析', fontsize=16, fontweight='bold')
    
    colors = {'Exploring Starts': 'blue', 'On-policy': 'green', 'Off-policy': 'red'}
    labels_cn = {'Exploring Starts': '探索性初始化', 'On-policy': 'On-policy', 'Off-policy': 'Off-policy'}
    
    ax1 = fig.add_subplot(2, 4, 1)
    for name, res in results.items():
        if res['history']['episodes']:
            mean_values = [np.mean(v) for v in res['history']['values']]
            ax1.plot(res['history']['episodes'], mean_values, 
                    color=colors[name], label=labels_cn[name], linewidth=2)
    ax1.set_xlabel('回合数', fontsize=12)
    ax1.set_ylabel('平均状态值', fontsize=12)
    ax1.set_title('学习曲线 - 平均状态值', fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    ax2 = fig.add_subplot(2, 4, 2)
    for name, res in results.items():
        if res['history']['episodes']:
            max_values = [np.max(v) for v in res['history']['values']]
            ax2.plot(res['history']['episodes'], max_values,
                    color=colors[name], label=labels_cn[name], linewidth=2)
    ax2.set_xlabel('回合数', fontsize=12)
    ax2.set_ylabel('最大状态值', fontsize=12)
    ax2.set_title('学习曲线 - 最大状态值', fontsize=13)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    ax3 = fig.add_subplot(2, 4, 3)
    method_names = list(results.keys())
    eval_rewards = [results[name]['eval_reward'][0] for name in method_names]
    eval_stds = [results[name]['eval_reward'][1] for name in method_names]
    x_pos = np.arange(len(method_names))
    bars = ax3.bar(x_pos, eval_rewards, yerr=eval_stds, 
                   color=[colors[n] for n in method_names], alpha=0.7, capsize=5)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels([labels_cn[n] for n in method_names], fontsize=9)
    ax3.set_ylabel('平均回合奖励', fontsize=12)
    ax3.set_title('真实环境评估结果', fontsize=13)
    ax3.grid(True, alpha=0.3, axis='y')
    
    ax4 = fig.add_subplot(2, 4, 4)
    for name, res in results.items():
        V = res['V']
        ax4.hist(V, bins=50, alpha=0.5, label=labels_cn[name], color=colors[name])
    ax4.set_xlabel('状态值', fontsize=12)
    ax4.set_ylabel('状态数量', fontsize=12)
    ax4.set_title('状态值分布', fontsize=13)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    ax5 = fig.add_subplot(2, 4, 5)
    for name, res in results.items():
        if 'policy_changes' in res['history'] and res['history']['policy_changes']:
            ax5.plot(res['history']['episodes'], res['history']['policy_changes'],
                    color=colors[name], label=labels_cn[name], linewidth=2)
    ax5.set_xlabel('回合数', fontsize=12)
    ax5.set_ylabel('累计策略变化次数', fontsize=12)
    ax5.set_title('策略变化趋势', fontsize=13)
    ax5.legend(fontsize=10)
    ax5.grid(True, alpha=0.3)
    
    nb = mdp.n_bins
    method_list = list(results.keys())
    for idx, name in enumerate(method_list):
        ax = fig.add_subplot(2, 4, 6 + idx)
        policy = results[name]['policy']
        angle_action = np.full((nb, nb), np.nan)
        for i in range(nb):
            for j in range(nb):
                s = (nb // 2) * nb ** 3 + (nb // 2) * nb ** 2 + i * nb + j
                if s < mdp.n_states:
                    angle_action[i, j] = np.argmax(policy[s])
        
        im = ax.imshow(angle_action, cmap='RdYlGn', aspect='equal', vmin=0, vmax=1)
        ax.set_title(f'{labels_cn[name]}策略', fontsize=12)
        ax.set_xlabel('角速度索引', fontsize=10)
        ax.set_ylabel('角度索引', fontsize=10)
        cbar = plt.colorbar(im, ax=ax, ticks=[0, 1])
        cbar.set_label('动作 (绿=右, 红=左)', fontsize=9)
    
    plt.tight_layout()
    save_path = 'mc_methods_comparison.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n比较图已保存至: {save_path}")


def print_method_comparison():
    print("\n" + "=" * 70)
    print("三种MC方法的详细比较")
    print("=" * 70)
    
    comparison_text = """
┌─────────────────┬──────────────────────────┬──────────────────────────┬──────────────────────────┐
│     特性        │     探索性初始化         │     On-policy            │     Off-policy           │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 探索方式        │ 随机初始化状态和动作     │ ε-soft策略               │ 行为策略(ε-soft)         │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 策略类型        │ 贪婪策略                 │ ε-soft策略               │ 目标策略(贪婪)           │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 采样策略        │ 与目标策略相同           │ 与目标策略相同           │ 与目标策略不同           │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 重要性采样      │ 不需要                   │ 不需要                   │ 需要                     │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 方差            │ 较低                     │ 中等                     │ 较高(重要性采样)         │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 收敛速度        │ 较快                     │ 中等                     │ 较慢                     │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 适用场景        │ 可模拟环境               │ 在线学习                 │ 从历史数据学习           │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 实现复杂度      │ 简单                     │ 简单                     │ 复杂                     │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 主要优点        │ 高效探索                 │ 无需模拟环境             │ 可利用任意策略数据       │
├─────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ 主要缺点        │ 需要环境模拟能力         │ 探索效率较低             │ 高方差、收敛慢           │
└─────────────────┴──────────────────────────┴──────────────────────────┴──────────────────────────┘
"""
    print(comparison_text)
    
    print("\n【核心算法原理】")
    print("-" * 70)
    
    print("\n1. 探索性初始化MC (Exploring Starts MC):")
    print("   - 每个回合随机选择起始状态和动作")
    print("   - 使用First-Visit方法估计Q值")
    print("   - 策略改进采用贪婪策略")
    print("   - 保证所有状态-动作对都能被访问")
    
    print("\n2. On-policy MC (ε-soft策略):")
    print("   - 使用ε-soft策略保证持续探索")
    print("   - 策略以概率(1-ε)选择贪婪动作，以概率ε随机探索")
    print("   - 边采样边改进策略")
    print("   - 最终策略是软策略，不是完全贪婪")
    
    print("\n3. Off-policy MC (重要性采样):")
    print("   - 分离行为策略(用于采样)和目标策略(用于评估)")
    print("   - 使用重要性采样比修正不同策略下的期望")
    print("   - 可以从任意策略产生的数据中学习")
    print("   - 增量式更新: Q(s,a) += (W/C(s,a)) * (G - Q(s,a))")
    
    print("\n【关键公式】")
    print("-" * 70)
    print("\n探索性初始化 & On-policy MC:")
    print("   Q(s,a) = average(Returns(s,a))")
    print("   G_t = R_t + γR_{t+1} + γ²R_{t+2} + ...")
    
    print("\nOff-policy MC (加权重要性采样):")
    print("   Q(s,a) = Σ_k W_k * G_k / Σ_k W_k")
    print("   W = Π_{i=t}^{T-1} π(A_i|S_i) / b(A_i|S_i)")
    print("   其中π是目标策略，b是行为策略")


def main():
    print("\n" + "=" * 70)
    print("蒙特卡洛方法求解小车倒立摆问题")
    print("=" * 70)
    
    from importlib import import_module
    module = import_module('3')
    CartPoleDiscreteMDP = module.CartPoleDiscreteMDP
    
    print("\n正在构建MDP环境...")
    mdp = CartPoleDiscreteMDP(n_bins=8, use_env_sampling=True, n_samples=30000)
    
    print(f"\n【MDP环境设置】")
    print(f"  离散化bin数: {mdp.n_bins}")
    print(f"  总状态数: {mdp.n_states}")
    print(f"  动作数: {mdp.n_actions}")
    print(f"  折扣因子γ: {mdp.gamma}")
    
    results = compare_mc_methods(mdp, n_episodes=5000)
    
    plot_mc_comparison(results, mdp)
    
    print_method_comparison()
    
    print("\n" + "=" * 70)
    print("实验完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
