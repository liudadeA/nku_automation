#!/usr/bin/env python3
# 同学们好，今天我们来逐行讲解这段Panda机械臂控制代码
# 这是Python脚本的标准开头，告诉Linux系统用Python 3解释器执行
# 加了可执行权限后，直接./panda_controller.py就能运行，不用写python3

# 首先导入我们需要的所有依赖库
import math  # Python自带数学库，后面画8字形、椭圆轨迹会用到三角函数
import rclpy  # ROS 2的Python客户端，所有ROS程序的基础
from rclpy.node import Node  # ROS节点基类，我们的控制器本身就是一个ROS节点

# 导入ROS标准消息类型：Point表示空间点，PoseStamped表示带时间戳和坐标系的位姿
from geometry_msgs.msg import Point, PoseStamped
# MoveIt 2最新的Python API核心，替代了旧版的moveit_commander
from moveit.planning import MoveItPy
# 配置加载工具，不用我们手动写几百行机械臂参数，直接加载官方配置
from moveit_configs_utils import MoveItConfigsBuilder
# 用来在RViz里显示规划好的机械臂运动轨迹
from moveit_msgs.msg import DisplayTrajectory
# 可视化标记，我们用它在RViz里画绿色的期望轨迹线
from visualization_msgs.msg import Marker
# 坐标变换库，专门解决欧拉角转四元数的问题，机器人控制必备
import tf_transformations


