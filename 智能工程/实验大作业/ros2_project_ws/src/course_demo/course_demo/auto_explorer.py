#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TwistStamped
from rclpy.qos import qos_profile_sensor_data
import random

class AutoExplorer(Node):
    def __init__(self):
        super().__init__('auto_explorer')
        self.publisher_ = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        self.subscription = self.create_subscription(LaserScan, 'scan', self.scan_callback, qos_profile_sensor_data)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.twist_stamped = TwistStamped()
        self.twist_stamped.header.frame_id = "base_link"
        self.state = 'FORWARD'
        self.turn_time = 0

    def scan_callback(self, msg):
        front_ranges = msg.ranges[-30:] + msg.ranges[:30]
        valid_ranges = [r for r in front_ranges if r > 0.1 and r < float('inf')]
        if len(valid_ranges) > 0:
            min_dist = min(valid_ranges)
            if min_dist < 0.6:
                if self.state == 'FORWARD':
                    self.state = 'TURN'
                    self.turn_time = random.randint(15, 30)
            else:
                if self.state == 'TURN' and self.turn_time <= 0:
                    self.state = 'FORWARD'

    def timer_callback(self):
        if self.state == 'FORWARD':
            self.twist_stamped.twist.linear.x = 0.15
            self.twist_stamped.twist.angular.z = random.uniform(-0.2, 0.2)
        elif self.state == 'TURN':
            self.twist_stamped.twist.linear.x = 0.0
            self.twist_stamped.twist.angular.z = 0.5
            self.turn_time -= 1
            self.get_logger().info('Turning to avoid obstacle...', throttle_duration_sec=2.0)
        
        self.twist_stamped.header.stamp = self.get_clock().now().to_msg()
        self.publisher_.publish(self.twist_stamped)

def main(args=None):
    rclpy.init(args=args)
    auto_explorer = AutoExplorer()
    rclpy.spin(auto_explorer)
    auto_explorer.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
