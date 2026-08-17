#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
搜索旋转节点 - 在状态机 state=1 时旋转搜索水瓶

速度指令发布策略:
  - 订阅状态机 /control_state, 仅在 state=1(搜索) 时发布旋转速度指令
  - 超时后发布 navi_status=2 通知状态机搜索失败
  - 其他状态不发布任何指令, 避免与其他节点竞争
"""
import rospy
import threading
import numpy as np
from geometry_msgs.msg import Twist
from std_msgs.msg import Int32
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

# 本节点活跃的状态机状态: 1=搜索
ACTIVE_STATES = {1}


class SearchSpin:
    def __init__(self):
        rospy.init_node('search_spin', anonymous=True)

        # ── 参数 ──
        self.spin_speed = rospy.get_param('~spin_speed', 0.4)
        self.search_timeout = rospy.get_param('~search_timeout', 30.0)

        # ── 状态 ──
        self.machine_state = -1
        self.spinning = False
        self.spin_start_time = None

        # ── 线程锁 ──
        self.lock = threading.Lock()

        # ── 发布 ──
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=10)
        self.navi_status_pub = rospy.Publisher('/navi_status', Int32, queue_size=10)

        # ── 订阅 ──
        rospy.Subscriber('/control_state', Int32, self.state_callback)

        rospy.loginfo("SearchSpin 就绪 (仅 state=1 时旋转搜索)")

    def state_callback(self, msg):
        """状态机状态回调"""
        with self.lock:
            prev = self.machine_state
            self.machine_state = msg.data

            # 进入搜索状态 → 开始旋转
            if self.machine_state in ACTIVE_STATES and prev not in ACTIVE_STATES:
                self.spinning = True
                self.spin_start_time = rospy.Time.now()
                rospy.loginfo("状态机→%d, 开始旋转搜索", self.machine_state)

            # 从搜索状态退出 → 停车
            if prev in ACTIVE_STATES and self.machine_state not in ACTIVE_STATES:
                self.cmd_vel_pub.publish(Twist())
                self.spinning = False
                rospy.loginfo("状态机 %d→%d, 停止旋转搜索", prev, self.machine_state)

    def run(self):
        rate = rospy.Rate(10)

        while not rospy.is_shutdown():
            with self.lock:
                if self.machine_state not in ACTIVE_STATES:
                    pass
                elif self.spinning:
                    elapsed = (rospy.Time.now() - self.spin_start_time).to_sec()
                    if elapsed < self.search_timeout:
                        cmd = Twist()
                        cmd.angular.z = self.spin_speed
                        self.cmd_vel_pub.publish(cmd)
                    else:
                        self.cmd_vel_pub.publish(Twist())
                        self.spinning = False
                        self.navi_status_pub.publish(Int32(2))
                        rospy.loginfo("搜索超时 (%ds), 通知状态机", int(self.search_timeout))

            rate.sleep()


if __name__ == '__main__':
    try:
        SearchSpin().run()
    except rospy.ROSInterruptException:
        pass
