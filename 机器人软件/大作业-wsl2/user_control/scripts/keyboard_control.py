#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘控制独立模块 - 在终端前台运行，具有标准输入访问权限
解决 roslaunch 下 stdin 不可用导致键盘输入失效的问题

用法:
  source /opt/ros/noetic/setup.bash
  source /path/to/ws/devel/setup.bash
  python3 keyboard_control.py

通信话题:
  发布:
    /user_command   (Int32)  - 用户命令
      0: 启动任务
      1: 停止/暂停
      2: 拾取
      3: 搜索瓶子
"""

import rospy
import sys
import select
from std_msgs.msg import Int32

CMD_START   = 0
CMD_STOP    = 1
CMD_PICK    = 2
CMD_SEARCH  = 3


def print_help():
    print("\n========== 键盘控制 ==========")
    print("  s - 启动任务")
    print("  x - 停止/暂停")
    print("  p - 拾取")
    print("  b - 搜索瓶子")
    print("  h - 显示帮助")
    print("  q - 退出")
    print("==============================\n")


def main():
    rospy.init_node('keyboard_control', anonymous=True)
    pub = rospy.Publisher('/user_command', Int32, queue_size=10)

    # 等待发布器就绪
    rospy.sleep(0.3)

    print_help()
    rospy.loginfo("[KeyboardControl] 键盘控制已启动 (s=启动, x=停止, p=拾取, b=搜索, h=帮助)")

    # 设置 stdin 为非阻塞模式
    import tty
    import termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        while not rospy.is_shutdown():
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()

                if key == 's':
                    pub.publish(CMD_START)
                    rospy.loginfo("[Keyboard] -> 启动任务")
                    print("\r[键盘] 已发送: 启动任务            ")
                elif key == 'x':
                    pub.publish(CMD_STOP)
                    rospy.loginfo("[Keyboard] -> 停止")
                    print("\r[键盘] 已发送: 停止              ")
                elif key == 'p':
                    pub.publish(CMD_PICK)
                    rospy.loginfo("[Keyboard] -> 拾取")
                    print("\r[键盘] 已发送: 拾取              ")
                elif key == 'b':
                    pub.publish(CMD_SEARCH)
                    rospy.loginfo("[Keyboard] -> 搜索瓶子")
                    print("\r[键盘] 已发送: 搜索瓶子          ")
                elif key == 'h':
                    print_help()
                elif key == 'q':
                    rospy.loginfo("[Keyboard] 用户请求退出")
                    print("\r[键盘] 退出                      ")
                    rospy.signal_shutdown("用户退出")
                    break
                # 忽略其他按键
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"[KeyboardControl] 错误: {e}")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == '__main__':
    main()