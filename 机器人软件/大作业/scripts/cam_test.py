#!/usr/bin/env python3
from cv_bridge import CvBridge, CvBridgeError
import rospy
import cv2
import time
from sensor_msgs.msg import Image

def callback(data):
    try:
        # 初始化 CvBridge，用于ROS图像和OpenCV图像的转换
        bridge = CvBridge()
        # 将ROS的sensor_msgs/Image消息转为OpenCV的BGR8格式图像
        cv_image = bridge.imgmsg_to_cv2(data, "bgr8")
        # 显示图像窗口
        cv2.imshow("Image Window", cv_image)
        # 等待1ms，确保窗口正常刷新
        cv2.waitKey(1)
    except CvBridgeError as e:
        print(e)

if __name__ == '__main__':
    # 初始化ROS节点，节点名为take_photo
    rospy.init_node('take_photo', anonymous=False)
    # 订阅摄像头话题（与usb_cam发布的话题对应）
    img_topic = '/usb_cam/image_raw'
    image_sub = rospy.Subscriber(img_topic, Image, callback)
    # 节点持续运行10秒，接收图像数据
    rospy.sleep(10)
    # 关闭所有OpenCV窗口
    cv2.destroyAllWindows()
