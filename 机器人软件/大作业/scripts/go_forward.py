#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist

if __name__ == '__main__':
    rospy.init_node('GoForward', anonymous=False)
    cmd_vel = rospy.Publisher('cmd_vel_mux/input/navi', Twist, queue_size=10)
    r = rospy.Rate(10)
    move_cmd = Twist()
    move_cmd.linear.x = 0.2
    move_cmd.angular.z = 0

    while not rospy.is_shutdown():
        cmd_vel.publish(move_cmd)
        r.sleep()
