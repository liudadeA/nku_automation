#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import rclpy.node
import time

def main():
    rclpy.init()

    navigator = BasicNavigator()
    # Set use_sim_time to true so that timestamps match Gazebo
    navigator.set_parameters([rclpy.parameter.Parameter('use_sim_time', rclpy.Parameter.Type.BOOL, True)])
    marker_pub = navigator.create_publisher(MarkerArray, '/waypoints', 10)

    # 设置初始位置
    initial_pose = PoseStamped()
    initial_pose.header.frame_id = 'map'
    initial_pose.header.stamp = navigator.get_clock().now().to_msg()
    initial_pose.pose.position.x = 0.0
    initial_pose.pose.position.y = 0.0
    initial_pose.pose.orientation.z = 0.0
    initial_pose.pose.orientation.w = 1.0

    print("正在设置初始位置...")
    navigator.setInitialPose(initial_pose)

    # 等待 Nav2 完全启动
    navigator.waitUntilNav2Active()
    print("Nav2 已准备就绪！开始全自动巡航...")

    # 设置预定的目标点 (Waypoints)
    # 根据 Turtlebot3_world 的环境，四个方向的角落点
    goals = []
    
    # 点 1
    goal_1 = PoseStamped()
    goal_1.header.frame_id = 'map'
    goal_1.pose.position.x = 1.5
    goal_1.pose.position.y = 1.5
    goal_1.pose.orientation.w = 1.0
    goals.append(goal_1)

    # 点 2
    goal_2 = PoseStamped()
    goal_2.header.frame_id = 'map'
    goal_2.pose.position.x = 2.0
    goal_2.pose.position.y = -1.5
    goal_2.pose.orientation.w = 1.0
    goals.append(goal_2)

    # 点 3 (右下侧)
    goal_3 = PoseStamped()
    goal_3.header.frame_id = 'map'
    goal_3.pose.position.x = 4.0
    goal_3.pose.position.y = 1.0
    goal_3.pose.orientation.w = 1.0
    goals.append(goal_3)

    # 点 4 (回到原点)
    goal_4 = PoseStamped()
    goal_4.header.frame_id = 'map'
    goal_4.pose.position.x = 0.0
    goal_4.pose.position.y = 0.0
    goal_4.pose.orientation.w = 1.0
    goals.append(goal_4)

    # Publish markers for visualization in RViz
    marker_array = MarkerArray()
    for i, goal in enumerate(goals):
        # 1. 球体标记 (表示目标点位置)
        sphere_marker = Marker()
        sphere_marker.header.frame_id = 'map'
        sphere_marker.header.stamp = navigator.get_clock().now().to_msg()
        sphere_marker.ns = 'waypoints'
        sphere_marker.id = i * 2
        sphere_marker.type = Marker.SPHERE
        sphere_marker.action = Marker.ADD
        sphere_marker.pose = goal.pose
        sphere_marker.scale.x = 0.2
        sphere_marker.scale.y = 0.2
        sphere_marker.scale.z = 0.2
        sphere_marker.color.a = 1.0
        sphere_marker.color.r = 1.0
        sphere_marker.color.g = 0.8
        sphere_marker.color.b = 0.0

        # 2. 文本标记 (表示序号)
        text_marker = Marker()
        text_marker.header.frame_id = 'map'
        text_marker.header.stamp = navigator.get_clock().now().to_msg()
        text_marker.ns = 'waypoints'
        text_marker.id = i * 2 + 1
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD
        text_marker.pose.position.x = goal.pose.position.x
        text_marker.pose.position.y = goal.pose.position.y + 0.15
        text_marker.pose.position.z = 0.0
        text_marker.pose.orientation = goal.pose.orientation
        text_marker.scale.z = 0.3  # 字体大小
        text_marker.color.a = 1.0
        text_marker.color.r = 0.0
        text_marker.color.g = 0.0
        text_marker.color.b = 0.0
        text_marker.text = f"Goal{i + 1}"

        marker_array.markers.append(sphere_marker)
        marker_array.markers.append(text_marker)

    # 发布几次确保 RViz 接收到 (由于是 Volatile)
    for _ in range(3):
        marker_pub.publish(marker_array)
        time.sleep(0.5)

    # 依次前往各个点
    for idx, goal_pose in enumerate(goals):
        print(f"========== 正在前往目标点 {idx + 1} ==========")
        navigator.goToPose(goal_pose)
        
        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            if feedback:
                print(f"剩余距离: {feedback.distance_remaining:.2f} 米", end='\r')
            time.sleep(1.0)
            
        result = navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            print(f"\n成功到达目标点 {idx + 1}！")
        elif result == TaskResult.CANCELED:
            print(f"\n目标点 {idx + 1} 被取消！")
        elif result == TaskResult.FAILED:
            print(f"\n前往目标点 {idx + 1} 失败！")
            
        time.sleep(2.0)

    print("========== 巡航任务全部完成！ ==========")
    navigator.lifecycleShutdown()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
