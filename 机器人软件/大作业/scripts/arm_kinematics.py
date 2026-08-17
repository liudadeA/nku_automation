#!/usr/bin/env python3
"""Forward and inverse kinematics for 4-DOF arm (tilt + 3 planar pitch joints)."""

import math
import rospy


class ArmKinematics:
    def __init__(self):
        # Load link lengths from param server
        self.L0 = rospy.get_param('~link_lengths/L0', 0.05)
        self.L1 = rospy.get_param('~link_lengths/L1', 0.12)
        self.L2 = rospy.get_param('~link_lengths/L2', 0.10)
        self.L3 = rospy.get_param('~link_lengths/L3', 0.08)

        # Joint limits
        limits_ns = '~joint_limits'
        self.limits = {}
        for j in ['tilt_joint', 'shoulder_joint', 'elbow_joint', 'wrist_joint']:
            self.limits[j] = {
                'min': rospy.get_param('%s/%s/min' % (limits_ns, j), -1.57),
                'max': rospy.get_param('%s/%s/max' % (limits_ns, j), 1.57),
            }

        rospy.loginfo('ArmKinematics: L0=%.3f L1=%.3f L2=%.3f L3=%.3f',
                      self.L0, self.L1, self.L2, self.L3)

    def fk(self, theta_tilt, theta_shoulder, theta_elbow, theta_wrist):
        """
        Forward kinematics.
        Returns (x, y, z) of gripper tip in arm_base frame.
        All angles in radians.
        """
        t1 = theta_tilt
        t2 = theta_shoulder
        t3 = theta_elbow
        t4 = theta_wrist

        # Shoulder position
        z_shoulder = self.L0
        r_shoulder = 0.0

        # Elbow position relative to shoulder (in arm plane)
        r_elbow_rel = self.L1 * math.cos(t2)
        z_elbow_rel = self.L1 * math.sin(t2)

        # Wrist position relative to elbow
        angle_se = t2 + t3
        r_wrist_rel = r_elbow_rel + self.L2 * math.cos(angle_se)
        z_wrist_rel = z_elbow_rel + self.L2 * math.sin(angle_se)

        # Gripper tip relative to wrist
        angle_sew = t2 + t3 + t4
        r_tip = r_wrist_rel + self.L3 * math.cos(angle_sew)
        z_tip = z_wrist_rel + self.L3 * math.sin(angle_sew)

        # Rotate by tilt angle into 3D
        x = r_tip * math.cos(t1)
        y = r_tip * math.sin(t1)
        z = z_tip

        return (x, y, z)

    def ik(self, x, y, z, wrist_angle=0.0):
        """
        Inverse kinematics.
        x, y, z: target gripper tip position in arm_base frame (meters)
        wrist_angle: desired end-effector orientation in arm plane (radians)
                     0 = horizontal (parallel to ground)
                     pi/2 = vertical downward

        Returns [theta_tilt, theta_shoulder, theta_elbow, theta_wrist] in radians,
        or None if unreachable.
        """
        # Step 1: Tilt angle
        theta_tilt = math.atan2(y, x)

        # Step 2: Project to arm plane
        r_target = math.sqrt(x * x + y * y)
        z_target = z

        # Step 3: Account for wrist link L3.
        # Wrist adds L3 along direction (cos(wrist_angle), sin(wrist_angle)) in plane.
        # We want gripper tip at (r_target, z_target).
        # Wrist joint position = tip_position - L3 * (cos(wrist_angle), sin(wrist_angle))
        r_wrist = r_target - self.L3 * math.cos(wrist_angle)
        z_wrist = z_target - self.L3 * math.sin(wrist_angle)

        # Step 4: 2-link IK for shoulder+elbow to reach wrist position
        # Coordinates relative to shoulder joint
        r_rel = r_wrist
        z_rel = z_wrist - self.L0

        D_sq = r_rel * r_rel + z_rel * z_rel
        D = math.sqrt(D_sq)

        if D > (self.L1 + self.L2) or D < abs(self.L1 - self.L2):
            rospy.logwarn('IK: target unreachable D=%.3f L1+L2=%.3f |L1-L2|=%.3f',
                          D, self.L1 + self.L2, abs(self.L1 - self.L2))
            return None

        # Cosine law for elbow
        cos_elbow = (D_sq - self.L1 * self.L1 - self.L2 * self.L2) / (2.0 * self.L1 * self.L2)
        cos_elbow = max(-1.0, min(1.0, cos_elbow))

        # Two solutions: elbow up (+acos) or elbow down (-acos)
        solutions = []
        for sign in [+1.0, -1.0]:
            theta_elbow = sign * math.acos(cos_elbow)

            # Shoulder angle
            alpha = math.atan2(z_rel, r_rel)
            beta = math.atan2(self.L2 * math.sin(theta_elbow),
                              self.L1 + self.L2 * math.cos(theta_elbow))
            theta_shoulder = alpha - beta

            # Wrist angle for desired gripper orientation
            theta_wrist = wrist_angle - theta_shoulder - theta_elbow

            # Normalize wrist to [-pi, pi]
            theta_wrist = math.atan2(math.sin(theta_wrist), math.cos(theta_wrist))

            # Check limits
            if self._check_limits(theta_tilt, theta_shoulder, theta_elbow, theta_wrist):
                solutions.append([theta_tilt, theta_shoulder, theta_elbow, theta_wrist])

        if solutions:
            # Prefer elbow-down (more natural for grasping from above)
            return solutions[-1]

        rospy.logwarn('IK: all solutions violate joint limits')
        return None

    def _check_limits(self, t1, t2, t3, t4):
        """Return True if all joint angles are within configured limits."""
        angles = {
            'tilt_joint': t1,
            'shoulder_joint': t2,
            'elbow_joint': t3,
            'wrist_joint': t4,
        }
        for name, angle in angles.items():
            lim = self.limits[name]
            if angle < lim['min'] or angle > lim['max']:
                return False
        return True

    def get_joint_limits(self):
        """Return dict of {joint_name: (min, max)}."""
        return {name: (lim['min'], lim['max']) for name, lim in self.limits.items()}


if __name__ == '__main__':
    rospy.init_node('arm_kinematics_test')
    k = ArmKinematics()

    # Self-test: FK then IK should recover the original point
    test_angles = [0.0, 0.5, -0.8, 0.3]
    x, y, z = k.fk(*test_angles)
    rospy.loginfo('FK(%s) = (%.3f, %.3f, %.3f)', test_angles, x, y, z)

    result = k.ik(x, y, z, wrist_angle=0.3 + 0.8 - 0.5)
    rospy.loginfo('IK(%.3f, %.3f, %.3f) = %s', x, y, z, result)

    if result:
        x2, y2, z2 = k.fk(*result)
        rospy.loginfo('FK(IK(xyz)) = (%.3f, %.3f, %.3f)', x2, y2, z2)
        rospy.loginfo('Error: %.4f m', math.sqrt((x - x2) ** 2 + (y - y2) ** 2 + (z - z2) ** 2))
