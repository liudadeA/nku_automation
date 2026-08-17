# TurtleBot 瓶子抓取系统 — 核心功能包说明

本文档描述 `main/` 目录下收录的核心自主编写功能包，即 `start_robot_remote.sh` 启动的系统实际使用的代码。

---

## 1. 概述

系统通过 `start_robot_remote.sh` 一键启动，执行 `roslaunch user_control robot_control_kinect.launch`，完成"语音/键盘启动 → 定点导航 → 搜索目标 → 视觉伺服靠近 → 机械臂抓取 → 前往终点"的完整任务流程。

导航采用 **AMCL 自适应蒙特卡洛定位 + move_base 导航** 框架：AMCL 使用 `/scan` 话题（由 Windows 端深度转 LaserScan 提供）进行扫描匹配定位，move_base 负责全局/局部路径规划和避障。


---

## 2. 目录结构

```
main/
├── sys_introduction.md                     # 本文档
│
├── user_control/                           # 主控制包
│   ├── package.xml
│   ├── CMakeLists.txt
│   ├── setup.py                            # catkin_python_setup
│   ├── scripts/
│   │   ├── state_machine.py                # 状态机主控（8 状态）
│   │   ├── kinect_data_receiver.py         # Kinect 综合数据接收客户端
│   │   ├── voice_control.py                # 语音控制（Vosk 离线识别）
│   │   ├── voice_feedback.py               # 语音反馈（TTS）
│   │   ├── keyboard_control.py             # 独立键盘控制
│   │   └── start_robot_remote.sh           # 一键启动脚本
│   ├── launch/
│   │   └── robot_control_kinect.launch     # 主 launch 文件
│   └── models/
│       └── vosk-model-small-cn-0.22/       # Vosk 中文语音识别模型
│
├── my_pkg/                                 # 导航与视觉伺服包
│   ├── package.xml
│   ├── CMakeLists.txt
│   ├── scripts/
│   │   ├── navi.py                         # 定点导航（AMCL + move_base）
│   │   ├── search_spin.py                  # 搜索旋转（state=1 时原地旋转搜索瓶子）
│   │   ├── visual_approach.py              # 视觉伺服靠近（检测框高度闭环控制）
│   │   ├── back_2_zero.py                  # 前往终点（反向回放 + AMCL + move_base）
│   │   ├── bottle_filter.py                # 瓶子检测过滤器
│   │   ├── jicheng.py                      # 机械臂位姿控制（4 段位姿插值）
│   │   └── global_localize.py              # AMCL 全局定位触发（发布大协方差初始位姿）
│   ├── config/
│   │   └── kinect_costmap.yaml             # move_base costmap 参数（Kinect 深度相机专用）
│   └── maps/
│       ├── room_map.yaml                   # 实际房间地图元数据
│       └── room_map.pgm                    # 实际房间地图栅格图像
│
├── my_dynamixel/                           # Dynamixel 机械臂驱动包
│   ├── package.xml
│   ├── CMakeLists.txt
│   ├── launch/
│   │   ├── controller_manager.launch       # Dynamixel 控制器管理器
│   │   └── start_tilt_controller.launch    # 5 电机控制器启动
│   └── config/
│       └── five_motors.yaml                # 5 个 Dynamixel 电机配置
│
├── yolov8_ros_msgs/                        # YOLO 检测消息定义包
│   ├── package.xml
│   ├── CMakeLists.txt
│   └── msg/
│       ├── BoundingBox.msg                 # 单个检测框消息
│       └── BoundingBoxes.msg               # 检测框数组消息
│
└── win_server/                             # Windows 端程序
    └── kinect_yolo_lidar_server.py         # Kinect 采集 + YOLO 推理 + 深度转 LaserScan
```

---

## 3. 功能包详解

### 3.1 user_control — 主控制包

系统顶层调度包，负责状态机控制、数据接收、用户交互和语音反馈。

| 节点/脚本 | 功能 | 话题 |
|-----------|------|------|
| `state_machine.py` | 8 状态有限状态机，控制整个任务流程 | 订阅: `/user_command`, `/detection_result`, `/navi_status`, `/bottle_in_pos`, `/jixiebi_in_pose`, `/robot_in_0`；发布: `/control_state`, `/controll_msg`, `/voice_feedback_cmd` |
| `kinect_data_receiver.py` | 连接 Windows 端两个 TCP 端口，接收检测和 LaserScan 数据 | 发布: `/detection_result`, `/scan`, `/kinect_server_status` |
| `voice_control.py` | Vosk 离线中文语音识别 + 键盘控制 | 发布: `/user_command` |
| `voice_feedback.py` | TTS 语音反馈，将状态 ID 转为语音播报 | 订阅: `/voice_feedback_cmd` |
| `keyboard_control.py` | 独立键盘控制模块，由 `start_robot_remote.sh` 在前台启动 | 发布: `/user_command` |
| `start_robot_remote.sh` | 一键启动脚本：检查服务器连通性 → 启动 roscore → 启动 roslaunch → 启动键盘控制 | — |

