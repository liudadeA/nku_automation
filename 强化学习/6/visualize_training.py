import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd

log_dir = Path("E:/study/强化学习/6/runs/pong_dqn")

eval_data = np.load(log_dir / "eval" / "evaluations.npz")
print("Keys in evaluations.npz:", eval_data.files)

timesteps = eval_data["timesteps"]
mean_rewards = eval_data["results"].mean(axis=1)
std_rewards = eval_data["results"].std(axis=1)
mean_ep_lengths = eval_data["ep_lengths"].mean(axis=1)

monitor_files = list((log_dir / "monitor").glob("*.monitor.csv"))
all_episodes = []
for f in monitor_files:
    df = pd.read_csv(f, skiprows=1)
    all_episodes.append(df)
episodes_df = pd.concat(all_episodes, ignore_index=True)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax1 = axes[0, 0]
ax1.plot(timesteps, mean_rewards, 'b-', linewidth=2, label='Mean Reward')
ax1.fill_between(timesteps, 
                  mean_rewards - std_rewards, 
                  mean_rewards + std_rewards, 
                  alpha=0.3, color='blue')
ax1.set_xlabel('Timesteps')
ax1.set_ylabel('Reward')
ax1.set_title('Evaluation Reward over Training')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2 = axes[0, 1]
ax2.plot(timesteps, mean_ep_lengths, 'g-', linewidth=2)
ax2.set_xlabel('Timesteps')
ax2.set_ylabel('Episode Length')
ax2.set_title('Evaluation Episode Length over Training')
ax2.grid(True, alpha=0.3)

ax3 = axes[1, 0]
if 'r' in episodes_df.columns:
    rewards = episodes_df['r'].values
    window = min(100, len(rewards) // 10) if len(rewards) > 10 else 1
    if window > 1:
        moving_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')
        ax3.plot(rewards, alpha=0.3, color='blue', label='Raw')
        ax3.plot(range(window-1, len(rewards)), moving_avg, 'b-', linewidth=2, label=f'Moving Avg ({window})')
    else:
        ax3.plot(rewards, 'b-', linewidth=2)
    ax3.set_xlabel('Episode')
    ax3.set_ylabel('Reward')
    ax3.set_title('Training Reward per Episode')
    ax3.legend()
ax3.grid(True, alpha=0.3)

ax4 = axes[1, 1]
if 'l' in episodes_df.columns:
    lengths = episodes_df['l'].values
    window = min(100, len(lengths) // 10) if len(lengths) > 10 else 1
    if window > 1:
        moving_avg = np.convolve(lengths, np.ones(window)/window, mode='valid')
        ax4.plot(lengths, alpha=0.3, color='green', label='Raw')
        ax4.plot(range(window-1, len(lengths)), moving_avg, 'g-', linewidth=2, label=f'Moving Avg ({window})')
    else:
        ax4.plot(lengths, 'g-', linewidth=2)
    ax4.set_xlabel('Episode')
    ax4.set_ylabel('Length')
    ax4.set_title('Training Episode Length')
    ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(log_dir / "training_visualization.png", dpi=150)
plt.show()

print(f"\nVisualization saved to: {log_dir / 'training_visualization.png'}")
print(f"\nFinal Evaluation Results:")
print(f"  Mean Reward: {mean_rewards[-1]:.2f} +/- {std_rewards[-1]:.2f}")
print(f"  Mean Episode Length: {mean_ep_lengths[-1]:.0f}")
print(f"  Total Timesteps: {timesteps[-1]}")
