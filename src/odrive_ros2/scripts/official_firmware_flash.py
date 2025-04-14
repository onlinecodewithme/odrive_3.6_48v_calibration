#!/Users/randikaprasad/miniforge3/bin/python
"""
ODrive Official Firmware Flash Script
This script downloads firmware directly from the official ODrive documentation site.
"""

import os
import sys
import subprocess
import time
import platform
import re

# Check and install required packages
print("Checking required packages...")
try:
    import bs4
    import requests
    from bs4 import BeautifulSoup
    print("All required packages are installed.")
except ImportError:
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        print("Packages installed. Reloading modules...")
        import requests
        import bs4
        from bs4 import BeautifulSoup
    except Exception as e:
        print(f"Failed to install required packages: {e}")
        print("Please install them manually with:")
        print("pip install beautifulsoup4 requests")
        sys.exit(1)

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

def fetch_firmware_versions():
    """Fetch available firmware versions from the official ODrive documentation"""
    print_header("FETCHING FIRMWARE VERSIONS")
    print("Accessing official ODrive firmware page...")
    
    url = "https://docs.odriverobotics.com/releases/firmware"
    
    try:
        # Install Beautiful Soup if not already installed
        try:
            import bs4
        except ImportError:
            print("Installing required packages...")
            subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
            # Reload the module
            import bs4
        
        # Fetch the page
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find firmware sections for ODrive v3.x
        v3_versions = []
        
        # Look for version headers or links
        for element in soup.find_all(['h2', 'h3', 'a']):
            text = element.get_text()
            # Look for version patterns like v0.5.1
            match = re.search(r'v(\d+\.\d+\.\d+)', text)
            if match:
                version = match.group(1)
                v3_link = None
                
                # If this is a link element, check if it points to ODrive v3.x firmware
                if element.name == 'a' and element.has_attr('href'):
                    href = element['href']
                    if 'v3' in href.lower() and ('hex' in href.lower() or 'bin' in href.lower()):
                        v3_link = href
                
                # If not found directly, look for nearby links
                if not v3_link and element.name in ['h2', 'h3']:
                    next_links = element.find_next_siblings('a')
                    for link in next_links:
                        if link.has_attr('href'):
                            href = link['href']
                            if 'v3' in href.lower() and ('hex' in href.lower() or 'bin' in href.lower()):
                                v3_link = href
                                break
                
                if v3_link:
                    # Make sure URL is absolute
                    if not v3_link.startswith('http'):
                        v3_link = 'https://docs.odriverobotics.com' + v3_link
                    
                    v3_versions.append({
                        'version': version,
                        'url': v3_link
                    })
        
        if v3_versions:
            print(f"Found {len(v3_versions)} firmware versions for ODrive v3.x:")
            for i, version_info in enumerate(v3_versions):
                print(f"{i+1}. v{version_info['version']} - {version_info['url']}")
            return v3_versions
        else:
            print("No specific ODrive v3.x firmware links found on the page.")
            print("Using default firmware URL pattern...")
            
            # Default to the known pattern for firmware files
            return [
                {'version': '0.5.1', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.1/ODriveFirmware_v3.6_0.5.1.hex'},
                {'version': '0.5.4', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.4/ODriveFirmware_v3.6_0.5.4.hex'},
                {'version': '0.5.6', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.6/ODriveFirmware_v3.6_0.5.6.hex'}
            ]
    except Exception as e:
        print(f"Error fetching firmware versions: {e}")
        print("Using default firmware URLs...")
        
        # Fallback to default versions
        return [
            {'version': '0.5.1', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.1/ODriveFirmware_v3.6_0.5.1.hex'},
            {'version': '0.5.4', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.4/ODriveFirmware_v3.6_0.5.4.hex'},
            {'version': '0.5.6', 'url': 'https://github.com/odriverobotics/ODrive/releases/download/v0.5.6/ODriveFirmware_v3.6_0.5.6.hex'}
        ]

def select_firmware(versions):
    """Allow user to select a firmware version"""
    if not versions:
        print("No firmware versions available.")
        return None
    
    print("\nSelect a firmware version to flash:")
    default_version = None
    
    # Find v0.5.1 as default (known to work well)
    for i, version_info in enumerate(versions):
        if version_info['version'] == '0.5.1':
            default_version = i
            break
    
    if default_version is None:
        default_version = 0  # Use first version if 0.5.1 not found
    
    selected = default_version
    try:
        choice = input(f"Enter selection [1-{len(versions)}] (default: {default_version+1} - v{versions[default_version]['version']}): ")
        if choice.strip():
            selected = int(choice) - 1
            if selected < 0 or selected >= len(versions):
                print(f"Invalid selection. Using default (v{versions[default_version]['version']}).")
                selected = default_version
    except ValueError:
        print(f"Invalid input. Using default (v{versions[default_version]['version']}).")
        selected = default_version
    
    print(f"Selected firmware v{versions[selected]['version']}")
    return versions[selected]

def download_firmware(firmware_info):
    """Download firmware from the specified URL"""
    version = firmware_info['version']
    url = firmware_info['url']
    
    print(f"Downloading firmware v{version} from {url}...")
    
    # Create directory for firmware files
    firmware_dir = os.path.expanduser("~/odrive_firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    
    # Generate filename from URL
    filename = os.path.basename(url)
    if not filename:
        filename = f"ODriveFirmware_v3.6_{version}.hex"
    
    firmware_path = os.path.join(firmware_dir, filename)
    
    # Check if file already exists
    if os.path.exists(firmware_path):
        print(f"Firmware file already exists at {firmware_path}")
        return firmware_path
    
    # Try to download using curl
    try:
        subprocess.run(["curl", "-L", url, "-o", firmware_path], check=True)
        print(f"✅ Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("curl failed, trying wget...")
    
    # Try wget as fallback
    try:
        subprocess.run(["wget", url, "-O", firmware_path], check=True)
        print(f"✅ Firmware downloaded to {firmware_path}")
        return firmware_path
    except subprocess.CalledProcessError:
        print("Download failed. Please download manually from:")
        print(url)
        alternative_path = input("Enter path to the downloaded firmware file, or press Enter to exit: ")
        if alternative_path.strip():
            return alternative_path
        else:
            print("Exiting without flashing firmware.")
            sys.exit(1)

def flash_firmware(firmware_path):
    """Flash firmware using dfu-util"""
    print_header("FLASHING FIRMWARE")
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
        
        # Print output
        print(result.stdout)
        
        # Check for success
        if "File downloaded successfully" in result.stdout:
            print("✅ Firmware flashed successfully!")
            return True
        else:
            print("❌ Firmware flashing may have failed.")
            print("Error output:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error flashing firmware: {e}")
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
    print_header("ODRIVE OFFICIAL FIRMWARE FLASH TOOL")
    
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
    
    # Fetch available firmware versions
    firmware_versions = fetch_firmware_versions()
    
    # Let user select a firmware version
    selected_firmware = select_firmware(firmware_versions)
    if not selected_firmware:
        return 1
    
    # Download the firmware
    firmware_path = download_firmware(selected_firmware)
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
        print(f"ODrive firmware updated to v{selected_firmware['version']}")
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
        print("3. Check the ODrive documentation for troubleshooting")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
