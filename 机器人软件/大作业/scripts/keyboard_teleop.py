#!/usr/bin/env python3
"""
键盘控制: 方向键固定速度移动, h 键切换手动/自主模式.
- 手动模式: 方向键控制, 松手后持续占用 teleop (零速), 阻止自主探索.
- 自主模式: 完全不发布, explore_lite 通过 navi 通道接管.
直接从 /dev/tty 读取按键, 不受 launch 重定向影响.
"""
import rospy
import sys
import termios
import tty
import select
from geometry_msgs.msg import Twist

# 固定速度参数
LINEAR_SPEED = 0.15     # 前进/后退速度 (m/s)
ANGULAR_SPEED = 0.6     # 旋转速度 (rad/s)

# 键码 (方向键转义序列的最后一个字节)
KEY_UP    = 65   # ↑
KEY_DOWN  = 66   # ↓
KEY_RIGHT = 67   # →
KEY_LEFT  = 68   # ←
KEY_q     = 113  # q 退出
KEY_h     = 104  # h 切换模式

# ── 打开真实终端, 绕过 launch 的 stdin 重定向 ──
try:
    TTY = open('/dev/tty', 'r')
except (IOError, OSError):
    rospy.logwarn("/dev/tty 不可用, 回退到 stdin")
    TTY = sys.stdin


def get_key(timeout=0.05):
    """非阻塞读取键盘输入, 返回按键码或 None"""
    rlist, _, _ = select.select([TTY], [], [], timeout)
    if not rlist:
        return None
    c = TTY.read(1)
    if not c:
        return None
    if c == '\x1b':
        # 方向键转义序列: \x1b + '[' + 方向码
        rlist2, _, _ = select.select([TTY], [], [], 0.01)
        if rlist2:
            rest = TTY.read(2)
            if len(rest) == 2:
                return ord(rest[1])
        return None  # 单独的 Esc
    return ord(c)


def main():
    rospy.init_node('keyboard_teleop', anonymous=True)

    pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=10)

    # 保存终端设置, 切到 raw 模式
    fd = TTY.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    MODE_MANUAL = 'manual'   # 手动: 占用 teleop, 阻止自主探索
    MODE_AUTO   = 'auto'     # 自主: 不发布, explore_lite 接管
    mode = MODE_MANUAL       # 默认手动模式

    rospy.loginfo("┌──────────────────────────────┐")
    rospy.loginfo("│ 键盘控制就绪                  │")
    rospy.loginfo("│ ↑↓←→ 移动  空格=停止  q=退出 │")
    rospy.loginfo("│ h = 切换模式 (当前: 手动)     │")
    rospy.loginfo("│ 线速度 %.2f  角速度 %.2f      │" % (LINEAR_SPEED, ANGULAR_SPEED))
    rospy.loginfo("└──────────────────────────────┘")

    rate = rospy.Rate(20)
    was_active = False

    try:
        while not rospy.is_shutdown():
            key = get_key()

            if key is not None:
                # ── 模式切换 ──
                if key == KEY_h:
                    if mode == MODE_MANUAL:
                        mode = MODE_AUTO
                        was_active = False
                        rospy.loginfo(">>> 切换到 [自主] 模式 (explore_lite 接管)")
                    else:
                        mode = MODE_MANUAL
                        rospy.loginfo(">>> 切换到 [手动] 模式 (键盘控制)")
                    continue

                # ── 退出 ──
                if key == KEY_q:
                    rospy.loginfo("退出键盘控制")
                    break

                # ── 手动模式下处理方向键 ──
                if mode == MODE_MANUAL:
                    cmd = Twist()
                    if key == KEY_UP:
                        cmd.linear.x = LINEAR_SPEED
                    elif key == KEY_DOWN:
                        cmd.linear.x = -LINEAR_SPEED
                    elif key == KEY_LEFT:
                        cmd.angular.z = ANGULAR_SPEED
                    elif key == KEY_RIGHT:
                        cmd.angular.z = -ANGULAR_SPEED
                    elif key == ord(' '):
                        pass  # 零速
                    else:
                        continue  # 其它键忽略

                    pub.publish(cmd)
                    was_active = True

            elif was_active and mode == MODE_MANUAL:
                # 松手: 发零速保持 teleop 占用, 阻止自主探索抢走控制权
                pub.publish(Twist())
                was_active = False

            # 自主模式: 不发布任何东西, explore_lite 通过 navi 接管

            rate.sleep()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        pub.publish(Twist())
        rospy.loginfo("已停止")


if __name__ == '__main__':
    main()
