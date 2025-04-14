#!/Users/randikaprasad/miniforge3/bin/python
"""
Simplified ODrive Firmware Force Update Script
This script provides a more direct way to force update the ODrive firmware.
"""

import sys
import os
import argparse
import time
import subprocess
import platform

def find_odrive():
    """Try to find the ODrive via direct USB commands"""
    print("Looking for ODrive...")
    try:
        # Try using lsusb on Linux
        if platform.system() == "Linux":
            result = subprocess.run(["lsusb", "-d", "1209:0d32"], 
                                   capture_output=True, text=True, check=False)
            if "1209:0d32" in result.stdout:
                print("Found ODrive via lsusb")
                return True
        
        # Try using system_profiler on macOS
        if platform.system() == "Darwin":
            result = subprocess.run(["system_profiler", "SPUSBDataType", "-xml"], 
                                  capture_output=True, text=True, check=False)
            if "ODrive" in result.stdout:
                print("Found ODrive via system_profiler")
                return True
        
        # Try using odrivetool
        result = subprocess.run(["odrivetool", "version"], 
                               capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("ODrive tool is available")
            return True
            
        print("ODrive not found. Please check connections and power.")
        return False
    except Exception as e:
        print(f"Error looking for ODrive: {e}")
        return False

def check_dfu_util():
    """Check if dfu-util is installed"""
    try:
        result = subprocess.run(["dfu-util", "--version"], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("dfu-util is available")
            return True
        
        print("dfu-util not found")
        return False
    except:
        print("dfu-util not found")
        return False

def install_dfu_util():
    """Install dfu-util"""
    system = platform.system()
    
    print(f"Installing dfu-util on {system}...")
    try:
        if system == "Linux":
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "dfu-util"], check=True)
        elif system == "Darwin":  # macOS
            subprocess.run(["brew", "install", "dfu-util"], check=True)
        else:
            print(f"Automatic installation not supported on {system}. Please install dfu-util manually.")
            return False
        
        print("dfu-util installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dfu-util: {e}")
        return False

def force_dfu_mode():
    """Force ODrive into DFU mode using various methods"""
    print("Attempting to put ODrive into DFU mode...")
    
    try:
        # Try using odrivetool
        subprocess.run(["odrivetool", "dfu"], check=False)
        print("Attempted to enter DFU mode using odrivetool")
        
        # Wait a bit to see if it worked
        time.sleep(2)
        
        # Check if device is in DFU mode
        result = subprocess.run(["dfu-util", "-l"], 
                              capture_output=True, text=True, check=False)
        
        if "Found DFU" in result.stdout:
            print("Device successfully entered DFU mode")
            return True
        
        print("Device not in DFU mode yet, trying another method...")
    except:
        print("odrivetool method failed, trying direct USB method...")
    
    # If we're here, we need to try a more forceful approach
    print("Please physically disconnect and reconnect the ODrive while holding the DFU button")
    print("The DFU button is the button on the ODrive board")
    input("Press Enter when you have reconnected the board in DFU mode...")
    
    # Check if device is in DFU mode now
    try:
        result = subprocess.run(["dfu-util", "-l"], 
                              capture_output=True, text=True, check=False)
        
        if "Found DFU" in result.stdout:
            print("Device successfully entered DFU mode")
            return True
    except:
        pass
    
    print("Could not confirm device is in DFU mode. We'll try to flash anyway.")
    return False

def download_firmware(version="0.5.1", hw_version="3.6"):
    """Download firmware binary from ODrive github"""
    firmware_file = f"ODriveFirmware_v{hw_version}_{version}.hex"
    url = f"https://github.com/odriverobotics/ODrive/releases/download/v{version}/{firmware_file}"
    
    print(f"Downloading firmware from: {url}")
    
    # Create a directory for the firmware if it doesn't exist
    firmware_dir = os.path.expanduser("~/odrive_firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    
    firmware_path = os.path.join(firmware_dir, firmware_file)
    
    # Try to use curl to download the file
    try:
        subprocess.run(["curl", "-L", url, "-o", firmware_path], check=True)
        print(f"Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("curl failed, trying wget...")
    
    # Try wget if curl fails
    try:
        subprocess.run(["wget", url, "-O", firmware_path], check=True)
        print(f"Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("wget failed. Please download the firmware manually from:")
        print(url)
        firmware_path = input("Enter the path to the downloaded firmware file: ")
        return firmware_path

def flash_firmware(firmware_path):
    """Flash firmware using dfu-util"""
    print(f"Flashing firmware: {firmware_path}")
    
    try:
        # Run dfu-util command
        subprocess.run([
            "dfu-util",
            "-a", "0",                 # Alt setting
            "-s", "0x08000000:leave",  # Start address and leave DFU mode after flashing
            "-D", firmware_path        # Firmware file
        ], check=True)
        
        print("Firmware flashed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error flashing firmware: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Force update ODrive firmware")
    parser.add_argument('--version', default="0.5.1", help="Firmware version to install")
    parser.add_argument('--hw-version', default="3.6", help="Hardware version (default: 3.6)")
    args = parser.parse_args()
    
    # Check for ODrive
    if not find_odrive():
        print("No ODrive found. Exiting.")
        sys.exit(1)
    
    # Check for dfu-util
    if not check_dfu_util():
        if not install_dfu_util():
            print("Cannot proceed without dfu-util. Please install it manually.")
            sys.exit(1)
    
    # Download firmware
    firmware_path = download_firmware(args.version, args.hw_version)
    
    # Put ODrive in DFU mode
    force_dfu_mode()
    
    # Flash firmware
    if flash_firmware(firmware_path):
        print(f"ODrive firmware updated to version {args.version}")
        print("Please power cycle the ODrive to start using the new firmware.")
    else:
        print("Firmware update failed.")
        print("You may need to try again or use the STLink/2 method described in the ODrive documentation.")

if __name__ == "__main__":
    main()
