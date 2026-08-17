#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音反馈模块 - TTS 文字转语音输出
参考：ttb_sim/scripts/controll_core.py 中的 speach_pub 逻辑

功能:
  1. 订阅 /voice_feedback_cmd (Int32) 获取语音反馈指令
  2. 将状态ID转换为语音文本
  3. 使用 TTS 引擎朗读反馈信息

状态ID -> 语音文本映射:
  -1: "系统已就绪，等待指令"
   0: "开始搜索目标"
   1: "已检测到目标"
   2: "正在靠近目标"
   3: "目标已就位"
   4: "正在返回初始位置"
   5: "全部任务已完成"
"""

import rospy
import threading
from std_msgs.msg import Int32

# 语音文本映射表
FEEDBACK_TEXTS = {
        -1: "系统已就绪，等待指令",
        0:  "开始定点导航",
        1:  "到达目标点，开始搜索",
        2:  "发现目标，开始靠近",
        3:  "机械臂伸出",
        4:  "正在抓取",
        5:  "抓取完成，正在前往终点",
        6:  "全部任务已完成",
    }


class VoiceFeedbackNode:
    def __init__(self):
        rospy.init_node('voice_feedback', anonymous=True)

        # TTS 引擎
        self.tts_engine = None
        self._init_tts()

        # 上次播报的状态（避免重复播报）
        self.last_state = None

        # 发布器（调试用：确认接收到的指令）
        self.debug_pub = rospy.Publisher('/voice_feedback_debug', Int32, queue_size=10)

        # 订阅器
        self.feedback_sub = rospy.Subscriber('/voice_feedback_cmd', Int32,
                                             self.feedback_callback, queue_size=10)

        rospy.loginfo("[VoiceFeedback] 语音反馈节点已启动")

    def _init_tts(self):
        """初始化 TTS 引擎"""
        # 优先使用 pyttsx3
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            # 获取当前语音参数
            voices = self.tts_engine.getProperty('voices')
            # 尝试设置中文语音
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            self.tts_engine.setProperty('rate', 150)    # 语速
            self.tts_engine.setProperty('volume', 1.0)  # 音量
            rospy.loginfo("[VoiceFeedback] TTS 引擎: pyttsx3")
            self.tts_type = 'pyttsx3'
            return
        except ImportError:
            rospy.logwarn("[VoiceFeedback] pyttsx3 不可用 (pip install pyttsx3)")

        # 备选: espeak
        try:
            import subprocess
            result = subprocess.run(['espeak', '--version'],
                                    capture_output=True, timeout=2)
            if result.returncode == 0:
                self.tts_type = 'espeak'
                rospy.loginfo("[VoiceFeedback] TTS 引擎: espeak")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 备选: gtts (Google TTS, 需要网络)
        try:
            from gtts import gTTS
            import os
            import tempfile

            # 测试gtts是否可用
            test_tts = gTTS(text='test', lang='zh-CN')
            self.tts_type = 'gtts'
            rospy.loginfo("[VoiceFeedback] TTS 引擎: gTTS (需要网络)")
            return
        except ImportError:
            rospy.logwarn("[VoiceFeedback] gTTS 不可用 (pip install gtts)")

        # 最后的备选: 只打印到日志
        self.tts_type = 'none'
        rospy.logwarn("[VoiceFeedback] 无可用 TTS 引擎，仅输出日志")

    def feedback_callback(self, msg):
        """语音反馈指令回调"""
        state_id = msg.data
        self.debug_pub.publish(msg)

        # 避免重复播报相同状态
        if state_id == self.last_state:
            return
        self.last_state = state_id

        # 获取语音文本
        text = FEEDBACK_TEXTS.get(state_id, f"状态 {state_id}")
        rospy.loginfo(f"[VoiceFeedback] 播报: {text}")

        # 执行 TTS 播报（在独立线程中执行，避免阻塞回调）
        if self.tts_type != 'none':
            threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text):
        """执行 TTS 播报"""
        try:
            if self.tts_type == 'pyttsx3':
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            elif self.tts_type == 'espeak':
                import subprocess
                subprocess.run(['espeak', '-v', 'zh', '-s', '150', text],
                               timeout=10)
            elif self.tts_type == 'gtts':
                from gtts import gTTS
                import os
                import tempfile
                import pygame

                tts = gTTS(text=text, lang='zh-CN')
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    tmp_path = f.name
                tts.save(tmp_path)

                pygame.mixer.init()
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    rospy.sleep(0.1)
                pygame.mixer.quit()
                os.unlink(tmp_path)
        except Exception as e:
            rospy.logwarn(f"[VoiceFeedback] 播报失败: {e}")

    def run(self):
        """保持节点运行"""
        rospy.spin()


# ---------- 命令行启动 ----------
def main():
    try:
        node = VoiceFeedbackNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        rospy.loginfo("[VoiceFeedback] 用户中断")


if __name__ == '__main__':
    main()