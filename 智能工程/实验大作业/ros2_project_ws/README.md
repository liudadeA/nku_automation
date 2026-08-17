# ROS2 TurtleBot3 自主建图与多点导航系统

本项目是一个基于 ROS2 (Jazzy) 和 Gazebo 的移动机器人仿真应用。以 TurtleBot3 为平台，集成了 `slam_toolbox` 和 `explore_lite` 实现未知环境的自主探索建图，并利用 Nav2 导航栈实现了已知环境下的自动多点巡航。

## 目录结构

*   `scripts/`：流程控制脚本（推荐直接运行这些脚本以启动不同模块）。
*   `src/course_demo/`：自定义控制节点包（包含了启动文件、RViz配置、多点巡航控制代码 `auto_navigator.py`）。
*   `src/m-explore-ros2/`：引入的第三方前沿探索功能包（`explore_lite`）。
*   `maps/`：保存的 2D 栅格地图文件（`.yaml` 和 `.pgm`）。

## 使用指南

在运行任何脚本前，请确保已经编译了工作空间并 sourcing 环境变量（脚本中已做部分自动化封装，但若要手动运行节点需确保环境配置正确）：
```bash
colcon build
source install/setup.bash
```

### 1. 全自动探索建图
启动仿真环境与自主建图算法，机器人将在环境中自动寻找边界进行建图：
```bash
bash scripts/1_mapping.sh
```

### 2. 保存地图
在建图完成后（地图已经完整覆盖所需区域），执行此脚本将地图保存到 `maps/` 文件夹下：
```bash
bash scripts/2_save_map.sh
```

### 3. 全自动多点巡航
加载保存的地图并启动 Nav2，机器人将按顺序自动前往预设的 4 个目标点进行巡航（可通过 RViz 观察进度和 Marker）：
```bash
bash scripts/3_navigation.sh
```

## 环境依赖
- ROS2 Jazzy
- Gazebo (TurtleBot3 World)
- slam_toolbox
- nav2_bringup
