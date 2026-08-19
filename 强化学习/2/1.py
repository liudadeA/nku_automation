import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

#Gym库游戏 - CartPole-v1
def task1_cartpole():

    try:
        import gymnasium as gym
    except ImportError:
        import gym
    
    env = gym.make('CartPole-v1', render_mode=None)
   
    print("\n【运行演示】")
    observation, info = env.reset()
    total_reward = 0
    
    for step in range(100):
        action = env.action_space.sample()
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        if step < 5:
            print(f"  步骤{step+1}: 状态={[f'{x:.3f}' for x in observation]}, 动作={action}, 奖励={reward}")
        
        if terminated or truncated:
            print(f"  游戏结束，总步数: {step+1}, 总奖励: {total_reward}")
            break
    
    env.close()
    return total_reward



# 任务2：4臂赌博机

class FourArmedBandit:
    
    ##臂赌博机环境
    #每个摇臂有不同的期望奖励
    
    def __init__(self):
        self.n_arms = 4
        self.true_means = [1.0, 2.0, 1.5, 3.0]
        self.std = 1.0
        self.best_arm = np.argmax(self.true_means)
    
    def pull(self, arm):
        #拉动指定摇臂，返回奖励
        return np.random.normal(self.true_means[arm], self.std)
    
    def get_optimal_reward(self):
        #返回最优摇臂的期望奖励
        return self.true_means[self.best_arm]


class EpsilonGreedyAgent:
    #贪婪策略
    def __init__(self, n_arms, epsilon=0.1):
        self.n_arms = n_arms
        self.epsilon = epsilon
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
    
    def select_action(self):
        if np.random.random() < self.epsilon:
            return np.random.randint(self.n_arms)
        else:
            max_value = np.max(self.values)
            candidates = np.where(self.values == max_value)[0]
            return np.random.choice(candidates)
    
    def update(self, arm, reward):
        self.counts[arm] += 1
        self.values[arm] += (reward - self.values[arm]) / self.counts[arm]


class BoltzmannAgent:
    #玻尔兹曼策略
    def __init__(self, n_arms, temperature=1.0):
        self.n_arms = n_arms
        self.temperature = temperature
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
    
    def select_action(self):
        if self.temperature == 0:
            return np.argmax(self.values)
        
        exp_values = np.exp(self.values / self.temperature)
        probs = exp_values / np.sum(exp_values)
        return np.random.choice(self.n_arms, p=probs)
    
    def update(self, arm, reward):
        self.counts[arm] += 1
        self.values[arm] += (reward - self.values[arm]) / self.counts[arm]


class UCBAgent:
    #UCB策略
    def __init__(self, n_arms, c=2.0):
        self.n_arms = n_arms
        self.c = c
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
        self.total_count = 0
    
    def select_action(self):
        if self.total_count < self.n_arms:
            return self.total_count
        
        ucb_values = np.zeros(self.n_arms)
        for arm in range(self.n_arms):
            if self.counts[arm] == 0:
                ucb_values[arm] = float('inf')
            else:
                bonus = self.c * np.sqrt(np.log(self.total_count) / self.counts[arm])
                ucb_values[arm] = self.values[arm] + bonus
        
        return np.argmax(ucb_values)
    
    def update(self, arm, reward):
        self.counts[arm] += 1
        self.total_count += 1
        self.values[arm] += (reward - self.values[arm]) / self.counts[arm]


class ThompsonSamplingAgent:
    #汤普森采样策略
    # 新增策略
    def __init__(self, n_arms):
        self.n_arms = n_arms
        self.alpha = np.ones(n_arms)
        self.beta = np.ones(n_arms)
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
    
    def select_action(self):
        samples = np.random.beta(self.alpha, self.beta)
        return np.argmax(samples)
    
    def update(self, arm, reward):
        self.counts[arm] += 1
        self.values[arm] += (reward - self.values[arm]) / self.counts[arm]
        
        normalized_reward = (reward + 3) / 6
        normalized_reward = np.clip(normalized_reward, 0, 1)
        
        self.alpha[arm] += normalized_reward
        self.beta[arm] += (1 - normalized_reward)


def run_experiment(agent_class, agent_params, bandit, n_steps=1000, n_runs=100):
    #运行实验
    all_rewards = np.zeros((n_runs, n_steps))
    all_arm_counts = np.zeros((n_runs, bandit.n_arms))
    
    for run in range(n_runs):
        agent = agent_class(**agent_params)
        for step in range(n_steps):
            arm = agent.select_action()
            reward = bandit.pull(arm)
            agent.update(arm, reward)
            all_rewards[run, step] = reward
        
        all_arm_counts[run] = agent.counts
    
    avg_rewards = np.mean(all_rewards, axis=0)
    cumulative_avg_rewards = np.cumsum(avg_rewards) / np.arange(1, n_steps + 1)
    avg_arm_counts = np.mean(all_arm_counts, axis=0)
    
    return cumulative_avg_rewards, avg_arm_counts


