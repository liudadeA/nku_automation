#!/usr/bin/python3
"""
导航到固定目标, 到达后通知状态机.
基于 AMCL 定位 + move_base 导航.

定位策略:
  - 使用 AMCL (Adaptive Monte Carlo Localization) 在已知地图上定位
  - 启动时通过 global_localize.py 发布大协方差初始位姿, 粒子遍布全图
  - 机器人移动后粒子逐渐收敛到实际位置

导航策略:
  - 使用 move_base action server 进行路径规划和导航
  - 向 move_base 发送目标点作为 MoveBaseGoal
  - move_base 自动完成全局/局部路径规划和避障

速度指令发布策略:
  - 订阅状态机 /control_state, 仅在 state=0(导航) 时发送 move_base 目标
  - 到达目标后发布 navi_status=1, 不执行搜索 (搜索由 search_spin.py 在 state=1 处理)
  - 其他状态不发送任何目标, 避免与其他节点竞争
"""
import threading
import rospy
import actionlib
from geometry_msgs.msg import Point, PoseStamped, Quaternion
from std_msgs.msg import Int32
from move_base_msgs.msg import MoveBaseGoal, MoveBaseAction
from tf.transformations import quaternion_from_euler

# 本节点活跃的状态机状态: 0=导航
ACTIVE_STATES = {0}


class NavToTarget:
    def __init__(self):
        rospy.init_node('navi_to_target', anonymous=True)

        # ── 导航目标参数 ──
        self.target_x = rospy.get_param('~target_x', 0.0)
        self.target_y = rospy.get_param('~target_y', 0.0)
        self.target_yaw = rospy.get_param('~target_yaw', 0.0)  # 目标朝向(度)

        # ── 线程锁 ──
        self.lock = threading.Lock()

        # ── 状态 ──
        self.machine_state = -1
        self.navigating = False

        # ── move_base Action Client ──
        self.move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("等待 move_base action server...")
        self.move_base_client.wait_for_server()
        rospy.loginfo("move_base action server 已连接")

        # ── 发布 ──
        self.start_pos_pub = rospy.Publisher('/robot_start_position', Point, queue_size=10)
        self.navi_status_pub = rospy.Publisher('/navi_status', Int32, queue_size=10)

        # ── 订阅 AMCL 位姿 (用于记录起点) ──
        rospy.Subscriber('/amcl_pose', PoseStamped, self.amcl_pose_callback)
        self.current_pose = None

        # ── 订阅 ──
        rospy.Subscriber('/control_state', Int32, self.state_callback)

        rospy.loginfo("NavToTarget 就绪 (AMCL + move_base 模式)")
        rospy.loginfo("目标: (%.1f, %.1f, %.0f°)",
                      self.target_x, self.target_y, self.target_yaw)

    def amcl_pose_callback(self, msg):
        """AMCL 位姿回调: 记录当前位置"""
        self.current_pose = msg.pose

    def state_callback(self, msg):
        """状态机状态回调: 控制本节点是否发送导航目标"""
        with self.lock:
            prev = self.machine_state
            self.machine_state = msg.data

            # 从活跃状态退出 → 取消导航目标
            if prev in ACTIVE_STATES and self.machine_state not in ACTIVE_STATES:
                self.move_base_client.cancel_goal()
                self.navigating = False
                rospy.loginfo("状态机 %d→%d, 取消导航目标", prev, self.machine_state)

            # 进入活跃状态 → 发送 move_base 目标
            if self.machine_state == 0 and prev not in ACTIVE_STATES:
                self._send_goal()

    def _send_goal(self):
        """向 move_base 发送导航目标"""
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = self.target_x
        goal.target_pose.pose.position.y = self.target_y

        q = quaternion_from_euler(0, 0, rospy.get_param('~target_yaw', 0.0) * 3.14159 / 180.0)
        goal.target_pose.pose.orientation = Quaternion(*q)

        # 记录起点位置
        if self.current_pose is not None:
            p = Point(
                x=self.current_pose.position.x,
                y=self.current_pose.position.y
            )
            self.start_pos_pub.publish(p)
            rospy.loginfo("记录起点: (%.2f, %.2f)", p.x, p.y)

        self.move_base_client.send_goal(goal, done_cb=self._goal_done_cb)
        self.navigating = True
        rospy.loginfo("已发送 move_base 目标: (%.1f, %.1f, %.0f°)",
                      self.target_x, self.target_y, self.target_yaw)

    def _goal_done_cb(self, state, result):
        """move_base 目标完成回调"""
        with self.lock:
            self.navigating = False
            if state == actionlib.GoalStatus.SUCCEEDED:
                rospy.loginfo("到达目标 (%.1f, %.1f)", self.target_x, self.target_y)
                self.navi_status_pub.publish(Int32(1))
            else:
                rospy.logwarn("导航失败 (状态=%d), 仍通知状态机继续", state)
                self.navi_status_pub.publish(Int32(1))

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    try:
        NavToTarget().run()
    except rospy.ROSInterruptException:
        pass
