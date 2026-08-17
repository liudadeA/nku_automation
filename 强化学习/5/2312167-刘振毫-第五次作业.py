import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import time

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

try:
    import gymnasium as gym
except ImportError:
    import gym


class CartPoleDiscreteMDP:
    def __init__(self, n_bins=8, gamma=0.99):
        self.n_bins = n_bins
        self.gamma = gamma
        self.n_actions = 2
        self.state_bounds = [
            (-2.4, 2.4),
            (-3.0, 3.0),
            (-0.5, 0.5),
            (-2.0, 2.0)
        ]
        self.n_states = n_bins ** 4
    
    def discretize_state(self, state):
        discretized = []
        for i, (s, (low, high)) in enumerate(zip(state, self.state_bounds)):
            s = np.clip(s, low, high)
            bin_width = (high - low) / self.n_bins
            discretized.append(int((s - low) / bin_width))
            discretized[-1] = min(discretized[-1], self.n_bins - 1)
        
        index = 0
        for i, d in enumerate(discretized):
            index = index * self.n_bins + d
        return index
    
    def continuous_state(self, index):
        state = []
        temp = index
        for i in range(4):
            state.append(temp % self.n_bins)
            temp = temp // self.n_bins
        state = state[::-1]
        
        continuous = []
        for i, (d, (low, high)) in enumerate(zip(state, self.state_bounds)):
            bin_width = (high - low) / self.n_bins
            continuous.append(low + (d + 0.5) * bin_width)
        return continuous


class SARSA:
    def __init__(self, mdp, gamma=0.99, alpha=0.1, epsilon=0.1):
        self.mdp = mdp
        self.gamma = gamma
        self.alpha = alpha
        self.epsilon = epsilon
        self.n_states = mdp.n_states
        self.n_actions = mdp.n_actions
        self.Q = np.zeros((self.n_states, self.n_actions))
        self.policy = np.ones((self.n_states, self.n_actions)) / self.n_actions
        self.history = {'episodes': [], 'rewards': [], 'values': []}
    
    def choose_action(self, s):
        if np.random.random() < self.epsilon:
            return np.random.randint(0, self.n_actions)
        else:
            return np.argmax(self.Q[s])
    
    def run(self, n_episodes=5000, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.999):
        print("  开始SARSA算法...")
        
        env = gym.make('CartPole-v1')
        epsilon = epsilon_start
        
        for episode_idx in range(n_episodes):
            epsilon = max(epsilon_end, epsilon * epsilon_decay)
            self.epsilon = epsilon
            
            state, _ = env.reset()
            s = self.mdp.discretize_state(state)
            a = self.choose_action(s)
            done = False
            truncated = False
            total_reward = 0
            
            while not (done or truncated):
                next_state, reward, done, truncated, _ = env.step(a)
                next_s = self.mdp.discretize_state(next_state)
                next_a = self.choose_action(next_s)
                
                self.Q[s, a] += self.alpha * (
                    reward + self.gamma * self.Q[next_s, next_a] - self.Q[s, a]
                )
                
                s = next_s
                a = next_a
                total_reward += reward
                
                if total_reward > 500:
                    break
            
            if (episode_idx + 1) % 100 == 0:
                V = np.max(self.Q, axis=1)
                self.history['episodes'].append(episode_idx + 1)
                self.history['rewards'].append(total_reward)
                self.history['values'].append(np.mean(V))
                print(f"    回合 {episode_idx + 1}, ε={epsilon:.4f}, 奖励={total_reward}, 平均V={np.mean(V):.4f}")
        
        env.close()
        
        for s in range(self.n_states):
            best_action = np.argmax(self.Q[s])
            self.policy[s] = np.zeros(self.n_actions)
            self.policy[s, best_action] = 1.0
        
        V = np.max(self.Q, axis=1)
        return self.policy, V, self.Q


class QLearning:
    def __init__(self, mdp, gamma=0.99, alpha=0.1, epsilon=0.1):
        self.mdp = mdp
        self.gamma = gamma
        self.alpha = alpha
        self.epsilon = epsilon
        self.n_states = mdp.n_states
        self.n_actions = mdp.n_actions
        self.Q = np.zeros((self.n_states, self.n_actions))
        self.policy = np.ones((self.n_states, self.n_actions)) / self.n_actions
        self.history = {'episodes': [], 'rewards': [], 'values': []}
    
    def choose_action(self, s):
        if np.random.random() < self.epsilon:
            return np.random.randint(0, self.n_actions)
        else:
            return np.argmax(self.Q[s])
    
    def run(self, n_episodes=5000, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.999):
        print("  开始Q-learning算法...")
        
        env = gym.make('CartPole-v1')
        epsilon = epsilon_start
        
        for episode_idx in range(n_episodes):
            epsilon = max(epsilon_end, epsilon * epsilon_decay)
            self.epsilon = epsilon
            
            state, _ = env.reset()
            s = self.mdp.discretize_state(state)
            done = False
            truncated = False
            total_reward = 0
            
            while not (done or truncated):
                a = self.choose_action(s)
                next_state, reward, done, truncated, _ = env.step(a)
                next_s = self.mdp.discretize_state(next_state)
                
                self.Q[s, a] += self.alpha * (
                    reward + self.gamma * np.max(self.Q[next_s]) - self.Q[s, a]
                )
                
                s = next_s
                total_reward += reward
                
                if total_reward > 500:
                    break
            
            if (episode_idx + 1) % 100 == 0:
                V = np.max(self.Q, axis=1)
                self.history['episodes'].append(episode_idx + 1)
                self.history['rewards'].append(total_reward)
                self.history['values'].append(np.mean(V))
                print(f"    回合 {episode_idx + 1}, ε={epsilon:.4f}, 奖励={total_reward}, 平均V={np.mean(V):.4f}")
        
        env.close()
        
        for s in range(self.n_states):
            best_action = np.argmax(self.Q[s])
            self.policy[s] = np.zeros(self.n_actions)
            self.policy[s, best_action] = 1.0
        
        V = np.max(self.Q, axis=1)
        return self.policy, V, self.Q


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


