import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# ==================== 经验回放池 ====================
class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states, dtype=np.float32),
                np.array(actions, dtype=np.int64),
                np.array(rewards, dtype=np.float32),
                np.array(next_states, dtype=np.float32),
                np.array(dones, dtype=np.float32))

    def __len__(self):
        return len(self.buffer)


# ==================== Actor 网络 ====================
class Actor(nn.Module):
    def __init__(self, state_dim, n_actions):
        super(Actor, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, n_actions)
        )
        self.n_actions = n_actions

    def forward(self, x, temperature=1.0, hard=False):
        logits = self.net(x)
        # Gumbel-Softmax：可导的离散化近似
        if self.training:
            y = F.gumbel_softmax(logits, tau=temperature, hard=hard)
        else:
            y = F.one_hot(logits.argmax(dim=1), self.n_actions).float()
        return y


# ==================== Critic 网络 ====================
class Critic(nn.Module):
    def __init__(self, state_dim, n_actions):
        super(Critic, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim + n_actions, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )

    def forward(self, x, a):
        return self.net(torch.cat([x, a], dim=1))


# ==================== DDPG 智能体 ====================
class DDPGAgent:
    def __init__(self, state_dim, n_actions, lr_actor=1e-3, lr_critic=1e-3,
                 gamma=0.99, tau=0.005, buffer_capacity=100000,
                 epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=5000):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.n_actions = n_actions
        self.state_dim = state_dim

        self.actor = Actor(state_dim, n_actions).to(self.device)
        self.actor_target = Actor(state_dim, n_actions).to(self.device)
        self.critic = Critic(state_dim, n_actions).to(self.device)
        self.critic_target = Critic(state_dim, n_actions).to(self.device)

        self.actor_target.load_state_dict(self.actor.state_dict())
        self.critic_target.load_state_dict(self.critic.state_dict())

        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr_actor)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr_critic, weight_decay=1e-4)

        self.replay_buffer = ReplayBuffer(buffer_capacity)

        self.gamma = gamma
        self.tau = tau
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.total_steps = 0

    def _soft_update(self, target, source):
        for tp, p in zip(target.parameters(), source.parameters()):
            tp.data.copy_(self.tau * p.data + (1 - self.tau) * tp.data)

    def select_action(self, state, training=True):
        if training and random.random() < self.epsilon:
            return random.randint(0, self.n_actions - 1)
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.actor.eval()
        with torch.no_grad():
            action_onehot = self.actor(state_t)
        self.actor.train()
        return action_onehot.argmax(dim=1).item()

    def update(self, batch_size):
        if len(self.replay_buffer) < batch_size:
            return

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(batch_size)

        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).unsqueeze(1).to(self.device)

        actions_onehot = F.one_hot(actions, self.n_actions).float()

        # ---- 更新 Critic ----
        with torch.no_grad():
            self.actor_target.eval()
            next_act_onehot = self.actor_target(next_states, temperature=1.0, hard=True)
            target_q = rewards + (1 - dones) * self.gamma * self.critic_target(next_states, next_act_onehot)
            self.actor_target.train()

        current_q = self.critic(states, actions_onehot)
        critic_loss = F.mse_loss(current_q, target_q)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 1.0)
        self.critic_optimizer.step()

        # Gumbel-Softmax 产生可导的 one-hot，梯度可以流过
        act_soft = self.actor(states, temperature=1.0, hard=True)
        actor_q = self.critic(states, act_soft)
        actor_loss = -actor_q.mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), 1.0)
        self.actor_optimizer.step()

        # ---- 软更新 ----
        self._soft_update(self.actor_target, self.actor)
        self._soft_update(self.critic_target, self.critic)

        # ---- 衰减 epsilon ----
        self.total_steps += 1
        self.epsilon = self.epsilon_end + (1.0 - self.epsilon_end) * \
                       np.exp(-self.total_steps / self.epsilon_decay)


# ==================== 绘制训练曲线 ====================
def plot_rewards(reward_history):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(reward_history, label="Episode Reward", alpha=0.6)
    if len(reward_history) >= 10:
        moving_avg = np.convolve(reward_history, np.ones(10) / 10, mode='valid')
        ax.plot(range(9, len(reward_history)), moving_avg,
                color='red', linewidth=2, label="10-Episode Moving Avg")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Reward")
    ax.set_title("DDPG Training on CartPole-v1")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig("ddpg_training_curve.png", dpi=150, bbox_inches='tight')
    print("训练曲线已保存为 ddpg_training_curve.png")


# ==================== 训练主循环 ====================
def train():
    env = gym.make("CartPole-v1")
    state_dim = env.observation_space.shape[0]   # 4
    n_actions = env.action_space.n                # 2

    agent = DDPGAgent(state_dim, n_actions)

    num_episodes = 500
    batch_size = 64

    reward_history = []

    for episode in range(num_episodes):
        state, _ = env.reset()
        episode_reward = 0

        while True:
            action = agent.select_action(state)
            next_state, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated

            agent.replay_buffer.push(state, action, reward, next_state, float(done))
            agent.update(batch_size)

            state = next_state
            episode_reward += reward

            if done:
                break

        reward_history.append(episode_reward)

        if (episode + 1) % 10 == 0:
            avg10 = np.mean(reward_history[-10:])
            print(f"Episode {episode + 1:3d} | Reward: {episode_reward:.0f} | Avg(10): {avg10:.1f} | Eps: {agent.epsilon:.3f}")

        if len(reward_history) >= 10 and np.mean(reward_history[-10:]) >= 495:
            print(f"在 Episode {episode + 1} 达到目标")
            break

    plot_rewards(reward_history)

    torch.save(agent.actor.state_dict(), "ddpg_actor.pth")
    torch.save(agent.critic.state_dict(), "ddpg_critic.pth")
    print("模型已保存")

    test(agent, env)


def test(agent, env, num_episodes=10):
    print("\n===== 测试训练结果 =====")
    for ep in range(num_episodes):
        state, _ = env.reset()
        total_reward = 0
        while True:
            action = agent.select_action(state, training=False)
            next_state, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward
            state = next_state
            if terminated or truncated:
                break
        print(f"测试 Episode {ep + 1} | Reward: {total_reward:.0f}")


if __name__ == "__main__":
    train()
