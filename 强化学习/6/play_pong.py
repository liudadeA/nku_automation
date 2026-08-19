import numpy as np
import ale_py
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.atari_wrappers import AtariWrapper
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack, VecTransposeImage

gym.register_envs(ale_py)

model_path = "E:/study/强化学习/6/checkpoints/pong_dqn/best_model/best_model.zip"
print(f"Loading model from: {model_path}")

env = gym.make("ALE/Pong-v5", render_mode="human", frameskip=1, repeat_action_probability=0.0)
env = AtariWrapper(env, noop_max=30, frame_skip=4, screen_size=84, terminal_on_life_loss=True, clip_reward=True)
env = DummyVecEnv([lambda: env])
env = VecFrameStack(env, n_stack=4, channels_order="last")
env = VecTransposeImage(env)

model = DQN.load(model_path, env=env)

print("Starting evaluation... Close the game window to stop.")
print("Press Ctrl+C in terminal to exit.\n")

total_reward = 0
episode_rewards = []
num_episodes = 5

for episode in range(num_episodes):
    obs = env.reset()
    episode_reward = 0
    done = False
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        episode_reward += reward
    
    episode_rewards.append(episode_reward)
    total_reward += episode_reward
    print(f"Episode {episode + 1}: Reward = {episode_reward:.2f}")

env.close()

print(f"\n{'='*40}")
print(f"Evaluation Results ({num_episodes} episodes):")
print(f"  Mean Reward: {np.mean(episode_rewards):.2f}")
print(f"  Std Reward: {np.std(episode_rewards):.2f}")
print(f"  Min Reward: {np.min(episode_rewards):.2f}")
print(f"  Max Reward: {np.max(episode_rewards):.2f}")
print(f"{'='*40}")
