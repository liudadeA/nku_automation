#!/usr/bin/env python3
"""
视觉伺服靠近瓶子: 检测框高度闭环控制, 误差±20%切换微调

目标检测框: xmin=259 ymin=114 xmax=374 ymax=471
           -> center_x=316.5  height=357

阶段:
  0: 旋转对准瓶子中心
  1: 前后移动: 粗调(0.15m/s) -> ±20%切微调(0.01m/s) -> -10%/+5%稳定0.5s完成
  2: 二次旋转对准
  5: 发布 bottle_in_pos=1 -> 触发机械臂 位姿1->位姿2
  51: 等待5s (机械臂稳定到位姿2)
  6: 开环前进 0.1m
  61: 等待5s (稳定后触发抓取)
  7: 发布 bottle_in_pos=2 -> jicheng 抓取
"""

import rospy
from std_msgs.msg import Int32
from yolov8_ros_msgs.msg import BoundingBox
from geometry_msgs.msg import Twist
import time


class VisualApproach:
    def __init__(self):
        rospy.init_node('visual_approach', anonymous=True)

        # ── 订阅 ──
        self.control_sub = rospy.Subscriber('controll_msg', Int32, self.control_callback)
        self.bottle_sub = rospy.Subscriber('/bottle_caught', BoundingBox, self.bottle_callback)

        # ── 发布 ──
        self.cmd_pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=10)
        self.bottle_in_pos_pub = rospy.Publisher('/bottle_in_pos', Int32, queue_size=10)

        # ── 目标检测框 ──
        self.target_center_x = 275
        self.target_height   = 310    

        # ── 控制参数 ──
        self.angular_speed = rospy.get_param('~angular_speed', 0.6)
        self.linear_speed  = rospy.get_param('~linear_speed', 0.20)
        self.center_threshold = 0.03
        self.fine_tune_threshold = rospy.get_param('~fine_tune_threshold', 0.50)  # ±20%切微调
        self.height_threshold_low  = rospy.get_param('~height_threshold_low', 0.10)   # -10%
        self.height_threshold_high = rospy.get_param('~height_threshold_high', 0.05)  # +5%
        self.min_angular_speed = 0.05
        self.micro_speed = rospy.get_param('~micro_speed', 0.10)
        self.open_loop_distance = rospy.get_param('~open_loop_distance', 0.15)
        self.wait_before_openloop = rospy.get_param('~wait_before_openloop', 5.0)
        self.wait_after_openloop  = rospy.get_param('~wait_after_openloop', 5.0)

        # ── 数据滤波 ──
        self.filter_size = 5
        self.center_x_history = []
        self.height_history = []
        self.bottle_center_x = 0.0
        self.bottle_height   = 0.0
        self.bottle_detected = False

        # ── 平滑控制 ──
        self.last_cmd = Twist()
        self.smoothing_factor = 0.2

        # ── 稳定检测 ──
        self.angular_stable_start = None
        self.linear_stable_start  = None

        # ── 开环阶段计时/计距 ──
        self.move_start_time = None
        self.move_distance = 0.0
        self.wait_start_time = None

        # ── 状态 ──
        self.control_state = 0
        self.control_phase = -1
        self.in_fine_tune = False

        self.rate = rospy.Rate(30)
        rospy.loginfo("VisualApproach 初始化完成")


    # ──────────────── 回调 ────────────────

    def control_callback(self, msg):
        self.control_state = msg.data
        if self.control_state == 1 and self.control_phase == -1:
            self.control_phase = 0
            self.center_x_history = []
            self.height_history = []
            self.angular_stable_start = None
            self.linear_stable_start = None
            self.move_start_time = None
            self.move_distance = 0.0
            self.wait_start_time = None
            self.in_fine_tune = False
            self.stop_robot()
            rospy.loginfo("> 收到 controll_msg=1，开始视觉伺服靠近")

    def bottle_callback(self, msg):
        self.bottle_detected = True
        cx = (msg.xmin + msg.xmax) / 2.0
        h  = msg.ymax - msg.ymin

        self.center_x_history.append(cx)
        self.height_history.append(h)

        if len(self.center_x_history) > self.filter_size:
            self.center_x_history.pop(0)
        if len(self.height_history) > self.filter_size:
            self.height_history.pop(0)

        self.bottle_center_x = sum(self.center_x_history) / len(self.center_x_history)
        self.bottle_height   = sum(self.height_history) / len(self.height_history)

    # ──────────────── 控制计算 ────────────────

    def stop_robot(self):
        cmd = Twist()
        self.cmd_pub.publish(cmd)
        rospy.sleep(0.1)

    def calc_angular_vel(self):
        if self.bottle_center_x <= 0:
            return 0.0
        deviation = (self.bottle_center_x - self.target_center_x) / self.target_center_x
        if abs(deviation) < self.center_threshold:
            return 0.0
        vel = self.angular_speed * (deviation / 0.5)
        vel = max(-self.angular_speed, min(vel, self.angular_speed))
        if abs(vel) > 0 and abs(vel) < self.min_angular_speed:
            vel = self.min_angular_speed * (1 if vel > 0 else -1)
        return vel

    def calc_linear_vel(self):
        """高度控制: 粗调->微调两段式"""
        if self.bottle_height <= 0:
            return 0.0
        lower = self.target_height * (1.0 - self.height_threshold_low)
        upper = self.target_height * (1.0 + self.height_threshold_high)
        if lower <= self.bottle_height <= upper:
            return 0.0
        # 微调用0.01, 粗调用0.15
        speed = self.micro_speed if self.in_fine_tune else self.linear_speed
        return speed if self.bottle_height < lower else -speed

    def _in_fine_zone(self):
        """是否进入微调区域 (±20%)"""
        if self.bottle_height <= 0:
            return False
        err = abs(self.bottle_height - self.target_height) / self.target_height
        return err <= self.fine_tune_threshold

    def check_angular_stable(self):
        if self.bottle_center_x <= 0:
            return False
        deviation = abs(self.bottle_center_x - self.target_center_x) / self.target_center_x
        if deviation < self.center_threshold:
            if self.angular_stable_start is None:
                self.angular_stable_start = time.time()
            elif time.time() - self.angular_stable_start >= 2.0:
                return True
        else:
            self.angular_stable_start = None
        return False

    def check_linear_stable(self):
        """阶段1完成判定: 在最终容差内且稳定0.5s"""
        if self.bottle_height <= 0:
            return False
        lower = self.target_height * (1.0 - self.height_threshold_low)
        upper = self.target_height * (1.0 + self.height_threshold_high)
        if lower <= self.bottle_height <= upper:
            if self.linear_stable_start is None:
                self.linear_stable_start = time.time()
            elif time.time() - self.linear_stable_start >= 2.0:
                return True
        else:
            self.linear_stable_start = None
        return False

    def smooth_cmd(self, cmd):
        smoothed = Twist()
        smoothed.linear.x  = self.smoothing_factor * cmd.linear.x  + \
                             (1 - self.smoothing_factor) * self.last_cmd.linear.x
        smoothed.angular.z = self.smoothing_factor * cmd.angular.z + \
                             (1 - self.smoothing_factor) * self.last_cmd.angular.z
        self.last_cmd = smoothed
        return smoothed

    # ──────────────── 主循环 ────────────────

    def run(self):
        while not rospy.is_shutdown():
            if self.control_state in [1, 2] and self.bottle_detected:

                # ── 阶段0: 旋转对准 ──
                if self.control_phase == 0:
                    ang_vel = self.calc_angular_vel()
                    cmd = Twist()
                    cmd.angular.z = -ang_vel
                    if ang_vel == 0:
                        self.cmd_pub.publish(cmd)       # 居中 → 立即停, 不衰减
                    else:
                        self.cmd_pub.publish(self.smooth_cmd(cmd))

                    if ang_vel == 0:
                        rospy.loginfo_throttle(2, "阶段0 旋转: 已居中, 等待稳定...")
                    else:
                        rospy.loginfo_throttle(2, "阶段0 旋转: ang=%.3f rad/s", cmd.angular.z)

                    if self.check_angular_stable():
                        self.stop_robot()
                        self.angular_stable_start = None
                        self.linear_stable_start = None
                        self.control_phase = 1
                        rospy.loginfo("[OK] 阶段0 完成 -> 阶段1 靠近")

                # ── 阶段1: 粗调->微调 ──
                elif self.control_phase == 1:
                    # 检测是否应切换微调 (±20%触发)
                    if not self.in_fine_tune and self._in_fine_zone():
                        self.in_fine_tune = True
                        rospy.loginfo("  |--> entering fine zone +/-%d%%, switching to micro (%.3f m/s)",
                                      int(self.fine_tune_threshold * 100), self.micro_speed)

                    lin_vel = self.calc_linear_vel()
                    cmd = Twist()
                    cmd.linear.x = lin_vel
                    if lin_vel == 0:
                        self.cmd_pub.publish(cmd)        # 到位 → 立即停
                    else:
                        self.cmd_pub.publish(self.smooth_cmd(cmd))

                    if lin_vel != 0:
                        err_pct = (self.bottle_height - self.target_height) / self.target_height * 100
                        mode = "微调" if self.in_fine_tune else "粗调"
                        rospy.loginfo_throttle(1, "阶段1 %s: h=%.0f (目标%d) 误差%+.1f%%  vel=%.3f",
                                               mode, self.bottle_height, self.target_height,
                                               err_pct, cmd.linear.x)

                    if self.check_linear_stable():
                        self.stop_robot()
                        self.angular_stable_start = None
                        self.linear_stable_start = None
                        self.in_fine_tune = False
                        self.control_phase = 2
                        err_pct = (self.bottle_height - self.target_height) / self.target_height * 100
                        rospy.loginfo("[OK] 阶段1 完成 (h=%.0f, 误差%+.1f%%) -> 阶段2 二次旋转",
                                      self.bottle_height, err_pct)

                # ── 阶段2: 二次旋转对准 ──
                elif self.control_phase == 2:
                    ang_vel = self.calc_angular_vel()
                    cmd = Twist()
                    cmd.angular.z = -ang_vel
                    if ang_vel == 0:
                        self.cmd_pub.publish(cmd)       # 居中 → 立即停
                    else:
                        self.cmd_pub.publish(self.smooth_cmd(cmd))

                    if self.check_angular_stable():
                        self.stop_robot()
                        self.angular_stable_start = None
                        self.linear_stable_start = None
                        self.control_phase = 5
                        rospy.loginfo("[OK] 阶段2 完成 -> 阶段5 发布 bottle_in_pos=1")

                # ── 阶段5: 发布=1, 等待机械臂伸出 ──
                elif self.control_phase == 5:
                    msg = Int32()
                    msg.data = 1
                    self.bottle_in_pos_pub.publish(msg)
                    rospy.loginfo(">>> 已发布 bottle_in_pos=1 (粗调完成, 机械臂伸出)")
                    self.wait_start_time = time.time()
                    self.control_phase = 51

                # ── 阶段51: 等待5s ──
                elif self.control_phase == 51:
                    elapsed = time.time() - self.wait_start_time
                    if elapsed >= self.wait_before_openloop:
                        self.wait_start_time = None
                        self.control_phase = 6
                        self.move_start_time = time.time()
                        self.move_distance = 0.0
                        rospy.loginfo("[OK] 等待 %.0fs 完成 -> 阶段6 开环前进 %.2fm",
                                      self.wait_before_openloop, self.open_loop_distance)
                    else:
                        rospy.loginfo_throttle(1, "阶段51 等待机械臂: %.1f / %.0f s",
                                               elapsed, self.wait_before_openloop)

                # ── 阶段6: 开环前进 ──
                elif self.control_phase == 6:
                    elapsed = time.time() - self.move_start_time
                    self.move_distance = self.linear_speed * 0.5 * elapsed

                    if self.move_distance < self.open_loop_distance:
                        cmd = Twist()
                        cmd.linear.x = self.linear_speed * 0.5
                        self.cmd_pub.publish(self.smooth_cmd(cmd))
                        rospy.loginfo_throttle(0.5, "阶段6 开环: 已前进 %.2f / %.2f m",
                                               self.move_distance, self.open_loop_distance)
                    else:
                        self.stop_robot()
                        self.move_start_time = None
                        self.move_distance = 0.0
                        self.wait_start_time = time.time()
                        self.control_phase = 61
                        rospy.loginfo("[OK] 阶段6 完成 (开环 %.2fm) -> 阶段61 等待 %.0fs 稳定",
                                      self.open_loop_distance, self.wait_after_openloop)

                # ── 阶段61: 等待5s ──
                elif self.control_phase == 61:
                    elapsed = time.time() - self.wait_start_time
                    if elapsed >= self.wait_after_openloop:
                        self.wait_start_time = None
                        self.control_phase = 7
                        rospy.loginfo("[OK] 等待 %.0fs 完成 -> 阶段7 发布 bottle_in_pos=2",
                                      self.wait_after_openloop)
                    else:
                        rospy.loginfo_throttle(1, "阶段61 等待稳定: %.1f / %.0f s",
                                               elapsed, self.wait_after_openloop)

                # ── 阶段7: 发布=2, 触发抓取 ──
                elif self.control_phase == 7:
                    msg = Int32()
                    msg.data = 2
                    self.bottle_in_pos_pub.publish(msg)
                    rospy.loginfo(">>> 已发布 bottle_in_pos=2 (开环完成, 触发抓取)")
                    self.control_phase = -1

            else:
                if self.control_phase != -1:
                    self.control_phase = -1
                    self.bottle_detected = False
                    self.angular_stable_start = None
                    self.linear_stable_start = None
                    self.in_fine_tune = False
                    self.move_start_time = None
                    self.wait_start_time = None
                    self.stop_robot()

            self.rate.sleep()


if __name__ == '__main__':
    try:
        tracker = VisualApproach()
        tracker.run()
    except rospy.ROSInterruptException:
        pass
