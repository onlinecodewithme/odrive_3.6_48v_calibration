#!/Users/randikaprasad/miniforge3/bin/python
"""
Simple script to check ODrive connection and firmware version
"""
import sys
import time
import odrive
from odrive.enums import *

def main():
    print("Looking for ODrive...")
    try:
        od = odrive.find_any(timeout=10)
        print(f"Found ODrive!")
        print(f"Serial Number: {od.serial_number}")
        print(f"Hardware version: {od.hw_version_major}.{od.hw_version_minor}")
        print(f"Firmware version: {od.fw_version_major}.{od.fw_version_minor}.{od.fw_version_revision}")
        
        # Check axis states
        try:
            print("\nAxis 0 state:", od.axis0.current_state)
            print("Axis 1 state:", od.axis1.current_state)
        except:
            print("Could not read axis states")
        
        return 0
    except TimeoutError:
        print("No ODrive found. Please check connections and power.")
        return 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
