#!/usr/bin/env python3
"""Command interface for the 5-DOF Dynamixel arm + gripper."""

import rospy
from std_msgs.msg import Float64
from arm_state import ArmState

JOINTS = ['tilt_joint', 'shoulder_joint', 'elbow_joint', 'wrist_joint', 'hand_joint']


class ArmCommander:
    def __init__(self, arm_state=None):
        self._state = arm_state if arm_state is not None else ArmState()
        self._pubs = {}
        for joint in JOINTS:
            topic = '/%s_controller/command' % joint
            self._pubs[joint] = rospy.Publisher(topic, Float64, queue_size=1)

        # Give subscribers time to connect
        rospy.sleep(0.5)

        # Load params
        self.speed = rospy.get_param('~joint_speed', 0.5)
        self.tolerance = rospy.get_param('~move_tolerance', 0.05)
        self.home = rospy.get_param('~home_angles', None)
        if self.home is None:
            self.home = {j: 0.0 for j in JOINTS}
            self.home['elbow_joint'] = 1.57
            self.home['wrist_joint'] = -1.57

        self.carry = rospy.get_param('~carry_angles', None)
        if self.carry is None:
            self.carry = {j: 0.0 for j in JOINTS}
            self.carry['shoulder_joint'] = -0.5
            self.carry['elbow_joint'] = 1.0
            self.carry['wrist_joint'] = -0.5
            self.carry['hand_joint'] = 1.0

        rospy.loginfo('ArmCommander: ready on %d topics', len(JOINTS))

    def _publish(self, joint_name, angle_rad):
        self._pubs[joint_name].publish(Float64(angle_rad))

    def move_joint(self, joint, angle, blocking=True, timeout=5.0):
        """Move a single joint to target angle (radians)."""
        if joint not in self._pubs:
            rospy.logerr('ArmCommander: unknown joint %s', joint)
            return False
        rospy.loginfo('ArmCommander: move %s -> %.3f rad', joint, angle)
        self._publish(joint, angle)

        if blocking:
            # Allow time for command to be received
            rospy.sleep(0.2)
            if not self._state.wait_for_stop(timeout):
                return False
            # Check final position
            actual = self._state.get_angle(joint)
            error = abs(actual - angle)
            if error > self.tolerance:
                rospy.logwarn('ArmCommander: %s pos error %.3f > tol %.3f',
                              joint, error, self.tolerance)
                return False
        return True

    def move_all(self, angles, blocking=True, timeout=10.0):
        """Move all joints to target angles. angles = {joint_name: rad}."""
        for j in JOINTS:
            if j in angles:
                self._publish(j, Float64(angles[j]))
        rospy.loginfo('ArmCommander: move_all %s', angles)

        if blocking:
            rospy.sleep(0.2)
            return self._state.wait_for_stop(timeout)
        return True

    def set_gripper(self, open_gripper=True, blocking=True, timeout=3.0):
        """Open or close the gripper."""
        gripper_open = rospy.get_param('~gripper/open_position', 0.0)
        gripper_close = rospy.get_param('~gripper/close_position', 1.57)
        angle = gripper_open if open_gripper else gripper_close
        return self.move_joint('hand_joint', angle, blocking, timeout)

    def go_to_home(self, blocking=True):
        """Move arm to safe home/transport position."""
        rospy.loginfo('ArmCommander: moving to home position')
        return self.move_all(self.home, blocking)

    def go_to_carry(self, blocking=True):
        """Move arm to carry position (holding object)."""
        rospy.loginfo('ArmCommander: moving to carry position')
        return self.move_all(self.carry, blocking)

    def get_state(self):
        return self._state


if __name__ == '__main__':
    rospy.init_node('arm_commander_test')
    cmd = ArmCommander()

    rospy.loginfo('=== HOME ===')
    cmd.go_to_home()

    rospy.loginfo('=== GRIPPER TEST ===')
    cmd.set_gripper(open_gripper=True)
    rospy.sleep(1.0)
    cmd.set_gripper(open_gripper=False)

    rospy.loginfo('=== BACK TO HOME ===')
    cmd.go_to_home()
    rospy.loginfo('=== DONE ===')
