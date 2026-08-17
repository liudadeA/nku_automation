import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
import gymnasium as gym
from collections import deque
import matplotlib.pyplot as plt


class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super(ActorCritic, self).__init__()
        
        self.actor = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, state):
        action_probs = self.actor(state)
        state_value = self.critic(state)
        return action_probs, state_value
    
    def act(self, state):
        action_probs, _ = self.forward(state)
        dist = Categorical(action_probs)
        action = dist.sample()
        action_logprob = dist.log_prob(action)
        return action.item(), action_logprob
    
    def evaluate(self, states, actions):
        action_probs, state_values = self.forward(states)
        dist = Categorical(action_probs)
        action_logprobs = dist.log_prob(actions)
        dist_entropy = dist.entropy()
        return action_logprobs, state_values, dist_entropy


class PPO:
    def __init__(self, state_dim, action_dim, lr=2.5e-4, gamma=0.99, 
                 K_epochs=10, eps_clip=0.2, gae_lambda=0.95):
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs
        self.gae_lambda = gae_lambda
        
        self.policy = ActorCritic(state_dim, action_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr, eps=1e-5)
        
        self.policy_old = ActorCritic(state_dim, action_dim)
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        self.MseLoss = nn.MSELoss()
    
    def select_action(self, state):
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0)
            action, action_logprob = self.policy_old.act(state)
        return action, action_logprob
    
    def compute_gae(self, rewards, values, dones, next_value):
        advantages = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_val = next_value
            else:
                next_val = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_val * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages.insert(0, gae)
        
        return advantages
    
    def update(self, memory):
        states = torch.FloatTensor(np.array(memory['states']))
        actions = torch.LongTensor(memory['actions'])
        old_logprobs = torch.FloatTensor(memory['logprobs'])
        rewards = memory['rewards']
        dones = memory['dones']
        
        with torch.no_grad():
            _, state_values = self.policy(states)
            state_values = state_values.squeeze()
        
        _, next_value = self.policy(torch.FloatTensor(memory['last_state']).unsqueeze(0))
        next_value = next_value.item()
        
        advantages = self.compute_gae(rewards, state_values.tolist(), dones, next_value)
        advantages = torch.FloatTensor(advantages)
        returns = advantages + state_values
        
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        for _ in range(self.K_epochs):
            logprobs, state_values, dist_entropy = self.policy.evaluate(states, actions)
            state_values = state_values.squeeze()
            
            ratios = torch.exp(logprobs - old_logprobs)
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            
            loss = -torch.min(surr1, surr2) + 0.5 * self.MseLoss(state_values, returns) - 0.02 * dist_entropy
            
            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()
        
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        return loss.mean().item()


def train_ppo(env_name='CartPole-v1', max_episodes=2000, max_timesteps=500, 
              update_timestep=2048, print_freq=20):
    env = gym.make(env_name)
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n
    
    ppo = PPO(state_dim, action_dim)
    
    memory = {
        'states': [],
        'actions': [],
        'logprobs': [],
        'rewards': [],
        'dones': [],
        'last_state': None
    }
    
    timestep = 0
    scores = []
    scores_window = deque(maxlen=100)
    losses = []
    
    for i_episode in range(1, max_episodes + 1):
        state, _ = env.reset()
        score = 0
        
        for t in range(max_timesteps):
            timestep += 1
            
            action, action_logprob = ppo.select_action(state)
            next_state, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            
            memory['states'].append(state)
            memory['actions'].append(action)
            memory['logprobs'].append(action_logprob.item())
            memory['rewards'].append(reward)
            memory['dones'].append(done)
            
            state = next_state
            score += reward
            
            if timestep % update_timestep == 0:
                memory['last_state'] = state
                loss = ppo.update(memory)
                losses.append(loss)
                
                memory = {
                    'states': [],
                    'actions': [],
                    'logprobs': [],
                    'rewards': [],
                    'dones': [],
                    'last_state': None
                }
            
            if done:
                break
        
        scores.append(score)
        scores_window.append(score)
        
        if i_episode % print_freq == 0:
            avg_score = np.mean(scores_window)
            print(f'Episode {i_episode}\tAverage Score: {avg_score:.2f}')
        
        if np.mean(scores_window) >= 495.0:
            print(f'\nEnvironment solved in {i_episode-100} episodes!\tAverage Score: {np.mean(scores_window):.2f}')
            break
    
    env.close()
    
    return scores, losses, ppo


def plot_results(scores, losses):
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    
    ax1.plot(scores, label='Score per Episode', alpha=0.6)
    ax1.set_xlabel('Episode', fontsize=12)
    ax1.set_ylabel('Score', fontsize=12)
    ax1.set_title('PPO Training Scores on CartPole', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    moving_avg = []
    for i in range(len(scores)):
        if i < 100:
            moving_avg.append(np.mean(scores[:i+1]))
        else:
            moving_avg.append(np.mean(scores[i-99:i+1]))
    ax1.plot(moving_avg, color='red', linewidth=2, label='Moving Average (100 episodes)')
    ax1.legend(fontsize=10)
    ax1.axhline(y=495, color='green', linestyle='--', label='Solved Threshold (495)')
    
    plt.tight_layout()
    plt.savefig('training_scores.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    if losses:
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot(losses, color='orange', alpha=0.7)
        ax2.set_xlabel('Update Step', fontsize=12)
        ax2.set_ylabel('Loss', fontsize=12)
        ax2.set_title('PPO Training Loss on CartPole', fontsize=14)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('training_loss.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    fig_combined, (ax1_combined, ax2_combined) = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1_combined.plot(scores, alpha=0.6)
    ax1_combined.set_xlabel('Episode')
    ax1_combined.set_ylabel('Score')
    ax1_combined.set_title('Training Scores')
    ax1_combined.grid(True, alpha=0.3)
    ax1_combined.plot(moving_avg, color='red', linewidth=2, label='Moving Average (100)')
    ax1_combined.legend()
    
    if losses:
        ax2_combined.plot(losses, color='orange', alpha=0.7)
        ax2_combined.set_xlabel('Update Step')
        ax2_combined.set_ylabel('Loss')
        ax2_combined.set_title('Training Loss')
        ax2_combined.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ppo_cartpole_results.png', dpi=150, bbox_inches='tight')
    plt.close()


def test_agent(ppo, env_name='CartPole-v1', num_episodes=10):
    env = gym.make(env_name, render_mode='human')
    
    for episode in range(num_episodes):
        state, _ = env.reset()
        score = 0
        done = False
        
        while not done:
            action, _ = ppo.select_action(state)
            state, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            score += reward
        
        print(f'Test Episode {episode + 1}: Score = {score}')
    
    env.close()


if __name__ == '__main__':
    print("开始训练PPO算法解决CartPole问题...")
    print("=" * 50)
    
    scores, losses, ppo = train_ppo(
        env_name='CartPole-v1',
        max_episodes=2000,
        max_timesteps=500,
        update_timestep=2048,
        print_freq=20
    )
    
    print("\n训练完成！")
    print(f"最高得分: {max(scores)}")
    print(f"最后100轮平均得分: {np.mean(scores[-100:]):.2f}")
    
    plot_results(scores, losses)
    
    torch.save(ppo.policy.state_dict(), 'ppo_cartpole_model.pth')
    print("\n模型已保存到 ppo_cartpole_model.pth")
