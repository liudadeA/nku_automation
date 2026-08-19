# 机器人视觉抓取项目

TurtleBot2 + Kinect 深度相机 + Dynamixel 5轴机械臂，基于 ROS Noetic。

## 项目结构

```
catkin_ws/src/
├── my_pkg/              ← 核心包: 状态机/导航/视觉/抓取/返航
│   ├── launch/          5个launch文件
│   ├── scripts/         8个Python节点
│   ├── config/          Kinect costmap配置
│   └── maps/            预建地图
├── my_dynamixel/        ← Dynamixel 5关节机械臂控制
├── robot_voice/         ← 语音识别(IAT)+合成(TTS)
├── voice_control/       ← 语音指令解析 → /voice_command
├── yolov8_ros/          ← YOLOv8 瓶子检测
├── kobuki_keyop/        ← 键盘方向键控制(手动建图)
├── turtlebot*/          ← TurtleBot 底盘/导航/AMCL 官方包
├── freenect_stack/      ← Kinect v1 驱动
├── dynamixel_motor_for_noetic/  ← Dynamixel 舵机驱动
└── yocs_*/              ← cmd_vel_mux 优先级复用
```

## 架构

```
                    ┌─────────────┐
                    │  map_server │  预建地图
                    └──────┬──────┘
                           ↓
┌──────────┐    ┌──────────────────┐    ┌──────────────┐
│  Kinect  │───→│ depthimage_to_   │───→│    AMCL      │  定位
│ (深度图) │    │ laserscan (/scan)│    │  (粒子滤波)   │
└────┬─────┘    └──────────────────┘    └──────┬───────┘
     │                                        │
     ↓                                        ↓
┌──────────┐    ┌──────────────┐    ┌──────────────────┐
│ YOLOv8   │───→│ bottle_filter│    │    move_base     │  导航
│ 瓶子检测  │    │  (过滤/透传) │    │ navfn + DWA      │
└────┬─────┘    └──────┬───────┘    └────────┬─────────┘
     │                 │                     │
     └────────┬────────┘                     │
              ↓                              │
     ┌────────────────┐                      │
     │ controll_core  │  中央状态机           │
     │ (10帧防抖)      │                      │
     └───────┬────────┘                      │
             │                               │
    ┌───────┴───────────────────────────────┴──┐
    │              cmd_vel_mux                 │
    │  teleop(v7) > switch(v6) > navi(v5)     │
    └──────────────────┬───────────────────────┘
                       ↓
              ┌─────────────────┐
              │  Kobuki 底盘    │
              └─────────────────┘
```

## 文件说明

### Launch 文件

| 文件 | 用途 |
|------|------|
| `full_pipeline.launch` | **生产任务**: 语音指令触发 → AMCL定位 → move_base导航到目标 → 视觉搜索 → 抓取 → 返航 |
| `real_gmapping.launch` | **自主建图**: gmapping + explore_lite 自主探索建图，保存地图 |
| `manual_gmapping.launch` | **混合建图**: gmapping + explore_lite 自主探索 + 键盘手动接管 (键盘优先级最高) |
| `arm_bringup.launch` | 机械臂子模块: 启动 Dynamixel 5关节控制器 |
| `full_debug.launch` | **调试**: 底盘+Kinect+YOLO+视觉对准+机械臂，无导航建图 |
| `grasp_pipeline.launch` | 旧版抓取流程 (AMCL + 颜色检测) |
| `visual_grasp.launch` | 仅视觉+机械臂，无底盘 |
| `sim_*.launch` | Gazebo 仿真场景 |

### Python 节点 (scripts/)

| 文件 | 功能 |
|------|------|
| `controll_core.py` | **中央状态机**: 发布 `/controll_msg` 协调所有节点。包含10帧滑动窗口防抖 (≥5/10帧确认瓶子)。状态: -1(空闲)→0(导航)→1(对准)→2(伸出)→3(抓取)→4(返航)→5(完成) |
| `navi.py` | **导航+搜索**: 收到指令后旋转15秒辅助AMCL收敛，再通过 move_base actionlib 导航到目标坐标，到达后旋转搜索水瓶 |
| `visual_approach.py` | **视觉伺服对准**: 基于YOLO检测框的闭环控制，粗调(0.15m/s)→微调(0.01m/s)→二次旋转→开环前进，发布 `/bottle_in_pos` 触发机械臂 |
| `jicheng.py` | **机械臂抓取**: 5关节Dynamixel 4位姿序列 (伸出预抓→下探→夹爪闭合→抬起搬运)，发布 `/jixiebi_in_pose` |
| `back_2_zero.py` | **返航**: 读取 `/robot_start_position`，直接速度控制导航回起点，发布 `/robot_in_0` |
| `bottle_filter.py` | **瓶子过滤**: 订阅 `/yolov8/BoundingBoxes`，过滤 class=bottle 且置信度>0.15，发布到 `/bottle_caught` |
| `global_localize.py` | **全局定位**: 延迟3秒后发布大协方差初始位姿到 `/initialpose`，触发AMCL全局粒子散布 |

