#!/usr/bin/env python3
"""Grasp planner: converts 3D object position to joint angles for pregrasp/grasp/lift."""

import math
import rospy
from arm_kinematics import ArmKinematics


class GraspPlanner:
    def __init__(self, kinematics=None):
        self.kin = kinematics if kinematics is not None else ArmKinematics()

        # Grasp strategy: 'top_down' or 'side'
        self.strategy = rospy.get_param('~grasp_strategy', 'top_down')

        # Pregrasp offset (meters) - distance behind object along approach direction
        self.pregrasp_offset = rospy.get_param('~pregrasp_offset', 0.08)

        # Lift height (meters) above object
        self.lift_height = rospy.get_param('~lift_height', 0.10)

        rospy.loginfo('GraspPlanner: strategy=%s pregrasp_offset=%.3f',
                      self.strategy, self.pregrasp_offset)

    def plan(self, obj_x, obj_y, obj_z):
        """
        Compute joint angles for pregrasp, grasp, and lift poses.

        obj_x, obj_y, obj_z: object position in arm_base frame (meters)

        Returns dict with keys 'pregrasp', 'grasp', 'lift', each a dict of
        joint_name -> angle_rad. Returns None if no solution found.
        """
        rospy.loginfo('GraspPlanner: planning for object at (%.3f, %.3f, %.3f)',
                      obj_x, obj_y, obj_z)

        # Determine approach direction based on strategy
        if self.strategy == 'top_down':
            wangle = math.pi / 2  # gripper vertical (downward)
            # For top-down: pregrasp is above the object
            pregrasp_pos = (obj_x, obj_y, obj_z + self.pregrasp_offset)
            grasp_pos = (obj_x, obj_y, obj_z)
            lift_pos = (obj_x, obj_y, obj_z + self.lift_height)
        else:
            # Side approach: gripper horizontal
            wangle = 0.0
            # For side approach: pregrasp is in front of object
            # Determine approach direction from robot perspective
            if obj_x > 0:
                # Object is in front: approach from slightly behind (in X)
                pregrasp_pos = (obj_x - self.pregrasp_offset, obj_y, obj_z)
            else:
                pregrasp_pos = (obj_x + self.pregrasp_offset, obj_y, obj_z)
            grasp_pos = (obj_x, obj_y, obj_z)
            lift_pos = (obj_x, obj_y, obj_z + self.lift_height)

        # Compute IK for each pose
        poses = {
            'pregrasp': pregrasp_pos,
            'grasp': grasp_pos,
            'lift': lift_pos,
        }

        joint_names = ['tilt_joint', 'shoulder_joint', 'elbow_joint', 'wrist_joint']

        plan = {}
        for phase, (x, y, z) in poses.items():
            result = self.kin.ik(x, y, z, wrist_angle=wangle)
            if result is None:
                rospy.logerr('GraspPlanner: IK failed for %s at (%.3f, %.3f, %.3f)',
                             phase, x, y, z)
                return None

            angles = dict(zip(joint_names, result))
            rospy.loginfo('GraspPlanner: %s -> %s', phase,
                          ' '.join('%s=%.2f' % (j, a) for j, a in angles.items()))
            plan[phase] = angles

        return plan


if __name__ == '__main__':
    rospy.init_node('grasp_planner_test')
    planner = GraspPlanner()

    # Test with a sample object position
    test_positions = [
        (0.20, 0.0, 0.10),   # directly in front, low
        (0.15, 0.10, 0.05),  # front-right, low
        (0.25, -0.05, 0.15), # front-left, higher
    ]

    for x, y, z in test_positions:
        rospy.loginfo('--- Test object at (%.3f, %.3f, %.3f) ---', x, y, z)
        plan = planner.plan(x, y, z)
        if plan:
            for phase, angles in plan.items():
                # Verify FK gives back the expected position
                t, s, e, w = [angles[n] for n in ['tilt_joint', 'shoulder_joint', 'elbow_joint', 'wrist_joint']]
                fk_x, fk_y, fk_z = planner.kin.fk(t, s, e, w)
                rospy.loginfo('  %s FK: (%.3f, %.3f, %.3f)', phase, fk_x, fk_y, fk_z)
        else:
            rospy.logerr('  Plan FAILED')
