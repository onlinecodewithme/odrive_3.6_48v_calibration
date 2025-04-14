#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Motor Calibration and Test Script

This script performs a complete calibration of both motors on the ODrive:
- Motor resistance and inductance calibration
- Encoder (hall sensor) calibration
- Motor rotation test

Use with caution: Motors will move during calibration and testing!
"""

import sys
import time
import argparse
import odrive
from odrive.enums import *
import numpy as np

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def connect_to_odrive():
    """Connect to the ODrive"""
    print_header("CONNECTING TO ODRIVE")
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
        print(f"❌ Error connecting to ODrive: {str(e)}")
        sys.exit(1)

def check_if_calibrated(axis):
    """Check if the specified axis is already calibrated"""
    if axis.motor.is_calibrated and axis.encoder.is_ready:
        return True
    return False

def setup_motor_config(axis, config):
    """Set up motor configuration for calibration"""
    # Set motor type
    try:
        axis.motor.config.motor_type = MOTOR_TYPE_HIGH_CURRENT
        print("  Set motor type: HIGH_CURRENT")
    except:
        print("  WARNING: Could not set motor type")
    
    # Handle different possible API structures based on firmware version
    if config:
        # Current configuration - try different API paths
        try:
            # New API (firmware v0.5.1+)
            if 'current_limit' in config:
                axis.config.dc_max_current = config['current_limit']
                axis.config.dc_max_negative_current = -config['current_limit']
            if 'calibration_current' in config:
                axis.config.calibration_current = config['calibration_current']
            print("  Using new current config API")
        except:
            try:
                # Old API
                if 'current_limit' in config:
                    axis.motor.config.current_lim = config['current_limit']
                if 'calibration_current' in config:
                    axis.motor.config.calibration_current = config['calibration_current']
                print("  Using older current config API")
            except:
                print("  WARNING: Could not set current limits")
        
        # Other motor settings
        try:
            if 'pole_pairs' in config:
                axis.motor.config.pole_pairs = config['pole_pairs']
                # Update CPR based on pole pairs for Hall sensors
                pole_pairs = config['pole_pairs']
            else:
                pole_pairs = 7  # Default
        except:
            print("  WARNING: Could not set pole pairs")
            pole_pairs = 7
            
        try:
            if 'resistance_calib_max_voltage' in config:
                axis.motor.config.resistance_calib_max_voltage = config['resistance_calib_max_voltage']
        except:
            print("  WARNING: Could not set calibration voltage")
    else:
        # Set defaults - try different API paths
        try:
            # Try new API first
            axis.config.dc_max_current = 30.0
            axis.config.dc_max_negative_current = -30.0
            axis.config.calibration_current = 10.0
            print("  Using new current config API with defaults")
        except:
            try:
                # Try old API
                axis.motor.config.current_lim = 30.0
                axis.motor.config.calibration_current = 10.0
                print("  Using older current config API with defaults")
            except:
                print("  WARNING: Could not set default current limits")
        
        # Try to set other default values
        try:
            axis.motor.config.pole_pairs = 7
            pole_pairs = 7
        except:
            print("  WARNING: Could not set default pole pairs")
            pole_pairs = 7
            
        try:
            axis.motor.config.resistance_calib_max_voltage = 4.0
        except:
            print("  WARNING: Could not set default calibration voltage")
    
    # Configure Hall sensors
    try:
        axis.encoder.config.mode = ENCODER_MODE_HALL
        axis.encoder.config.cpr = 6 * pole_pairs  # For hall sensors
        print("  Hall sensor mode configured")
    except:
        try:
            # Try alternative API
            axis.encoder.config.mode = 1  # Hall mode
            axis.encoder.config.cpr = 6 * pole_pairs
            print("  Hall sensor mode configured (alt method)")
        except:
            print("  WARNING: Could not configure hall sensors")
    
    # Controller configuration
    try:
        axis.controller.config.vel_limit = 20.0  # [rad/s]
        axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
    except:
        print("  WARNING: Could not set controller configuration")

def calibrate_motor(od, axis_num, config=None):
    """Calibrate motor and encoder for a single axis"""
    print_header(f"CALIBRATING AXIS {axis_num}")
    
    # Get the axis
    axis = getattr(od, f'axis{axis_num}')
    
    # Check if already calibrated
    if check_if_calibrated(axis):
        print(f"Axis {axis_num} appears to be already calibrated.")
        recalibrate = input("Would you like to recalibrate anyway? (y/n): ")
        if recalibrate.lower() != 'y':
            print(f"Skipping calibration for axis {axis_num}.")
            return True
    
    # Configure motor
    print(f"Configuring axis {axis_num}...")
    try:
        setup_motor_config(axis, config)
        print("Configuration applied.")
    except Exception as e:
        print(f"❌ Error during configuration: {str(e)}")
        return False
    
    # Start motor calibration
    print(f"Starting motor calibration for axis {axis_num}...")
    print("This will make the motor chirp and vibrate.")
    
    try:
        axis.requested_state = AXIS_STATE_MOTOR_CALIBRATION
        
        # Wait for calibration to finish (with timeout)
        timeout = 30  # seconds
        start_time = time.time()
        
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("❌ Motor calibration timed out!")
                return False
            
        if not axis.motor.is_calibrated:
            print("❌ Motor calibration failed!")
            print(f"Error: {axis.motor.error}")
            return False
        
        print("✅ Motor calibration successful!")
        
        # Start encoder (hall sensor) calibration
        print(f"Starting encoder calibration for axis {axis_num}...")
        print("This will rotate the motor slowly. Make sure it can spin freely.")
        
        axis.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION
        
        # Wait for calibration to finish (with timeout)
        timeout = 30  # seconds
        start_time = time.time()
        
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("❌ Encoder calibration timed out!")
                return False
        
        if not axis.encoder.is_ready:
            print("❌ Encoder calibration failed!")
            print(f"Error: {axis.encoder.error}")
            return False
        
        print("✅ Encoder calibration successful!")
        
        # Save configuration
        print("Saving configuration...")
        od.save_configuration()
        print("✅ Configuration saved.")
        
        return True
    
    except Exception as e:
        print(f"❌ Error during calibration: {str(e)}")
        return False

def test_motor(od, axis_num, speed=2.0, duration=3.0):
    """Test motor by spinning it at the specified speed"""
    print_header(f"TESTING AXIS {axis_num}")
    
    # Get the axis
    axis = getattr(od, f'axis{axis_num}')
    
    # Check if calibrated
    if not check_if_calibrated(axis):
        print(f"❌ Axis {axis_num} is not calibrated. Please calibrate first.")
        return False
    
    try:
        # Set closed loop control
        print(f"Setting axis {axis_num} to closed loop control...")
        axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        time.sleep(0.1)
        
        if axis.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
            print(f"❌ Failed to enter closed loop control. Error: {axis.error}")
            return False
        
        # Test forward rotation
        print(f"Spinning motor {axis_num} forward at {speed} rad/s for {duration} seconds...")
        axis.controller.input_vel = float(speed)
        time.sleep(duration)
        
        # Stop
        print("Stopping motor...")
        axis.controller.input_vel = 0.0
        time.sleep(0.5)
        
        # Test reverse rotation
        print(f"Spinning motor {axis_num} backward at {speed} rad/s for {duration} seconds...")
        axis.controller.input_vel = float(-speed)
        time.sleep(duration)
        
        # Stop
        print("Stopping motor...")
        axis.controller.input_vel = 0.0
        time.sleep(0.5)
        
        # Idle state
        axis.requested_state = AXIS_STATE_IDLE
        
        print(f"✅ Motor {axis_num} test complete!")
        return True
    
    except Exception as e:
        print(f"❌ Error during motor test: {str(e)}")
        # Try to stop the motor
        try:
            axis.controller.input_vel = 0.0
            axis.requested_state = AXIS_STATE_IDLE
        except:
            pass
        return False

def main():
    print_header("ODRIVE MOTOR CALIBRATION AND TEST")
    print("This script will calibrate your motors and encoders, then test rotation.")
    print("WARNING: Motors will move during this process!")
    print("Make sure the motors are clear to rotate freely.")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="ODrive motor calibration and test")
    parser.add_argument('--axis', type=int, choices=[0, 1], help="Calibrate and test only this axis")
    parser.add_argument('--current-limit', type=float, default=30.0, help="Motor current limit (A)")
    parser.add_argument('--calibration-current', type=float, default=10.0, help="Calibration current (A)")
    parser.add_argument('--pole-pairs', type=int, default=7, help="Motor pole pairs")
    parser.add_argument('--speed', type=float, default=2.0, help="Test rotation speed (rad/s)")
    args = parser.parse_args()
    
    # Connect to ODrive
    od = connect_to_odrive()
    
    # Motor configuration 
    motor_config = {
        'current_limit': args.current_limit,
        'calibration_current': args.calibration_current,
        'pole_pairs': args.pole_pairs,
        'resistance_calib_max_voltage': 4.0,  # Safe for most motors
        'requested_current_range': 60.0,  # For high-power motors
    }
    
    # Determine which axes to calibrate
    axes_to_calibrate = [args.axis] if args.axis in [0, 1] else [0, 1]
    
    # Confirm before proceeding
    proceed = input("\nReady to begin calibration? Motors will move! (y/n): ")
    if proceed.lower() != 'y':
        print("Calibration cancelled.")
        sys.exit(0)
    
    # Calibrate each axis
    success = True
    for axis_num in axes_to_calibrate:
        if not calibrate_motor(od, axis_num, motor_config):
            success = False
            print(f"Calibration failed for axis {axis_num}")
        else:
            # If calibration succeeded, test the motor
            test_motor(od, axis_num, args.speed)
    
    # Final status
    print_header("CALIBRATION COMPLETE")
    if success:
        print("✅ All requested axes have been calibrated and tested successfully!")
        print("\nYou can now use the motors with the ROS 2 ODrive driver.")
        print("Run the driver with: ros2 launch odrive_ros2 odrive.launch.py")
    else:
        print("⚠️ Some calibration steps failed. Check the output above for details.")
        print("You may need to retry the calibration or adjust parameters.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCalibration cancelled by user.")
        sys.exit(0)
