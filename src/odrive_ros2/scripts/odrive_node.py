#!/Users/randikaprasad/miniforge3/bin/python

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64, Int32, Bool
from tf2_ros import TransformBroadcaster
import time
import math
import threading
import numpy as np
from enum import Enum

try:
    import odrive
    from odrive.enums import *
    ODRIVE_FOUND = True
except ImportError:
    ODRIVE_FOUND = False
    print("ODrive library not found. Running in simulation mode.")

class ODriveMode(Enum):
    IDLE = 0
    POSITION_CONTROL = 1
    VELOCITY_CONTROL = 2
    TORQUE_CONTROL = 3
    
class ODriveNode(Node):

    def __init__(self):
        super().__init__('odrive_node')
        
        # Declare parameters
        self.declare_parameter('left_motor_axis', 0)
        self.declare_parameter('right_motor_axis', 1)
        self.declare_parameter('wheel_radius', 0.0762)  # in meters, default = 3 inches
        self.declare_parameter('wheel_base', 0.5)  # in meters, distance between wheels
        self.declare_parameter('ticks_per_rev', 8192)
        self.declare_parameter('connect_on_startup', True)
        self.declare_parameter('simulation_mode', not ODRIVE_FOUND)
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('control_mode', 'velocity')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('max_motor_speed', 30.0)  # rad/s
        self.declare_parameter('gear_ratio', 1.0)
        
        # Get parameters
        self.left_motor_axis = self.get_parameter('left_motor_axis').get_parameter_value().integer_value
        self.right_motor_axis = self.get_parameter('right_motor_axis').get_parameter_value().integer_value
        self.wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value
        self.wheel_base = self.get_parameter('wheel_base').get_parameter_value().double_value
        self.ticks_per_rev = self.get_parameter('ticks_per_rev').get_parameter_value().integer_value
        self.connect_on_startup = self.get_parameter('connect_on_startup').get_parameter_value().bool_value
        self.simulation_mode = self.get_parameter('simulation_mode').get_parameter_value().bool_value
        self.publish_tf = self.get_parameter('publish_tf').get_parameter_value().bool_value
        self.control_mode_str = self.get_parameter('control_mode').get_parameter_value().string_value
        self.odom_frame = self.get_parameter('odom_frame').get_parameter_value().string_value
        self.base_frame = self.get_parameter('base_frame').get_parameter_value().string_value
        self.max_motor_speed = self.get_parameter('max_motor_speed').get_parameter_value().double_value
        self.gear_ratio = self.get_parameter('gear_ratio').get_parameter_value().double_value
        
        # Set control mode
        if self.control_mode_str == 'velocity':
            self.control_mode = ODriveMode.VELOCITY_CONTROL
        elif self.control_mode_str == 'position':
            self.control_mode = ODriveMode.POSITION_CONTROL
        elif self.control_mode_str == 'torque':
            self.control_mode = ODriveMode.TORQUE_CONTROL
        else:
            self.control_mode = ODriveMode.VELOCITY_CONTROL
            self.get_logger().warning(f"Invalid control mode '{self.control_mode_str}'. Using velocity control.")
        
        # Initialize ODrive
        self.driver = None
        self.axes = []
        self.axis_state = [AxisState.IDLE, AxisState.IDLE]
        
        # Initialize robot state
        self.position = [0.0, 0.0, 0.0]  # x, y, theta
        self.velocity = [0.0, 0.0, 0.0]  # vx, vy, vtheta
        self.encoder_counts = [0, 0]
        self.last_encoder_counts = [0, 0]
        self.wheel_speeds = [0.0, 0.0]  # rad/s
        
        # Set up publishers and subscribers
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Publishers
        self.odom_pub = self.create_publisher(Odometry, 'odom', qos_profile)
        self.left_speed_pub = self.create_publisher(Float64, 'left_wheel_speed', qos_profile)
        self.right_speed_pub = self.create_publisher(Float64, 'right_wheel_speed', qos_profile)
        self.left_pos_pub = self.create_publisher(Float64, 'left_wheel_position', qos_profile)
        self.right_pos_pub = self.create_publisher(Float64, 'right_wheel_position', qos_profile)
        
        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, qos_profile)
        
        self.emergency_stop_sub = self.create_subscription(
            Bool, 'emergency_stop', self.emergency_stop_callback, qos_profile)
        
        # TF broadcaster
        if self.publish_tf:
            self.tf_broadcaster = TransformBroadcaster(self)
        
        # Timers
        self.odom_timer = self.create_timer(0.02, self.update_odometry)  # 50 Hz
        self.status_timer = self.create_timer(1.0, self.publish_status)  # 1 Hz
        
        # Connect to ODrive
        if self.connect_on_startup and not self.simulation_mode:
            self.connect_odrive()
        else:
            self.get_logger().info("Running in simulation mode or waiting for manual connection.")
    
    def connect_odrive(self):
        self.get_logger().info("Connecting to ODrive...")
        try:
            self.driver = odrive.find_any()
            self.get_logger().info(f"Connected to ODrive. Serial number: {self.driver.serial_number}")
            
            self.axes = [
                getattr(self.driver, f'axis{self.left_motor_axis}'),
                getattr(self.driver, f'axis{self.right_motor_axis}')
            ]
            
            self.configure_odrive()
            self.get_logger().info("ODrive setup complete.")
            return True
        except Exception as e:
            self.get_logger().error(f"Failed to connect to ODrive: {str(e)}")
            return False
    
    def configure_odrive(self):
        """Configure the ODrive for differential drive operation"""
        if self.simulation_mode:
            return
        
        self.get_logger().info("Configuring ODrive...")
        
        # Configure each axis
        for i, axis in enumerate(self.axes):
            self.get_logger().info(f"Configuring axis {i}")
            
            # Configuration for motor
            axis.motor.config.current_lim = 40.0  # Adjust as needed
            axis.motor.config.calibration_current = 10.0
            axis.motor.config.resistance_calib_max_voltage = 4.0
            
            # Configuration for encoder
            axis.encoder.config.cpr = self.ticks_per_rev
            axis.encoder.config.use_index = False
            
            # Configuration for controller
            axis.controller.config.vel_limit = self.max_motor_speed  # rad/s
            axis.controller.config.control_mode = self.control_mode.value
            
            # Apply configuration
            axis.requested_state = AxisState.CLOSED_LOOP_CONTROL
    
    def emergency_stop_callback(self, msg):
        """Handle emergency stop messages"""
        if msg.data:
            self.get_logger().warning("Emergency Stop activated")
            self.stop_motors()
            if not self.simulation_mode and self.driver:
                for axis in self.axes:
                    axis.requested_state = AxisState.IDLE
        else:
            self.get_logger().info("Emergency Stop released")
            if not self.simulation_mode and self.driver:
                for axis in self.axes:
                    axis.requested_state = AxisState.CLOSED_LOOP_CONTROL
    
    def cmd_vel_callback(self, msg):
        """Handle velocity command messages"""
        # Extract linear and angular velocity from the Twist message
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Calculate wheel speeds using differential drive kinematics
        left_speed = (linear_x - angular_z * self.wheel_base / 2.0) / self.wheel_radius
        right_speed = (linear_x + angular_z * self.wheel_base / 2.0) / self.wheel_radius
        
        # Apply gear ratio
        left_speed *= self.gear_ratio
        right_speed *= self.gear_ratio
        
        # Apply motor speed limits
        left_speed = np.clip(left_speed, -self.max_motor_speed, self.max_motor_speed)
        right_speed = np.clip(right_speed, -self.max_motor_speed, self.max_motor_speed)
        
        self.set_wheel_speeds(left_speed, right_speed)
    
    def set_wheel_speeds(self, left_speed, right_speed):
        """Set the wheel speeds in rad/s"""
        self.wheel_speeds = [left_speed, right_speed]
        
        if self.simulation_mode:
            return
        
        if not self.driver:
            self.get_logger().warning("Cannot set speeds, ODrive not connected")
            return
        
        try:
            if self.control_mode == ODriveMode.VELOCITY_CONTROL:
                self.axes[0].controller.input_vel = float(left_speed)
                self.axes[1].controller.input_vel = float(right_speed)
            elif self.control_mode == ODriveMode.POSITION_CONTROL:
                # In position control, we integrate the velocity to get position
                current_pos_0 = self.axes[0].encoder.pos_estimate
                current_pos_1 = self.axes[1].encoder.pos_estimate
                self.axes[0].controller.input_pos = current_pos_0 + float(left_speed) * 0.02  # 20ms control cycle
                self.axes[1].controller.input_pos = current_pos_1 + float(right_speed) * 0.02
            elif self.control_mode == ODriveMode.TORQUE_CONTROL:
                # Simple conversion from velocity to torque (proportional)
                torque_factor = 0.1  # Adjust as needed
                self.axes[0].controller.input_torque = float(left_speed) * torque_factor
                self.axes[1].controller.input_torque = float(right_speed) * torque_factor
        except Exception as e:
            self.get_logger().error(f"Failed to set wheel speeds: {str(e)}")
    
    def stop_motors(self):
        """Stop both motors"""
        self.set_wheel_speeds(0.0, 0.0)
    
    def read_encoder_values(self):
        """Read encoder values from ODrive"""
        if self.simulation_mode:
            # In simulation, we use the commanded wheel_speeds to calculate encoder counts
            dt = 0.02  # 20ms control cycle
            self.encoder_counts[0] += int(self.wheel_speeds[0] * dt * self.ticks_per_rev / (2 * math.pi))
            self.encoder_counts[1] += int(self.wheel_speeds[1] * dt * self.ticks_per_rev / (2 * math.pi))
            return
        
        if not self.driver:
            return
        
        try:
            # Read current encoder position
            self.encoder_counts[0] = int(self.axes[0].encoder.pos_estimate * self.ticks_per_rev / (2 * math.pi))
            self.encoder_counts[1] = int(self.axes[1].encoder.pos_estimate * self.ticks_per_rev / (2 * math.pi))
        except Exception as e:
            self.get_logger().error(f"Failed to read encoder values: {str(e)}")
    
    def update_odometry(self):
        """Update and publish odometry information"""
        self.read_encoder_values()
        
        # Calculate displacement in encoder ticks
        ticks_delta = [
            self.encoder_counts[0] - self.last_encoder_counts[0],
            self.encoder_counts[1] - self.last_encoder_counts[1]
        ]
        
        # Convert to wheel displacement in radians
        wheel_delta = [
            2 * math.pi * ticks_delta[0] / self.ticks_per_rev,
            2 * math.pi * ticks_delta[1] / self.ticks_per_rev
        ]
        
        # Calculate displacement in meters
        wheel_displacement = [
            wheel_delta[0] * self.wheel_radius / self.gear_ratio,
            wheel_delta[1] * self.wheel_radius / self.gear_ratio
        ]
        
        # Update wheel speeds
        dt = 0.02  # 50Hz update rate
        self.wheel_speeds = [
            wheel_delta[0] / dt,
            wheel_delta[1] / dt
        ]
        
        # Calculate robot displacement in local frame
        # For differential drive, we use the average of the wheel displacements for forward motion
        # and the difference for rotation
        local_displacement = [
            (wheel_displacement[0] + wheel_displacement[1]) / 2,  # dx
            0.0,  # dy (no sideways motion in differential drive)
            (wheel_displacement[1] - wheel_displacement[0]) / self.wheel_base  # dtheta
        ]
        
        # Update robot position (integrate displacement)
        # Apply rotation matrix to convert local displacement to global frame
        cos_theta = math.cos(self.position[2])
        sin_theta = math.sin(self.position[2])
        
        # Rotation matrix to convert local displacement to global frame
        self.position[0] += local_displacement[0] * cos_theta - local_displacement[1] * sin_theta
        self.position[1] += local_displacement[0] * sin_theta + local_displacement[1] * cos_theta
        self.position[2] += local_displacement[2]
        
        # Normalize theta to [-pi, pi]
        self.position[2] = math.atan2(math.sin(self.position[2]), math.cos(self.position[2]))
        
        # Update robot velocity
        self.velocity = [
            local_displacement[0] / dt,  # vx
            local_displacement[1] / dt,  # vy
            local_displacement[2] / dt   # vtheta
        ]
        
        # Save current encoder counts
        self.last_encoder_counts = self.encoder_counts.copy()
        
        # Publish odometry
        self.publish_odometry()
        
        # Publish wheel speeds
        left_speed_msg = Float64()
        left_speed_msg.data = self.wheel_speeds[0]
        self.left_speed_pub.publish(left_speed_msg)
        
        right_speed_msg = Float64()
        right_speed_msg.data = self.wheel_speeds[1]
        self.right_speed_pub.publish(right_speed_msg)
        
        # Publish wheel positions
        left_pos_msg = Float64()
        left_pos_msg.data = self.encoder_counts[0] * 2 * math.pi / self.ticks_per_rev
        self.left_pos_pub.publish(left_pos_msg)
        
        right_pos_msg = Float64()
        right_pos_msg.data = self.encoder_counts[1] * 2 * math.pi / self.ticks_per_rev
        self.right_pos_pub.publish(right_pos_msg)
    
    def publish_odometry(self):
        """Publish odometry message and transform"""
        current_time = self.get_clock().now().to_msg()
        
        # Create and publish odometry message
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time
        odom_msg.header.frame_id = self.odom_frame
        odom_msg.child_frame_id = self.base_frame
        
        # Position
        odom_msg.pose.pose.position.x = self.position[0]
        odom_msg.pose.pose.position.y = self.position[1]
        odom_msg.pose.pose.position.z = 0.0
        
        # Orientation (convert theta to quaternion)
        cy = math.cos(self.position[2] * 0.5)
        sy = math.sin(self.position[2] * 0.5)
        odom_msg.pose.pose.orientation.x = 0.0
        odom_msg.pose.pose.orientation.y = 0.0
        odom_msg.pose.pose.orientation.z = sy
        odom_msg.pose.pose.orientation.w = cy
        
        # Velocity
        odom_msg.twist.twist.linear.x = self.velocity[0]
        odom_msg.twist.twist.linear.y = self.velocity[1]
        odom_msg.twist.twist.angular.z = self.velocity[2]
        
        # Publish
        self.odom_pub.publish(odom_msg)
        
        # Publish transform if enabled
        if self.publish_tf:
            tf_msg = TransformStamped()
            tf_msg.header.stamp = current_time
            tf_msg.header.frame_id = self.odom_frame
            tf_msg.child_frame_id = self.base_frame
            
            tf_msg.transform.translation.x = self.position[0]
            tf_msg.transform.translation.y = self.position[1]
            tf_msg.transform.translation.z = 0.0
            
            tf_msg.transform.rotation.x = 0.0
            tf_msg.transform.rotation.y = 0.0
            tf_msg.transform.rotation.z = sy
            tf_msg.transform.rotation.w = cy
            
            self.tf_broadcaster.sendTransform(tf_msg)
    
    def publish_status(self):
        """Publish status information"""
        if self.simulation_mode:
            self.get_logger().debug("Simulation mode active")
            return
        
        if not self.driver:
            self.get_logger().debug("ODrive not connected")
            return
        
        try:
            for i, axis in enumerate(self.axes):
                self.get_logger().debug(f"Axis {i} state: {axis.current_state}")
                self.get_logger().debug(f"Axis {i} encoder pos: {axis.encoder.pos_estimate}")
                self.get_logger().debug(f"Axis {i} velocity: {axis.encoder.vel_estimate}")
        except Exception as e:
            self.get_logger().error(f"Failed to publish status: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    node = ODriveNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop motors before shutting down
        node.stop_motors()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