# 定义我们的控制器类，继承自ROS的Node类
# 这意味着我们的控制器天生就具备ROS的所有通信能力
class PandaController(Node):
    def __init__(self):
        # 调用父类构造函数，给我们的节点起个名字叫"panda_controller"
        super().__init__("panda_controller")
        # 打印一条日志，告诉大家程序开始初始化了
        self.get_logger().info("Initializing MoveItPy...")

        # ====================== 第一步：加载并配置MoveIt ======================
        # 这是最容易出问题的部分，因为我们用的是最新的Jazzy版本
        # 很多网上旧版的代码在这里都会报错
        moveit_config = (
            MoveItConfigsBuilder(
                robot_name="panda",  # 机器人名称，必须和官方配置包一致
                package_name="moveit_resources_panda_moveit_config",  # 官方配置包
            )
            # 指定用OMPL这个开源运动规划库，最常用也最稳定
            .planning_pipelines(pipelines=["ompl"])
            .to_moveit_configs()  # 生成完整的配置对象
        )

        # 把配置转成字典，方便我们修改参数
        config_dict = moveit_config.to_dict()
        pp = moveit_config.planning_pipelines

        # 【重点！Jazzy版本第一个大坑】
        # 默认生成的planning_pipelines是个简单列表['ompl']
        # 但MoveItPy内部需要的是嵌套字典格式，不改这里直接运行会报错
        config_dict["planning_pipelines"] = {
            "pipeline_names": pp["planning_pipelines"],
            "namespace": "",
        }

        # 设置全局规划参数
        config_dict["plan_request_params"] = {
            "planning_pipeline": "ompl",  # 默认用OMPL规划器
            "planning_attempts": 10,      # 一次规划失败最多重试10次
            "planning_time": 5.0,         # 单次规划最多给5秒时间
            "max_velocity_scaling_factor": 1.0,  # 速度缩放，真实机械臂一定要改成0.2-0.5
            "max_acceleration_scaling_factor": 1.0,  # 加速度缩放
        }

        # 【Jazzy版本第二个大坑】
        # Panda机械臂默认的初始姿态有轻微自碰撞
        # 这个CheckStartStateCollision检查会直接导致规划失败
        # 所以我们把它从请求适配器列表里删掉
        if "ompl" in config_dict and "request_adapters" in config_dict["ompl"]:
            config_dict["ompl"]["request_adapters"] = [
                a for a in config_dict["ompl"]["request_adapters"]
                if "CheckStartStateCollision" not in a
            ]

        # 删掉默认的轨迹显示，避免和我们后面自定义的绿色轨迹线重复
        if "ompl" in config_dict and "response_adapters" in config_dict["ompl"]:
            config_dict["ompl"]["response_adapters"] = [
                a for a in config_dict["ompl"]["response_adapters"]
                if "DisplayMotionPath" not in a
            ]

        # 现在配置改好了，创建MoveItPy核心实例
        # 这一步会在后台自动启动所有需要的MoveIt服务
        self.moveit = MoveItPy(node_name="moveit_py", config_dict=config_dict)

        # 获取机械臂的规划组件，对应Panda的7个关节
        self.arm = self.moveit.get_planning_component("panda_arm")
        # 指定末端执行器是panda_hand，也就是机械臂的手
        self.eef_link = "panda_hand"

        # 创建两个ROS发布者
        # 第一个发布规划好的轨迹，让RViz显示
        self._display_pub = self.create_publisher(
            DisplayTrajectory, "/display_planned_path", 10
        )
        # 第二个发布我们自定义的绿色轨迹线
        self._marker_pub = self.create_publisher(Marker, "/trajectory_marker", 10)

        # 设置允许碰撞矩阵，解决自碰撞问题
        self._setup_acm()
        self.get_logger().info("Panda Controller Ready")

    # ====================== 允许碰撞矩阵设置 ======================
    def _setup_acm(self):
        # 获取规划场景监视器，用来修改碰撞检测规则
        psm = self.moveit.get_planning_scene_monitor()
        # 获取读写权限
        with psm.read_write() as scene:
            acm = scene.allowed_collision_matrix
            # 这里我们允许两对连杆之间发生碰撞
            # 这是Panda机械臂的标准配置，不会损坏硬件
            # 但能大大扩大工作空间，提高规划成功率
            acm.set_entry("panda_hand", "panda_link5", True)
            acm.set_entry("panda_link5", "panda_link7", True)
            self.get_logger().info("Added self-collision exceptions to ACM")

    # ====================== 轨迹可视化函数 ======================
    def _display_trajectory(self, plan_result):
        # 把规划好的轨迹包装成ROS消息
        display_msg = DisplayTrajectory()
        display_msg.model_id = "panda"
        display_msg.trajectory.append(
            plan_result.trajectory.get_robot_trajectory_msg()
        )
        # 发布出去，RViz会自动显示
        self._display_pub.publish(display_msg)

    # 发布自定义的绿色轨迹线
    def _publish_path_marker(self, waypoints):
        marker = Marker()
        marker.header.frame_id = "panda_link0"  # 轨迹参考机械臂基座
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "desired_path"
        marker.id = 0
        marker.type = Marker.LINE_STRIP  # 类型是连续线条
        marker.action = Marker.ADD
        marker.scale.x = 0.003  # 线宽3毫米
        marker.color.a = 1.0
        marker.color.r = 0.0
        marker.color.g = 1.0  # 绿色
        marker.color.b = 0.0

        # 【非常重要的细节】
        # panda_hand坐标系的原点在手部根部
        # 而我们实际看到的指尖在原点前方0.11米处
        # 所以这里加个偏移，让RViz里显示的轨迹就是指尖实际走的路径
        finger_offset = 0.11
        for wp in waypoints:
            p = wp.pose.position
            marker.points.append(
                Point(x=p.x, y=p.y, z=p.z + finger_offset)
            )
        self._marker_pub.publish(marker)
        self.get_logger().info(
            f"Published path marker with {len(waypoints)} points"
        )

    # ====================== 核心函数1：单点位姿控制 ======================
    # 所有其他运动函数最终都调用这个函数
    def go_to_pose(self, x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
        # 第一步：创建目标位姿消息
        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = "panda_link0"  # 参考基座坐标系
        # 设置目标位置，单位是米
        pose_stamped.pose.position.x = x
        pose_stamped.pose.position.y = y
        pose_stamped.pose.position.z = z

        # 第二步：欧拉角转四元数
        # 为什么不用欧拉角直接表示姿态？
        # 因为欧拉角有万向锁问题，计算效率也低
        # 机器人内部都是用四元数的
        q = tf_transformations.quaternion_from_euler(roll, pitch, yaw)
        pose_stamped.pose.orientation.x = q[0]
        pose_stamped.pose.orientation.y = q[1]
        pose_stamped.pose.orientation.z = q[2]
        pose_stamped.pose.orientation.w = q[3]

        # 第三步：设置规划起点和终点
        # 起点是机械臂当前的实际状态，从关节话题获取
        self.arm.set_start_state_to_current_state()
        # 终点是我们刚才创建的目标位姿
        self.arm.set_goal_state(
            pose_stamped_msg=pose_stamped, pose_link=self.eef_link
        )

        # 第四步：执行运动规划
        # 这一步MoveIt会自动完成：逆运动学求解、碰撞检测、路径搜索、轨迹生成
        plan_result = self.arm.plan()

        # 第五步：如果规划成功就执行，失败就打印错误
        if plan_result and plan_result.trajectory:
            self.get_logger().info("Plan succeeded, executing...")
            self._display_trajectory(plan_result)  # 先在RViz显示轨迹
            self.moveit.execute(plan_result.trajectory, [])  # 执行轨迹，阻塞调用
        else:
            self.get_logger().error("Planning failed for this pose")

    # ====================== 核心函数2：多路径点顺序运动 ======================
    def go_through_poses(self, poses_stamped):
        # 遍历所有路径点，一个一个走
        for i, pose_stamped in enumerate(poses_stamped):
            self.get_logger().info(f"Moving to waypoint {i + 1}")
            # 每次都从当前实际位置开始规划
            # 这样即使上一次执行有误差，也不会累积
            self.arm.set_start_state_to_current_state()
            self.arm.set_goal_state(
                pose_stamped_msg=pose_stamped, pose_link=self.eef_link
            )
            plan_result = self.arm.plan()
            if plan_result and plan_result.trajectory:
                self._display_trajectory(plan_result)
                self.moveit.execute(plan_result.trajectory, [])
            else:
                self.get_logger().error(f"Planning failed at waypoint {i + 1}")
                break  # 任何一个点规划失败，就停下来

    # ====================== 核心函数3：近似笛卡尔路径跟随 ======================
    # 这是今天最有意思的部分，实现连续曲线运动
    def follow_cartesian_path(self, waypoints, eef_step=0.01, jump_threshold=0.0):
        # 先把期望的轨迹画成绿色线条显示在RViz里
        self._publish_path_marker(waypoints)

        # 路径采样：把连续的曲线拆成很多小段
        if eef_step <= 0:
            sampled_waypoints = waypoints  # 步长≤0就不采样
        else:
            sampled_waypoints = []
            accumulated = 0.0  # 累积距离计数器
            prev = None  # 上一个路径点

            for wp in waypoints:
                if prev is not None:
                    # 计算当前点和上一个点之间的距离
                    dx = wp.pose.position.x - prev.pose.position.x
                    dy = wp.pose.position.y - prev.pose.position.y
                    dz = wp.pose.position.z - prev.pose.position.z
                    accumulated += math.sqrt(dx * dx + dy * dy + dz * dz)

                    # 当累积距离达到我们设置的步长时
                    # 就把这个点加入采样列表
                    if accumulated >= eef_step:
                        sampled_waypoints.append(wp)
                        accumulated = 0.0
                else:
                    sampled_waypoints.append(wp)  # 第一个点直接加
                prev = wp

            # 确保最后一个点被包含，保证机械臂走到终点
            if sampled_waypoints[-1] is not waypoints[-1]:
                sampled_waypoints.append(waypoints[-1])

        self.get_logger().info(
            f"Following path with {len(sampled_waypoints)} waypoints"
        )
        # 调用多路径点函数，依次执行所有采样点
        # 因为步长很小，所以整体看起来就是平滑的曲线
        self.go_through_poses(sampled_waypoints)

    # ====================== 演示函数1：6点折线运动 ======================
    def demo_six_points(self):
        # 预定义6个空间点位
        waypoints = [
            self._create_pose_stamped(0.4, 0.0, 0.6),
            self._create_pose_stamped(0.4, 0.1, 0.6),
            self._create_pose_stamped(0.4, 0.1, 0.7),
            self._create_pose_stamped(0.3, 0.0, 0.7),
            self._create_pose_stamped(0.3, -0.1, 0.7),
            self._create_pose_stamped(0.3, -0.1, 0.6),
        ]
        self._publish_path_marker(waypoints)
        self.go_through_poses(waypoints)

    # ====================== 演示函数2：8字形轨迹 ======================
    def demo_eight_shape(self):
        waypoints = []
        radius = 0.08  # 8字形半径8厘米
        cx, cy, cz = 0.4, 0.0, 0.6  # 轨迹中心

        # 用利萨如曲线的参数方程生成8字形
        # 角度从0到2π，步长0.1弧度，总共63个点
        for angle in range(0, 628, 10):
            t = angle / 100.0
            x = cx + radius * math.sin(t)
            z = cz + radius * math.sin(2 * t) * 0.5
            waypoints.append(self._create_pose_stamped(x, cy, z))

        # 步长设为5毫米，平衡平滑性和速度
        self.follow_cartesian_path(waypoints, eef_step=0.005)

    # ====================== 演示函数3：椭圆轨迹 ======================
    def demo_ellipse(self):
        waypoints = []
        a, b = 0.1, 0.05  # 长半轴10厘米，短半轴5厘米
        cx, cy, cz = 0.4, 0.0, 0.6  # 椭圆中心

        # 用椭圆参数方程生成轨迹点
        for angle in range(0, 628, 10):
            t = angle / 100.0
            x = cx + a * math.cos(t)
            z = cz + b * math.sin(t)
            waypoints.append(self._create_pose_stamped(x, cy, z))

        self.follow_cartesian_path(waypoints, eef_step=0.005)

    # ====================== 辅助函数：创建位姿消息 ======================
    # 把重复代码封装起来，简化演示函数
    def _create_pose_stamped(self, x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = "panda_link0"
        pose_stamped.pose.position.x = x
        pose_stamped.pose.position.y = y
        pose_stamped.pose.position.z = z
        q = tf_transformations.quaternion_from_euler(roll, pitch, yaw)
        pose_stamped.pose.orientation.x = q[0]
        pose_stamped.pose.orientation.y = q[1]
        pose_stamped.pose.orientation.z = q[2]
        pose_stamped.pose.orientation.w = q[3]
        return pose_stamped


# ====================== 主函数：程序入口 ======================
def main(args=None):
    rclpy.init(args=args)  # 初始化ROS 2环境
    controller = PandaController()  # 创建控制器实例

    # ====================== 切换演示模式 ======================
    # 三选一运行，修改后不用重新编译，直接运行就行
    controller.demo_six_points()    # 6点折线运动
    # controller.demo_eight_shape()  # 8字形轨迹
    # controller.demo_ellipse()      # 椭圆轨迹
    # 注意：这里有个笔误，zcontroller应该是controller，运行前要改过来

    controller.destroy_node()  # 销毁节点
    rclpy.shutdown()  # 关闭ROS 2环境


if __name__ == "__main__":
    main()