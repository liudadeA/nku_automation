#!/usr/bin/python3
"""
前往终点节点 - 基于 AMCL 定位 + move_base 导航.

返航策略:
  - 阶段1 (reversing): 反向回放视觉伺服阶段录制的控制序列, 回到定点导航目标点附近
  - 阶段2 (navigating): 使用 AMCL 定位 + move_base 导航前往终点

速度指令发布策略:
  - 订阅状态机 /control_state, 仅在 state=5(前往终点) 时发布速度指令
  - 其他状态不发布任何指令, 避免与其他节点竞争
"""

import threading
import rospy
import actionlib
from geometry_msgs.msg import Twist, Point, PoseStamped, Quaternion
from std_msgs.msg import Int32
from move_base_msgs.msg import MoveBaseGoal, MoveBaseAction
from tf.transformations import quaternion_from_euler

# 本节点活跃的状态机状态: 5=前往终点
ACTIVE_STATES = {5}

# 视觉伺服录制话题的发布频率 (与 visual_approach.py 一致)
APPROACH_RECORD_HZ = 30


class ReturnToOriginNode:
    def __init__(self):
        rospy.init_node('return_to_origin_node', anonymous=True)

        # ── 终点坐标参数 ──
        self.goal_x = rospy.get_param('~goal_x', 0.0)
        self.goal_y = rospy.get_param('~goal_y', 0.0)
        self.goal_yaw = rospy.get_param('~goal_yaw', 0.0)

        # ── 线程锁 ──
        self.lock = threading.Lock()

        # ── 状态 ──
        self.machine_state = -1
        self.start_position = None
        self.at_origin = False

        # ── 返航阶段: idle → reversing → navigating ──
        self.phase = 'idle'

        # ── 阶段1: 反向回放序列 ──
        self.reverse_sequence = []
        self.reverse_idx = 0

        # ── 视觉伺服录制缓存 ──
        self.approach_cmds = []

        # ── move_base Action Client ──
        self.move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("等待 move_base action server...")
        self.move_base_client.wait_for_server()
        rospy.loginfo("move_base action server 已连接")

        # ── 订阅 ──
        rospy.Subscriber('/control_state', Int32, self.state_callback)
        rospy.Subscriber('/robot_start_position', Point, self.start_position_callback)
        rospy.Subscriber('/approach_cmd_record', Twist, self.approach_cmd_callback)

        # ── 发布 ──
        self.at_origin_pub = rospy.Publisher('/robot_in_0', Int32, queue_size=10)
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=10)

        rospy.loginfo("Return to Origin Node Initialized (AMCL + move_base)")

    def state_callback(self, msg):
        """状态机状态回调: 控制本节点是否发布速度指令"""
        with self.lock:
            prev = self.machine_state
            self.machine_state = msg.data

            # 从活跃状态退出 → 停车并重置
            if prev in ACTIVE_STATES and self.machine_state not in ACTIVE_STATES:
                self.move_base_client.cancel_goal()
                self.cmd_vel_pub.publish(Twist())
                self.at_origin = False
                self.phase = 'idle'
                self.reverse_sequence = []
                self.reverse_idx = 0
                rospy.loginfo("状态机 %d→%d, 停止发布速度指令", prev, self.machine_state)

            # 进入活跃状态 → 启动返航
            if self.machine_state in ACTIVE_STATES and prev not in ACTIVE_STATES:
                self.at_origin = False
                self._start_return()

    def start_position_callback(self, msg):
        self.start_position = msg
        rospy.loginfo("接收到起始位置: x=%.3f, y=%.3f", msg.x, msg.y)

    def approach_cmd_callback(self, msg):
        """接收视觉伺服阶段录制的控制指令"""
        self.approach_cmds.append(Twist(linear=msg.linear, angular=msg.angular))

    def _start_return(self):
        """启动两阶段返航"""
        if self.approach_cmds:
            # 阶段1: 构建反向控制序列
            self.reverse_sequence = self._build_reverse_sequence(self.approach_cmds)
            self.reverse_idx = 0
            self.phase = 'reversing'
            rospy.loginfo("返航阶段1: 反向回放 %d 步 (原始录制 %d 条)",
                          len(self.reverse_sequence), len(self.approach_cmds))
        else:
            # 无录制数据, 直接进入 move_base 导航
            rospy.loginfo("无视觉伺服录制数据, 直接 move_base 返回")
            self._send_move_base_goal()

    def _build_reverse_sequence(self, cmds):
        """
        将录制的控制序列反转并取反, 用于回到导航目标点附近.
        反转: 指令顺序倒序 (先撤销最后的动作)
        取反: linear.x → -linear.x, angular.z → -angular.z
        """
        reverse_seq = []
        for cmd in reversed(cmds):
            rev = Twist()
            rev.linear.x = -cmd.linear.x
            rev.linear.y = -cmd.linear.y
            rev.linear.z = -cmd.linear.z
            rev.angular.x = -cmd.angular.x
            rev.angular.y = -cmd.angular.y
            rev.angular.z = -cmd.angular.z
            reverse_seq.append(rev)
        return reverse_seq

    def _send_move_base_goal(self):
        """阶段2: 使用 move_base 导航前往终点"""
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.header.stamp = rospy.Time.now()

        # 终点坐标: 优先使用参数, 若无则使用起点位置
        if self.start_position is not None:
            gx = self.goal_x if self.goal_x != 0.0 or self.goal_y != 0.0 else self.start_position.x
            gy = self.goal_y if self.goal_x != 0.0 or self.goal_y != 0.0 else self.start_position.y
        else:
            gx = self.goal_x
            gy = self.goal_y

        goal.target_pose.pose.position.x = gx
        goal.target_pose.pose.position.y = gy

        q = quaternion_from_euler(0, 0, self.goal_yaw * 3.14159 / 180.0)
        goal.target_pose.pose.orientation = Quaternion(*q)

        self.move_base_client.send_goal(goal, done_cb=self._goal_done_cb)
        self.phase = 'navigating'
        rospy.loginfo("返航阶段2: move_base 导航到终点 (%.2f, %.2f, %.0f°)",
                      gx, gy, self.goal_yaw)

    def _goal_done_cb(self, state, result):
        """move_base 目标完成回调"""
        with self.lock:
            if state == actionlib.GoalStatus.SUCCEEDED:
                rospy.loginfo("已到达终点!")
                self.at_origin = True
                self.at_origin_pub.publish(Int32(1))
            else:
                rospy.logwarn("move_base 导航失败 (状态=%d), 仍通知到达", state)
                self.at_origin = True
                self.at_origin_pub.publish(Int32(1))

    def run(self):
        rate_10 = rospy.Rate(10)
        rate_30 = rospy.Rate(APPROACH_RECORD_HZ)

        while not rospy.is_shutdown():
            with self.lock:
                if self.machine_state not in ACTIVE_STATES:
                    pass
                elif self.at_origin:
                    pass
                elif self.phase == 'reversing':
                    # ── 阶段1: 反向回放视觉伺服控制序列 ──
                    if self.reverse_idx < len(self.reverse_sequence):
                        self.cmd_vel_pub.publish(self.reverse_sequence[self.reverse_idx])
                        self.reverse_idx += 1
                        rospy.loginfo_throttle(2, "反向回放: 步骤 %d/%d",
                                               self.reverse_idx, len(self.reverse_sequence))
                    else:
                        self.cmd_vel_pub.publish(Twist())
                        rospy.loginfo("反向回放完成, 切换到 move_base 返回")
                        self._send_move_base_goal()

                # 阶段2 由 move_base action 回调处理, 无需在主循环中操作

            # 根据阶段选择不同频率
            if self.phase == 'reversing':
                rate_30.sleep()
            else:
                rate_10.sleep()


if __name__ == '__main__':
    try:
        node = ReturnToOriginNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
