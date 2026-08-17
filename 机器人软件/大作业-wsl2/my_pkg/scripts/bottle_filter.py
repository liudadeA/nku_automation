#!/usr/bin/env python3
"""从 YOLO 检测结果中筛选瓶子，检测到立刻发布，丢失立刻停止

订阅 /detection_result (BoundingBoxes) 或 /yolov8/BoundingBoxes，
发布 /bottle_caught (BoundingBox) 单个瓶子检测框。
可通过 ~input_topic 参数切换输入话题。
"""
import rospy
from yolov8_ros_msgs.msg import BoundingBox, BoundingBoxes

class BottleFilter:
    def __init__(self):
        rospy.init_node('bottle_filter', anonymous=True)
        self.bottle_pub = rospy.Publisher('/bottle_caught', BoundingBox, queue_size=10)
        input_topic = rospy.get_param('~input_topic', '/detection_result')
        self.sub = rospy.Subscriber(input_topic, BoundingBoxes, self.callback)
        rospy.loginfo("瓶子过滤器已启动（输入: %s，实时发布，无保持）", input_topic)

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
