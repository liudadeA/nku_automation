#!/usr/bin/env python3
"""
Navigate to colored blocks: Red -> Green -> Blue.
1. Detect block via camera → compute map position → navigate there
2. If detection fails, rotate / move to search position
3. After visiting all blocks, return to start.

Usage:
  rosrun my_pkg nav_to_blocks.py
"""

import rospy
import sys
import math
import tf2_ros
import numpy as np
from geometry_msgs.msg import PointStamped, Twist

sys.path.insert(0, '/home/liu/catkin_ws/src/my_pkg/scripts')
from slam import NavToPoint
from object_detector import ObjectDetector


COLOR_ORDER = ['red', 'green', 'blue']

DEFAULT_HSV = {
    'red':   {'range1': {'hsv_lower': [0, 80, 50], 'hsv_upper': [10, 255, 255]},
              'range2': {'hsv_lower': [170, 80, 50], 'hsv_upper': [179, 255, 255]}},
    'green': {'range1': {'hsv_lower': [40, 80, 50], 'hsv_upper': [80, 255, 255]}},
    'blue':  {'range1': {'hsv_lower': [100, 80, 50], 'hsv_upper': [130, 255, 255]}},
}


class NavToBlocks:
    def __init__(self):
        rospy.init_node('nav_to_blocks')
        rospy.loginfo('=' * 50)
        rospy.loginfo('NavToBlocks: Red -> Green -> Blue')
        rospy.loginfo('=' * 50)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        self.navigator = NavToPoint()
        self.detector = ObjectDetector()
        self.cmd_vel = rospy.Publisher('/cmd_vel_mux/input/navi', Twist, queue_size=1)

        self.start_pos = (0.0, 0.0)
        self.visited = set()

    def _set_color(self, name):
        hsv = DEFAULT_HSV.get(name, DEFAULT_HSV['red'])
        self.detector.color_ranges = []
        for r in hsv.values():
            self.detector.color_ranges.append(
                (np.array(r['hsv_lower'], dtype=np.uint8),
                 np.array(r['hsv_upper'], dtype=np.uint8)))
        rospy.loginfo('  Looking for: %s', name)

    def _get_map_position(self, x, y, z):
        pt = PointStamped()
        pt.header.frame_id = 'camera_rgb_optical_frame'
        pt.header.stamp = rospy.Time(0)
        pt.point.x = x; pt.point.y = y; pt.point.z = z
        try:
            self.tf_buffer.can_transform('map', pt.header.frame_id,
                                         rospy.Time(0), rospy.Duration(1.0))
            pt_map = self.tf_buffer.transform(pt, 'map')
            return pt_map.point.x, pt_map.point.y, pt_map.point.z
        except Exception as e:
            rospy.logwarn('TF cam->map: %s', e)
            return None, None, None

    def _get_pose(self):
        try:
            self.tf_buffer.can_transform('map', 'base_link',
                                         rospy.Time(0), rospy.Duration(1.0))
            t = self.tf_buffer.lookup_transform('map', 'base_link', rospy.Time(0))
            return (t.transform.translation.x,
                    t.transform.translation.y)
        except Exception:
            return None, None

    def _rotate(self, angle_rad, speed=0.5):
        """Rotate in place by approximate angle."""
        duration = abs(angle_rad) / speed
        twist = Twist()
        twist.angular.z = speed if angle_rad > 0 else -speed
        t0 = rospy.Time.now()
        rate = rospy.Rate(20)
        while (rospy.Time.now() - t0).to_sec() < duration and not rospy.is_shutdown():
            self.cmd_vel.publish(twist)
            rate.sleep()
        # Stop
        self.cmd_vel.publish(Twist())
        rospy.sleep(0.5)

    def _navigate(self, x, y, label="target"):
        """Navigate to map position. Returns True on success."""
        rospy.loginfo('  Navigate to %s: (%.2f, %.2f)', label, x, y)
        try:
            return self.navigator.goto([x, y, 0.0], blocking=True)
        except Exception as e:
            rospy.logwarn('  Nav error: %s', e)
            return False

    def _detect_block(self, color_name, timeout=20.0):
        """Scan camera frames for a specific color block.
        Returns (x, y) in map frame or (None, None)."""
        self._set_color(color_name)
        start = rospy.Time.now()

        while (rospy.Time.now() - start).to_sec() < timeout and not rospy.is_shutdown():
            cx, cy, annotated = self.detector.detect_2d()
            self.detector.publish_debug(annotated)

            if cx is not None:
                X, Y, Z = self.detector.get_3d_position(cx, cy)
                if X is not None and Z > 0.2:
                    mx, my, mz = self._get_map_position(X, Y, Z)
                    if mx is not None:
                        rospy.loginfo('  Detected %s: cam=(%.2f,%.2f,%.2f) map=(%.2f,%.2f)',
                                      color_name, X, Y, Z, mx, my)
                        return mx, my

            rospy.sleep(0.3)

        rospy.logwarn('  %s not found in %.1fs', color_name, timeout)
        return None, None

    def run(self):
        # Wait for camera and nav
        rospy.loginfo('Waiting for camera/nav ready...')
        if not self.detector._wait_for_data(timeout=30.0):
            rospy.logerr('No camera data!')
            return

        # Let AMCL converge
        rospy.loginfo('Waiting for AMCL convergence (5s)...')
        rospy.sleep(5.0)

        # Record start
        pos = self._get_pose()
        if pos:
            self.start_pos = pos
        rospy.loginfo('Start: (%.2f, %.2f)', *self.start_pos)

        # ---- Visit each block ----
        for color in COLOR_ORDER:
            if color in self.visited:
                continue
            rospy.loginfo('=== %s ===', color.upper())

            # Detect
            mx, my = self._detect_block(color, timeout=15.0)

            if mx is None:
                # Try rotating to find it
                rospy.loginfo('  Rotating to search...')
                for angle in [0.8, -1.6, 0.8]:
                    self._rotate(angle, speed=0.6)
                    mx, my = self._detect_block(color, timeout=8.0)
                    if mx is not None:
                        break

            if mx is not None:
                ok = self._navigate(mx, my, color)
                if ok:
                    rospy.loginfo('  Arrived at %s!', color)
                    self.visited.add(color)
                else:
                    rospy.logwarn('  Nav to %s failed, trying closer approach', color)
                    # Navigate partway and re-detect
                    px, py = self._get_pose() or (0, 0)
                    mid_x = px + (mx - px) * 0.5
                    mid_y = py + (my - py) * 0.5
                    self._navigate(mid_x, mid_y, 'midpoint')
                    mx2, my2 = self._detect_block(color, timeout=10.0)
                    if mx2 is not None:
                        self._navigate(mx2, my2, color)
                        self.visited.add(color)
            else:
                rospy.logwarn('  Skipping %s', color)

            rospy.sleep(1.0)

        # ---- Return home ----
        rospy.loginfo('=== Returning home ===')
        self._navigate(self.start_pos[0], self.start_pos[1], 'home')

        rospy.loginfo('=' * 50)
        rospy.loginfo('COMPLETE. Visited: %s', sorted(self.visited))
        rospy.loginfo('=' * 50)


if __name__ == '__main__':
    try:
        NavToBlocks().run()
    except Exception as e:
        rospy.logerr('Error: %s', e)
        import traceback
        traceback.print_exc()