**`robot_control_kinect.launch`** 启动的节点：

1. `voice_feedback` — 语音反馈
2. `state_machine` — 状态机主控
3. `kinect_data_receiver` — 数据接收客户端
4. `voice_control` — 语音/键盘控制
5. `map_server` — 地图服务器（加载 `room_map.yaml`）
6. AMCL 定位节点（`kinect_amcl.launch.xml`）
7. `global_localize` — 全局定位触发
8. `move_base` — 导航栈（全局/局部规划 + 避障）
9. `navi_to_target` (my_pkg/navi.py) — 定点导航（向 move_base 发送目标）
10. `search_spin` (my_pkg/search_spin.py) — 搜索旋转
11. `bottle_filter` (my_pkg/bottle_filter.py) — 瓶子过滤器
12. `visual_approach` (my_pkg/visual_approach.py) — 视觉伺服
13. Dynamixel 控制器管理器 + 5 电机控制器 (my_dynamixel)
14. `arm_pose_controller` (my_pkg/jicheng.py) — 机械臂控制
15. `return_to_origin` (my_pkg/back_2_zero.py) — 前往终点
16. TurtleBot 底盘驱动 (turtlebot_bringup，官方包)

---

### 3.2 my_pkg — 导航与视觉伺服包

核心运动控制包，包含导航、搜索、视觉伺服、返航和机械臂控制。

#### 4.4.1 定位：AMCL 自适应蒙特卡洛定位

系统使用 AMCL（Adaptive Monte Carlo Localization）进行定位，基于粒子滤波在已知地图上估计机器人位姿。

**AMCL 配置**（`kinect_amcl.launch.xml`，来自 `turtlebot_navigation`）：
- 针对 Kinect v1 窄视场（~57°）调整了 AMCL 参数
- 使用 `/scan` 话题（由 Windows 端深度转 LaserScan 提供）进行扫描匹配
- 全局定位：启动时通过 `global_localize.py` 发布大协方差初始位姿，粒子遍布全图，移动后自动收敛

**`global_localize.py`**：延迟 3 秒后发布协方差 20m/360° 的初始位姿到 `/initialpose`，触发 AMCL 全局定位。机器人移动后粒子逐渐收敛到实际位置。

#### 4.4.2 导航：move_base

move_base 负责全局/局部路径规划和避障，配置文件 `kinect_costmap.yaml` 针对 Kinect 深度相机做了特殊调整：

| 参数 | 值 | 说明 |
|------|-----|------|
| `obstacle_range` | 3.5m | 标记障碍物范围 |
| `raytrace_range` | 5.0m | 清除障碍物范围 |
| `inflation_radius` | 0.3m | 膨胀半径 |
| `robot_radius` | 0.15m | 机器人半径 |
| `inf_is_valid` | true | 忽略深度相机 NaN/Inf |

#### `navi.py`（定点导航）

基于 AMCL 定位 + move_base 导航的定点导航节点。通过 actionlib 向 move_base 发送 `MoveBaseGoal`，由 move_base 完成路径规划和速度控制。

| 功能 | 实现方式 |
|------|---------|
| 定位 | AMCL 粒子滤波，订阅 `/amcl_pose` 获取位姿 |
| 导航 | move_base action client，发送 `MoveBaseGoal` |
| 速度控制 | 由 move_base 自动规划并发布到 `/cmd_vel_mux/input/navi` |
| 起点记录 | 导航开始时从 `/amcl_pose` 获取当前位置，发布到 `/robot_start_position` |
| 到达通知 | move_base 回调确认到达后发布 `/navi_status=1` |

仅在 `control_state=0` 时发送导航目标。

#### `search_spin.py`（搜索旋转）

在 `control_state=1` 时原地旋转搜索瓶子，超时后发布 `/navi_status=2`。

#### `visual_approach.py`（视觉伺服靠近）

基于检测框高度的闭环控制，两阶段靠近目标。

| 阶段 | 描述 |
|------|------|
| 0 | 旋转对准瓶子中心（`target_center_x=316.5`） |
| 1 | 前后移动：粗调 0.15m/s → ±20% 切微调 0.01m/s → 稳定 0.5s |
| 2 | 二次旋转对准 |
| 5 | 发布 `bottle_in_pos=1`，触发机械臂伸出 |
| 51 | 等待 5s（机械臂到位姿 2） |
| 6 | 开环前进 0.1m |
| 61 | 等待 5s |
| 7 | 发布 `bottle_in_pos=2`，触发机械臂抓取 |

