#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Recovery Tool

This script helps diagnose and recover an ODrive that's not being detected
after a firmware update.
"""

import os
import sys
import time
import subprocess
import platform
import usb.core
import usb.util
import glob
import re

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_usb_devices():
    """Check all USB devices connected to the system"""
    print_header("CHECKING USB DEVICES")
    
    print("Looking for USB devices...")
    
    # Check using system-specific commands
    if platform.system() == "Darwin":  # macOS
        try:
            # First try system_profiler
            print("\nRunning system_profiler to list USB devices:")
            subprocess.run(["system_profiler", "SPUSBDataType"], check=False)
            
            # Also try ioreg which might show more details
            print("\nRunning ioreg to check for ODrive devices:")
            ioreg_output = subprocess.run(
                ["ioreg", "-p", "IOUSB"], 
                capture_output=True, 
                text=True, 
                check=False
            ).stdout
            
            if "ODrive" in ioreg_output:
                print("Found ODrive-related device in ioreg output!")
                for line in ioreg_output.split('\n'):
                    if "ODrive" in line:
                        print(f"  {line.strip()}")
            else:
                print("No ODrive-related devices found in ioreg output.")
        except Exception as e:
            print(f"Error running system commands: {e}")
    
    elif platform.system() == "Linux":
        try:
            print("\nRunning lsusb to list USB devices:")
            subprocess.run(["lsusb"], check=False)
            
            # Check dmesg for USB connection events
            print("\nChecking recent USB connection events in dmesg:")
            subprocess.run(["dmesg", "|", "grep", "USB", "|", "tail", "-n", "20"], 
                         shell=True, check=False)
        except Exception as e:
            print(f"Error running system commands: {e}")
    
    # Check using PyUSB
    try:
        print("\nScanning all USB devices using PyUSB:")
        devices = usb.core.find(find_all=True)
        if devices:
            for i, dev in enumerate(devices):
                try:
                    print(f"Device {i+1}:")
                    print(f"  ID {dev.idVendor:04x}:{dev.idProduct:04x}")
                    try:
                        print(f"  Manufacturer: {usb.util.get_string(dev, dev.iManufacturer)}")
                    except:
                        pass
                    try:
                        print(f"  Product: {usb.util.get_string(dev, dev.iProduct)}")
                    except:
                        pass
                except:
                    print(f"  Could not get detailed info for device {i+1}")
        else:
            print("No USB devices found using PyUSB.")
    except Exception as e:
        print(f"Error scanning USB devices: {e}")
    
    # Check specifically for ODrive VID/PID
    try:
        print("\nLooking specifically for ODrive devices:")
        # Standard ODrive VID/PID
        odrive_dev = usb.core.find(idVendor=0x1209, idProduct=0x0d32)
        if odrive_dev:
            print("Found ODrive device in normal mode!")
            return True
        
        # DFU mode VID/PID
        dfu_dev = usb.core.find(idVendor=0x0483, idProduct=0xdf11)
        if dfu_dev:
            print("Found ODrive device in DFU mode!")
            return True
            
        print("No ODrive or DFU mode devices found.")
    except Exception as e:
        print(f"Error looking for ODrive devices: {e}")
    
    return False

def check_serial_devices():
    """Check serial/tty devices that might be ODrive"""
    print_header("CHECKING SERIAL DEVICES")
    
    if platform.system() == "Darwin":  # macOS
        serial_patterns = [
            "/dev/tty.usbmodem*",
            "/dev/tty.usbserial*"
        ]
    elif platform.system() == "Linux":
        serial_patterns = [
            "/dev/ttyACM*",
            "/dev/ttyUSB*"
        ]
    else:
        print("Unsupported platform for serial device check")
        return False
    
    found_devices = []
    for pattern in serial_patterns:
        devices = glob.glob(pattern)
        found_devices.extend(devices)
    
    if found_devices:
        print(f"Found {len(found_devices)} serial devices:")
        for device in found_devices:
            print(f"  {device}")
        print("\nThese might be your ODrive. Try connecting to one of them.")
        return True
    else:
        print("No serial devices found that match typical ODrive patterns.")
        return False

def check_dfu_mode():
    """Check if a device in DFU mode is connected"""
    print_header("CHECKING FOR DFU MODE")
    
    try:
        print("Running dfu-util -l to check for devices in DFU mode:")
        result = subprocess.run(["dfu-util", "-l"], capture_output=True, text=True)
        print(result.stdout)
        
        if "Found DFU" in result.stdout:
            print("Device in DFU mode detected!")
            return True
        else:
            print("No device in DFU mode detected.")
            return False
    except Exception as e:
        print(f"Error checking DFU mode: {e}")
        return False

def attempt_connect_odrivetool():
    """Try to connect using odrivetool"""
    print_header("TRYING TO CONNECT WITH ODRIVETOOL")
    
    try:
        print("Attempting to find ODrive using odrivetool...")
        print("This will timeout after 10 seconds if no device is found.")
        print("Press Ctrl+C if it hangs.")
        
        cmd = [
            "odrivetool", "shell", "-c", 
            "import odrive; print('Searching...'); od = odrive.find_any(timeout=10); print(f'Connected to ODrive {od.serial_number}')"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(result.stdout)
        
        if "Connected to ODrive" in result.stdout:
            print("Successfully connected to ODrive!")
            return True
        else:
            print("Could not connect to ODrive using odrivetool.")
            return False
    except subprocess.TimeoutExpired:
        print("Connection attempt timed out.")
        return False
    except Exception as e:
        print(f"Error attempting to connect: {e}")
        return False

def try_exit_dfu_mode():
    """Try to exit DFU mode using dfu-util"""
    print_header("ATTEMPTING TO EXIT DFU MODE")
    
    if not check_dfu_mode():
        print("Device not in DFU mode, skipping...")
        return False
    
    print("Attempting to exit DFU mode...")
    try:
        # Create an empty file to use with dfu-util
        with open("/tmp/dummy.bin", "wb") as f:
            f.write(bytes([0xFF]))
        
        # Try to exit DFU mode by writing to a safe address with the leave flag
        subprocess.run([
            "dfu-util",
            "-a", "0",
            "-s", "0x08000000:leave",  # Address to write with leave flag
            "-D", "/tmp/dummy.bin"     # Dummy file
        ], check=False)
        
        print("Command executed. Check if the device has restarted in normal mode.")
        print("Wait a few seconds for the device to initialize...")
        time.sleep(5)
        
        # Try to connect with odrivetool
        return attempt_connect_odrivetool()
    except Exception as e:
        print(f"Error attempting to exit DFU mode: {e}")
        return False

def suggest_power_cycle():
    """Suggest a full power cycle"""
    print_header("POWER CYCLE INSTRUCTIONS")
    
    print("It seems the ODrive is not being detected properly.")
    print("Please perform a full power cycle:")
    print("1. Disconnect the USB cable from your computer")
    print("2. Disconnect power from the ODrive (48V supply)")
    print("3. Wait 30 seconds")
    print("4. Reconnect power to the ODrive")
    print("5. Reconnect the USB cable to your computer")
    print("\nAfter following these steps, run this script again to see if the ODrive is detected.")
    
    response = input("\nHave you already tried a full power cycle? (y/n): ")
    return response.lower() == 'y'

def display_recovery_options():
    """Display recovery options for the user"""
    print_header("RECOVERY OPTIONS")
    
    print("Here are your options to recover the ODrive:")
    print("\n1. OPTION ONE: Try again with manual DFU mode")
    print("   - Run ./scripts/manual_dfu_flash.py")
    print("   - Follow the instructions carefully")
    print("   - Make sure to use the DFU button (Boot0) while powering on the device")
    
    print("\n2. OPTION TWO: Use an STLink/2 programmer (advanced)")
    print("   - This is a more direct way to flash the firmware")
    print("   - Requires additional hardware (STLink/2 programmer)")
    print("   - Follow instructions at: https://docs.odriverobotics.com/developer-guide")
    
    print("\n3. OPTION THREE: Use the ODrive in its current state")
    print("   - If the device was working before, you might be able to use it with the current firmware")
    print("   - The ROS driver should work with firmware version 0.5.1 and above")
    
    print("\nFor more details, see the FIRMWARE_UPDATE.md file in this package.")

def main():
    print("ODrive Recovery Tool")
    print("This tool will help diagnose and potentially fix connection issues with your ODrive.")
    
    # First, check all USB devices
    usb_found = check_usb_devices()
    
    # Check serial devices
    serial_found = check_serial_devices()
    
    # Check for DFU mode
    dfu_found = check_dfu_mode()
    
    # Try to connect using odrivetool
    odrive_connected = attempt_connect_odrivetool()
    
    if odrive_connected:
        print_header("SUCCESS")
        print("Successfully connected to ODrive!")
        print("Your ODrive is now detected and ready to use.")
        print("You can proceed with using the ROS driver.")
        return 0
    
    # If in DFU mode, try to exit it
    if dfu_found:
        print("Device is in DFU mode. Attempting to exit...")
        if try_exit_dfu_mode():
            print_header("SUCCESS")
            print("Successfully exited DFU mode and connected to ODrive!")
            return 0
    
    # Suggest power cycle if not already tried
    if not suggest_power_cycle():
        print("\nPlease try a full power cycle first, then run this script again.")
        return 1
    
    # Display recovery options
    display_recovery_options()
    return 1

if __name__ == "__main__":
    sys.exit(main())
