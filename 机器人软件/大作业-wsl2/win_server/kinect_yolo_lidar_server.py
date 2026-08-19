#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 端 Kinect YOLO + 深度点云服务器
在 Windows 主机上运行，采集 Kinect v1 的 RGB 图像和深度图像，
分别处理：
  - RGB 图像 -> YOLOv8 检测 -> 发布检测信息
  - 深度图像 -> 模拟 depthimage_to_laserscan 算法 -> 发布 LaserScan 数据

工作流程:
  1. 通过 pykinect (Kinect SDK) 采集 Kinect v1 的 RGB 和深度图像
  2. RGB 图像经 YOLOv8 检测，序列化检测结果为 JSON
  3. 深度图像经 depthimage_to_laserscan 算法，提取水平扫描线转换为 LaserScan
  4. 通过两个 TCP 端口分别发送检测信息和 LaserScan 数据

通信协议 (KINECT_DET_LASER_V1):
  检测端口 (默认 9999):
    握手: {'type': 'handshake', 'protocol': 'KINECT_DET_LASER_V1', 'channel': 'detection', ...}
    数据: [4字节长度][4字节seq][JSON payload] (与原 yolo_kinect_server 兼容)
  激光扫描端口 (默认 9998):
    握手: {'type': 'handshake', 'protocol': 'KINECT_DET_LASER_V1', 'channel': 'laser_scan', ...}
    数据: [4字节长度][4字节seq][JSON payload]

用法:
  python kinect_yolo_lidar_server.py
  python kinect_yolo_lidar_server.py --det-port 9999 --scan-port 9998 --target bottle

依赖 (Windows 端):
  pip install opencv-python ultralytics
  Kinect v1 SDK 1.8 已安装 (Kinect10.dll 由 SDK 提供，通过 ctypes 直接调用)

  注意: 需要 Kinect SDK 1.8 已安装 (通过 ctypes 直接调用 Kinect10.dll，无需第三方 Python 包)
        若无 Kinect，可使用 --source opencv 回退到普通摄像头模式 (仅测试用)