def compare_methods(mdp, n_episodes=5000):
    print("SARSA vs Q-learning 比较")
    
    results = {}
    
    print("\n[1/2] SARSA算法...")
    t0 = time.time()
    sarsa = SARSA(mdp)
    sarsa_policy, sarsa_V, sarsa_Q = sarsa.run(n_episodes=n_episodes)
    sarsa_time = time.time() - t0
    results['SARSA'] = {
        'policy': sarsa_policy, 'V': sarsa_V, 'Q': sarsa_Q,
        'time': sarsa_time, 'history': sarsa.history
    }
    
    print("\n[2/2] Q-learning算法...")
    t0 = time.time()
    qlearning = QLearning(mdp)
    q_policy, q_V, q_Q = qlearning.run(n_episodes=n_episodes)
    q_time = time.time() - t0
    results['Q-learning'] = {
        'policy': q_policy, 'V': q_V, 'Q': q_Q,
        'time': q_time, 'history': qlearning.history
    }
    
    print("两种方法性能比较")
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


def plot_comparison(results, mdp):
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('SARSA vs Q-learning 比较分析', fontsize=16, fontweight='bold')
    
    colors = {'SARSA': 'blue', 'Q-learning': 'red'}
    labels_cn = {'SARSA': 'SARSA', 'Q-learning': 'Q-learning'}
    
    ax1 = fig.add_subplot(2, 3, 1)
    for name, res in results.items():
        if res['history']['episodes']:
            ax1.plot(res['history']['episodes'], res['history']['values'],
                    color=colors[name], label=labels_cn[name], linewidth=2)
    ax1.set_xlabel('回合数', fontsize=12)
    ax1.set_ylabel('平均状态值', fontsize=12)
    ax1.set_title('学习曲线 - 平均状态值', fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    ax2 = fig.add_subplot(2, 3, 2)
    for name, res in results.items():
        if res['history']['episodes']:
            window = 10
            smoothed = np.convolve(res['history']['rewards'], np.ones(window)/window, mode='valid')
            episodes = res['history']['episodes'][:len(smoothed)]
            ax2.plot(episodes, smoothed,
                    color=colors[name], label=labels_cn[name], linewidth=2)
    ax2.set_xlabel('回合数', fontsize=12)
    ax2.set_ylabel('平均奖励', fontsize=12)
    ax2.set_title('学习曲线 - 奖励（平滑后）', fontsize=13)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    ax3 = fig.add_subplot(2, 3, 3)
    method_names = list(results.keys())
    eval_rewards = [results[name]['eval_reward'][0] for name in method_names]
    eval_stds = [results[name]['eval_reward'][1] for name in method_names]
    x_pos = np.arange(len(method_names))
    bars = ax3.bar(x_pos, eval_rewards, yerr=eval_stds,
                   color=[colors[n] for n in method_names], alpha=0.7, capsize=5)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels([labels_cn[n] for n in method_names], fontsize=11)
    ax3.set_ylabel('平均回合奖励', fontsize=12)
    ax3.set_title('真实环境评估结果', fontsize=13)
    ax3.grid(True, alpha=0.3, axis='y')
    
    ax4 = fig.add_subplot(2, 3, 4)
    for name, res in results.items():
        V = res['V']
        ax4.hist(V, bins=50, alpha=0.5, label=labels_cn[name], color=colors[name])
    ax4.set_xlabel('状态值', fontsize=12)
    ax4.set_ylabel('状态数量', fontsize=12)
    ax4.set_title('状态值分布', fontsize=13)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    nb = mdp.n_bins
    method_list = list(results.keys())
    for idx, name in enumerate(method_list):
        ax = fig.add_subplot(2, 3, 5 + idx)
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
    save_path = 'sarsa_vs_qlearning.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n比较图已保存至: {save_path}")

def main():
    print("SARSA和Q-learning求解小车倒立摆问题")

    mdp = CartPoleDiscreteMDP(n_bins=8)
    
    print(f"\n【MDP环境设置】")
    print(f"  离散化bin数: {mdp.n_bins}")
    print(f"  总状态数: {mdp.n_states}")
    print(f"  动作数: {mdp.n_actions}")
    print(f"  折扣因子γ: {mdp.gamma}")
    
    results = compare_methods(mdp, n_episodes=3000)
    
    plot_comparison(results, mdp)

if __name__ == "__main__":
    main()
