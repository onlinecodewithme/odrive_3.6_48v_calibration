#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Motor Troubleshooting Script

This script helps diagnose and solve calibration issues with ODrive motors.
It provides various calibration modes and detailed diagnostics.
"""

import sys
import time
import argparse
import odrive
from odrive.enums import *

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_motor_info(axis):
    """Print detailed motor information for diagnosis"""
    print("Motor state:", axis.current_state)
    
    # Print motor error
    try:
        motor_error = axis.motor.error
        print(f"Motor error: {motor_error}")
        
        # Motor error bit meanings
        error_meanings = {
            0: "NONE",
            1: "PHASE_RESISTANCE_OUT_OF_RANGE",
            2: "PHASE_INDUCTANCE_OUT_OF_RANGE",
            4: "DRV_FAULT",
            8: "CONTROL_DEADLINE_MISSED",
            16: "MODULATION_MAGNITUDE",
            32: "CURRENT_SENSE_SATURATION",
            64: "CURRENT_LIMIT_VIOLATION",
            128: "DC_BUS_OVER_VOLTAGE",
            256: "DC_BUS_UNDER_VOLTAGE",
            512: "DC_BUS_OVER_CURRENT"
        }
        
        # Decode error (assuming it's a bit field)
        if motor_error > 0:
            print("Error details:")
            for bit, meaning in error_meanings.items():
                if bit > 0 and (motor_error & bit):
                    print(f"  - {meaning}")
    except:
        print("Could not access motor error")
    
    # Print encoder error
    try:
        encoder_error = axis.encoder.error
        print(f"Encoder error: {encoder_error}")
    except:
        print("Could not access encoder error")
    
    # Print configuration
    print("\nCurrent Configuration:")
    try:
        print(f"Motor type: {axis.motor.config.motor_type}")
    except:
        pass
        
    try:
        # Try different API paths for current limits
        try:
            print(f"Current limit: {axis.config.dc_max_current}")
        except:
            try:
                print(f"Current limit: {axis.motor.config.current_lim}")
            except:
                print("Could not access current limit")
        
        try:
            print(f"Calibration current: {axis.config.calibration_current}")
        except:
            try:
                print(f"Calibration current: {axis.motor.config.calibration_current}")
            except:
                print("Could not access calibration current")
    except:
        pass
    
    try:
        print(f"Pole pairs: {axis.motor.config.pole_pairs}")
    except:
        pass
        
    try:
        print(f"Encoder mode: {axis.encoder.config.mode}")
        print(f"Encoder CPR: {axis.encoder.config.cpr}")
    except:
        pass

def configure_motor(axis, calibration_current=5.0, current_limit=20.0, pole_pairs=7):
    """Configure motor with conservative settings for troubleshooting"""
    print("Configuring motor with conservative settings...")
    
    # Motor type
    try:
        axis.motor.config.motor_type = MOTOR_TYPE_HIGH_CURRENT
        print("Set motor type: HIGH_CURRENT")
    except:
        print("WARNING: Could not set motor type")
        
    # Current limits - try different API paths
    try:
        # New API (firmware v0.5.1+)
        axis.config.dc_max_current = current_limit
        axis.config.dc_max_negative_current = -current_limit
        axis.config.calibration_current = calibration_current
        print(f"Using new current config API: {current_limit}A limit, {calibration_current}A cal current")
    except:
        try:
            # Old API
            axis.motor.config.current_lim = current_limit
            axis.motor.config.calibration_current = calibration_current
            print(f"Using older current config API: {current_limit}A limit, {calibration_current}A cal current")
        except:
            print("WARNING: Could not set current limits")
    
    # Set pole pairs
    try:
        axis.motor.config.pole_pairs = pole_pairs
        print(f"Set pole pairs: {pole_pairs}")
    except:
        print("WARNING: Could not set pole pairs")
        
    # Safely set calibration voltage
    try:
        axis.motor.config.resistance_calib_max_voltage = 4.0
        print("Set calibration voltage: 4.0V")
    except:
        print("WARNING: Could not set calibration voltage")
    
    # Configure Hall sensors
    try:
        axis.encoder.config.mode = ENCODER_MODE_HALL
        axis.encoder.config.cpr = 6 * pole_pairs
        print(f"Hall sensor mode configured: {6 * pole_pairs} CPR")
    except:
        try:
            # Try alternative API
            axis.encoder.config.mode = 1  # Hall mode
            axis.encoder.config.cpr = 6 * pole_pairs
            print(f"Hall sensor mode configured (alt method): {6 * pole_pairs} CPR")
        except:
            print("WARNING: Could not configure hall sensors")
    
    # Controller settings
    try:
        axis.controller.config.vel_limit = 10.0  # Conservative value
        axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
        print("Controller configured: velocity mode, 10 rad/s limit")
    except:
        print("WARNING: Could not set controller configuration")

def calibrate_motor_only(axis):
    """Perform only motor calibration (resistance/inductance)"""
    print("Starting MOTOR ONLY calibration (no encoder)...")
    print("This will make the motor chirp and vibrate.")
    
    try:
        axis.requested_state = AXIS_STATE_MOTOR_CALIBRATION
        
        # Wait for calibration to finish (with timeout)
        timeout = 30  # seconds
        start_time = time.time()
        
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("Motor calibration timed out!")
                return False
            
        if not axis.motor.is_calibrated:
            print("Motor calibration failed!")
            print_motor_info(axis)
            return False
        
        print("✅ Motor calibration successful!")
        return True
    
    except Exception as e:
        print(f"Error during calibration: {str(e)}")
        return False

def calibrate_encoder_only(axis):
    """Perform only encoder calibration (assuming motor is calibrated)"""
    print("Starting ENCODER ONLY calibration...")
    print("Motor will rotate slowly during this process.")
    
    try:
        if not axis.motor.is_calibrated:
            print("Cannot calibrate encoder: Motor is not calibrated!")
            return False
            
        axis.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION
        
        # Wait for calibration to finish (with timeout)
        timeout = 30  # seconds
        start_time = time.time()
        
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("Encoder calibration timed out!")
                return False
        
        if not axis.encoder.is_ready:
            print("Encoder calibration failed!")
            print_motor_info(axis)
            return False
        
        print("✅ Encoder calibration successful!")
        return True
    
    except Exception as e:
        print(f"Error during calibration: {str(e)}")
        return False

def test_motor(axis, speed=2.0, duration=3.0):
    """Test motor by spinning it at the specified speed"""
    print("Testing motor rotation...")
    
    try:
        # Set closed loop control
        print("Setting closed loop control...")
        axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        time.sleep(0.5)
        
        if axis.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
            print(f"Failed to enter closed loop control. Current state: {axis.current_state}")
            print_motor_info(axis)
            return False
        
        # Forward rotation
        print(f"Spinning forward at {speed} rad/s for {duration} seconds...")
        axis.controller.input_vel = float(speed)
        time.sleep(duration)
        
        # Stop
        print("Stopping...")
        axis.controller.input_vel = 0.0
        time.sleep(0.5)
        
        # Reverse rotation
        print(f"Spinning backward at {speed} rad/s for {duration} seconds...")
        axis.controller.input_vel = float(-speed)
        time.sleep(duration)
        
        # Stop
        print("Stopping...")
        axis.controller.input_vel = 0.0
        time.sleep(0.5)
        
        # Return to idle
        axis.requested_state = AXIS_STATE_IDLE
        
        print("✅ Motor test complete!")
        return True
    
    except Exception as e:
        print(f"Error during motor test: {str(e)}")
        # Try to stop the motor
        try:
            axis.controller.input_vel = 0.0
            axis.requested_state = AXIS_STATE_IDLE
        except:
            pass
        return False

def forced_calibration(axis):
    """Perform a special forced calibration procedure"""
    print("Starting FORCED calibration procedure...")
    
    # Fully reset motor errors
    try:
        axis.motor.error = 0
        axis.encoder.error = 0
        print("Motor and encoder errors reset")
    except:
        print("Failed to reset errors")
    
    # Set very conservative values for motor calibration
    try:
        try:
            axis.config.calibration_current = 3.0  # Very conservative
        except:
            try:
                axis.motor.config.calibration_current = 3.0
            except:
                pass
        
        try:
            axis.motor.config.resistance_calib_max_voltage = 2.0  # Very conservative
        except:
            pass
            
        print("Set ultra-conservative calibration parameters")
    except:
        print("Failed to set conservative parameters")
    
    # Try calibration with forced reset first
    print("Attempting motor calibration with conservative parameters...")
    try:
        axis.requested_state = AXIS_STATE_MOTOR_CALIBRATION
        
        # Wait for calibration to finish
        timeout = 30  # seconds
        start_time = time.time()
        
        while axis.current_state != AXIS_STATE_IDLE:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("Motor calibration timed out!")
                return False
            
        if not axis.motor.is_calibrated:
            print("Conservative calibration failed.")
            return False
            
        print("✅ Motor calibration successful!")
        return True
    except:
        print("Forced calibration attempt failed")
        return False

def main():
    print_header("ODRIVE MOTOR TROUBLESHOOTING")
    print("This script helps diagnose and solve motor calibration issues.")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="ODrive motor troubleshooting")
    parser.add_argument('--axis', type=int, choices=[0, 1], default=0, help="Which axis to troubleshoot (default: 0)")
    parser.add_argument('--current', type=float, default=5.0, help="Calibration current (default: 5.0)")
    parser.add_argument('--limit', type=float, default=20.0, help="Current limit (default: 20.0)")
    parser.add_argument('--poles', type=int, default=7, help="Motor pole pairs (default: 7)")
    parser.add_argument('--mode', choices=['full', 'motor', 'encoder', 'test', 'diagnose', 'force'], 
                        default='diagnose', help="Operation mode (default: diagnose)")
    args = parser.parse_args()
    
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
    
    # Get the specified axis
    axis = getattr(od, f'axis{args.axis}')
    
    print_header(f"TROUBLESHOOTING AXIS {args.axis}")
    print(f"Current state: {axis.current_state}")
    
    if args.mode == 'diagnose':
        # Just diagnose current state
        print("DIAGNOSTICS MODE")
        print_motor_info(axis)
        print("\nTry running with --mode=motor to calibrate only the motor")
        print("Or try --mode=force for conservative calibration")
        
    elif args.mode == 'full':
        # Configure and run full calibration
        configure_motor(axis, args.current, args.limit, args.poles)
        od.save_configuration()
        
        # Motor calibration
        if calibrate_motor_only(axis):
            # If motor calibration succeeded, try encoder
            calibrate_encoder_only(axis)
        
        # Save again
        od.save_configuration()
        
        # Test if both calibrations succeeded
        if axis.motor.is_calibrated and axis.encoder.is_ready:
            test_motor(axis, 2.0, 3.0)
            
    elif args.mode == 'motor':
        # Configure and calibrate only the motor
        configure_motor(axis, args.current, args.limit, args.poles)
        od.save_configuration()
        calibrate_motor_only(axis)
        od.save_configuration()
        
    elif args.mode == 'encoder':
        # Just calibrate the encoder (if motor is already calibrated)
        if not axis.motor.is_calibrated:
            print("Motor must be calibrated before encoder!")
            print("Run with --mode=motor first")
        else:
            calibrate_encoder_only(axis)
            od.save_configuration()
    
    elif args.mode == 'test':
        # Just test the motor
        if not axis.motor.is_calibrated or not axis.encoder.is_ready:
            print("WARNING: Motor and/or encoder are not calibrated!")
            print("Testing may not work or might be dangerous.")
            proceed = input("Continue anyway? (y/n): ")
            if proceed.lower() != 'y':
                print("Test cancelled.")
                sys.exit(0)
                
        test_motor(axis, 2.0, 3.0)
        
    elif args.mode == 'force':
        # Try the forced calibration procedure
        configure_motor(axis, 3.0, 15.0, args.poles)  # Conservative values
        od.save_configuration()
        forced_calibration(axis)
        od.save_configuration()
        
    print_header("TROUBLESHOOTING COMPLETE")
    print("Current motor state:")
    print_motor_info(axis)
    print("\nFor help with calibration issues, refer to MOTOR_CALIBRATION.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTroubleshooting cancelled by user.")
        sys.exit(0)
