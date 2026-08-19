#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSL2 端 Kinect 综合数据接收客户端
连接 Windows 端 kinect_yolo_lidar_server.py，接收检测信息和 LaserScan 数据，
转换为 ROS 消息发布到对应话题。

工作流程:
  1. 通过两个 TCP 连接分别连接 Windows 端的检测端口和扫描端口
  2. 检测端口 -> BoundingBoxes 消息 -> /detection_result 话题
  3. 扫描端口 -> LaserScan 消息 -> /scan 话题
  4. 发布服务器连接状态到 /kinect_server_status 话题

通信协议 (KINECT_DET_LASER_V1):
  检测端口 (默认 9999):
    握手: {'type': 'handshake', 'protocol': 'KINECT_DET_LASER_V1', 'channel': 'detection', ...}
    数据: {'type': 'detection', 'seq': N, 'detections': [...], 'checksum': '...'}
  扫描端口 (默认 9998):
    握手: {'type': 'handshake', 'protocol': 'KINECT_DET_LASER_V1', 'channel': 'laser_scan', ...}
    数据: {'type': 'laser_scan', 'seq': N, 'scan': {...}, 'checksum': '...'}

通信话题:
  发布:
    /detection_result        (BoundingBoxes) - YOLO 检测结果
    /scan                    (LaserScan)     - 深度转激光扫描数据
    /kinect_server_status    (Int32)         - 服务器连接状态
        0: 全部未连接
        1: 检测已连接
        2: 扫描已连接
        3: 全部已连接，数据正常
        4: 校验失败
        5: 重连中

用法:
  rosrun user_control kinect_data_receiver.py
  rosrun user_control kinect_data_receiver.py _server_host:=192.168.1.100 _det_port:=9999 _scan_port:=9998
