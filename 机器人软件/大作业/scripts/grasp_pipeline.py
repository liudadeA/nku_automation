#!/usr/bin/env python3
"""
Grasp Pipeline State Machine.
Orchestrates: navigate → detect object → arm grasp → return home.

Usage:
  rosrun my_pkg grasp_pipeline.py _nav_target_x:=2.0 _nav_target_y:=0.5 _nav_target_yaw:=90
"""

import sys
import math
import rospy

# Reuse existing navigation module
sys.path.insert(0, '/home/liu/catkin_ws/src/my_pkg/scripts')
from slam import NavToPoint
from arm_state import ArmState
from arm_commander import ArmCommander
from arm_kinematics import ArmKinematics
from arm_grasp_planner import GraspPlanner
from object_detector import ObjectDetector


class GraspPipeline:
    def __init__(self):
        rospy.loginfo('=' * 60)
        rospy.loginfo('GraspPipeline: initializing...')
        rospy.loginfo('=' * 60)

        # Navigation targets
        self.nav_target = {
            'x': rospy.get_param('~nav_target_x', 3.0),
            'y': rospy.get_param('~nav_target_y', 0.0),
            'yaw': rospy.get_param('~nav_target_yaw', 90.0),
        }
        self.home_pos = {
            'x': rospy.get_param('~home_x', 0.0),
            'y': rospy.get_param('~home_y', 0.0),
            'yaw': rospy.get_param('~home_yaw', 0.0),
        }

        # Subsystems
        rospy.loginfo('Initializing navigation client...')
        self.navigator = NavToPoint()

        rospy.loginfo('Initializing arm state monitor...')
        self.arm_state = ArmState()

        rospy.loginfo('Initializing arm commander...')
        self.arm_commander = ArmCommander(arm_state=self.arm_state)

        rospy.loginfo('Initializing kinematics...')
        self.kinematics = ArmKinematics()

        rospy.loginfo('Initializing grasp planner...')
        self.grasp_planner = GraspPlanner(kinematics=self.kinematics)

        rospy.loginfo('Initializing object detector...')
        self.detector = ObjectDetector()

        # State
        self.current_state = 'INIT'
        self.retry_counts = {}
        self.max_retries = rospy.get_param('~max_retries', 3)

        rospy.loginfo('GraspPipeline: ready.')
        rospy.loginfo('  Target: (%.1f, %.1f, %.0f deg)',
                      self.nav_target['x'], self.nav_target['y'], self.nav_target['yaw'])
        rospy.loginfo('  Home:   (%.1f, %.1f, %.0f deg)',
                      self.home_pos['x'], self.home_pos['y'], self.home_pos['yaw'])

    def _transition(self, new_state):
        rospy.loginfo('--- %s -> %s ---', self.current_state, new_state)
        self.current_state = new_state

    def _retry_or_abort(self, phase):
        """Return True to retry, False to abort."""
        self.retry_counts[phase] = self.retry_counts.get(phase, 0) + 1
        if self.retry_counts[phase] <= self.max_retries:
            rospy.logwarn('Retry %s (%d/%d)', phase, self.retry_counts[phase], self.max_retries)
            return True
        rospy.logerr('Max retries reached for %s, aborting', phase)
        return False

    def run(self):
        """Run the complete pipeline state machine."""
        rospy.loginfo('GraspPipeline: starting mission')

        while not rospy.is_shutdown():
            if self.current_state == 'INIT':
                self._transition('HOME_ARM')

            elif self.current_state == 'HOME_ARM':
                rospy.loginfo('Moving arm to home position...')
                if self.arm_commander.go_to_home(blocking=True):
                    self._transition('NAVIGATE_TO_TARGET')
                else:
                    rospy.logwarn('Arm home failed, retrying...')
                    rospy.sleep(1.0)

            elif self.current_state == 'NAVIGATE_TO_TARGET':
                target = [self.nav_target['x'], self.nav_target['y'], self.nav_target['yaw']]
                rospy.loginfo('Navigating to target (%.1f, %.1f)', target[0], target[1])
                success = self.navigator.goto(target, blocking=True)
                if success:
                    rospy.loginfo('Navigation succeeded')
                    self.retry_counts['navigate'] = 0
                    self._transition('SEARCH_OBJECT')
                else:
                    rospy.logerr('Navigation failed')
                    if self._retry_or_abort('navigate'):
                        self._transition('NAVIGATE_TO_TARGET')
                    else:
                        self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'SEARCH_OBJECT':
                rospy.loginfo('Waiting for camera data stabilization...')
                rospy.sleep(2.0)
                if self.detector._wait_for_data(timeout=5.0):
                    self._transition('DETECT_OBJECT')
                else:
                    rospy.logwarn('No camera data available')
                    if self._retry_or_abort('camera'):
                        self._transition('SEARCH_OBJECT')
                    else:
                        self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'DETECT_OBJECT':
                rospy.loginfo('Detecting object...')
                timeout = rospy.get_param('~detection_timeout', 30.0)
                start = rospy.Time.now()
                x, y, z = None, None, None

                while not rospy.is_shutdown():
                    x, y, z = self.detector.detect_and_locate(target_frame='arm_base')
                    if x is not None:
                        break
                    if (rospy.Time.now() - start).to_sec() > timeout:
                        rospy.logwarn('Detection timeout after %.1fs', timeout)
                        break
                    rospy.sleep(0.5)

                if x is not None:
                    rospy.loginfo('Object detected at arm_base: (%.3f, %.3f, %.3f)', x, y, z)
                    self.object_pos = (x, y, z)
                    self._transition('PLAN_GRASP')
                else:
                    rospy.logwarn('No object found')
                    if self._retry_or_abort('detect'):
                        self._transition('SEARCH_OBJECT')
                    else:
                        self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'PLAN_GRASP':
                x, y, z = self.object_pos
                plan = self.grasp_planner.plan(x, y, z)
                if plan is not None:
                    self.grasp_plan = plan
                    self._transition('APPROACH_PREGRASP')
                else:
                    rospy.logerr('Grasp planning failed')
                    self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'APPROACH_PREGRASP':
                rospy.loginfo('Moving arm to pregrasp position...')
                if self.arm_commander.move_all(self.grasp_plan['pregrasp'], blocking=True):
                    self._transition('APPROACH_GRASP')
                else:
                    rospy.logwarn('Pregrasp move failed')
                    self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'APPROACH_GRASP':
                rospy.loginfo('Moving arm to grasp position...')
                if self.arm_commander.move_all(self.grasp_plan['grasp'], blocking=True):
                    self._transition('CLOSE_GRIPPER')
                else:
                    rospy.logwarn('Grasp move failed')
                    self.arm_commander.move_all(self.grasp_plan['pregrasp'], blocking=False)
                    rospy.sleep(1.0)
                    self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'CLOSE_GRIPPER':
                rospy.loginfo('Closing gripper...')
                if self.arm_commander.set_gripper(open_gripper=False, blocking=True):
                    rospy.sleep(0.5)
                    self._transition('LIFT_OBJECT')
                else:
                    rospy.logwarn('Gripper close failed')
                    self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'LIFT_OBJECT':
                rospy.loginfo('Lifting object...')
                if self.arm_commander.move_all(self.grasp_plan['lift'], blocking=True):
                    self._transition('NAVIGATE_HOME')
                else:
                    rospy.logwarn('Lift move failed')
                    self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'NAVIGATE_HOME':
                home = [self.home_pos['x'], self.home_pos['y'], self.home_pos['yaw']]
                rospy.loginfo('Returning home (%.1f, %.1f)...', home[0], home[1])
                success = self.navigator.goto(home, blocking=True)
                if success:
                    rospy.loginfo('Return navigation succeeded')
                    self._transition('PLACE_OBJECT')
                else:
                    rospy.logerr('Return navigation failed')
                    if self._retry_or_abort('return'):
                        self._transition('NAVIGATE_HOME')
                    else:
                        self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'PLACE_OBJECT':
                rospy.loginfo('Placing object...')
                self.arm_commander.set_gripper(open_gripper=True, blocking=True)
                rospy.sleep(0.5)
                self._transition('HOME_ARM_FINAL')

            elif self.current_state == 'HOME_ARM_FINAL':
                rospy.loginfo('Returning arm to home...')
                self.arm_commander.go_to_home(blocking=True)
                self._transition('DONE')

            elif self.current_state == 'DONE':
                rospy.loginfo('=' * 60)
                rospy.loginfo('MISSION COMPLETE')
                rospy.loginfo('=' * 60)
                break

            else:
                rospy.logerr('Unknown state: %s', self.current_state)
                break

            # State-to-state delay for smooth transitions
            rospy.sleep(0.5)

    def shutdown(self):
        rospy.loginfo('GraspPipeline: shutdown')
        self.navigator.clean_up()
        self.arm_commander.go_to_home(blocking=False)


if __name__ == '__main__':
    rospy.init_node('grasp_pipeline')
    pipeline = GraspPipeline()
    rospy.on_shutdown(pipeline.shutdown)

    try:
        pipeline.run()
    except Exception as e:
        rospy.logerr('Pipeline exception: %s', e)
        import traceback
        traceback.print_exc()
