import argparse
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    import gymnasium as gym
except ImportError:  # pragma: no cover
    import gym


@dataclass
class TrainConfig:
    env_name: str = "CartPole-v1"
    gamma: float = 0.99
    policy_learning_rate: float = 1e-3
    value_learning_rate: float = 3e-3
    hidden_dim: int = 128
    num_episodes: int = 1500
    max_steps: int = 500
    seed: int = 42
    render: bool = False
    batch_episodes: int = 8
    entropy_coef: float = 1e-3
    grad_clip: float = 1.0


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class PolicyNetwork(nn.Module):
    def __init__(self, state_dim: int, hidden_dim: int, action_dim: int) -> None:
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.model(state)


class ValueNetwork(nn.Module):
    def __init__(self, state_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.model(state).squeeze(-1)


def compute_returns(rewards: list[float], gamma: float) -> torch.Tensor:
    returns = []
    discounted_sum = 0.0
    for reward in reversed(rewards):
        discounted_sum = reward + gamma * discounted_sum
        returns.insert(0, discounted_sum)

    return torch.tensor(returns, dtype=torch.float32)


def reset_env(env: gym.Env, seed: int | None = None) -> np.ndarray:
    reset_result = env.reset(seed=seed)
    if isinstance(reset_result, tuple):
        state, _ = reset_result
    else:
        state = reset_result
    return np.asarray(state, dtype=np.float32)


def step_env(env: gym.Env, action: int) -> tuple[np.ndarray, float, bool]:
    step_result = env.step(action)
    if len(step_result) == 5:
        next_state, reward, terminated, truncated, _ = step_result
        done = terminated or truncated
    else:
        next_state, reward, done, _ = step_result
    return np.asarray(next_state, dtype=np.float32), float(reward), bool(done)


def train(config: TrainConfig) -> tuple[PolicyNetwork, dict]:
    set_seed(config.seed)
    env = gym.make(
        config.env_name,
        render_mode="human" if config.render else None,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n
    policy = PolicyNetwork(state_dim, config.hidden_dim, action_dim).to(device)
    value_net = ValueNetwork(state_dim, config.hidden_dim).to(device)
    policy_optimizer = optim.Adam(
        policy.parameters(), lr=config.policy_learning_rate
    )
    value_optimizer = optim.Adam(
        value_net.parameters(), lr=config.value_learning_rate
    )

    episode_rewards = []
    moving_avgs = []
    policy_losses = []
    value_losses = []
    batch_log_probs = []
    batch_entropies = []
    batch_values = []
    batch_returns = []

    def update_parameters() -> tuple[float, float] | None:
        if not batch_log_probs:
            return None

        returns_tensor = torch.cat(batch_returns).to(device)
        log_probs_tensor = torch.cat(batch_log_probs)
        entropies_tensor = torch.cat(batch_entropies)
        values_tensor = torch.cat(batch_values)

        advantages = returns_tensor - values_tensor.detach()
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        policy_loss = -(log_probs_tensor * advantages).mean()
        policy_loss -= config.entropy_coef * entropies_tensor.mean()
        value_loss = nn.functional.mse_loss(values_tensor, returns_tensor)

        policy_optimizer.zero_grad()
        value_optimizer.zero_grad()
        (policy_loss + value_loss).backward()
        nn.utils.clip_grad_norm_(policy.parameters(), config.grad_clip)
        nn.utils.clip_grad_norm_(value_net.parameters(), config.grad_clip)
        policy_optimizer.step()
        value_optimizer.step()

        batch_log_probs.clear()
        batch_entropies.clear()
        batch_values.clear()
        batch_returns.clear()
        return float(policy_loss.item()), float(value_loss.item())

    for episode in range(1, config.num_episodes + 1):
        state = reset_env(env, seed=config.seed + episode)
        log_probs = []
        entropies = []
        values = []
        rewards = []
        total_reward = 0.0
        last_losses = None

        for _ in range(config.max_steps):
            state_tensor = torch.as_tensor(
                state, dtype=torch.float32, device=device
            ).unsqueeze(0)
            logits = policy(state_tensor)
            dist = torch.distributions.Categorical(logits=logits)
            action = dist.sample()
            value = value_net(state_tensor)

            next_state, reward, done = step_env(env, action.item())
            log_probs.append(dist.log_prob(action).view(-1))
            entropies.append(dist.entropy().view(-1))
            values.append(value)
            rewards.append(reward)
            total_reward += reward
            state = next_state

            if done:
                break

        returns = compute_returns(rewards, config.gamma)
        batch_log_probs.extend(log_probs)
        batch_entropies.extend(entropies)
        batch_values.extend(values)
        batch_returns.append(returns)

        if (
            episode % config.batch_episodes == 0
            or episode == config.num_episodes
        ):
            last_losses = update_parameters()
            if last_losses is not None:
                policy_losses.append(last_losses[0])
                value_losses.append(last_losses[1])

        episode_rewards.append(total_reward)
        moving_avg = np.mean(episode_rewards[-50:])
        moving_avgs.append(moving_avg)

        if episode % 20 == 0 or episode == 1:
            loss_info = ""
            if last_losses is not None:
                policy_loss, value_loss = last_losses
                loss_info = (
                    f" | Policy Loss: {policy_loss:7.4f}"
                    f" | Value Loss: {value_loss:7.4f}"
                )
            print(
                f"Episode {episode:4d} | Reward: {total_reward:6.1f} | "
                f"Moving Avg(50): {moving_avg:6.2f}{loss_info}"
            )

        if moving_avg >= 475.0 and episode >= 50:
            if episode % config.batch_episodes != 0:
                update_parameters()
            print(f"环境已基本学会，训练在第 {episode} 回合提前结束。")
            break

    env.close()
    
    training_data = {
        "config": asdict(config),
        "episode_rewards": episode_rewards,
        "moving_avgs": moving_avgs,
        "policy_losses": policy_losses,
        "value_losses": value_losses,
    }
    
    return policy, training_data


def evaluate(
    policy: PolicyNetwork,
    env_name: str,
    episodes: int = 5,
    max_steps: int = 500,
    seed: int = 2024,
) -> list[float]:
    env = gym.make(env_name, render_mode=None)
    device = next(policy.parameters()).device
    rewards = []

    for episode in range(episodes):
        state = reset_env(env, seed=seed + episode)
        total_reward = 0.0

        for _ in range(max_steps):
            with torch.no_grad():
                state_tensor = torch.as_tensor(
                    state, dtype=torch.float32, device=device
                ).unsqueeze(0)
                logits = policy(state_tensor)
                action = torch.argmax(logits, dim=-1).item()

            state, reward, done = step_env(env, action)
            total_reward += reward

            if done:
                break

        rewards.append(total_reward)
        print(f"Eval Episode {episode + 1}: reward = {total_reward:.1f}")

    print(f"平均评估回报: {np.mean(rewards):.2f}")
    env.close()
    return rewards


def save_training_data(data: dict, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"训练数据已保存到: {filepath}")


def plot_training_results(data: dict, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    episode_rewards = data["episode_rewards"]
    moving_avgs = data["moving_avgs"]
    policy_losses = data["policy_losses"]
    value_losses = data["value_losses"]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    ax1 = axes[0]
    episodes = range(1, len(episode_rewards) + 1)
    ax1.plot(episodes, episode_rewards, alpha=0.6, linewidth=0.8, label="Episode Reward")
    ax1.plot(episodes, moving_avgs, linewidth=2, color="red", label="Moving Avg (50)")
    ax1.set_xlabel("Training Episode", fontsize=12)
    ax1.set_ylabel("Reward", fontsize=12)
    ax1.set_title("Training Reward Curve", fontsize=14, fontweight="bold")
    ax1.legend(loc="lower right")
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[1]
    if policy_losses and value_losses:
        update_steps = range(1, len(policy_losses) + 1)
        ax2.plot(update_steps, policy_losses, linewidth=1.5, label="Policy Loss")
        ax2.plot(update_steps, value_losses, linewidth=1.5, label="Value Loss")
        ax2.set_xlabel("Parameter Update Steps", fontsize=12)
        ax2.set_ylabel("Loss Value", fontsize=12)
        ax2.set_title("Training Loss Curve", fontsize=14, fontweight="bold")
        ax2.legend(loc="upper right")
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    reward_path = output_path / "training_results.png"
    plt.savefig(reward_path, dpi=300, bbox_inches="tight")
    print(f"训练结果图已保存到: {reward_path}")
    plt.close()
    
    fig2, ax = plt.subplots(figsize=(8, 5))
    episodes = range(1, len(episode_rewards) + 1)
    ax.plot(episodes, episode_rewards, alpha=0.6, linewidth=0.8, label="Episode Reward")
    ax.plot(episodes, moving_avgs, linewidth=2, color="red", label="Moving Avg (50)")
    ax.set_xlabel("Training Episode", fontsize=12)
    ax.set_ylabel("Reward", fontsize=12)
    ax.set_title("Training Reward Curve", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    
    reward_only_path = output_path / "reward_curve.png"
    fig2.savefig(reward_only_path, dpi=300, bbox_inches="tight")
    print(f"奖励曲线图已保存到: {reward_only_path}")
    plt.close()
    
    if policy_losses and value_losses:
        fig3, ax = plt.subplots(figsize=(8, 5))
        update_steps = range(1, len(policy_losses) + 1)
        ax.plot(update_steps, policy_losses, linewidth=1.5, label="Policy Loss")
        ax.plot(update_steps, value_losses, linewidth=1.5, label="Value Loss")
        ax.set_xlabel("Parameter Update Steps", fontsize=12)
        ax.set_ylabel("Loss Value", fontsize=12)
        ax.set_title("Training Loss Curve", fontsize=14, fontweight="bold")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)
        
        loss_path = output_path / "loss_curve.png"
        fig3.savefig(loss_path, dpi=300, bbox_inches="tight")
        print(f"损失曲线图已保存到: {loss_path}")
        plt.close()


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="使用 REINFORCE 训练 CartPole")
    parser.add_argument("--episodes", type=int, default=1500, help="训练回合数")
    parser.add_argument(
        "--policy-lr", type=float, default=1e-3, help="策略网络学习率"
    )
    parser.add_argument(
        "--value-lr", type=float, default=3e-3, help="价值网络学习率"
    )
    parser.add_argument("--gamma", type=float, default=0.99, help="折扣因子")
    parser.add_argument("--hidden-dim", type=int, default=128, help="隐藏层维度")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--batch-episodes", type=int, default=8, help="每次更新包含的回合数")
    parser.add_argument("--entropy-coef", type=float, default=1e-3, help="熵正则系数")
    parser.add_argument("--render", action="store_true", help="训练时可视化环境")
    args = parser.parse_args()

    return TrainConfig(
        policy_learning_rate=args.policy_lr,
        value_learning_rate=args.value_lr,
        gamma=args.gamma,
        hidden_dim=args.hidden_dim,
        num_episodes=args.episodes,
        seed=args.seed,
        batch_episodes=args.batch_episodes,
        entropy_coef=args.entropy_coef,
        render=args.render,
    )


def main() -> None:
    config = parse_args()
    policy, training_data = train(config)
    
    output_dir = "output"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    save_training_data(training_data, f"{output_dir}/training_data.json")
    plot_training_results(training_data, output_dir)
    
    eval_rewards = evaluate(policy, config.env_name, seed=config.seed + 10000)
    
    training_data["eval_rewards"] = eval_rewards
    save_training_data(training_data, f"{output_dir}/training_data.json")
    
    print("\n" + "="*50)
    print("训练完成！")
    print(f"总训练回合数: {len(training_data['episode_rewards'])}")
    print(f"最终移动平均奖励: {training_data['moving_avgs'][-1]:.2f}")
    print(f"评估平均奖励: {np.mean(eval_rewards):.2f}")
    print("="*50)


if __name__ == "__main__":
    main()