"""

import rospy
import socket
import struct
import json
import hashlib
import math
import time
import threading
from std_msgs.msg import Int32, Header
from sensor_msgs.msg import LaserScan
from yolov8_ros_msgs.msg import BoundingBox, BoundingBoxes


# 服务器连接状态
STATUS_ALL_DISCONNECTED = 0
STATUS_DET_CONNECTED = 1
STATUS_SCAN_CONNECTED = 2
STATUS_ALL_CONNECTED_OK = 3
STATUS_CHECKSUM_FAIL = 4
STATUS_RECONNECTING = 5


def compute_checksum(data_bytes):
    """计算校验值 (与服务器端一致: MD5 前8位十六进制)"""
    return hashlib.md5(data_bytes).hexdigest()[:8]


class ChannelReceiver:
    """单个通道的 TCP 接收器"""

    def __init__(self, channel_name, host, port, reconnect_interval=3.0,
                 checksum_enabled=True):
        self.channel_name = channel_name
        self.host = host
        self.port = port
        self.reconnect_interval = reconnect_interval
        self.checksum_enabled = checksum_enabled

        self.sock = None
        self.connected = False
        self.handshake_done = False
        self.handshake_info = {}
        self.last_seq = 0
        self.msg_count = 0
        self.checksum_fail_count = 0
        self.lock = threading.Lock()
        self.running = True

    def connect(self):
        """连接到服务器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(5.0)
            self.connected = True
            rospy.loginfo(f"[{self.channel_name}] 已连接到 {self.host}:{self.port}")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            rospy.logwarn(f"[{self.channel_name}] 连接失败: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.handshake_done = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def receive_exact(self, n_bytes):
        """精确接收 n 字节数据"""
        data = b''
        while len(data) < n_bytes:
            chunk = self.sock.recv(n_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def receive_handshake(self):
        """接收握手消息"""
        try:
            header = self.receive_exact(8)
            if header is None:
                return False
            payload_len, seq = struct.unpack('!II', header)
            if payload_len > 10 * 1024 * 1024:
                rospy.logwarn(f"[{self.channel_name}] 无效握手长度: {payload_len}")
                return False

            payload = self.receive_exact(payload_len)
            if payload is None:
                return False

            hs = json.loads(payload.decode('utf-8'))
            if hs.get('type') != 'handshake' or hs.get('protocol') != 'KINECT_DET_LASER_V1':
                rospy.logwarn(f"[{self.channel_name}] 未知协议: {hs}")
                return False

            self.handshake_info = hs
            self.handshake_done = True
            rospy.loginfo(f"[{self.channel_name}] 握手成功: {hs}")
            return True
        except Exception as e:
            rospy.logwarn(f"[{self.channel_name}] 握手失败: {e}")
            return False

    def receive_message(self):
        """接收一条消息

        支持两种帧格式:
          纯 JSON: [8字节头][JSON载荷]
          混合编码: [8字节头][JSON载荷][二进制ranges]
        混合编码用于 LaserScan 消息, JSON 头中包含 ranges_size 字段,
        ranges 数据以 float32 二进制紧跟在 JSON 之后。
        """
        try:
            header = self.receive_exact(8)
            if header is None:
                return None
            payload_len, seq = struct.unpack('!II', header)
            if payload_len > 10 * 1024 * 1024:
                rospy.logwarn(f"[{self.channel_name}] 无效消息长度: {payload_len}")
                return None

            payload = self.receive_exact(payload_len)
            if payload is None:
                return None

            msg_data = json.loads(payload.decode('utf-8'))

            # 检查是否有二进制 ranges 数据 (混合编码帧)
            scan_info = msg_data.get('scan')
            ranges_size = scan_info.get('ranges_size') if scan_info else None
            if ranges_size is not None:
                # 读取二进制 ranges 数据
                ranges_bytes = self.receive_exact(ranges_size * 4)
                if ranges_bytes is None:
                    rospy.logwarn(f"[{self.channel_name}] ranges 数据不完整")
                    return None
                ranges_list = list(struct.unpack(f'{ranges_size}f', ranges_bytes))
                scan_info['ranges'] = ranges_list
                del scan_info['ranges_size']

                # 校验 checksum (JSON + 二进制 ranges 的联合校验)
                if self.checksum_enabled and 'checksum' in msg_data:
                    received_checksum = msg_data['checksum']
                    verify_payload = payload.replace(
                        f'"checksum": "{received_checksum}"'.encode('utf-8'),
                        b'"checksum": "pending"'
                    )
                    expected_checksum = compute_checksum(verify_payload + ranges_bytes)
                    if received_checksum != expected_checksum:
                        self.checksum_fail_count += 1
                        rospy.logwarn(
                            f"[{self.channel_name}] 校验失败: 期望 {expected_checksum}, "
                            f"收到 {received_checksum}")
                        return None
            else:
                # 纯 JSON 帧: 传统校验
                if self.checksum_enabled and 'checksum' in msg_data:
                    received_checksum = msg_data['checksum']
                    verify_payload = payload.replace(
                        f'"checksum": "{received_checksum}"'.encode('utf-8'),
                        b'"checksum": "pending"'
                    )
                    expected_checksum = compute_checksum(verify_payload)
                    if received_checksum != expected_checksum:
                        self.checksum_fail_count += 1
                        rospy.logwarn(
                            f"[{self.channel_name}] 校验失败: 期望 {expected_checksum}, "
                            f"收到 {received_checksum}")
                        return None

            return msg_data

        except socket.timeout:
            return None
        except (ConnectionResetError, BrokenPipeError,
                ConnectionAbortedError, OSError) as e:
            rospy.logwarn(f"[{self.channel_name}] 连接断开: {e}")
            self.disconnect()
            return None
        except Exception as e:
            rospy.logwarn(f"[{self.channel_name}] 接收错误: {e}")
            return None


class KinectDataReceiver:
    """WSL2 端 Kinect 综合数据接收客户端"""

    def __init__(self):
        rospy.init_node('kinect_data_receiver', anonymous=True)

        # === 参数 ===
        self.server_host = rospy.get_param('~server_host', 'localhost')
        self.det_port = rospy.get_param('~det_port', 9999)
        self.scan_port = rospy.get_param('~scan_port', 9998)
        self.reconnect_interval = rospy.get_param('~reconnect_interval', 3.0)
        self.checksum_enabled = rospy.get_param('~checksum_enabled', True)

        # LaserScan 参数 (从握手信息中获取，此处为默认值)
        self.scan_frame_id = rospy.get_param('~scan_frame_id', 'camera_depth_frame')
        self.scan_angle_min = DEFAULT_SCAN_ANGLE_MIN
        self.scan_angle_max = DEFAULT_SCAN_ANGLE_MAX
        self.scan_angle_increment = DEFAULT_SCAN_ANGLE_INCREMENT
        self.scan_range_min = DEFAULT_SCAN_RANGE_MIN
        self.scan_range_max = DEFAULT_SCAN_RANGE_MAX

        # === 状态 ===
        self.server_status = STATUS_ALL_DISCONNECTED

        # === 发布器 ===
        self.detection_pub = rospy.Publisher('/detection_result', BoundingBoxes, queue_size=10)
        self.scan_pub = rospy.Publisher('/scan', LaserScan, queue_size=10)
        self.status_pub = rospy.Publisher('/kinect_server_status', Int32, queue_size=10)

        # === 接收器 ===
        self.det_receiver = ChannelReceiver(
            'detection', self.server_host, self.det_port,
            self.reconnect_interval, self.checksum_enabled
        )
        self.scan_receiver = ChannelReceiver(
            'laser_scan', self.server_host, self.scan_port,
            self.reconnect_interval, self.checksum_enabled
        )

        rospy.loginfo(f"[KinectDataReceiver] 初始化完成, "
                      f"检测: {self.server_host}:{self.det_port}, "
                      f"扫描: {self.server_host}:{self.scan_port}")

    def _update_status(self, status):
        """更新并发布服务器连接状态"""
        if status != self.server_status:
            self.server_status = status
            rospy.loginfo(f"[KinectDataReceiver] 服务器状态: {self._status_name(status)}")
        msg = Int32()
        msg.data = status
        self.status_pub.publish(msg)

    @staticmethod
    def _status_name(status):
        names = {
            STATUS_ALL_DISCONNECTED: "全部未连接",
            STATUS_DET_CONNECTED: "检测已连接",
            STATUS_SCAN_CONNECTED: "扫描已连接",
            STATUS_ALL_CONNECTED_OK: "全部已连接-正常",
            STATUS_CHECKSUM_FAIL: "校验失败",
            STATUS_RECONNECTING: "重连中",
        }
        return names.get(status, f"未知({status})")

    def _compute_overall_status(self):
        """计算整体连接状态"""
        det_ok = self.det_receiver.connected
        scan_ok = self.scan_receiver.connected

        if det_ok and scan_ok:
            return STATUS_ALL_CONNECTED_OK
        elif det_ok:
            return STATUS_DET_CONNECTED
        elif scan_ok:
            return STATUS_SCAN_CONNECTED
        else:
            return STATUS_ALL_DISCONNECTED

    def _build_detection_msg(self, msg_data):
        """将检测结果转换为 ROS BoundingBoxes 消息"""
        boxes_msg = BoundingBoxes()
        boxes_msg.header = Header(stamp=rospy.Time.now())
        boxes_msg.header.frame_id = 'camera_rgb_optical_frame'
        boxes_msg.image_header = boxes_msg.header

        for det in msg_data.get('detections', []):
            bbox = BoundingBox()
            bbox.xmin = det['xmin']
            bbox.ymin = det['ymin']
            bbox.xmax = det['xmax']
            bbox.ymax = det['ymax']
            bbox.Class = det['class']
            bbox.probability = det['confidence']
            bbox.track_id = det.get('track_id', -1)
            boxes_msg.bounding_boxes.append(bbox)

        return boxes_msg

    def _build_laserscan_msg(self, msg_data):
        """将 LaserScan 数据转换为 ROS LaserScan 消息"""
        scan_info = msg_data.get('scan', {})

        scan_msg = LaserScan()
        scan_msg.header = Header(stamp=rospy.Time.now())
        scan_msg.header.frame_id = self.scan_frame_id

        scan_msg.angle_min = scan_info.get('angle_min', self.scan_angle_min)
        scan_msg.angle_max = scan_info.get('angle_max', self.scan_angle_max)
        scan_msg.angle_increment = scan_info.get('angle_increment', self.scan_angle_increment)
        scan_msg.time_increment = scan_info.get('time_increment', 0.0)
        scan_msg.scan_time = scan_info.get('scan_time', 0.033)
        scan_msg.range_min = scan_info.get('range_min', self.scan_range_min)
        scan_msg.range_max = scan_info.get('range_max', self.scan_range_max)

        ranges = scan_info.get('ranges', [])
        # 将 0.0 (无有效深度) 转换为 inf，AMCL 期望 inf 表示"该方向无障碍物"
        # 0.0 在 Kinect 深度数据中表示无效像素，不是"0米处有障碍物"
        scan_msg.ranges = [float('inf') if r <= 0 else float(r) for r in ranges]
        scan_msg.intensities = []

        return scan_msg

    def _det_loop(self):
        """检测数据接收循环"""
        while not rospy.is_shutdown() and self.det_receiver.running:
            # 连接
            if not self.det_receiver.connected:
                self._update_status(STATUS_RECONNECTING)
                if not self.det_receiver.connect():
                    rospy.sleep(self.reconnect_interval)
                    continue

            # 握手
            if not self.det_receiver.handshake_done:
                if not self.det_receiver.receive_handshake():
                    self.det_receiver.disconnect()
                    rospy.sleep(self.reconnect_interval)
                    continue

            # 接收消息
            msg_data = self.det_receiver.receive_message()
            if msg_data is None:
                if not self.det_receiver.connected:
                    rospy.sleep(0.1)
                    continue
                continue

            self.det_receiver.msg_count += 1
            seq = msg_data.get('seq', 0)

            # 检测序号跳跃
            if self.det_receiver.last_seq > 0 and seq > self.det_receiver.last_seq + 1:
                rospy.logwarn(f"[detection] 序号跳跃: {self.det_receiver.last_seq} -> {seq}")
            self.det_receiver.last_seq = seq

            # 转换并发布
            ros_msg = self._build_detection_msg(msg_data)
            self.detection_pub.publish(ros_msg)

            self._update_status(self._compute_overall_status())

            # 定期日志
            if self.det_receiver.msg_count % 100 == 0:
                det_count = len(msg_data.get('detections', []))
                rospy.loginfo(f"[detection] 已接收 {self.det_receiver.msg_count} 条, "
                              f"当前 {det_count} 个目标, seq={seq}")

        self.det_receiver.disconnect()

    def _scan_loop(self):
        """LaserScan 数据接收循环"""
        while not rospy.is_shutdown() and self.scan_receiver.running:
            # 连接
            if not self.scan_receiver.connected:
                if not self.scan_receiver.connect():
                    rospy.sleep(self.reconnect_interval)
                    continue

            # 握手
            if not self.scan_receiver.handshake_done:
                if not self.scan_receiver.receive_handshake():
                    self.scan_receiver.disconnect()
                    rospy.sleep(self.reconnect_interval)
                    continue

                # 从握手信息中更新 LaserScan 参数
                hs = self.scan_receiver.handshake_info
                if 'angle_min' in hs:
                    self.scan_angle_min = hs['angle_min']
                if 'angle_max' in hs:
                    self.scan_angle_max = hs['angle_max']
                if 'angle_increment' in hs:
                    self.scan_angle_increment = hs['angle_increment']
                if 'range_min' in hs:
                    self.scan_range_min = hs['range_min']
                if 'range_max' in hs:
                    self.scan_range_max = hs['range_max']

            # 接收消息
            msg_data = self.scan_receiver.receive_message()
            if msg_data is None:
                if not self.scan_receiver.connected:
                    rospy.sleep(0.1)
                    continue
                continue

            self.scan_receiver.msg_count += 1
            seq = msg_data.get('seq', 0)

            # 检测序号跳跃
            if self.scan_receiver.last_seq > 0 and seq > self.scan_receiver.last_seq + 1:
                rospy.logwarn(f"[laser_scan] 序号跳跃: {self.scan_receiver.last_seq} -> {seq}")
            self.scan_receiver.last_seq = seq

            # 转换并发布 (始终发布当前帧, 不做缓存重发)
            # 缓存重发会导致"范围内无障碍物"时仍发布旧障碍物数据,
            # 造成导航系统误判前方有障碍
            ros_msg = self._build_laserscan_msg(msg_data)
            self.scan_pub.publish(ros_msg)

            self._update_status(self._compute_overall_status())

            # 定期日志
            if self.scan_receiver.msg_count % 100 == 0:
                ranges = msg_data.get('scan', {}).get('ranges', [])
                valid = sum(1 for r in ranges if r > 0)
                rospy.loginfo(f"[laser_scan] 已接收 {self.scan_receiver.msg_count} 条, "
                              f"有效点: {valid}/{len(ranges)}, seq={seq}")

        self.scan_receiver.disconnect()

    def run(self):
        """主循环：启动两个接收线程"""
        rospy.loginfo("[KinectDataReceiver] 开始运行")

        # 启动检测接收线程
        det_thread = threading.Thread(target=self._det_loop, daemon=True)
        det_thread.start()

        # 启动扫描接收线程
        scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        scan_thread.start()

        # 主线程：定期发布状态
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            self._update_status(self._compute_overall_status())
            rate.sleep()

        # 等待线程结束
        self.det_receiver.running = False
        self.scan_receiver.running = False
        det_thread.join(timeout=2.0)
        scan_thread.join(timeout=2.0)

        rospy.loginfo("[KinectDataReceiver] 已退出")


# 默认 LaserScan 参数 (与服务器端一致)
DEFAULT_SCAN_ANGLE_MIN = -0.5
DEFAULT_SCAN_ANGLE_MAX = 0.5
DEFAULT_SCAN_ANGLE_INCREMENT = 0.0016
DEFAULT_SCAN_RANGE_MIN = 0.45
DEFAULT_SCAN_RANGE_MAX = 10.0


def main():
    try:
        receiver = KinectDataReceiver()
        receiver.run()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        rospy.loginfo("[KinectDataReceiver] 用户中断")


if __name__ == '__main__':
    main()
