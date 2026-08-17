#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音控制与键盘控制输入模块

功能:
  1. 语音识别：使用 Vosk 离线中文语音识别，无需网络
  2. 键盘控制：作为备用/辅助输入方式
  3. 支持关键词: "start" / "开始" -> 启动任务
                 "stop" / "停止" -> 停止任务
                 "pick" / "捡"   -> 拾取指令
                 "bottle" / "瓶子" -> 搜索瓶子

依赖:
  pip install vosk pyaudio
  下载 Vosk 中文模型: https://alphacephei.com/vosk/models
  推荐模型: vosk-model-small-cn-0.22 (~42MB)

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
import threading
from std_msgs.msg import Int32

# 命令定义
CMD_START   = 0   # 启动任务
CMD_STOP    = 1   # 停止/暂停
CMD_PICK    = 2   # 拾取
CMD_SEARCH  = 3   # 搜索瓶子


class VoiceControlNode:
    """语音控制节点 - 使用 Vosk 离线中文语音识别"""

    def __init__(self, pub):
        self.pub = pub
        self.running = False
        self.thread = None
        self.listen_count = 0       # 监听尝试计数
        self.recognize_count = 0    # 成功识别计数

    def start(self):
        """在后台线程中启动语音监听"""
        try:
            import vosk
            import pyaudio
        except ImportError as e:
            missing = 'vosk' if 'vosk' in str(e) else 'pyaudio'
            rospy.logwarn(f"[VoiceControl] {missing} 未安装 (pip install {missing})")
            rospy.logwarn("[VoiceControl] 语音控制不可用，请使用键盘控制")
            return False

        # 查找 Vosk 模型路径
        model_path = self._find_model()
        if model_path is None:
            rospy.logwarn("[VoiceControl] 未找到 Vosk 中文模型")
            rospy.logwarn("[VoiceControl] 请下载模型到以下任一位置:")
            rospy.logwarn("  1. 脚本同目录: voice_control.py 所在目录/model/")
            rospy.logwarn("  2. 包目录: user_control/models/")
            rospy.logwarn("  3. 指定路径: rosparam set /vosk_model_path <路径>")
            rospy.logwarn("[VoiceControl] 下载地址: https://alphacephei.com/vosk/models")
            rospy.logwarn("[VoiceControl] 推荐模型: vosk-model-small-cn-0.22 (~42MB)")
            rospy.logwarn("[VoiceControl] 语音控制不可用，请使用键盘控制")
            return False

        try:
            import vosk
            import pyaudio

            # 加载模型
            rospy.loginfo(f"[VoiceControl] 加载 Vosk 模型: {model_path}")
            self.model = vosk.Model(model_path)

            # 初始化 PyAudio
            self.pa = pyaudio.PyAudio()

            # 检查麦克风设备
            input_devices = self._find_input_devices()
            if not input_devices:
                rospy.logwarn("[VoiceControl] 未找到麦克风输入设备")
                rospy.logwarn("[VoiceControl] WSL2 环境下麦克风通常不可用，请使用键盘控制")
                return False

            rospy.loginfo(f"[VoiceControl] 可用麦克风设备: {input_devices}")

            # 使用默认输入设备
            self.device_index = None  # None = 系统默认
            self.sample_rate = 16000

            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            rospy.loginfo("[VoiceControl] Vosk 离线语音识别已启动")
            return True

        except Exception as e:
            rospy.logwarn(f"[VoiceControl] 语音初始化失败: {e}")
            rospy.logwarn("[VoiceControl] 语音控制不可用，请使用键盘控制")
            return False

    def _find_model(self):
        """查找 Vosk 中文模型路径（需指向包含 am/graph 等子目录的模型文件夹）"""
        import os

        # 1. ROS 参数指定路径
        if rospy.has_param('~vosk_model_path'):
            path = rospy.get_param('~vosk_model_path')
            if self._is_valid_model(path):
                return path

        # 2. 脚本同目录下
        script_dir = os.path.dirname(os.path.abspath(__file__))
        result = self._search_model_in(script_dir)
        if result:
            return result

        # 3. 包目录下
        pkg_dir = os.path.dirname(script_dir)  # scripts/ -> user_control/
        result = self._search_model_in(pkg_dir)
        if result:
            return result

        # 4. 用户主目录
        home = os.path.expanduser('~')
        for name in ['vosk-model-small-cn-0.22', 'vosk-model-cn-0.22']:
            path = os.path.join(home, name)
            if self._is_valid_model(path):
                return path

        return None

    def _is_valid_model(self, path):
        """检查路径是否为有效的 Vosk 模型目录（包含 am/ 或 graph/ 子目录）"""
        import os
        if not os.path.isdir(path):
            return False
        # Vosk 模型目录必须包含 am/ 或 graph/ 子目录
        return os.path.isdir(os.path.join(path, 'am')) or os.path.isdir(os.path.join(path, 'graph'))

    def _search_model_in(self, base_dir):
        """在指定目录及其子目录中搜索 Vosk 模型"""
        import os
        # 先检查直接命名的目录
        for name in ['vosk-model-small-cn-0.22', 'vosk-model-cn-0.22', 'vosk-model', 'model']:
            path = os.path.join(base_dir, name)
            if self._is_valid_model(path):
                return path

        # 检查 models/ 容器目录下的子目录
        models_dir = os.path.join(base_dir, 'models')
        if os.path.isdir(models_dir):
            # 先检查 models/ 本身是否就是模型
            if self._is_valid_model(models_dir):
                return models_dir
            # 遍历子目录查找模型
            try:
                for entry in os.listdir(models_dir):
                    subpath = os.path.join(models_dir, entry)
                    if self._is_valid_model(subpath):
                        return subpath
            except OSError:
                pass

        return None

    def _find_input_devices(self):
        """查找可用的麦克风输入设备"""
        devices = []
        try:
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    devices.append(f"#{i} {info['name']}")
        except Exception:
            pass
        return devices

    def _listen_loop(self):
        """Vosk 离线语音监听循环"""
        import vosk
        import pyaudio
        import json

        # 创建识别器（SetPartialWords 用于获取部分识别结果）
        recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        recognizer.SetWords(True)

        # 打开音频流
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=4000
            )
        except OSError as e:
            rospy.logwarn(f"[VoiceControl] 无法打开麦克风音频流: {e}")
            rospy.logwarn("[VoiceControl] WSL2 环境下请确认 PulseAudio 已正确配置")
            self.running = False
            return

        stream.start_stream()
        rospy.loginfo("[VoiceControl] 麦克风已打开，开始离线监听...")

        while self.running and not rospy.is_shutdown():
            try:
                data = stream.read(4000, exception_on_overflow=False)
                self.listen_count += 1

                if recognizer.AcceptWaveform(data):
                    # 一句话识别完成
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        self.recognize_count += 1
                        rospy.loginfo(f"[VoiceControl] 识别结果: '{text}' (第{self.recognize_count}次成功)")
                        self._match_keywords(text)
                else:
                    # 部分识别结果（正在说话）
                    partial = json.loads(recognizer.PartialResult())
                    partial_text = partial.get('partial', '').strip()
                    if partial_text:
                        # 每30秒输出一次心跳日志
                        rospy.loginfo_throttle(30, f"[VoiceControl] 监听中... (检测到: '{partial_text}')")

            except IOError:
                # 音频缓冲区溢出，继续
                continue
            except Exception as e:
                rospy.logwarn_throttle(10, f"[VoiceControl] 识别异常: {e}")
                continue

        # 清理
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass

    def _match_keywords(self, text):
        """匹配关键词并发布命令"""
        matched = False
        if any(kw in text for kw in ["start", "开始", "启动", "开动", "开", "导航"]):
            self.pub.publish(CMD_START)
            rospy.loginfo("[VoiceControl] -> 发送命令: 启动任务 (cmd=0)")
            matched = True
        elif any(kw in text for kw in ["stop", "停止", "暂停", "停下", "停"]):
            self.pub.publish(CMD_STOP)
            rospy.loginfo("[VoiceControl] -> 发送命令: 停止 (cmd=1)")
            matched = True
        elif any(kw in text for kw in ["pick", "捡", "拿", "抓", "夹","取"]):
            self.pub.publish(CMD_PICK)
            rospy.loginfo("[VoiceControl] -> 发送命令: 拾取 (cmd=2)")
            matched = True
        elif any(kw in text for kw in ["bottle", "瓶子", "搜索", "寻找", "找","查"]):
            self.pub.publish(CMD_SEARCH)
            rospy.loginfo("[VoiceControl] -> 发送命令: 搜索瓶子 (cmd=3)")
            matched = True

        if not matched:
            rospy.loginfo(f"[VoiceControl] 未匹配到关键词: '{text}'")

    def stop(self):
        """停止语音监听"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        try:
            if hasattr(self, 'pa'):
                self.pa.terminate()
        except Exception:
            pass


class KeyboardControlNode:
    """键盘控制节点 - 作为备用输入"""

    def __init__(self, pub):
        self.pub = pub
        self.running = False
        self.thread = None

    def start(self):
        """启动键盘监听（在终端中）"""
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        rospy.loginfo("[KeyboardControl] 键盘控制已启动 (s=启动, x=停止, p=拾取, b=搜索, h=帮助)")
        return True

    def _listen_loop(self):
        """键盘监听循环"""
        import sys
        import select

        # 显示帮助
        self._print_help()

        while self.running and not rospy.is_shutdown():
            try:
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()

                    if key == 's':
                        self.pub.publish(CMD_START)
                        rospy.loginfo("[Keyboard] -> 启动任务")
                        print("\n[键盘] 已发送: 启动任务")
                    elif key == 'x':
                        self.pub.publish(CMD_STOP)
                        rospy.loginfo("[Keyboard] -> 停止")
                        print("\n[键盘] 已发送: 停止")
                    elif key == 'p':
                        self.pub.publish(CMD_PICK)
                        rospy.loginfo("[Keyboard] -> 拾取")
                        print("\n[键盘] 已发送: 拾取")
                    elif key == 'b':
                        self.pub.publish(CMD_SEARCH)
                        rospy.loginfo("[Keyboard] -> 搜索瓶子")
                        print("\n[键盘] 已发送: 搜索瓶子")
                    elif key == 'h':
                        self._print_help()
                    elif key == 'q':
                        rospy.loginfo("[Keyboard] 用户请求退出")
                        rospy.signal_shutdown("用户退出")

            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                continue

    def _print_help(self):
        print("\n========== 键盘控制 ==========")
        print("  s - 启动任务")
        print("  x - 停止/暂停")
        print("  p - 拾取")
        print("  b - 搜索瓶子")
        print("  h - 显示帮助")
        print("  q - 退出")
        print("==============================\n")

    def stop(self):
        """停止键盘监听"""
        self.running = False


# ======== ROS 节点入口 ========
def main():
    rospy.init_node('voice_control', anonymous=True)

    # 创建发布器
    pub = rospy.Publisher('/user_command', Int32, queue_size=10)
    rospy.loginfo("[VoiceControl] 节点已启动")

    # 启动语音控制
    voice = VoiceControlNode(pub)
    has_voice = voice.start()

    # 启动键盘控制
    keyboard = KeyboardControlNode(pub)
    has_keyboard = keyboard.start()

    if not has_voice and not has_keyboard:
        rospy.logerr("[VoiceControl] 语音和键盘控制均不可用!")
        sys.exit(1)

    # 输出控制方式汇总
    rospy.loginfo("===========================================")
    rospy.loginfo("  控制输入状态:")
    rospy.loginfo(f"    语音控制: {'可用' if has_voice else '不可用'}")
    rospy.loginfo(f"    键盘控制: {'可用' if has_keyboard else '不可用'}")
    rospy.loginfo("  话题: /user_command (Int32)")
    rospy.loginfo("    0=启动  1=停止  2=拾取  3=搜索")
    rospy.loginfo("===========================================")

    rospy.spin()

    voice.stop()
    keyboard.stop()


if __name__ == '__main__':
    main()