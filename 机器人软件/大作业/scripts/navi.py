#!/usr/bin/python3
"""
导航到固定目标 (0,0), 到达后旋转搜索水瓶.
使用 move_base (actionlib) 导航, AMCL 定位.
"""
import rospy
import numpy as np
import actionlib
from geometry_msgs.msg import Point, Quaternion, Twist
from std_msgs.msg import Int32, String
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal


class NavToTarget:
    def __init__(self):
        rospy.init_node('navi_to_target', anonymous=True)

        # ── 参数 ──
        self.target_x = rospy.get_param('~target_x', 0.0)
        self.target_y = rospy.get_param('~target_y', 0.0)
        self.target_yaw = rospy.get_param('~target_yaw', 0.0)  # 目标朝向(度)
        self.localize_spin_time = rospy.get_param('~localize_spin_time', 20.0)
        self.search_spin_time = rospy.get_param('~search_spin_time', 90.0)

        # ── 状态 ──
        self.robot_pose = None
        self.control_msg = -1
        self.phase = 'idle'          # idle → localizing → navigating → searching
        self.start_position = None
        self.pending_command = False   # data=0 已收到但定位尚未完成
        self.nav_retry_count = 0       # 导航失败重试计数
        self.max_nav_retries = 3       # 最多重试3次

        # ── move_base 客户端 ──
        self.move_base = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("等待 move_base ...")
        self.move_base.wait_for_server(rospy.Duration(30))
        rospy.loginfo("move_base 已连接, 目标: (%.1f, %.1f, %.0f°)", self.target_x, self.target_y, self.target_yaw)

        # ── 发布 ──
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel_mux/input/navi', Twist, queue_size=10)
        self.start_pos_pub = rospy.Publisher('/robot_start_position', Point, queue_size=10)
        self.phase_pub = rospy.Publisher('/navi_phase', String, queue_size=10)

        # ── 定时 ──
        self.phase_start = rospy.Time.now()

        # ── 订阅 ──
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        rospy.Subscriber('/controll_msg', Int32, self.control_callback)

        rospy.loginfo("NavToTarget 就绪 (等待 voice_command data=0)")
        self.phase_pub.publish(String(data='idle'))

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        o = msg.pose.pose.orientation
        _, _, yaw = euler_from_quaternion([o.x, o.y, o.z, o.w])
        self.robot_pose = (p.x, p.y, yaw)

    def control_callback(self, msg):
        prev = self.control_msg
        self.control_msg = msg.data

        if msg.data == 0 and prev != 0:
            # 收到指令: 先旋转帮助AMCL收敛, 定位完成后再记录起点
            rospy.loginfo("收到任务指令, 开始AMCL定位旋转 %ds", int(self.localize_spin_time))
            self.phase = 'localizing'
            self.phase_pub.publish(String(data='localizing'))
            self.phase_start = rospy.Time.now()
            self.nav_retry_count = 0
            self.pending_command = True

        elif msg.data != 0 and self.phase in ('localizing', 'navigating', 'searching'):
            self.move_base.cancel_goal()
            self.cmd_vel_pub.publish(Twist())
            self.phase = 'idle'
            self.phase_pub.publish(String(data='idle'))
            self.pending_command = False
            rospy.loginfo("状态→%d, 任务中断", msg.data)

    def _send_goal(self):
        """发送导航目标到 move_base"""
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = self.target_x
        goal.target_pose.pose.position.y = self.target_y
        q = quaternion_from_euler(0, 0, np.radians(self.target_yaw))
        goal.target_pose.pose.orientation = Quaternion(*q)
        self.move_base.send_goal(goal)
        rospy.loginfo("已发送目标: (%.1f, %.1f)", self.target_x, self.target_y)

    def _goal_reached(self):
        state = self.move_base.get_state()
        return state in [actionlib.GoalStatus.SUCCEEDED,
                         actionlib.GoalStatus.ABORTED,
                         actionlib.GoalStatus.REJECTED]

    def run(self):
        rate = rospy.Rate(10)
        idle_counter = 0

        while not rospy.is_shutdown():
            if self.phase == 'idle':
                # 空闲: 不发布, 让其他节点使用 teleop
                pass

            elif self.phase == 'localizing':
                # 收到 data=0 后, 旋转帮助 AMCL 收敛
                elapsed = (rospy.Time.now() - self.phase_start).to_sec()
                if elapsed < self.localize_spin_time:
                    cmd = Twist()
                    cmd.angular.z = 0.3
                    self.cmd_vel_pub.publish(cmd)
                    rospy.loginfo_throttle(3, "AMCL 定位中 (旋转, 0.3rad/s)... %d/%ds",
                                           int(elapsed), int(self.localize_spin_time))
                else:
                    self.cmd_vel_pub.publish(Twist())
                    # 定位收敛后记录起点, 再导航
                    if self.robot_pose:
                        self.start_position = (self.robot_pose[0], self.robot_pose[1])
                        p = Point(x=self.start_position[0], y=self.start_position[1])
                        self.start_pos_pub.publish(p)
                        rospy.loginfo("定位完成, 起点: (%.2f, %.2f) → 导航到 (%.1f, %.1f)",
                                      p.x, p.y, self.target_x, self.target_y)
                    self.phase = 'navigating'
                    self.phase_pub.publish(String(data='navigating'))
                    self.phase_start = rospy.Time.now()
                    self._send_goal()

            elif self.phase == 'navigating':
                if self._goal_reached():
                    state = self.move_base.get_state()
                    if state == actionlib.GoalStatus.SUCCEEDED:
                        rospy.loginfo("到达 (%.1f, %.1f), 旋转搜索 %ds",
                                      self.target_x, self.target_y, int(self.search_spin_time))
                        self.nav_retry_count = 0
                        self.phase = 'searching'
                        self.phase_pub.publish(String(data='searching'))
                        self.phase_start = rospy.Time.now()
                    elif self.nav_retry_count < self.max_nav_retries:
                        self.nav_retry_count += 1
                        rospy.logwarn("导航失败 (state=%d), 重新定位后重试 (%d/%d)",
                                      state, self.nav_retry_count, self.max_nav_retries)
                        self.phase = 'localizing'
                        self.phase_pub.publish(String(data='localizing'))
                        self.phase_start = rospy.Time.now()
                    else:
                        rospy.logwarn("导航重试%d次仍失败, 放弃, 进入搜索", self.max_nav_retries)
                        self.nav_retry_count = 0
                        self.phase = 'searching'
                        self.phase_pub.publish(String(data='searching'))
                        self.phase_start = rospy.Time.now()

            elif self.phase == 'searching':
                elapsed = (rospy.Time.now() - self.phase_start).to_sec()
                if elapsed < self.search_spin_time:
                    cmd = Twist()
                    cmd.angular.z = 0.2
                    self.cmd_vel_pub.publish(cmd)
                else:
                    self.cmd_vel_pub.publish(Twist())
                    self.phase = 'idle'
                    self.phase_pub.publish(String(data='idle'))
                    rospy.loginfo("搜索超时 (%ds), 等待新指令", int(self.search_spin_time))

            rate.sleep()


if __name__ == '__main__':
    try:
        NavToTarget().run()
    except rospy.ROSInterruptException:
        pass
