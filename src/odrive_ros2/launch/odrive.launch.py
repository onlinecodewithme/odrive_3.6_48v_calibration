from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get the package directory
    pkg_dir = get_package_share_directory('odrive_ros2')
    
    # Default path to the config file
    default_config_path = os.path.join(pkg_dir, 'config', 'odrive_config.yaml')
    
    # Declare launch arguments
    config_file = LaunchConfiguration('config_file')
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=default_config_path,
        description='Path to the config file for ODrive parameters'
    )
    
    simulation_mode = LaunchConfiguration('simulation_mode')
    simulation_mode_arg = DeclareLaunchArgument(
        'simulation_mode',
        default_value='false',
        description='Run in simulation mode without hardware'
    )
    
    # Create the odrive node
    odrive_node = Node(
        package='odrive_ros2',
        executable='odrive_node.py',
        name='odrive_node',
        output='screen',
        parameters=[config_file],
        remappings=[
            ('cmd_vel', '/cmd_vel'),
            ('odom', '/odom')
        ]
    )
    
    # Return the launch description
    return LaunchDescription([
        config_file_arg,
        simulation_mode_arg,
        odrive_node
    ])
