#!/usr/bin/env python3
import rospy
import math
import actionlib
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, Point, Quaternion
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler

ACTION_MOVE_BASE = 'move_base'
FRAME_MAP = 'map'

class NavToPoint:
    def __init__(self):
        # 注册关闭回调
        rospy.on_shutdown(self.clean_up)

        # 创建 move_base 客户端
        self.move_base = actionlib.SimpleActionClient(ACTION_MOVE_BASE, MoveBaseAction)
        rospy.loginfo('Waiting for move_base action server ...')
        self.move_base.wait_for_server(rospy.Duration(120))
        rospy.loginfo('Connected to move_base server')

        self.map_robot_pose = [0.0, 0.0, 0.0]
        self.move_base_running = False
        self.blocking = True
        rospy.loginfo('Ready to go ...')
        rospy.sleep(1)

    def goto(self, target, blocking=True):
        """
        target: [x, y, yaw_degree]
        """
        self.blocking = blocking
        x, y, yaw_deg = target
        yaw = math.radians(yaw_deg)

        # 欧拉角转四元数
        q = quaternion_from_euler(0.0, 0.0, yaw)
        target_pose = Pose(
            position=Point(x, y, 0.0),
            orientation=Quaternion(*q)
        )

        self.goal = MoveBaseGoal()
        self.goal.target_pose.header.frame_id = FRAME_MAP
        self.goal.target_pose.header.stamp = rospy.Time.now()
        self.goal.target_pose.pose = target_pose

        rospy.loginfo('Sending navigation goal...')
        self.move_base.send_goal(self.goal)
        self.move_base_running = True

        if blocking:
            rospy.loginfo('Waiting for result...')
            finished = self.move_base.wait_for_result()
            self.move_base_running = False

            if not finished:
                rospy.logerr('Action server not available!')
                return False

            state = self.move_base.get_state()
            result = self.move_base.get_result()
            rospy.loginfo('Navigation state: %d, result: %s' % (state, result))
            return state == GoalStatus.SUCCEEDED
        return True

    def clean_up(self):
        rospy.loginfo('Shutting down navigation ...')
        if self.move_base_running:
            self.move_base.cancel_goal()

if __name__ == '__main__':
    rospy.init_node('nav_to_point')
    nav = NavToPoint()
    # 目标：x=3, y=0, 航向角90度
    nav.goto([3.0, 0.0, 90.0])
