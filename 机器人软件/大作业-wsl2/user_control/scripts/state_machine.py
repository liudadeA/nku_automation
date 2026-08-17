#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态机主控模块 - 机器人控制流程的核心状态机

新流程: 待命 → 定点导航 → 搜索目标 → 视觉伺服靠近 → 机械臂伸出 →
       机械臂抓取 → 返回起点 → 完成 → 待命

状态定义:
  -1: 系统待命
   0: 定点导航 (navi.py 导航到目标点)
   1: 搜索目标 (navi.py 旋转搜索, 等待 YOLO 检测)
   2: 视觉伺服靠近 (visual_approach.py 靠近瓶子)
   3: 机械臂伸出 (visual_approach.py 触发, jicheng.py 伸出)
   4: 机械臂抓取 (jicheng.py 闭合夹爪并抬起)
   5: 返回起点 (back_2_zero.py 导航返回)
   6: 全部任务完成

通信话题:
  订阅:
    /user_command       (Int32)         - 用户命令（语音/键盘输入）
    /detection_result   (BoundingBoxes) - YOLO检测结果
    /navi_status        (Int32)         - 导航状态 (1=到达目标点 2=搜索超时)
    /bottle_in_pos      (Int32)         - 瓶子到位信号 (1=粗调完成 2=开环完成)
    /jixiebi_in_pose    (Int32)         - 机械臂到位信号 (4=抓取完成)
    /robot_in_0         (Int32)         - 回到原点信号 (1=已到达)
  发布:
    /control_state      (Int32)         - 当前状态 (兼容旧模块)
    /controll_msg       (Int32)         - 控制指令 (驱动 my_pkg 脚本)
    /voice_feedback_cmd (Int32)         - 语音反馈指令
