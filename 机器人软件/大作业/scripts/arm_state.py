#!/usr/bin/env python3
"""Monitor joint states for all 5 Dynamixel servos."""

import rospy
from dynamixel_msgs.msg import JointState

JOINTS = ['tilt_joint', 'shoulder_joint', 'elbow_joint', 'wrist_joint', 'hand_joint']


class ArmState:
    def __init__(self):
        self._states = {}
        for joint in JOINTS:
            topic = '/%s_controller/state' % joint
            self._states[joint] = JointState()
            rospy.Subscriber(topic, JointState,
                             self._make_callback(joint))
        rospy.loginfo('ArmState: subscribed to %d joint states', len(JOINTS))

    def _make_callback(self, name):
        def cb(msg):
            self._states[name] = msg
        return cb

    def get_angle(self, joint_name):
        """Return current angle in radians for one joint."""
        return self._states[joint_name].current_pos

    def get_angles(self):
        """Return dict of {joint_name: angle_rad} for all 5 joints."""
        return {j: self._states[j].current_pos for j in JOINTS}

    def is_moving(self):
        """Return True if any joint is currently moving."""
        return any(self._states[j].is_moving for j in JOINTS)

    def get_error(self, joint_name):
        """Return position error for one joint."""
        return abs(self._states[joint_name].error)

    def wait_for_stop(self, timeout=10.0):
        """Block until all joints stop moving or timeout expires."""
        rate = rospy.Rate(20)
        start = rospy.Time.now()
        while not rospy.is_shutdown():
            if not self.is_moving():
                # Extra settle time
                rospy.sleep(0.3)
                if not self.is_moving():
                    return True
            if (rospy.Time.now() - start).to_sec() > timeout:
                rospy.logwarn('ArmState: wait_for_stop timeout (%.1fs)', timeout)
                return False
            rate.sleep()
        return False

    def log_state(self):
        """Log current joint angles."""
        angles = self.get_angles()
        strs = ['%s=%.3f' % (j, a) for j, a in angles.items()]
        rospy.loginfo('Arm state: %s', '  '.join(strs))


if __name__ == '__main__':
    rospy.init_node('arm_state')
    state = ArmState()
    rate = rospy.Rate(2)
    while not rospy.is_shutdown():
        state.log_state()
        rate.sleep()
