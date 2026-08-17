#!/usr/bin/env python3
import rospy
from std_msgs.msg import Int32, String
from yolov8_ros_msgs.msg import BoundingBox
from geometry_msgs.msg import Twist
from collections import deque
import time

class BottleController:
    def __init__(self):
        rospy.init_node('controll_core', anonymous=True)

        # 变量必须在订阅之前创建，避免回调竞态
        self.control_msg = Int32()
        self.control_msg.data = -1
        self.last_logged = -1

        self.control_pub = rospy.Publisher('/controll_msg', Int32, queue_size=10)
        self.speech_pub = rospy.Publisher('/speech_feedback', Int32, queue_size=10)
        self.cmd_pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=10)
        self.tts_pub = rospy.Publisher('/tts_text', String, queue_size=10)

        self.bottle_sub = rospy.Subscriber('/bottle_caught', BoundingBox, self.bottle_callback)
        self.bottle_in_pos_sub = rospy.Subscriber('/bottle_in_pos', Int32, self.bottle_in_pos_callback)
        self.jixiebi_in_pos_sub = rospy.Subscriber('/jixiebi_in_pose', Int32, self.jixiebi_in_pos_callback)
        self.voice_cmd_sub = rospy.Subscriber('/voice_command', Int32, self.voice_cmd_callback)
        self.robot_in_0_sub = rospy.Subscriber('/robot_in_0', Int32, self.robot_in_0_callback)
        self.navi_phase_sub = rospy.Subscriber('/navi_phase', String, self.navi_phase_callback)
        self.last_logged = -1
        self.navi_phase = 'idle'  # 只在 searching 时允许瓶子触发状态切换

        # ── 瓶子检测防抖: 10帧中≥5帧检测到才切换 ──
        self.detect_window = deque(maxlen=10)  # 最近10帧: True=检测到, False=未检测到
        self.bottle_seen_this_frame = False    # 当前帧是否看到瓶子
        self.bottle_detected = False           # 防抖确认后的检测结果
        self.detect_start_time = None          # 首次检测到瓶子的时间 (5s超时)

        self.rate = rospy.Rate(10)

    def _set_state(self, new_state):
        if self.control_msg.data != new_state:
            self.control_msg.data = new_state
            rospy.loginfo("状态 → %d", new_state)
            # 切出搜索态时清空检测窗口
            if new_state != 0:
                self.detect_window.clear()
                self.bottle_seen_this_frame = False
                self.bottle_detected = False
                self.detect_start_time = None
            # 检测到瓶子 → 急停
            if new_state == 1:
                self.cmd_pub.publish(Twist())
                rospy.loginfo("急停! 检测到瓶子, 切换视觉对准")

    def navi_phase_callback(self, msg):
        self.navi_phase = msg.data

    def voice_cmd_callback(self, msg):
        if msg.data == 0:
            self._set_state(0)  # 触发任务: navi 先定位→导航→搜索
        elif msg.data == 1 and self.control_msg.data == 4:
            self._set_state(-1)  # 返航确认: 回到原点后说"好"/"谢" → 空闲

    def bottle_callback(self, msg):
        """状态0搜索阶段 或 状态4返航前, 检测到瓶子立即停车"""
        if (self.control_msg.data == 0 and self.navi_phase == 'searching') or \
           self.control_msg.data == 4:
            self.cmd_pub.publish(Twist())
            if self.detect_start_time is None:
                self.detect_start_time = time.time()
            self.bottle_seen_this_frame = True

    def _eval_detection(self):
        """在主循环中每帧调用，统计滑动窗口内检测到的比例"""
        self.detect_window.append(self.bottle_seen_this_frame)
        self.bottle_seen_this_frame = False

        if (self.control_msg.data == 0 and self.navi_phase == 'searching') or \
           self.control_msg.data == 4:
            if self.detect_start_time is not None:
                if time.time() - self.detect_start_time > 5.0:
                    rospy.loginfo("瓶子确认超时 (5s), 放弃, 继续搜索")
                    self.detect_window.clear()
                    self.bottle_seen_this_frame = False
                    self.bottle_detected = False
                    self.detect_start_time = None
                    return

            detected_count = sum(1 for d in self.detect_window if d)
            if detected_count >= 5 and not self.bottle_detected:
                self.bottle_detected = True
                self.detect_start_time = None
                self._set_state(1)
                rospy.loginfo("瓶子检测已确认 (%d/10 帧), 切换到视觉对准", detected_count)
            elif detected_count <= 2 and self.bottle_detected:
                self.bottle_detected = False
                rospy.loginfo("瓶子检测丢失 (%d/10 帧), 重置", detected_count)

    def bottle_in_pos_callback(self, msg):
        if msg.data == 1 and self.control_msg.data == 1:
            self._set_state(2)  # 对准完成 → 机械臂伸出
        elif msg.data == 2 and self.control_msg.data == 2:
            self._set_state(3)  # 靠近完成 → 夹爪闭合

    def jixiebi_in_pos_callback(self, msg):
        if self.control_msg.data == 3:
            self._set_state(4)  # 抓取完成 → 返航

    def robot_in_0_callback(self, msg):
        if msg.data == 1 and self.control_msg.data == 4:
            self.tts_pub.publish(String(data="已拿到"))
            rospy.loginfo("已回到原点, TTS: 已拿到, 等待语音确认 ('好'/'谢')")

    def run(self):
        while not rospy.is_shutdown():
            self._eval_detection()  # 每帧评估瓶子检测结果
            self.control_pub.publish(self.control_msg)
            if self.control_msg.data != self.last_logged:
                rospy.loginfo("controll_msg: %d", self.control_msg.data)
                self.last_logged = self.control_msg.data
            self.rate.sleep()

if __name__ == '__main__':
    try:
        BottleController().run()
    except rospy.ROSInterruptException:
        pass
