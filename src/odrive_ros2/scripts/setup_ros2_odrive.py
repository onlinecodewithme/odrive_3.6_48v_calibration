#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive ROS 2 Setup Script

This script configures the ODrive for use with ROS 2 after calibration
and helps verify that the ROS 2 driver can communicate properly.
"""

import sys
import time
import argparse
import os
import subprocess
import odrive
from odrive.enums import *

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_odrive():
    """Check if ODrive is connected and return instance"""
    print("Looking for ODrive...")
    try:
        od = odrive.find_any(timeout=10)
        print(f"✅ Found ODrive!")
        print(f"Serial Number: {od.serial_number}")
        print(f"Hardware version: {od.hw_version_major}.{od.hw_version_minor}")
        print(f"Firmware version: {od.fw_version_major}.{od.fw_version_minor}.{od.fw_version_revision}")
        print("\nAxis 0 state:", od.axis0.current_state)
        print("Axis 1 state:", od.axis1.current_state)
        return od
    except Exception as e:
        print(f"❌ Cannot find ODrive: {str(e)}")
        return None

def check_ros_installation():
    """Check if ROS 2 is installed and sourced"""
    print("Checking ROS 2 installation...")
    try:
        result = subprocess.run(["ros2", "--version"], 
                               capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"✅ ROS 2 is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ ROS 2 command failed. Make sure ROS 2 is installed and sourced.")
            return False
    except Exception as e:
        print(f"❌ Error checking ROS 2: {str(e)}")
        print("Make sure ROS 2 is installed and the environment is properly sourced.")
        return False

def check_calibration_status(od):
    """Check if motors and encoders are calibrated"""
    all_calibrated = True
    
    for axis_num in [0, 1]:
        axis = getattr(od, f'axis{axis_num}')
        print(f"\nAxis {axis_num} status:")
        
        # Check motor calibration
        try:
            if axis.motor.is_calibrated:
                print(f"✅ Motor {axis_num} is calibrated")
            else:
                print(f"❌ Motor {axis_num} is NOT calibrated")
                all_calibrated = False
        except:
            print(f"❌ Could not determine motor {axis_num} calibration status")
            all_calibrated = False
        
        # Check encoder calibration
        try:
            if axis.encoder.is_ready:
                print(f"✅ Encoder {axis_num} is calibrated")
            else:
                print(f"❌ Encoder {axis_num} is NOT calibrated")
                all_calibrated = False
        except:
            print(f"❌ Could not determine encoder {axis_num} status")
            all_calibrated = False
    
    return all_calibrated

def configure_for_ros2(od, config):
    """Apply ROS 2 specific configuration to ODrive"""
    print_header("CONFIGURING FOR ROS 2")
    
    for axis_num in [0, 1]:
        axis = getattr(od, f'axis{axis_num}')
        print(f"Configuring axis {axis_num} for ROS 2...")
        
        # High current mode 
        try:
            axis.motor.config.motor_type = MOTOR_TYPE_HIGH_CURRENT
            print("✓ Set motor type: HIGH_CURRENT")
        except:
            print("! Could not set motor type")
        
        # Current limits
        try:
            # Try new API
            axis.config.dc_max_current = config['current_limit']
            axis.config.dc_max_negative_current = -config['current_limit']
            print(f"✓ Set current limits: {config['current_limit']}A (new API)")
        except:
            try:
                # Try old API
                axis.motor.config.current_lim = config['current_limit']
                print(f"✓ Set current limits: {config['current_limit']}A (old API)")
            except:
                print("! Could not set current limits")
        
        # Velocity limits
        try:
            axis.controller.config.vel_limit = config['velocity_limit']
            print(f"✓ Set velocity limit: {config['velocity_limit']} rad/s")
        except:
            print("! Could not set velocity limit")
        
        # Control mode - velocity control for differential drive
        try:
            axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
            print("✓ Set control mode: VELOCITY_CONTROL")
        except:
            print("! Could not set control mode")
        
        # Input mode
        try:
            axis.controller.config.input_mode = INPUT_MODE_VEL_RAMP
            print("✓ Set input mode: VEL_RAMP")
        except:
            print("! Could not set input mode")
        
        # Trap traj - for smoother velocity ramping
        try:
            axis.trap_traj.config.vel_limit = config['velocity_limit']
            axis.trap_traj.config.accel_limit = config['acceleration_limit']
            axis.trap_traj.config.decel_limit = config['deceleration_limit']
            print(f"✓ Set trajectory limits")
        except:
            print("! Could not set trajectory limits")
    
    # Save configuration
    try:
        od.save_configuration()
        print("\n✅ Configuration saved")
    except Exception as e:
        print(f"\n❌ Error saving configuration: {str(e)}")

def test_basic_movement(od):
    """Test basic movement of both motors"""
    print_header("TESTING BASIC MOVEMENT")
    print("This will move the motors at low speed. Ensure the robot is free to move!")
    proceed = input("Continue with movement test? (y/n): ")
    if proceed.lower() != 'y':
        print("Movement test cancelled.")
        return
    
    # Test each axis
    for axis_num in [0, 1]:
        axis = getattr(od, f'axis{axis_num}')
        print(f"\nTesting axis {axis_num}...")
        
        # Motor and encoder must be calibrated
        if not axis.motor.is_calibrated or not axis.encoder.is_ready:
            print(f"❌ Axis {axis_num} is not fully calibrated. Skipping test.")
            continue
        
        try:
            # Enter closed loop control
            print(f"Setting closed loop control...")
            axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
            time.sleep(0.5)
            
            if axis.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
                print(f"❌ Failed to enter closed loop control. State: {axis.current_state}")
                continue
            
            # Forward at low speed
            print(f"Moving forward at 1 rad/s for 2 seconds...")
            axis.controller.input_vel = 1.0
            time.sleep(2.0)
            
            # Stop
            print("Stopping...")
            axis.controller.input_vel = 0.0
            time.sleep(0.5)
            
            # Backward at low speed
            print(f"Moving backward at 1 rad/s for 2 seconds...")
            axis.controller.input_vel = -1.0
            time.sleep(2.0)
            
            # Stop and idle
            print("Stopping...")
            axis.controller.input_vel = 0.0
            time.sleep(0.5)
            axis.requested_state = AXIS_STATE_IDLE
            
            print(f"✅ Axis {axis_num} test complete")
            
        except Exception as e:
            print(f"❌ Error during movement test: {str(e)}")
            try:
                axis.controller.input_vel = 0.0
                axis.requested_state = AXIS_STATE_IDLE
            except:
                pass

def generate_ros2_example(wheel_radius, wheel_base):
    """Generate example ROS 2 commands for testing"""
    print_header("ROS 2 COMMANDS")
    print("Use these commands to test with ROS 2 once the driver is running:")
    print("\n1. Launch the ODrive driver:")
    print("   ros2 launch odrive_ros2 odrive.launch.py")
    
    print("\n2. Check the available topics:")
    print("   ros2 topic list")
    
    print("\n3. Send velocity commands (adjust values as needed):")
    print("   # Forward at 0.2 m/s:")
    print("   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"linear: {x: 0.2, y: 0.0, z: 0.0}\" -1")
    
    print("\n   # Turn left at 0.5 rad/s while moving forward:")
    print("   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}\" -1")
    
    print("\n   # Stop:")
    print("   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}\" -1")
    
    # Calculate wheel velocities for reference
    print(f"\nFor reference, with wheel_radius={wheel_radius}m and wheel_base={wheel_base}m:")
    v = 0.2  # linear velocity in m/s
    w = 0.5  # angular velocity in rad/s
    right_wheel_vel = (v + w * wheel_base / 2) / wheel_radius
    left_wheel_vel = (v - w * wheel_base / 2) / wheel_radius
    print(f"  - Forward 0.2 m/s + Turn 0.5 rad/s results in:")
    print(f"    Left wheel: {left_wheel_vel:.2f} rad/s, Right wheel: {right_wheel_vel:.2f} rad/s")
    
    print("\n4. Monitor odometry data:")
    print("   ros2 topic echo /odom")
    
    print("\n5. Visualize in RViz (if installed):")
    print("   ros2 run rviz2 rviz2 -d [path-to-config-file]")

def update_ros2_config(wheel_radius, wheel_base):
    """Update ROS 2 configuration file"""
    print_header("UPDATING ROS 2 CONFIGURATION")
    
    config_path = "config/odrive_config.yaml"
    if not os.path.exists(config_path):
        print(f"Creating new configuration file: {config_path}")
        os.makedirs("config", exist_ok=True)
        
        config_content = f"""# ODrive ROS 2 Driver Configuration
