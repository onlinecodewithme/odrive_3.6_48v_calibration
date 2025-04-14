#!/Users/randikaprasad/miniforge3/bin/python
"""
Manual ODrive Firmware Flash Script
This script assumes you've already put the ODrive in DFU mode manually.
"""

import os
import sys
import subprocess
import time
import platform

def check_dfu_mode():
    """Check if a device in DFU mode is connected"""
    print("Checking for devices in DFU mode...")
    try:
        result = subprocess.run(["dfu-util", "-l"], capture_output=True, text=True)
        if "Found DFU" in result.stdout:
            print("✅ Device in DFU mode detected!")
            return True
        else:
            print("❌ No device in DFU mode detected.")
            return False
    except Exception as e:
        print(f"Error checking DFU mode: {e}")
        return False

def download_firmware(version="0.5.1", hw_version="3.6"):
    """Download firmware binary from ODrive GitHub"""
    firmware_file = f"ODriveFirmware_v{hw_version}_{version}.hex"
    url = f"https://github.com/odriverobotics/ODrive/releases/download/v{version}/{firmware_file}"
    
    print(f"Downloading firmware from: {url}")
    
    # Create a directory for the firmware if it doesn't exist
    firmware_dir = os.path.expanduser("~/odrive_firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    
    firmware_path = os.path.join(firmware_dir, firmware_file)
    
    # Check if we already have the file
    if os.path.exists(firmware_path):
        print(f"Firmware file already exists at {firmware_path}")
        return firmware_path
    
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
    print("This may take a minute or two...")
    
    try:
        # Run dfu-util command
        result = subprocess.run([
            "dfu-util",
            "-a", "0",                 # Alt setting
            "-s", "0x08000000:leave",  # Start address and leave DFU mode after flashing
            "-D", firmware_path        # Firmware file
        ], capture_output=True, text=True)
        
        # Check for success
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully!")
            return True
        else:
            print("❌ Firmware flashing may have failed.")
            print("Output:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error flashing firmware: {e}")
        return False

def manual_dfu_instructions():
    """Print instructions for manually entering DFU mode"""
    print("\n====== HOW TO PUT ODRIVE IN DFU MODE MANUALLY ======")
    print("1. Disconnect power from the ODrive")
    print("2. Connect the ODrive to your computer via USB")
    print("3. Find and press the DFU button on the ODrive board")
    print("   (It's a small button on the board, often labeled 'Boot0')")
    print("4. While holding the button, reconnect power to the ODrive")
    print("5. Keep holding the button for 2-3 seconds, then release")
    print("===================================================\n")

def main():
    print("ODrive Manual Firmware Flash Utility")
    print("------------------------------------")
    
    # Check for dfu-util
    try:
        subprocess.run(["dfu-util", "--version"], 
                      capture_output=True, text=True, check=True)
        print("✅ dfu-util is available")
    except:
        print("❌ dfu-util is not installed. Please install it first.")
        print("On macOS: brew install dfu-util")
        print("On Linux: sudo apt install dfu-util")
        return
    
    # Download firmware
    firmware_version = "0.5.1"  # Downgrading to previously working version
    hw_version = "3.6"          # For ODrive 3.6
    firmware_path = download_firmware(firmware_version, hw_version)
    
    # Check if device is already in DFU mode
    if not check_dfu_mode():
        manual_dfu_instructions()
        
        # Wait for user to put device in DFU mode
        input("Press Enter once you've put the ODrive in DFU mode...")
        
        # Check again
        if not check_dfu_mode():
            print("Still can't detect the ODrive in DFU mode.")
            retry = input("Do you want to try flashing anyway? (y/n): ")
            if retry.lower() != 'y':
                print("Exiting. Please try again after successfully putting the ODrive in DFU mode.")
                return
    
    # Flash firmware
    if flash_firmware(firmware_path):
        print(f"\n✅ ODrive firmware updated to version {firmware_version}")
        print("Please power cycle the ODrive to start using the new firmware.")
    else:
        print("\n❌ Firmware update failed.")
        print("You may need to try again or refer to the ODrive documentation for troubleshooting.")

if __name__ == "__main__":
    main()