### 配置文件 (config/)

| 文件 | 用途 |
|------|------|
| `kinect_costmap.yaml` | Kinect 窄视场(57°)适配: `inf_is_valid=true`(忽略NaN)，放宽高度限制，减小膨胀半径，禁用旋转恢复 |

### 地图 (maps/)

| 文件 | 用途 |
|------|------|
| `room_map.yaml` + `room_map.pgm` | 已保存的建图结果，`full_pipeline.launch` 加载此地图进行定位导航 |

## 使用方法

### 1. 建图

**自主探索建图:**
```bash
roslaunch my_pkg real_gmapping.launch
# explore_lite 自动探索，gmapping 实时建图
```

**混合建图 (自主探索 + 键盘接管):**
```bash
roslaunch my_pkg manual_gmapping.launch
# 默认手动模式, 方向键控制底盘:
#   ↑↓←→ 移动, 空格=停止
#   h = 切换 手动/自主 模式
#   q = 退出
# 手动模式: 键盘优先, 松手后保持静止 (teleop 占用)
# 自主模式: explore_lite 自动探索建图
```

保存地图 (带时间戳, 防止覆盖):
```bash
rosrun map_server map_saver -f ~/catkin_ws/src/my_pkg/maps/room_map_$(date +%Y%m%d_%H%M%S)
```

### 2. 执行任务

```bash
roslaunch my_pkg full_pipeline.launch
# 启动后等待语音指令触发任务:
# 说 "抓取" / "pick" / "开始任务" → 自动执行全流程
# 或手动触发:
rostopic pub /voice_command std_msgs/Int32 "data: 0" -1
```

### 3. 修改目标坐标

编辑 `full_pipeline.launch` 中的参数:
```xml
<param name="target_x" value="0.24"/>   <!-- 目标X坐标(地图坐标系) -->
<param name="target_y" value="-0.02"/>  <!-- 目标Y坐标 -->
<param name="target_yaw" value="180.0"/> <!-- 目标朝向(度) -->
```

## 状态机流程

```
voice_command "pick bottle" (语音/手动)
        │
        │ navi: 旋转15秒帮助AMCL收敛定位
        │ AMCL收敛后记录起点
        ↓
State 0 │ navi: move_base 导航到目标(x,y)
        │
        │  到达目标
        ↓
        │ navi: 慢速旋转30秒搜索水瓶
        │ YOLO 检测 ≥5/10帧确认
        ↓
State 1 │ visual_approach: 旋转对准 → 前后粗调 → 微调 → 前进
        │
        │  bottle_in_pos=1
        ↓
State 2 │ jicheng: 位姿1→位姿2(伸出下探)
        │  visual_approach: 等待→开环前进→发布 bottle_in_pos=2
        ↓
State 3 │ jicheng: 位姿2→位姿3(夹爪闭合)→位姿4(抬起)
        │
        │  jixiebi_in_pose=4
        ↓
State 4 │ back_2_zero: 直接速度控制返回起点
        │
        │  robot_in_0=1 (到达)
        ↓
State 5 │ 完成
```

## 硬件依赖

| 硬件 | 接口 | 用途 |
|------|------|------|
| Kobuki 底座 | `/dev/ttyKobuki` | 移动 |
| Kinect v1 | USB | RGB+深度 |
| Dynamixel 舵机×5 | `/dev/ttyDynamixel` (1Mbps) | 机械臂 |

## 软件依赖 (apt)

```bash
ros-noetic-amcl ros-noetic-move-base ros-noetic-gmapping
ros-noetic-explore-lite ros-noetic-depthimage-to-laserscan
ros-noetic-map-server ros-noetic-freenect-launch
ros-noetic-turtlebot-bringup ros-noetic-turtlebot-navigation
ros-noetic-dynamixel-controllers ros-noetic-yolov8-ros
```