# Created by setup_ros2_odrive.py

# Robot physical parameters
wheel_radius: {wheel_radius}  # meters
wheel_base: {wheel_base}  # meters

# Motor configuration
left_motor_axis: 0
right_motor_axis: 1
invert_left_motor: false
invert_right_motor: false

# Velocity control
max_linear_velocity: 0.5  # m/s
max_angular_velocity: 1.0  # rad/s
publish_rate: 50  # Hz

# Odometry configuration
encoder_counts_per_rev: 42  # For Hall sensors
enable_odom_tf: true
odom_frame: odom
base_frame: base_link
"""
        
        # Write the config file
        with open(config_path, 'w') as f:
            f.write(config_content)
        print(f"Configuration file created: {config_path}")
    else:
        print(f"Configuration file already exists: {config_path}")
        print("Please edit it manually to set your wheel_radius and wheel_base parameters.")
    
    print("\nKey ROS 2 configuration parameters:")
    print(f"- wheel_radius: {wheel_radius} meters")
    print(f"- wheel_base: {wheel_base} meters")
    print(f"- left_motor_axis: 0")
    print(f"- right_motor_axis: 1")

def main():
    parser = argparse.ArgumentParser(description='ODrive ROS 2 Setup')
    parser.add_argument('--wheel-radius', type=float, default=0.085, help='Wheel radius in meters (default: 0.085)')
    parser.add_argument('--wheel-base', type=float, default=0.3, help='Distance between wheels in meters (default: 0.3)')
    parser.add_argument('--current-limit', type=float, default=30.0, help='Motor current limit in amps (default: 30.0)')
    parser.add_argument('--velocity-limit', type=float, default=15.0, help='Motor velocity limit in rad/s (default: 15.0)')
    parser.add_argument('--accel-limit', type=float, default=5.0, help='Acceleration limit in rad/s² (default: 5.0)')
    args = parser.parse_args()
    
    print_header("ODRIVE ROS 2 SETUP UTILITY")
    print("This utility will configure your ODrive for use with ROS 2")
    print("and help test that everything is working properly.")
    
    # Config dictionary from args
    config = {
        'wheel_radius': args.wheel_radius,
        'wheel_base': args.wheel_base,
        'current_limit': args.current_limit,
        'velocity_limit': args.velocity_limit,
        'acceleration_limit': args.accel_limit,
        'deceleration_limit': args.accel_limit
    }
    
    # Check if ODrive is connected
    od = check_odrive()
    if not od:
        print("Please make sure your ODrive is connected and try again.")
        sys.exit(1)
    
    # Check calibration status
    calibrated = check_calibration_status(od)
    if not calibrated:
        print("\n⚠️ One or both motors/encoders are not calibrated.")
        print("Run calibration first:")
        print("  ./scripts/calibration_sequence.py")
        retry = input("\nContinue anyway? (not recommended) (y/n): ")
        if retry.lower() != 'y':
            print("Setup cancelled. Please run calibration first.")
            sys.exit(0)
    
    # Configure ODrive for ROS 2
    configure_for_ros2(od, config)
    
    # Test basic movement
    test_basic_movement(od)
    
    # Update ROS 2 configuration
    update_ros2_config(config['wheel_radius'], config['wheel_base'])
    
    # Check ROS 2 installation
    ros_installed = check_ros_installation()
    
    # Generate ROS 2 example commands
    generate_ros2_example(config['wheel_radius'], config['wheel_base'])
    
    print_header("SETUP COMPLETE")
    print("Your ODrive is now configured for use with ROS 2.")
    
    if not ros_installed:
        print("\n⚠️ ROS 2 check failed. Please make sure ROS 2 is installed")
        print("and properly sourced before trying to use the driver.")
    
    print("\nNext steps:")
    print("1. Check the configuration in config/odrive_config.yaml")
    print("2. Run the ROS 2 driver:")
    print("   ros2 launch odrive_ros2 odrive.launch.py")
    print("3. Send test commands as shown above")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        sys.exit(0)