"""

import cv2
import numpy as np
import socket
import struct
import json
import hashlib
import time
import argparse
import sys
import select
import threading
import queue
import os


# ============================================================
# Kinect v1 参数 (基于 Kinect v1 硬件规格)
# ============================================================
KINECT_RGB_WIDTH = 640
KINECT_RGB_HEIGHT = 480
KINECT_DEPTH_WIDTH = 640
KINECT_DEPTH_HEIGHT = 480

# Kinect v1 深度相机内参
KINECT_FX = 525.0   # 焦距 x (像素)
KINECT_FY = 525.0   # 焦距 y (像素)
KINECT_CX = 319.5   # 光心 x (像素)
KINECT_CY = 239.5   # 光心 y (像素)
#KINECT_CY = 300.0

# Kinect v1 深度范围 (毫米)
KINECT_MIN_DEPTH = 800    # 0.8m
KINECT_MAX_DEPTH = 4000   # 4.0m

# depthimage_to_laserscan 参数 (对齐 ROS 官方包 depthimage_to_laserscan)
# scan_height: 采样行数 (官方默认1, 从 cy-scan_height/2 到 cy+scan_height/2)
DEFAULT_SCAN_HEIGHT = 100       # 采样行数 (像素行数, 非行号)
DEFAULT_SCAN_RANGE_MIN = 0.45   # 最小扫描距离 (米)
DEFAULT_SCAN_RANGE_MAX = 10.0   # 最大扫描距离 (米, 官方默认10.0)
DEFAULT_SCAN_ANGLE_MIN = -0.5   # 最小角度 (弧度, 约 -28.6°)
DEFAULT_SCAN_ANGLE_MAX = 1.0    # 最大角度 (弧度, 约 28.6°)
DEFAULT_SCAN_ANGLE_INCREMENT = 0.0016  # 角度增量 (弧度, 约 640点)
DEFAULT_SCAN_HEIGHT_THRESHOLD = 0.1  # 高度过滤阈值 (米), Y坐标大于此值的像素被剔除
                                      # Y>0 表示点在传感器下方 (地面), 阈值0.05m允许略低于传感器的障碍物通过
DEFAULT_SCAN_DEPTH_MAX = 4.0    # 原始深度上限 (米), 超过此深度的像素视为不可靠而剔除

# 射线状噪声滤波参数
RADIAL_NOISE_WINDOW_HALF = 5       # 角度邻域半径 (索引数, 单侧)
RADIAL_NOISE_MIN_VALID = 3         # 邻域内最少有效点数
RADIAL_NOISE_ORIGIN_DIST = 0.3     # 直线到原点距离阈值 (米), 小于此值判定为射线状噪声
RADIAL_NOISE_LINEARITY = 0.3       # 线性度阈值, 点集方差比(法线/切线)超过此值则不判定


def compute_checksum(data_bytes):
    """计算校验值 (MD5 前8位十六进制)"""
    return hashlib.md5(data_bytes).hexdigest()[:8]


def depth_to_laserscan(depth_image, scan_height=DEFAULT_SCAN_HEIGHT,
                       range_min=DEFAULT_SCAN_RANGE_MIN,
                       range_max=DEFAULT_SCAN_RANGE_MAX,
                       angle_min=DEFAULT_SCAN_ANGLE_MIN,
                       angle_max=DEFAULT_SCAN_ANGLE_MAX,
                       height_threshold=DEFAULT_SCAN_HEIGHT_THRESHOLD,
                       depth_max=DEFAULT_SCAN_DEPTH_MAX,
                       fx=KINECT_FX, fy=KINECT_FY, cx=KINECT_CX, cy=KINECT_CY):
    """
    将深度图像转换为 LaserScan 数据

    完全对齐 ROS 官方包 depthimage_to_laserscan 的 C++ 源码算法:
      https://github.com/ros-perception/depthimage_to_laserscan

    核心算法 (来自官方 DepthImageToLaserScan.h):
      1. scan_height 为采样行数 (非行号), 从 cy - scan_height/2 开始
      2. 遍历 scan_height 行中的每个像素
      3. 对每个像素 (u, depth):
         - th = -atan2((u - cx) / fx, 1.0)   # 角度 (ROS惯例: 左正右负)
         - index = (th - angle_min) / angle_increment
         - x = (u - cx) * depth_m / fx
         - z = depth_m
         - r = sqrt(x^2 + z^2)
         - 若 range_min <= r <= range_max 且 r < ranges[index], 则更新
      4. 多行扫描时, 同一角度取最小距离 (更近的障碍物优先)

    向量化实现: 逐行处理, 每行用 NumPy 向量化代替像素循环
    """
    if depth_image is None or depth_image.size == 0:
        return None

    img_h, img_w = depth_image.shape[:2]
    num_readings = int(round((angle_max - angle_min) / DEFAULT_SCAN_ANGLE_INCREMENT)) + 1

    # 初始化 ranges 为 inf (官方: 初始值由 LaserScan 构造设为 range_max+1)
    ranges = np.full(num_readings, np.inf)

    # 计算采样行范围 (对齐官方: offset = cy - scan_height/2)
    offset = int(cy - scan_height / 2.0)
    offset = max(0, min(offset, img_h - 1))
    end_row = min(offset + scan_height, img_h)

    # unit_scaling: uint16 深度值转米的系数 (官方: DepthTraits<uint16_t>::toMeters)
    unit_scaling = 0.001  # 毫米 -> 米
    constant_x = unit_scaling / fx  # 官方: constant_x = unit_scaling / cam_model.fx()
    constant_y = unit_scaling / fy  # Y方向系数, 用于计算像素3D高度

    # 预计算列索引
    col_indices = np.arange(img_w, dtype=np.float64)

    # 逐行处理 (对齐官方 C++ 的行循环)
    for v in range(offset, end_row):
        row = depth_image[v, :].astype(np.float64)

        # 官方: th = -atan2((double)(u - center_x) * constant_x, unit_scaling)
        # 注意: 官方用 constant_x 和 unit_scaling 而非实际深度值计算角度
        # 因为 atan2((u-cx)*depth/fx, depth) = atan2((u-cx)/fx, 1)
        # 而官方写法 atan2((u-cx)*constant_x, unit_scaling) = atan2((u-cx)/fx, 1)
        # 等价, 只是省略了 depth (分子分母都有)
        th = -np.arctan2((col_indices - cx) * constant_x, unit_scaling)

        # 计算索引: index = (th - angle_min) / angle_increment
        index = ((th - angle_min) / DEFAULT_SCAN_ANGLE_INCREMENT).astype(np.int32)

        # 官方: 检查 depth 是否有效 (非 NaN/Inf, 非 0)
        valid_depth = row > 0

        # 官方: 计算 XYZ
        # x = (u - center_x) * depth * constant_x
        # z = depth * unit_scaling  (toMeters)
        depth_m = row * unit_scaling
        x = (col_indices - cx) * row * constant_x
        z = depth_m
        y = (v - cy) * row * constant_y  # 3D Y坐标, 正值=传感器下方(地面)

        # 官方: r = sqrt(x^2 + z^2)
        r = np.sqrt(x * x + z * z)

        # 高度过滤: y > height_threshold 的像素被剔除 (地面在传感器下方, y值大)
        # 深度上限: z > depth_max 的像素被剔除 (传感器最大量程处不可靠)
        valid = valid_depth & (y <= height_threshold) & (r <= range_max) & (z <= depth_max)
        valid &= (index >= 0) & (index < num_readings)

        # 更新 ranges: 取最小距离 (对齐官方 use_point 逻辑)
        valid_indices = index[valid]
        valid_ranges = r[valid]
        np.minimum.at(ranges, valid_indices, valid_ranges)

    # 将 inf 替换为 0.0 (无数据)
    ranges_out = np.where(np.isinf(ranges), 0.0, np.round(ranges, 3)).tolist()

    return {
        'angle_min': round(angle_min, 6),
        'angle_max': round(angle_max, 6),
        'angle_increment': round(DEFAULT_SCAN_ANGLE_INCREMENT, 6),
        'time_increment': 0.0,
        'scan_time': 0.033,
        'range_min': range_min,
        'range_max': range_max,
        'ranges': ranges_out,
    }


def filter_radial_noise(scan_data,
                        window_half=RADIAL_NOISE_WINDOW_HALF,
                        min_valid=RADIAL_NOISE_MIN_VALID,
                        origin_dist_threshold=RADIAL_NOISE_ORIGIN_DIST,
                        linearity_threshold=RADIAL_NOISE_LINEARITY):
    """
    过滤极坐标点云中的射线状噪声

    Kinect v1 的典型噪声呈射线状分布: 从原点出发, 沿一条射线分布.
    真实障碍物(如墙壁)在极坐标中形成弧线, 对应笛卡尔坐标中不过原点的线段;
    而射线状噪声在笛卡尔坐标中形成过原点(或接近原点)的线段.

    算法: 对每个有效点, 收集其角度邻域内的有效点, 在笛卡尔坐标下用 PCA 拟合直线,
    若直线到原点的距离小于阈值, 则判定为射线状噪声并剔除.

    Args:
        scan_data: depth_to_laserscan 返回的 dict
        window_half: 角度邻域半径 (索引数, 单侧)
        min_valid: 邻域内最少有效点数
        origin_dist_threshold: 直线到原点距离阈值 (米), 小于此值判定为射线状噪声
        linearity_threshold: 线性度阈值, 法线方差/切线方差超过此值则不判定

    Returns:
        过滤后的 scan_data dict (原地修改 ranges 并返回)
    """
    ranges = scan_data['ranges']
    n = len(ranges)
    arr = np.array(ranges, dtype=np.float64)
    valid = arr > 0

    if not valid.any():
        return scan_data

    # 预计算角度和笛卡尔坐标
    angle_min = scan_data['angle_min']
    angle_inc = scan_data['angle_increment']
    angles = angle_min + np.arange(n) * angle_inc
    x_all = arr * np.cos(angles)
    y_all = arr * np.sin(angles)

    noise_mask = np.zeros(n, dtype=bool)

    for i in range(n):
        if not valid[i]:
            continue

        lo = max(0, i - window_half)
        hi = min(n, i + window_half + 1)
        mask = valid[lo:hi]
        count = mask.sum()

        if count < min_valid:
            continue

        wx = x_all[lo:hi][mask]
        wy = y_all[lo:hi][mask]

        # PCA 拟合直线: 质心和协方差
        cx, cy = wx.mean(), wy.mean()
        dx = wx - cx
        dy = wy - cy
        cxx = np.dot(dx, dx)
        cyy = np.dot(dy, dy)
        cxy = np.dot(dx, dy)

        # 最小/最大特征值
        trace = cxx + cyy
        det = cxx * cyy - cxy * cxy
        disc = max(0.0, trace * trace - 4 * det)
        sqrt_disc = np.sqrt(disc)
        lambda_min = (trace - sqrt_disc) / 2
        lambda_max = (trace + sqrt_disc) / 2

        # 线性度检查: 点集应近似为一条直线 (法线方向方差远小于切线方向)
        if lambda_max < 1e-10 or lambda_min / lambda_max > linearity_threshold:
            continue

        # 法线方向 (最小特征值对应的特征向量)
        if abs(cxy) > 1e-10:
            nx = lambda_min - cyy
            ny = cxy
        elif cxx <= cyy:
            nx, ny = 1.0, 0.0
        else:
            nx, ny = 0.0, 1.0

        norm = np.sqrt(nx * nx + ny * ny)
        if norm < 1e-10:
            continue
        nx /= norm
        ny /= norm

        # 直线到原点的距离 = |n · centroid|
        origin_dist = abs(nx * cx + ny * cy)

        if origin_dist < origin_dist_threshold:
            noise_mask[i] = True

    arr[noise_mask] = 0.0
    scan_data['ranges'] = arr.tolist()
    return scan_data


class KinectCapture:
    """Kinect v1 数据采集

    优先级:
      1. pythonnet (通过 pythonnet 调用 Microsoft.Kinect 托管 API，与 C# 服务器相同) - 推荐
      2. sdk (通过 ctypes 直接调用 Kinect10.dll) - 备选
      3. freenect (libfreenect 开源驱动) - 备选
      4. opencv (普通摄像头，仅测试用)
    """

    def __init__(self, source='auto'):
        self.rgb_frame = None
        self.depth_frame = None
        self.lock = threading.Lock()
        self.running = False
        self._source = source  # 'auto', 'pythonnet', 'sdk', 'freenect', 'opencv'
        self._backend = None   # 实际使用的后端名称
        self._rgb_cap = None
        self._depth_cap = None

        # pythonnet (Microsoft.Kinect) 相关属性
        self._kinect_sensor = None
        self._kinect_depth_format = None

        # SDK (ctypes) 相关属性
        self._kinect_dll = None
        self._nui_sensor = None
        self._video_stream_handle = None
        self._depth_stream_handle = None
        self._depth_player_index = False  # DEPTH_AND_PLAYER_INDEX 模式
        self._depth_width = KINECT_DEPTH_WIDTH
        self._depth_height = KINECT_DEPTH_HEIGHT

    def init(self):
        """初始化 Kinect 数据源"""
        backends_to_try = []

        if self._source == 'auto':
            backends_to_try = ['pythonnet', 'sdk', 'freenect', 'opencv']
        elif self._source == 'pythonnet':
            backends_to_try = ['pythonnet']
        elif self._source in ('sdk', 'pykinect'):
            backends_to_try = ['sdk']
        elif self._source == 'freenect':
            backends_to_try = ['freenect']
        elif self._source == 'opencv':
            backends_to_try = ['opencv']
        else:
            print(f"[Kinect] 未知数据源: {self._source}", flush=True)
            return False

        for backend in backends_to_try:
            print(f"[Kinect] 尝试 {backend} ...", flush=True)
            if backend == 'pythonnet':
                if self._init_pythonnet():
                    return True
            elif backend == 'sdk':
                if self._init_sdk():
                    return True
            elif backend == 'freenect':
                if self._init_freenect():
                    return True
            elif backend == 'opencv':
                if self._init_opencv():
                    return True

        print("[Kinect] 错误: 所有数据源初始化失败", flush=True)
        return False

    # ================================================================
    # 方式1: 通过 pythonnet 调用 Microsoft.Kinect 托管 API
    # 与 C# 服务器使用完全相同的 API，最可靠
    # 需安装: pip install pythonnet
    # ================================================================

    def _init_pythonnet(self):
        """通过 pythonnet 调用 Microsoft.Kinect 托管 API (与 C# 服务器相同)"""
        try:
            import clr
        except ImportError:
            print("[Kinect] pythonnet 未安装", flush=True)
            print("  安装方法: pip install pythonnet", flush=True)
            return False

        try:
            import System
            from System import Array, Byte, Int16

            # 查找 Microsoft.Kinect.dll
            asm_paths = [
                r"C:\Program Files\Microsoft SDKs\Kinect\v1.8\Assemblies\Microsoft.Kinect.dll",
                r"C:\Program Files (x86)\Microsoft SDKs\Kinect\v1.8\Assemblies\Microsoft.Kinect.dll",
                r"C:\Program Files\Microsoft SDKs\Kinect\v1.7\Assemblies\Microsoft.Kinect.dll",
                r"C:\Program Files (x86)\Microsoft SDKs\Kinect\v1.7\Assemblies\Microsoft.Kinect.dll",
            ]

            asm_loaded = False
            for path in asm_paths:
                if os.path.exists(path):
                    clr.AddReference(path)
                    asm_loaded = True
                    print(f"[Kinect] 已加载: {path}", flush=True)
                    break

            if not asm_loaded:
                try:
                    clr.AddReference("Microsoft.Kinect")
                    asm_loaded = True
                except Exception:
                    pass

            if not asm_loaded:
                print("[Kinect] 未找到 Microsoft.Kinect.dll", flush=True)
                print("  请确认 Kinect SDK 1.8 已安装", flush=True)
                return False

            from Microsoft.Kinect import (
                KinectSensor, KinectStatus,
                ColorImageFormat, DepthImageFormat,
            )

            # 查找已连接的传感器
            sensor = None
            for s in KinectSensor.KinectSensors:
                if s.Status == KinectStatus.Connected:
                    sensor = s
                    print(f"[Kinect] 找到传感器: {s.DeviceConnectionId}", flush=True)
                    break

            if sensor is None:
                print("[Kinect] 未找到已连接的 Kinect 传感器", flush=True)
                for s in KinectSensor.KinectSensors:
                    print(f"  设备: {s.DeviceConnectionId} ({s.Status})", flush=True)
                return False

            # 启用彩色流
            sensor.ColorStream.Enable(ColorImageFormat.RgbResolution640x480Fps30)
            print("[Kinect] 彩色流已启用: 640x480 @ 30fps", flush=True)

            # 启用深度流 (尝试 640x480，失败则回退 320x240)
            depth_format = None
            self._depth_player_index = False

            try:
                sensor.DepthStream.Enable(
                    DepthImageFormat.Resolution640x480Fps30)
                depth_format = DepthImageFormat.Resolution640x480Fps30
                self._depth_width = 640
                self._depth_height = 480
                print("[Kinect] 深度流已启用: 640x480 @ 30fps", flush=True)
            except Exception as e:
                print(f"[Kinect] 深度流 640x480 失败: {e}", flush=True)
                try:
                    sensor.DepthStream.Enable(
                        DepthImageFormat.Resolution320x240Fps30)
                    depth_format = DepthImageFormat.Resolution320x240Fps30
                    self._depth_width = 320
                    self._depth_height = 240
                    self._depth_player_index = True
                    print("[Kinect] 深度流已启用: 320x240 @ 30fps (含玩家索引)",
                          flush=True)
                except Exception as e2:
                    print(f"[Kinect] 深度流 320x240 也失败: {e2}", flush=True)
                    print("[Kinect] 将仅使用 RGB 流，深度使用模拟数据", flush=True)

            # 启动传感器
            sensor.Start()
            print("[Kinect] 传感器已启动", flush=True)

            self._kinect_sensor = sensor
            self._kinect_depth_format = depth_format
            self._backend = 'pythonnet'
            print("[Kinect] pythonnet + Microsoft.Kinect 初始化成功", flush=True)
            return True

        except Exception as e:
            print(f"[Kinect] pythonnet 初始化失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def _pythonnet_loop(self):
        """pythonnet 采集循环 (使用 Microsoft.Kinect 托管 API)"""
        import System
        from System import Array, Byte, Int16
        import gc

        sensor = self._kinect_sensor
        depth_format = self._kinect_depth_format

        # 预分配 .NET 缓冲区，避免每帧创建新对象
        color_buf = None
        color_buf_len = 0
        depth_buf = None
        depth_buf_len = 0
        depth_byte_buf = None

        while self.running:
            # ---- RGB ----
            try:
                color_frame = sensor.ColorStream.OpenNextFrame(33)
                if color_frame is not None:
                    # 复用或创建缓冲区
                    if color_buf_len != color_frame.PixelDataLength:
                        color_buf = Array.CreateInstance(Byte,
                                                         color_frame.PixelDataLength)
                        color_buf_len = color_frame.PixelDataLength
                    color_frame.CopyPixelDataTo(color_buf)
                    # BGRX format (4 bytes per pixel)
                    bgrx = np.frombuffer(bytes(color_buf), dtype=np.uint8)
                    bgrx = bgrx.reshape(color_frame.Height,
                                        color_frame.Width, 4)
                    bgr = cv2.cvtColor(bgrx, cv2.COLOR_BGRA2BGR)
                    with self.lock:
                        self.rgb_frame = bgr
                    color_frame.Dispose()
            except Exception:
                pass

            # ---- Depth ----
            if depth_format is not None:
                try:
                    depth_frame = sensor.DepthStream.OpenNextFrame(33)
                    if depth_frame is not None:
                        # 复用或创建缓冲区
                        if depth_buf_len != depth_frame.PixelDataLength:
                            depth_buf = Array.CreateInstance(
                                Int16, depth_frame.PixelDataLength)
                            depth_byte_buf = Array.CreateInstance(
                                System.Byte, depth_frame.PixelDataLength * 2)
                            depth_buf_len = depth_frame.PixelDataLength
                        depth_frame.CopyPixelDataTo(depth_buf)

                        # 转换 .NET Int16 数组为 numpy
                        System.Buffer.BlockCopy(
                            depth_buf, 0, depth_byte_buf, 0,
                            depth_frame.PixelDataLength * 2)
                        raw = np.frombuffer(bytes(depth_byte_buf),
                                            dtype=np.int16)
                        raw = raw.reshape(depth_frame.Height,
                                          depth_frame.Width)

                        # 提取深度值
                        if self._depth_player_index:
                            depth_mm = ((raw >> 3) & 0x0FFF).astype(
                                np.uint16)
                        else:
                            depth_mm = (raw & 0x0FFF).astype(np.uint16)

                        # 缩放到统一尺寸
                        if (depth_frame.Width != KINECT_DEPTH_WIDTH or
                                depth_frame.Height != KINECT_DEPTH_HEIGHT):
                            depth_mm = cv2.resize(
                                depth_mm,
                                (KINECT_DEPTH_WIDTH, KINECT_DEPTH_HEIGHT),
                                interpolation=cv2.INTER_NEAREST
                            )

                        with self.lock:
                            self.depth_frame = depth_mm
                        depth_frame.Dispose()
                except Exception:
                    pass
            else:
                # 无深度流，生成模拟数据 (缓存)
                if self.rgb_frame is not None:
                    shape = self.rgb_frame.shape[:2]
                    if not hasattr(self, '_sim_depth') or self._sim_depth_shape != shape:
                        h, w = shape
                        y_coords = np.arange(h, dtype=np.float32).reshape(-1, 1)
                        x_coords = np.arange(w, dtype=np.float32).reshape(1, -1)
                        center_y, center_x = h // 2, w // 2
                        dist = np.sqrt(
                            (y_coords - center_y) ** 2 +
                            (x_coords - center_x) ** 2)
                        self._sim_depth = (1500 + dist * 2).astype(np.uint16)
                        self._sim_depth_shape = shape
                    with self.lock:
                        self.depth_frame = self._sim_depth

            time.sleep(0.001)

    # ================================================================
    # 方式2: 通过 ctypes 直接调用 Kinect SDK (Kinect10.dll)
    # 无需安装任何第三方 Python 包，仅需 Kinect SDK 1.x 已安装
    # ================================================================

    def _init_sdk(self):
        """通过 ctypes 直接调用 Kinect SDK (Kinect10.dll)"""
        try:
            import ctypes
            import ctypes.wintypes
        except ImportError:
            print("[Kinect] ctypes 不可用 (非 Windows 环境)", flush=True)
            return False

        # 加载 Kinect10.dll
        try:
            self._kinect_dll = ctypes.windll.Kinect10
        except (OSError, AttributeError):
            print("[Kinect] 无法加载 Kinect10.dll", flush=True)
            print("  请确认 Kinect SDK 1.8 已安装", flush=True)
            return False

        try:
            # ---- 常量定义 (来自 NuiApi.h) ----
            # NUI_INITIALIZE_FLAGS
            NUI_INITIALIZE_FLAG_USES_COLOR = 0x00000002
            NUI_INITIALIZE_FLAG_USES_DEPTH = 0x00000004
            NUI_INITIALIZE_FLAG_USES_DEPTH_AND_PLAYER_INDEX = 0x00000008

            # NUI_IMAGE_TYPE (来自 NuiApi.h 枚举)
            #   NUI_IMAGE_TYPE_DEPTH_AND_PLAYER_INDEX = 0
            #   NUI_IMAGE_TYPE_COLOR                  = 2
            #   NUI_IMAGE_TYPE_COLOR_YUV              = 3
            #   NUI_IMAGE_TYPE_DEPTH                  = 4
            NUI_IMAGE_TYPE_DEPTH_AND_PLAYER_INDEX = 0
            NUI_IMAGE_TYPE_COLOR = 2
            NUI_IMAGE_TYPE_DEPTH = 4

            # NUI_IMAGE_RESOLUTION (来自 NuiApi.h 枚举)
            #   NUI_IMAGE_RESOLUTION_80x60     = 0
            #   NUI_IMAGE_RESOLUTION_320x240   = 1
            #   NUI_IMAGE_RESOLUTION_640x480   = 2
            #   NUI_IMAGE_RESOLUTION_1280x1024 = 3
            NUI_IMAGE_RESOLUTION_320x240 = 1
            NUI_IMAGE_RESOLUTION_640x480 = 2

            # ---- 设置函数参数类型 (确保 ctypes 正确传参) ----
            dll = self._kinect_dll
            dll.NuiInitialize.argtypes = [ctypes.c_uint32]
            dll.NuiInitialize.restype = ctypes.c_long

            dll.NuiImageStreamOpen.argtypes = [
                ctypes.c_uint32,   # eImageType
                ctypes.c_uint32,   # eResolution
                ctypes.c_uint32,   # dwImageStreamFlags
                ctypes.c_uint32,   # dwFrameLimit
                ctypes.c_void_p,   # hNextFrameEvent (NULL=不使用事件)
                ctypes.POINTER(ctypes.c_void_p),  # phStreamHandle
            ]
            dll.NuiImageStreamOpen.restype = ctypes.c_long

            dll.NuiImageStreamGetNextFrame.argtypes = [
                ctypes.c_void_p,   # hStream
                ctypes.c_uint32,   # dwMillisecondsToWait
                ctypes.c_void_p,   # pImageFrame
            ]
            dll.NuiImageStreamGetNextFrame.restype = ctypes.c_long

            dll.NuiImageStreamReleaseFrame.argtypes = [
                ctypes.c_void_p,   # hStream
                ctypes.c_void_p,   # pImageFrame
            ]
            dll.NuiImageStreamReleaseFrame.restype = ctypes.c_long

            # 注意: NuiImageBuffer_LockRect / UnlockRect 不是 DLL 导出函数
            # 它们是 INuiFrameBuffer COM 接口的方法，需通过 vtable 调用
            # 详见 _sdk_poll_frames 中的实现

            dll.NuiShutdown.argtypes = []
            dll.NuiShutdown.restype = None

            # ---- 深度流配置列表 (按优先级尝试) ----
            # Kinect for Windows 支持: DEPTH 640x480, DEPTH_AND_PLAYER_INDEX 640x480/320x240
            # Kinect for Xbox 360 支持: DEPTH_AND_PLAYER_INDEX 320x240
            # 参考 C# 托管 API: DepthImageFormat.Resolution640x480Fps30 / Resolution320x240Fps30
            depth_configs = [
                {
                    'type': NUI_IMAGE_TYPE_DEPTH,
                    'res': NUI_IMAGE_RESOLUTION_640x480,
                    'init_flag': NUI_INITIALIZE_FLAG_USES_DEPTH,
                    'label': 'DEPTH 640x480',
                    'depth_w': 640, 'depth_h': 480,
                    'player_index': False,
                },
                {
                    'type': NUI_IMAGE_TYPE_DEPTH_AND_PLAYER_INDEX,
                    'res': NUI_IMAGE_RESOLUTION_640x480,
                    'init_flag': NUI_INITIALIZE_FLAG_USES_DEPTH_AND_PLAYER_INDEX,
                    'label': 'DEPTH_AND_PLAYER_INDEX 640x480',
                    'depth_w': 640, 'depth_h': 480,
                    'player_index': True,
                },
                {
                    'type': NUI_IMAGE_TYPE_DEPTH_AND_PLAYER_INDEX,
                    'res': NUI_IMAGE_RESOLUTION_320x240,
                    'init_flag': NUI_INITIALIZE_FLAG_USES_DEPTH_AND_PLAYER_INDEX,
                    'label': 'DEPTH_AND_PLAYER_INDEX 320x240',
                    'depth_w': 320, 'depth_h': 240,
                    'player_index': True,
                },
            ]

            depth_opened = False
            for dc in depth_configs:
                print(f"[Kinect] 尝试深度流: {dc['label']} ...", flush=True)

                # 每次尝试都需要重新初始化 (NuiInitialize 的 flags 必须匹配要打开的流)
                # 先 Shutdown 再 Initialize
                dll.NuiShutdown()
                init_flags = NUI_INITIALIZE_FLAG_USES_COLOR | dc['init_flag']
                hr = dll.NuiInitialize(init_flags)
                if hr != 0:
                    print(f"  NuiInitialize 失败 (flags=0x{init_flags:X}), "
                          f"hr=0x{hr & 0xFFFFFFFF:08X}", flush=True)
                    continue

                # 重新打开 RGB 流 (NuiShutdown 后需要重新打开)
                self._video_stream_handle = ctypes.c_void_p(0)
                hr = dll.NuiImageStreamOpen(
                    NUI_IMAGE_TYPE_COLOR,
                    NUI_IMAGE_RESOLUTION_640x480,
                    0, 2,
                    ctypes.c_void_p(None),
                    ctypes.byref(self._video_stream_handle)
                )
                if hr != 0:
                    print(f"  RGB 流打开失败, hr=0x{hr & 0xFFFFFFFF:08X}", flush=True)
                    continue

                # 尝试打开深度流
                self._depth_stream_handle = ctypes.c_void_p(0)
                hr = dll.NuiImageStreamOpen(
                    dc['type'], dc['res'],
                    0, 2,
                    ctypes.c_void_p(None),
                    ctypes.byref(self._depth_stream_handle)
                )
                if hr == 0:
                    depth_opened = True
                    self._depth_player_index = dc['player_index']
                    self._depth_width = dc['depth_w']
                    self._depth_height = dc['depth_h']
                    print(f"  深度流打开成功: {dc['label']}", flush=True)
                    break
                else:
                    print(f"  深度流打开失败, hr=0x{hr & 0xFFFFFFFF:08X}", flush=True)

            if not depth_opened:
                print("[Kinect] 所有深度流配置均失败", flush=True)
                self._kinect_dll.NuiShutdown()
                return False

            self._backend = 'sdk'
            print(f"[Kinect] Kinect SDK 初始化成功 (ctypes -> Kinect10.dll)", flush=True)
            print(f"  RGB: 640x480 | Depth: {self._depth_width}x{self._depth_height}"
                  f"{' (含玩家索引)' if self._depth_player_index else ''}",
                  flush=True)
            return True

        except Exception as e:
            print(f"[Kinect] SDK 初始化异常: {e}", flush=True)
            try:
                self._kinect_dll.NuiShutdown()
            except Exception:
                pass
            return False

    def _sdk_poll_frames(self):
        """从 SDK 轮询 RGB 和深度帧

        INuiFrameBuffer 是 COM 接口，LockRect/UnlockRect 需通过 vtable 调用:
          vtable[0] = QueryInterface  (IUnknown)
          vtable[1] = AddRef          (IUnknown)
          vtable[2] = Release         (IUnknown)
          vtable[3] = LockRect
          vtable[4] = UnlockRect
          vtable[5] = GetLevelDesc
          vtable[6] = GetBuffer
          vtable[7] = GetPitch
        """
        import ctypes

        # ---- 结构体定义 ----
        class NUI_IMAGE_VIEW_AREA(ctypes.Structure):
            _fields_ = [
                ("eCentroidX", ctypes.c_long),
                ("eCentroidY", ctypes.c_long),
                ("eRotateX", ctypes.c_long),
                ("eRotateY", ctypes.c_long),
            ]

        class NUI_IMAGE_FRAME(ctypes.Structure):
            _fields_ = [
                ("liTimeStamp", ctypes.c_int64),
                ("dwFrameNumber", ctypes.c_uint32),
                ("eImageType", ctypes.c_uint32),
                ("eResolution", ctypes.c_uint32),
                ("pFrameBuffer", ctypes.c_void_p),  # INuiFrameBuffer*
                ("dwFlags", ctypes.c_uint32),
                ("dwFrameFlags", ctypes.c_uint32),
                ("eImageType2", ctypes.c_uint32),
                ("ViewArea", NUI_IMAGE_VIEW_AREA),
                ("rcFrame", ctypes.c_long * 4),
            ]

        class NUI_LOCKED_RECT(ctypes.Structure):
            _fields_ = [
                ("size", ctypes.c_uint32),
                ("pitch", ctypes.c_int),
                ("pBits", ctypes.c_void_p),
            ]

        ptr_size = ctypes.sizeof(ctypes.c_void_p)
        depth_w = self._depth_width
        depth_h = self._depth_height

        def com_lock_rect(frame_buffer_ptr, locked_rect):
            """通过 vtable 调用 INuiFrameBuffer::LockRect"""
            vtable = ctypes.c_void_p.from_address(frame_buffer_ptr).value
            func_ptr = ctypes.c_void_p.from_address(
                vtable + 3 * ptr_size
            ).value
            func_type = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.POINTER(NUI_LOCKED_RECT),
                ctypes.c_void_p,
                ctypes.c_uint32,
            )
            return func_type(func_ptr)(
                frame_buffer_ptr, 0, locked_rect, None, 0
            )

        def com_unlock_rect(frame_buffer_ptr):
            """通过 vtable 调用 INuiFrameBuffer::UnlockRect"""
            vtable = ctypes.c_void_p.from_address(frame_buffer_ptr).value
            func_ptr = ctypes.c_void_p.from_address(
                vtable + 4 * ptr_size
            ).value
            func_type = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
            )
            return func_type(func_ptr)(frame_buffer_ptr)

        # ---- 读取 RGB 帧 ----
        try:
            video_frame = NUI_IMAGE_FRAME()
            hr = self._kinect_dll.NuiImageStreamGetNextFrame(
                self._video_stream_handle, 0, ctypes.byref(video_frame)
            )
            if hr == 0:  # S_OK
                locked_rect = NUI_LOCKED_RECT()
                hr2 = com_lock_rect(video_frame.pFrameBuffer, locked_rect)
                if hr2 == 0 and locked_rect.pBits:
                    # RGB 数据为 BGRA 32位格式
                    buf_size = KINECT_RGB_HEIGHT * locked_rect.pitch
                    data = (ctypes.c_ubyte * buf_size).from_address(locked_rect.pBits)
                    bgra = np.frombuffer(data, dtype=np.uint8).copy()
                    bgra = bgra.reshape(KINECT_RGB_HEIGHT, KINECT_RGB_WIDTH, 4)
                    bgr = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
                    with self.lock:
                        self.rgb_frame = bgr

                    com_unlock_rect(video_frame.pFrameBuffer)

                self._kinect_dll.NuiImageStreamReleaseFrame(
                    self._video_stream_handle, ctypes.byref(video_frame)
                )
        except Exception:
            pass

        # ---- 读取深度帧 ----
        try:
            depth_frame = NUI_IMAGE_FRAME()
            hr = self._kinect_dll.NuiImageStreamGetNextFrame(
                self._depth_stream_handle, 0, ctypes.byref(depth_frame)
            )
            if hr == 0:  # S_OK
                locked_rect = NUI_LOCKED_RECT()
                hr2 = com_lock_rect(depth_frame.pFrameBuffer, locked_rect)
                if hr2 == 0 and locked_rect.pBits:
                    # 深度数据: 每像素 16 位
                    buf_size = depth_h * locked_rect.pitch
                    data = (ctypes.c_ubyte * buf_size).from_address(locked_rect.pBits)
                    raw = np.frombuffer(data, dtype=np.uint16).copy()
                    raw = raw.reshape(depth_h, depth_w)

                    # 提取深度值 (毫米)
                    if self._depth_player_index:
                        # DEPTH_AND_PLAYER_INDEX 模式: 低 3 位为玩家索引，高位为深度
                        depth_mm = (raw >> 3) & 0x0FFF
                    else:
                        # 纯 DEPTH 模式: 低 12 位为深度
                        depth_mm = raw & 0x0FFF

                    # 若深度分辨率与 RGB 不同，缩放到统一尺寸
                    if depth_w != KINECT_DEPTH_WIDTH or depth_h != KINECT_DEPTH_HEIGHT:
                        depth_mm = cv2.resize(
                            depth_mm.astype(np.uint16),
                            (KINECT_DEPTH_WIDTH, KINECT_DEPTH_HEIGHT),
                            interpolation=cv2.INTER_NEAREST
                        )

                    with self.lock:
                        self.depth_frame = depth_mm

                    com_unlock_rect(depth_frame.pFrameBuffer)

                self._kinect_dll.NuiImageStreamReleaseFrame(
                    self._depth_stream_handle, ctypes.byref(depth_frame)
                )
        except Exception:
            pass

    # ================================================================
    # 方式2: freenect (libfreenect 开源驱动)
    # ================================================================

    def _init_freenect(self):
        """使用 freenect (libfreenect) 初始化"""
        try:
            import freenect
        except ImportError:
            print("[Kinect] freenect 未安装", flush=True)
            return False

        try:
            ctx = freenect.init()
            dev = freenect.open_device(ctx, 0)
            if dev is not None:
                freenect.close_device(dev)
            freenect.shutdown(ctx)
            self._backend = 'freenect'
            print("[Kinect] freenect 初始化成功", flush=True)
            return True
        except Exception as e:
            print(f"[Kinect] freenect 初始化失败: {e}", flush=True)
            return False

    # ================================================================
    # 方式3: OpenCV (普通摄像头，仅测试用)
    # ================================================================

    def _init_opencv(self):
        """使用 OpenCV 打开普通摄像头 (测试用)"""
        print("[Kinect] OpenCV 模式: 扫描摄像头设备...", flush=True)

        devices = []
        for idx in range(10):
            for backend_name, backend in [('DSHOW', cv2.CAP_DSHOW), ('MSMF', cv2.CAP_MSMF)]:
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            h, w = frame.shape[:2]
                            channels = frame.shape[2] if len(frame.shape) == 3 else 1
                            devices.append({
                                'idx': idx, 'backend': backend,
                                'backend_name': backend_name,
                                'width': w, 'height': h,
                                'channels': channels,
                            })
                            print(f"  设备 {idx} ({backend_name}): {w}x{h} ch={channels}",
                                  flush=True)
                        cap.release()
                except Exception:
                    continue

        if len(devices) == 0:
            print("[Kinect] 未找到任何摄像头设备", flush=True)
            return False

        d = devices[0]
        print(f"[Kinect] 使用设备 {d['idx']} ({d['backend_name']})", flush=True)
        self._rgb_cap = cv2.VideoCapture(d['idx'], d['backend'])
        self._rgb_cap.set(cv2.CAP_PROP_FRAME_WIDTH, KINECT_RGB_WIDTH)
        self._rgb_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, KINECT_RGB_HEIGHT)
        if not self._rgb_cap.isOpened():
            print("[Kinect] 无法打开摄像头", flush=True)
            return False

        self._backend = 'opencv'
        print("[Kinect] OpenCV 模式: 仅 RGB，深度将使用模拟数据", flush=True)
        return True

    # ================================================================
    # 采集启动与循环
    # ================================================================

    def start(self):
        """开始采集"""
        self.running = True

        if self._backend == 'pythonnet':
            self._thread = threading.Thread(target=self._pythonnet_loop,
                                            daemon=True)
            self._thread.start()
        elif self._backend == 'sdk':
            self._thread = threading.Thread(target=self._sdk_loop, daemon=True)
            self._thread.start()
        elif self._backend == 'freenect':
            self._thread = threading.Thread(target=self._freenect_loop,
                                            daemon=True)
            self._thread.start()
        elif self._backend == 'opencv':
            self._thread = threading.Thread(target=self._opencv_loop,
                                            daemon=True)
            self._thread.start()

    def _sdk_loop(self):
        """SDK 轮询采集循环 (ctypes 直接调用 Kinect10.dll)"""
        print("[Kinect] SDK 采集循环已启动", flush=True)
        while self.running:
            self._sdk_poll_frames()
            time.sleep(0.005)  # ~200Hz 轮询，实际帧率由 Kinect 决定 (~30fps)

    def _freenect_loop(self):
        """freenect 采集循环"""
        import freenect

        def depth_callback(dev, depth):
            with self.lock:
                self.depth_frame = depth.copy()

        def rgb_callback(dev, rgb):
            with self.lock:
                self.rgb_frame = rgb.copy()

        try:
            freenect.runloop(depth=depth_callback, video=rgb_callback)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

    def _opencv_loop(self):
        """OpenCV 采集循环 (测试用)"""
        cached_depth = None
        cached_shape = None

        while self.running:
            if self._rgb_cap is not None:
                ret, rgb = self._rgb_cap.read()
                if ret:
                    with self.lock:
                        self.rgb_frame = rgb

                    # 无深度摄像头时生成模拟深度数据 (缓存，避免每帧重算)
                    shape = rgb.shape[:2]
                    if cached_depth is None or cached_shape != shape:
                        h, w = shape
                        y_coords = np.arange(h, dtype=np.float32).reshape(-1, 1)
                        x_coords = np.arange(w, dtype=np.float32).reshape(1, -1)
                        center_y, center_x = h // 2, w // 2
                        dist = np.sqrt(
                            (y_coords - center_y) ** 2 +
                            (x_coords - center_x) ** 2
                        )
                        cached_depth = (1500 + dist * 2).astype(np.uint16)
                        cached_shape = shape

                    with self.lock:
                        self.depth_frame = cached_depth

            time.sleep(0.001)

    def get_frames(self):
        """获取最新的 RGB 和深度帧 (RGB 必须 copy，depth 只读可不 copy)"""
        with self.lock:
            rgb = self.rgb_frame.copy() if self.rgb_frame is not None else None
            depth = self.depth_frame if self.depth_frame is not None else None
        return rgb, depth

    def get_latest_rgb(self):
        """仅获取 RGB 帧 (避免同时锁住 depth)"""
        with self.lock:
            return self.rgb_frame.copy() if self.rgb_frame is not None else None

    def stop(self):
        """停止采集"""
        self.running = False
        if self._kinect_sensor is not None:
            try:
                self._kinect_sensor.Stop()
            except Exception:
                pass
            self._kinect_sensor = None
        if self._kinect_dll is not None:
            try:
                self._kinect_dll.NuiShutdown()
            except Exception:
                pass
            self._kinect_dll = None
        if self._rgb_cap:
            self._rgb_cap.release()
        if self._depth_cap:
            self._depth_cap.release()