def task2_bandit():
    #4臂赌博机实验
   
    print("任务2：4臂赌博机实验")
    print("【4臂赌博机设置】")
    bandit = FourArmedBandit()
    print(f"摇臂数量: {bandit.n_arms}")
    print(f"各摇臂真实期望奖励: {bandit.true_means}")
    print(f"奖励标准差: {bandit.std}")
    print(f"最优摇臂: 摇臂{bandit.best_arm} (期望={bandit.true_means[bandit.best_arm]})")
    
    n_steps = 1000
    n_runs = 100
    
    print(f"\n实验设置: 每轮{n_steps}步, 重复{n_runs}次取平均")
    
    agents_config = {
        '贪婪策略(ε=0.1)': (EpsilonGreedyAgent, {'n_arms': 4, 'epsilon': 0.1}),
        '贪婪策略(ε=0.01)': (EpsilonGreedyAgent, {'n_arms': 4, 'epsilon': 0.01}),
        '玻尔兹曼策略(T=0.5)': (BoltzmannAgent, {'n_arms': 4, 'temperature': 0.5}),
        'UCB策略(c=2)': (UCBAgent, {'n_arms': 4, 'c': 2.0}),
        '汤普森采样': (ThompsonSamplingAgent, {'n_arms': 4}),
    }
    
    results = {}
    for name, (agent_class, params) in agents_config.items():
        print(f"  运行 {name}...")
        cumulative_avg, arm_counts = run_experiment(agent_class, params, bandit, n_steps, n_runs)
        results[name] = {
            'cumulative_avg_rewards': cumulative_avg,
            'arm_counts': arm_counts
        }
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    ax1 = axes[0, 0]
    for name, data in results.items():
        ax1.plot(data['cumulative_avg_rewards'], label=name, linewidth=1.5)
    ax1.axhline(y=bandit.get_optimal_reward(), color='red', linestyle='--', 
                label=f'最优期望奖励 ({bandit.get_optimal_reward()})', linewidth=2)
    ax1.set_xlabel('训练步数', fontsize=12)
    ax1.set_ylabel('平均累积奖励', fontsize=12)
    ax1.set_title('各策略训练次数与平均累积奖励的关系', fontsize=14)
    ax1.legend(loc='lower right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[0, 1]
    arm_names = [f'摇臂{i}\n(μ={bandit.true_means[i]})' for i in range(4)]
    x = np.arange(4)
    width = 0.15
    
    for i, (name, data) in enumerate(results.items()):
        bars = ax2.bar(x + i * width, data['arm_counts'], width, label=name)
    
    ax2.set_xlabel('摇臂', fontsize=12)
    ax2.set_ylabel('平均选中次数', fontsize=12)
    ax2.set_title('各策略下每个摇臂的选中次数', fontsize=14)
    ax2.set_xticks(x + width * 2)
    ax2.set_xticklabels(arm_names)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3, axis='y')
    
    ax3 = axes[1, 0]
    window = 50
    for name, data in results.items():
        cumulative = data['cumulative_avg_rewards']
        ax3.plot(cumulative, label=name, linewidth=1.5, alpha=0.7)
    ax3.axhline(y=bandit.get_optimal_reward(), color='red', linestyle='--', 
                label='最优期望奖励', linewidth=2)
    ax3.set_xlabel('训练步数', fontsize=12)
    ax3.set_ylabel('平均累积奖励', fontsize=12)
    ax3.set_title('收敛过程对比', fontsize=14)
    ax3.legend(loc='lower right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(0, 200)
    
    ax4 = axes[1, 1]
    strategies = list(results.keys())
    final_rewards = [results[s]['cumulative_avg_rewards'][-1] for s in strategies]
    colors = plt.cm.Set3(np.linspace(0, 1, len(strategies)))
    
    bars = ax4.barh(strategies, final_rewards, color=colors)
    ax4.axvline(x=bandit.get_optimal_reward(), color='red', linestyle='--', 
                label=f'最优期望奖励', linewidth=2)
    ax4.set_xlabel('最终平均累积奖励', fontsize=12)
    ax4.set_title('各策略最终性能对比', fontsize=14)
    ax4.legend(loc='lower right', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='x')
    
    for bar, reward in zip(bars, final_rewards):
        ax4.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, 
                f'{reward:.3f}', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('e:/study/强化学习/2/bandit_results.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print("【实验结果总结】")
    print(f"\n各摇臂真实期望: {bandit.true_means}")
    print(f"最优摇臂: 摇臂{bandit.best_arm} (期望={bandit.true_means[bandit.best_arm]})")
    print("\n各策略最终平均累积奖励:")
    for name, data in sorted(results.items(), key=lambda x: x[1]['cumulative_avg_rewards'][-1], reverse=True):
        final_reward = data['cumulative_avg_rewards'][-1]
        print(f"  {name}: {final_reward:.4f}")
    
    print("\n各策略摇臂选中分布:")
    for name, data in results.items():
        counts = data['arm_counts']
        total = sum(counts)
        percentages = [c/total*100 for c in counts]
        print(f"  {name}:")
        for i, (cnt, pct) in enumerate(zip(counts, percentages)):
            print(f"    摇臂{i}: {cnt:.1f}次 ({pct:.1f}%)")
    
    print("\n图表已保存至: bandit_results.png")


if __name__ == "__main__":   
    task1_cartpole()
    task2_bandit()
    
    print("\n所有任务完成！")
