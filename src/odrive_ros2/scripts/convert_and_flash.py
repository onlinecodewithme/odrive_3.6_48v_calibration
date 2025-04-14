#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Firmware Convert and Flash Script
This script converts the ELF firmware to binary format and flashes it.
"""

import os
import sys
import subprocess
import time
import platform

# Custom firmware URL
CUSTOM_FIRMWARE_URL = "https://odrive-cdn.nyc3.digitaloceanspaces.com/releases/firmware/BhI6UROJjzOq9x1S755S9xKxf8SJcOhtuW9g2OV45-8/firmware.elf"

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_dependencies():
    """Check for required tools"""
    print_header("CHECKING DEPENDENCIES")
    
    # Check for dfu-util
    dfu_ok = False
    try:
        result = subprocess.run(["dfu-util", "--version"], 
                               capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ dfu-util is available")
            dfu_ok = True
        else:
            print("❌ dfu-util is not installed")
    except:
        print("❌ dfu-util is not installed")
    
    # Check for arm-none-eabi-objcopy
    objcopy_ok = False
    try:
        result = subprocess.run(["arm-none-eabi-objcopy", "--version"], 
                               capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ arm-none-eabi-objcopy is available")
            objcopy_ok = True
        else:
            print("❌ arm-none-eabi-objcopy is not installed")
    except:
        print("❌ arm-none-eabi-objcopy is not installed")
    
    if not dfu_ok:
        print("\nPlease install dfu-util:")
        print("macOS: brew install dfu-util")
        print("Linux: sudo apt install dfu-util")
    
    if not objcopy_ok:
        print("\nPlease install arm-none-eabi-gcc toolchain:")
        print("macOS: brew install arm-none-eabi-gcc")
        print("Linux: sudo apt install gcc-arm-none-eabi")
    
    return dfu_ok and objcopy_ok

def download_firmware():
    """Download the firmware ELF file"""
    print_header("DOWNLOADING FIRMWARE")
    print(f"Source: {CUSTOM_FIRMWARE_URL}")
    
    # Create firmware directory
    firmware_dir = os.path.expanduser("~/odrive_firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    
    # Paths for ELF and BIN files
    elf_path = os.path.join(firmware_dir, "custom_firmware.elf")
    
    if os.path.exists(elf_path):
        replace = input("Firmware ELF file already exists. Download again? (y/n): ")
        if replace.lower() != 'y':
            print(f"Using existing file: {elf_path}")
            return elf_path
    
    try:
        # Download with curl
        subprocess.run(["curl", "-L", CUSTOM_FIRMWARE_URL, "-o", elf_path], check=True)
        print(f"✅ Firmware downloaded to {elf_path}")
        return elf_path
    except:
        try:
            # Try with wget if curl fails
            subprocess.run(["wget", CUSTOM_FIRMWARE_URL, "-O", elf_path], check=True)
            print(f"✅ Firmware downloaded to {elf_path}")
            return elf_path
        except:
            print("❌ Failed to download firmware")
            print("Please download manually and provide the path")
            path = input("Enter path to the ELF file (or press Enter to exit): ")
            if path.strip():
                return path
            else:
                sys.exit(1)

def convert_elf_to_binary(elf_path):
    """Convert ELF file to binary using arm-none-eabi-objcopy"""
    print_header("CONVERTING ELF TO BINARY")
    print(f"Source ELF: {elf_path}")
    
    # Create binary file path
    bin_path = elf_path.replace('.elf', '.bin')
    if not bin_path.endswith('.bin'):
        bin_path = elf_path + '.bin'
    
    print(f"Target binary: {bin_path}")
    
    try:
        subprocess.run([
            "arm-none-eabi-objcopy",
            "-O", "binary",
            elf_path,
            bin_path
        ], check=True)
        
        print(f"✅ Successfully converted to binary: {bin_path}")
        
        # Check file sizes
        elf_size = os.path.getsize(elf_path)
        bin_size = os.path.getsize(bin_path)
        
        print(f"ELF size: {elf_size:,} bytes")
        print(f"BIN size: {bin_size:,} bytes")
        
        return bin_path
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return None

def check_dfu_mode():
    """Check if device is in DFU mode"""
    print_header("CHECKING DFU MODE")
    
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

def flash_binary(bin_path):
    """Flash the binary file to the ODrive"""
    print_header("FLASHING BINARY FIRMWARE")
    print(f"Binary file: {bin_path}")
    
    # First attempt - standard approach
    print("\nAttempt 1: Using standard flashing method...")
    try:
        result = subprocess.run([
            "dfu-util",
            "-v",                      # Verbose output
            "-a", "0",                 # Alt setting
            "-s", "0x08000000:leave",  # Start address with leave flag
            "-D", bin_path             # Binary file
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully!")
            return True
    except Exception as e:
        print(f"Error: {e}")
    
    # Second attempt - with different addressing
    print("\nAttempt 2: Using alternative addressing...")
    try:
        alt_result = subprocess.run([
            "dfu-util",
            "-a", "0",
            "-s", "0x08000000",        # Just address, no leave flag
            "-D", bin_path
        ], capture_output=True, text=True)
        
        print(alt_result.stdout)
        
        if "File downloaded successfully" in alt_result.stdout:
            print("✅ Firmware flashed successfully with alternative method!")
            # Attempt to reset device
            subprocess.run(["dfu-util", "-e"], check=False)
            return True
    except Exception as e:
        print(f"Error: {e}")
    
    print("❌ Standard flashing methods failed.")
    
    # Third attempt - simplest approach
    print("\nAttempt 3: Using simplest method...")
    try:
        simple_result = subprocess.run([
            "dfu-util",
            "-D", bin_path
        ], capture_output=True, text=True)
        
        print(simple_result.stdout)
        
        if "File downloaded successfully" in simple_result.stdout:
            print("✅ Firmware flashed successfully with simple method!")
            return True
    except Exception as e:
        print(f"Error: {e}")
    
    print("❌ All flashing methods failed")
    return False

def main():
    print_header("ODRIVE FIRMWARE CONVERT & FLASH TOOL")
    print("This tool converts the ODrive firmware ELF file to binary format")
    print("and then flashes it to the device.")
    
    # Check dependencies
    if not check_dependencies():
        print("\nMissing required dependencies. Please install them and try again.")
        return 1
    
    # Download firmware
    elf_path = download_firmware()
    if not elf_path:
        return 1
    
    # Convert ELF to binary
    bin_path = convert_elf_to_binary(elf_path)
    if not bin_path:
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
    
    # Flash the binary
    if flash_binary(bin_path):
        print_header("SUCCESS")
        print("ODrive firmware successfully updated!")
        print("\nNext steps:")
        print("1. Power cycle the ODrive (disconnect and reconnect)")
        print("2. Wait 5-10 seconds for initialization")
        print("3. Run the check script: ./scripts/check_odrive.py")
        return 0
    else:
        print_header("FIRMWARE UPDATE FAILED")
        print("Please try:")
        print("1. Make sure you have the correct firmware file for your ODrive version")
        print("2. Ensure the ODrive is properly in DFU mode")
        print("3. Try a different USB port or cable")
        print("4. Contact the firmware provider for further assistance")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
