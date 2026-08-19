#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float64, Int32
from dynamixel_msgs.msg import JointState
import time

class ArmController:
    def __init__(self):
        rospy.init_node('arm_pose_controller')

        # 创建关节控制发布者
        self.joints = [
            rospy.Publisher(f'/motor{i}_controller/command', Float64, queue_size=10)
            for i in range(1, 6)
        ]

        # 读取实际位置
        self.actual_positions = {i: None for i in range(1, 6)}
        for i in range(1, 6):
            rospy.Subscriber(f'/motor{i}_controller/state', JointState,
                             lambda msg, m=i: self._state_cb(m, msg))

        # 定义四个位姿:
        #   位姿1: 伸出预抓取，夹爪张开
        #   位姿2: 下探靠近瓶子，夹爪张开
        #   位姿3: 下探位置不变，夹爪闭合抓取
        #   位姿4: 收回抬起，夹爪保持闭合(搬运)
        self.poses = [
            [1.6618, 2.5936, -2.3933, 1.7508,  0.6321],   # 索引0 - 位姿1
            [1.6618, 2.5936,  0.9363, -1.5008,  0.6332],   # 索引1 - 位姿2
            [1.6618, 2.5936,  0.9363, -1.5008, 0.1332],   # 索引2 - 位姿3 (夹爪闭合)
            [1.6618, 2.5936, -2.3933, 1.7508, 0.1321]    # 索引3 - 位姿4
        ]

        # 控制参数
        self.rate = rospy.Rate(10)  # 控制频率
        self.wait_grip  = rospy.get_param('~wait_grip', 2.0)   # 下探到位→闭合夹爪等待 s
        self.wait_lift  = rospy.get_param('~wait_lift', 2.0)   # 闭合→抬起等待 s

        # 状态变量
        self.current_pose_index = 0     # 默认从位姿1开始
        self.prev_pose_index = 0        # 记录上一个位姿(用于插值)
        self.next_pose_index = 0        # 下一个目标位姿
        self.target_pose = self.poses[self.current_pose_index]
        self.is_moving = False
        self.wait_start_time = None

        # 控制信号状态
        self.received_2 = False         # 收到过controll_msg=2
        self.received_3 = False         # 收到过controll_msg=3
        self.pose2_reached = False      # 是否已到达位姿2
        self.pose3_reached = False      # 是否已到达位姿3
        self.pose4_reached = False      # 是否已到达位姿4

        # 订阅控制消息
        self.control_sub = rospy.Subscriber('controll_msg', Int32, self.control_callback)

        # 发布位姿到达消息
        self.pose_reached_pub = rospy.Publisher('jixiebi_in_pose', Int32, queue_size=10)

        # 初始化：等待所有电机控制器就绪 (最长5s)
        rospy.loginfo("等待 Dynamixel 控制器就绪...")
        start = time.time()
        while not rospy.is_shutdown():
            if all(self.actual_positions[i] is not None for i in range(1, 6)):
                rospy.loginfo("全部电机就绪 (%.1fs)", time.time() - start)
                break
            if time.time() - start > 5.0:
                rospy.logwarn("等待超时 (5s), 仍然尝试初始化")
                break
            rospy.sleep(2.0)
        self.move_to_pose(self.poses[0])
        rospy.loginfo("机械臂已初始化为位姿1（预抓取伸出，夹爪张开），等待控制指令...")

    def control_callback(self, msg):
        """控制状态回调函数"""
        # 状态切回→1时重置, 允许重复抓取
        if msg.data == 1:
            self.received_2 = False
            self.received_3 = False
            self.pose2_reached = False
            self.pose3_reached = False
            self.pose4_reached = False
            self.current_pose_index = 0  # 回到位姿1

        if msg.data == 2 and not self.received_2:
            # 第一次收到controll_msg=2: 位姿1 → 位姿2 (下探)
            self.received_2 = True
            self.prev_pose_index = self.current_pose_index  # 保存当前位置
            self.next_pose_index = 1
            self.start_move()
            rospy.loginfo("收到controll_msg=2: 位姿1 → 位姿2 (下探)")

        elif msg.data == 3 and not self.received_3:
            # 第一次收到controll_msg=3: 位姿2等待10秒后→位姿3
            if self.received_2:
                self.received_3 = True
                self.wait_start_time = time.time()
                rospy.loginfo("收到controll_msg=3: 位姿2保持%.0fs后闭合夹爪...", self.wait_grip)

    def _state_cb(self, motor_id, msg):
        self.actual_positions[motor_id] = msg.current_pos

    def start_move(self):
        """开始移动到目标位姿"""
        self.target_pose = self.poses[self.next_pose_index]
        self.is_moving = True
        self.wait_start_time = None

    def move_to_pose(self, pose):
        """从 prev_pose_index 平滑插值移动到目标位姿, 完成后验证"""
        current_angles = self.poses[self.prev_pose_index]  # 用保存的旧位姿
        self._do_move(current_angles, pose)
        self._verify_pose(pose, current_angles)

    def _do_move(self, from_angles, to_angles):
        """执行插值移动"""
        delta_angles = [t - f for t, f in zip(to_angles, from_angles)]
        steps = max(1, int(abs(max(delta_angles, key=abs)) * 10))
        rospy.loginfo("插值移动: steps=%d, delta=%s", steps,
                      ' '.join('%.3f' % d for d in delta_angles))
        for step in range(steps + 1):
            if rospy.is_shutdown():
                break
            t = float(step) / steps
            current_step = [f + d * t for f, d in zip(from_angles, delta_angles)]
            for i, angle in enumerate(current_step):
                msg = Float64()
                msg.data = angle
                self.joints[i].publish(msg)
            self.rate.sleep()

    def _verify_pose(self, target, fallback):
        """读取实际位置, 任一关节偏差>0.2rad则从当前位置重试 (最多3次)"""
        rospy.sleep(0.5)  # 等状态更新
        for retry in range(3):
            max_err = 0
            actuals = []
            for i, target_angle in enumerate(target):
                actual = self.actual_positions.get(i + 1)
                if actual is None:
                    rospy.logwarn("电机%d 无状态数据, 跳过验证", i + 1)
                    return
                actuals.append(actual)
                max_err = max(max_err, abs(actual - target_angle))
            if max_err <= 0.2:
                rospy.loginfo("位姿验证通过 (最大偏差 %.3f rad)", max_err)
                return
            rospy.logwarn("位姿偏差 %.3f > 0.2, 重试 %d/3", max_err, retry + 1)
            self._do_move(actuals, target)  # 从实际位置再移到目标

    def run(self):
        """主控制循环"""
        while not rospy.is_shutdown():
            if self.is_moving:
                self.move_to_pose(self.target_pose)
                self.current_pose_index = self.next_pose_index  # 移动完成后更新当前索引
                self.is_moving = False
                rospy.loginfo("已到达位姿 %d (poses[%d])", self.current_pose_index + 1, self.current_pose_index)

                # 到达位姿2后标记，等待controll_msg=3触发下一段等待
                if self.current_pose_index == 1 and not self.pose2_reached:
                    self.pose2_reached = True
                    rospy.loginfo("已到达位姿2（下探），等待controll_msg=3...")

                # 到达位姿3后等待 → 位姿4
                if self.current_pose_index == 2 and not self.pose3_reached:
                    self.pose3_reached = True
                    self.wait_start_time = time.time()
                    rospy.loginfo("已到达位姿3（夹爪闭合），%.0fs后抬起到位姿4...", self.wait_lift)

            # ── 等待1: 位姿2收到controll_msg=3后，等待10秒 → 位姿3 ──
            if (self.current_pose_index == 1 and self.received_3
                    and not self.pose3_reached and self.wait_start_time is not None):
                elapsed = time.time() - self.wait_start_time
                if elapsed >= self.wait_grip:
                    self.prev_pose_index = self.current_pose_index  # 保存当前(位姿2)
                    self.next_pose_index = 2                         # 目标是位姿3
                    self.start_move()
                    rospy.loginfo("%.0fs 倒计时结束: 位姿2 → 位姿3 (夹爪闭合)", self.wait_grip)

            # ── 等待2: 位姿3保持10秒后 → 位姿4, 发布完成信号 ──
            if (self.current_pose_index == 2 and self.pose3_reached
                    and not self.pose4_reached and self.wait_start_time is not None):
                elapsed = time.time() - self.wait_start_time
                if elapsed >= self.wait_lift:
                    self.prev_pose_index = self.current_pose_index  # 保存当前(位姿3)
                    self.next_pose_index = 3                         # 目标是位姿4
                    self.start_move()
                    self.pose4_reached = True
                    rospy.loginfo("%.0fs 倒计时结束: 位姿3 → 位姿4 (抬起搬运)", self.wait_lift)

                    # 到达位姿4后发布完成信号
                    msg = Int32()
                    msg.data = 4
                    self.pose_reached_pub.publish(msg)
                    rospy.loginfo("已发布 jixiebi_in_pose=4，抓取流程完成")

            self.rate.sleep()

if __name__ == '__main__':
    try:
        controller = ArmController()
        controller.run()
    except rospy.ROSInterruptException:
        pass
