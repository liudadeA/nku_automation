#!/usr/bin/env python3
"""延迟3秒后发布大协方差初始位姿，触发 AMCL 全局定位"""
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped

rospy.init_node('global_localize', anonymous=True)
rospy.sleep(3)

msg = PoseWithCovarianceStamped()
msg.header.frame_id = 'map'
msg.header.stamp = rospy.Time.now()
msg.pose.pose.position.x = 0
msg.pose.pose.position.y = 0
msg.pose.pose.orientation.w = 1.0
# 20m位置不确定, 360°朝向不确定 → 粒子遍布全图
msg.pose.covariance[0] = 400.0   # xx
msg.pose.covariance[7] = 400.0   # yy
msg.pose.covariance[35] = 6.28   # aa

pub = rospy.Publisher('/initialpose', PoseWithCovarianceStamped, queue_size=1, latch=True)
rospy.sleep(0.5)
pub.publish(msg)
rospy.loginfo("全局定位已触发 (协方差=20m, 360°), 移动机器人即可收敛")
