#!/usr/bin/python3

import rospy
import numpy as np
from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import Twist, Point
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int32
from tf.transformations import euler_from_quaternion
from visualization_msgs.msg import Marker, MarkerArray
import time

class ReturnToOriginNode:
    def __init__(self):
        rospy.init_node('return_to_origin_node', anonymous=True)
        
        # 订阅地图、里程计、激光数据、控制消息和机器人起始位置
        self.map_sub = rospy.Subscriber('/map', OccupancyGrid, self.map_callback)
        self.odom_sub = rospy.Subscriber('/odom', Odometry, self.odom_callback)
        self.laser_sub = rospy.Subscriber('/scan', LaserScan, self.laser_callback)
        self.control_sub = rospy.Subscriber('/controll_msg', Int32, self.control_callback)
        self.start_position_sub = rospy.Subscriber('/robot_start_position', Point, self.start_position_callback)
        
        # 发布速度指令和到达原点的消息
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel_mux/input/navi', Twist, queue_size=10)
        self.at_origin_pub = rospy.Publisher('/robot_in_0', Int32, queue_size=10)
        
        # 初始化变量
        self.current_map = None
        self.robot_pose = None
        self.laser_data = None
        self.map_resolution = 0.05  # 地图分辨率 (m/pixel)
        self.map_origin = None
        self.control_msg = 0  # 初始化为0，不发布速度指令
        self.at_origin = False  # 是否到达原点的标志
        self.start_position = None  # 机器人起始位置
        self.zero_velocity_start_time = None  # 记录开始保持零速度的时间
        self.state4_start_time = None  # 进入状态4的时间, 用于延迟10s
        self.backing_up = False        # 后退中
        self.backup_start = None       # 后退起始里程
        self.backup_distance = 0.5     # 后退距离 (m)

        # 控制参数
        self.Kp_linear = 0.1
        self.Kp_angular = 0.8
        self.max_speed = 0.5
        self.safe_distance = 1.2 # 安全停止距离 (m)
        self.obstacle_slowdown_factor = 0.7  # 障碍物附近减速因子
        self.arrival_threshold = 0.15  # 到达原点的距离阈值 (m)
        self.zero_velocity_duration = 3.0  # 零速度持续时间阈值 (秒)
        
        rospy.loginfo("Return to Origin Node Initialized")

    def map_callback(self, msg):
        """处理地图更新"""
        self.current_map = msg
        self.map_origin = (msg.info.origin.position.x, msg.info.origin.position.y)
        self.map_resolution = msg.info.resolution
        rospy.loginfo("地图更新: 尺寸=%dx%d, 分辨率=%.3f m/像素, 原点=(%.3f, %.3f)", 
                      msg.info.width, msg.info.height, self.map_resolution, 
                      self.map_origin[0], self.map_origin[1])

    def odom_callback(self, msg):
        """更新机器人位姿"""
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        _, _, yaw = euler_from_quaternion([orientation.x, orientation.y, orientation.z, orientation.w])
        self.robot_pose = (position.x, position.y, yaw)

    def calculate_distance_to_origin(self):
        """计算机器人到原点的距离"""
        if self.robot_pose is None or self.start_position is None:
            return float('inf')
        robot_x, robot_y, _ = self.robot_pose
        origin_x = self.start_position.x
        origin_y = self.start_position.y
        return np.hypot(robot_x - origin_x, robot_y - origin_y)

    def laser_callback(self, msg):
        """更新激光数据"""
        self.laser_data = msg.ranges

    def obstacle_avoidance(self):
        """改进的避障逻辑"""
        if self.laser_data is None:
            return False
            
        # 检查前方180度范围内的障碍物
        front_scan = self.laser_data[:120] + self.laser_data[-120:]
        min_distance = min(front_scan) if front_scan else float('inf')
        
        if min_distance < self.safe_distance:
            rospy.loginfo("检测到障碍物! 最小距离=%.3f m", min_distance)
            return True
        return False

    def check_zero_velocity_duration(self, cmd):
        """检查零速度持续时间"""
        current_time = time.time()
        
        # 检查当前命令是否为零速度
        if abs(cmd.linear.x) < 0.003 and abs(cmd.angular.z) < 0.003:
            if self.zero_velocity_start_time is None:
                self.zero_velocity_start_time = current_time
            else:
                # 计算持续时间
                duration = current_time - self.zero_velocity_start_time
                if duration >= self.zero_velocity_duration and not self.at_origin:
                    self.at_origin = True
                    rospy.loginfo("到达原点! 已保持零速度 %.1f 秒", duration)
                    self.at_origin_pub.publish(Int32(1))  # 发布到达原点的消息
        else:
            # 速度不为零，重置计时器
            self.zero_velocity_start_time = None
            if self.at_origin:
                self.at_origin = False
                rospy.loginfo("离开原点区域")

    def navigate_to_origin(self):
        """生成导航到原点的控制指令"""
        if self.start_position is None or self.robot_pose is None:
            rospy.loginfo("没有起始位置或机器人位姿，发布零速度指令")
            return Twist()
            
        robot_x, robot_y, robot_yaw = self.robot_pose
        target_x = self.start_position.x
        target_y = self.start_position.y
        
        # 计算目标方向
        dx = target_x - robot_x
        dy = target_y - robot_y
        target_distance = np.hypot(dx, dy)
        target_angle = np.arctan2(dy, dx)
        
        # 角度误差 (归一化到[-π, π])
        angle_error = target_angle - robot_yaw
        if angle_error > np.pi:
            angle_error -= 2 * np.pi
        elif angle_error < -np.pi:
            angle_error += 2 * np.pi
        
        # 创建控制指令
        cmd = Twist()
        
        # 避障优先级最高
        if self.obstacle_avoidance():
            # 障碍物太近，停止前进并旋转
            cmd.linear.x = 0.0
            cmd.linear.y = 0.0
            
            # 尝试寻找远离障碍物的方向
            left_scan = self.laser_data[0:45]
            right_scan = self.laser_data[-45:]
            
            left_min = min(left_scan) if left_scan else float('inf')
            right_min = min(right_scan) if right_scan else float('inf')
            
            if left_min > right_min:
                # 左边空间更大，向左转
                cmd.angular.z = self.Kp_angular * 1.4
            else:
                # 向右转
                cmd.angular.z = self.Kp_angular * 1.4
                
            rospy.loginfo("避障模式: 角速度=%.3f rad/s", cmd.angular.z)
            return cmd
        
        # 距离控制
        if target_distance > self.arrival_threshold:
            cmd.linear.x = min(self.Kp_linear * target_distance, self.max_speed)
            # 接近目标时减速
            if target_distance < 0.8:
                cmd.linear.x *= 0.7
        else:
            # 已到达原点附近，停止移动
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
        
        # 如果附近有障碍物，减速慢行
        if self.obstacle_avoidance():
            cmd.linear.x *= self.obstacle_slowdown_factor
        
        # 角度控制
        if abs(angle_error) > 0.1:
            # 角度误差较大时，优先转向
            if target_distance > 0.3:
                cmd.linear.x *= 0.3  # 减小线速度，专注转向
            cmd.angular.z = self.Kp_angular * angle_error
        
        rospy.loginfo("发布控制指令: 线速度=%.3f m/s, 角速度=%.3f rad/s", 
                     cmd.linear.x, cmd.angular.z)
        
        return cmd

    def control_callback(self, msg):
        """处理控制消息"""
        if msg.data != self.control_msg:
            rospy.loginfo("控制消息: %d → %d", self.control_msg, msg.data)
        prev_msg = self.control_msg
        self.control_msg = msg.data
        
        # 重置到达原点的标志和相关计时器
        if self.control_msg == 4 and prev_msg != 4:
            self.at_origin = False
            self.zero_velocity_start_time = None
            self.state4_start_time = time.time()
            self.backing_up = False
            self.backup_start = None
            rospy.loginfo("进入状态4, 等待10s后开始返航")

    def start_position_callback(self, msg):
        """处理机器人起始位置消息"""
        self.start_position = msg
        rospy.loginfo("接收到机器人起始位置: x=%.3f, y=%.3f", msg.x, msg.y)

    def run(self):
        rate = rospy.Rate(10)  # 10Hz
        while not rospy.is_shutdown():
            if self.control_msg == 4 and not self.at_origin:
                # 进入状态4后等待10s, 再开始返航
                if self.state4_start_time is not None:
                    elapsed = time.time() - self.state4_start_time
                    if elapsed < 10.0:
                        self.cmd_vel_pub.publish(Twist())  # 原地等待
                        rospy.loginfo_throttle(2, "状态4 等待返航: %.1f / 10.0 s", elapsed)
                    else:
                        self.state4_start_time = None  # 等待完成
                        self.backing_up = True
                        self.backup_start = self.robot_pose
                        rospy.loginfo("等待完成, 先后退 %.1fm 再返航", self.backup_distance)
                elif self.backing_up:
                    # 后退0.5m, 离开抓取位置
                    if self.robot_pose and self.backup_start:
                        moved = np.hypot(self.robot_pose[0] - self.backup_start[0],
                                         self.robot_pose[1] - self.backup_start[1])
                        if moved < self.backup_distance:
                            cmd = Twist()
                            cmd.linear.x = -0.1  # 慢速后退
                            self.cmd_vel_pub.publish(cmd)
                            rospy.loginfo_throttle(1, "后退中: %.2f / %.1f m", moved, self.backup_distance)
                        else:
                            self.cmd_vel_pub.publish(Twist())
                            self.backing_up = False
                            self.backup_start = None
                            rospy.loginfo("后退完成, 开始返航导航")
                else:
                    cmd_vel = self.navigate_to_origin()
                    self.cmd_vel_pub.publish(cmd_vel)
                    self.check_zero_velocity_duration(cmd_vel)
            else:
                if not self.at_origin:
                   pass

            rate.sleep()

if __name__ == '__main__':
    try:
        node = ReturnToOriginNode()
        node.run()
    except rospy.ROSInterruptException:
        pass