仅在 `control_state=2,3` 时发布速度指令。

#### `back_2_zero.py`（前往终点）

两阶段前往终点：阶段 1 反向回放视觉伺服录制的控制序列（回到导航目标点附近）；阶段 2 使用 AMCL + move_base 导航到终点坐标。

| 阶段 | 实现方式 |
|------|---------|
| 阶段 1 (reversing) | 反向回放 `/approach_cmd_record` 录制的控制序列 |
| 阶段 2 (navigating) | move_base action client，发送终点坐标作为 `MoveBaseGoal` |

仅在 `control_state=5` 时发布速度指令。

#### `bottle_filter.py`（瓶子过滤器）

从 YOLO 检测结果中筛选 `bottle` 类别，发布到 `/bottle_caught`。

#### `jicheng.py`（机械臂位姿控制）

4 段位姿插值控制，通过 `/motor{i}_controller/command` 发布关节角度。

| 位姿 | 描述 |
|------|------|
| 1 | 伸出预抓取，夹爪张开 |
| 2 | 下探靠近瓶子，夹爪张开 |
| 3 | 下探位置不变，夹爪闭合抓取 |
| 4 | 收回抬起，夹爪保持闭合（搬运） |

#### `global_localize.py`（AMCL 全局定位触发）

延迟 3 秒后向 `/initialpose` 发布协方差 20m/360° 的初始位姿，触发 AMCL 全局定位。粒子遍布全图，机器人移动后自动收敛到实际位置。

---

### 3.3 my_dynamixel — Dynamixel 机械臂驱动包

提供 Dynamixel 电机控制器启动配置。

| 文件 | 功能 |
|------|------|
| `controller_manager.launch` | 启动 Dynamixel 控制器管理器，配置串口和波特率 |
| `start_tilt_controller.launch` | 加载 `five_motors.yaml` 参数，启动 5 个关节位置控制器 |
| `five_motors.yaml` | 5 个 Dynamixel 电机（ID 1-5）的关节名、速度、角度范围配置 |

---

### 3.4 yolov8_ros_msgs — YOLO 检测消息定义包

定义 YOLO 检测结果的 ROS 消息类型，供 `kinect_data_receiver.py`、`bottle_filter.py`、`visual_approach.py` 等节点使用。

| 消息 | 字段 |
|------|------|
| `BoundingBox` | `probability`, `xmin`, `ymin`, `xmax`, `ymax`, `Class`, `track_id` |
| `BoundingBoxes` | `header`, `image_header`, `BoundingBox[] bounding_boxes` |

---

### 3.5 win_server — Windows 端程序

#### `kinect_yolo_lidar_server.py`

运行在 Windows 上，负责采集 Kinect 数据并执行推理，通过两个 TCP 端口分发结果。

| 功能 | 实现方式 |
|------|---------|
| Kinect RGB/深度采集 | `KinectCapture` 类，优先级：pythonnet → SDK(ctypes) → libfreenect → OpenCV |
| YOLO 检测 | `model.predict()`，支持 `--target` 过滤目标类别 |
| 深度转 LaserScan | `depth_to_laserscan()`，向量化实现，取深度图水平扫描行 |
| TCP 发送 | 双端口（检测 9999 / 扫描 9998），`KINECT_DET_LASER_V1` 协议 |
| 数据校验 | MD5 前 8 位十六进制 checksum |

---

## 4. 状态机流程

| 状态 | 名称 | 活跃节点 | 触发条件 | 动作 |
|------|------|---------|---------|------|
| -1 | 待命 | 无 | 系统启动 / 任务完成 | 等待用户命令 |
| 0 | 定点导航 | navi.py + move_base | 用户发送启动命令 | 向 move_base 发送目标点 |
| 1 | 搜索目标 | search_spin.py | navi.py 到达目标点 | 等待 YOLO 检测到瓶子 |
| 2 | 视觉伺服 | visual_approach.py | YOLO 检测到 bottle | 发布 `controll_msg=1` |
| 3 | 机械臂伸出 | visual_approach.py | 瓶子粗调完成 | 发布 `controll_msg=2` |
| 4 | 机械臂抓取 | jicheng.py | 开环前进完成 | 发布 `controll_msg=3` |
| 5 | 前往终点 | back_2_zero.py + move_base | 抓取完成 | 反向回放 + move_base 返回 |
| 6 | 完成 | 无 | 到达终点 | 5 秒后重置为待命 |

---

## 5. 话题总览

