from __future__ import annotations

import argparse
from pathlib import Path

import ale_py
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.atari_wrappers import AtariWrapper
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback, EvalCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecFrameStack, VecTransposeImage

gym.register_envs(ale_py)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use DQN to train an Atari agent from video-frame observations."
    )
    parser.add_argument("--env-id", type=str, default="ALE/Pong-v5")
    parser.add_argument("--total-timesteps", type=int, default=2_000_000)  # [FIX] 原 1M 太少，Atari 通常需 2-10M
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=500_000,  # [FIX] 原 100k -> 500k。样本多样性不足是效果差的首要原因
    )
    parser.add_argument(
        "--learning-starts",
        type=int,
        default=50_000,  # [FIX] 原 20k -> 50k。冷启动样本太少，早期梯度噪声极大
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--train-freq", type=int, default=4)
    parser.add_argument(
        "--target-update-interval",
        type=int,
        default=10_000,  # [FIX] 原 1k -> 10k。目标网络更新过频会导致训练震荡（原论文用 10k）
    )
    parser.add_argument(
        "--exploration-fraction",
        type=float,
        default=0.20,  # [FIX] 原 0.10 -> 0.20。探索期太短容易陷入局部最优
    )
    parser.add_argument("--exploration-final-eps", type=float, default=0.01)
    parser.add_argument(
        "--exploration-initial-eps",
        type=float,
        default=1.0,  # [NEW] 明确设置初始 epsilon，确保足够探索
    )
    parser.add_argument("--frame-stack", type=int, default=4)
    parser.add_argument(
        "--n-envs",
        type=int,
        default=4,  # [NEW] 并行环境：提升数据多样性，同时加速采样
    )
    parser.add_argument(
        "--max-grad-norm",
        type=float,
        default=10.0,  # [NEW] 梯度裁剪：防止梯度爆炸，稳定训练
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("runs") / "pong_dqn",
    )
    parser.add_argument("--tensorboard-log-dir", type=Path, default=None)
    parser.add_argument(
        "--save-dir",
        type=Path,
        default=Path("checkpoints") / "pong_dqn",
    )
    parser.add_argument("--eval-freq", type=int, default=50_000)
    parser.add_argument("--eval-episodes", type=int, default=10)  # [FIX] 5 -> 10，减小评估方差
    parser.add_argument("--checkpoint-freq", type=int, default=100_000)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to a saved model to resume training from.",
    )
    return parser.parse_args()


def make_atari_env(
    env_id: str,
    seed: int,
    n_envs: int = 1,
    monitor_dir: Path | None = None,
):
    env = make_vec_env(
        env_id=env_id,
        n_envs=n_envs,
        seed=seed,
        monitor_dir=str(monitor_dir) if monitor_dir else None,
        env_kwargs={
            "frameskip": 1,
            "repeat_action_probability": 0.0,
            "full_action_space": False,
        },
        wrapper_class=AtariWrapper,
        wrapper_kwargs={
            "noop_max": 30,
            "frame_skip": 4,
            "screen_size": 84,
            "terminal_on_life_loss": True,   # [FIX] False -> True：失命视为回合结束，提供更密集的监督信号
            "clip_reward": True,
        },
    )
    return env


def main() -> None:
    args = parse_args()

    args.log_dir = args.log_dir.resolve()
    args.save_dir = args.save_dir.resolve()

    monitor_dir       = args.log_dir / "monitor"
    eval_monitor_dir  = args.log_dir / "eval_monitor"
    best_model_dir    = args.save_dir / "best_model"
    eval_log_dir      = args.log_dir / "eval"

    for d in [monitor_dir, eval_monitor_dir, best_model_dir, eval_log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    tensorboard_dir = None
    if args.tensorboard_log_dir is not None:
        tensorboard_dir = args.tensorboard_log_dir.resolve()
        tensorboard_dir.mkdir(parents=True, exist_ok=True)

    # [FIX] 训练环境支持多并行实例
    train_env = make_atari_env(args.env_id, args.seed, n_envs=args.n_envs, monitor_dir=monitor_dir)
    train_env = VecFrameStack(train_env, n_stack=args.frame_stack)
    train_env = VecTransposeImage(train_env)

    # 评估环境保持单实例，结果更具可比性
    eval_env = make_atari_env(args.env_id, args.seed + 1, n_envs=1, monitor_dir=eval_monitor_dir)
    eval_env = VecFrameStack(eval_env, n_stack=args.frame_stack)
    eval_env = VecTransposeImage(eval_env)

    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.checkpoint_freq // args.n_envs, 1),
        save_path=str(args.save_dir),
        name_prefix="dqn_atari",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )
    eval_callback = EvalCallback(
        eval_env=eval_env,
        best_model_save_path=str(best_model_dir),
        log_path=str(eval_log_dir),
        eval_freq=max(args.eval_freq // args.n_envs, 1),
        n_eval_episodes=args.eval_episodes,
        deterministic=True,
        render=False,
    )
    callbacks = CallbackList([checkpoint_callback, eval_callback])

    if args.resume:
        print(f"Resuming training from: {args.resume}")
        model = DQN.load(args.resume, env=train_env, device=args.device)
        model.tensorboard_log = str(tensorboard_dir) if tensorboard_dir is not None else None
    else:
        model = DQN(
            policy="CnnPolicy",
            env=train_env,
            learning_rate=args.learning_rate,
            buffer_size=args.buffer_size,
            learning_starts=args.learning_starts,
            batch_size=args.batch_size,
            gamma=args.gamma,
            train_freq=(args.train_freq, "step"),
            gradient_steps=1,
            target_update_interval=args.target_update_interval,
            exploration_fraction=args.exploration_fraction,
            exploration_initial_eps=args.exploration_initial_eps,
            exploration_final_eps=args.exploration_final_eps,
            optimize_memory_usage=False,
            max_grad_norm=args.max_grad_norm,
            tensorboard_log=str(tensorboard_dir) if tensorboard_dir is not None else None,
            verbose=1,
            seed=args.seed,
            device=args.device,
        )

    try:
        model.learn(total_timesteps=args.total_timesteps, callback=callbacks, progress_bar=True)
        model.save(str(args.save_dir / "final_model"))
    finally:
        eval_env.close()
        train_env.close()

    print(f"Training finished. Final model saved to: {args.save_dir / 'final_model.zip'}")


if __name__ == "__main__":
    main()