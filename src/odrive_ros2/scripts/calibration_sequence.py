#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Calibration Sequence

This script runs a sequence of different calibration approaches,
capturing the results of each to help diagnose and solve calibration issues.
"""

import os
import sys
import time
import subprocess
import datetime

def print_header(text):
    header = "\n" + "=" * 70 + "\n"
    header += f"  {text}\n"
    header += "=" * 70
    print(header)
    return header

def run_command(command, log_file=None):
    """Run a command and optionally log the output to a file"""
    print(f"Executing: {command}")
    
    if log_file:
        with open(log_file, 'a') as f:
            f.write(f"\n\n{'-' * 40}\n")
            f.write(f"COMMAND: {command}\n")
            f.write(f"TIME: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'-' * 40}\n\n")
        
        # Run command and capture output to log file
        with open(log_file, 'a') as f:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Read and write output line by line (and also print to console)
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                f.write(line)
            
            process.stdout.close()
            return_code = process.wait()
            f.write(f"\nCommand completed with return code: {return_code}\n")
            return return_code
    else:
        # Just run the command normally
        return subprocess.call(command, shell=True)

def main():
    # Create log directory
    logs_dir = os.path.expanduser("~/odrive_calibration_logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a log file for this calibration sequence
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"calibration_sequence_{timestamp}.log")
    
    with open(log_file, 'w') as f:
        f.write("ODrive Calibration Sequence Log\n")
        f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n\n")
    
    print_header("ODRIVE CALIBRATION SEQUENCE")
    print(f"Running a sequence of calibration approaches...")
    print(f"Results will be logged to: {log_file}")
    print()
    
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # List of calibration approaches to try (in order of increasing aggressiveness)
    calibration_steps = [
        {
            "name": "Initial Diagnostic",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=diagnose",
            "description": "Getting initial diagnostic information"
        },
        {
            "name": "Minimal Calibration",
            "command": f"{script_dir}/minimal_calibration.py",
            "description": "Using minimal conservative settings for both axes"
        },
        {
            "name": "Axis 0 - Ultra Conservative",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=force --axis=0 --current=1.5",
            "description": "Ultra conservative forced calibration for Axis 0"
        },
        {
            "name": "Axis 1 - Ultra Conservative",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=force --axis=1 --current=1.5",
            "description": "Ultra conservative forced calibration for Axis 1"
        },
        {
            "name": "Axis 0 - Conservative",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=motor --axis=0 --current=3.0 --limit=15.0",
            "description": "Conservative motor-only calibration for Axis 0"
        },
        {
            "name": "Axis 1 - Conservative",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=motor --axis=1 --current=3.0 --limit=15.0",
            "description": "Conservative motor-only calibration for Axis 1"
        },
        {
            "name": "Axis 0 - Standard",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=motor --axis=0 --current=5.0 --limit=20.0",
            "description": "Standard motor-only calibration for Axis 0"
        },
        {
            "name": "Axis 1 - Standard",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=motor --axis=1 --current=5.0 --limit=20.0",
            "description": "Standard motor-only calibration for Axis 1"
        },
        {
            "name": "Axis 0 - Encoder Calibration",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=encoder --axis=0",
            "description": "Encoder calibration for Axis 0 (if motor is calibrated)"
        },
        {
            "name": "Axis 1 - Encoder Calibration",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=encoder --axis=1",
            "description": "Encoder calibration for Axis 1 (if motor is calibrated)"
        },
        {
            "name": "Final Diagnostic",
            "command": f"{script_dir}/troubleshoot_calibration.py --mode=diagnose",
            "description": "Getting final diagnostic information"
        }
    ]
    
    # Run each step
    results = []
    
    for i, step in enumerate(calibration_steps):
        print_header(f"STEP {i+1}/{len(calibration_steps)}: {step['name']}")
        print(f"Description: {step['description']}")
        
        # Ask for confirmation
        if i > 0:  # Don't ask for first step (diagnostic)
            proceed = input(f"Continue with this step? (y/n): ")
            if proceed.lower() != 'y':
                print(f"Skipping step {i+1}")
                results.append({"step": step['name'], "result": "Skipped"})
                continue
        
        # Run the command
        try:
            return_code = run_command(step['command'], log_file)
            if return_code == 0:
                results.append({"step": step['name'], "result": "Success"})
            else:
                results.append({"step": step['name'], "result": f"Failed (code {return_code})"})
        except Exception as e:
            print(f"Error executing command: {e}")
            results.append({"step": step['name'], "result": f"Error: {str(e)}"})
        
        # Pause between steps
        if i < len(calibration_steps) - 1:
            print("\nPausing for system to settle...")
            time.sleep(3)
    
    # Print summary
    print_header("CALIBRATION SEQUENCE SUMMARY")
    
    for result in results:
        print(f"{result['step']:30} : {result['result']}")
    
    print(f"\nDetailed results logged to: {log_file}")
    print("\nNext steps:")
    print("1. Check the log file for detailed information about each calibration attempt")
    print("2. If any of the motor calibrations succeeded, try the encoder calibration next")
    print("3. If motors are calibrated and encoders are ready, try the ROS 2 launch:")
    print("   ros2 launch odrive_ros2 odrive.launch.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCalibration sequence cancelled by user.")
        sys.exit(0)
