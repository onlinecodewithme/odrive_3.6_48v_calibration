#!/Users/randikaprasad/miniforge3/bin/python
"""
Custom ODrive Firmware Flash Script
This script downloads and flashes a specific custom firmware.
"""

import os
import sys
import subprocess
import time
import platform

# Custom firmware URL provided by the user
CUSTOM_FIRMWARE_URL = "https://odrive-cdn.nyc3.digitaloceanspaces.com/releases/firmware/BhI6UROJjzOq9x1S755S9xKxf8SJcOhtuW9g2OV45-8/firmware.elf"

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

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

def download_firmware():
    """Download the custom firmware file"""
    print_header("DOWNLOADING CUSTOM FIRMWARE")
    print(f"Downloading from: {CUSTOM_FIRMWARE_URL}")
    
    # Create directory for firmware files
    firmware_dir = os.path.expanduser("~/odrive_firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    
    firmware_path = os.path.join(firmware_dir, "custom_firmware.elf")
    
    # Check if file already exists
    if os.path.exists(firmware_path):
        replace = input("Firmware file already exists. Download again? (y/n): ")
        if replace.lower() != 'y':
            print(f"Using existing firmware file: {firmware_path}")
            return firmware_path
    
    # Try to download using curl
    try:
        subprocess.run(["curl", "-L", CUSTOM_FIRMWARE_URL, "-o", firmware_path], check=True)
        print(f"✅ Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("curl failed, trying wget...")
    
    # Try wget as fallback
    try:
        subprocess.run(["wget", CUSTOM_FIRMWARE_URL, "-O", firmware_path], check=True)
        print(f"✅ Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("Download failed. Please download manually from:")
        print(CUSTOM_FIRMWARE_URL)
        alternative_path = input("Enter path to the downloaded firmware file, or press Enter to exit: ")
        if alternative_path.strip():
            return alternative_path
        else:
            print("Exiting without flashing firmware.")
            sys.exit(1)

def flash_firmware(firmware_path):
    """Flash firmware using dfu-util"""
    print_header("FLASHING CUSTOM FIRMWARE")
    print(f"Flashing firmware: {firmware_path}")
    print("This may take a minute or two...")
    
    # Since we saw a specific error related to file size, let's try multiple methods
    # with different parameters that might handle large ELF files better
    
    # Method 1: Standard approach but with more detailed debug output
    print("\nTrying Method 1: Standard flashing approach...")
    try:
        result = subprocess.run([
            "dfu-util",
            "-v",                      # Verbose output
            "-a", "0",                 # Alt setting
            "-s", "0x08000000:leave",  # Start address and leave DFU mode after flashing
            "-D", firmware_path        # Firmware file
        ], capture_output=True, text=True)
        
        print(result.stdout)
        print(result.stderr)
        
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully!")
            return True
    except Exception as e:
        print(f"Method 1 exception: {e}")
    
    print("\nTrying Method 2: Alternative addressing...")
    try:
        # Try using a different addressing scheme
        result = subprocess.run([
            "dfu-util",
            "-v",
            "-a", "0",
            "-s", "0x08000000",        # Just address, no leave flag
            "-D", firmware_path
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully with Method 2!")
            
            # Now try to reset the device
            print("Attempting to reset device...")
            subprocess.run(["dfu-util", "-e"], check=False)
            
            return True
    except Exception as e:
        print(f"Method 2 exception: {e}")
    
    print("\nTrying Method 3: Split file approach...")
    try:
        # Try downloading in segments (for some large files this works better)
        result = subprocess.run([
            "dfu-util",
            "-v",
            "-a", "0",
            "-s", "0x08000000:mass-erase:force",  # Erase first
            "-D", firmware_path
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully with Method 3!")
            
            # Reset the device
            subprocess.run(["dfu-util", "-e"], check=False)
            
            return True
    except Exception as e:
        print(f"Method 3 exception: {e}")
    
    print("\nAll automatic methods failed.")
    print("\nSuggested manual approach:")
    print("1. Convert the ELF file to a binary file:")
    print("   arm-none-eabi-objcopy -O binary custom_firmware.elf custom_firmware.bin")
    print("2. Flash the binary file:")
    print("   dfu-util -a 0 -s 0x08000000 -D custom_firmware.bin")
    print("\nYou may need to install the arm-none-eabi-gcc toolchain for this.")
    
    manual_attempt = input("Would you like to try a simpler method that might work? (y/n): ")
    if manual_attempt.lower() == 'y':
        print("\nTrying simpler approach...")
        try:
            simple_result = subprocess.run([
                "dfu-util",
                "-D", firmware_path
            ], capture_output=True, text=True)
            
            print(simple_result.stdout)
            
            if "File downloaded successfully" in simple_result.stdout:
                print("✅ Firmware flashed successfully with simple method!")
                return True
            else:
                print("❌ Simple method also failed.")
        except Exception as e:
            print(f"Simple method exception: {e}")
    
    return False

def manual_dfu_instructions():
    """Print instructions for manually entering DFU mode"""
    print_header("DFU MODE INSTRUCTIONS")
    print("To put your ODrive in DFU mode:")
    print("1. Disconnect power from the ODrive")
    print("2. Connect the ODrive to your computer via USB")
    print("3. Find and press the DFU button on the ODrive board")
    print("   (It's a small button on the board, often labeled 'Boot0')")
    print("4. While holding the button, reconnect power to the ODrive")
    print("5. Keep holding the button for 2-3 seconds, then release")

def main():
    print_header("ODRIVE CUSTOM FIRMWARE FLASH TOOL")
    
    # Check for dfu-util
    try:
        subprocess.run(["dfu-util", "--version"], 
                      capture_output=True, text=True, check=True)
        print("✅ dfu-util is available")
    except:
        print("❌ dfu-util is not installed. Please install it first:")
        print("   macOS: brew install dfu-util")
        print("   Linux: sudo apt install dfu-util")
        return 1
    
    # Download the firmware
    firmware_path = download_firmware()
    if not firmware_path:
        return 1
    
    # Check if device is in DFU mode
    if not check_dfu_mode():
        manual_dfu_instructions()
        
        input("\nPress Enter when you have put the ODrive in DFU mode...")
        
        # Check again
        if not check_dfu_mode():
            print("Still cannot detect ODrive in DFU mode.")
            retry = input("Do you want to try flashing anyway? (y/n): ")
            if retry.lower() != 'y':
                print("Exiting. Please try again after putting the ODrive in DFU mode.")
                return 1
    
    # Flash the firmware
    if flash_firmware(firmware_path):
        print_header("SUCCESS")
        print("ODrive firmware updated with custom firmware!")
        print("\nNext steps:")
        print("1. Power cycle the ODrive (disconnect and reconnect)")
        print("2. Wait 5-10 seconds for initialization")
        print("3. Run the check script: ./scripts/check_odrive.py")
        return 0
    else:
        print_header("FIRMWARE UPDATE FAILED")
        print("Please try:")
        print("1. Ensure the ODrive is properly in DFU mode")
        print("2. Try a different USB port or cable")
        print("3. Contact the firmware provider for specific flashing instructions")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