"""

import rospy
from std_msgs.msg import Int32
from yolov8_ros_msgs.msg import BoundingBoxes


# 语音反馈消息定义
FEEDBACK = {
    -1: "系统已就绪，等待指令",
    0:  "开始定点导航",
    1:  "到达目标点，开始搜索",
    2:  "发现目标，开始靠近",
    3:  "机械臂伸出",
    4:  "正在抓取",
    5:  "抓取完成，正在返回起点",
    6:  "全部任务已完成",
}


class StateMachine:
    def __init__(self):
        rospy.init_node('state_machine', anonymous=True)

        # === 状态变量 ===
        self.state = -1
        self.prev_state = -1
        self.command_received = False
        self.target_detected = False

        # === 状态首次进入标志（只触发一次语音反馈） ===
        self.state_first_trigger = {s: True for s in range(-1, 7)}

        # === 发布器 ===
        self.state_pub = rospy.Publisher('/control_state', Int32, queue_size=10)
        self.controll_pub = rospy.Publisher('/controll_msg', Int32, queue_size=10)
        self.feedback_pub = rospy.Publisher('/voice_feedback_cmd', Int32, queue_size=10)

        # === 订阅器 ===
        self.cmd_sub = rospy.Subscriber('/user_command', Int32, self.cmd_callback, queue_size=10)
        self.detection_sub = rospy.Subscriber('/detection_result', BoundingBoxes,
                                              self.detection_callback, queue_size=10)
        self.navi_status_sub = rospy.Subscriber('/navi_status', Int32,
                                                self.navi_status_callback, queue_size=10)
        self.bottle_pos_sub = rospy.Subscriber('/bottle_in_pos', Int32,
                                               self.bottle_pos_callback, queue_size=10)
        self.arm_pos_sub = rospy.Subscriber('/jixiebi_in_pose', Int32,
                                            self.arm_pos_callback, queue_size=10)
        self.robot_home_sub = rospy.Subscriber('/robot_in_0', Int32,
                                               self.robot_home_callback, queue_size=10)

        self.rate = rospy.Rate(10)
        rospy.loginfo("[StateMachine] 状态机已初始化，状态: 待命(-1)")

    # ---------- 回调函数 ----------
    def cmd_callback(self, msg):
        cmd = msg.data
        rospy.loginfo("[StateMachine] 收到用户命令: %d", cmd)

        if cmd == 0 and self.state == -1:
            self.command_received = True
            rospy.loginfo("[StateMachine] 收到启动指令")
        elif cmd == 1 and self.state >= 0:
            rospy.loginfo("[StateMachine] 收到停止指令")
            self._transition_to(-1)
            self._publish_controll_msg(-1)

    def detection_callback(self, msg):
        if self.state != 1:
            return
        boxes = msg.bounding_boxes
        if boxes:
            target_boxes = [b for b in boxes if b.Class == 'bottle']
            if target_boxes and not self.target_detected:
                self.target_detected = True
                rospy.loginfo("[StateMachine] YOLO检测到目标! 共%d个瓶子", len(target_boxes))
                self._transition_to(2)
                self._publish_controll_msg(1)  # 触发 visual_approach.py

    def navi_status_callback(self, msg):
        if msg.data == 1 and self.state == 0:
            rospy.loginfo("[StateMachine] 导航到达目标点，开始搜索")
            self._transition_to(1)
        elif msg.data == 2 and self.state == 1:
            rospy.logwarn("[StateMachine] 搜索超时，未找到目标")
            self._transition_to(-1)
            self._publish_controll_msg(-1)

    def bottle_pos_callback(self, msg):
        if msg.data == 1 and self.state == 2:
            rospy.loginfo("[StateMachine] 瓶子粗调完成，机械臂伸出")
            self._transition_to(3)
            self._publish_controll_msg(2)  # 触发 jicheng.py 伸出
        elif msg.data == 2 and self.state == 3:
            rospy.loginfo("[StateMachine] 开环完成，触发抓取")
            self._transition_to(4)
            self._publish_controll_msg(3)  # 触发 jicheng.py 抓取

    def arm_pos_callback(self, msg):
        if msg.data == 4 and self.state == 4:
            rospy.loginfo("[StateMachine] 机械臂抓取完成，返回起点")
            self._transition_to(5)
            self._publish_controll_msg(4)  # 触发 back_2_zero.py

    def robot_home_callback(self, msg):
        if msg.data == 1 and self.state == 5:
            rospy.loginfo("[StateMachine] 机器人已回到起点")
            self._transition_to(6)

    # ---------- 状态转换 ----------
    def _transition_to(self, new_state):
        if new_state == self.state:
            return
        self.prev_state = self.state
        self.state = new_state
        rospy.loginfo("[StateMachine] 状态转换: %d -> %d", self.prev_state, self.state)

        # 发布状态
        state_msg = Int32()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)

        # 首次进入某状态时发布语音反馈
        if self.state_first_trigger.get(self.state, False):
            self._publish_feedback(self.state)
            self.state_first_trigger[self.state] = False

    def _publish_controll_msg(self, value):
        msg = Int32()
        msg.data = value
        self.controll_pub.publish(msg)
        rospy.loginfo("[StateMachine] 发布 controll_msg=%d", value)

    def _publish_feedback(self, state_id):
        msg = Int32()
        msg.data = state_id
        self.feedback_pub.publish(msg)
        text = FEEDBACK.get(state_id, "状态 %d" % state_id)
        rospy.loginfo("[StateMachine] 语音反馈: %s", text)

    # ---------- 状态机逻辑 ----------
    def run(self):
        rospy.loginfo("[StateMachine] 状态机运行中，等待指令...")

        while not rospy.is_shutdown():
            if self.state == -1:
                if self.command_received:
                    self.command_received = False
                    self.target_detected = False
                    self._transition_to(0)
                    self._publish_controll_msg(0)  # 触发 navi.py 导航

            elif self.state == 6:
                rospy.loginfo("[StateMachine] 任务完成，5秒后重置为待命状态")
                rospy.sleep(5)
                self.state_first_trigger = {s: True for s in self.state_first_trigger}
                self._transition_to(-1)
                self._publish_controll_msg(-1)

            self.rate.sleep()


if __name__ == '__main__':
    try:
        StateMachine().run()
    except rospy.ROSInterruptException:
        pass