| 话题 | 类型 | 发布者 | 订阅者 | 说明 |
|------|------|--------|--------|------|
| `/user_command` | Int32 | voice_control / keyboard_control | state_machine | 用户命令 |
| `/control_state` | Int32 | state_machine | navi, search_spin, visual_approach, back_2_zero | 当前状态 |
| `/controll_msg` | Int32 | state_machine | navi, visual_approach, jicheng, back_2_zero | 控制指令 |
| `/detection_result` | BoundingBoxes | kinect_data_receiver | state_machine, bottle_filter | YOLO 检测结果 |
| `/bottle_caught` | BoundingBox | bottle_filter | visual_approach | 瓶子检测框 |
| `/scan` | LaserScan | kinect_data_receiver | AMCL, move_base | 深度转激光扫描 |
| `/kinect_server_status` | Int32 | kinect_data_receiver | — | 服务器连接状态 |
| `/navi_status` | Int32 | navi, search_spin | state_machine | 导航状态 |
| `/bottle_in_pos` | Int32 | visual_approach | state_machine | 瓶子就位信号 |
| `/jixiebi_in_pose` | Int32 | jicheng | state_machine | 机械臂到位信号 |
| `/robot_in_0` | Int32 | back_2_zero | state_machine | 到达终点信号 |
| `/robot_start_position` | Point | navi | back_2_zero | 起点位置 |
| `/approach_cmd_record` | Twist | visual_approach | back_2_zero | 视觉伺服速度录制 |
| `/voice_feedback_cmd` | Int32 | state_machine | voice_feedback | 语音反馈指令 |
| `/amcl_pose` | PoseWithCovarianceStamped | AMCL | navi | AMCL 定位位姿 |
| `/initialpose` | PoseWithCovarianceStamped | global_localize | AMCL | 初始位姿（全局定位） |
| `/cmd_vel_mux/input/teleop` | Twist | search_spin, visual_approach, back_2_zero | cmd_vel_mux | 速度指令 |
| `/cmd_vel_mux/input/navi` | Twist | move_base | cmd_vel_mux | move_base 导航速度 |
| `/motor{i}_controller/command` | Float64 | jicheng | dynamixel_controllers | 关节角度指令 |

---

## 6. 速度指令仲裁

导航阶段（state=0）由 move_base 通过 `/cmd_vel_mux/input/navi` 发布速度指令；其他阶段各节点通过 `/cmd_vel_mux/input/teleop` 发布，仅在自身活跃状态时发布：

```
state=0 → move_base 通过 /cmd_vel_mux/input/navi 发布导航速度
state=1 → search_spin.py 通过 /cmd_vel_mux/input/teleop 发布旋转速度
state=2,3 → visual_approach.py 通过 /cmd_vel_mux/input/teleop 发布视觉伺服速度
state=5 → back_2_zero.py 阶段1 通过 /cmd_vel_mux/input/teleop 发布回放速度
        → back_2_zero.py 阶段2 由 move_base 通过 /cmd_vel_mux/input/navi 发布导航速度
其他状态 → 无节点发布速度
```

---

## 7. TCP 通信协议

Windows 端与 WSL2 端通过 `KINECT_DET_LASER_V1` 协议通信，双端口（检测 9999 / 扫描 9998）。

- **纯 JSON 帧**（检测数据）：`[8字节头: payload长度+seq][JSON载荷]`
- **混合编码帧**（LaserScan）：`[8字节头: payload长度+seq][JSON头][二进制ranges]`

LaserScan 的 ranges 数据以 float32 二进制紧跟 JSON 头之后传输，避免 JSON 序列化大量浮点数的性能开销。

---

## 8. 依赖的官方/第三方包

以下包未收录在 `main/` 中，但系统运行需要：

| 包 | 用途 |
|----|------|
| `rospy` / `roscore` | ROS 核心 |
| `turtlebot_bringup` | TurtleBot 底盘驱动 |
| `turtlebot_navigation` | AMCL + move_base 导航栈（含 `kinect_amcl.launch.xml`、`move_base.launch.xml`） |
| `dynamixel_controllers` | Dynamixel 电机控制器框架 |
| `yocs_cmd_vel_mux` | 速度指令多路复用 |
| `map_server` | 地图服务器 |
| `amcl` | 自适应蒙特卡洛定位 |
| `move_base` | 全局/局部路径规划 + 避障 |
| `std_msgs` / `geometry_msgs` / `sensor_msgs` / `nav_msgs` | ROS 标准消息 |
| `tf` / `tf2_ros` | 坐标变换 |
| `actionlib` / `move_base_msgs` | 动作库 |
| `cv_bridge` | OpenCV-ROS 桥接 |
| Python: `vosk`, `pyaudio` | 语音识别 |
| Python: `ultralytics` (Windows 端) | YOLOv8 推理 |
