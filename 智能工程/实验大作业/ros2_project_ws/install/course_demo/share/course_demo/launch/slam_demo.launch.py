import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Directories
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    slam_toolbox_dir = get_package_share_directory('slam_toolbox')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    explore_lite_dir = get_package_share_directory('explore_lite')
    
    # Include Gazebo World Launch
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'turtlebot3_world.launch.py')
        )
    )

    # Include SLAM Toolbox Launch
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox_dir, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    # RViz Node
    rviz_config_dir = os.path.join(get_package_share_directory('course_demo'), 'rviz', 'nav2_custom_view.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_dir],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # Nav2 Navigation Launch (without AMCL, since SLAM provides localization)
    nav2_params_file = os.path.join(get_package_share_directory('course_demo'), 'param', 'burger.yaml')
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': nav2_params_file
        }.items()
    )

    # Explore Lite Node
    explore_params_file = os.path.join(get_package_share_directory('course_demo'), 'param', 'explore.yaml')
    explore_lite_node = Node(
        package='explore_lite',
        name='explore_node',
        executable='explore',
        parameters=[explore_params_file, {'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        gazebo_launch,
        slam_launch,
        navigation_launch,
        TimerAction(
            period=3.0,
            actions=[rviz_node]
        ),
        TimerAction(
            period=8.0,
            actions=[explore_lite_node]
        )
    ])
