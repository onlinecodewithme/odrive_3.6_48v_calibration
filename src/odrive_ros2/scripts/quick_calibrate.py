#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Quick Calibration Script

A simpler, streamlined version of the motor calibration process 
specifically for 48V 1000W motors with Hall sensors.
"""

import sys
import time
import odrive
from odrive.enums import *

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def main():
    print_header("ODRIVE QUICK CALIBRATION")
    print("This script will quickly calibrate your ODrive 48V motors with Hall sensors")
    print("WARNING: Motors will move during this process!")
    
    print("\nLooking for ODrive...")
    try:
        od = odrive.find_any(timeout=10)
        print(f"✅ Found ODrive!")
        print(f"Hardware: v{od.hw_version_major}.{od.hw_version_minor}")
        print(f"Firmware: v{od.fw_version_major}.{od.fw_version_minor}.{od.fw_version_revision}")
    except Exception as e:
        print(f"❌ Cannot find ODrive: {str(e)}")
        sys.exit(1)
    
    # Ask for confirmation
    proceed = input("\nBoth motors will be calibrated. Make sure they can rotate freely.\nContinue? (y/n): ")
    if proceed.lower() != 'y':
        print("Calibration cancelled.")
        sys.exit(0)
    
    # Configure both motors for 48V 1000W motors with Hall sensors
    for axis_num in [0, 1]:
        try:
            axis = getattr(od, f'axis{axis_num}')
            
            # Configure motor (optimized for 48V 1000W motors)
            print(f"\nConfiguring motor {axis_num}...")
            # In newer ODrive firmware, some config parameters have moved
            # Motor configuration
            axis.motor.config.motor_type = MOTOR_TYPE_HIGH_CURRENT
            
            # Current limits
            try:
                # Try the current API (newer firmware)
                axis.config.dc_max_negative_current = -40.0  # 40A for 1000W motors
                axis.config.dc_max_current = 40.0
                axis.config.calibration_current = 10.0
                print("  Using new current config API")
            except:
                try:
                    # Try the older API structure
                    axis.motor.config.current_lim = 40.0
                    axis.motor.config.calibration_current = 10.0
                    print("  Using older current config API")
                except:
                    print("  WARNING: Could not set current limits")
            
            # Other motor settings
            try:
                axis.motor.config.pole_pairs = 7
            except:
                print("  WARNING: Could not set pole pairs")
                
            try:
                axis.motor.config.resistance_calib_max_voltage = 4.0
            except:
                print("  WARNING: Could not set calibration voltage")
            
            # Configure Hall sensors
            try:
                axis.encoder.config.mode = ENCODER_MODE_HALL
                axis.encoder.config.cpr = 42  # 6 states * 7 pole pairs
                print("  Hall sensor mode configured")
            except:
                try:
                    # Try alternative paths
                    axis.encoder.config.mode = 1  # Hall mode
                    axis.encoder.config.cpr = 42
                    print("  Hall sensor mode configured (alt method)")
                except:
                    print("  WARNING: Could not configure hall sensors")
            
            # Configure controller
            try:
                axis.controller.config.vel_limit = 25.0
                axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
            except:
                print("  WARNING: Could not set controller config")
            
            print(f"✅ Configuration applied to motor {axis_num}")
        except Exception as e:
            print(f"❌ Error configuring motor {axis_num}: {str(e)}")
            continue
    
    # Run calibration for both motors
    print_header("STARTING CALIBRATION")
    
    # First calibrate motors (resistance/inductance)
    for axis_num in [0, 1]:
        try:
            axis = getattr(od, f'axis{axis_num}')
            print(f"\nCalibrating motor {axis_num}...")
            axis.requested_state = AXIS_STATE_MOTOR_CALIBRATION
            
            # Wait for calibration to complete
            while axis.current_state != AXIS_STATE_IDLE:
                time.sleep(0.1)
                
            if axis.motor.is_calibrated:
                print(f"✅ Motor {axis_num} calibration successful")
            else:
                print(f"❌ Motor {axis_num} calibration failed: {axis.motor.error}")
        except Exception as e:
            print(f"❌ Error during motor {axis_num} calibration: {str(e)}")
    
    # Then calibrate encoders (hall sensors)
    for axis_num in [0, 1]:
        try:
            axis = getattr(od, f'axis{axis_num}')
            if not axis.motor.is_calibrated:
                print(f"⚠️ Skipping encoder calibration for axis {axis_num} due to failed motor calibration")
                continue
                
            print(f"\nCalibrating encoder {axis_num}...")
            print("Motor will rotate slowly during this process.")
            axis.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION
            
            # Wait for calibration to complete
            while axis.current_state != AXIS_STATE_IDLE:
                time.sleep(0.1)
                
            if axis.encoder.is_ready:
                print(f"✅ Encoder {axis_num} calibration successful")
            else:
                print(f"❌ Encoder {axis_num} calibration failed: {axis.encoder.error}")
        except Exception as e:
            print(f"❌ Error during encoder {axis_num} calibration: {str(e)}")
    
    # Save configuration
    try:
        od.save_configuration()
        print("\n✅ Configuration saved")
    except Exception as e:
        print(f"\n❌ Error saving configuration: {str(e)}")
    
    # Brief rotation test
    print_header("MOTOR TEST")
    print("Testing motor rotation (3 seconds in each direction)")
    
    # After saving configuration, reconnect to the ODrive to avoid potential interface issues
    try:
        print("Reconnecting to ODrive for motor testing...")
        # Give time for the ODrive to reset if needed
        time.sleep(1.0)
        # Reconnect
        od = odrive.find_any(timeout=10)
        print("✅ Reconnected to ODrive for testing")
    except Exception as e:
        print(f"❌ Failed to reconnect to ODrive: {str(e)}")
        print("Skipping motor testing phase")
        od = None
    
    # Only proceed with tests if ODrive is connected
    if od:
        for axis_num in [0, 1]:
            try:
                axis = getattr(od, f'axis{axis_num}')
                # Check if axis and motor attributes are accessible
                if not hasattr(axis, 'motor') or not hasattr(axis, 'encoder'):
                    print(f"⚠️ Axis {axis_num} attributes not accessible. Skipping test.")
                    continue
                
                # Check calibration status
                if not hasattr(axis.motor, 'is_calibrated') or not axis.motor.is_calibrated or not hasattr(axis.encoder, 'is_ready') or not axis.encoder.is_ready:
                    print(f"⚠️ Axis {axis_num} not fully calibrated. Skipping test.")
                    continue
                    
                print(f"\nTesting motor {axis_num}...")
                
                # Set closed loop control with additional error checking
                try:
                    axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
                    time.sleep(0.5)  # Give more time to enter closed loop mode
                    
                    if hasattr(axis, 'current_state') and axis.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
                        print(f"⚠️ Failed to enter closed loop control. Current state: {axis.current_state}")
                        continue
                        
                    # Forward
                    print(f"  - Rotating forward...")
                    axis.controller.input_vel = 5.0  # 5 rad/s
                    time.sleep(3.0)
                    
                    # Stop
                    axis.controller.input_vel = 0.0
                    time.sleep(0.5)
                    
                    # Reverse
                    print(f"  - Rotating backward...")
                    axis.controller.input_vel = -5.0  # -5 rad/s
                    time.sleep(3.0)
                    
                    # Stop and return to idle
                    axis.controller.input_vel = 0.0
                    time.sleep(0.5)
                    axis.requested_state = AXIS_STATE_IDLE
                    print(f"✅ Motor {axis_num} test complete")
                except Exception as e:
                    print(f"❌ Error during motor {axis_num} control: {str(e)}")
                    # Try to stop the motor
                    try:
                        axis.controller.input_vel = 0.0
                        axis.requested_state = AXIS_STATE_IDLE
                    except:
                        pass
            except Exception as e:
                print(f"❌ Error accessing axis {axis_num}: {str(e)}")
    else:
        print("⚠️ Motor tests skipped due to ODrive connection issues")
    
    print_header("CALIBRATION COMPLETE")
    print("Your ODrive motors have been calibrated and tested.")
    print("You can now run the ROS 2 driver:")
    print("  ros2 launch odrive_ros2 odrive.launch.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCalibration cancelled by user.")
        sys.exit(0)
