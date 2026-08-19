cmake_minimum_required(VERSION 3.0.2)
project(user_control)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  yolov8_ros_msgs
)

catkin_python_setup()

catkin_package(
  CATKIN_DEPENDS rospy std_msgs yolov8_ros_msgs
)

catkin_install_python(PROGRAMS
  scripts/state_machine.py
  scripts/vision_detector.py
  scripts/voice_control.py
  scripts/voice_feedback.py
  scripts/robot_control.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)