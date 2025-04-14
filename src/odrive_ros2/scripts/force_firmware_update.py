#!/usr/bin/env python3
"""
ODrive Firmware Force Update Script
This script bypasses the typical firmware checks and forcefully updates the ODrive firmware.
"""

import sys
import os
import argparse
import time
import requests
import tempfile
import platform
import subprocess
import odrive
from odrive.utils import dump_errors
from odrive.configuration import backup_config

FIRMWARE_BASE_URL = "https://github.com/odriverobotics/ODrive/releases/download"

def find_odrive():
    print("Looking for ODrive...")
    try:
        od = odrive.find_any(timeout=10)
        print(f"Found ODrive (Serial: {od.serial_number})")
        return od
    except TimeoutError:
        print("No ODrive found. Is it connected and powered?")
        return None

def get_hw_version(od):
    try:
        hw_version = f"{od.hw_version_major}.{od.hw_version_minor}"
        print(f"Hardware version: {hw_version}")
        return hw_version
    except:
        print("Could not determine hardware version. Using 3.6 as default.")
        return "3.6"

def get_latest_version():
    try:
        # This is a simple approach - in a production environment, you'd use the GitHub API
        print("Checking for latest firmware version...")
        response = requests.get("https://github.com/odriverobotics/ODrive/releases/latest")
        version = response.url.split('/')[-1]
        if version.startswith('v'):
            version = version[1:]  # Remove 'v' prefix
        print(f"Latest version: {version}")
        return version
    except:
        print("Could not determine latest version. Using 0.5.6 as default.")
        return "0.5.6"

def download_firmware(hw_version, firmware_version):
    """Download firmware binary for the specified hardware and firmware versions"""
    firmware_file = f"ODriveFirmware_v{hw_version}_{firmware_version}.hex"
    url = f"{FIRMWARE_BASE_URL}/v{firmware_version}/{firmware_file}"
    
    print(f"Downloading firmware from {url}...")
    
    temp_dir = tempfile.gettempdir()
    local_path = os.path.join(temp_dir, firmware_file)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Firmware downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"Error downloading firmware: {e}")
        sys.exit(1)

def backup_odrive_config(od):
    """Backup ODrive configuration before flashing"""
    print("Backing up ODrive configuration...")
    try:
        # Create a backup directory if it doesn't exist
        backup_dir = os.path.expanduser("~/odrive_backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Filename with timestamp
        filename = f"odrive_config_{od.serial_number}_{int(time.time())}.json"
        backup_path = os.path.join(backup_dir, filename)
        
        # Backup configuration
        backup_config(od, backup_path)
        print(f"Configuration backed up to {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Warning: Failed to backup configuration: {e}")
        return None

def install_dfu_util():
    """Install dfu-util if it's not already installed"""
    # Check if dfu-util is installed
    try:
        subprocess.run(["dfu-util", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        print("dfu-util is already installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("dfu-util not found, attempting to install...")
    
    system = platform.system()
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
    except subprocess.CalledProcessError:
        print(f"Failed to install dfu-util. Please install it manually.")
        return False

def force_dfu_mode(od):
    """Force the ODrive into DFU mode"""
    print("Putting ODrive into DFU mode...")
    try:
        # Try the firmware's built-in command
        od.enter_dfu_mode()
        print("ODrive entered DFU mode via official command")
        return True
    except:
        print("Could not use built-in DFU mode command, trying manual method...")
    
    try:
        # Fallback to manual method
        import usb.core
        dev = usb.core.find(idVendor=0x1209, idProduct=0x0d32)
        if dev is None:
            print("ODrive USB device not found")
            return False
        
        try:
            # This command should cause the ODrive to reboot into DFU mode
            dev.ctrl_transfer(0x40, 0xDF, 0, 0, None)
            print("ODrive entered DFU mode via manual command")
            time.sleep(2)  # Give it time to reboot
            return True
        except:
            print("Failed to send DFU command via USB")
            return False
    except ImportError:
        print("PyUSB not installed. Please install with: pip install pyusb")
        return False

def flash_with_dfu_util(firmware_path):
    """Flash the firmware using dfu-util"""
    print("Flashing firmware with dfu-util...")
    
    # Wait for DFU device to appear
    time.sleep(2)
    
    try:
        # Run dfu-util command to flash the firmware
        cmd = [
            "dfu-util",
            "-a", "0",              # Target specific alt setting on device
            "-s", "0x08000000:leave",  # Start address and leave DFU mode after flashing
            "-D", firmware_path     # Path to firmware file
        ]
        
        # Execute the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line.strip())
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            print("Firmware flashed successfully!")
            return True
        else:
            print(f"dfu-util failed with return code {process.returncode}")
            return False
    
    except Exception as e:
        print(f"Error flashing firmware: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Force update ODrive firmware')
    parser.add_argument('--version', help='Firmware version to install (defaults to latest)')
    parser.add_argument('--no-backup', action='store_true', help='Skip configuration backup')
    args = parser.parse_args()
    
    # Find connected ODrive
    od = find_odrive()
    if not od:
        sys.exit(1)
    
    # Get hardware version
    hw_version = get_hw_version(od)
    
    # Get firmware version to install
    firmware_version = args.version if args.version else get_latest_version()
    
    # Backup configuration if not skipped
    if not args.no_backup:
        backup_path = backup_odrive_config(od)
    
    # Install dfu-util if needed
    if not install_dfu_util():
        print("Cannot proceed without dfu-util")
        sys.exit(1)
    
    # Download firmware
    firmware_path = download_firmware(hw_version, firmware_version)
    
    # Put ODrive in DFU mode
    if not force_dfu_mode(od):
        print("Failed to put ODrive in DFU mode. Try running this script again or manually reset the board.")
        sys.exit(1)
    
    # Flash firmware
    if flash_with_dfu_util(firmware_path):
        print(f"ODrive firmware updated to version {firmware_version}")
        print("Waiting for ODrive to restart...")
        time.sleep(5)
        
        # Try to reconnect
        try:
            new_od = odrive.find_any(timeout=10)
            print(f"Reconnected to ODrive. New firmware version: {new_od.fw_version_major}.{new_od.fw_version_minor}.{new_od.fw_version_revision}")
        except:
            print("Could not reconnect to ODrive. It may need a power cycle.")
    else:
        print("Firmware update failed. Try again or follow manual instructions in the ODrive documentation.")

if __name__ == "__main__":
    main()
