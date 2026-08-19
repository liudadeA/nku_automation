#!/usr/bin/env python3
"""Color-based object detection using Kinect RGB + depth for 3D localization."""

import math
import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image, CameraInfo
import tf2_ros
import tf2_geometry_msgs
from geometry_msgs.msg import PointStamped


class ObjectDetector:
    def __init__(self):
        self.bridge = CvBridge()
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # Load params
        self._load_color_ranges()
        self.min_area = rospy.get_param('~min_contour_area', 300)
        self.kernel_size = rospy.get_param('~morph_kernel_size', 5)
        self.timeout = rospy.get_param('~detection_timeout', 30.0)
        self.debug = rospy.get_param('~debug', True)

        # Topic names
        rgb_topic = rospy.get_param('~rgb_topic', '/camera/rgb/image_raw')
        depth_topic = rospy.get_param('~depth_topic', '/camera/depth_registered/image_raw')
        info_topic = rospy.get_param('~camera_info_topic', '/camera/rgb/camera_info')

        # Latest data
        self._rgb = None
        self._depth = None
        self._camera_info = None
        self._rgb_time = None

        # Subscribers
        self._rgb_sub = rospy.Subscriber(rgb_topic, Image, self._rgb_cb)
        self._depth_sub = rospy.Subscriber(depth_topic, Image, self._depth_cb)
        self._info_sub = rospy.Subscriber(info_topic, CameraInfo, self._info_cb)

        # Fallback depth topic for simulation (Gazebo publishes unregistered depth)
        self._depth_fallback_sub = None
        if depth_topic != '/camera/depth/image_raw':
            self._depth_fallback_sub = rospy.Subscriber(
                '/camera/depth/image_raw', Image, self._depth_cb)

        # Debug publisher
        self._debug_pub = None
        if self.debug:
            self._debug_pub = rospy.Publisher('/object_detector/debug_image', Image, queue_size=1)

        rospy.loginfo('ObjectDetector: ready (HSV ranges loaded, min_area=%d)', self.min_area)

    def _load_color_ranges(self):
        """Load HSV color ranges from param server."""
        self.color_ranges = []
        ranges = rospy.get_param('~color_ranges', {})
        for key in ranges:
            r = ranges[key]
            lower = np.array(r['hsv_lower'], dtype=np.uint8)
            upper = np.array(r['hsv_upper'], dtype=np.uint8)
            self.color_ranges.append((lower, upper))
        if not self.color_ranges:
            rospy.logwarn('No color ranges configured, using default red range')
            self.color_ranges = [
                (np.array([0, 100, 100], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)),
                (np.array([170, 100, 100], dtype=np.uint8), np.array([179, 255, 255], dtype=np.uint8)),
            ]

    def _rgb_cb(self, msg):
        self._rgb = msg
        self._rgb_time = msg.header.stamp

    def _depth_cb(self, msg):
        self._depth = msg

    def _info_cb(self, msg):
        self._camera_info = msg

    def _wait_for_data(self, timeout=5.0):
        """Wait until RGB, depth, and camera_info are available."""
        start = rospy.Time.now()
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            if self._rgb is not None and self._depth is not None and self._camera_info is not None:
                return True
            if (rospy.Time.now() - start).to_sec() > timeout:
                rospy.logerr('ObjectDetector: timeout waiting for camera data')
                return False
            rate.sleep()
        return False

    def detect_2d(self):
        """
        Run color detection on latest RGB image.
        Returns (cx, cy, annotated_image) centroid in pixel coordinates or (None, None, None).
        """
        if self._rgb is None:
            return None, None, None

        try:
            bgr = self.bridge.imgmsg_to_cv2(self._rgb, 'bgr8')
        except CvBridgeError as e:
            rospy.logerr('ObjectDetector: cv_bridge error %s', e)
            return None, None, None

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        # Combine all color ranges
        mask = None
        for lower, upper in self.color_ranges:
            m = cv2.inRange(hsv, lower, upper)
            if mask is None:
                mask = m
            else:
                mask = cv2.bitwise_or(mask, m)

        # Morphological opening to remove noise
        kernel = np.ones((self.kernel_size, self.kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter by area and find largest
        best = None
        best_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_area and area > best_area:
                best = cnt
                best_area = area

        annotated = bgr.copy() if self.debug else None

        if best is not None:
            M = cv2.moments(best)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])

                if self.debug:
                    cv2.drawContours(annotated, [best], -1, (0, 255, 0), 2)
                    cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(annotated, '(%d, %d) area=%d' % (cx, cy, best_area),
                                (cx + 10, cy - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                return cx, cy, annotated

        if self.debug and annotated is not None:
            cv2.putText(annotated, 'No object detected', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return None, None, annotated

    def get_3d_position(self, u, v):
        """
        Convert pixel (u,v) + depth to 3D point in camera_rgb_optical_frame.
        Returns (X, Y, Z) in meters or (None, None, None) if no valid depth.
        """
        if self._depth is None or self._camera_info is None:
            return None, None, None

        try:
            depth_img = self.bridge.imgmsg_to_cv2(self._depth, 'passthrough')
        except CvBridgeError:
            return None, None, None

        h, w = depth_img.shape[:2]
        if u < 0 or u >= w or v < 0 or v >= h:
            return None, None, None

        # Get depth at centroid, with neighbor averaging for robustness
        depth_val = self._get_robust_depth(depth_img, u, v)
        if depth_val <= 0 or math.isnan(depth_val):
            rospy.logwarn('ObjectDetector: invalid depth at (%d,%d): %.3f', u, v, depth_val)
            return None, None, None

        # Project to 3D using camera intrinsics
        K = self._camera_info.K
        fx = K[0]
        fy = K[4]
        cx = K[2]
        cy = K[5]

        X = (u - cx) * depth_val / fx
        Y = (v - cy) * depth_val / fy
        Z = depth_val

        return X, Y, Z

    def _get_robust_depth(self, depth_img, u, v, window=3):
        """Average depth over a small window around (u,v), excluding zeros/NaNs."""
        r = window // 2
        h, w = depth_img.shape[:2]
        u0 = max(0, u - r)
        u1 = min(w, u + r + 1)
        v0 = max(0, v - r)
        v1 = min(h, v + r + 1)
        patch = depth_img[v0:v1, u0:u1]
        valid = patch[(patch > 0) & (~np.isnan(patch))]
        if len(valid) == 0:
            return 0.0
        return float(np.median(valid))

    def transform_to_frame(self, x, y, z, target_frame, source_frame='camera_rgb_optical_frame'):
        """
        Transform a 3D point from source frame to target frame.
        Returns (x, y, z) in target frame or (None, None, None) if unavailable.
        """
        point = PointStamped()
        point.header.frame_id = source_frame
        point.header.stamp = rospy.Time(0)  # latest transform
        point.point.x = x
        point.point.y = y
        point.point.z = z

        try:
            # Quick check if transform exists (with short timeout to avoid hangs)
            available = self.tf_buffer.can_transform(
                target_frame, source_frame, rospy.Time(0),
                rospy.Duration(0.5))
            if not available:
                rospy.loginfo('ObjectDetector: TF %s -> %s not available',
                              source_frame, target_frame)
                return None, None, None
            transformed = self.tf_buffer.transform(point, target_frame)
            return transformed.point.x, transformed.point.y, transformed.point.z
        except (tf2_ros.TransformException, tf2_ros.LookupException,
                tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException,
                rospy.exceptions.ROSInterruptException) as e:
            rospy.loginfo('ObjectDetector: TF %s -> %s: %s',
                          source_frame, target_frame, e)
            return None, None, None

    def transform_to_arm_base(self, x, y, z, source_frame='camera_rgb_optical_frame'):
        """Backward-compatible wrapper."""
        return self.transform_to_frame(x, y, z, 'arm_base', source_frame)

    def publish_debug(self, annotated):
        """Publish annotated debug image."""
        if self._debug_pub is not None and annotated is not None:
            try:
                img_msg = self.bridge.cv2_to_imgmsg(annotated, 'bgr8')
                self._debug_pub.publish(img_msg)
            except CvBridgeError:
                pass

    def detect_and_locate(self, target_frame='arm_base'):
        """
        Full detection pipeline:
        1. Color detection in RGB image
        2. Depth-based 3D localization in camera frame
        3. TF transform to target frame (default: arm_base)

        Returns (x, y, z) in target frame, or (None, None, None) on failure.
        """
        cx, cy, annotated = self.detect_2d()
        self.publish_debug(annotated)

        if cx is None:
            return None, None, None

        X, Y, Z = self.get_3d_position(cx, cy)
        if X is None:
            return None, None, None

        rospy.loginfo('ObjectDetector: 3D in camera: (%.3f, %.3f, %.3f)', X, Y, Z)

        if target_frame == 'camera_rgb_optical_frame':
            return X, Y, Z

        # Try TF to target frame, fall back to camera frame if unavailable
        x_arm, y_arm, z_arm = self.transform_to_arm_base(X, Y, Z)
        if x_arm is not None:
            rospy.loginfo('ObjectDetector: 3D in arm_base: (%.3f, %.3f, %.3f)',
                          x_arm, y_arm, z_arm)
        else:
            # TF failed (e.g., no arm_base in sim), use camera frame position
            rospy.loginfo('ObjectDetector: using camera frame position')
            x_arm, y_arm, z_arm = X, Y, Z

        return x_arm, y_arm, z_arm


if __name__ == '__main__':
    rospy.init_node('object_detector')
    detector = ObjectDetector()

    if not detector._wait_for_data(timeout=10.0):
        rospy.logerr('Failed to get camera data')
        rospy.signal_shutdown('No camera data')

    rate = rospy.Rate(5)
    while not rospy.is_shutdown():
        x, y, z = detector.detect_and_locate()
        if x is not None:
            rospy.loginfo('Object at arm_base: (%.3f, %.3f, %.3f)', x, y, z)
        rate.sleep()
