#!/usr/bin/env python3
"""从 YOLO 检测结果中筛选瓶子，检测到立刻发布，丢失立刻停止"""
import rospy
from yolov8_ros_msgs.msg import BoundingBox, BoundingBoxes

class BottleFilter:
    def __init__(self):
        rospy.init_node('bottle_filter', anonymous=True)
        self.bottle_pub = rospy.Publisher('/bottle_caught', BoundingBox, queue_size=10)
        self.sub = rospy.Subscriber('/yolov8/BoundingBoxes', BoundingBoxes, self.callback)
        rospy.loginfo("瓶子过滤器已启动（实时发布，无保持）")

    def callback(self, msg):
        for box in msg.bounding_boxes:
            if box.Class == 'bottle' and box.probability > 0.15:
                self.bottle_pub.publish(box)
                return

if __name__ == '__main__':
    try:
        BottleFilter()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
