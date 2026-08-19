#!/usr/bin/env python3
"""
Simulation test: Navigation + Object Detection (no arm).
Drives robot to target, detects colored blocks, returns home.
"""

import rospy
import sys
import math

sys.path.insert(0, '/home/liu/catkin_ws/src/my_pkg/scripts')
from slam import NavToPoint
from object_detector import ObjectDetector


class SimTest:
    def __init__(self):
        rospy.loginfo('=' * 50)
        rospy.loginfo('SimTest: Navigation + Detection Test')
        rospy.loginfo('=' * 50)

        # Navigation
        rospy.loginfo('Connecting to move_base...')
        self.navigator = NavToPoint()

        # Object detector
        rospy.loginfo('Initializing object detector...')
        self.detector = ObjectDetector()

    def run(self):
        # Wait for camera data
        rospy.loginfo('Waiting for camera data...')
        if not self.detector._wait_for_data(timeout=30.0):
            rospy.logerr('No camera data! Is Gazebo running with Kinect?')
            return

        rospy.loginfo('Camera data OK! Starting test sequence...')

        # Phase 1: Navigate to observation point (1.5m forward = near red block)
        target = [1.5, 0.0, 0.0]
        rospy.loginfo('Phase 1: Navigate to (%.1f, %.1f)', target[0], target[1])

        try:
            success = self.navigator.goto(target, blocking=True)
            if success:
                rospy.loginfo('Navigation SUCCESS')
            else:
                rospy.logerr('Navigation FAILED')
        except Exception as e:
            rospy.logwarn('Navigation error (may be OK in sim): %s', e)

        # Phase 2: Detect objects
        rospy.loginfo('Phase 2: Detecting colored objects...')
        rospy.sleep(2.0)  # Stabilize

        found_count = 0
        attempts = 0
        max_attempts = 30

        while attempts < max_attempts and not rospy.is_shutdown():
            try:
                cx, cy, annotated = self.detector.detect_2d()

                if cx is not None:
                    rospy.loginfo('DETECTED object at pixel (%d, %d)', cx, cy)
                    X, Y, Z = self.detector.get_3d_position(cx, cy)
                    if X is not None:
                        rospy.loginfo('  3D in camera: (%.3f, %.3f, %.3f) m', X, Y, Z)
                    found_count += 1
                else:
                    rospy.loginfo_throttle(3.0, 'Scanning for objects... (attempt %d/%d)',
                                           attempts, max_attempts)

                self.detector.publish_debug(annotated)
            except Exception as e:
                rospy.logwarn('Detection error: %s', e)

            rospy.sleep(0.5)
            attempts += 1

        rospy.loginfo('Detection complete: found %d objects in %d attempts',
                      found_count, attempts)

        # Phase 3: Return home
        rospy.loginfo('Phase 3: Returning home...')
        try:
            home = [0.0, 0.0, 0.0]
            success = self.navigator.goto(home, blocking=True)
            if success:
                rospy.loginfo('Return SUCCESS')
            else:
                rospy.logerr('Return FAILED')
        except Exception as e:
            rospy.logwarn('Return navigation error: %s', e)

        rospy.loginfo('=' * 50)
        rospy.loginfo('SimTest COMPLETE')
        rospy.loginfo('=' * 50)


if __name__ == '__main__':
    rospy.init_node('sim_test')
    test = SimTest()
    try:
        test.run()
    except Exception as e:
        rospy.logerr('SimTest error: %s', e)
        import traceback
        traceback.print_exc()
