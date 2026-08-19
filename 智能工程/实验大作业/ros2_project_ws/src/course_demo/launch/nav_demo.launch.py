import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Directories
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    
    # Launch Configuration
    map_yaml_file = LaunchConfiguration('map')

    # Declare launch arguments
    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(os.path.expanduser('~'), 'ros2_project_ws', 'maps', 'my_map.yaml'),
        description='Full path to map file to load')

    # Include Gazebo World Launch
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'turtlebot3_world.launch.py')
        )
    )

    nav2_params_file = os.path.join(get_package_share_directory('course_demo'), 'param', 'burger.yaml')

    # Include Nav2 Bringup Launch
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'map': map_yaml_file,
            'params_file': nav2_params_file
        }.items()
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

    return LaunchDescription([
        declare_map_yaml_cmd,
        gazebo_launch,
        nav2_launch,
        TimerAction(
            period=5.0,
            actions=[rviz_node]
        )
    ])