class TCPSender:
    """TCP 数据发送器，管理单个客户端连接

    使用发送队列 + 独立发送线程实现非阻塞发送，
    避免 sendall() 阻塞主循环导致帧率下降和 LaserScan 数据空窗。
    """

    MAX_QUEUE_SIZE = 10  # 队列最大深度, 超出时丢弃最旧消息

    def __init__(self, port, channel_name):
        self.port = port
        self.channel_name = channel_name
        self.server_sock = None
        self.client_sock = None
        self.lock = threading.Lock()
        self.seq = 0
        self._handshake_sent = False
        # 非阻塞发送: 队列 + 发送线程
        self._send_queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._send_thread = None
        self._send_running = False
        self._send_error = False  # 发送线程检测到连接错误

    def start(self):
        """启动 TCP 服务器"""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('0.0.0.0', self.port))
        self.server_sock.listen(1)
        self.server_sock.setblocking(False)
        # 启动发送线程
        self._send_running = True
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self._send_thread.start()
        print(f"  [{self.channel_name}] TCP 服务器已启动 (端口 {self.port})", flush=True)

    def _send_loop(self):
        """发送线程主循环: 从队列取数据并发送"""
        while self._send_running:
            try:
                data = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if data is None:
                continue
            with self.lock:
                sock = self.client_sock
            if sock is None:
                continue
            try:
                sock.sendall(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError,
                    socket.timeout, OSError) as e:
                print(f"  [{self.channel_name}] 数据发送失败: {e}", flush=True)
                self._send_error = True
                self._disconnect()

    def check_connection(self):
        """非阻塞检查客户端连接"""
        # 检查发送线程是否检测到连接错误
        if self._send_error:
            self._send_error = False
            return False
        with self.lock:
            if self.client_sock is not None:
                return True
        try:
            readable, _, _ = select.select([self.server_sock], [], [], 0)
            if readable:
                client_sock, addr = self.server_sock.accept()
                client_sock.settimeout(1.0)
                # 非阻塞检测探活连接（连接后立即关闭的短连接）
                r, _, _ = select.select([client_sock], [], [], 0)
                if r:
                    try:
                        if client_sock.recv(1, socket.MSG_PEEK) == b'':
                            client_sock.close()
                            return False
                    except Exception:
                        client_sock.close()
                        return False
                with self.lock:
                    self.client_sock = client_sock
                print(f"  [{self.channel_name}] 客户端已连接: {addr}", flush=True)
                return True
        except Exception as e:
            print(f"  [{self.channel_name}] Accept 错误: {e}", flush=True)
        return False

    def send_handshake(self, extra_info=None):
        """发送握手消息"""
        with self.lock:
            if self.client_sock is None:
                return False
        hs_data = {
            'type': 'handshake',
            'protocol': 'KINECT_DET_LASER_V1',
            'channel': self.channel_name,
        }
        if extra_info:
            hs_data.update(extra_info)
        payload = json.dumps(hs_data, ensure_ascii=False).encode('utf-8')
        header = struct.pack('!II', len(payload), 0)
        with self.lock:
            sock = self.client_sock
        if sock is None:
            return False
        try:
            sock.sendall(header + payload)
            self._handshake_sent = True
            return True
        except Exception as e:
            print(f"  [{self.channel_name}] 握手发送失败: {e}", flush=True)
            self._disconnect()
            return False

    def send_message(self, msg_data):
        """发送一条消息 (非阻塞, 放入发送队列)

        对于 LaserScan 消息, 使用混合编码:
          JSON 头部 (type, seq, checksum, scan 元数据) + 二进制 ranges 数据
        其他消息仍使用纯 JSON 编码。
        """
        with self.lock:
            if self.client_sock is None:
                return False
            self.seq += 1
            seq = self.seq

        # 检查是否为 LaserScan 消息且包含 ranges 数据
        scan_data = msg_data.get('scan')
        if (msg_data.get('type') == 'laser_scan' and scan_data is not None
                and 'ranges' in scan_data):
            # 混合编码: JSON 头 + 二进制 ranges
            ranges_list = scan_data['ranges']
            num_ranges = len(ranges_list)
            ranges_binary = struct.pack(f'{num_ranges}f', *ranges_list)
            # 构建 JSON 头 (不含 ranges, 用 ranges_size 替代)
            scan_meta = {k: v for k, v in scan_data.items() if k != 'ranges'}
            scan_meta['ranges_size'] = num_ranges
            msg_data['scan'] = scan_meta
            msg_data['seq'] = seq
            msg_data['checksum'] = 'pending'
            json_payload = json.dumps(msg_data, ensure_ascii=False).encode('utf-8')
            checksum = compute_checksum(json_payload + ranges_binary)
            json_payload = json_payload.replace(
                b'"checksum": "pending"',
                f'"checksum": "{checksum}"'.encode('utf-8')
            )
            # 帧格式: [8字节头][JSON载荷][二进制ranges]
            header = struct.pack('!II', len(json_payload), seq)
            data = header + json_payload + ranges_binary
        else:
            # 纯 JSON 编码 (检测结果等)
            msg_data['seq'] = seq
            msg_data['checksum'] = 'pending'
            payload = json.dumps(msg_data, ensure_ascii=False).encode('utf-8')
            checksum = compute_checksum(payload)
            payload = payload.replace(
                b'"checksum": "pending"',
                f'"checksum": "{checksum}"'.encode('utf-8')
            )
            header = struct.pack('!II', len(payload), seq)
            data = header + payload

        # 非阻塞: 放入发送队列, 队列满时丢弃最旧消息
        try:
            self._send_queue.put_nowait(data)
        except queue.Full:
            try:
                self._send_queue.get_nowait()  # 丢弃最旧消息
            except queue.Empty:
                pass
            self._send_queue.put_nowait(data)
        return True

    def _disconnect(self):
        """断开客户端连接"""
        with self.lock:
            if self.client_sock:
                try:
                    self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
                self.seq = 0
                self._handshake_sent = False
                print(f"  [{self.channel_name}] 客户端已断开", flush=True)

    def is_connected(self):
        with self.lock:
            return self.client_sock is not None

    def stop(self):
        """停止服务器"""
        self._send_running = False
        if self._send_thread is not None:
            self._send_thread.join(timeout=2.0)
        self._disconnect()
        if self.server_sock:
            self.server_sock.close()


