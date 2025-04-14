#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Minimal Calibration Script

A specialized script for calibrating motors that are difficult to calibrate.
Uses extremely conservative settings and a step-by-step approach for 48V 1000W motors.
"""

import sys
import time
import odrive
from odrive.enums import *

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def reset_errors(axis):
    """Reset all errors on the axis"""
    try:
        axis.motor.error = 0
        print("Motor errors reset")
    except:
        pass
        
    try:
        axis.encoder.error = 0
        print("Encoder errors reset")
    except:
        pass
        
    try:
        axis.controller.error = 0
        print("Controller errors reset")
    except:
        pass
        
    try:
        axis.error = 0
        print("Axis errors reset")
    except:
        pass

def safe_config_48v_motor(od, axis_num):
    """Apply minimal safe configuration for a 48V motor"""
    print(f"Applying minimal safe configuration for axis {axis_num}...")
    
    # Get the axis
    axis = getattr(od, f'axis{axis_num}')
    
    # Reset errors first
    reset_errors(axis)
    
    # Motor configuration (special version for problematic motors)
    try:
        axis.motor.config.motor_type = MOTOR_TYPE_HIGH_CURRENT
        print("- Set motor type: HIGH_CURRENT")
    except:
        print("! Could not set motor type")
    
    # Use extremely conservative current limits
    try:
        # Try API v0.5.1+
        axis.config.dc_max_current = 5.0  # Very conservative
        axis.config.dc_max_negative_current = -5.0
        print("- Set current limits: 5.0A (new API)")
    except:
        try:
            # Older API
            axis.motor.config.current_lim = 5.0
            print("- Set current limits: 5.0A (old API)")
        except:
            print("! Could not set current limits")
    
    # Set very low calibration current
    try:
        # Try API v0.5.1+
        axis.config.calibration_current = 2.0  # Minimum usable value
        print("- Set calibration current: 2.0A (new API)")
    except:
        try:
            # Older API
            axis.motor.config.calibration_current = 2.0
            print("- Set calibration current: 2.0A (old API)")
        except:
            print("! Could not set calibration current")
            
    # Minimum voltage for calibration
    try:
        axis.motor.config.resistance_calib_max_voltage = 2.0  # Very low, safe value
        print("- Set calibration voltage: 2.0V")
    except:
        print("! Could not set calibration voltage")
    
    # Configure default pole pairs
    try:
        axis.motor.config.pole_pairs = 7
        print("- Set pole pairs: 7")
    except:
        print("! Could not set pole pairs")
    
    # Configure for Hall sensors
    try:
        axis.encoder.config.mode = ENCODER_MODE_HALL
        axis.encoder.config.cpr = 42  # 6 * 7 pole pairs
        print("- Set Hall sensor mode: 42 CPR")
    except:
        try:
            # Alternate API
            axis.encoder.config.mode = 1  # Hall
            axis.encoder.config.cpr = 42
            print("- Set Hall sensor mode: 42 CPR (alt)")
        except:
            print("! Could not configure Hall sensors")
            
    # Save configuration
    try:
        od.save_configuration()
        print("✓ Configuration saved")
    except:
        print("! Failed to save configuration")
    
    # Extra time for saving
    time.sleep(1.0)

def minimal_motor_calibration(od, axis_num):
    """Perform a minimal motor calibration"""
    print_header(f"MINIMAL MOTOR CALIBRATION (AXIS {axis_num})")
    
    # Get the axis
    axis = getattr(od, f'axis{axis_num}')
    
    # Minimal calibration
    print(f"Starting motor calibration with minimal current...")
    print("This will make the motor emit a slight noise.")
    
    try:
        # Put in motor calibration state
        axis.requested_state = AXIS_STATE_MOTOR_CALIBRATION
        
        # Wait for calibration (with timeout)
        timeout = 20.0  # Use shorter timeout
        start = time.time()
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.2)
            # Print progress
            elapsed = time.time() - start
            if elapsed > timeout:
                print("! Calibration timed out")
                return False
                
        # Check result
        if axis.motor.is_calibrated:
            print("✓ Motor calibration successful")
            return True
        else:
            print(f"! Motor calibration failed: {axis.motor.error}")
            return False
            
    except Exception as e:
        print(f"! Error during motor calibration: {e}")
        return False

def main():
    print_header("ODRIVE MINIMAL CALIBRATION")
    print("This script uses extremely conservative settings for difficult motors.")
    print("For use with 48V 1000W motors that are challenging to calibrate.")
    print("WARNING: Motors will move very slightly during calibration.")
    
    # Connect to ODrive
    print("Looking for ODrive...")
    try:
        od = odrive.find_any(timeout=10)
        print(f"✅ Found ODrive!")
        print(f"Hardware: v{od.hw_version_major}.{od.hw_version_minor}")
        print(f"Firmware: v{od.fw_version_major}.{od.fw_version_minor}.{od.fw_version_revision}")
    except Exception as e:
        print(f"Cannot find ODrive: {str(e)}")
        sys.exit(1)
    
    # Confirm before proceeding
    proceed = input("Ready to apply minimal calibration to both motors? (y/n): ")
    if proceed.lower() != 'y':
        print("Calibration cancelled.")
        sys.exit(0)
    
    # Apply configuration to both axes
    for axis_num in [0, 1]:
        safe_config_48v_motor(od, axis_num)
        time.sleep(1.0)  # Extra time between operations
    
    # Give a moment for configuration to settle
    print("Waiting for configuration to settle...")
    time.sleep(2.0)
    
    # Try to reconnect to ODrive
    try:
        print("Reconnecting to ODrive...")
        od = odrive.find_any(timeout=10)
        print("✓ Reconnected")
    except:
        print("! Failed to reconnect. Please restart the ODrive and try again.")
        sys.exit(1)
    
    # Calibrate one axis at a time
    results = []
    for axis_num in [0, 1]:
        result = minimal_motor_calibration(od, axis_num)
        results.append(result)
        time.sleep(1.0)  # Extra time between calibrations
        
    # Save configuration again
    try:
        od.save_configuration()
        print("✓ Final configuration saved")
    except:
        print("! Failed to save final configuration")
    
    print_header("CALIBRATION SUMMARY")
    for axis_num in [0, 1]:
        if results[axis_num]:
            print(f"Axis {axis_num}: ✓ Successfully calibrated")
        else:
            print(f"Axis {axis_num}: ✗ Calibration failed")
    
    print("\nNext steps:")
    if any(results):
        print("1. For successful calibrations, try to run the encoder calibration:")
        print("   ./scripts/troubleshoot_calibration.py --mode=encoder --axis=0  # or axis=1")
    else:
        print("1. Try further reducing the calibration current:")
        print("   ./scripts/troubleshoot_calibration.py --mode=force --current=1.5 --axis=0")
        
    print("2. For more detailed motor diagnostics:")
    print("   ./scripts/troubleshoot_calibration.py --mode=diagnose")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCalibration cancelled by user.")
        sys.exit(0)
