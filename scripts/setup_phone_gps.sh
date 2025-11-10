#!/bin/bash
# Setup Android Phone GPS for Gattrose-NG

echo "========================================================================="
echo "  Android Phone GPS Setup for Gattrose-NG"
echo "========================================================================="
echo ""

# Check if phone is connected via USB
echo "[*] Checking USB connection..."
if lsusb | grep -iE "google|android|18d1" > /dev/null; then
    echo "[+] Android phone detected via USB"
else
    echo "[!] No Android phone detected via USB"
    echo ""
    echo "    Please connect your Android phone via USB cable"
    exit 1
fi

echo ""
echo "========================================================================="
echo "  Step 1: Enable USB Debugging on Your Phone"
echo "========================================================================="
echo ""
echo "  1. Open Settings on your phone"
echo "  2. Go to 'About Phone' or 'About Device'"
echo "  3. Tap 'Build Number' 7 times (you'll see 'You are now a developer!')"
echo "  4. Go back to Settings"
echo "  5. Open 'System' or 'Developer Options'"
echo "  6. Enable 'USB Debugging'"
echo "  7. When prompted on phone, tap 'Allow' to authorize this computer"
echo ""
read -p "Press ENTER when you have enabled USB debugging..."

# Check ADB connection
echo ""
echo "[*] Checking ADB connection..."
adb devices -l

if adb devices | grep -v "List of devices" | grep "device$" > /dev/null; then
    echo "[+] Phone is authorized and connected!"
else
    echo "[!] Phone not authorized yet"
    echo ""
    echo "    Check your phone screen for the USB debugging authorization dialog"
    echo "    Tap 'Allow' and check 'Always allow from this computer'"
    echo ""
    read -p "Press ENTER after authorizing..."

    adb devices
fi

echo ""
echo "========================================================================="
echo "  Step 2: Testing GPS Connection"
echo "========================================================================="
echo ""

# Get GPS location
echo "[*] Reading GPS location from phone..."
echo ""

adb shell "dumpsys location" | grep -A 15 "gps:" | head -20

echo ""
echo "========================================================================="
echo "  Step 3: Testing GPS Service"
echo "========================================================================="
echo ""

cd "$(dirname "$0")"
.venv/bin/python test_phone_gps.py

echo ""
echo "========================================================================="
echo "  Setup Complete!"
echo "========================================================================="
echo ""
echo "  Your phone GPS is now ready to use with Gattrose-NG"
echo ""
