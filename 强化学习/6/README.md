# Atari DQN 训练示例

这个项目使用 `DQN` 训练一款雅达利游戏，并且直接以游戏视频帧作为输入。默认环境是 `ALE/Pong-v5`，你也可以切换为其他 Atari 游戏。

## 方案说明

输入处理流程如下：

1. 从 Atari 环境读取原始 RGB 视频帧。
2. 使用 `AtariWrapper` 做经典 DQN 预处理：
   - 随机无操作开局
   - 动作重复与跳帧
   - 灰度化
   - 缩放到 `84 x 84`
   - 奖励裁剪
3. 将最近 `4` 帧堆叠为一个状态。
4. 使用 `CnnPolicy` 的卷积 Q 网络进行训练。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 开始训练

默认训练 `Pong`：

```bash
python train_dqn_atari.py --env-id ALE/Pong-v5 --total-timesteps 1000000
```

如果你想训练 `Breakout`：

```bash
python train_dqn_atari.py --env-id ALE/Breakout-v5 --total-timesteps 1000000
```

## 常用参数

- `--buffer-size`：经验回放池大小
- `--learning-starts`：开始更新网络前的预热步数
- `--frame-stack`：状态中堆叠的视频帧数量
- `--eval-freq`：评估间隔
- `--device cuda`：使用 GPU 训练
- `--tensorboard-log-dir`：可选的 TensorBoard 日志目录

示例：

```bash
python train_dqn_atari.py ^
  --env-id ALE/Pong-v5 ^
  --total-timesteps 2000000 ^
  --buffer-size 100000 ^
  --learning-starts 20000 ^
  --device cuda
```

## 训练产物

- 模型检查点保存在 `checkpoints/pong_dqn`
- 最优模型保存在 `checkpoints/pong_dqn/best_model`
- 评估日志保存在 `runs/pong_dqn/eval`

如果你需要 TensorBoard，可以显式指定日志目录：

```bash
python train_dqn_atari.py --tensorboard-log-dir tb_logs/pong_dqn
```

然后启动：

```bash
tensorboard --logdir tb_logs
```

## 说明

- Atari 从像素输入直接学习通常需要较长训练时间，`1M` 步只是一个起点。
- 如果显存或内存不足，可以先减小 `--buffer-size`。
- 若你本机的 Atari ROM 或环境版本不同，可以把 `--env-id` 换成自己已安装的 Atari 环境 ID。
- 如果 TensorBoard 在你的 Windows 环境下因为路径问题报错，可以先不传 `--tensorboard-log-dir`，不影响训练主流程。