def main():
    parser = argparse.ArgumentParser(description='Windows 端 Kinect YOLO + 深度点云服务器')
    parser.add_argument('--det-port', type=int, default=9999,
                        help='检测结果 TCP 端口')
    parser.add_argument('--scan-port', type=int, default=9998,
                        help='LaserScan 数据 TCP 端口')
    parser.add_argument('--target', type=str, default='bottle',
                        help='YOLO 检测目标类别')
    parser.add_argument('--conf', type=float, default=0.3,
                        help='YOLO 置信度阈值')
    parser.add_argument('--model', type=str, default='yolov8s.pt',
                        help='YOLO 模型路径')
    parser.add_argument('--track', action='store_true', default=True,
                        help='启用跟踪模式')
    parser.add_argument('--no-track', action='store_true',
                        help='禁用跟踪模式')
    parser.add_argument('--visualize', action='store_true', default=True,
                        help='在 Windows 端显示检测画面')
    parser.add_argument('--device', type=str, default='cuda',
                        help='推理设备 (cuda/cpu)')
    # LaserScan 参数
    parser.add_argument('--scan-height', type=int, default=DEFAULT_SCAN_HEIGHT,
                        help='深度图扫描行数 (像素行数, 默认1, 对齐ROS官方)')
    parser.add_argument('--scan-range-min', type=float, default=DEFAULT_SCAN_RANGE_MIN,
                        help='LaserScan 最小距离 (米)')
    parser.add_argument('--scan-range-max', type=float, default=DEFAULT_SCAN_RANGE_MAX,
                        help='LaserScan 最大距离 (米)')
    parser.add_argument('--scan-angle-min', type=float, default=DEFAULT_SCAN_ANGLE_MIN,
                        help='LaserScan 最小角度 (弧度)')
    parser.add_argument('--scan-angle-max', type=float, default=DEFAULT_SCAN_ANGLE_MAX,
                        help='LaserScan 最大角度 (弧度)')
    parser.add_argument('--source', type=str, default='auto',
                        choices=['auto', 'pythonnet', 'sdk', 'freenect', 'opencv'],
                        help='Kinect 数据源 (auto=自动检测, pythonnet=Microsoft.Kinect托管API, sdk=Kinect SDK(ctypes), freenect, opencv=测试)')
    args = parser.parse_args()

    track_enabled = args.track and not args.no_track

    print("=" * 60, flush=True)
    print("  Windows 端 Kinect YOLO + 深度点云服务器", flush=True)
    print("=" * 60, flush=True)
    print(f"  检测端口: {args.det_port}", flush=True)
    print(f"  扫描端口: {args.scan_port}", flush=True)
    print(f"  目标: {args.target}", flush=True)
    print(f"  置信度: {args.conf}", flush=True)
    print(f"  模型: {args.model}", flush=True)
    print(f"  跟踪: {track_enabled}", flush=True)
    print(f"  扫描行: {args.scan_height}", flush=True)
    print(f"  扫描范围: {args.scan_range_min}~{args.scan_range_max}m", flush=True)
    print(f"  扫描角度: {args.scan_angle_min}~{args.scan_angle_max}rad", flush=True)
    print(f"  数据源: {args.source}", flush=True)
    print("", flush=True)

    # ========== 1. 加载 YOLO 模型 ==========
    print("[1/4] 加载 YOLO 模型...", flush=True)
    from ultralytics import YOLO

    # 在加载模型前设置 CUDA，避免内存不足导致换页
    device = 'cpu'
    use_half = False
    if args.device == 'cuda':
        import torch
        if torch.cuda.is_available():
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  GPU 显存: {total_vram:.1f} GB", flush=True)
            device = 'cuda'
            use_half = True  # FP16 半精度推理，速度翻倍
            print(f"  CUDA 可用: {torch.cuda.get_device_name(0)}", flush=True)
        else:
            device = 'cpu'
            print("  警告: CUDA 不可用，回退到 CPU", flush=True)
    else:
        device = args.device
    print(f"  推理设备: {device} | FP16: {use_half}", flush=True)

    model = YOLO(args.model)
    model.fuse()
    model.conf = args.conf

    # 查找目标类别 ID
    target_class_id = None
    for cid, name in model.names.items():
        if name == args.target:
            target_class_id = cid
            break
    if target_class_id is not None:
        print(f"  目标类别 '{args.target}' -> ID: {target_class_id}", flush=True)
    else:
        print(f"  警告: 目标类别 '{args.target}' 不在模型列表中", flush=True)

    # 预热推理
    print("  预热推理...", flush=True)
    try:
        warmup = np.zeros((480, 640, 3), dtype=np.uint8)
        model.predict(warmup, verbose=False, device=device, save=False, half=use_half)
        print("  预热完成", flush=True)
    except Exception as e:
        print(f"  预热异常 (可忽略): {e}", flush=True)

    # ========== 2. 初始化 Kinect ==========
    print("[2/4] 初始化 Kinect v1...", flush=True)
    kinect = KinectCapture(source=args.source)
    if not kinect.init():
        print("  错误: Kinect 初始化失败", flush=True)
        sys.exit(1)
    kinect.start()
    print("  Kinect 采集已启动", flush=True)

    # 等待首帧
    print("  等待首帧...", flush=True)
    for i in range(50):
        rgb, depth = kinect.get_frames()
        if rgb is not None:
            h, w = rgb.shape[:2]
            print(f"  RGB 首帧: {w}x{h}", flush=True)
            break
        time.sleep(0.1)
    else:
        print("  警告: 等待首帧超时，继续运行", flush=True)

    # ========== 3. 启动 TCP 服务器 ==========
    print("[3/4] 启动 TCP 服务器...", flush=True)
    det_sender = TCPSender(args.det_port, 'detection')
    scan_sender = TCPSender(args.scan_port, 'laser_scan')
    det_sender.start()
    scan_sender.start()
    print("  等待 WSL2 客户端连接...", flush=True)

    # ========== 4. 主循环 ==========
    print("[4/4] 开始主循环", flush=True)
    running = True
    total_frame_count = 0
    stat_frame_count = 0
    last_log_time = time.time()
    last_fps = 0.0

    if args.visualize:
        cv2.namedWindow('Kinect YOLO+LaserScan Server', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Kinect YOLO+LaserScan Server', 960, 720)

    try:
        while running:
            t_loop_start = time.perf_counter()

            # 检查客户端连接
            det_connected = det_sender.check_connection()
            scan_connected = scan_sender.check_connection()

            # 新连接时发送握手 (延迟到获取帧之后)
            need_det_handshake = det_connected and not det_sender._handshake_sent
            need_scan_handshake = scan_connected and not scan_sender._handshake_sent

            # 获取帧 (RGB 和 Depth 分开获取，减少锁持有时间)
            t_get_frame = time.perf_counter()
            rgb = kinect.get_latest_rgb()
            t_after_frame = time.perf_counter()
            if rgb is None:
                time.sleep(0.005)
                continue

            total_frame_count += 1

            # 发送握手 (在获取到帧之后)
            if need_det_handshake:
                img_h, img_w = rgb.shape[:2]
                det_sender.send_handshake({
                    'image_width': img_w,
                    'image_height': img_h,
                })
            if need_scan_handshake:
                scan_sender.send_handshake({
                    'scan_height': args.scan_height,
                    'range_min': args.scan_range_min,
                    'range_max': args.scan_range_max,
                    'angle_min': args.scan_angle_min,
                    'angle_max': args.scan_angle_max,
                    'angle_increment': DEFAULT_SCAN_ANGLE_INCREMENT,
                })

            # ---- YOLO 检测 ----
            t_yolo_start = time.perf_counter()

            classes_filter = [target_class_id] if target_class_id is not None else None
            # 统一使用 model.predict()，避免 model.track(persist=True) 导致内存泄漏和性能退化
            results = model.predict(rgb, show=False, conf=args.conf,
                                    classes=classes_filter,
                                    verbose=False, device=device,
                                    save=False, half=use_half)
            t_yolo_end = time.perf_counter()

            # 构建检测结果
            detections = []
            for result in results[0].boxes:
                cls_id = int(result.cls.item())
                class_name = results[0].names[cls_id]
                if target_class_id is not None and cls_id != target_class_id:
                    continue
                x1, y1, x2, y2 = [int(v) for v in result.xyxy[0].tolist()]
                conf = float(result.conf.item())
                detections.append({
                    'class': class_name,
                    'class_id': cls_id,
                    'confidence': round(conf, 4),
                    'xmin': x1, 'ymin': y1, 'xmax': x2, 'ymax': y2,
                    'track_id': -1,
                })

            # 发送检测结果
            if det_sender.is_connected():
                det_msg = {
                    'type': 'detection',
                    'timestamp': time.time(),
                    'image_width': rgb.shape[1],
                    'image_height': rgb.shape[0],
                    'detections': detections,
                }
                det_sender.send_message(det_msg)

            # 释放 YOLO results 占用的 GPU/CPU 内存
            del results

            # ---- 深度图转 LaserScan (仅在有扫描客户端时获取深度) ----
            depth = None
            if scan_sender.is_connected():
                with kinect.lock:
                    depth = kinect.depth_frame if kinect.depth_frame is not None else None
                if depth is not None:
                    scan_data = depth_to_laserscan(
                        depth,
                        scan_height=args.scan_height,
                        range_min=args.scan_range_min,
                        range_max=args.scan_range_max,
                        angle_min=args.scan_angle_min,
                        angle_max=args.scan_angle_max,
                    )
                    if scan_data is not None:
                        filter_radial_noise(scan_data)
                        scan_msg = {
                            'type': 'laser_scan',
                            'timestamp': time.time(),
                            'scan': scan_data,
                        }
                        scan_sender.send_message(scan_msg)

            # ---- 统计 ----
            stat_frame_count += 1
            now = time.time()
            if now - last_log_time >= 2.0:
                last_fps = stat_frame_count / (now - last_log_time)
                det_status = "已连接" if det_sender.is_connected() else "等待"
                scan_status = "已连接" if scan_sender.is_connected() else "等待"
                has_depth = "有" if depth is not None else "无"
                yolo_ms = (t_yolo_end - t_yolo_start) * 1000
                frame_ms = (t_after_frame - t_get_frame) * 1000
                total_ms = (time.perf_counter() - t_loop_start) * 1000
                print(f"[Server] FPS: {last_fps:.1f} | YOLO: {yolo_ms:.0f}ms | "
                      f"Frame: {frame_ms:.0f}ms | Total: {total_ms:.0f}ms | "
                      f"检测: {len(detections)}个 | 深度: {has_depth} | "
                      f"帧 #{total_frame_count}", flush=True)
                stat_frame_count = 0
                last_log_time = now

                # 定期强制 GC，防止 Python 对象累积导致内存增长
                import gc
                gc.collect(1)

            # ---- 可视化 ----
            if args.visualize:
                vis_frame = rgb.copy()

                # 绘制检测框
                for det in detections:
                    x1, y1 = det['xmin'], det['ymin']
                    x2, y2 = det['xmax'], det['ymax']
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"{det['class']} {det['confidence']:.2f}"
                    if det['track_id'] >= 0:
                        label = f"ID:{det['track_id']} {label}"
                    cv2.putText(vis_frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                # 绘制扫描区域 (对齐官方: cy - scan_height/2 到 cy + scan_height/2)
                scan_y_start = max(0, int(KINECT_CY - args.scan_height / 2.0))
                scan_y_end = min(vis_frame.shape[0] - 1, int(KINECT_CY + args.scan_height / 2.0))
                cv2.line(vis_frame, (0, scan_y_start), (vis_frame.shape[1], scan_y_start),
                         (0, 0, 255), 1)
                if scan_y_end != scan_y_start:
                    cv2.line(vis_frame, (0, scan_y_end), (vis_frame.shape[1], scan_y_end),
                             (0, 0, 255), 1)

                # 状态信息
                det_status = "Det:ON" if det_sender.is_connected() else "Det:OFF"
                scan_status = "Scan:ON" if scan_sender.is_connected() else "Scan:OFF"
                cv2.putText(vis_frame, f"FPS: {last_fps:.1f} | {det_status} | {scan_status}",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow('Kinect YOLO+LaserScan Server', vis_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    running = False
                    break

    except KeyboardInterrupt:
        print("\n[Server] 正在关闭...", flush=True)
    finally:
        kinect.stop()
        det_sender.stop()
        scan_sender.stop()
        if args.visualize:
            cv2.destroyAllWindows()
        print("[Server] 已清理完毕", flush=True)


if __name__ == '__main__':
    main()
